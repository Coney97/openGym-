# Android 安装包

[下载完整 ZIP 安装包](https://github.com/Coney97/openGym-/archive/7aaae66a4f11259fff3a622d1da4b824204f650b.zip)。安装包已通过普通 Git 分片发布到专用下载分支。ZIP 中包含原 APK 的全部分片和中文离线合并页面。

## 获取 APK

1. 等待 ZIP 下载完成，解压全部文件。
2. 在浏览器打开解压后的 **生成APK.html**，选中同目录下的五个 `part01` 至 `part05` 分片。
3. 点击“校验并生成”，校验完成后点击“下载 APK 安装包”，再从系统下载目录打开并安装。

页面完全离线运行，逐个校验 SHA-256，固定合并顺序；文件缺失、大小不符或内容损坏时不会生成下载链接。若手机文件管理器只显示 HTML 预览，请使用支持本地网页的浏览器打开。不要把分片直接改名为 APK。

此包由提交 `dd391d28d9b7f936bb3836c372219f5c0699d0b1` 在云端构建，仅包含 Android 手机应用。应用名称为“openGym 简体中文版”，包名为 `io.github.coney97.opengym.zh`，内部版本 `1.0.0`、版本代码 `1`，使用独立正式签名，可与原版及旧 Beta 并存。

- APK 大小：229559865 字节，约 219 MiB。
- [独立 SHA-256 校验文件](openGym-zh-CN-1.0.0-candidate-20261108.apk.sha256)。
- [构建及核验记录](BUILD_INFO.zh-CN.json)：源码指纹、公开签名证书指纹和本次实际执行的 50 项 Android 单元测试结果。
- [GitHub 下载复核记录](GITHUB_DOWNLOAD_VERIFICATION.zh-CN.json)：完整 ZIP 已实际下载，五个分片均通过校验，还原 APK 的大小、SHA-256 和独立签名均与原包一致。
- [数据迁移说明](../../docs/CHINESE_MIGRATION.md)：先从原版或 Beta 导出备份，保留原应用和备份文件。

**当前为测试候选，完整汉化和语义审校尚未完成。** 本次构建、50 项 Android 单元测试、签名、包名、版本、ZIP 对齐及源码指纹检查均通过。云端 Android 软件模拟器此前发生系统 WebView 崩溃，原生启动及完整功能验收尚未通过；不要将单元测试或成功打包当作运行验收结果。

## 安装包位置与上传状态

云端仓库内的文件位于 `frontend/android/app/build/outputs/apk/sideload/release/openGym-zh-CN-1.0.0-candidate-20261108.apk`，另在 `/workspace/releases/zh-CN-v1.0.0-candidate-20261108/` 保留一份。构建日志与校验文件同样保存在该云端目录中。

Git LFS 上传被 GitHub 的公共 Fork 限制拒绝。现在已将同一个签名 APK 分成五个低于普通 Git 单文件大小上限的分片，存放于独立的 `apk-download-20261108` 分支，提供 GitHub 的标准 ZIP 下载。分片合并后与原 APK 逐字节一致，没有改变签名或移除动作媒体。

离线合并页已在云端 Chromium 的手机视口中验证缺失、乱序、损坏、大小不符及实际下载；恢复出的 APK 哈希与原包一致。云端浏览器策略禁止 `file://` 导航，因此测试使用相同 HTML 的离线夹具，不能声称已完成真实安卓手机的本地文件打开测试。详细记录见下载包中的 `DOWNLOAD_VALIDATION.zh-CN.json`。

GitHub Releases 上传仍需要云环境的实际网络策略放行 `api.github.com` 和 `uploads.github.com`；此前这两个域名仅保存在配置草稿中。当前未创建此构建对应的 Release。

正式稳定版仍需满足完整汉化和功能验收门槛。
