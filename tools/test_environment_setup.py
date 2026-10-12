"""Live isolated environment smoke runner (large downloads; explicitly invoked)."""
import json
import os
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from proveit.environments import manager

if __name__ == "__main__":
    preset = sys.argv[1] if len(sys.argv) > 1 else "core"
    job = manager.start(preset)
    previous = None
    while job["status"] in {"queued", "running"}:
        marker = (job["stage"], int(job["progress"] or 0) // 10)
        if marker != previous:
            print(json.dumps({k: job[k] for k in ("status", "stage", "progress", "downloadedBytes")}), flush=True)
            previous = marker
        time.sleep(1)
        job = manager.job(job["id"])
    print(json.dumps(job, ensure_ascii=False, indent=2), flush=True)
    if job["status"] != "ready":
        raise SystemExit(1)
