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
import re

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
    active = sum(report['counts'].values())
    if not active or not q.db.execute("SELECT COUNT(*) FROM tasks WHERE active=1 AND kind='catalogue'").fetchone()[0]:
        failures.append('Translation inventory is empty')
    if any(count for status, count in report['counts'].items() if status != 'applied'):
        failures.append('Translations are missing or lack recorded review/application')
    for row in q.db.execute("SELECT * FROM tasks WHERE active=1 AND status='applied'"):
        events = q.db.execute("SELECT detail FROM events WHERE key=? AND event='review' ORDER BY time DESC", (row['key'],)).fetchall()
        if not any((event := json.loads(r[0])).get('approved') and event.get('source_hash') == row['hash']
                   and event.get('target_hash') == m.digest(json.loads(row['target'])) and event.get('note') for r in events):
            failures.append('Missing matching semantic review: ' + row['key'])
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
        edition = json.loads((args.root / 'frontend/chinese-edition.json').read_text())
        cert = json.loads((args.root / 'frontend/chinese-release-certificate.json').read_text())
        tools = Path('/workspace/android-sdk/build-tools/35.0.0')
        try:
            signing = subprocess.run([str(tools / 'apksigner'), 'verify', '--print-certs', str(args.apk)], check=True, capture_output=True, text=True).stdout
            if cert['sha256'].lower() not in signing.lower():
                failures.append('APK does not use the independent release certificate')
            manifest = subprocess.run([str(tools / 'aapt'), 'dump', 'badging', str(args.apk)], check=True, capture_output=True, text=True).stdout
            fields = dict(re.findall(r"(name|versionCode|versionName)='([^']+)'", manifest.splitlines()[0]))
            if fields != {'name': edition['appId'], 'versionCode': str(edition['versionCode']), 'versionName': edition['versionName']}:
                failures.append('APK package/version differs from Chinese edition configuration')
            if 'application-debuggable' in manifest:
                failures.append('Final APK must not be debuggable')
        except (OSError, subprocess.CalledProcessError):
            failures.append('Unable to verify APK signing and identity')
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
        if validation.get('source_fingerprint') != proof.fingerprint(args.root):
            failures.append('Acceptance record refers to different sources')
        for check in ('frontend_suite', 'api_suite', 'mcp_suite', 'translation_queue_suite', 'training_calculations', 'android_unit_tests', 'apk_signature', 'android_install_launch', 'android_chinese_screens', 'android_offline_workout', 'android_saved_restart', 'android_notifications', 'android_backup_json_migration', 'android_backup_media_zip_migration'):
            result = validation.get('checks', {}).get(check, {})
            if result.get('status') != 'passed' or not result.get('evidence') or not result.get('reviewer'):
                failures.append(f'Missing acceptance evidence: {check}')
                continue
            evidence = result['evidence']
            if not isinstance(evidence, list):
                failures.append(f'Evidence must include file hashes: {check}')
                continue
            for item in evidence:
                file = Path(item.get('path', ''))
                if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != item.get('sha256'):
                    failures.append(f'Missing or changed evidence file: {check}')
            if check in ('frontend_suite', 'api_suite', 'mcp_suite', 'translation_queue_suite', 'training_calculations', 'android_unit_tests'):
                if result.get('tests', 0) <= 0 or result.get('failures') != 0:
                    failures.append(f'Incomplete or failed test execution: {check}')
    print(json.dumps({'ready': not failures, 'failures': failures, 'queue': report['counts']}, ensure_ascii=False, indent=2))
    return bool(failures)

if __name__ == '__main__':
    sys.exit(main())
