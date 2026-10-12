"""OpenAI-compatible chat transport; credentials never enter workspace settings."""
from __future__ import annotations
import base64
import ctypes
import json
import os
import urllib.request
import urllib.error
from urllib.parse import urlsplit
from . import workspace

class Blob(ctypes.Structure):
    _fields_ = [("size", ctypes.c_ulong), ("data", ctypes.POINTER(ctypes.c_ubyte))]

def _protect(value: bytes, decrypt=False) -> bytes:
    buffer = ctypes.create_string_buffer(value)
    source = Blob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = Blob()
    fn = ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
    if not fn(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise OSError("Windows credential protection failed.")
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        ctypes.windll.kernel32.LocalFree(output.data)

def key_path():
    return workspace.STATE_DIR / "api-credential"

def read_key():
    path = key_path()
    if not path.exists():
        return ""
    value = path.read_bytes()
    return (_protect(base64.b64decode(value[6:]), True) if value.startswith(b"dpapi:") else value).decode()

def save_key(value):
    workspace.STATE_DIR.mkdir(parents=True, exist_ok=True)
    if value is None:
        return
    if not isinstance(value, str) or len(value) > 8192 or any(c in value for c in "\r\n"):
        raise ValueError("Invalid API key.")
    if not value.strip():
        key_path().unlink(missing_ok=True)
        return
    data = value.strip().encode()
    if os.name == "nt":
        data = b"dpapi:" + base64.b64encode(_protect(data))
    temporary = key_path().with_suffix(".tmp")
    temporary.write_bytes(data)
    temporary.chmod(0o600)
    os.replace(temporary, key_path())

def validate(config):
    url = urlsplit(config.get("baseUrl", ""))
    if url.scheme not in {"https", "http"} or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError("Enter a valid Base URL without credentials, query or fragment.")
    if url.scheme == "http" and url.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Remote API endpoints require HTTPS.")
    if not config.get("apiModel", "").strip():
        raise ValueError("Model name is required.")

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def complete(config, messages, tool_schemas=None):
    validate(config)
    key = read_key()
    if not key:
        raise ValueError("Configure an API key in Settings.")
    payload = {"model": config["apiModel"], "messages": messages, "stream": False}
    if tool_schemas:
        payload["tools"] = [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["inputSchema"]}} for t in tool_schemas]
    request = urllib.request.Request(config["baseUrl"].rstrip("/") + "/chat/completions", json.dumps(payload).encode(), {"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=60) as response:
            data = response.read(2_000_001)
        if len(data) > 2_000_000:
            raise RuntimeError("API response exceeded the size limit.")
        result = json.loads(data)
        return result["choices"][0]["message"]
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"API HTTP {exc.code}. Check credentials, endpoint and model access.") from None
    except (urllib.error.URLError, TimeoutError):
        raise RuntimeError("API connection failed or timed out. Check Base URL and network.") from None
    except (ValueError, KeyError, IndexError, TypeError):
        raise RuntimeError("Invalid chat completion response from API.") from None
