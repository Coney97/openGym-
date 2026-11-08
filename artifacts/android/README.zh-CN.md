# Android 安装包

已在云环境中生成 `openGym-zh-CN-1.0.0-candidate-20261108.apk`。本目录保存构建和校验记录；APK 尚未上传到 GitHub。

此包由提交 `dd391d28d9b7f936bb3836c372219f5c0699d0b1` 在云端构建，仅包含 Android 手机应用。应用名称为“openGym 简体中文版”，包名为 `io.github.coney97.opengym.zh`，内部版本 `1.0.0`、版本代码 `1`，使用独立正式签名，可与原版及旧 Beta 并存。

- APK 大小：229559865 字节，约 219 MiB。
- [独立 SHA-256 校验文件](openGym-zh-CN-1.0.0-candidate-20261108.apk.sha256)。
- [构建及核验记录](BUILD_INFO.zh-CN.json)：源码指纹、公开签名证书指纹和本次实际执行的 50 项 Android 单元测试结果。
- [数据迁移说明](../../docs/CHINESE_MIGRATION.md)：先从原版或 Beta 导出备份，保留原应用和备份文件。

**当前为测试候选，完整汉化和语义审校尚未完成。** 本次构建、50 项 Android 单元测试、签名、包名、版本、ZIP 对齐及源码指纹检查均通过。云端 Android 软件模拟器此前发生系统 WebView 崩溃，原生启动及完整功能验收尚未通过；不要将单元测试或成功打包当作运行验收结果。

## 安装包位置与上传状态

云端仓库内的文件位于 `frontend/android/app/build/outputs/apk/sideload/release/openGym-zh-CN-1.0.0-candidate-20261108.apk`，另在 `/workspace/releases/zh-CN-v1.0.0-candidate-20261108/` 保留一份。构建日志与校验文件同样保存在该云端目录中。

已实际尝试将此 APK 通过 Git LFS 上传到仓库。GitHub 返回：`@Coney97 can not upload new objects to public fork Coney97/openGym-`。推送被拒绝，仓库没有发布对应 LFS 指针。APK 超过 GitHub 普通单文件的 100 MiB 限制，因此构建文件保持在云端，等待作为 Releases 附件发布。

GitHub Releases 上传仍需要云环境的实际网络策略放行 `api.github.com` 和 `uploads.github.com`；此前这两个域名仅保存在配置草稿中。当前未创建此构建对应的 Release。

正式稳定版仍需满足完整汉化和功能验收门槛。
