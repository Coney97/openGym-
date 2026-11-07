#!/usr/bin/env bash
# Build only the Android phone app. Requires reviewed/applied translations for final release.
set -euo pipefail
translation_repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
translation_variant=${ZH_BUILD_TYPE:-debug}
case "$translation_variant" in debug|release) ;; *) echo 'ZH_BUILD_TYPE must be debug or release' >&2; exit 1;; esac
cd "$translation_repo"
export VITE_MOBILE=1 VITE_ZH_CN_EDITION=1
node scripts/catalogue/validate.mjs
node scripts/catalogue/build.mjs --check
cd frontend
npm run build
node ../scripts/catalogue/stage-media.mjs dist
npx --no-install cap sync android
# Sync generates Gradle configuration included in the proof. Stamp after it, then copy only
# the proof into the already-synced assets so the APK and current inputs have the same hash.
python3 ../scripts/translation/stamp_build.py
cp -- dist/translation-build.json android/app/src/main/assets/public/translation-build.json
node scripts/check-mobile-bundle.mjs
cd android
export JAVA_HOME="${JAVA_HOME:-/workspace/jdk21}"
export ANDROID_HOME="${ANDROID_HOME:-/workspace/android-sdk}"
if [ "$translation_variant" = release ]; then
    : "${OPENGYM_ZH_SIGNING_PROPERTIES:?Set the private Chinese release signing configuration}"
    ./gradlew --no-daemon --max-workers=2 -PchineseEdition=true :app:testSideloadReleaseUnitTest :app:assembleSideloadRelease "$@"
else
    ./gradlew --no-daemon --max-workers=2 -PchineseEdition=true :app:testSideloadDebugUnitTest :app:assembleSideloadDebug "$@"
fi
# A signed APK remains a candidate until the release gate and actual acceptance pass.
