# User guide

English · [简体中文](USAGE.zh-CN.md)

## First research session

1. Create a project, such as “Basic algebra”, and a new research conversation.
2. Ask: “Formalize and prove that every natural number n satisfies n + 0 = n, using core Lean.” Choose an available model and reasoning effort, then send.
3. On Research, review the proposed quantifiers, assumptions and natural/formal statements. Approving their meaning is not a claim that the proof is complete.
4. On Lean, inspect saved code and actual verification evidence. The checked target must be the complete proposition, not an auxiliary lemma.
5. Ask for an explanation of `rfl` or suggest a different direction. Tool events appear alongside the relevant responses.

You can also register this test manually:

- Target name: `ProveIt.nat_add_zero`
- Complete type: `∀ n : Nat, n + 0 = n`

```lean
namespace ProveIt
theorem nat_add_zero : ∀ n : Nat, n + 0 = n := by
  intro n
  rfl
end ProveIt
```

Save it and run the check on the Lean tab. Only an actual successful local result counts as verification.

## Working with the AI

A new direction interrupts the current turn and queues the next one. Pause stops automatic continuation; an active Lean check may finish or time out first. Each request allows up to eight automatic turns by default and stops for missing information or lack of progress. The AI can propose and revise goals, steps and proofs, but cannot approve human review.

Version checks prevent stale model writes from silently overwriting newly saved edits. English is the default for new workspaces; select Chinese in Settings. Existing preferences and historical research text remain unchanged. The interface language influences new AI responses, not automatic translation of history.

## Export and recovery

The research menu exports Markdown, JSON and Lean. Markdown contains the goal, argument, code, verification summary and conversation/tool record. JSON retains additional revision history. Restoring a historical version creates a new revision.

Trash restores deleted research. Importing exported JSON as a complete workspace is not currently supported. For a full backup, quit the application and copy the entire workspace directory, including proofs and .proveit. Quit before restoring it as well.

Default desktop storage: `%APPDATA%/ProveIt/workspace`. Source mode defaults to the project root; override it with PROVEIT_DATA_DIR.

To migrate from source mode, quit both services and copy proofs/ and .proveit/workspace.sqlite3, plus any existing SQLite -wal/-shm companions, to matching locations inside the desktop workspace. Back up an existing destination first; do not overwrite unrelated research. Register external Lake paths again on another machine.

Uninstall preserves user data. The ZIP edition also stores research in the user directory, not beside its EXE. Review exported records for private content before sharing them.

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| PROVEIT_DATA_DIR | Source-mode workspace | Project directory |
| PROVEIT_DESKTOP_DATA_DIR | Desktop user-data override | Electron userData |
| PROVEIT_PORT | Source-mode port | 8765 |
| LEAN_EXE / LAKE_EXE / CODEX_EXE | Executable overrides | PATH |
| PROVEIT_MAX_TURNS | Automatic turn limit | 8 |
| PROVEIT_TURN_TIMEOUT | Seconds per Codex turn | 1800 |
| PROVEIT_LEAN_TIMEOUT | Seconds per Lean check | 120 |

The desktop application allocates a loopback port and owns its backend process. Do not manually start the backend inside the installation. Use `python app.py` for source mode.

## Environment setup during research

The sidebar's Lean environments manager provides core and Mathlib presets. The model can call `proveit_get_environments` and `proveit_setup_environment`; missing common environments can also be prepared automatically before verification. Code importing Mathlib in the core environment selects the managed Mathlib project after setup. Install success checks a representative example and never marks the research target verified. That target still needs its own saved-source, complete-type and axiom checks. Prefer specific Mathlib imports to loading the whole library.

You may pause research while setup runs. Shared setup may continue for other work; cancel it separately in the environment manager. Retry reuses downloads and managed caches. Disable automatic setup in Settings to require a deliberate install from the manager.
