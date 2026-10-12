#!/usr/bin/env python3
"""Start the ProveIt local mathematical research workbench."""

import os

from proveit.http_server import serve
from proveit.instance import WorkspaceLease


if __name__ == "__main__":
    port = int(os.environ.get("PROVEIT_PORT", "8765"))
    with WorkspaceLease(port):
        serve(port)
