"""Codex App Server transport and serialized, interruptible research sessions.

The model operates typed product tools. Research state and Lean evidence belong
in research.py; chat text is never interpreted as a database mutation.
"""
from __future__ import annotations

import json
import os
import queue
import shutil
import sqlite3
import subprocess
import threading
import time
from collections import deque
from pathlib import Path

from .lean import ROOT, verify, project_path
from . import research, workspace
from .research_tools import SYSTEM_PROMPT, tools


def find_codex():
    configured = workspace.get_settings().get("codexPath") or os.environ.get("CODEX_EXE")
    if configured:
        return shutil.which(configured) or (configured if Path(configured).is_file() else None)
    found = shutil.which("codex")
    if found:
        if Path(found).suffix.lower() in {".cmd", ".bat", ".ps1"}:
            package = Path(found).parent / "node_modules" / "@openai" / "codex"
            binaries = list(package.glob("**/codex.exe")) if package.is_dir() else []
            if binaries:
                return str(max(binaries, key=lambda p: p.stat().st_mtime))
        else:
            return found
    # Explorer does not inherit terminal profile PATH updates.
    root = Path(os.environ.get("LOCALAPPDATA", "")) / "OpenAI" / "Codex" / "bin"
    candidates = list(root.glob("*/codex.exe")) if root.is_dir() else []
    return str(max(candidates, key=lambda p: p.stat().st_mtime)) if candidates else None


class CodexBridge:
    def __init__(self):
        self.process = None
        self.thread_id = None
        self.active_turn_id = None
        self.current_proof_id = ""
        self.current_project_id = "standalone"
        self.subscribers = set()
        self.subscribers_lock = threading.Lock()
        self.state_lock = threading.RLock()
        self.start_lock = threading.Lock()
        self.lifecycle_lock = threading.RLock()
        self.write_lock = threading.Lock()
        self.artifact_lock = threading.RLock()
        self.pending = {}
        self.counter = 0
        self.busy_turn = False
        self.verifying = False
        self.retry_attempt = 0
        self.requests = queue.Queue()
        self.completed = queue.Queue()
        self.cancel = threading.Event()
        self.loaded_threads = set()
        self.turn_text = []
        self.stderr_tail = deque(maxlen=20)
        self.worker = None
        self.last_item = None
        self.stopping = False
        self.item_text = {}
        self.item_flush = {}
        self.models_cache = []
        self.recovered_session = False

    def start(self):
        with self.start_lock:
            if self.process and self.process.poll() is None:
                return
            executable = find_codex()
            if not executable:
                raise RuntimeError("未找到 Codex CLI。请安装并通过 codex login 登录。")
            self.loaded_threads.clear()
            workspace.DATA_ROOT.mkdir(parents=True, exist_ok=True)
            self.process = subprocess.Popen([executable, "app-server", "--listen", "stdio://"], cwd=workspace.DATA_ROOT,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace", bufsize=1,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            process = self.process
            threading.Thread(target=self._read_loop, args=(process,), daemon=True).start()
            threading.Thread(target=self._read_errors, args=(process,), daemon=True).start()
            try:
                self.call("initialize", {"clientInfo": {"name": "proveit", "title": "ProveIt", "version": "0.3.0"},
                                         "capabilities": {"experimentalApi": True}})
                self.notify("initialized", {})
            except Exception:
                process.terminate()
                raise

    def close(self):
        """Release only this bridge's child and its writer leases, never another client."""
        with self.lifecycle_lock, self.start_lock:
            process, self.process = self.process, None
            self.loaded_threads.clear()
            if process and process.poll() is None:
                process.stdin.close()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    process.wait(timeout=5)

    def models(self):
        with self.lifecycle_lock:
            self.start()
            items, cursor = [], None
            for _ in range(20):
                page = self.call("model/list", {"cursor": cursor, "includeHidden": False})
                items.extend(item for item in page.get("data", []) if not item.get("hidden"))
                cursor = page.get("nextCursor")
                if not cursor:
                    break
            self.models_cache = items
            return items

    def _record_timeline(self, method, params):
        proof_id = self.current_proof_id
        if not proof_id:
            return
        item = params.get("item", {})
        item_id = params.get("itemId") or item.get("id")
        if not item_id:
            return
        key = f"{self.thread_id}:{item_id}"
        content, kind, tool = '', '', ''
        status = 'completed' if method == 'item/completed' else 'running'
        if method == 'item/agentMessage/delta':
            content = self.item_text.get(key, '') + params.get('delta', '')
            self.item_text[key] = content
            kind = 'assistant'
            now = time.monotonic()
            if now-self.item_flush.get(key, 0) < 0.15:
                return
            self.item_flush[key] = now
        elif item.get('type') == 'agentMessage':
            kind, content = 'assistant', item.get('text') or self.item_text.get(key, '')
        elif item.get('type') in {'dynamicToolCall', 'mcpToolCall', 'commandExecution', 'webSearch', 'fileChange'}:
            kind, tool = 'tool', item.get('tool') or item.get('type')
            content = json.dumps({k:item[k] for k in ('arguments','command','result','error') if k in item}, ensure_ascii=False)[:16000]
            if item.get('success') is False or item.get('status') in {'failed','declined'}:
                status = 'failed'
        if kind:
            entry = research.timeline_write(proof_id, key, kind, content, status, tool)
            self.publish({'method':'research/timeline', 'params':{'entry':entry,'proofId':proof_id}})

    def _read_errors(self, process):
        for line in process.stderr:
            self.stderr_tail.append(line.strip())

    def _read_loop(self, process):
        for line in process.stdout:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if "method" not in event:
                with self.state_lock:
                    waiter = self.pending.get(str(event.get("id")))
                if waiter:
                    waiter.put(event)
                continue
            if "id" in event:
                if event["method"] == "item/tool/call":
                    threading.Thread(target=self._tool, args=(event,), daemon=True).start()
                elif event["method"] in {"item/commandExecution/requestApproval", "item/fileChange/requestApproval"}:
                    self._send({"id": event["id"], "result": {"decision": "decline"}})
                else:
                    self._send({"id": event["id"], "error": {"code": -32601, "message": "Use ProveIt product tools."}})
                continue
            method, params = event["method"], event.get("params", {})
            if params.get("threadId") and params["threadId"] != self.thread_id:
                continue
            if method in {'item/started','item/completed','item/agentMessage/delta'}:
                try:
                    self._record_timeline(method, params)
                except (OSError, sqlite3.Error) as exc:
                    self.stderr_tail.append(str(exc))
            if method == "turn/started":
                self.active_turn_id = params["turn"]["id"]
                if self.cancel.is_set():
                    threading.Thread(target=self._interrupt, daemon=True).start()
            elif method == "item/agentMessage/delta":
                item = params.get("itemId")
                if item != self.last_item and self.turn_text:
                    self.turn_text.append("\n\n")
                self.last_item = item
                self.turn_text.append(params.get("delta", ""))
            self.publish(event)
            if method == "turn/completed":
                self.completed.put(params["turn"])
        if process is self.process:
            with self.state_lock:
                for waiter in self.pending.values():
                    waiter.put({"error": {"message": "Codex 进程已退出。"}})
            self.completed.put({"status": "failed", "error": {"message": "Codex 进程已退出。"}})
            self.publish({"method": "bridge/closed", "params": {}})

    def _send(self, message):
        with self.write_lock:
            if not self.process or self.process.poll() is not None:
                raise RuntimeError("Codex 连接已关闭。")
            self.process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
            self.process.stdin.flush()

    def call(self, method, params, timeout=30):
        waiter = queue.Queue()
        with self.state_lock:
            self.counter += 1
            request_id = str(self.counter)
            self.pending[request_id] = waiter
        try:
            self._send({"id": request_id, "method": method, "params": params})
            reply = waiter.get(timeout=timeout)
        except queue.Empty as exc:
            raise RuntimeError(f"等待 Codex {method} 超时。") from exc
        finally:
            with self.state_lock:
                self.pending.pop(request_id, None)
        if "error" in reply:
            raise RuntimeError(reply["error"].get("message", "Codex 请求失败"))
        return reply.get("result", {})

    def notify(self, method, params):
        self._send({"method": method, "params": params})

    def publish(self, event):
        event.setdefault("params", {}).setdefault("proofId", self.current_proof_id)
        with self.subscribers_lock:
            for subscriber in tuple(self.subscribers):
                try:
                    subscriber.put_nowait(event)
                except queue.Full:
                    # A stalled tab must not consume unbounded host memory.
                    self.subscribers.discard(subscriber)

    def status(self):
        return {"connected": bool(self.process and self.process.poll() is None),
                "threadId": self.thread_id, "turnId": self.active_turn_id,
                "proofId": self.current_proof_id, "busy": self.busy_turn,
                "verifying": self.verifying, "attempt": self.retry_attempt,
                "queuedMessages": self.requests.qsize()}

    def _select_thread(self, proof_id):
        state = research.get(proof_id)
        stored = state["threadId"]
        schema_hash = research.digest(tools())
        self.recovered_session = False
        if stored and stored not in self.loaded_threads:
            try:
                self.call("thread/resume", {"threadId": stored, "cwd": str(workspace.DATA_ROOT),
                    "approvalPolicy": "on-request", "sandbox": "read-only"})
                # Dynamic tools belong to thread/start and cannot be changed by
                # thread/resume. Preserve local history when upgrading the tools.
                if state.get("toolSchemaHash") != schema_hash:
                    research.set_runtime(proof_id, previousThreadIds=[*state.get("previousThreadIds", []), stored][-30:])
                    stored = None
                    self.recovered_session = True
            except RuntimeError as exc:
                # Writer conflicts are not fixed by interrupting or deleting somebody else's thread.
                if not any(reason in str(exc).lower() for reason in ('active writer', 'no rollout found', 'thread not found')):
                    raise
                research.set_runtime(proof_id, previousThreadIds=[*state.get('previousThreadIds', []), stored][-30:])
                stored = None
                self.recovered_session = True
        if not stored:
            reply = self.call("thread/start", {"cwd": str(workspace.DATA_ROOT), "approvalPolicy": "on-request",
                "sandbox": "read-only", "dynamicTools": tools()})
            stored = reply["thread"]["id"]
            research.set_runtime(proof_id, threadId=stored, toolSchemaHash=schema_hash)
        self.loaded_threads.add(stored)
        self.thread_id = stored
        if self.recovered_session:
            entry = research.timeline_write(proof_id, 'session-'+stored, 'recovery', '', 'completed')
            self.publish({'method':'research/timeline','params':{'entry':entry,'proofId':proof_id}})

    def send_message(self, text, context, project_id, proof_id="", language="en", model="", effort=""):
        workspace.get_proof(proof_id)
        project_path(project_id)
        if workspace.get_settings().get("provider") == "api":
            from .model_api import validate, read_key
            validate(workspace.get_settings())
            if not read_key():
                raise ValueError("Configure an API key in Settings.")
        elif model:
            models = self.models_cache or self.models()
            selected = next((m for m in models if m.get('model') == model), None)
            if not selected:
                raise ValueError("Selected model is not in the Codex model catalog.")
            if effort and effort not in [r['reasoningEffort'] for r in selected.get('supportedReasoningEfforts', [])]:
                raise ValueError("Reasoning effort is not supported by this model.")
        with self.state_lock:
            research.timeline(proof_id)
            research.message(proof_id, "user", text)
            queued = self.busy_turn
            self.requests.put((text, project_id, proof_id, language, model, effort))
            if queued:
                self.cancel.set()
                threading.Thread(target=self._interrupt, daemon=True).start()
            if not self.worker or not self.worker.is_alive():
                self.busy_turn = True
                self.worker = threading.Thread(target=self._work, daemon=True)
                self.worker.start()
        return queued

    def pause(self):
        with self.state_lock:
            self.cancel.set()
            while not self.requests.empty():
                try:
                    self.requests.get_nowait()
                except queue.Empty:
                    break
        self._interrupt()
        return self.status()

    def _interrupt(self):
        turn = self.active_turn_id
        if turn:
            try:
                self.call("turn/interrupt", {"threadId": self.thread_id, "turnId": turn})
            except RuntimeError as exc:
                self.publish({"method": "bridge/error", "params": {"message": str(exc)}})

    def _work(self):
        while True:
            with self.state_lock:
                try:
                    text, project_id, proof_id, language, model, effort = self.requests.get_nowait()
                except queue.Empty:
                    self.busy_turn = False
                    self.worker = None
                    return
                self.cancel.clear()
                self.current_proof_id, self.current_project_id = proof_id, project_id
            try:
                self._run(text, project_id, proof_id, language, model, effort)
            except Exception as exc:
                try:
                    research.set_runtime(proof_id, runStatus="failed", runReason=str(exc))
                except (ValueError, OSError, sqlite3.Error):
                    pass
                self.publish({"method": "bridge/error", "params": {"message": str(exc)}})
            finally:
                self.active_turn_id = None
                try:
                    self.close()
                    for entry in research.timeline_interrupt(proof_id):
                        self.publish({'method':'research/timeline', 'params':{'entry':entry,'proofId':proof_id}})
                finally:
                    self.verifying = False
                    self.publish({"method": "research/idle", "params": {}})

    def _run(self, text, project_id, proof_id, language="en", model="", effort=""):
        if workspace.get_settings().get("provider") == "api":
            return self._run_api(text, project_id, proof_id, language)
        self.start()
        self._select_thread(proof_id)
        research.set_runtime(proof_id, projectId=project_id, runStatus="running", runReason="")
        maximum = max(1, min(int(os.environ.get("PROVEIT_MAX_TURNS", "8")), 100))
        previous = None
        prose_attempts = 0
        for attempt in range(1, maximum + 4):
            if self.cancel.is_set():
                break
            self.retry_attempt = attempt
            self.turn_text, self.last_item = [], None
            self.item_text, self.item_flush = {}, {}
            state = research.get(proof_id)
            state["checks"] = state["checks"][-1:]
            proof = workspace.get_proof(proof_id)
            finalizing = state["targetVerified"] and not proof["natural_proof"].strip()
            if attempt > maximum and not finalizing:
                break
            proof = {k: proof[k] for k in ("id", "title", "description", "source", "natural_proof")}
            prompt = SYSTEM_PROMPT + "\n研究者要求：" + text + "\n当前状态：" + json.dumps({
                "research": state, "proof": proof, "sourceHash": research.artifact_hash(proof)}, ensure_ascii=False)
            prompt += "\nWrite new researcher-facing responses and research prose in " + ("English." if language == "en" else "Chinese.")
            if finalizing:
                prompt += "\n" + self._prose_prompt(proof_id)
            if attempt > 1:
                prompt += "\n继续推进同一目标，读取上次真实诊断；不要重复没有新信息的尝试。"
            self.publish({"method": "codex/prompt", "params": {"prompt": prompt, "attempt": attempt}})
            if self.recovered_session:
                prompt += "\nRecovered conversation context (local record): " + json.dumps(research.messages(proof_id)[-40:], ensure_ascii=False)[-100000:]
            params = {"threadId": self.thread_id, "input": [{"type": "text", "text": prompt}]}
            if model:
                params["model"] = model
            if effort:
                params["effort"] = effort
            reply = self.call("turn/start", params)
            self.active_turn_id = reply["turn"]["id"]
            if self.cancel.is_set():
                self._interrupt()
            deadline = time.monotonic() + max(30, float(os.environ.get("PROVEIT_TURN_TIMEOUT", "1800")))
            while True:
                try:
                    turn = self.completed.get(timeout=1)
                    if turn.get("id") in {None, self.active_turn_id}:
                        break
                except queue.Empty:
                    if not self.process or self.process.poll() is not None:
                        raise RuntimeError("Codex 进程已退出。")
                    if time.monotonic() > deadline:
                        self.cancel.set()
                        self._interrupt()
                        raise RuntimeError("Codex 本轮超过时间预算，已请求中断；已保存的研究工作可继续。")
            self.active_turn_id = None
            content = "".join(self.turn_text)
            if content:
                research.message(proof_id, "assistant", content, record_event=False)
            if self.cancel.is_set() or turn["status"] == "interrupted":
                break
            if turn["status"] != "completed":
                raise RuntimeError(str(turn.get("error") or turn["status"]))
            state = research.get(proof_id)
            if state["targetVerified"]:
                if self._complete_research(proof_id, language):
                    return
                if finalizing:
                    prose_attempts += 1
                if prose_attempts >= 3:
                    self._prose_blocked(proof_id, language)
                    return
                continue
            if state["runStatus"] == "blocked":
                return
            proof = workspace.get_proof(proof_id)
            progress = research.digest([state["goal"], state["steps"], proof["source"], proof["natural_proof"]])
            if progress == previous:
                research.set_runtime(proof_id, runStatus="blocked", runReason="连续两轮没有产物变化，请补充研究方向后继续。")
                return
            previous = progress
            self.publish({"method": "proof/researchContinued", "params": {"attempt": attempt + 1, "reason": "继续推进登记目标"}})
        reason = "研究者已暂停。" if self.cancel.is_set() else f"本次已完成 {maximum} 轮；进展已保存，可继续研究。"
        research.set_runtime(proof_id, runStatus="paused", runReason=reason)

    def _prose_prompt(self, proof_id):
        proof = workspace.get_proof(proof_id)
        state = research.get(proof_id)
        return ("The registered target already passed Lean, but the saved natural-language proof is empty. "
                "Finish the research document now: call proveit_get_research for the current sourceHash, "
                "then use proveit_propose_natural_proof or proveit_modify_natural_proof to SAVE a complete "
                "reader-facing proof explaining the verified theorem, assumptions, mathematical steps and conclusion. "
                "A chat response alone does not save it. Preserve the verified Lean code and target; "
                "do not change human review. Current authoritative context: " + json.dumps({
                    "goal": state["goal"], "source": proof["source"],
                    "naturalProof": proof["natural_proof"], "sourceHash": research.artifact_hash(proof)}, ensure_ascii=False))

    def _complete_research(self, proof_id, language):
        with self.artifact_lock, research.LOCK:
            if self.cancel.is_set() or not research.get(proof_id)["targetVerified"]:
                return False
            if not workspace.get_proof(proof_id)["natural_proof"].strip():
                return False
            research.set_runtime(proof_id, runStatus="completed", runReason=(
                "形式目标已通过 Lean 验证，自然语言证明已保存；含义与意义仍需人工审阅。" if language == "zh" else
                "Lean verified the registered target and the natural-language proof is saved; human review remains separate."))
            return True

    def _prose_blocked(self, proof_id, language):
        research.set_runtime(proof_id, runStatus="blocked", runReason=(
            "Lean 已验证目标，但自然语言证明尚未保存；自动补写未成功，请继续研究以补齐证明正文。" if language == "zh" else
            "Lean verified the target, but the natural-language proof has not been saved. Automatic completion failed; continue research to finish the document."))
        self.publish({"method": "research/updated", "params": {}})

    def _tool(self, event):
        params = event.get("params", {})
        tool, args = params.get("tool", ""), params.get("arguments", {})
        if params.get("namespace") == "proveit":
            tool = "proveit_" + tool
        proof_id, project_id = self.current_proof_id, self.current_project_id
        try:
            if self.cancel.is_set() or params.get("turnId") != self.active_turn_id:
                raise ValueError("轮次已结束或被打断，请在新轮次读取最新状态。")
            if not isinstance(args, dict):
                raise ValueError("工具参数必须是对象。")
            if tool in {"proveit_verify_lean", "proveit_check_candidate", "proveit_get_environments", "proveit_setup_environment"}:
                result = self._execute(tool, args, proof_id, project_id)
            else:
                with self.artifact_lock:
                    if self.cancel.is_set() or proof_id != self.current_proof_id or params.get("turnId") != self.active_turn_id:
                        raise ValueError("轮次已变化，请重新读取研究状态。")
                    result = self._execute(tool, args, proof_id, project_id)
            success = True
        except (ValueError, RuntimeError, OSError, sqlite3.Error, KeyError, TypeError) as exc:
            result, success = {"error": str(exc)}, False
        try:
            self._send({"id": event["id"], "result": {"success": success,
                "contentItems": [{"type": "inputText", "text": json.dumps(result, ensure_ascii=False)}]}})
        except (RuntimeError, OSError):
            pass

    def _execute(self, tool, args, proof_id, project_id):
        from . import environments
        proof = workspace.get_proof(proof_id)
        project_id = research.get(proof_id)["projectId"]
        if tool == "proveit_get_environments":
            return environments.status()
        if tool == "proveit_setup_environment":
            if not workspace.get_settings().get("autoSetupLean", True):
                raise ValueError("Automatic environment setup is disabled in Settings.")
            result = environments.manager.wait(args.get("preset"), self.cancel)
            self.current_project_id = result.get("projectId", "standalone")
            if self.cancel.is_set():
                raise ValueError("Research was paused; the environment is available for a later run.")
            research.set_runtime(proof_id, projectId=self.current_project_id)
            self.publish({"method": "research/updated", "params": {}})
            return result
        if tool == "proveit_get_research":
            state = research.get(proof_id)
            state["checks"] = state["checks"][-1:]
            proof = {k: proof[k] for k in ("id", "title", "description", "source", "natural_proof")}
            return {"research": state, "proof": proof, "sourceHash": research.artifact_hash(proof)}
        if tool == "proveit_update_research":
            if set(args) - {"revision", "goal", "steps"}:
                raise ValueError("AI 只能修改提议目标和证明步骤。")
            result = research.update(proof_id, args, "codex")
        elif tool == "proveit_report_blocker":
            result = research.set_runtime(proof_id, runStatus="blocked", runReason=str(args["reason"])[:4000])
        elif tool in {"proveit_verify_lean", "proveit_check_candidate"}:
            source = args.get("code", "")
            if not isinstance(source, str) or not source.strip() or len(source) > 200000:
                raise ValueError("Lean 源码为空或过长。")
            if tool == "proveit_verify_lean" and source != proof["source"]:
                raise ValueError("Save the candidate before verifying it.")
            project_id = environments.prepare(source, project_id, self.cancel)
            if self.cancel.is_set():
                raise ValueError("Research paused before Lean verification.")
            self.current_project_id = project_id
            research.set_runtime(proof_id, projectId=project_id)
            if tool == "proveit_check_candidate":
                return {"candidateOnly": True, "result": verify(source, project_id)}
            if source != proof["source"]:
                raise ValueError("候选与已保存源码不同，请先保存后检查。")
            self.verifying = True
            self.publish({"method": "proof/checkStarted", "params": {"attempt": self.retry_attempt, "projectId": project_id}})
            try:
                result = research.check(proof_id, source, project_id)
            finally:
                self.verifying = False
            import hashlib
            self.publish({"method": "proof/checkResult", "params": {**result,
                "sourceHash": hashlib.sha256(source.encode()).hexdigest(), "willRetry": not result["targetVerified"]}})
        elif tool in {"proveit_create_lean_code", "proveit_modify_lean_code", "proveit_propose_natural_proof", "proveit_modify_natural_proof"}:
            if args.get("sourceHash") != research.artifact_hash(proof):
                raise ValueError("源码已改变，请重新读取，不能覆盖研究者的修改。")
            is_code = tool.endswith("lean_code")
            if is_code:
                result = workspace.save_proof(proof_id, {**proof, "source": args["code"]})
            else:
                if not isinstance(args["content"], str) or not args["content"].strip():
                    raise ValueError("Save a nonempty natural-language proof, not a blank placeholder.")
                result = workspace.save_natural_proof(proof_id, args["content"])
            self.publish({"method": "proof/artifactUpdated", "params": {
                "kind": "leanCode" if is_code else "naturalProof", "operation": "modify",
                "code": args.get("code"), "content": args.get("content"), "note": args.get("note", ""),
                "sourceHash": result.get("source_hash"), "updatedAt": result.get("updated_at")}})
        else:
            raise ValueError("未知 ProveIt 工具。")
        self.publish({"method": "research/updated", "params": {}})
        return result

    def _run_api(self, text, project_id, proof_id, language):
        from .model_api import complete
        import uuid
        config = workspace.get_settings()
        research.set_runtime(proof_id, projectId=project_id, runStatus="running", runReason="")
        self.publish({"method": "turn/started", "params": {}})
        messages = [{"role": "system", "content": SYSTEM_PROMPT + "\nRespond in " + ("Chinese." if language == "zh" else "English.")}]
        messages += [{"role": m["role"], "content": m["content"]} for m in research.messages(proof_id)[-30:] if m["role"] in {"user", "assistant"}]
        allowed = {t["name"] for t in tools()}
        prose_attempts = 0
        for attempt in range(1, 28):
            if self.cancel.is_set(): break
            state = research.get(proof_id)
            finalizing = state["targetVerified"] and not workspace.get_proof(proof_id)["natural_proof"].strip()
            if attempt > 24 and not finalizing:
                break
            if finalizing:
                messages.append({"role": "system", "content": self._prose_prompt(proof_id)})
            self.retry_attempt = attempt
            reply = complete(config, messages, tools())
            if self.cancel.is_set(): break
            calls = reply.get("tool_calls") or []
            if len(calls) > 16: raise RuntimeError("API returned too many tool calls.")
            content = reply.get("content") or ""
            if not isinstance(content, str): raise RuntimeError("Invalid API message content.")
            messages.append({"role": "assistant", "content": content, **({"tool_calls": calls} if calls else {})})
            if content:
                research.message(proof_id, "assistant", content)
                self.publish({"method": "research/updated", "params": {}})
            for call in calls:
                if self.cancel.is_set(): break
                name = call.get("function", {}).get("name", "")
                status = "completed"
                try:
                    args = json.loads(call["function"]["arguments"])
                    if name not in allowed or not isinstance(args, dict): raise ValueError("Unknown tool or invalid arguments.")
                    if name in {"proveit_verify_lean", "proveit_check_candidate", "proveit_get_environments", "proveit_setup_environment"}:
                        result = self._execute(name, args, proof_id, project_id)
                    else:
                        with self.artifact_lock:
                            if self.cancel.is_set(): break
                            result = self._execute(name, args, proof_id, project_id)
                except (ValueError, RuntimeError, OSError, KeyError, TypeError, sqlite3.Error) as exc:
                    result, status = {"error": str(exc)}, "failed"
                entry = research.timeline_write(proof_id, "api:" + uuid.uuid4().hex, "tool", json.dumps(result, ensure_ascii=False)[:16000], status, name)
                self.publish({"method": "research/timeline", "params": {"entry": entry}})
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result, ensure_ascii=False)})
            state = research.get(proof_id)
            if state["targetVerified"]:
                if self._complete_research(proof_id, language):
                    return
                if finalizing:
                    prose_attempts += 1
                if prose_attempts >= 3:
                    self._prose_blocked(proof_id, language)
                    return
                continue
            if state["runStatus"] == "blocked": return
            if not calls: break
        research.set_runtime(proof_id, runStatus="paused", runReason="Paused by researcher." if self.cancel.is_set() else "API turn finished or reached its tool budget. Continue with a new direction.")
