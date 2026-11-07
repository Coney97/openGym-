#!/usr/bin/env python3
"""Create the independent Chinese release key, never writing it into the checkout."""
import os
from pathlib import Path
import secrets
import subprocess

DIRECTORY = Path('/workspace/signing')
STORE = DIRECTORY / 'opengym-zh-release.p12'
PROPERTIES = DIRECTORY / 'opengym-zh-release.properties'

def main():
    DIRECTORY.mkdir(mode=0o700, parents=True, exist_ok=True)
    DIRECTORY.chmod(0o700)
    if STORE.exists() or PROPERTIES.exists():
        if not STORE.exists() or not PROPERTIES.exists():
            raise SystemExit('Incomplete signing files; inspect and recover, do not overwrite.')
        print('Existing Chinese release signing configuration retained:', PROPERTIES)
        return
    password = secrets.token_hex(32)
    env = {**os.environ, 'OPENGYM_ZH_STORE_PASSWORD': password}
    subprocess.run(['/workspace/jdk21/bin/keytool', '-genkeypair', '-noprompt',
                    '-keystore', str(STORE), '-storetype', 'PKCS12',
                    '-storepass:env', 'OPENGYM_ZH_STORE_PASSWORD', '-keypass:env', 'OPENGYM_ZH_STORE_PASSWORD',
                    '-alias', 'opengym-zh', '-keyalg', 'RSA', '-keysize', '3072', '-validity', '10000',
                    '-dname', 'CN=openGym Chinese Edition, OU=Independent Distribution'],
                   env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
    STORE.chmod(0o600)
    with PROPERTIES.open('x') as output:
        PROPERTIES.chmod(0o600)
        output.write(f'storeFile={STORE}\nstorePassword={password}\nkeyAlias=opengym-zh\nkeyPassword={password}\n')
    print('Created private signing configuration:', PROPERTIES)

if __name__ == '__main__':
    main()
