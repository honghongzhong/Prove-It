# ProveIt

ProveIt is a local AI-assisted mathematical research workspace connecting Codex and Lean 4. Researchers set goals and guide the argument; Codex edits structured research steps, prose and Lean source, then iterates on real verification feedback.

[Download Windows x64](https://github.com/honghongzhong/Prove-It/releases/latest) · [Setup](INSTALL.md) · [Build](DEVELOPMENT.md) · [中文](../README.md)

Install the Setup EXE or extract the entire ZIP. Python is bundled; native Lean/Elan and an authenticated Codex CLI are required separately. Mathlib is optional and uses your existing Lake project. The first release is unsigned. Verify the release checksums. macOS and Linux desktop packages are not provided.

The interface supports English/Chinese, light/dark themes, project folders, model and reasoning-effort selection, streamed tool events, rendered math, and Markdown/JSON/Lean export. The Research tab separates goals, assumptions, proof steps and written arguments from technical Lean details.

Only the complete registered target passing actual Lean checking and axiom audit counts as verified. Candidate compilation, helper lemmas and finite examples do not establish the target. Human review remains necessary for meaning, assumptions, fidelity, novelty and significance.

Research is stored under `%APPDATA%/ProveIt/workspace`. Quit before backing up this entire folder. Application upgrades do not overwrite it. No personal workspaces, conversations or credentials are included in the repository or installer. Codex receives the research you submit under your own account/provider settings. Lean and Codex can execute local code: this is a trusted local workspace, not a sandbox for untrusted code.

For source mode, use Python 3.11+ and run `python app.py`, then open http://127.0.0.1:8765. See the linked documentation for configuration and release builds.

MIT licensed; third-party licenses are retained. Not affiliated with OpenAI or the Lean project.
