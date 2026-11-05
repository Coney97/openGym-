#!/usr/bin/env python3
"""Install only the model named by the official Argos index, using verified HTTPS."""
import hashlib
import json
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import zipfile

INDEX = 'https://raw.githubusercontent.com/argosopentech/argospm-index/main/index.json'
MODEL = 'https://argos-net.com/v1/translate-en_zh-1_9.argosmodel'
DEST = Path('/workspace/translation-model/en-zh')


def main():
    if DEST.exists():
        raise SystemExit('Model directory already exists; inspect it instead of overwriting it.')
    DEST.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=DEST.parent) as work:
        work = Path(work)
        index = work / 'index.json'
        subprocess.run(['curl', '-fLsS', '--max-time', '60', INDEX, '-o', str(index)], check=True)
        entries = json.loads(index.read_text())
        match = [e for e in entries if e.get('from_code') == 'en' and e.get('to_code') == 'zh' and MODEL in e.get('links', [])]
        if len(match) != 1:
            raise SystemExit('Official index changed; inspect it before selecting a new model.')
        archive = work / 'model.argosmodel'
        subprocess.run(['curl', '-fLsS', '--max-time', '600', MODEL, '-o', str(archive)], check=True)
        unpack = work / 'unpack'
        with zipfile.ZipFile(archive) as z:
            if sum(i.file_size for i in z.infolist()) > 2_000_000_000:
                raise SystemExit('Model is unexpectedly large')
            for i in z.infolist():
                path = Path(i.filename)
                if path.is_absolute() or '..' in path.parts or stat.S_ISLNK(i.external_attr >> 16):
                    raise SystemExit('Unsafe archive member')
            z.extractall(unpack)
        metadata = list(unpack.rglob('metadata.json'))
        if len(metadata) != 1:
            raise SystemExit('Unexpected package layout')
        info = json.loads(metadata[0].read_text())
        if info.get('from_code') != 'en' or info.get('to_code') != 'zh':
            raise SystemExit('Wrong language pair')
        model = metadata[0].parent
        if not (model / 'model/model.bin').is_file() or not (model / 'sentencepiece.model').is_file():
            raise SystemExit('Missing model or tokenizer')
        provenance = {'url': MODEL, 'index_url': INDEX, 'package': match[0],
                      'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                      'integrity_note': 'Downloaded with TLS verification from official index; SHA-256 records this artifact, not an independently published expected checksum.'}
        (model / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
        shutil.move(str(model), str(DEST))
    print('Installed model:', DEST)


if __name__ == '__main__':
    main()
