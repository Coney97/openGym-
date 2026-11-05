#!/usr/bin/env bash
# Build only the Android phone app. Requires reviewed/applied translations for final release.
set -euo pipefail
translation_repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$translation_repo"
node scripts/catalogue/validate.mjs
node scripts/catalogue/build.mjs --check
cd frontend
VITE_MOBILE=1 VITE_ZH_CN_EDITION=1 npm run build
node ../scripts/catalogue/stage-media.mjs dist
python3 ../scripts/translation/stamp_build.py
npx --no-install cap sync android
node scripts/check-mobile-bundle.mjs
cd android
export JAVA_HOME="${JAVA_HOME:-/workspace/jdk21}"
export ANDROID_HOME="${ANDROID_HOME:-/workspace/android-sdk}"
./gradlew --no-daemon --max-workers=2 :app:testSideloadDebugUnitTest :app:assembleSideloadDebug "$@"
# The resulting debug-signed APK is a candidate. This script does not label it final.
