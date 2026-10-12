"""Loopback HTTP/SSE routes for the Prove It browser workbench."""

from __future__ import annotations

import json
import queue
import sqlite3
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .codex_bridge import CodexBridge
from .lean import ROOT, list_projects, add_project, verify
from . import workspace, research

STATIC = ROOT / "ui"
codex = CodexBridge()


def proof_record(filename):
    proof = workspace.get_proof(filename)
    state = research.get(filename)
    proof["verification_current"] = state["verificationCurrent"]
    if proof["verification_status"] == "verified" and not state["targetVerified"]:
        proof["verification_status"] = "not_run"
    return proof


class Handler(BaseHTTPRequestHandler):
    server_version = "ProveIt/0.3"

    def parse_request(self):
        if not super().parse_request():
            return False
        host = self.headers.get("Host", "")
        allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        origin = self.headers.get("Origin")
        if host not in allowed or (origin and origin not in {f"http://{h}" for h in allowed}):
            # Drain small rejected requests so Windows does not reset the socket
            # before the browser receives the 403 response.
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if 0 < length <= 1_000_000:
                    self.connection.settimeout(2)
                    self.rfile.read(length)
            except (ValueError, OSError):
                pass
            self.send_error(403, "Local same-origin requests only")
            return False
        return True

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[Prove It] {self.address_string()} {fmt % args}")

    def _json(self, value: dict, status: int = 200) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length < 0 or length > 1_000_000:
            raise ValueError("请求内容过大。")
        body = json.loads(self.rfile.read(length) or b"{}")
        if not isinstance(body, dict):
            raise ValueError("请求内容必须为 JSON 对象。")
        return body

    def _api_call(self, key: str, operation) -> None:
        try:
            self._json({key: operation()})
        except (ValueError, RuntimeError, OSError, sqlite3.Error) as exc:
            self._json({"error": str(exc)}, 400)

    def do_GET(self) -> None:  # noqa: N802
        path = unquote(urlparse(self.path).path)
        if path == "/api/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            event_queue: queue.Queue[dict] = queue.Queue(maxsize=2048)
            with codex.subscribers_lock:
                codex.subscribers.add(event_queue)
            try:
                self.wfile.write(b": connected\n\n")
                self.wfile.flush()
                while True:
                    try:
                        event = event_queue.get(timeout=15)
                        payload = json.dumps(event, ensure_ascii=False).encode("utf-8")
                        self.wfile.write(b"data: " + payload + b"\n\n")
                    except queue.Empty:
                        self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                with codex.subscribers_lock:
                    codex.subscribers.discard(event_queue)
            return
        if path == "/api/codex/models":
            self._api_call("models", codex.models)
            return
        if path == "/api/lean/projects":
            self._json({"projects": list_projects()})
            return
        if path == "/api/health":
            import shutil
            import os
            self._json({"codexInstalled": bool(shutil.which(os.environ.get("CODEX_EXE", "codex"))),
                        "leanInstalled": bool(shutil.which(os.environ.get("LEAN_EXE", "lean"))),
                        "lakeInstalled": bool(shutil.which("lake")), "projects": list_projects()})
            return
        if path == "/api/proofs":
            self._api_call("proofs", workspace.list_proofs)
            return
        if path == "/api/projects":
            self._api_call("projects", workspace.list_research_projects)
            return
        if path == "/api/trash":
            self._api_call("proofs", workspace.list_trash)
            return
        if path == "/api/settings":
            self._api_call("settings", workspace.get_settings)
            return
        parts = path.strip("/").split("/")
        if len(parts) == 4 and parts[:2] == ["api", "proofs"]:
            operations = {"workflow": research.get, "messages": research.messages, "revisions": research.history, "timeline": research.timeline}
            if parts[3] in operations:
                self._api_call(parts[3], lambda: operations[parts[3]](parts[2]))
                return
            if parts[3] == "bundle":
                self._api_call("bundle", lambda: research.export(parts[2]))
                return
        if len(parts) == 3 and parts[:2] == ["api", "proofs"] and parts[2].endswith(".lean"):
            self._api_call("proof", lambda: proof_record(parts[2]))
            return
        if len(parts) == 4 and parts[:2] == ["api", "proofs"] and parts[3] == "history":
            self._api_call("history", lambda: workspace.get_history(parts[2]))
            return
        if len(parts) == 4 and parts[:2] == ["api", "proofs"] and parts[3] == "notes":
            self._api_call("notes", lambda: workspace.get_notes(parts[2]))
            return
        if path == "/api/codex/status":
            self._json(codex.status())
            return
        if path.startswith("/api/"):
            self._json({"error": "Not found"}, 404)
            return

        relative = "index.html" if path in {"/", "/index.html"} else path.lstrip("/")
        candidate = (STATIC / relative).resolve()
        if not candidate.is_file() or STATIC.resolve() not in candidate.parents:
            self.send_error(404)
            return
        content = candidate.read_bytes()
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
        }.get(candidate.suffix, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:  # noqa: N802
        try:
            body = self._body()
            path = unquote(urlparse(self.path).path)
            parts = path.strip("/").split("/")
            if len(parts) == 6 and parts[:2] == ["api", "proofs"] and parts[3] == "revisions" and parts[5] == "restore":
                with codex.artifact_lock:
                    self._json({"workflow": research.restore(parts[2], int(parts[4]), body.get("revision"))})
                return
            if path == "/api/codex/start":
                codex.start()
                self._json({"connected": True, "threadId": codex.thread_id})
                return
            if path == "/api/codex/pause":
                self._json(codex.pause())
                return
            if path == "/api/codex/message":
                message = str(body.get("message", "")).strip()
                context = str(body.get("context", ""))
                project_id = str(body.get("projectId", "mathlib"))
                proof_id = str(body.get("filename", ""))
                if not message:
                    raise ValueError("请先输入一条消息。")
                if not context.strip() or len(context) > 250_000:
                    raise ValueError("当前命题与 Lean 代码上下文为空或过长。")
                queued = codex.send_message(message, context, project_id, proof_id, "en" if body.get("language") == "en" else "zh", str(body.get("model", "")), str(body.get("effort", "")))
                self._json({"accepted": True, "queued": queued}, 202)
                return
            if path == "/api/lean/verify":
                source = str(body.get("source", ""))
                project_id = str(body.get("projectId", "mathlib"))
                if not source.strip() or len(source) > 200_000:
                    raise ValueError("Lean 代码为空或过长。")
                filename = str(body.get("filename", ""))
                if filename:
                    research.set_runtime(filename, projectId=project_id)
                    result = research.check(filename, source, project_id)
                else:
                    result = verify(source, project_id)
                self._json(result)
                return
            if path == "/api/lean/projects":
                project = add_project(str(body.get("name", "")), str(body.get("path", "")))
                self._json({"project": project}, 201)
                return
            if path == "/api/proofs":
                proof = workspace.create_proof(
                    str(body.get("filename", "")), title=str(body.get("title", "")),
                    description=str(body.get("description", "")), proposition=str(body.get("proposition", "")),
                    assumptions=str(body.get("assumptions", "")), source=str(body.get("source", "")),
                    project_id=body.get("projectId"),
                )
                self._json({"proof": proof}, 201)
                return
            if path == "/api/projects":
                self._json({"project": workspace.save_research_project(str(body.get("name", "")))}, 201)
                return
            if len(parts) == 4 and parts[:2] == ["api", "proofs"] and parts[3] == "rename":
                if codex.busy_turn and codex.current_proof_id == parts[2]:
                    raise ValueError("请先暂停当前研究，待轮次结束后重命名。")
                self._json({"proof": workspace.rename_proof(parts[2], str(body.get("filename", "")))})
                return
            if len(parts) == 4 and parts[:2] == ["api", "proofs"] and parts[3] == "verification":
                self._json({"error": "验证证据只能由服务器实际运行 Lean 后写入。"}, 403)
                return
            if len(parts) == 6 and parts[:2] == ["api", "proofs"] and parts[3] == "history" and parts[5] == "restore":
                self._json({"proof": workspace.restore_history(parts[2], int(parts[4]))})
                return
            if len(parts) == 4 and parts[:2] == ["api", "trash"] and parts[3] == "restore":
                self._json({"proof": workspace.restore_proof(parts[2])})
                return
            self._json({"error": "Not found"}, 404)
        except (
            ValueError,
            RuntimeError,
            OSError,
            subprocess.TimeoutExpired,
            json.JSONDecodeError,
            sqlite3.Error,
        ) as exc:
            self._json({"error": str(exc)}, 400)

    def do_PUT(self) -> None:  # noqa: N802
        try:
            body = self._body()
            path = unquote(urlparse(self.path).path)
            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[:2] == ["api", "projects"]:
                self._json({"project": workspace.save_research_project(str(body.get("name", "")), parts[2])})
                return
            if len(parts) == 4 and parts[:2] == ["api", "proofs"] and parts[3] == "project":
                self._json({"proof": workspace.move_conversation(parts[2], body.get("projectId"))})
                return
            if len(parts) == 4 and parts[:2] == ["api", "proofs"] and parts[3] == "title":
                self._json({"proof": workspace.rename_conversation(parts[2], str(body.get("title", "")))})
                return
            if len(parts) == 4 and parts[:2] == ["api", "proofs"] and parts[3] == "workflow":
                with codex.artifact_lock:
                    self._json({"workflow": research.update(parts[2], body)})
                codex.publish({"method": "research/updated", "params": {"proofId": parts[2]}})
                return
            if len(parts) == 3 and parts[:2] == ["api", "proofs"]:
                with codex.artifact_lock:
                    self._json({"proof": workspace.save_proof(parts[2], body)})
                return
            if len(parts) == 4 and parts[:2] == ["api", "proofs"] and parts[3] == "notes":
                self._json({"notes": workspace.save_notes(parts[2], str(body.get("content", "")))})
                return
            if len(parts) == 4 and parts[:2] == ["api", "proofs"] and parts[3] == "research":
                with codex.artifact_lock:
                    self._json(workspace.save_natural_proof(
                        parts[2], str(body.get("content", "")),
                        formalization=str(body.get("formalization", "")),
                        assumptions=str(body.get("assumptions", "")),
                        expected_content=body.get("expectedContent"),
                    ))
                return
            if len(parts) == 4 and parts[:2] == ["api", "proofs"] and parts[3] == "activity":
                self._json(workspace.save_research_state(parts[2], body.get("events", []), str(body.get("summary", ""))))
                return
            if path == "/api/settings":
                self._json({"settings": workspace.save_settings(body)})
                return
            self._json({"error": "Not found"}, 404)
        except (ValueError, OSError, sqlite3.Error, json.JSONDecodeError) as exc:
            self._json({"error": str(exc)}, 400)

    def do_DELETE(self) -> None:  # noqa: N802
        try:
            path = unquote(urlparse(self.path).path)
            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[:2] == ["api", "proofs"]:
                if codex.busy_turn and codex.current_proof_id == parts[2]:
                    raise ValueError("请先暂停当前研究，待轮次结束后移至回收站。")
                self._json(workspace.delete_proof(parts[2]))
                return
            self._json({"error": "Not found"}, 404)
        except (ValueError, RuntimeError, OSError, sqlite3.Error) as exc:
            self._json({"error": str(exc)}, 400)


class ProveItHTTPServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address) -> None:
        import sys

        error = sys.exc_info()[1]
        if isinstance(error, (BrokenPipeError, ConnectionAbortedError, ConnectionResetError)):
            return
        super().handle_error(request, client_address)


def serve(port: int = 8765, *, desktop: bool = False) -> None:
    server = ProveItHTTPServer(("127.0.0.1", port), Handler)
    research.recover_runs()
    if desktop:
        import sys
        import threading
        def parent_closed():
            sys.stdin.buffer.read()
            server.shutdown()
        threading.Thread(target=parent_closed, daemon=True).start()
        print(json.dumps({"ready": True, "port": server.server_port}), flush=True)
    else:
        print(f"Prove It is ready at http://127.0.0.1:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        codex.pause()
        codex.close()
        server.server_close()
