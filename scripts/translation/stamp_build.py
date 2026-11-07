#!/usr/bin/env python3
"""Bind Android's packaged translation proof to the current source files."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def fingerprint(root):
    root = Path(root)
    paths = []
    for directory in ('frontend/src', 'frontend/scripts', 'scripts/translation', 'catalogue/i18n', 'catalogue/exercises', 'api', 'mcp'):
        for base, dirs, files in os.walk(root / directory):
            dirs[:] = [d for d in dirs if d not in ('node_modules', '.git', '__pycache__', 'coverage', 'data')]
            paths += [Path(base) / name for name in files if Path(name).suffix in ('.js', '.jsx', '.mjs', '.py', '.sh', '.json', '.css')]
    paths += [p for p in (root / 'frontend/android/app/src').rglob('*') if p.is_file() and p.suffix in ('.java', '.kt', '.xml') and 'assets' not in p.relative_to(root / 'frontend/android/app/src').parts]
    paths += [root / p for p in ('frontend/package-lock.json', 'frontend/package.json', 'frontend/vite.config.js', 'frontend/capacitor.config.json', 'frontend/capacitor.config.js', 'frontend/chinese-edition.json', 'frontend/chinese-release-certificate.json', 'frontend/android/app/build.gradle') if (root / p).exists()]
    paths += [root / 'frontend/android' / p for p in ('build.gradle', 'settings.gradle', 'variables.gradle', 'gradle.properties', 'gradle/wrapper/gradle-wrapper.properties', 'app/capacitor.build.gradle', 'app/proguard-rules.pro') if (root / 'frontend/android' / p).exists()]
    h = hashlib.sha256()
    for p in sorted(set(paths)):
        h.update(str(p.relative_to(root)).encode() + b'\0' + p.read_bytes() + b'\0')
    return h.hexdigest()

if __name__ == '__main__':
    output = ROOT / 'frontend/dist/translation-build.json'
    output.write_text(json.dumps({'source_fingerprint': fingerprint(ROOT), 'edition': 'zh-CN', 'platform': 'android'}, indent=2) + '\n')
    print('Stamped', output)
