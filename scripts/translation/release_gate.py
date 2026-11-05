#!/usr/bin/env python3
"""Fail closed until translations, candidate review and Android acceptance are complete."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import importlib.util
import zipfile

spec = importlib.util.spec_from_file_location('translation_queue', Path(__file__).with_name('workflow.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
proof_spec = importlib.util.spec_from_file_location('stamp_build', Path(__file__).with_name('stamp_build.py'))
proof = importlib.util.module_from_spec(proof_spec)
proof_spec.loader.exec_module(proof)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state', type=Path, default=Path('/workspace/translation-state'))
    p.add_argument('--root', type=Path, default=m.ROOT)
    p.add_argument('--apk', type=Path, required=True)
    args = p.parse_args()
    q = m.Queue(args.root, args.state)
    report = q.scan()
    failures = []
    if any(count for status, count in report['counts'].items() if status != 'applied'):
        failures.append('Catalogue translations are missing or lack recorded review/application')
    subprocess.run(['node', str(Path(__file__).with_name('audit.mjs')), str(args.state)], check=True)
    audit = json.loads((args.state / 'audit.json').read_text())
    decisions_file = args.state / 'audit-decisions.json'
    decisions = json.loads(decisions_file.read_text()) if decisions_file.exists() else {}
    unresolved = [item for item in audit['issues'] if not (
        decisions.get(item['id'], {}).get('action') == 'accept'
        and decisions[item['id']].get('reviewer') and decisions[item['id']].get('reason'))]
    if unresolved:
        failures.append(f'{len(unresolved)} static candidates await review (including proper names/internal strings)')
    if not args.apk.is_file():
        failures.append('APK does not exist')
    else:
        try:
            with zipfile.ZipFile(args.apk) as apk:
                stamp = json.loads(apk.read('assets/public/translation-build.json'))
            if stamp != {'source_fingerprint': proof.fingerprint(args.root), 'edition': 'zh-CN', 'platform': 'android'}:
                failures.append('APK was built from different sources or for a different edition')
        except (KeyError, ValueError, zipfile.BadZipFile):
            failures.append('APK is missing a valid source fingerprint')
        expected = hashlib.sha256(args.apk.read_bytes()).hexdigest()
        validation_file = args.state / 'acceptance.json'
        validation = json.loads(validation_file.read_text()) if validation_file.exists() else {}
        if validation.get('apk_sha256') != expected:
            failures.append('Acceptance record missing or refers to a different APK')
        for check in ('frontend_suite', 'api_suite', 'mcp_suite', 'training_calculations', 'android_unit_tests', 'apk_signature', 'android_install_launch', 'android_chinese_screens', 'android_offline_workout', 'android_notifications'):
            result = validation.get('checks', {}).get(check, {})
            if result.get('status') != 'passed' or not result.get('evidence') or not result.get('reviewer'):
                failures.append(f'Missing acceptance evidence: {check}')
    print(json.dumps({'ready': not failures, 'failures': failures, 'queue': report['counts']}, ensure_ascii=False, indent=2))
    return bool(failures)

if __name__ == '__main__':
    sys.exit(main())
