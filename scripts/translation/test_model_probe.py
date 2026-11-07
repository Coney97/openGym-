import json
from pathlib import Path
import tempfile
import unittest
from probe_model import probe
from workflow import digest


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        for name in ['catalogue/exercises', 'catalogue/i18n', 'scripts/translation']:
            (self.root / name).mkdir(parents=True)
        self.source = ['Hold for 20-60 seconds.']
        self.target = ['保持20-60秒。']
        (self.root / 'catalogue/exercises/0001.json').write_text(json.dumps({'instructions': self.source}))
        (self.root / 'catalogue/i18n/zh.json').write_text(json.dumps({'0001': {'instructions': self.target}}))
        (self.root / 'scripts/translation/representative-samples.json').write_text(json.dumps([
            {'id': '0001', 'category': 'static_hold', 'fields': {'instructions': {
                'source_hash': digest(self.source), 'reviewed_target_hash': digest(self.target), 'review_focus': 'Duration and posture.'}}}]))

    def tearDown(self):
        self.directory.cleanup()

    def test_drafts_cannot_approve_or_overwrite_the_reference(self):
        class Backend:
            def translate(self, source):
                return ['保持30秒。']
        before = {str(file.relative_to(self.root)): file.read_bytes() for file in self.root.rglob('*') if file.is_file()}
        result = probe(self.root, Backend())
        self.assertFalse(result['semantic_approval'])
        self.assertEqual(result['drafts'][0]['semantic_review'], 'required')
        self.assertIn('numbers_changed', result['drafts'][0]['issues'])
        self.assertEqual(json.loads((self.root / 'catalogue/i18n/zh.json').read_text())['0001']['instructions'], self.target)
        self.assertEqual({str(file.relative_to(self.root)): file.read_bytes() for file in self.root.rglob('*') if file.is_file()}, before)

    def test_changed_reference_is_rejected_before_model_execution(self):
        class Backend:
            def translate(self, source):
                raise AssertionError('must not execute')
        (self.root / 'catalogue/exercises/0001.json').write_text(json.dumps({'instructions': ['Changed.']}))
        with self.assertRaises(ValueError):
            probe(self.root, Backend())

    def test_failed_probe_is_bounded_to_three_attempts(self):
        class Backend:
            calls = 0
            def translate(self, source):
                self.calls += 1
                raise RuntimeError('provider error')
        backend = Backend()
        result = probe(self.root, backend)
        self.assertEqual(backend.calls, 3)
        self.assertEqual(result['drafts'][0]['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
