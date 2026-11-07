#!/usr/bin/env bash
set -euo pipefail
release_repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
release_apk=${1:?Usage: publish_release.sh /path/to/reviewed-release.apk}
release_apk=$(realpath -- "$release_apk")
cd "$release_repo"
python3 scripts/translation/release_gate.py --apk "$release_apk"
git diff --exit-code
git diff --cached --exit-code
if [ -n "$(git ls-files --others --exclude-standard)" ]; then
    echo 'Commit the reviewed source files before publication.' >&2
    exit 1
fi
release_version=$(node -p 'JSON.parse(require("fs").readFileSync("frontend/chinese-edition.json")).versionName')
release_tag="zh-CN-v$release_version"
release_name="openGym-zh-CN-$release_version-android.apk"
release_dir="/workspace/releases/$release_tag"
mkdir -p "$release_dir"
cp -- "$release_apk" "$release_dir/$release_name"
cd "$release_dir"
sha256sum "$release_name" > "$release_name.sha256"
cp -- "$release_repo/docs/CHINESE_MIGRATION.md" MIGRATION.zh-CN.md
: "${OPENGYM_ZH_RELEASE_NOTES:?Set the path to the reviewed Chinese release notes}"
cp -- "$OPENGYM_ZH_RELEASE_NOTES" RELEASE_NOTES.md
gh api repos/Coney97/openGym- --jq '.permissions.push' | python3 -c 'import sys; assert sys.stdin.read().strip() == "true"'
cd "$release_repo"
git tag -a "$release_tag" -m "Independent Simplified Chinese edition $release_version"
git push origin "HEAD:refs/heads/feature/zh-cn-complete" "refs/tags/$release_tag"
cd "$release_dir"
gh release create "$release_tag" "$release_name" "$release_name.sha256" RELEASE_NOTES.md MIGRATION.zh-CN.md \
    --repo Coney97/openGym- --verify-tag --latest=true \
    --title "openGym 简体中文版 $release_version" --notes-file RELEASE_NOTES.md
verification=$(mktemp -d /workspace/releases/verify-zh-XXXXXX)
gh release download "$release_tag" --repo Coney97/openGym- --dir "$verification" \
    --pattern "$release_name" --pattern "$release_name.sha256"
cd "$verification"
sha256sum -c "$release_name.sha256"
cmp -- "$release_name" "$release_dir/$release_name"
gh release view "$release_tag" --repo Coney97/openGym- --json url,assets,isPrerelease
