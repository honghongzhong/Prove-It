"""Lean project discovery and verification helpers."""

from __future__ import annotations

import json
import hashlib
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = Path(os.environ.get("PROVEIT_DATA_DIR", str(ROOT))) / ".proveit" / "lean-projects.json"


def _project_record(project_id: str, name: str, path: Path) -> dict:
    toolchain_file = path / "lean-toolchain"
    toolchain = toolchain_file.read_text(encoding="utf-8").strip() if toolchain_file.is_file() else "Lean 4"
    packages_dir = path / ".lake" / "packages"
    packages = sorted(item.name for item in packages_dir.iterdir() if item.is_dir()) if packages_dir.is_dir() else []
    return {
        "id": project_id,
        "name": name,
        "path": str(path),
        "toolchain": toolchain,
        "packages": packages,
        "packageCount": len(packages),
    }


def list_projects() -> list[dict]:
    """Return configured Lake projects, including the bundled Mathlib project."""
    projects: dict[str, dict] = {
        "standalone": {
            "id": "standalone",
            "name": "Lean 核心环境",
            "path": "",
            "toolchain": os.environ.get("LEAN_EXE", "PATH 中的 Lean"),
            "packages": [],
            "packageCount": 0,
        }
    }
    defaults = ROOT / "mathlib"
    if (defaults / "lakefile.toml").is_file() or (defaults / "lakefile.lean").is_file():
        projects["mathlib"] = _project_record("mathlib", "Mathlib", defaults.resolve())

    if REGISTRY.is_file():
        try:
            for item in json.loads(REGISTRY.read_text(encoding="utf-8")):
                path = Path(item["path"]).expanduser().resolve()
                if (path / "lakefile.toml").is_file() or (path / "lakefile.lean").is_file():
                    projects[item["id"]] = _project_record(item["id"], item["name"], path)
        except (OSError, ValueError, KeyError, TypeError):
            pass
    return list(projects.values())


def add_project(name: str, path_text: str) -> dict:
    path = Path(path_text).expanduser().resolve()
    if not name.strip():
        raise ValueError("请输入项目名称。")
    if not path.is_dir() or not ((path / "lakefile.toml").is_file() or (path / "lakefile.lean").is_file()):
        raise ValueError("目录中没有 lakefile.toml 或 lakefile.lean。")

    items = []
    if REGISTRY.is_file():
        try:
            items = json.loads(REGISTRY.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            items = []
    digest = hashlib.sha256(str(path).casefold().encode("utf-8")).hexdigest()[:12]
    project_id = f"project-{digest}"
    record = {"id": project_id, "name": name.strip(), "path": str(path)}
    items = [item for item in items if item.get("path", "").casefold() != str(path).casefold()]
    items.append(record)
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return _project_record(project_id, name.strip(), path)


def project_path(project_id: str) -> Path | None:
    for project in list_projects():
        if project["id"] == project_id and project["path"]:
            return Path(project["path"])
    if project_id == "standalone":
        return None
    raise ValueError("所选 Lean 项目不存在或 Lake 配置已失效。")


def verify(source: str, project_id: str = "standalone") -> dict:
    # A file avoids the Windows command-line size limit for real Mathlib proofs.
    with tempfile.TemporaryDirectory(prefix="proveit-source-") as directory:
        candidate = Path(directory) / "Candidate.lean"
        candidate.write_text(source, encoding="utf-8")
        return _verify_file(candidate, project_id)


def _verify_file(candidate: Path, project_id: str) -> dict:
    command = ([sys.executable, "--verify"] if getattr(sys, "frozen", False) else
               [os.environ.get("PYTHON_EXE", sys.executable), str(ROOT / "tools" / "lean_verify.py")])
    command.extend(["--file", str(candidate)])
    timeout = float(os.environ.get("PROVEIT_LEAN_TIMEOUT", "120"))
    if timeout <= 0:
        raise ValueError("PROVEIT_LEAN_TIMEOUT 必须大于 0。")
    command.extend(["--timeout", str(timeout)])
    from .environments import runtime_env
    environment = runtime_env(project_id)
    if environment.get("LEAN_EXE"):
        command.extend(["--lean", environment["LEAN_EXE"]])
    if environment.get("LAKE_EXE"):
        command.extend(["--lake", environment["LAKE_EXE"]])
    project = project_path(project_id)
    if project is not None:
        command.extend(["--project", str(project)])
    options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        env={**environment, "PYINSTALLER_RESET_ENVIRONMENT": "1"} if getattr(sys, "frozen", False) else environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        **options,
    )
    try:
        stdout, _ = process.communicate(timeout=timeout + 15)
    except subprocess.TimeoutExpired:
        _kill_process_tree(process)
        stdout, stderr = process.communicate()
        return {
            "status": "timeout", "verified": False, "exit_code": None,
            "stdout": stdout[-20_000:], "stderr": stderr[-20_000:], "diagnostics": [],
            "error": f"Lean verification exceeded {timeout:g} seconds; the verifier process tree was stopped.",
        }
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Lean verifier returned invalid JSON (exit {process.returncode}): {stdout[-2000:]}") from exc


def _kill_process_tree(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
            timeout=10, creationflags=flags,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
