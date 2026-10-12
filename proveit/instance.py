"""OS-backed single-owner lease for each workspace (automatically released on exit)."""
import os
from . import workspace

class WorkspaceLease:
    def __init__(self, port):
        self.port = port
        self.file = None

    def __enter__(self):
        workspace.STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.file = (workspace.STATE_DIR / 'server.lock').open('a+b')
        if os.fstat(self.file.fileno()).st_size == 0:
            self.file.write(b'0'); self.file.flush()
        self.file.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.file.close()
            raise RuntimeError('This ProveIt workspace already has a running server. Open its existing URL.') from exc
        return self

    def __exit__(self, *_):
        self.file.close()
