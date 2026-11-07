import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('release_gate', Path(__file__).with_name('release_gate.py'))
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class ReleaseIdentityTests(unittest.TestCase):
    edition = {'appId': 'io.github.coney97.opengym.zh', 'versionCode': 1, 'versionName': '1.0.0'}

    def test_compile_sdk_codename_does_not_replace_the_application_name(self):
        badging = "package: name='io.github.coney97.opengym.zh' versionCode='1' versionName='1.0.0' platformBuildVersionName='16' platformBuildVersionCode='36' compileSdkVersion='36' compileSdkVersionCodename='16'\n"
        self.assertTrue(gate.package_matches(badging, self.edition))

    def test_foreign_beta_wrong_versions_and_invalid_badging_are_rejected(self):
        for badging in [
            "package: name='ch.duartesantos.opengym.test' versionCode='32' versionName='1.4.4-zh-CN-beta.1'",
            "package: name='io.github.coney97.opengym.zh' versionCode='2' versionName='1.0.0'",
            "package: name='io.github.coney97.opengym.zh' versionCode='1' versionName='1.1.0'",
            "not a package: name='io.github.coney97.opengym.zh' versionCode='1' versionName='1.0.0'",
            '',
        ]:
            self.assertFalse(gate.package_matches(badging, self.edition), badging)


if __name__ == '__main__':
    unittest.main()
