#!/usr/bin/env python3
"""Resumable zh-CN catalogue translation. Generated text never approves itself."""
import argparse
from collections import Counter
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import sqlite3
import subprocess
import sys
import time
import tempfile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def digest(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def android_text(item):
    value = ''.join(item.itertext())
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    return re.sub(r'\\([nrt\\\'"])', lambda m: {'n': '\n', 'r': '\r', 't': '\t'}.get(m[1], m[1]), value)


def process_start(pid):
    try:
        # PID plus Linux start ticks avoids confusing a reused PID with the old worker.
        return Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19]
    except (OSError, IndexError):
        return None


def atomic_json(path, value):
    path = Path(path)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False, encoding='utf-8') as f:
        tmp = Path(f.name)
        f.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def checks(source, target):
    """Structural checks only; passing does NOT establish semantic accuracy."""
    issues = []
    if isinstance(source, str) and isinstance(target, dict) and target and set(target) <= {'zero', 'one', 'two', 'few', 'many', 'other'}:
        return sorted(set(flag for form in target.values() for flag in checks(source, form)))
    if type(source) is not type(target):
        return ['type_changed']
    if isinstance(source, list):
        if len(source) != len(target):
            issues.append('step_count_changed')
        for original, translated in zip(source, target):
            issues.extend(checks(original, translated))
        return sorted(set(issues))
    if not isinstance(target, str) or not target.strip():
        return ['empty_text']
    if not re.search(r'[\u3400-\u9fff]', target):
        issues.append('no_chinese')
    if Counter(re.findall(r'\{\d+\}|%\d*\$?[sdf]', source)) != Counter(re.findall(r'\{\d+\}|%\d*\$?[sdf]', target)):
        issues.append('placeholders_changed')
    # Multisets preserve repetitions; Chinese digits are intentionally flagged for review.
    if Counter(re.findall(r'\d+(?:\.\d+)?', source)) != Counter(re.findall(r'\d+(?:\.\d+)?', target)):
        issues.append('numbers_changed')
    if re.search(r'[A-Za-z]{3,}', target):
        issues.append('latin_text_review')
    return sorted(set(issues))


class Queue:
    def __init__(self, root, state):
        self.root, self.state = Path(root).resolve(), Path(state).resolve()
        self.state.mkdir(parents=True, exist_ok=True)
        owner = self.state / 'project.json'
        if owner.exists() and json.loads(owner.read_text())['root'] != str(self.root):
            raise ValueError('This state directory belongs to another checkout')
        atomic_json(owner, {'root': str(self.root)})
        self.db = sqlite3.connect(self.state / 'queue.sqlite3')
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS tasks (
            key TEXT PRIMARY KEY, exercise TEXT NOT NULL, field TEXT NOT NULL,
            source TEXT NOT NULL, hash TEXT NOT NULL, target TEXT,
            baseline TEXT,
            status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
            retry_at REAL NOT NULL DEFAULT 0, issues TEXT NOT NULL DEFAULT '[]',
            reviewer TEXT, error TEXT, active INTEGER NOT NULL DEFAULT 1);
          CREATE TABLE IF NOT EXISTS events (
            time REAL, key TEXT, event TEXT, detail TEXT);
          CREATE INDEX IF NOT EXISTS events_by_key ON events(key,event,time);
        ''')
        columns = [row[1] for row in self.db.execute('PRAGMA table_info(tasks)')]
        missing = [name for name in ('baseline', 'kind', 'locator') if name not in columns]
        if missing:
            backup = sqlite3.connect(self.state / ('schema-backup-' + str(time.time_ns()) + '.sqlite3'))
            self.db.backup(backup)
            backup.close()
            for name in missing:
                self.db.execute('ALTER TABLE tasks ADD COLUMN ' + name + (" TEXT NOT NULL DEFAULT 'catalogue'" if name == 'kind' else ' TEXT'))
            if 'baseline' in missing:
                self.db.execute("UPDATE tasks SET baseline=target WHERE status IN ('existing','applied')")
            self.db.commit()

    def event(self, key, event, detail):
        self.db.execute('INSERT INTO events VALUES (?, ?, ?, ?)', (time.time(), key, event, encoded(detail)))

    def _upsert(self, key, exercise, field, source, existing, kind='catalogue', locator=None):
        source_hash = digest(source)
        old = self.db.execute('SELECT * FROM tasks WHERE key=?', (key,)).fetchone()
        target = encoded(existing) if existing else None
        if old and old['hash'] == source_hash:
            if old['status'] in ('existing', 'applied') and target != old['target']:
                self.db.execute("UPDATE tasks SET target=?, baseline=?, status=?, reviewer=NULL, issues=?, active=1 WHERE key=?",
                    (target, target, 'existing' if existing else 'pending', encoded(checks(source, existing)) if existing else '[]', key))
                self.event(key, 'external_edit', {})
            else:
                self.db.execute('UPDATE tasks SET active=1, kind=?, locator=? WHERE key=?', (kind, encoded(locator), key))
            return
        if old:
            self.event(key, 'source_changed', dict(old))
        self.db.execute('''INSERT OR REPLACE INTO tasks
          (key, exercise, field, source, hash, target, baseline, status, issues, active, kind, locator)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)''',
          (key, exercise, field, encoded(source), source_hash, target, target,
           'existing' if existing else 'pending', encoded(checks(source, existing)) if existing else '[]', kind, encoded(locator)))

    def _ui(self):
        if not (self.root / 'frontend/src/locales/zh.js').exists():
            return []
        result = subprocess.run(['node', str(Path(__file__).with_name('ui_tasks.mjs')), str(self.root)],
                                check=True, capture_output=True, text=True)
        return json.loads(result.stdout)

    def _resources(self):
        if not (self.root / 'frontend').exists():
            return []
        result = subprocess.run(['node', str(Path(__file__).with_name('resource_tasks.mjs')), str(self.root)], check=True, capture_output=True, text=True)
        return json.loads(result.stdout)

    def _native(self):
        base = self.root / 'frontend/android/app/src/main/res/values'
        translated = self.root / 'frontend/android/app/src/chinese/res/values/strings.xml'
        known = {}
        for directory in ('main/res/values-zh-rCN', 'chinese/res/values'):
            for file in (self.root / 'frontend/android/app/src' / directory).glob('*.xml'):
                for item in ET.parse(file).getroot().findall('string'):
                    known[item.get('name')] = android_text(item)
        rows = []
        for file in base.glob('*.xml'):
            for item in ET.parse(file).getroot().findall('string'):
                name, value = item.get('name'), android_text(item)
                if name in ('package_name', 'custom_url_scheme') or item.get('translatable') == 'false' or value.startswith('@'):
                    continue
                if list(item):
                    continue  # Styled resources stay in the static audit, not an unsafe text rewrite.
                rows.append((name, value, known.get(name), str(file.relative_to(self.root)), str(translated.relative_to(self.root))))
        return rows

    def scan(self):
        zh = json.loads((self.root / 'catalogue/i18n/zh.json').read_text())
        ui, native, resources = self._ui(), self._native(), self._resources()
        with self.db:
            self.db.execute('UPDATE tasks SET active=0')
            for path in sorted((self.root / 'catalogue/exercises').glob('*.json')):
                ex = json.loads(path.read_text())
                if ex.get('variantOf'):
                    continue
                for field in ('name', 'description', 'instructions'):
                    if ex.get(field):
                        self._upsert(f'{ex["id"]}:{field}', ex['id'], field, ex[field], zh.get(ex['id'], {}).get(field))
            for entry in ui:
                self._upsert('ui:' + digest(entry['source']), '', 'text', entry['source'], entry['target'], 'ui', {'key': entry['source'], 'pack': entry.get('pack', 'frontend/src/locales/zh.js')})
            for name, value, target, source_file, destination in native:
                self._upsert('native:' + name, '', 'text', value, target, 'native', {'key': name, 'source_file': source_file, 'destination': destination})
            for entry in resources:
                self._upsert(entry['kind'] + ':' + digest(entry['key']), '', 'text', entry['source'], entry['target'], entry['kind'], entry['locator'])
            registry = Path(__file__).with_name('source-conflicts.json')
            conflicts = json.loads(registry.read_text()) if registry.exists() else {}
            for key, conflict in conflicts.items():
                exercise = self.root / f"catalogue/exercises/{key.split(':')[0]}.json"
                row = self.db.execute('SELECT * FROM tasks WHERE key=? AND active=1', (key,)).fetchone()
                if not exercise.exists() or not row:
                    continue
                source = json.loads(exercise.read_text())
                unresolved = digest({'name': source['name'], 'instructions': source['instructions']}) == conflict['context_hash']
                if unresolved and row['error'] != 'conflicting-source-posture':
                    self.db.execute("UPDATE tasks SET status='blocked',reviewer=NULL,error='conflicting-source-posture' WHERE key=?", (key,))
                    self.event(key, 'source_conflict', conflict)
                elif not unresolved and row['error'] == 'conflicting-source-posture':
                    self.db.execute("UPDATE tasks SET status=?,reviewer=NULL,error=NULL WHERE key=?", ('existing' if row['target'] else 'pending', key))
                    self.event(key, 'source_conflict_context_changed', conflict)
        return self.report()

    def report(self):
        counts = dict(self.db.execute('SELECT status, COUNT(*) FROM tasks WHERE active=1 GROUP BY status').fetchall())
        fields = [dict(r) for r in self.db.execute('SELECT field, status, COUNT(*) AS count FROM tasks WHERE active=1 GROUP BY field,status')]
        report = {'time': time.time(), 'counts': counts, 'fields': fields,
                  'structural_flags': self.db.execute("SELECT COUNT(*) FROM tasks WHERE active=1 AND issues!='[]'").fetchone()[0],
                  'review_note': 'existing and generated translations still require review; structural checks are not semantic review'}
        marker = self.state / 'worker.json'
        worker = json.loads(marker.read_text()) if marker.exists() else {'state': 'not_started'}
        if worker.get('state') == 'running' and (not worker.get('start_ticks') or process_start(worker['pid']) != worker['start_ticks']):
            worker = {**worker, 'state': 'interrupted'}
        report['worker'] = worker
        atomic_json(self.state / 'status.json', report)
        return report

    def export(self, output, status=None):
        rows = self.db.execute('SELECT * FROM tasks WHERE active=1 ORDER BY key')
        atomic_json(Path(output), [{**dict(row), 'target_hash': digest(json.loads(row['target'])) if row['target'] else None} for row in rows if not status or row['status'] == status])

    def _review(self, key, expected_hash, expected_target_hash, reviewer, approve, note, allow_technical=False, allow_format=False):
        row = self.db.execute('SELECT * FROM tasks WHERE key=? AND active=1', (key,)).fetchone()
        if not row or row['hash'] != expected_hash or not row['target']:
            raise ValueError('Missing translation or stale source hash')
        if approve and row['error'] == 'conflicting-source-posture':
            raise ValueError('Resolve the conflicting English source before approving its translation')
        target, source = json.loads(row['target']), json.loads(row['source'])
        if digest(target) != expected_target_hash:
            raise ValueError('Stale translation hash')
        issues = checks(source, target)
        permitted = {'latin_text_review'}
        terms = {'kg', 'lb', 'RPE', 'RIR', 'openGym', 'Bluetooth', 'Health Connect', 'Android', 'NFC', 'JSON', 'ZIP', 'PDF', 'HD', 'Google', 'YouTube', 'GitHub', 'SHA-256'}
        retained = Path(__file__).with_name('retained-terms.json')
        if retained.exists():
            terms.update(json.loads(retained.read_text()))
        token = re.sub(r'\{\d+\}', '', source).strip() if isinstance(source, str) else ''
        if allow_technical and row['kind'] != 'catalogue' and source == target and token in terms:
            permitted.add('no_chinese')
        formats = Path(__file__).with_name('reviewed-formats.json')
        if allow_format and row['kind'] == 'ui' and isinstance(source, str) and formats.exists():
            pair = json.loads(formats.read_text()).get(source)
            if pair and target == pair['target']:
                permitted.update(set(pair['flags']) & {'numbers_changed', 'no_chinese'})
        if approve and any(i not in permitted for i in issues):
            raise ValueError('Resolve structural checks before approval: ' + ', '.join(issues))
        if not reviewer.strip() or not note.strip():
            raise ValueError('Reviewer and review note required')
        self.db.execute('UPDATE tasks SET status=?, reviewer=?, issues=? WHERE key=?', ('approved' if approve else 'blocked', reviewer, encoded(issues), key))
        self.event(key, 'review', {'source_hash': expected_hash, 'target_hash': expected_target_hash, 'reviewer': reviewer, 'approved': approve, 'note': note, 'retained_technical': allow_technical, 'localized_format': allow_format})

    def review(self, key, expected_hash, expected_target_hash, reviewer, approve, note, allow_technical=False, allow_format=False):
        with self.db:
            self._review(key, expected_hash, expected_target_hash, reviewer, approve, note, allow_technical, allow_format)
        self.report()

    def review_batch(self, reviews):
        if len(reviews) > 100:
            raise ValueError('At most 100 review decisions per batch')
        if len({row['key'] for row in reviews}) != len(reviews):
            raise ValueError('Duplicate review decisions')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            for row in reviews:
                if row['decision'] not in ('approve', 'reject'):
                    raise ValueError('Unknown decision')
                self._review(row['key'], row['source_hash'], row['target_hash'], row['reviewer'], row['decision'] == 'approve', row['note'], row.get('allow_technical', False), row.get('allow_format', False))
        self.report()

    def import_candidates(self, candidates):
        with self.db:
            for candidate in candidates:
                row = self.db.execute('SELECT * FROM tasks WHERE key=? AND active=1', (candidate['key'],)).fetchone()
                if not row or row['hash'] != candidate['source_hash']:
                    raise ValueError('Unknown task or stale source hash')
                if row['error'] == 'conflicting-source-posture':
                    raise ValueError('A new target cannot resolve conflicting source instructions')
                translated = candidate['target']
                flags = checks(json.loads(row['source']), translated)
                self.db.execute("UPDATE tasks SET target=?, status='generated', reviewer=NULL, issues=?, error=NULL WHERE key=?", (encoded(translated), encoded(flags), row['key']))
                self.event(row['key'], 'candidate_imported', {'target_hash': digest(translated), 'issues': flags})
        self.report()

    def apply(self):
        """Apply reviewed fields with a recoverable journal and optimistic file conflict checks."""
        self.db.execute('BEGIN IMMEDIATE')
        rows = []
        try:
            rows = list(self.db.execute("SELECT * FROM tasks WHERE active=1 AND status='approved' ORDER BY key"))
            catalogue_file = self.root / 'catalogue/i18n/zh.json'
            catalogue = json.loads(catalogue_file.read_text())
            ui = {entry['source']: entry['target'] for entry in self._ui()}
            native = {row[0]: row for row in self._native()}
            ui_updates, native_updates, resource_updates, destinations = [], {}, [], {}
            resources = {(r['kind'], r['locator']['key']): r for r in self._resources()}
            for row in rows:
                location = json.loads(row['locator']) if row['locator'] else None
                value = json.loads(row['target'])
                if row['kind'] == 'catalogue':
                    current_source = json.loads((self.root / f'catalogue/exercises/{row["exercise"]}.json').read_text()).get(row['field'])
                    old = catalogue.get(row['exercise'], {}).get(row['field'])
                    destination = catalogue_file
                elif row['kind'] == 'ui':
                    current_source, old = location['key'], ui.get(location['key'])
                    if location['key'] not in ui:
                        raise ValueError('UI source key removed; rescan first')
                    destination = self.root / location.get('pack', 'frontend/src/locales/zh.js')
                elif row['kind'] in ('boot', 'export', 'native_fallback'):
                    current = resources.get((row['kind'], location['key']))
                    if not current:
                        raise ValueError('Text resource removed; rescan first')
                    current_source, old = current['source'], current['target']
                    destination = self.root / location['file']
                else:
                    current = native.get(location['key'])
                    if not current:
                        raise ValueError('Native source removed; rescan first')
                    current_source, old = current[1], current[2]
                    destination = self.root / location['destination']
                if digest(current_source) != row['hash']:
                    raise ValueError('Source changed; rescan and review again: ' + row['key'])
                baseline = json.loads(row['baseline']) if row['baseline'] else None
                if old != baseline and old != value:
                    raise ValueError('Destination already has a different value: ' + row['key'])
                if destination not in destinations:
                    destinations[destination] = destination.read_text() if destination.exists() else None
                if row['kind'] == 'catalogue':
                    catalogue.setdefault(row['exercise'], {})[row['field']] = value
                elif row['kind'] == 'ui':
                    ui_updates.append({'key': location['key'], 'target': value, 'pack': location.get('pack', 'frontend/src/locales/zh.js')})
                elif row['kind'] in ('boot', 'export', 'native_fallback'):
                    resource_updates.append({'kind': row['kind'], 'locator': location, 'target': value})
                else:
                    native_updates[location['key']] = value
            if rows:
                journal = self.state / ('apply-' + str(time.time_ns()) + '.json')
                atomic_json(journal, {'status': 'prepared', 'files': {str(p): text for p, text in destinations.items()}, 'keys': [row['key'] for row in rows]})
                # Check exact file baselines, not just target fields, before writing anything.
                for destination, original in destinations.items():
                    if (destination.read_text() if destination.exists() else None) != original:
                        raise ValueError('Concurrent file edit: ' + str(destination))
                if any(row['kind'] == 'catalogue' for row in rows):
                    atomic_json(catalogue_file, catalogue)
                if ui_updates:
                    subprocess.run(['node', str(Path(__file__).with_name('apply_ui.mjs')), str(self.root)], input=encoded(ui_updates), text=True, check=True, capture_output=True)
                if resource_updates:
                    subprocess.run(['node', str(Path(__file__).with_name('apply_resource.mjs')), str(self.root)], input=encoded(resource_updates), text=True, check=True, capture_output=True)
                if native_updates:
                    destination = self.root / 'frontend/android/app/src/chinese/res/values/strings.xml'
                    xml = ET.parse(destination) if destination.exists() else ET.ElementTree(ET.Element('resources'))
                    for key, value in native_updates.items():
                        item = next((e for e in xml.getroot().findall('string') if e.get('name') == key), None)
                        if item is None:
                            item = ET.SubElement(xml.getroot(), 'string', {'name': key})
                        item.text = value.replace('\\', '\\\\').replace('\n', '\\n').replace('"', '\\"').replace("'", "\\'")
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    ET.indent(xml)
                    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as output:
                        xml.write(output, encoding='utf-8', xml_declaration=True)
                        temporary = output.name
                    os.replace(temporary, destination)
                for row in rows:
                    self.db.execute("UPDATE tasks SET status='applied', baseline=target WHERE key=?", (row['key'],))
                    self.event(row['key'], 'applied', {'hash': row['hash']})
            self.db.commit()
            if rows:
                atomic_json(journal, {'status': 'complete', 'files': {str(p): text for p, text in destinations.items()}, 'keys': [row['key'] for row in rows]})
        except BaseException:
            self.db.rollback()
            raise
        self.report()
        return len(rows)


class Argos:
    def __init__(self, model):
        import ctranslate2
        import sentencepiece
        from opencc import OpenCC
        model = Path(model)
        if not (model / 'model/model.bin').is_file() or not (model / 'sentencepiece.model').is_file():
            raise ValueError('Official en-zh model not installed: ' + str(model))
        self.tokenizer = sentencepiece.SentencePieceProcessor(model_file=str(model / 'sentencepiece.model'))
        self.simplified = OpenCC('t2s')
        self.engine = ctranslate2.Translator(str(model / 'model'), device='cpu', compute_type='int8', inter_threads=1, intra_threads=2)
        self.identity = {'engine': ctranslate2.__version__, 'provenance': json.loads((model / 'provenance.json').read_text()) if (model / 'provenance.json').exists() else 'unrecorded'}

    def translate(self, source):
        strings = source if isinstance(source, list) else [source]
        tokens = [self.tokenizer.encode(s, out_type=str) for s in strings]
        results = self.engine.translate_batch(tokens, beam_size=4, max_decoding_length=512)
        translations = [self.simplified.convert(self.tokenizer.decode(r.hypotheses[0])) for r in results]
        return translations if isinstance(source, list) else translations[0]


def run(queue, backend, limit=0, max_attempts=3):
    stop = False
    def stopping(*_):
        nonlocal stop
        stop = True
    signal.signal(signal.SIGTERM, stopping)
    signal.signal(signal.SIGINT, stopping)
    processed = 0
    with (queue.state / 'worker.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        atomic_json(queue.state / 'worker.json', {'pid': os.getpid(), 'start_ticks': process_start(os.getpid()), 'state': 'running', 'started': time.time()})
        try:
            while not stop and (not limit or processed < limit):
                row = queue.db.execute("SELECT * FROM tasks WHERE active=1 AND status IN ('pending','retry') AND retry_at<=? ORDER BY exercise,field LIMIT 1", (time.time(),)).fetchone()
                if row is None:
                    waiting = queue.db.execute("SELECT MIN(retry_at) FROM tasks WHERE active=1 AND status='retry'").fetchone()[0]
                    if waiting is None:
                        break
                    time.sleep(min(2, max(0.1, waiting - time.time())))
                    continue
                attempts = row['attempts'] + 1
                try:
                    original = json.loads(row['source'])
                    translated = backend.translate(original)
                    flags = checks(original, translated)
                    with queue.db:
                        updated = queue.db.execute("UPDATE tasks SET target=?, status='generated', attempts=?, issues=?, error=NULL WHERE key=? AND hash=? AND status IN ('pending','retry') AND attempts=? AND active=1", (encoded(translated), attempts, encoded(flags), row['key'], row['hash'], row['attempts']))
                        queue.event(row['key'], 'generated' if updated.rowcount else 'discarded_stale_result', {'source_hash': row['hash'], 'attempt': attempts, 'issues': flags, 'backend': type(backend).__name__, 'model': getattr(backend, 'identity', 'test fixture')})
                except Exception as error:
                    # Never log exception messages from a provider: they may contain credentials.
                    with queue.db:
                        queue.db.execute("UPDATE tasks SET status=?, attempts=?, error=?, retry_at=? WHERE key=? AND hash=? AND status IN ('pending','retry') AND attempts=? AND active=1", ('blocked' if attempts >= max_attempts else 'retry', attempts, type(error).__name__, time.time() + min(30, 2 ** attempts), row['key'], row['hash'], row['attempts']))
                        queue.event(row['key'], 'generation_error', {'type': type(error).__name__, 'attempt': attempts})
                processed += 1
                queue.report()
                print(encoded({'key': row['key'], 'processed': processed, 'time': time.time()}), flush=True)
        finally:
            atomic_json(queue.state / 'worker.json', {'pid': os.getpid(), 'state': 'stopped', 'time': time.time()})
            queue.report()
    return processed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--state', type=Path, default=Path('/workspace/translation-state'))
    parser.add_argument('--model', type=Path, default=Path('/workspace/translation-model/en-zh'))
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('scan', 'status', 'apply'):
        commands.add_parser(name)
    for name in ('run', 'start'):
        p = commands.add_parser(name)
        p.add_argument('--limit', type=int, default=0)
    p = commands.add_parser('export')
    p.add_argument('output', type=Path)
    p.add_argument('--status')
    p = commands.add_parser('import')
    p.add_argument('input', type=Path)
    p = commands.add_parser('review-batch')
    p.add_argument('input', type=Path)
    p = commands.add_parser('review')
    p.add_argument('key')
    p.add_argument('--source-hash', required=True)
    p.add_argument('--target-hash', required=True)
    p.add_argument('--reviewer', required=True)
    p.add_argument('--note', required=True)
    p.add_argument('--reject', action='store_true')
    p.add_argument('--allow-technical', action='store_true')
    p.add_argument('--allow-format', action='store_true', help='Only exact reviewed UI format pairs; never catalogue numbers')
    args = parser.parse_args()
    queue = Queue(args.root, args.state)
    if args.command == 'scan':
        print(encoded(queue.scan()))
    elif args.command == 'status':
        print(encoded(queue.report()))
    elif args.command == 'export':
        queue.export(args.output, args.status)
    elif args.command == 'review-batch':
        queue.review_batch(json.loads(args.input.read_text()))
    elif args.command == 'import':
        queue.import_candidates(json.loads(args.input.read_text()))
    elif args.command == 'apply':
        print('Applied:', queue.apply())
    elif args.command == 'review':
        queue.review(args.key, args.source_hash, args.target_hash, args.reviewer, not args.reject, args.note, args.allow_technical, args.allow_format)
    elif args.command in ('run', 'start'):
        queue.scan()
        backend = Argos(args.model)  # Fail before starting a misleading idle background process.
        if args.command == 'run':
            run(queue, backend, args.limit)
        else:
            # A detached process survives this CLI, not cloud VM shutdown/publication.
            with (args.state / 'worker.log').open('ab') as log:
                process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--root', str(args.root), '--state', str(args.state), '--model', str(args.model), 'run', '--limit', str(args.limit)], stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                marker = args.state / 'worker.json'
                if marker.exists() and json.loads(marker.read_text()).get('pid') == process.pid:
                    print('Started worker PID', process.pid)
                    break
                if process.poll() is not None:
                    raise RuntimeError('Worker exited before acquiring its lock; inspect worker.log')
                time.sleep(0.05)
            else:
                process.terminate()
                raise RuntimeError('Worker did not report startup; inspect worker.log')


if __name__ == '__main__':
    main()
