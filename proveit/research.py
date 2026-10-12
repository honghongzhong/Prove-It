"""Versioned research state shared by the browser and Codex tools.

SQLite is authoritative. Agent claims never set kernel verification or human review.
All writes use optimistic revisions so a delayed tool cannot erase researcher edits.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import uuid
from typing import Callable

from . import workspace
from .lean import verify, project_path

LOCK = threading.RLock()
NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_']*(?:\.[A-Za-z_][A-Za-z0-9_']*)*")
ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def artifact_hash(proof: dict) -> str:
    return digest([proof["source"], proof.get("natural_proof", "")])


def environment(project_id: str) -> str:
    path = project_path(project_id)
    import os
    files = {name: (path / name).read_text(encoding="utf-8") if (path / name).is_file() else ""
             for name in ("lean-toolchain", "lake-manifest.json", "lakefile.toml", "lakefile.lean")} if path else {}
    return digest([str(path), files, os.environ.get("LEAN_EXE", "lean")])


def _connect():
    connection = workspace._connect()
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS research_documents (
            filename TEXT PRIMARY KEY, revision INTEGER NOT NULL, state TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS research_revisions (
            id INTEGER PRIMARY KEY, filename TEXT NOT NULL, revision INTEGER NOT NULL,
            actor TEXT NOT NULL, action TEXT NOT NULL, state TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS research_messages (
            id INTEGER PRIMARY KEY, filename TEXT NOT NULL, role TEXT NOT NULL,
            content TEXT NOT NULL, created_at TEXT NOT NULL);
    """)
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS research_events (
            id INTEGER PRIMARY KEY, filename TEXT NOT NULL, event_key TEXT NOT NULL,
            kind TEXT NOT NULL, content TEXT NOT NULL, status TEXT NOT NULL,
            tool TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(filename,event_key));
    """)
    return connection


def _initial() -> dict:
    return {"revision": 0, "goal": {}, "steps": [], "reviews": {}, "checks": [],
            "projectId": "standalone", "threadId": None, "runStatus": "idle", "runReason": ""}


def get(filename: str) -> dict:
    proof = workspace.get_proof(filename)
    with _connect() as db:
        row = db.execute("SELECT state FROM research_documents WHERE filename=?", (filename,)).fetchone()
    state = json.loads(row[0]) if row else _initial()
    state["proofId"] = filename
    goal_hash = digest(state["goal"])
    state["goalReviewed"] = state["reviews"].get("goal") == goal_hash
    latest = state["checks"][-1] if state["checks"] else None
    try:
        current_environment = environment(state["projectId"])
        state["environmentError"] = None
    except (ValueError, OSError) as exc:
        current_environment = None
        state["environmentError"] = str(exc)
    state["verificationCurrent"] = bool(latest and latest["sourceHash"] == digest(proof["source"])
        and latest["goalHash"] == goal_hash and latest["projectId"] == state["projectId"]
        and latest["environment"] == current_environment)
    state["targetVerified"] = bool(state["verificationCurrent"] and latest["targetVerified"])
    state["phase"] = ("目标已验证，待人工审阅" if state["targetVerified"] else
                      "形式化与证明探索" if state["goal"] else "澄清研究目标")
    if state["targetVerified"] and state["goalReviewed"]:
        state["phase"] = "形式目标已验证，目标含义已审阅"
    return state


def mutate(filename: str, revision: int, actor: str, action: str, update: Callable[[dict], None]) -> dict:
    workspace.get_proof(filename)
    with LOCK, _connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT state FROM research_documents WHERE filename=?", (filename,)).fetchone()
        state = json.loads(row[0]) if row else _initial()
        if revision != state["revision"]:
            raise ValueError("研究状态已更新，请重新读取后再修改，避免覆盖他人的工作。")
        update(state)
        state["revision"] += 1
        raw = json.dumps(state, ensure_ascii=False)
        db.execute("INSERT OR REPLACE INTO research_documents VALUES(?,?,?)", (filename, state["revision"], raw))
        db.execute("INSERT INTO research_revisions(filename,revision,actor,action,state,created_at) VALUES(?,?,?,?,?,?)",
                   (filename, state["revision"], actor, action, raw, workspace._now()))
    return get(filename)


def update(filename: str, payload: dict, actor: str = "researcher") -> dict:
    revision = payload.get("revision")
    if type(revision) is not int:
        raise ValueError("必须提供当前 revision。")
    def apply(state):
        if "goal" in payload:
            goal = payload["goal"]
            if not isinstance(goal, dict):
                raise ValueError("目标必须是对象。")
            cleaned = {key: str(goal.get(key, "")).strip() for key in ("natural", "formalType", "targetName", "assumptions")}
            if not all(cleaned[key] for key in ("natural", "formalType", "targetName")):
                raise ValueError("目标需包含自然语言、完整封闭 Lean 类型和定理名称。")
            if not NAME.fullmatch(cleaned["targetName"]) or any(len(v) > 20000 for v in cleaned.values()):
                raise ValueError("定理名或目标长度无效。")
            state["goal"] = cleaned
        if "steps" in payload:
            steps = payload["steps"]
            if not isinstance(steps, list) or len(steps) > 200:
                raise ValueError("步骤必须是最多 200 项的列表。")
            cleaned, ids = [], set()
            for step in steps:
                if not isinstance(step, dict):
                    raise ValueError("步骤格式错误。")
                item = {key: str(step.get(key, "")) for key in ("id", "title", "content", "leanDeclaration", "status")}
                if not item["id"] or item["id"] in ids or not item["title"]:
                    raise ValueError("步骤需有唯一 id 和标题。")
                if item["status"] not in {"planned", "working", "candidate", "blocked"}:
                    raise ValueError("步骤状态只能是 planned/working/candidate/blocked；验证状态由 Lean 提供。")
                if any(len(v) > 20000 for v in item.values()):
                    raise ValueError("步骤内容过长。")
                deps = step.get("dependsOn", [])
                if not isinstance(deps, list) or any(not isinstance(d, str) for d in deps):
                    raise ValueError("步骤依赖必须是 id 列表。")
                item["dependsOn"] = deps
                cleaned.append(item)
                ids.add(item["id"])
            graph = {s["id"]: s["dependsOn"] for s in cleaned}
            visited = set()
            def visit(key, stack):
                if key not in ids or key in stack:
                    raise ValueError("步骤依赖不存在或形成循环。")
                if key in visited:
                    return
                for dep in graph[key]:
                    visit(dep, stack | {key})
                visited.add(key)
            for key in graph:
                visit(key, set())
            state["steps"] = cleaned
        if "projectId" in payload:
            project_path(str(payload["projectId"]))
            state["projectId"] = str(payload["projectId"])
        if "review" in payload:
            if actor != "researcher":
                raise ValueError("只有研究者可以记录人工审阅。")
            if not state["goal"]:
                raise ValueError("请先明确目标。")
            state["reviews"]["goal"] = digest(state["goal"]) if payload["review"] else ""
    return mutate(filename, revision, actor, "update", apply)


def set_runtime(filename: str, **values) -> dict:
    with LOCK:
        current = get(filename)
        return mutate(filename, current["revision"], "host", "runtime", lambda state: state.update(values))


def recover_runs() -> None:
    """A server restart does not silently restart paid model work."""
    with _connect() as db:
        rows = db.execute("SELECT filename,state FROM research_documents").fetchall()
    for row in rows:
        timeline_interrupt(row["filename"])
        if json.loads(row["state"]).get("runStatus") == "running":
            try:
                set_runtime(row["filename"], runStatus="paused", runReason="服务已重启；已保存的工作可继续。")
            except ValueError:
                pass


def message(filename: str, role: str, content: str, *, record_event=True) -> None:
    if record_event:
        timeline(filename)
    with _connect() as db:
        db.execute("INSERT INTO research_messages(filename,role,content,created_at) VALUES(?,?,?,?)",
                   (filename, role, content, workspace._now()))

    if record_event:
        timeline_write(filename, uuid.uuid4().hex, role, content, "completed")


def messages(filename: str) -> list[dict]:
    workspace.get_proof(filename)
    with _connect() as db:
        return [dict(row) for row in db.execute("SELECT * FROM (SELECT * FROM research_messages WHERE filename=? ORDER BY id DESC LIMIT 200) ORDER BY id", (filename,))]


def timeline(filename: str, limit: int = 1000) -> list[dict]:
    workspace.get_proof(filename)
    with _connect() as db:
        # Backfill only older messages; new messages use their own event rows.
        if not db.execute("SELECT 1 FROM research_events WHERE filename=? LIMIT 1", (filename,)).fetchone():
            for old in db.execute("SELECT * FROM research_messages WHERE filename=? ORDER BY id", (filename,)).fetchall():
                db.execute("INSERT OR IGNORE INTO research_events(filename,event_key,kind,content,status,tool,created_at) VALUES(?,?,?,?,?,?,?)",
                    (filename, 'legacy-'+str(old['id']), old['role'], old['content'], 'completed', '', old['created_at']))
        return [dict(row) for row in db.execute("SELECT * FROM (SELECT * FROM research_events WHERE filename=? ORDER BY id DESC LIMIT ?) ORDER BY id", (filename, limit))]


def timeline_write(filename: str, key: str, kind: str, content: str = '', status: str = 'running', tool: str = '') -> dict:
    with _connect() as db:
        db.execute("INSERT INTO research_events(filename,event_key,kind,content,status,tool,created_at) VALUES(?,?,?,?,?,?,?) "
                   "ON CONFLICT(filename,event_key) DO UPDATE SET content=excluded.content,status=excluded.status,tool=excluded.tool",
                   (filename, key, kind, content, status, tool, workspace._now()))
        return dict(db.execute("SELECT * FROM research_events WHERE filename=? AND event_key=?", (filename,key)).fetchone())


def timeline_interrupt(filename: str) -> list[dict]:
    """Finalize unfinished items without claiming their tools succeeded."""
    with _connect() as db:
        rows = db.execute("SELECT * FROM research_events WHERE filename=? AND status='running'", (filename,)).fetchall()
        db.execute("UPDATE research_events SET status='interrupted' WHERE filename=? AND status='running'", (filename,))
    return [dict(row, status='interrupted') for row in rows]


def history(filename: str) -> list[dict]:
    workspace.get_proof(filename)
    with _connect() as db:
        return [dict(row) for row in db.execute("SELECT revision,actor,action,created_at FROM research_revisions WHERE filename=? ORDER BY id DESC LIMIT 100", (filename,))]


def export(filename: str) -> dict:
    proof = workspace.get_proof(filename)
    with _connect() as db:
        versions = [dict(row) for row in db.execute("SELECT * FROM research_revisions WHERE filename=? ORDER BY id", (filename,))]
        sources = [dict(row) for row in db.execute("SELECT * FROM proof_history WHERE filename=? ORDER BY id", (filename,))]
        prose = [dict(row) for row in db.execute("SELECT * FROM natural_proof_history WHERE filename=? ORDER BY id", (filename,))]
    for version in versions:
        version["state"] = json.loads(version["state"])
    return {"format": "proveit-research-v1", "exportedAt": workspace._now(), "proof": proof,
            "research": get(filename), "timeline": timeline(filename, -1), "messages": messages(filename), "sourceHistory": sources,
            "researchHistory": versions, "naturalProofHistory": prose, "notes": workspace.get_notes(filename)}


def restore(filename: str, revision: int, expected: int) -> dict:
    with _connect() as db:
        row = db.execute("SELECT state FROM research_revisions WHERE filename=? AND revision=?", (filename, revision)).fetchone()
    if row is None:
        raise ValueError("找不到指定研究版本。")
    old = json.loads(row[0])
    # Restoring a plan does not restore its old run or claim old checks are current.
    return update(filename, {"revision": expected, "goal": old["goal"], "steps": old["steps"], "review": False})


def check(filename: str, source: str, project_id: str) -> dict:
    """Check a snapshot, then attach evidence only to that snapshot, even after edits."""
    state = get(filename)
    goal = state["goal"]
    env = environment(project_id)
    audit_name = "proveit_audit_" + digest([source, goal])[:20]
    candidate = source
    if goal:
        candidate += (f"\n\nset_option autoImplicit false in\n"
                      f"theorem {audit_name} : ({goal['formalType']}) := @{goal['targetName']}\n"
                      f"#print axioms {audit_name}\n")
    result = verify(candidate, project_id)
    output = result.get("stdout", "")
    match = re.search(re.escape(audit_name) + r"'? depends on axioms:\s*\[([^\]]*)\]", output, re.S)
    no_axioms = bool(re.search(re.escape(audit_name) + r"'? does not depend on any axioms", output))
    axioms = [v.strip() for v in match.group(1).split(",") if v.strip()] if match else []
    audited = bool(match or no_axioms)
    target_verified = bool(goal and result.get("verified") and audited and set(axioms) <= ALLOWED_AXIOMS)
    result.update(targetVerified=target_verified, axioms=axioms, projectId=project_id)
    if result.get("verified") and not target_verified:
        result.update(status="formalization_checked", verified=False,
                      error="源码编译通过，但尚无已核验的完整目标。请设置目标并核对公理依赖。")
    evidence = {"sourceHash": digest(source), "goalHash": digest(goal), "projectId": project_id,
                "environment": env, "targetVerified": target_verified, "result": result,
                "createdAt": workspace._now()}
    with LOCK:
        latest = get(filename)
        def attach(value):
            value["checks"] = (value["checks"] + [evidence])[-30:]
        mutate(filename, latest["revision"], "lean", "verification", attach)
        workspace.record_verification(filename, source, result)
    result["current"] = get(filename)["verificationCurrent"]
    return result
