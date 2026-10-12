# Security and privacy

English · [简体中文](SECURITY.zh-CN.md)

ProveIt is a trusted local workspace, not a sandbox for untrusted Lean, Lake or Codex code. Do not publicly expose its loopback backend.

The Electron renderer uses context isolation, sandboxing and disabled Node integration. External HTTP(S) links open in the system browser. ProveIt adds no telemetry. Codex receives submitted research context under the user's own account and provider configuration.

Redact research, prompts, local paths and credentials before sharing reports. Use private vulnerability reporting when available; otherwise request a private contact channel without posting sensitive details.
