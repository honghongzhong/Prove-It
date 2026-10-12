# ProveIt

**An AI-assisted mathematical research workspace connecting Codex and Lean 4.**

[Download](https://github.com/honghongzhong/Prove-It/releases/latest) · [Installation](docs/INSTALL.md) · [User guide](docs/USAGE.md) · [Build from source](docs/DEVELOPMENT.md) · [简体中文](README.zh-CN.md)

ProveIt brings Codex's reasoning and coding capabilities into a human-guided mathematical workflow. Researchers pose questions, clarify assumptions and choose directions. The AI maintains structured goals, proof steps, natural-language arguments and Lean code, then iterates on actual verification feedback.

![ProveIt desktop workspace](docs/assets/workspace.png)

## Download and run

For **Windows x64**, download `ProveIt-*-windows-x64-setup.exe` from [Releases](https://github.com/honghongzhong/Prove-It/releases). A ZIP distribution is also available: extract the entire archive and run `ProveIt.exe`. Do not move the executable out of its accompanying files.

The desktop package includes Electron and the Python backend. **You do not need to install Python.** Install these tools separately:

- **Lean 4 / Elan**, available to native Windows processes.
- **Codex CLI**, authenticated with your own account.
- Optionally, a prepared **Mathlib / Lake project** for library-dependent research.

See the [installation guide](docs/INSTALL.md) for setup, custom executable paths and troubleshooting. This release provides Windows x64 packages; macOS and Linux desktop installers are not included.

The release is **unsigned**, so Windows may display an unknown-publisher prompt. Obtain files from this repository's release page and compare their hashes with `SHA256SUMS.txt`. Do not disable operating-system security protections. ProveIt is not an official OpenAI or Lean product.

## Workspace

- **Project sidebar:** create, rename, search and organize research conversations; restore deleted research from Trash.
- **Conversation:** choose a model and reasoning effort, follow streamed responses and interleaved tool calls, give new directions, pause or continue.
- **Research:** manage the natural-language goal, assumptions, complete formal target, proof outline and written argument. Human review is recorded separately.
- **Lean:** edit source, select the verification environment and inspect real diagnostics and evidence tied to the current artifacts.
- **Export:** save Lean source, a readable Markdown report or a JSON record containing revision history.
- **Appearance:** English by default for new installations, with Chinese available in Settings; light and dark themes, locally hosted fonts and KaTeX math rendering.

## Research workflow

1. Describe the mathematical question and any constraints or preferred methods.
2. Review the AI's proposed statement, quantifiers and assumptions before approving its interpretation.
3. Break the argument into steps and refine the natural-language proof alongside Lean code.
4. Run Lean, inspect actual diagnostics and iterate on saved candidates.
5. Give further direction whenever needed. The AI cannot approve human review on your behalf.
6. Export the work, including unresolved steps and the current verification status.

For a first check, ask ProveIt to prove that every natural number satisfies `n + 0 = n` using core Lean. The [user guide](docs/USAGE.md) also provides a complete manual test target and explains backup and recovery.

## Run from source

The Python backend uses only the standard library and requires Python 3.11+:

```powershell
git clone https://github.com/honghongzhong/Prove-It.git
cd Prove-It
lean --version
codex --version
codex login
python app.py
```

Open http://127.0.0.1:8765. For desktop development and installer builds, see [DEVELOPMENT.md](docs/DEVELOPMENT.md).

## What verification means

A target is marked verified only after Lean actually accepts the complete registered proposition and its axiom audit passes. Compiling a candidate, proving a helper lemma or checking finite examples does **not** establish the full research target.

The audit rejects `sorryAx` and additional axioms. The accepted standard foundational axioms are `propext`, `Classical.choice` and `Quot.sound`. Changing the source, target or selected environment invalidates older evidence.

**Lean checks the encoded proposition. It does not establish the fidelity of a natural-language translation, the suitability of assumptions, novelty or mathematical significance.** These remain human review tasks. ProveIt does not guarantee that AI can solve a proposed problem.

## Data and privacy

Desktop research is stored in `%APPDATA%/ProveIt/workspace`, separately from application files. Source mode stores it locally under `proofs/` and `.proveit/` by default. Quit the app before backing up the entire workspace; see the user guide for migration instructions.

The repository and installers contain no author's research, conversations, account credentials, databases, logs or local Lean/Mathlib workspaces. Git ignore rules, explicit packaging resource lists and release checks restrict what is published.

Codex receives the research and context you submit under your own account, provider and configuration. ProveIt adds no telemetry and does not collect login passwords. Lean metaprograms, Lake projects and Codex tools can execute local code: this is a **trusted local research environment**, not a sandbox for untrusted code. Do not publicly forward the backend port.

## Contributing and license

[Issues](https://github.com/honghongzhong/Prove-It/issues) and focused contributions are welcome. Remove private research, tokens and local paths from reports. See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and the [language policy](docs/LANGUAGE_POLICY.md).

Released under the repository's existing [MIT License](LICENSE). Third-party license information is retained in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and the distributed dependencies.

### Use your own API model

Open Settings → Model connection → Custom API. Enter an API key, an OpenAI-compatible Base URL (including `/v1` when required), and the exact model name. Save and test performs a small inference request and may incur provider charges. Codex is not required in this mode. The endpoint must support Chat Completions and function calling for research tools. Remote endpoints require HTTPS; HTTP is allowed for localhost.

Windows encrypts the key with user-scoped DPAPI in the local data directory; it is excluded from settings responses and research exports. A blank key field preserves the saved key; Remove saved key deletes it. API responses use bounded tool iterations; Pause prevents subsequent artifact writes after an in-flight request returns (network timeout: 60 seconds).

When no model connection is ready, startup opens the connection guide. ProveIt detects the Codex installation, checks account state, and creates its own working sessions. You may also specify a Codex executable path in Settings. Project grouping can be renamed or removed without deleting its research conversations.

### Automatic Lean environments

Open **Lean environments** in the sidebar to install or check Lean core or Mathlib. ProveIt reuses a matching, runnable installation first; otherwise it downloads an official Windows x64 Lean/Lake distribution into the application's data directory. Mathlib setup also fetches its pinned dependencies and compiled cache, and downloads portable Git when Git is missing. Lean and Mathlib are pinned together to v4.34.1. Downloaded Lean and Git archives are checked against fixed SHA-256 digests before extraction. A real Lean smoke check is required before an environment is reported ready.

The default **Automatically set up missing common Lean environments** setting lets research tools prepare environments. Code importing Mathlib in the core environment automatically selects the configured Mathlib project when checked. Both Codex and custom API models can inspect environments and call the fixed `core` or `mathlib` setup tools; they cannot choose arbitrary installer URLs, commands or paths. Disable the setting to require manual setup through the environment manager. User projects and global toolchain defaults are preserved.

Setup jobs show stage progress and logs, support cancellation and retry, and resume partial archive downloads when the server supports byte ranges. Interrupted jobs are marked interrupted after restart and can be retried. Pausing research stops that research from waiting or changing its artifacts; shared setup may continue, and can be cancelled separately in the environment manager. A download proxy can be set in Settings. Fresh Lean downloads are approximately 850 MB; reserve at least 4 GB for Lean and 8 GB for Mathlib (actual requirements depend on the cache). The application installer includes the downloader; environments are downloaded on demand and require network access on first setup.

See [Lean releases](https://github.com/leanprover/lean4/releases/tag/v4.34.1) and the [Mathlib project guide](https://leanprover-community.github.io/install/project.html) for upstream sources and cache behavior.

Research completion requires both the registered Lean target to be verified and a nonempty natural-language proof saved in the research document. If the model omits the prose, ProveIt requests up to three focused follow-up turns to save it. If unsuccessful, the session reports the missing document while retaining Lean evidence. Prose quality and fidelity still require human review.
