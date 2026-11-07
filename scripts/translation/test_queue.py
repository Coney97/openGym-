import importlib.util
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('workflow.py')
spec = importlib.util.spec_from_file_location('translation_queue', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'project'
        self.state = Path(self.temp.name) / 'state'
        (self.root / 'catalogue/exercises').mkdir(parents=True)
        (self.root / 'catalogue/i18n').mkdir()
        self.exercise = {'id': '0001', 'name': 'test squat', 'description': 'A test squat.',
                         'instructions': ['Hold for 20-30 seconds.', 'Switch sides.']}
        self.file = self.root / 'catalogue/exercises/0001.json'
        self.file.write_text(json.dumps(self.exercise))
        self.zh = self.root / 'catalogue/i18n/zh.json'
        self.zh.write_text('{}')
        self.q = module.Queue(self.root, self.state)
        self.q.scan()
        self.handlers = {s: signal.getsignal(s) for s in (signal.SIGTERM, signal.SIGINT)}

    def tearDown(self):
        self.q.db.close()
        for s, handler in self.handlers.items():
            signal.signal(s, handler)
        self.temp.cleanup()

    def generated(self, key='0001:description', value='测试深蹲。'):
        self.q.db.execute("UPDATE tasks SET target=?, status='generated' WHERE key=?", (module.encoded(value), key))
        self.q.db.commit()
        return self.q.db.execute('SELECT * FROM tasks WHERE key=?', (key,)).fetchone()

    def approve(self, row):
        self.q.review(row['key'], row['hash'], module.digest(json.loads(row['target'])), 'test reviewer', True, 'Fixture semantics reviewed')

    def test_scan_idempotence_and_existing_preserved(self):
        row = self.generated()
        self.q.scan()
        self.assertEqual(self.q.report()['counts']['generated'], 1)
        self.assertEqual(len(list(self.q.db.execute('SELECT * FROM tasks'))), 3)
        self.assertEqual(self.zh.read_text(), '{}')

    def test_apply_requires_review(self):
        self.generated()
        self.assertEqual(self.q.apply(), 0)
        self.assertEqual(json.loads(self.zh.read_text()), {})

    def test_review_apply_and_source_change(self):
        row = self.generated()
        self.approve(row)
        self.assertEqual(self.q.apply(), 1)
        self.assertEqual(json.loads(self.zh.read_text())['0001']['description'], '测试深蹲。')
        self.exercise['description'] = 'Changed source.'
        self.file.write_text(json.dumps(self.exercise))
        self.q.scan()
        row = self.q.db.execute("SELECT * FROM tasks WHERE key='0001:description'").fetchone()
        self.assertEqual(row['status'], 'existing')
        self.assertIsNone(row['reviewer'])

    def test_edit_after_review_is_not_overwritten(self):
        self.approve(self.generated())
        self.zh.write_text('{"0001":{"description":"用户自己的修改。"}}')
        with self.assertRaises(ValueError):
            self.q.apply()
        self.assertIn('用户自己的修改', self.zh.read_text())

    def test_stale_source_and_target_hashes_cannot_approve(self):
        row = self.generated()
        for source, target in [('stale', module.digest('测试深蹲。')), (row['hash'], 'stale')]:
            with self.assertRaises(ValueError):
                self.q.review(row['key'], source, target, 'reviewer', True, 'checked')

    def test_candidate_import_is_atomic_and_revokes_approval(self):
        row = self.generated()
        self.approve(row)
        with self.assertRaises(ValueError):
            self.q.import_candidates([
                {'key': row['key'], 'source_hash': row['hash'], 'target': '修改草稿。'},
                {'key': row['key'], 'source_hash': 'stale', 'target': '无效草稿。'}])
        self.assertEqual(self.q.db.execute('SELECT status FROM tasks WHERE key=?', (row['key'],)).fetchone()[0], 'approved')
        self.q.import_candidates([{'key': row['key'], 'source_hash': row['hash'], 'target': '修改草稿。'}])
        self.assertEqual(self.q.db.execute('SELECT status FROM tasks WHERE key=?', (row['key'],)).fetchone()[0], 'generated')

    def test_reviewed_correction_can_replace_unchanged_existing_translation(self):
        self.zh.write_text('{"0001":{"description":"旧的译文。"}}')
        self.q.db.execute('DELETE FROM tasks')
        self.q.db.commit()
        self.q.scan()
        row = self.q.db.execute("SELECT * FROM tasks WHERE key='0001:description'").fetchone()
        self.q.import_candidates([{'key': row['key'], 'source_hash': row['hash'], 'target': '正确的译文。'}])
        row = self.q.db.execute("SELECT * FROM tasks WHERE key='0001:description'").fetchone()
        self.approve(row)
        self.assertEqual(self.q.apply(), 1)
        self.assertEqual(json.loads(self.zh.read_text())['0001']['description'], '正确的译文。')

    def test_structural_flags_block_approval(self):
        row = self.generated('0001:instructions', ['保持30秒。'])
        with self.assertRaises(ValueError):
            self.approve(row)
        self.assertIn('step_count_changed', module.checks(json.loads(row['source']), json.loads(row['target'])))
        self.assertIn('placeholders_changed', module.checks('Set {0}', '组数'))

    def test_destination_removal_invalidates_review(self):
        self.approve(self.generated())
        self.q.apply()
        self.zh.write_text('{}')
        self.q.scan()
        self.assertNotIn('applied', self.q.report()['counts'])

    def test_worker_resumes_after_process_termination(self):
        # Kill an actual child during task 2. Task 1 must remain committed, task 2 unclaimed.
        code = '''
import importlib.util, os, sys
spec=importlib.util.spec_from_file_location('worker_module', sys.argv[1])
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
q=m.Queue(sys.argv[2],sys.argv[3])
class Backend:
 n=0
 def translate(self, text):
  self.n+=1
  if self.n==2: os._exit(17)
  return '测试翻译。'
m.run(q,Backend())
'''
        result = subprocess.run([sys.executable, '-c', code, str(SCRIPT), str(self.root), str(self.state)], capture_output=True)
        self.assertEqual(result.returncode, 17)
        self.assertEqual(self.q.report()['counts']['generated'], 1)
        self.assertEqual(self.q.report()['worker']['state'], 'interrupted')
        class Backend:
            def translate(self, text):
                return ['保持20至30秒。', '换边。'] if isinstance(text, list) else '测试翻译。'
        self.assertEqual(module.run(self.q, Backend()), 2)
        self.assertEqual(self.q.report()['counts'], {'generated': 3})
        self.assertEqual(self.q.apply(), 0)

    def test_failures_are_bounded_and_no_provider_secret_is_logged(self):
        class Backend:
            def translate(self, text):
                raise RuntimeError('SENSITIVE_TEST_VALUE')
        module.run(self.q, Backend(), max_attempts=1)
        self.assertEqual(self.q.report()['counts'], {'blocked': 3})
        self.assertTrue(all(row[0] == 'RuntimeError' for row in self.q.db.execute('SELECT error FROM tasks')))

    def test_changed_source_during_translation_discards_old_result(self):
        test = self
        class Backend:
            def translate(self, text):
                test.exercise['description'] = 'New source during inference.'
                test.file.write_text(json.dumps(test.exercise))
                test.q.scan()
                return '旧原文的译文。'
        module.run(self.q, Backend(), limit=1)
        row = self.q.db.execute("SELECT * FROM tasks WHERE key='0001:description'").fetchone()
        self.assertEqual(row['status'], 'pending')
        self.assertIsNone(row['target'])

    def test_only_one_worker_can_write(self):
        import fcntl
        class Backend:
            def translate(self, text):
                raise AssertionError('Must not execute while another worker has the lock')
        with (self.state / 'worker.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                module.run(self.q, Backend())

    def test_state_cannot_be_reused_for_another_checkout(self):
        with self.assertRaises(ValueError):
            module.Queue(self.root.parent, self.state)

    def test_bulk_review_rolls_back_on_stale_item(self):
        first = self.generated()
        second = self.generated('0001:name', '测试深蹲')
        def decision(row):
            return {'key': row['key'], 'source_hash': row['hash'], 'target_hash': module.digest(json.loads(row['target'])),
                    'decision': 'approve', 'reviewer': 'fixture reviewer', 'note': 'Checked fixture meaning'}
        reviews = [decision(first), {**decision(second), 'target_hash': 'stale'}]
        with self.assertRaises(ValueError):
            self.q.review_batch(reviews)
        self.assertEqual(self.q.report()['counts']['generated'], 2)
        self.assertEqual(self.q.db.execute("SELECT COUNT(*) FROM events WHERE event='review'").fetchone()[0], 0)
        with self.assertRaises(ValueError):
            self.q.review_batch([decision(first)] * 101)

    def test_source_conflict_cannot_be_cleared_by_translating_or_approving(self):
        row = self.generated()
        self.q.db.execute("UPDATE tasks SET status='blocked',error='conflicting-source-posture' WHERE key=?", (row['key'],))
        self.q.db.commit()
        with self.assertRaises(ValueError):
            self.approve(row)
        with self.assertRaises(ValueError):
            self.q.import_candidates([{'key': row['key'], 'source_hash': row['hash'], 'target': '另一份译文。'}])
        self.exercise['description'] = 'Corrected English source.'
        self.file.write_text(json.dumps(self.exercise))
        self.q.scan()
        updated = self.q.db.execute('SELECT * FROM tasks WHERE key=?', (row['key'],)).fetchone()
        self.assertIsNone(updated['error'])

    def test_known_source_conflict_is_detected_without_prior_database_history(self):
        original = module.ROOT / 'catalogue/exercises/0240.json'
        fixture = json.loads(original.read_text())
        path = self.root / 'catalogue/exercises/0240.json'
        path.write_text(json.dumps(fixture))
        restored = module.Queue(self.root, self.state.parent / 'restored')
        restored.scan()
        row = restored.db.execute("SELECT * FROM tasks WHERE key='0240:instructions'").fetchone()
        self.assertEqual(row['status'], 'blocked')
        fixture['name'] = 'corrected prone reverse fly'
        path.write_text(json.dumps(fixture))
        restored.scan()
        row = restored.db.execute("SELECT * FROM tasks WHERE key='0240:instructions'").fetchone()
        self.assertEqual(row['status'], 'pending')
        self.assertIsNone(row['error'])
        restored.db.close()

    def test_native_fallback_review_rewrites_only_the_chinese_display_value(self):
        native = self.root / 'frontend/android/app/src/main/java/ch/duartesantos/opengym/NativeWords.java'
        native.parent.mkdir(parents=True)
        native.write_text('class NativeWords { String get(String text) { switch(text) { case "No voice": return "无声音"; default: return text; } } }')
        self.q.scan()
        key = 'native_fallback:' + module.digest('No voice')
        row = self.q.db.execute('SELECT * FROM tasks WHERE key=?', (key,)).fetchone()
        self.q.import_candidates([{'key': key, 'source_hash': row['hash'], 'target': '没有可用的语音'}])
        self.approve(self.q.db.execute('SELECT * FROM tasks WHERE key=?', (key,)).fetchone())
        self.assertEqual(self.q.apply(), 1)
        self.assertIn('case "No voice": return "没有可用的语音";', native.read_text())
        self.assertIn('default: return text;', native.read_text())
        self.q.scan()
        self.assertEqual(self.q.db.execute('SELECT status FROM tasks WHERE key=?', (key,)).fetchone()[0], 'applied')

    def test_calendar_format_requires_explicit_review_of_the_exact_pair(self):
        locale = self.root / 'frontend/src/locales/zh.js'
        locale.parent.mkdir(parents=True)
        locale.write_text('export default {"Jan":"1月"}')
        self.q.scan()
        row = self.q.db.execute('SELECT * FROM tasks WHERE key=?', ('ui:' + module.digest('Jan'),)).fetchone()
        with self.assertRaises(ValueError):
            self.approve(row)
        self.q.review(row['key'], row['hash'], module.digest('1月'), 'calendar reviewer', True,
                      'Jan names the first month; 1月 is the same calendar month.', allow_format=True)
        self.assertEqual(self.q.db.execute('SELECT status FROM tasks WHERE key=?', (row['key'],)).fetchone()[0], 'approved')

    def test_incorrect_month_or_placeholder_cannot_use_a_format_exception(self):
        locale = self.root / 'frontend/src/locales/zh.js'
        locale.parent.mkdir(parents=True)
        locale.write_text('export default {"Jan":"2月", "{0} × {1} on {2}":"{2}：{0} × {0}"}')
        self.q.scan()
        for row in self.q.db.execute("SELECT * FROM tasks WHERE kind='ui'"):
            with self.assertRaises(ValueError):
                self.q.review(row['key'], row['hash'], module.digest(json.loads(row['target'])),
                              'reviewer', True, 'Do not allow a changed month or lost placeholder.', allow_format=True)

    def test_ui_format_exception_never_applies_to_catalogue_fields(self):
        self.exercise['name'] = 'Jan'
        self.file.write_text(json.dumps(self.exercise))
        self.q.scan()
        row = self.generated('0001:name', '1月')
        with self.assertRaises(ValueError):
            self.q.review(row['key'], row['hash'], module.digest('1月'), 'reviewer', True,
                          'Catalogue numbers still require correction.', allow_format=True)

    def test_ui_and_native_use_same_review_and_conflict_rules(self):
        locale = self.root / 'frontend/src/locales/zh.js'
        locale.parent.mkdir(parents=True)
        locale.write_text('// preserve this comment\nexport default {"Hello": "你好", "Other": "其他"}\n')
        source = self.root / 'frontend/android/app/src/main/res/values/strings.xml'
        source.parent.mkdir(parents=True)
        source.write_text('<resources><string name="hint">"Hold for 20 seconds."</string></resources>')
        self.q.scan()
        ui_key = 'ui:' + module.digest('Hello')
        ui = self.q.db.execute('SELECT * FROM tasks WHERE key=?', (ui_key,)).fetchone()
        native = self.q.db.execute("SELECT * FROM tasks WHERE key='native:hint'").fetchone()
        self.q.import_candidates([
            {'key': ui_key, 'source_hash': ui['hash'], 'target': '您好'},
            {'key': 'native:hint', 'source_hash': native['hash'], 'target': '保持20秒。'}])
        for key in [ui_key, 'native:hint']:
            self.approve(self.q.db.execute('SELECT * FROM tasks WHERE key=?', (key,)).fetchone())
        self.assertEqual(self.q.apply(), 2)
        self.assertIn('// preserve this comment', locale.read_text())
        self.assertIn('"Other": "其他"', locale.read_text())
        self.assertIn('您好', locale.read_text())
        self.q.scan()
        self.assertEqual(self.q.db.execute("SELECT status FROM tasks WHERE key='native:hint'").fetchone()[0], 'applied')


if __name__ == '__main__':
    unittest.main()
