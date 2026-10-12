"""Managed, pinned Lean environments with observable and resumable setup jobs.

Only audited presets can install software. Models cannot supply URLs, shell commands,
versions or destinations. All managed files live under the user's workspace state.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import tempfile
import threading
import time
import urllib.request
import uuid
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

from . import workspace

VERSION = "4.34.1"
LEAN_ASSET = {"name": f"lean-{VERSION}-windows.zip", "url": f"https://github.com/leanprover/lean4/releases/download/v{VERSION}/lean-{VERSION}-windows.zip", "sha256": "457698d4e2132243e899ff32178d7ae63c16431d09ed9ad524d859c3581992af", "size": 850624573}
GIT_ASSET = {"name": "MinGit-2.51.0-64-bit.zip", "url": "https://github.com/git-for-windows/git/releases/download/v2.51.0.windows.1/MinGit-2.51.0-64-bit.zip", "sha256": "c2c955a21fa99889d83f485f24fa5d9a38fffc2d509d4022385510e11c26b250", "size": 41268410}
PRESETS = {"core": {"name": "Lean core", "version": VERSION, "downloadBytes": LEAN_ASSET["size"], "description": "Lean, Lake and the standard library"}, "mathlib": {"name": "Mathlib", "version": VERSION, "downloadBytes": None, "description": "Mathlib, Batteries, Aesop, Qq and pinned dependencies; several GB of disk space may be required"}}

class SetupCancelled(RuntimeError):
    pass


def root() -> Path:
    return workspace.STATE_DIR / "environments"


def manifest() -> dict:
    try:
        return json.loads((root() / "installed.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def validate_proxy(value: str) -> str:
    if not value:
        return ""
    u = urlsplit(value)
    if u.scheme not in {"http", "https"} or not u.hostname or u.username or u.password or u.query or u.fragment:
        raise ValueError("Download proxy must be an HTTP(S) URL without credentials.")
    return value


def process_env() -> dict:
    env = dict(os.environ)
    proxy = validate_proxy(workspace.get_settings().get("environmentProxy", ""))
    if not proxy and os.name == "nt":
        # urllib sees Windows system proxies; curl and Git otherwise miss them.
        system = urllib.request.getproxies()
        candidate = system.get("https") or system.get("http") or ""
        try:
            proxy = validate_proxy(candidate)
        except ValueError:
            proxy = ""
    if proxy:
        env.update(HTTP_PROXY=proxy, HTTPS_PROXY=proxy, http_proxy=proxy, https_proxy=proxy)
    return env


def runtime_env(project_id: str = "standalone") -> dict:
    env = dict(os.environ)
    record = manifest().get("core", {})
    lean = record.get("lean", "")
    lake = record.get("lake", "")
    compatible = True
    if project_id != "standalone":
        from .lean import project_path
        path = project_path(project_id)
        toolchain = (path / "lean-toolchain").read_text(encoding="utf-8").strip() if path and (path / "lean-toolchain").is_file() else ""
        compatible = not toolchain or toolchain in {f"leanprover/lean4:v{VERSION}", f"v{VERSION}"}
    if compatible and lean and Path(lean).is_file() and not os.environ.get("LEAN_EXE") and not os.environ.get("LAKE_EXE"):
        env["LEAN_EXE"], env["LAKE_EXE"] = lean, lake
        path_key = next((k for k in env if k.lower() == "path"), "PATH")
        env[path_key] = str(Path(lean).parent) + os.pathsep + env.get(path_key, "")
    git = manifest().get("git", {}).get("git", "")
    if git and Path(git).is_file():
        path_key = next((k for k in env if k.lower() == "path"), "PATH")
        env[path_key] = str(Path(git).parent) + os.pathsep + env.get(path_key, "")
    return env


def executable(name: str, env: dict | None = None) -> str | None:
    env = env or runtime_env()
    candidate = env.get(name.upper() + "_EXE") or name
    return shutil.which(candidate, path=env.get("PATH", env.get("Path", ""))) or (candidate if Path(candidate).is_file() else None)


def _quick_version(command: str | None) -> str:
    if not command:
        return ""
    try:
        p = subprocess.run([command, "--version"], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=8, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return p.stdout.strip() if p.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def status() -> dict:
    env = runtime_env()
    lean, lake = executable("lean", env), executable("lake", env)
    lean_version, lake_version = _quick_version(lean), _quick_version(lake)
    installed = manifest()
    return {"leanReady": bool(lean_version and lake_version), "leanVersion": lean_version, "lakeVersion": lake_version, "lean": lean, "lake": lake, "installed": installed, "presets": [{"id": k, **v} for k, v in PRESETS.items()], "jobs": manager.jobs(), "automatic": workspace.get_settings().get("autoSetupLean", True)}


class EnvironmentManager:
    def __init__(self):
        self.lock = threading.RLock()
        self.install_lock = threading.Lock()
        self._jobs = {}
        self._cancel = {}
        self._threads = {}
        self._loaded_root = None
        self.publisher = None

    def _load(self):
        current = str(root().resolve())
        if self._loaded_root == current:
            return
        self._jobs, self._cancel, self._threads = {}, {}, {}
        self._loaded_root = current
        try:
            data = json.loads((root() / "jobs.json").read_text(encoding="utf-8"))
            for job in data[-20:]:
                if job["status"] in {"queued", "running"}:
                    job.update(status="interrupted", error="Setup was interrupted. Retry to resume downloads.")
                self._jobs[job["id"]] = job
        except (OSError, ValueError, KeyError, TypeError):
            pass

    def jobs(self):
        with self.lock:
            self._load()
            return copy.deepcopy(list(self._jobs.values())[-20:])

    def job(self, job_id):
        with self.lock:
            self._load()
            if job_id not in self._jobs:
                raise ValueError("Environment setup job not found.")
            return copy.deepcopy(self._jobs[job_id])

    def start(self, preset):
        if preset not in PRESETS:
            raise ValueError("Unknown environment preset. Choose core or mathlib.")
        with self.lock:
            self._load()
            for job in self._jobs.values():
                if job["preset"] == preset and job["status"] in {"queued", "running"}:
                    return copy.deepcopy(job)
            job_id = uuid.uuid4().hex
            job = {"id": job_id, "preset": preset, "status": "queued", "stage": "queued", "progress": None, "downloadedBytes": 0, "totalBytes": None, "log": [], "createdAt": workspace._now(), "updatedAt": workspace._now(), "error": None, "result": None}
            self._jobs[job_id] = job
            self._cancel[job_id] = threading.Event()
            self._persist()
            thread = threading.Thread(target=self._work, args=(job_id,), daemon=True)
            self._threads[job_id] = thread
            thread.start()
            return copy.deepcopy(job)

    def _persist(self):
        _write_json(root() / "jobs.json", list(self._jobs.values())[-20:])

    def _update(self, job_id, line=None, **fields):
        with self.lock:
            job = self._jobs[job_id]
            job.update(fields, updatedAt=workspace._now())
            if line:
                text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", str(line))
                job["log"] = [*job["log"], text[-2000:]][-60:]
                if job["stage"] == "dependencies":
                    percent = re.search(r"attempted \d+/\d+ = (\d+)%", text)
                    if percent:
                        job["progress"] = min(100, int(percent[1]))
            self._persist()
            payload = copy.deepcopy(job)
        if self.publisher:
            self.publisher({"method": "environment/progress", "params": {"job": payload, "proofId": ""}})

    def _check(self, job_id):
        if self._cancel[job_id].is_set():
            raise SetupCancelled("Environment setup cancelled. Downloads can be resumed.")

    def cancel(self, job_id):
        self.job(job_id)
        with self.lock:
            if job_id in self._cancel:
                self._cancel[job_id].set()
        return self.job(job_id)

    def shutdown(self):
        with self.lock:
            for event in self._cancel.values():
                event.set()
            threads = list(self._threads.values())
        deadline = time.monotonic() + 5
        for thread in threads:
            if thread is not threading.current_thread():
                thread.join(timeout=max(0, deadline - time.monotonic()))

    def wait(self, preset, cancelled=None):
        job = self.start(preset)
        while True:
            if cancelled and cancelled.is_set():
                # Research interruption stops waiting; an independently requested
                # shared installer may safely finish for another conversation.
                raise SetupCancelled("Research paused while the shared environment setup continues.")
            job = self.job(job["id"])
            if job["status"] == "ready":
                return job["result"]
            if job["status"] in {"failed", "cancelled", "interrupted"}:
                raise RuntimeError(job["error"] or "Environment setup failed.")
            time.sleep(0.15)

    def _work(self, job_id):
        try:
            while not self.install_lock.acquire(timeout=0.2):
                self._check(job_id)
            try:
                self._check(job_id)
                self._update(job_id, status="running", stage="checking")
                core = self._core(job_id)
                result = core if self._jobs[job_id]["preset"] == "core" else self._mathlib(job_id, core)
                self._check(job_id)
                self._update(job_id, status="ready", stage="ready", progress=100, result=result)
            finally:
                self.install_lock.release()
        except SetupCancelled as exc:
            self._update(job_id, status="cancelled", stage="cancelled", error=str(exc))
        except Exception as exc:
            self._update(job_id, status="failed", stage="failed", error=str(exc)[-3000:])

    def _save(self, key, record):
        data = manifest()
        data[key] = {**record, "checkedAt": workspace._now()}
        _write_json(root() / "installed.json", data)
        return data[key]

    def _command(self, job_id, command, cwd=None, env=None, timeout=1800):
        self._check(job_id)
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | (getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0)
        options = {"creationflags": flags} if os.name == "nt" else {"start_new_session": True}
        process = subprocess.Popen(command, cwd=cwd, env=env or process_env(), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", **options)
        output = []
        def read():
            for line in process.stdout:
                output.append(line)
                if len(output) > 200:
                    del output[:100]
                self._update(job_id, line=line.strip())
        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        deadline = time.monotonic() + timeout
        try:
            while process.poll() is None:
                self._check(job_id)
                if time.monotonic() > deadline:
                    raise RuntimeError("Environment command timed out. Retry setup to continue.")
                time.sleep(0.15)
        except Exception:
            from .lean import _kill_process_tree
            _kill_process_tree(process)
            process.wait(timeout=10)
            raise
        finally:
            reader.join(timeout=5)
            if not reader.is_alive():
                process.stdout.close()
        if process.returncode:
            raise RuntimeError("Environment command failed: " + "".join(output)[-2500:])
        return "".join(output)

    def _download(self, job_id, asset):
        directory = root() / "downloads"
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / asset["name"]
        def digest(path):
            h = hashlib.sha256()
            with path.open("rb") as f:
                for block in iter(lambda: f.read(1024*1024), b""):
                    self._check(job_id); h.update(block)
            return h.hexdigest()
        if destination.is_file() and digest(destination) == asset["sha256"]:
            return destination
        partial = destination.with_suffix(destination.suffix + ".part")
        offset = partial.stat().st_size if partial.exists() else 0
        headers = {"User-Agent": "ProveIt-environment-setup", "Accept-Encoding": "identity"}
        if offset:
            headers["Range"] = f"bytes={offset}-"
        proxy = workspace.get_settings().get("environmentProxy", "")
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy})) if proxy else urllib.request.build_opener()
        self._update(job_id, stage="downloading", line="Downloading " + asset["name"], totalBytes=asset["size"], progress=0)
        if offset != asset["size"]:
            with opener.open(urllib.request.Request(asset["url"], headers=headers), timeout=45) as response:
                if response.status == 206:
                    content_range = response.headers.get("Content-Range", "")
                    if not content_range.startswith(f"bytes {offset}-"):
                        raise RuntimeError("Invalid download resume response.")
                else:
                    offset = 0
                last = 0.0
                with partial.open("ab" if offset else "wb") as f:
                    while True:
                        self._check(job_id)
                        block = response.read(1024*1024)
                        if not block: break
                        offset += len(block)
                        if offset > asset["size"]:
                            raise RuntimeError("Downloaded archive exceeds its expected size.")
                        f.write(block)
                        if time.monotonic() - last > 0.5:
                            last = time.monotonic()
                            self._update(job_id, downloadedBytes=offset, progress=round(offset / asset["size"] * 100, 1))
        self._update(job_id, stage="checksum", line="Checking archive SHA-256", progress=None, downloadedBytes=offset)
        if not partial.is_file() or partial.stat().st_size != asset["size"] or digest(partial) != asset["sha256"]:
            if partial.exists():
                partial.replace(partial.with_name(partial.name + ".invalid-" + uuid.uuid4().hex))
            raise RuntimeError("Archive checksum failed; retry to download a fresh verified copy.")
        os.replace(partial, destination)
        return destination

    def _extract(self, job_id, archive, destination):
        destination.mkdir(parents=True, exist_ok=False)
        resolved = destination.resolve()
        with zipfile.ZipFile(archive) as z:
            members = z.infolist()
            if sum(i.file_size for i in members) > 8_000_000_000 or len(members) > 300_000:
                raise ValueError("Archive exceeds extraction limits.")
            if shutil.disk_usage(destination).free < sum(i.file_size for i in members) + 250_000_000:
                raise RuntimeError("Not enough free space to extract this archive.")
            for i, member in enumerate(members):
                self._check(job_id)
                name = member.filename.replace("\\", "/")
                path = (destination / name).resolve()
                if path != resolved and resolved not in path.parents or stat.S_ISLNK(member.external_attr >> 16) or ":" in name:
                    raise ValueError("Unsafe archive path.")
                if member.is_dir():
                    path.mkdir(parents=True, exist_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(member) as source, path.open("wb") as target:
                        shutil.copyfileobj(source, target, 1024*1024)
                if i % 500 == 0:
                    self._update(job_id, stage="extracting", progress=round((i+1)/max(1,len(members))*100,1))

    def _core(self, job_id):
        installed = manifest().get("core", {})
        candidates = [installed.get("lean")]
        if os.environ.get("PROVEIT_ENV_IGNORE_SYSTEM") != "1":
            candidates.append(executable("lean", dict(os.environ)))
        for candidate in candidates:
            if candidate and re.search(r"version " + re.escape(VERSION) + r"(?:[ ,)]|$)", _quick_version(candidate), re.I):
                prefix = self._command(job_id, [candidate, "--print-prefix"], timeout=15).strip()
                lake = str(Path(prefix) / "bin" / ("lake.exe" if os.name == "nt" else "lake"))
                lean = str(Path(prefix) / "bin" / ("lean.exe" if os.name == "nt" else "lean"))
                if Path(lean).is_file() and _quick_version(lake):
                    self._smoke(job_id, lean)
                    previous = installed if candidate == installed.get("lean") else {"source": "existing"}
                    return self._save("core", {**previous, "version": VERSION, "lean": lean, "lake": lake, "smokeVerified": True})
        if os.name != "nt" or platform.machine().lower() not in {"amd64", "x86_64"}:
            raise RuntimeError("Automatic binary download currently supports Windows x64. An installed Lean may still be reused.")
        if shutil.disk_usage(root().parent).free < 4_000_000_000:
            raise RuntimeError("At least 4 GB free disk space is required for Lean setup.")
        archive = self._download(job_id, LEAN_ASSET)
        destination = root() / "toolchains" / ("lean-" + VERSION)
        destination.parent.mkdir(parents=True, exist_ok=True)
        stage = destination.with_name(destination.name + ".pending-" + uuid.uuid4().hex)
        self._extract(job_id, archive, stage)
        binaries = list(stage.glob("*/bin/lean.exe"))
        if len(binaries) != 1:
            raise RuntimeError("Lean archive is missing its expected executable.")
        base = binaries[0].parent.parent
        self._smoke(job_id, str(binaries[0]))
        if destination.exists():
            # Preserve a broken managed installation rather than removing user files.
            destination.rename(destination.with_name(destination.name + ".previous-" + uuid.uuid4().hex))
        base.rename(destination)
        stage.rmdir()
        lean, lake = str(destination / "bin/lean.exe"), str(destination / "bin/lake.exe")
        return self._save("core", {"version": VERSION, "lean": lean, "lake": lake, "source": LEAN_ASSET["url"], "sha256": LEAN_ASSET["sha256"], "smokeVerified": True})

    def _smoke(self, job_id, lean, project=None, env=None):
        self._update(job_id, stage="verifying", progress=None, line="Running real Lean environment smoke check")
        with tempfile.TemporaryDirectory(prefix="proveit-env-check-") as directory:
            candidate = Path(directory) / "EnvironmentCheck.lean"
            source = ("import Mathlib.Data.Nat.Prime.Defs\n"
                      "theorem proveit_environment_check : Nat.Prime 2 := Nat.prime_two\n") if project else (
                      "theorem proveit_environment_check : ∀ n : Nat, n = n := by intro n; rfl\n")
            candidate.write_text(source, encoding="utf-8")
            command = [lean, "env", "lean", str(candidate)] if project else [lean, str(candidate)]
            self._command(job_id, command, cwd=project, env=env, timeout=180)

    def _git(self, job_id):
        git = None if os.environ.get("PROVEIT_ENV_IGNORE_SYSTEM") == "1" else shutil.which("git")
        git = git or manifest().get("git", {}).get("git")
        if git and _quick_version(git):
            return git
        archive = self._download(job_id, GIT_ASSET)
        destination = root() / "git" / "mingit-2.51.0"
        destination.parent.mkdir(parents=True, exist_ok=True)
        stage = destination.with_name(destination.name + ".pending-" + uuid.uuid4().hex)
        self._extract(job_id, archive, stage)
        git = stage / "cmd/git.exe"
        if not _quick_version(str(git)):
            raise RuntimeError("Portable Git smoke check failed.")
        if destination.exists():
            destination.rename(destination.with_name(destination.name + ".previous-" + uuid.uuid4().hex))
        stage.rename(destination)
        git = str(destination / "cmd/git.exe")
        self._save("git", {"git": git, "sha256": GIT_ASSET["sha256"]})
        return git

    def _recover_git_locks(self, job_id, project):
        # Only repair locks left by our interrupted installer in private projects.
        managed = (root() / "projects").resolve()
        if managed not in project.resolve().parents:
            raise ValueError("Recovery is restricted to managed projects.")
        if not any(j["preset"] == "mathlib" and j["id"] != job_id and j["status"] in {"interrupted", "cancelled", "failed"} for j in self._jobs.values()):
            return
        git_dirs = [project / ".git", *project.glob(".lake/packages/*/.git")]
        for directory in git_dirs:
            for name in ("index.lock", "shallow.lock", "packed-refs.lock", "config.lock", "HEAD.lock"):
                lock = directory / name
                if lock.is_file() and managed in lock.resolve().parents:
                    try:
                        lock.rename(lock.with_name(name + ".interrupted-" + uuid.uuid4().hex))
                        self._update(job_id, line="Recovered interrupted installer lock: " + directory.parent.name + "/" + name)
                    except PermissionError:
                        raise RuntimeError("A managed Git lock is still in use; stop the other setup and retry.") from None

    def _cache_env(self, env):
        network = root() / "network"
        network.mkdir(parents=True, exist_ok=True)
        # Keep cache transfers bounded without changing the user's curl settings
        # or the upstream Mathlib source. Modest concurrency works through proxies.
        (network / ".curlrc").write_text(
            "connect-timeout = 20\nmax-time = 120\nretry-max-time = 180\nparallel-max = 8\n",
            encoding="utf-8")
        return {**env, "CURL_HOME": str(network), "MATHLIB_CACHE_DIR": str(root() / "mathlib-cache")}

    def _mathlib(self, job_id, core):
        from .lean import ROOT, add_project
        saved = manifest().get("mathlib", {})
        candidates = [Path(saved["path"])] if saved.get("path") else []
        if os.environ.get("PROVEIT_ENV_IGNORE_SYSTEM") != "1":
            candidates.append(ROOT / "mathlib")
        env = {**process_env(), **{k:v for k,v in runtime_env().items() if k.lower() == "path" or k in {"LEAN_EXE", "LAKE_EXE"}}}
        for project in candidates:
            if (project / "lean-toolchain").is_file() and (project / "lean-toolchain").read_text(encoding="utf-8").strip() in {f"leanprover/lean4:v{VERSION}", f"v{VERSION}"}:
                try:
                    self._smoke(job_id, core["lake"], project, env)
                    record = add_project("Mathlib " + VERSION, str(project))
                    previous = saved if saved.get("path") and Path(saved["path"]).resolve() == project.resolve() else {"source": "existing"}
                    return self._save("mathlib", {**previous, "path": str(project), "projectId": record["id"], "version": VERSION, "smokeVerified": True, "smokeImport": "Mathlib.Data.Nat.Prime.Defs"})
                except RuntimeError:
                    if project == ROOT / "mathlib":
                        continue  # Existing user projects are never repaired in place.
        if shutil.disk_usage(root().parent).free < 8_000_000_000:
            raise RuntimeError("At least 8 GB free disk space is required for Mathlib setup.")
        git = self._git(job_id)
        env = self._cache_env(env)
        path_key = next((k for k in env if k.lower() == "path"), "PATH")
        env[path_key] = str(Path(git).parent) + os.pathsep + env.get(path_key, "")
        project = root() / "projects" / ("mathlib-" + VERSION)
        project.parent.mkdir(parents=True, exist_ok=True)
        if not (project / ".git").is_dir():
            if project.exists():
                project.rename(project.with_name(project.name + ".partial-" + uuid.uuid4().hex))
            self._update(job_id, stage="cloning", progress=None, line="Downloading pinned Mathlib sources")
            self._command(job_id, [git, "clone", "--depth", "1", "--branch", "v" + VERSION, "https://github.com/leanprover-community/mathlib4.git", str(project)], env=env, timeout=600)
        if (project / "lean-toolchain").read_text(encoding="utf-8").strip() != f"leanprover/lean4:v{VERSION}":
            raise RuntimeError("Mathlib toolchain does not match the pinned Lean version.")
        self._recover_git_locks(job_id, project)
        self._update(job_id, stage="dependencies", progress=None, line="Fetching Mathlib dependencies and compiled cache")
        for attempt in range(2):
            try:
                self._command(job_id, [core["lake"], "exe", "cache", "get"], cwd=project, env=env, timeout=3600)
                break
            except SetupCancelled:
                raise
            except RuntimeError:
                if attempt:
                    raise
                self._update(job_id, line="Retrying Mathlib cache with already downloaded files preserved")
        self._smoke(job_id, core["lake"], project, env)
        record = add_project("Mathlib " + VERSION, str(project))
        return self._save("mathlib", {"path": str(project), "projectId": record["id"], "version": VERSION, "smokeVerified": True, "smokeImport": "Mathlib.Data.Nat.Prime.Defs", "source": "https://github.com/leanprover-community/mathlib4", "revision": self._command(job_id, [git, "rev-parse", "HEAD"], cwd=project, env=env, timeout=15).strip()})


manager = EnvironmentManager()


def prepare(source: str, project_id: str, cancelled=None) -> str:
    """Select a trusted preset only when automatically configured environments are needed."""
    from .lean import project_path
    if not workspace.get_settings().get("autoSetupLean", True):
        return project_id
    needs_mathlib = bool(re.search(r"(?m)^\s*import\s+Mathlib(?:[.\s]|$)", source))
    if project_id in {"standalone", "mathlib"} and needs_mathlib:
        result = manager.wait("mathlib", cancelled)
        return result["projectId"]
    if project_id == "standalone" and not _quick_version(executable("lean")):
        manager.wait("core", cancelled)
    return project_id
