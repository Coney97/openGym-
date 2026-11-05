#!/usr/bin/env bash
# Upload a prepared beta only after GitHub API access is available.
set -euo pipefail
beta_dir=${1:?Usage: publish_beta.sh /workspace/releases/openGym-1.4.4-zh-CN-beta.1}
beta_dir=$(cd -- "$beta_dir" && pwd)
beta_tag=v1.4.4-zh-CN-beta.1
beta_repo=Coney97/openGym-
beta_apk=openGym-1.4.4-zh-CN-beta.1-android.apk
cd "$beta_dir"
sha256sum -c SHA256SUMS
gh api "repos/$beta_repo" --jq '.permissions.push' | python3 -c 'import sys; assert sys.stdin.read().strip() == "true", "Repository write permission required"'
# Refuse to alter an existing release or overwrite its attachments.
gh release create "$beta_tag" "$beta_apk" SHA256SUMS \
  --repo "$beta_repo" --verify-tag --prerelease --latest=false \
  --title 'openGym 简体中文 Beta 1（汉化进行中）' \
  --notes-file RELEASE_NOTES.md
gh release view "$beta_tag" --repo "$beta_repo" --json url,assets,isPrerelease
