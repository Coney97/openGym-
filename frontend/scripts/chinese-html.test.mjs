import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { chineseHtml } from './chinese-html.mjs'

describe('Chinese first paint and boot failure messages', () => {
  it('overrides a saved foreign language before rendering and localizes reload/error text', () => {
    const source = readFileSync(new URL('../index.html', import.meta.url), 'utf8')
    const html = chineseHtml(source)
    expect(html).toContain('<html lang="zh-CN">')
    expect(html).toContain("var l = 'zh-CN';")
    expect(html).toContain('<title>openGym 简体中文版</title>')
    expect(html).toContain("r.textContent = '重新加载'")
    expect(html).not.toContain('openGym could not start on this browser.')
    expect(html).not.toContain('Personal gym & body weight tracker')
    expect(source).toContain('<html lang="en">')
  })
})
