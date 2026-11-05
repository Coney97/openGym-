#!/usr/bin/env python3
"""Bind Android's packaged translation proof to the current source files."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def fingerprint(root):
    root = Path(root)
    paths = [p for directory in ('frontend/src', 'catalogue/i18n', 'catalogue/exercises', 'frontend/android/app/src/main/java', 'frontend/android/app/src/main/res')
             for p in (root / directory).rglob('*') if p.is_file()]
    paths += [root / p for p in ('frontend/package-lock.json', 'frontend/package.json', 'frontend/vite.config.js', 'frontend/capacitor.config.json', 'frontend/android/app/build.gradle')]
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(str(p.relative_to(root)).encode() + b'\0' + p.read_bytes() + b'\0')
    return h.hexdigest()

if __name__ == '__main__':
    output = ROOT / 'frontend/dist/translation-build.json'
    output.write_text(json.dumps({'source_fingerprint': fingerprint(ROOT), 'edition': 'zh-CN', 'platform': 'android'}, indent=2) + '\n')
    print('Stamped', output)
