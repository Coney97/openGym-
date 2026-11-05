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


if __name__ == '__main__':
    unittest.main()
