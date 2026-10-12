---
name: lean-research-assistant
description: Propose and refine mathematical proof ideas with a local Lean 4 verification tool. Use when a user asks to prove, formalize, explore, or check a mathematical claim in this workspace.
---

# Lean Research Assistant

English · [简体中文](SKILL.zh-CN.md)

Use the model for mathematical exploration and Lean for checking the exact formal proposition. Keep the human in control of the research direction and theorem statement.

## Workflow

1. Restate the user's goal and identify definitions, assumptions, domain, and quantifiers. Ask only if an ambiguity changes the theorem materially.
2. Give a short informal proof plan before writing Lean. If the user requests open-ended exploration, generate several clearly labeled conjectures and explain why each is plausible; do not label them as discoveries.
3. Write a complete Lean 4 declaration with no `sorry`, `admit`, or unverified placeholder. Prefer core Lean unless a project with Mathlib is explicitly configured; do not assume an import is available.
4. Call the verifier from the workspace root:

   ```powershell
   python tools/lean_verify.py --file proofs\Candidate.lean
   ```

   For Mathlib files, select the configured Lake project so Lean sees its pinned dependencies:

   ```powershell
   python tools/lean_verify.py --project mathlib --file mathlib\Main.lean
   ```

   Or submit source directly:

   ```powershell
   python tools/lean_verify.py --code 'theorem demo : True := trivial'
   ```

5. If Lean rejects the candidate, read the diagnostics and revise the proof. Retry at most three times for one candidate, then report the blocker and ask the human to steer or clarify.
6. Report the exact Lean source, verifier status, and any relevant diagnostics. Say “Lean verified” only when the tool returns `status: verified`.

## Required distinctions

- Lean checks that the proof term inhabits the proposition encoded in Lean, under the imported environment and axioms.
- Lean does not determine whether the encoding matches the user's informal intent. Show the formal statement and assumptions for human review.
- Kernel acceptance alone does not establish that a result is novel, useful, or important. Literature checks and mathematical evaluation are separate.
- A model-generated proof plan is a proposal until the verifier accepts a complete proof.
- If the verifier reports `unavailable`, do not infer success from the presence of Lean source code. Request/configure a built Lean 4 executable (`LEAN_EXE`) and retry.

## Response format

For each attempt, show:

1. **Idea** — concise mathematical strategy.
2. **Formal statement** — the exact Lean theorem and its assumptions.
3. **Lean check** — verified / rejected / unavailable, with a brief reason.
4. **Boundaries** — translation fidelity, novelty, or significance questions still requiring human judgment.
