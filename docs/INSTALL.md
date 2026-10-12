# Installation

English · [简体中文](INSTALL.zh-CN.md)

## Windows x64

1. Download Setup from the [release page](https://github.com/honghongzhong/Prove-It/releases/latest), or extract the complete ZIP and run ProveIt.exe. Neither administrator access nor a separate Python installation is required.
2. Launch ProveIt. In Settings, choose either your own OpenAI-compatible API (key, Base URL and model) or Codex. API mode does not require Codex.
3. Open **Lean environments** in the sidebar. Choose **Lean core** or **Mathlib** and click **Set up / Check**. Matching installations are reused; missing components are downloaded without administrator access or changes to system defaults. Automatic setup is enabled by default for research tools and proof checks.
4. Wait for the environment's real Lean check to finish, then create a research conversation. The environment manager shows progress, logs, cancellation and retry; Settings includes an optional download proxy. The first download needs network access and several GB of disk space.

For the Codex option, install [Codex CLI](https://github.com/openai/codex). If using npm, install Node.js and run:

```powershell
npm install -g @openai/codex
codex login
```

Click **Save and test connection** in Settings. ProveIt creates its own working session; a separate Codex project is not required. Account/model access and API charges remain provider-dependent.

New installations default to **English**. Select Chinese in Settings. Previously saved language preferences are preserved. The installer language chooser also starts in English and offers Chinese.

Releases are unsigned; Windows may show an unknown publisher. Compare the downloaded file with SHA256SUMS.txt from the release:

```powershell
Get-FileHash .\ProveIt-0.7.0-windows-x64-setup.exe -Algorithm SHA256
```

## Tools outside PATH

Press Alt to reveal the desktop menu and choose **ProveIt → Open data folder**. Create `toolchain.json` in that directory, set only the overrides you need, then restart:

```json
{
  "LEAN_EXE": "C:/Tools/elan/bin/lean.exe",
  "LAKE_EXE": "C:/Tools/elan/bin/lake.exe",
  "CODEX_EXE": "C:/Tools/codex/codex.exe"
}
```

These are example paths. Replace them with real executable locations; never put credentials in this file. ProveIt searches PATH, the user's `.elan/bin`, `.cargo/bin` and npm program directory. Programs installed only inside WSL are not native Windows executables; this package needs native Windows tools.

## Mathlib

Mathlib is downloaded on demand by the environment manager, together with matching Lean, package dependencies and compiled caches. The presets pin Lean/Mathlib to v4.34.1. A representative Mathlib theorem is compiled to check the environment; this is separate from checking a research target. You can still add an existing Lake project using **Add Lean environment** and select it on the Lean tab. Existing projects are preserved. For details see the [Mathlib documentation](https://github.com/leanprover-community/mathlib4).

## Troubleshooting

- **Model discovery fails:** check `codex --version` and `codex login status`, confirm account access, then restart or retry.
- **Lean unavailable:** use Lean environments → Lean core → Set up / Check. Invalid manual toolchain.json overrides should be corrected or removed. A source checkout is not an installed compiler.
- **Mathlib import fails:** set up Mathlib in the environment manager and select its returned project. Use specific Mathlib modules where possible; importing the entire library may take much longer. Failed/interrupted setup can be retried, reusing downloads.
- **Active writer conflict:** ProveIt preserves local research and recovers through a new working session when an explicit ownership conflict occurs. It does not terminate another client. Authentication and network failures remain separate errors.
- **Startup fails:** check toolchain.json syntax and close another instance using the same workspace. Do not delete workspace.sqlite3 as a repair attempt.
- **Upgrade:** quit before running the new installer. Research stays in the user directory; back up important work first. Updates are manual.

Only Windows x64 desktop packages are currently published.
