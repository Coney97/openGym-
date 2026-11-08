# 独立简体中文版测试候选资料

本目录保存当前 Android 候选版的发布资料。拟用标签为 `zh-CN-v1.0.0-beta.1`，APK 内部版本为 `1.0.0`，版本代码为 `1`。**资料入库不代表 GitHub Release 已发布，也不代表汉化或 Android 功能验收已经完成。**

## 文件

- [中文发布说明](RELEASE_NOTES.zh-CN.md)：当前覆盖范围、测试结果和已知限制。
- [中文迁移说明](MIGRATION.zh-CN.md)：通过 JSON 或含媒体 ZIP 从原版及旧 Beta 迁移。
- [APK 校验文件](openGym-zh-CN-1.0.0-candidate.apk.sha256)：精确对应当前候选 APK。
- [候选版清单](artifact.json)：APK 字节数、SHA-256、包名、版本、公开签名证书指纹和源码提交。

APK 对应源码提交为 `2db6fb778dabffebbd32c2ca53bb827a7d6e27b3`。构建完成后的资料提交不会改变该 APK 的来源记录。

## 待发布状态

APK 约 219 MiB，保存在云环境的 `/workspace/releases/zh-CN-v1.0.0-candidate-20261107/`，应作为 GitHub Releases 附件分发。仓库仅记录发布资料和校验信息。正式签名私钥保留在云端签名目录，不进入仓库或发行附件。

截至 2026-11-08，Git 操作可以访问本仓库；Releases API 的连接被云端代理以 HTTP 403 拦截，实际网络策略尚未应用配置草稿中的 `api.github.com` 和 `uploads.github.com`。网络配置生效后，继续上传上述精确 APK，标记为预发布，不设为最新稳定版。上传后必须下载附件再次核对 SHA-256；完成后更新本目录中的发布状态。

云端候选目录中已准备 `publish_prerelease.py`，支持只检查本地资料、恢复缺失附件和下载复核。发布前重新检查远端同名标签及附件，不能覆盖来源不一致的内容。

稳定标签 `zh-CN-v1.0.0` 仍须等待全部汉化、语义审核及 Android 实际功能验收通过。
