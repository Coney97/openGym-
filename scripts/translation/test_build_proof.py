import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('build_proof', Path(__file__).with_name('stamp_build.py'))
proof = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proof)


class BuildProofTests(unittest.TestCase):
    def test_regression_inputs_change_the_fingerprint_but_runtime_data_does_not(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = ['frontend/src/main.jsx', 'api/server.js', 'mcp/src/tools.js',
                     'frontend/android/variables.gradle',
                     'frontend/android/app/src/main/java/App.java',
                     'scripts/translation/reviews/receipt.json']
            for name in files:
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text('original source')
            for name in files:
                before = proof.fingerprint(root)
                (root / name).write_text('changed source')
                self.assertNotEqual(proof.fingerprint(root), before, name)
            before = proof.fingerprint(root)
            for name in ['api/data/session.json', 'mcp/node_modules/package/index.js']:
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text('runtime/dependency cache')
            self.assertEqual(proof.fingerprint(root), before)


if __name__ == '__main__':
    unittest.main()
