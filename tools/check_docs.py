"""Validate bilingual public documentation pairs and relative Markdown links."""
from pathlib import Path
import re
import subprocess

root = Path(__file__).resolve().parents[1]
paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
documents = [root / name for name in paths if name.endswith('.md') and not name.startswith('ui/vendor/')]
errors = []
for document in documents:
    if document.name.endswith('.zh-CN.md'):
        partner = document.with_name(document.name.replace('.zh-CN.md', '.md'))
        if document.parent.name == 'docs' and document.name == 'README.zh-CN.md':
            partner = document.with_name('README.en.md')
    elif document.name == 'README.en.md':
        partner = document.with_name('README.zh-CN.md')
    else:
        partner = document.with_name(document.stem + '.zh-CN.md')
    text = document.read_text(encoding='utf-8-sig')
    if not partner.is_file() or partner.name not in text:
        errors.append(f'{document.relative_to(root)}: missing linked language counterpart')
    for target in re.findall(r'\]\(([^)]+)\)', text):
        if '://' in target or target.startswith('#'):
            continue
        if not (document.parent / target.split('#')[0]).exists():
            errors.append(f'{document.relative_to(root)}: missing relative link {target}')
if errors:
    raise SystemExit('\n'.join(errors))
print(f'PASS: {len(documents)} public Markdown documents have linked English/Chinese counterparts and valid local links')
