// Localize the pre-bundle error screen too: locale packs cannot help when JS fails to load.
export function chineseHtml(html, name = 'openGym 简体中文版') {
  const messages = {
    'Reloading often helps. If it keeps happening, please send us this:': "重新加载通常可以解决问题。如果问题持续，请提供以下诊断信息：",
    'No error, it just never finished loading.': "未捕获到错误，但加载未能完成。",
    'Reload': "重新加载",
    'openGym could not start on this browser.': "openGym 无法在当前环境中启动。",
    'openGym is taking too long to start.': "openGym 启动耗时过长。",
    'Could not load ': "无法加载：",
    'a script': "脚本文件",
    'Personal gym & body weight tracker': "个人健身与体重记录工具"
  }
  let output = html.replace('<html lang="en">', '<html lang="zh-CN">')
    .replace(/var l = s\.lang[^\n]*;/, "var l = 'zh-CN';")
    .replace('<title>openGym</title>', `<title>${name}</title>`)
  for (const [source, target] of Object.entries(messages)) output = output.replaceAll(source, target)
  return output
}
