"""Build from an explicit application resource list; never copy workspace data."""
import subprocess
import sys
import shutil
import importlib.metadata
from pathlib import Path
root = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
    "--name", "proveit-backend", "--distpath", str(root / "build/backend"),
    "--workpath", str(root / "build/pyinstaller"), "--specpath", str(root / "build"),
    "--paths", str(root), "--add-data", str(root / "ui") + ":ui",
    str(root / "desktop/backend.py")], cwd=root, check=True)
destination = root / 'build/backend/proveit-backend'
shutil.copyfile(Path(sys.base_prefix) / 'LICENSE.txt', destination / 'Python-LICENSE.txt')
distribution = importlib.metadata.distribution('pyinstaller')
license_file = next(f for f in distribution.files if str(f).endswith('licenses/COPYING.txt'))
shutil.copyfile(distribution.locate_file(license_file), destination / 'PyInstaller-LICENSE.txt')
