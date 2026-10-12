"""Local proof documents, notes, history, and preferences."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from .lean import ROOT

DATA_ROOT = Path(os.environ.get("PROVEIT_DATA_DIR", str(ROOT))).resolve()
PROOFS = DATA_ROOT / "proofs"
STATE_DIR = DATA_ROOT / ".proveit"
DATABASE = STATE_DIR / "workspace.sqlite3"
MAX_SOURCE = 200_000
_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,95}\.lean$", re.IGNORECASE)


class Connection(sqlite3.Connection):
    """A transaction context also releases its OS handles on Windows."""
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE, timeout=10, factory=Connection)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS proofs (
            filename TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            proposition TEXT NOT NULL DEFAULT '',
            assumptions TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_opened TEXT,
            deleted_at TEXT,
            trashed_path TEXT,
            natural_proof TEXT NOT NULL DEFAULT '',
            verification_status TEXT NOT NULL DEFAULT 'not_run',
            verification_message TEXT NOT NULL DEFAULT '',
            verification_source_hash TEXT NOT NULL DEFAULT '',
            verification_at TEXT,
            research_activity TEXT NOT NULL DEFAULT '[]',
            research_summary TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS proof_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            source TEXT NOT NULL,
            created_at TEXT NOT NULL,
            reason TEXT NOT NULL DEFAULT '保存'
        );
        CREATE INDEX IF NOT EXISTS proof_history_file ON proof_history(filename, id DESC);
        CREATE TABLE IF NOT EXISTS proof_notes (
            filename TEXT PRIMARY KEY,
            content TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS natural_proof_history (
            id INTEGER PRIMARY KEY, filename TEXT NOT NULL, content TEXT NOT NULL,
            created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS research_projects (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL);
    """)
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(proofs)")}
    for name, declaration in (
        ("project_id", "TEXT"),
        ("natural_proof", "TEXT NOT NULL DEFAULT ''"),
        ("verification_status", "TEXT NOT NULL DEFAULT 'not_run'"),
        ("verification_message", "TEXT NOT NULL DEFAULT ''"),
        ("verification_source_hash", "TEXT NOT NULL DEFAULT ''"),
        ("verification_at", "TEXT"),
        ("research_activity", "TEXT NOT NULL DEFAULT '[]'"),
        ("research_summary", "TEXT NOT NULL DEFAULT ''"),
    ):
        if name not in columns:
            connection.execute(f"ALTER TABLE proofs ADD COLUMN {name} {declaration}")
    return connection


def _filename(value: str) -> str:
    name = Path(str(value)).name
    if name != value or not _FILENAME.fullmatch(name) or name.startswith("."):
        raise ValueError("文件名需为普通 .lean 文件名，且不能包含目录。")
    return name


def _proof_path(filename: str) -> Path:
    path = (PROOFS / _filename(filename)).resolve()
    if path.parent != PROOFS.resolve():
        raise ValueError("证明文件必须位于当前工作区的 proofs 目录中。")
    return path


def _seed(connection: sqlite3.Connection) -> None:
    PROOFS.mkdir(parents=True, exist_ok=True)
    examples = {
        "AddAssoc": {
            "title": "加法结合律",
            "description": "对任意自然数 a、b、c，先计算 a + b 再加 c，与先计算 b + c 再加 a，结果相同。",
            "proposition": "(a + b) + c = a + (b + c)",
            "assumptions": "a b c : ℕ",
        },
        "Candidate": {
            "title": "加法交换律",
            "description": "对任意自然数 a、b，交换两个加数的顺序，总和不变。",
            "proposition": "a + b = b + a",
            "assumptions": "a b : ℕ",
        },
    }
    for path in PROOFS.glob("*.lean"):
        filename = path.name
        example = examples.get(path.stem, {})
        connection.execute(
            "INSERT OR IGNORE INTO proofs(filename,title,description,proposition,assumptions,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
            (filename, example.get("title", path.stem), example.get("description", ""), example.get("proposition", ""), example.get("assumptions", ""), _now(), _now()),
        )


def _record(row: sqlite3.Row, *, include_source: bool = False) -> dict:
    item = dict(row)
    item["id"] = item.pop("filename")
    if include_source:
        source = _proof_path(item["id"]).read_text(encoding="utf-8")
        item["source"] = source
        item["source_hash"] = hashlib.sha256(source.encode("utf-8")).hexdigest()
        item["verification_current"] = item.get("verification_source_hash") == hashlib.sha256(source.encode("utf-8")).hexdigest() and item.get("verification_status") != "not_run"
    return item


def list_proofs() -> list[dict]:
    with _connect() as connection:
        _seed(connection)
        rows = connection.execute(
            "SELECT * FROM proofs WHERE deleted_at IS NULL ORDER BY last_opened IS NULL, last_opened DESC, filename COLLATE NOCASE"
        ).fetchall()
        return [_record(row) for row in rows]


def get_proof(filename: str) -> dict:
    name = _filename(filename)
    with _connect() as connection:
        _seed(connection)
        row = connection.execute("SELECT * FROM proofs WHERE filename=? AND deleted_at IS NULL", (name,)).fetchone()
        path = _proof_path(name)
        if row is None or not path.is_file():
            raise ValueError("找不到这个证明文件。")
        connection.execute("UPDATE proofs SET last_opened=? WHERE filename=?", (_now(), name))
        row = connection.execute("SELECT * FROM proofs WHERE filename=?", (name,)).fetchone()
        return _record(row, include_source=True)


def create_proof(filename: str, *, title: str, description: str = "", proposition: str = "", assumptions: str = "", source: str = "", project_id: str | None = None) -> dict:
    name = _filename(filename)
    _validate_text(source, "Lean 代码", MAX_SOURCE)
    _validate_text(title, "标题", 200, required=True)
    with _connect() as connection:
        _seed(connection)
        if project_id and not connection.execute("SELECT 1 FROM research_projects WHERE id=?", (project_id,)).fetchone():
            raise ValueError("Project not found.")
        if connection.execute("SELECT 1 FROM proofs WHERE filename=?", (name,)).fetchone():
            raise ValueError("同名证明文件已存在。")
        path = _proof_path(name)
        if path.exists():
            raise ValueError("同名证明文件已存在。")
        path.write_text(source, encoding="utf-8")
        timestamp = _now()
        connection.execute(
            "INSERT INTO proofs(filename,title,description,proposition,assumptions,created_at,updated_at,last_opened) VALUES(?,?,?,?,?,?,?,?)",
            (name, title.strip(), description.strip(), proposition.strip(), assumptions.strip(), timestamp, timestamp, timestamp),
        )
        if project_id:
            connection.execute("UPDATE proofs SET project_id=? WHERE filename=?", (project_id, name))
        return _record(connection.execute("SELECT * FROM proofs WHERE filename=?", (name,)).fetchone(), include_source=True)


def _validate_text(value: str, label: str, maximum: int, *, required: bool = False) -> None:
    if required and not value.strip():
        raise ValueError(f"{label}不能为空。")
    if len(value) > maximum:
        raise ValueError(f"{label}过长（上限 {maximum} 个字符）。")


def save_proof(filename: str, payload: dict) -> dict:
    name = _filename(filename)
    source = str(payload.get("source", ""))
    title = str(payload.get("title", ""))
    description = str(payload.get("description", ""))
    proposition = str(payload.get("proposition", ""))
    assumptions = str(payload.get("assumptions", ""))
    _validate_text(source, "Lean 代码", MAX_SOURCE)
    _validate_text(title, "标题", 200, required=True)
    _validate_text(description, "说明", 20_000)
    _validate_text(proposition, "命题", 20_000)
    _validate_text(assumptions, "假设", 20_000)
    with _connect() as connection:
        row = connection.execute("SELECT * FROM proofs WHERE filename=? AND deleted_at IS NULL", (name,)).fetchone()
        path = _proof_path(name)
        if row is None or not path.is_file():
            raise ValueError("找不到这个证明文件。")
        previous = path.read_text(encoding="utf-8")
        if payload.get("expectedSourceHash") and payload["expectedSourceHash"] != hashlib.sha256(previous.encode("utf-8")).hexdigest():
            raise ValueError("源码已被其他操作修改；请重新打开文件后合并修改。")
        if previous != source:
            connection.execute("INSERT INTO proof_history(filename,source,created_at,reason) VALUES(?,?,?,?)", (name, previous, _now(), "保存前版本"))
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        temporary.write_text(source, encoding="utf-8")
        os.replace(temporary, path)
        connection.execute(
            "UPDATE proofs SET title=?,description=?,proposition=?,assumptions=?,updated_at=? WHERE filename=?",
            (title.strip(), description.strip(), proposition.strip(), assumptions.strip(), _now(), name),
        )
        return _record(connection.execute("SELECT * FROM proofs WHERE filename=?", (name,)).fetchone(), include_source=True)


def rename_proof(filename: str, new_filename: str) -> dict:
    name = _filename(filename)
    target = _filename(new_filename)
    with _connect() as connection:
        row = connection.execute("SELECT * FROM proofs WHERE filename=? AND deleted_at IS NULL", (name,)).fetchone()
        if row is None:
            raise ValueError("找不到这个证明文件。")
        if name.casefold() == target.casefold() and name != target:
            raise ValueError("请勿只更改文件名大小写；请使用不同的名称。")
        if name != target and (connection.execute("SELECT 1 FROM proofs WHERE filename=?", (target,)).fetchone() or _proof_path(target).exists()):
            raise ValueError("目标文件名已存在。")
        old_path, new_path = _proof_path(name), _proof_path(target)
        old_path.replace(new_path)
        connection.execute("UPDATE proofs SET filename=?, updated_at=? WHERE filename=?", (target, _now(), name))
        connection.execute("UPDATE proof_history SET filename=? WHERE filename=?", (target, name))
        connection.execute("UPDATE proof_notes SET filename=? WHERE filename=?", (target, name))
        tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table in ("research_documents", "research_revisions", "research_messages", "research_events", "natural_proof_history"):
            if table in tables:
                connection.execute(f"UPDATE {table} SET filename=? WHERE filename=?", (target, name))
        return _record(connection.execute("SELECT * FROM proofs WHERE filename=?", (target,)).fetchone(), include_source=True)


def delete_proof(filename: str) -> dict:
    name = _filename(filename)
    trash_dir = STATE_DIR / "trash"
    trash_dir.mkdir(parents=True, exist_ok=True)
    with _connect() as connection:
        row = connection.execute("SELECT * FROM proofs WHERE filename=? AND deleted_at IS NULL", (name,)).fetchone()
        path = _proof_path(name)
        if row is None or not path.is_file():
            raise ValueError("找不到这个证明文件。")
        trash_path = trash_dir / f"{uuid.uuid4().hex}--{name}"
        path.replace(trash_path)
        connection.execute("UPDATE proofs SET deleted_at=?, trashed_path=? WHERE filename=?", (_now(), str(trash_path), name))
        return {"id": name, "deletedAt": _now(), "recoverable": True}


def list_trash() -> list[dict]:
    with _connect() as connection:
        return [dict(row) for row in connection.execute("SELECT filename AS id,title,deleted_at AS deletedAt FROM proofs WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC")]


def restore_proof(filename: str) -> dict:
    name = _filename(filename)
    with _connect() as connection:
        row = connection.execute("SELECT * FROM proofs WHERE filename=? AND deleted_at IS NOT NULL", (name,)).fetchone()
        if row is None or not row["trashed_path"] or not Path(row["trashed_path"]).is_file():
            raise ValueError("回收站中找不到这个文件。")
        target = _proof_path(name)
        if target.exists():
            raise ValueError("工作区已有同名文件，请先重命名或移走现有文件。")
        Path(row["trashed_path"]).replace(target)
        connection.execute("UPDATE proofs SET deleted_at=NULL, trashed_path=NULL, updated_at=? WHERE filename=?", (_now(), name))
        return _record(connection.execute("SELECT * FROM proofs WHERE filename=?", (name,)).fetchone(), include_source=True)


def get_history(filename: str) -> list[dict]:
    name = _filename(filename)
    with _connect() as connection:
        return [dict(row) for row in connection.execute("SELECT id,created_at AS createdAt,reason FROM proof_history WHERE filename=? ORDER BY id DESC LIMIT 100", (name,))]


def restore_history(filename: str, history_id: int) -> dict:
    name = _filename(filename)
    with _connect() as connection:
        row = connection.execute("SELECT source FROM proof_history WHERE id=? AND filename=?", (history_id, name)).fetchone()
        if row is None:
            raise ValueError("找不到该历史版本。")
        proof = connection.execute("SELECT * FROM proofs WHERE filename=? AND deleted_at IS NULL", (name,)).fetchone()
        if proof is None:
            raise ValueError("找不到这个证明文件。")
        payload = dict(proof)
        payload["source"] = row["source"]
    return save_proof(name, payload)


def get_notes(filename: str) -> dict:
    name = _filename(filename)
    with _connect() as connection:
        row = connection.execute("SELECT content,updated_at AS updatedAt FROM proof_notes WHERE filename=?", (name,)).fetchone()
        return dict(row) if row else {"content": "", "updatedAt": None}


def save_natural_proof(filename: str, content: str, *, formalization: str = "", assumptions: str = "", expected_content: str | None = None) -> dict:
    name = _filename(filename)
    _validate_text(content, "自然语言证明思路", 100_000)
    _validate_text(formalization, "Lean 形式化命题", 20_000)
    _validate_text(assumptions, "形式化约定与假设", 20_000)
    with _connect() as connection:
        row = connection.execute("SELECT natural_proof FROM proofs WHERE filename=? AND deleted_at IS NULL", (name,)).fetchone()
        if row is None:
            raise ValueError("找不到这个证明文件。")
        if expected_content is not None and row[0] != expected_content:
            raise ValueError("自然语言证明已更新，请重新读取后合并修改。")
        if row[0] != content:
            connection.execute("INSERT INTO natural_proof_history(filename,content,created_at) VALUES(?,?,?)", (name, row[0], _now()))
        if formalization:
            connection.execute(
                "UPDATE proofs SET natural_proof=?, proposition=?, assumptions=?, updated_at=? WHERE filename=? AND deleted_at IS NULL",
                (content, formalization, assumptions, _now(), name),
            )
        else:
            connection.execute("UPDATE proofs SET natural_proof=?, updated_at=? WHERE filename=? AND deleted_at IS NULL", (content, _now(), name))
        if connection.total_changes == 0:
            raise ValueError("找不到这个证明文件。")
    return {"naturalProof": content, "formalization": formalization or None, "assumptions": assumptions or None}


def save_research_state(filename: str, events: list, summary: str) -> dict:
    name = _filename(filename)
    if not isinstance(events, list) or len(events) > 100:
        raise ValueError("研究活动记录格式无效或超过 100 条。")
    safe_events = []
    for event in events:
        if not isinstance(event, dict):
            continue
        safe_events.append({
            "title": str(event.get("title", ""))[:500],
            "detail": str(event.get("detail", ""))[:4_000],
            "kind": event.get("kind") if event.get("kind") in {"working", "success", "error", "idle"} else "working",
            "createdAt": str(event.get("createdAt", ""))[:80],
        })
    _validate_text(summary, "研究摘要", 4_000)
    with _connect() as connection:
        cursor = connection.execute("UPDATE proofs SET research_activity=?,research_summary=? WHERE filename=? AND deleted_at IS NULL", (json.dumps(safe_events, ensure_ascii=False), summary, name))
        if cursor.rowcount == 0:
            raise ValueError("找不到这个证明文件。")
    return {"events": safe_events, "summary": summary}


def record_verification(filename: str, source: str, result: dict) -> dict:
    name = _filename(filename)
    status = str(result.get("status", "unknown"))
    if status not in {"verified", "formalization_checked", "rejected", "unavailable", "timeout", "input_error", "unknown"}:
        status = "unknown"
    diagnostics = result.get("diagnostics")
    first_diagnostic = diagnostics[0] if isinstance(diagnostics, list) and diagnostics and isinstance(diagnostics[0], dict) else {}
    message = str(result.get("error") or first_diagnostic.get("message", "") or result.get("stdout", "") or result.get("stderr", ""))[:20_000]
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    timestamp = _now()
    with _connect() as connection:
        cursor = connection.execute("UPDATE proofs SET verification_status=?,verification_message=?,verification_source_hash=?,verification_at=? WHERE filename=? AND deleted_at IS NULL", (status, message, source_hash, timestamp, name))
        if cursor.rowcount == 0:
            raise ValueError("找不到这个证明文件。")
    return {"status": status, "message": message, "sourceHash": source_hash, "verifiedAt": timestamp}


def save_notes(filename: str, content: str) -> dict:
    name = _filename(filename)
    _validate_text(content, "研究备注", 50_000)
    with _connect() as connection:
        if not connection.execute("SELECT 1 FROM proofs WHERE filename=? AND deleted_at IS NULL", (name,)).fetchone():
            raise ValueError("找不到这个证明文件。")
        timestamp = _now()
        connection.execute("INSERT INTO proof_notes(filename,content,updated_at) VALUES(?,?,?) ON CONFLICT(filename) DO UPDATE SET content=excluded.content, updated_at=excluded.updated_at", (name, content, timestamp))
        return {"content": content, "updatedAt": timestamp}


def get_settings() -> dict:
    defaults = {"autoSave": True, "autoVerify": False, "theme": "light", "language": "en", "provider": "codex", "baseUrl": "https://api.openai.com/v1", "apiModel": "", "codexPath": "", "autoSetupLean": True, "environmentProxy": ""}
    with _connect() as connection:
        for row in connection.execute("SELECT key,value FROM settings"):
            try:
                defaults[row["key"]] = json.loads(row["value"])
            except (ValueError, TypeError):
                continue
    return defaults


def save_settings(payload: dict) -> dict:
    current = get_settings()
    for key in ("autoSave", "autoVerify", "autoSetupLean"):
        if key in payload:
            current[key] = bool(payload[key])
    if payload.get("theme") in {"light", "dark"}:
        current["theme"] = payload["theme"]
    if payload.get("language") in {"zh", "en"}:
        current["language"] = payload["language"]
    if payload.get("provider") in {"codex", "api"}:
        current["provider"] = payload["provider"]
    for key in ("baseUrl", "apiModel", "codexPath", "environmentProxy"):
        if key in payload:
            current[key] = str(payload[key]).strip()[:2048]
    for key in ("model", "effort"):
        if key in payload:
            current[key] = str(payload[key])[:100]
    with _connect() as connection:
        for key, value in current.items():
            connection.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, json.dumps(value)))
    return current


def list_research_projects() -> list[dict]:
    """Folders for research conversations, distinct from Lean/Lake environments."""
    with _connect() as db:
        return [dict(row) for row in db.execute(
            "SELECT p.*, COUNT(d.filename) AS conversation_count FROM research_projects p "
            "LEFT JOIN proofs d ON d.project_id=p.id AND d.deleted_at IS NULL "
            "GROUP BY p.id ORDER BY p.created_at,p.id")]


def save_research_project(name: str, project_id: str | None = None) -> dict:
    _validate_text(name, "Project name", 100, required=True)
    with _connect() as db:
        if project_id:
            cursor = db.execute("UPDATE research_projects SET name=? WHERE id=?", (name.strip(), project_id))
            if not cursor.rowcount:
                raise ValueError("Project not found.")
        else:
            project_id = uuid.uuid4().hex
            db.execute("INSERT INTO research_projects VALUES(?,?,?)", (project_id, name.strip(), _now()))
        return dict(db.execute("SELECT * FROM research_projects WHERE id=?", (project_id,)).fetchone())


def move_conversation(filename: str, project_id: str | None) -> dict:
    name = _filename(filename)
    with _connect() as db:
        if project_id and not db.execute("SELECT 1 FROM research_projects WHERE id=?", (project_id,)).fetchone():
            raise ValueError("Project not found.")
        cursor = db.execute("UPDATE proofs SET project_id=? WHERE filename=? AND deleted_at IS NULL", (project_id or None, name))
        if not cursor.rowcount:
            raise ValueError("Conversation not found.")
    return get_proof(name)


def rename_conversation(filename: str, title: str) -> dict:
    _validate_text(title, "Title", 200, required=True)
    name = _filename(filename)
    with _connect() as db:
        cursor = db.execute("UPDATE proofs SET title=?,updated_at=? WHERE filename=? AND deleted_at IS NULL", (title.strip(), _now(), name))
        if not cursor.rowcount:
            raise ValueError("Conversation not found.")
    return get_proof(name)


def remove_research_project(project_id: str) -> dict:
    """Remove a grouping while preserving all conversations, including trash."""
    with _connect() as db:
        if not db.execute("SELECT 1 FROM research_projects WHERE id=?", (project_id,)).fetchone():
            raise ValueError("Project not found.")
        db.execute("UPDATE proofs SET project_id=NULL WHERE project_id=?", (project_id,))
        db.execute("DELETE FROM research_projects WHERE id=?", (project_id,))
    return {"removed": project_id}
