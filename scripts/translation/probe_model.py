#!/usr/bin/env python3
"""Generate representative model drafts for inspection; never approve or apply them."""
import argparse
import json
from pathlib import Path
from workflow import Argos, ROOT, atomic_json, checks, digest


def probe(root, backend):
    root = Path(root)
    samples = json.loads((root / 'scripts/translation/representative-samples.json').read_text())
    chinese = json.loads((root / 'catalogue/i18n/zh.json').read_text())
    tasks = []
    for sample in samples:
        source = json.loads((root / f'catalogue/exercises/{sample["id"]}.json').read_text())
        for field, expected in sample['fields'].items():
            target = chinese[sample['id']][field]
            if digest(source[field]) != expected['source_hash'] or digest(target) != expected['reviewed_target_hash']:
                raise ValueError('Representative source/reference changed; review it again first')
            tasks.append({'key': sample['id'] + ':' + field, 'category': sample['category'],
                          'source': source[field], 'reviewed_reference': target, **expected})
    drafts = []
    for task in tasks:
        result = {**task, 'semantic_review': 'required'}
        for attempt in range(1, 4):
            try:
                draft = backend.translate(task['source'])
                result.update(status='generated', draft=draft, draft_hash=digest(draft),
                              issues=checks(task['source'], draft), attempts=attempt)
                break
            except Exception as error:
                result.update(status='failed', error=type(error).__name__, attempts=attempt)
        drafts.append(result)
    return {'model': getattr(backend, 'identity', 'test fixture'), 'semantic_approval': False, 'drafts': drafts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--model', type=Path, default=Path('/workspace/translation-model/en-zh'))
    parser.add_argument('--output', type=Path, default=Path('/workspace/translation-state/model-probe.json'))
    args = parser.parse_args()
    result = probe(args.root, Argos(args.model))
    atomic_json(args.output, result)
    print('Saved representative drafts for semantic inspection:', args.output)


if __name__ == '__main__':
    main()
