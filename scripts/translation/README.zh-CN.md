# 云端简体中文翻译工作流

任务状态存放在 `/workspace/translation-state/`，与应用源码分离。SQLite 每项提交，保留原文哈希、译文、重试次数、检查结果、审核人和事件记录。不要删除此目录；云机器重启后需要重新启动进程。模型和运行环境分别位于 `/workspace/translation-model/en-zh` 和 `/workspace/translation-venv`。

## 当前状态与网络要求

本地推理引擎已经安装；官方英译中文模型尚未下载。官方目录指向 `https://argos-net.com/v1/translate-en_zh-1_9.argosmodel`，当前云环境返回 HTTP 403。已将 `argos-net.com` 加入环境配置草稿，需在环境设置中审核并保存。模型在本机 CPU 上运行，不需要 API 密钥；不会向外部翻译服务发送动作文本。正式生成任务目前没有启动。

只读取动作文本；不读取、修改或上传动作图片和视频。所有现有译文都会保留，但标记为 `existing` 而非自动审校通过。

## 安装与运行

在 `/workspace/openGym-` 执行：

```bash
python3 -m venv /workspace/translation-venv
/workspace/translation-venv/bin/pip install -r scripts/translation/requirements.txt
python3 scripts/translation/workflow.py scan
node scripts/translation/audit.mjs
# 网络配置实际生效后才下载模型，保持 TLS 校验：
python3 scripts/translation/install_model.py
# 先进行有限批次，检查输出质量和速度：
/workspace/translation-venv/bin/python scripts/translation/workflow.py run --limit 10
```

确认有限批次质量后，运行剩余任务：

```bash
/workspace/translation-venv/bin/python scripts/translation/workflow.py start
python3 scripts/translation/workflow.py status
python3 scripts/translation/workflow.py export /workspace/translation-state/review.json --status generated
```

`start` 使用独立进程组和文件日志，父命令结束不影响它；不保证能抵抗云机器销毁或平台回收。一次只允许一个 worker。进程被终止后，已提交的结果保留，未提交任务会再次运行。新机器启动后再次执行 `start`，跳过已经生成的任务。`worker.json` 是最后报告状态，不保证进程仍存活；结合进程 PID、日志及状态计数判断。

普通调用失败最多重试三次；此后标记 `blocked`。不会无限请求失败服务。状态为 `retry` 的任务会按退避时间重试；不要手动修改数据库消除检查标记。

## 审校与应用

`generated` 只是草稿。检查器只验证步骤数量、非空、中文字符、数字和占位符，不证明动作含义正确。必须对照原文，审查动作方向、部位、器材、姿势、幅度、时长、单位、左右侧和安全提示；英文人名、品牌和单位需要单独判断。不要用通用套话替代具体动作步骤。

导出文件每项包含原文 `source`、译文 `target`、原文 `hash` 和译文 `target_hash`。审核命令绑定两份哈希，不能对另一版本误审批：

```bash
python3 scripts/translation/workflow.py review 1006:description \
  --source-hash <导出的原文哈希> --target-hash <导出的译文哈希> \
  --reviewer <审核人> --note <实际审校结论>
# --reject 将该项标记 blocked，待纠正。
python3 scripts/translation/workflow.py apply
node scripts/catalogue/validate.mjs
node scripts/catalogue/build.mjs
```

`apply` 仅将已审批的目录字段写入 `catalogue/i18n/zh.json`；会备份原始文件，不覆盖现有的不同译文。现有译文与新译文冲突需要明确处理，不能覆盖用户修改。源文本或已应用译文变化后，重新扫描会要求重新审核。

修正草稿时，准备 JSON 数组，每项为 `{"key":"动作编号:字段","source_hash":"导出的hash","target":"修正后的译文"}`；步骤字段的 `target` 是字符串数组。执行 `workflow.py import <文件>` 后回到 `generated`，必须重新审核。已存在译文可用同样方式纠正；仅当应用端仍与扫描时相同才会写入，期间用户的修改会阻止覆盖。

`audit.json` 包含界面及 Android 原生候选。混合中英文、品牌、内部标识都可能出现，候选不等于实际漏洞；扫描也不能覆盖所有动态字符串。按候选的内容哈希建立 `audit-decisions.json`，仅对确认为应保留的术语填写 `{"候选id":{"action":"accept","reviewer":"审核人","reason":"保留原因"}}`。真正的遗漏应修正源码并重新扫描，而不是批量接受。

## APK 交付条件

不能将队列清空或结构检查通过等同于完成。所有目录项必须有审核记录；所有静态候选必须处理；需要检查 Android 实际页面、错误弹窗、通知、导出、离线训练和数据保存。完整前端/API/MCP、计算及 Android 单元测试均需完成。

`bash scripts/translation/build_android.sh` 只构建 Android 手机调试包，不构建 iOS 或手表。它将源文件指纹写入 APK，防止把旧包当成新译文的产物。保留环境的 Java 代理和 CA 配置；本环境构建时可使用已验证的 `JAVA_TOOL_OPTIONS` 代理参数。调试包为独立测试包名和调试签名，需要正式发布签名时另行配置，不冒充原版升级包。

```bash
python3 scripts/translation/release_gate.py --apk <APK路径>
```

门槛检查会默认失败，直到译文审核、静态候选和验收记录都完成。`acceptance.json` 须绑定 APK 的 SHA-256，在 `checks` 下记录每项的 `status: passed`、`reviewer`、`evidence`。检查项为 `frontend_suite`、`api_suite`、`mcp_suite`、`training_calculations`、`android_unit_tests`、`apk_signature`、`android_install_launch`、`android_chinese_screens`、`android_offline_workout`、`android_notifications`。这些是实际执行证据，不是自动填写的通行证。

测试队列自身：`python3 -m unittest discover -s scripts/translation -p 'test_*.py' -v`。
