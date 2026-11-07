package ch.duartesantos.opengym;

/** Chinese fallbacks used before the WebView has supplied translated notification/widget text. */
final class NativeWords {
    static String get(String text) {
        return BuildConfig.CHINESE_EDITION ? chinese(text) : text;
    }

    static String chinese(String text) {
        if (text == null) return null;
        switch (text) {
            case "Rest": return "休息";
            case "Rest over": return "休息结束";
            case "Rest’s over. Next set!": return "休息结束，开始下一组！";
            case "Pause": return "暂停";
            case "Resume": return "继续";
            case "Skip": return "跳过";
            case "− 15s": return "− 15秒";
            case "+ 15s": return "+ 15秒";
            case "Checking if you made it to the gym": return "正在确认你是否已到达健身房";
            case "Weight goal": return "体重目标";
            case "No weigh-ins yet": return "尚无体重记录";
            case "This week": return "本周";
            case "Next workout": return "下次训练";
            case "Nothing planned": return "暂无计划";
            case "Today": return "今天";
            case "Records": return "个人纪录";
            case "Volume": return "训练量";
            case "Challenges": return "挑战";
            case "Week streak": return "连续训练周数";
            case "config is required": return "缺少必要配置";
            case "location not allowed": return "未授予位置权限";
            case "no location service": return "位置服务不可用";
            case "location is switched off": return "位置服务已关闭";
            case "no fix": return "暂时无法确定当前位置";
            case "this folder cannot be kept for later writes": return "无法保留此文件夹的后续写入权限";
            case "uri, name and data are required": return "缺少文件位置、名称或数据";
            case "not a backup file name": return "备份文件名无效";
            case "this folder is not one the app may write to": return "应用没有此文件夹的写入权限";
            case "could not write to the backup folder: ": return "无法写入备份文件夹：";
            case "uri, pattern and keep are required": return "缺少文件夹位置、匹配规则或保留数量";
            case "html is required": return "缺少要打印的内容";
            case "printing is not available on this device": return "此设备不支持打印";
            case "json is required": return "缺少必要数据";
            case "could not write the widget data": return "无法保存小组件数据";
            case "unknown icon": return "未知的应用图标";
            case "Health Connect is not available": return "健康连接不可用";
            case "from and to are needed": return "请提供开始和结束时间";
            case "since is needed": return "请提供起始时间";
            case "url is required": return "请提供有效链接";
            case "this phone has no NFC": return "此手机不支持近场通信";
            case "NFC is disabled": return "近场通信已关闭";
            case "no screen lock": return "尚未设置屏幕锁定";
            case "cancelled": return "已取消";
            case "server is required": return "请提供服务器地址";
            case "could not keep the check": return "无法保存后台检查任务";
            case "no context": return "应用运行环境暂不可用";
            case "at must be in the future": return "提醒时间必须晚于当前时间";
            case "nothing to say": return "没有可播报的内容";
            case "no voice": return "没有可用的语音";
            case "asset packs are not available on Android yet": return "此安装方式不支持下载额外资源包";
            case "not downloaded": return "尚未下载";
            case "replaced by a newer write": return "已由新的写入任务替代";
            case "the sticker is read-only": return "此贴纸为只读，无法写入";
            case "the sticker is too small": return "此贴纸的存储空间不足";
            case "the sticker cannot hold NDEF": return "此贴纸不支持所需的数据格式";
            case "the folder refused a new file": return "文件夹不允许新建文件";
            case "the file cannot be opened for writing": return "无法打开文件进行写入";
            case "could not switch the launcher icon": return "无法更换应用图标";
            case "Confirm it's you": return "请验证你的身份";
            case "Gym spotted": return "已到达健身房";
            case "Ready for your workout? 💪": return "准备好开始训练了吗？💪";
            case "Gym reminder": return "健身房提醒";
            case "not an update file name": return "更新文件名无效";
            case "sha256 is required": return "缺少下载文件的SHA-256校验值";
            case "APK file not found": return "未找到安装包";
            case "SHA-256 mismatch: the download may be corrupted or tampered with": return "SHA-256校验值不匹配，下载文件可能已损坏或被修改";
            case "Could not check the download": return "无法校验下载文件，请重新下载";
            case "Update package identity, signature or version is invalid": return "安装包的应用身份、签名或版本不符合中文版更新要求";
            case "Could not verify update identity": return "无法验证安装包身份，请稍后重试";
            default: return text;
        }
    }
}
