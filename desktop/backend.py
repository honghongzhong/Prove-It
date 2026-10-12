"""Frozen server entry point; verifier is dispatched in its own child process."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if __name__ == "__main__":
    if "--verify" in sys.argv:
        sys.argv.remove("--verify")
        from tools.lean_verify import main
        raise SystemExit(main())
    from proveit.http_server import serve
    from proveit.instance import WorkspaceLease
    with WorkspaceLease(0):
        serve(0, desktop=True)
