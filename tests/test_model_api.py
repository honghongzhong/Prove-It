"""Provider regressions with a local HTTP endpoint, no paid service credentials."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from proveit import workspace, research, model_api
from proveit.codex_bridge import CodexBridge, find_codex
import test_research

class ApiTests(unittest.TestCase):
    setUp = test_research.ResearchTests.setUp
    tearDown = test_research.ResearchTests.tearDown

    def test_key_encrypted_and_excluded_from_settings(self):
        model_api.save_key("test-private-value")
        self.assertEqual(model_api.read_key(), "test-private-value")
        self.assertNotIn("test-private-value", model_api.key_path().read_text())
        workspace.save_settings({"apiKey": "should-not-store", "provider": "api", "apiModel": "custom"})
        self.assertNotIn("apiKey", workspace.get_settings())
        model_api.save_key(None)
        self.assertEqual(model_api.read_key(), "test-private-value")
        model_api.save_key("")
        self.assertEqual(model_api.read_key(), "")

    def test_endpoint_validation(self):
        for url in ("file:///tmp", "https://user:pass@example.com", "http://example.com/v1", "https://example.com?secret=a"):
            with self.assertRaises(ValueError): model_api.validate({"baseUrl": url, "apiModel": "test"})
        model_api.validate({"baseUrl": "http://127.0.0.1:8000/v1", "apiModel": "test"})

    def test_project_removal_retains_proofs_and_workflow(self):
        project = workspace.save_research_project("Arithmetic")
        workspace.move_conversation("Test.lean", project["id"])
        workspace.remove_research_project(project["id"])
        self.assertIsNone(workspace.get_proof("Test.lean")["project_id"])
        self.assertEqual(research.get("Test.lean")["goal"], self.goal)

    def test_api_tool_cycle_with_real_http_and_lean(self):
        owner = self
        requests = []
        class Endpoint(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append(payload)
                owner.assertEqual(self.path, "/v1/chat/completions")
                owner.assertEqual(self.headers["Authorization"], "Bearer fake-local-key")
                if len(requests) == 1:
                    reply = {"content": None, "tool_calls": [{"id": "read", "type": "function", "function": {"name": "proveit_get_research", "arguments": "{}"}}]}
                elif len(requests) == 2:
                    reply = {"content": "Checked the saved target.", "tool_calls": [{"id": "verify", "type": "function", "function": {"name": "proveit_verify_lean", "arguments": json.dumps({"code": owner.source})}}]}
                else:
                    proof = workspace.get_proof("Test.lean")
                    reply = {"content": "Saved explanation.", "tool_calls": [{"id": "prose", "type": "function", "function": {"name": "proveit_propose_natural_proof", "arguments": json.dumps({"content": "Let n be arbitrary. Reflexivity gives n = n, proving the universally quantified statement.", "sourceHash": research.artifact_hash(proof)})}}]}
                data = json.dumps({"choices": [{"message": reply}]}).encode()
                self.send_response(200); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
        server = ThreadingHTTPServer(("127.0.0.1", 0), Endpoint)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            model_api.save_key("fake-local-key")
            workspace.save_settings({"provider": "api", "baseUrl": f"http://127.0.0.1:{server.server_port}/v1", "apiModel": "local-model"})
            research.message("Test.lean", "user", "Prove reflexivity")
            bridge = CodexBridge(); bridge.current_proof_id = "Test.lean"
            with patch.object(bridge, "start", side_effect=AssertionError("Codex must not start")):
                bridge._run("Prove reflexivity", "standalone", "Test.lean", "en")
            self.assertEqual(len(requests), 3)
            self.assertEqual(requests[1]["messages"][-1]["role"], "tool")
            self.assertTrue(research.get("Test.lean")["targetVerified"])
            self.assertEqual(research.get("Test.lean")["runStatus"], "completed")
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_pause_discards_response_before_tool_write(self):
        bridge = CodexBridge(); bridge.current_proof_id = "Test.lean"
        def response(*args):
            bridge.cancel.set()
            return {"tool_calls": [{"function": {"name": "invalid"}}]}
        with patch.object(model_api, "complete", side_effect=response):
            bridge._run_api("test", "standalone", "Test.lean", "en")
        self.assertEqual(research.get("Test.lean")["runStatus"], "paused")
        self.assertEqual(workspace.get_proof("Test.lean")["source"], self.source)

    def test_explicit_missing_codex_path_is_not_ignored(self):
        workspace.save_settings({"codexPath": "missing-codex-executable"})
        self.assertIsNone(find_codex())

    def test_plain_model_claim_cannot_mark_target_verified(self):
        bridge = CodexBridge(); bridge.current_proof_id = "Test.lean"
        with patch.object(model_api, "complete", return_value={"content": "The theorem is verified."}):
            bridge._run_api("test", "standalone", "Test.lean", "en")
        self.assertFalse(research.get("Test.lean")["targetVerified"])
        self.assertEqual(research.get("Test.lean")["runStatus"], "paused")

    def test_unknown_tool_returns_error_without_writing(self):
        bridge = CodexBridge(); bridge.current_proof_id = "Test.lean"
        replies = [{"tool_calls": [{"id": "unknown", "type": "function", "function": {"name": "delete_everything", "arguments": "{}"}}]}, {"content": "Stopped."}]
        with patch.object(model_api, "complete", side_effect=replies):
            bridge._run_api("test", "standalone", "Test.lean", "en")
        self.assertEqual(workspace.get_proof("Test.lean")["source"], self.source)
        self.assertTrue(any(x["status"] == "failed" for x in research.timeline("Test.lean")))

    def test_missing_key_rejected_before_user_message_is_saved(self):
        workspace.save_settings({"provider": "api", "apiModel": "test"})
        with self.assertRaises(ValueError):
            CodexBridge().send_message("test", "context", "standalone", "Test.lean")
        self.assertEqual(research.messages("Test.lean"), [])
