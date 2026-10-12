"""Fail closed on unexpected staged paths and common secret/private-path patterns."""
import re
import subprocess
from pathlib import PurePosixPath

allowed_roots = {'proveit', 'ui', 'desktop', 'tools', 'tests', 'skills', '.github'}
allowed_docs = {'INSTALL.md', 'USAGE.md', 'README.en.md', 'DEVELOPMENT.md', 'LANGUAGE_POLICY.md'}
allowed_docs |= {name.replace('.md', '.zh-CN.md') for name in allowed_docs if name != 'README.en.md'}
allowed_docs.add('README.zh-CN.md')
allowed_files = {'.gitignore', 'README.zh-CN.md', 'README.md', 'LICENSE', 'package.json', 'package-lock.json',
                 'requirements-build.txt', 'app.py', 'CONTRIBUTING.md', 'SECURITY.md', 'THIRD_PARTY_NOTICES.md', 'docs/assets/workspace.png'}
allowed_files |= {'CONTRIBUTING.zh-CN.md', 'SECURITY.zh-CN.md', 'THIRD_PARTY_NOTICES.zh-CN.md'}
patterns = [rb'gh[pousr]_[A-Za-z0-9]{20,}', rb'sk-[A-Za-z0-9_-]{24,}',
            rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
            rb'[A-Za-z]:[\\/]Users[\\/][^\\/\s"\']+',
            rb'01a[0-9a-f]{5}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}']
files = subprocess.check_output(['git', 'ls-files', '-z']).decode().split('\0')
issues = []
for name in filter(None, files):
    path = PurePosixPath(name)
    allowed = name in allowed_files or path.parts[0] in allowed_roots or (path.parts[0] == 'docs' and path.name in allowed_docs)
    if not allowed or any(p in {'.proveit', 'proofs', 'node_modules', '__pycache__'} for p in path.parts):
        issues.append((name, 'unexpected tracked path'))
        continue
    data = subprocess.check_output(['git', 'show', ':' + name])
    if path.suffix in {'.sqlite', '.db', '.log', '.pem', '.key', '.exe', '.zip'}:
        issues.append((name, 'generated or sensitive extension'))
    if any(re.search(pattern, data) for pattern in patterns):
        issues.append((name, 'sensitive pattern; inspect locally'))
if issues:
    for name, reason in issues:
        print(f'FAIL {name}: {reason}')
    raise SystemExit(1)
print(f'PASS: {len(list(filter(None, files)))} tracked files; explicit path allowlist and sensitive-pattern scan')
