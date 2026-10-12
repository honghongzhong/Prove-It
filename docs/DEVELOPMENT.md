# Development and releases

English · [简体中文](DEVELOPMENT.zh-CN.md)

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
python tools/check_docs.py
python tools/release_audit.py
```

The smoke test uses a temporary workspace and actual Lean. Stage intended public files before running the privacy audit. Do not publish local logs or smoke reports.

For an Electron launch check, set PROVEIT_DESKTOP_DATA_DIR to an empty temporary directory and PROVEIT_SMOKE_REPORT to a temporary JSON path, then run the packaged ProveIt.exe. It writes a health report and screenshot and exits. This is a test hook, not telemetry.

Publish only after tests, package launch and privacy review pass. Release attachments are Setup, ZIP and SHA256SUMS.txt. Preserve repository history; do not force-push.

References: [Electron security](https://www.electronjs.org/docs/latest/tutorial/security), [NSIS](https://www.electron.build/docs/nsis/), [Codex App Server](https://learn.chatgpt.com/docs/app-server).

Follow the [language policy](LANGUAGE_POLICY.md).

## Model provider regression checks

`python -m unittest discover -s tests -v` covers a local HTTP Chat Completions server calling the research tools and then the real installed Lean verifier, with Codex startup forbidden. Additional cases cover DPAPI round trips, key removal and settings redaction, endpoint validation, interrupted response discard, and project removal preserving research. No paid API credentials are required for these tests.

Desktop smoke mode (`PROVEIT_SMOKE_REPORT` and an isolated `PROVEIT_DESKTOP_DATA_DIR`) captures renderer onboarding, provider form visibility, password field type and horizontal overflow as well as a screenshot. Set `CODEX_EXE` to a nonexistent executable in the isolated profile's `toolchain.json` to exercise first-run guidance. The screenshot hook briefly displays the test window to allow Chromium to paint. `python tools/smoke_backend.py build/backend/proveit-backend/proveit-backend.exe --codex` checks the frozen backend and real Lean separately. Model catalog/account checks establish transport and login state; they do not establish inference entitlement.

## Managed environment tests

Environment regressions cover archive traversal/symlink rejection, resumed local HTTP downloads and checksum failures, cancellation, subprocess timeout cleanup, interrupted Git lock recovery limited to managed projects, Windows proxy propagation, local curl limits, model setup selection and separation from goal approval, and tool-schema upgrades for existing Codex sessions. `tools/test_environment_setup.py core` or `mathlib` runs a live setup against `PROVEIT_DATA_DIR`; `PROVEIT_ENV_IGNORE_SYSTEM=1` skips discovery of system installations for clean-download tests. These live tests download large public artifacts and should use an isolated data directory. Desktop smoke mode also accepts `PROVEIT_SMOKE_ENV=1` to exercise the actual environment manager and core setup through the renderer. `import Mathlib` can be slow; the setup smoke test uses `Mathlib.Data.Nat.Prime.Defs` and a checked prime theorem.
