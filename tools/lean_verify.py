#!/usr/bin/env python3
"""Run a Lean proof candidate and emit a compact JSON verification result."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, help="Existing Lean file to check")
    parser.add_argument("--code", help="Lean source string to check")
    parser.add_argument("--lean", help="Path/name of the Lean 4 executable")
    parser.add_argument("--project", type=Path, help="Lake project directory; runs `lake env lean`")
    parser.add_argument("--lake", help="Path/name of the Lake executable (default: lake)")
    parser.add_argument("--timeout", type=float, default=30.0, help="Timeout in seconds (default: 30)")
    parser.add_argument("--json", action="store_true", help="Emit JSON (default behavior)")
    args = parser.parse_args()
    if bool(args.file) == bool(args.code):
        parser.error("provide exactly one of --file or --code")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    return args


def find_lean(explicit: str | None) -> str | None:
    candidate = explicit or os.environ.get("LEAN_EXE") or "lean"
    found = shutil.which(candidate)
    if found:
        return found
    path = Path(candidate).expanduser()
    if path.is_file():
        return str(path.resolve())
    return None


def find_lake(explicit: str | None) -> str | None:
    candidate = explicit or os.environ.get("LAKE_EXE") or "lake"
    found = shutil.which(candidate)
    if found:
        return found
    path = Path(candidate).expanduser()
    if path.is_file():
        return str(path.resolve())
    return None


def diagnostics(output: str) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    pattern = re.compile(r"^(.*?):(\d+):(\d+):\s*(error|warning):\s*(.*)$")
    for line in output.splitlines():
        match = pattern.match(line)
        if match:
            parsed.append({
                "file": match.group(1),
                "line": int(match.group(2)),
                "column": int(match.group(3)),
                "severity": match.group(4),
                "message": match.group(5),
            })
        elif parsed and line.strip():
            parsed[-1]["message"] += "\n" + line
    return parsed


def kill_process_tree(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=False, timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def main() -> int:
    args = parse_args()
    project = args.project.expanduser().resolve() if args.project else None
    lake = find_lake(args.lake) if project else None
    lean = find_lean(args.lean) if not project else None
    if project and not project.is_dir():
        result = {"status": "input_error", "verified": False, "error": f"Project directory not found: {project}"}
        print(json.dumps(result, ensure_ascii=False))
        return 2
    if project and not (project / "lakefile.lean").is_file() and not (project / "lakefile.toml").is_file():
        result = {"status": "input_error", "verified": False, "error": f"No Lake config found in: {project}"}
        print(json.dumps(result, ensure_ascii=False))
        return 2
    if (project and lake is None) or (not project and lean is None):
        result = {
            "status": "unavailable",
            "verified": False,
            "error": "Lake executable not found. Put lake on PATH or pass --lake PATH." if project else "Lean 4 executable not found. Set LEAN_EXE or pass --lean PATH.",
            "hint": "Use --project to compile against a project's pinned Lean version and dependencies." if not project else None,
        }
        print(json.dumps(result, ensure_ascii=False))
        return 2

    source_file: Path | None = args.file
    temporary = None
    try:
        if source_file is not None:
            source_file = source_file.expanduser().resolve()
            if not source_file.is_file():
                result = {"status": "input_error", "verified": False, "error": f"File not found: {source_file}"}
                print(json.dumps(result, ensure_ascii=False))
                return 2
        else:
            temporary = tempfile.TemporaryDirectory(prefix="proveit-lean-", dir=str(project) if project else None)
            source_file = Path(temporary.name) / "Candidate.lean"
            source_file.write_text(args.code, encoding="utf-8")

        try:
            command = [lake, "env", "lean", str(source_file)] if project else [lean, str(source_file)]
            process_options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
            proc = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=project,
                **process_options,
            )
            try:
                stdout, stderr = proc.communicate(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                kill_process_tree(proc)
                stdout, stderr = proc.communicate()
                result = {
                    "status": "timeout", "verified": False, "exit_code": None,
                    "stdout": stdout[-20_000:], "stderr": stderr[-20_000:],
                    "diagnostics": diagnostics(stdout + "\n" + stderr),
                    "error": f"Lean verification exceeded {args.timeout:g} seconds; the Lean/Lake process tree was stopped.",
                }
                print(json.dumps(result, ensure_ascii=False))
                return 1
        except OSError as exc:
            result = {"status": "unavailable", "verified": False, "error": str(exc), "diagnostics": []}
            print(json.dumps(result, ensure_ascii=False))
            return 2

        combined = "\n".join(part for part in (stdout, stderr) if part).strip()
        has_sorry = bool(re.search(r"declaration uses 'sorry'|sorryAx", combined))
        verified = proc.returncode == 0 and not has_sorry
        result = {
            "status": "verified" if verified else ("rejected" if proc.returncode != 0 or has_sorry else "unknown"),
            "verified": verified,
            "exit_code": proc.returncode,
            "source": str(source_file) if args.file else None,
            "contains_placeholder": has_sorry,
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
            "diagnostics": diagnostics(combined),
            "interpretation": "Lean checked the encoded proposition; it does not assess translation fidelity, novelty, or significance.",
        }
        print(json.dumps(result, ensure_ascii=False))
        return 0 if verified else 1
    finally:
        if temporary is not None:
            temporary.cleanup()


if __name__ == "__main__":
    sys.exit(main())
