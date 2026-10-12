# Development and releases

Source mode needs Python 3.11+, Lean 4 and an authenticated Codex CLI. Run `python app.py` and open http://127.0.0.1:8765.

## Windows desktop build

Use Node.js 22+ and Python 3.13 x64:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-build.txt
npm ci
npm start
npm run dist
```

Outputs are in dist/. Python and UI assets are bundled. Lean, Codex, Mathlib and user workspaces are not bundled. Installation is per-user; uninstall preserves research. Current releases are unsigned.

## Validation

```powershell
python -m unittest discover -s tests -v
node tests/test_export.mjs
python tools/smoke_backend.py build/backend/proveit-backend/proveit-backend.exe
python tools/release_audit.py
```

The smoke test uses a temporary workspace and actual Lean. Stage intended public files before running the privacy audit. Do not publish local logs or smoke reports.

For an Electron launch check, set PROVEIT_DESKTOP_DATA_DIR to an empty temporary directory and PROVEIT_SMOKE_REPORT to a temporary JSON path, then run the packaged ProveIt.exe. It writes a health report and screenshot and exits. This is a test hook, not telemetry.

Publish only after tests, package launch and privacy review pass. Release attachments are Setup, ZIP and SHA256SUMS.txt. Preserve repository history; do not force-push.

References: [Electron security](https://www.electronjs.org/docs/latest/tutorial/security), [NSIS](https://www.electron.build/docs/nsis/), [Codex App Server](https://learn.chatgpt.com/docs/app-server).
