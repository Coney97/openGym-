import { afterEach, describe, expect, it, vi } from 'vitest'
import { chineseReleaseVersion, pickChineseRelease, pickChineseApk } from './update.js'

describe('independent Chinese distribution updates', () => {
  afterEach(() => { vi.unstubAllEnvs(); vi.resetModules() })
  it('selects only published stable Chinese releases and compares versions numerically', () => {
    expect(pickChineseRelease([
      { tag_name: 'v9.0.0' }, { tag_name: 'zh-CN-v1.2.0' },
      { tag_name: 'zh-CN-v1.10.0' }, { tag_name: 'zh-CN-v2.0.0', draft: true },
      { tag_name: 'zh-CN-v3.0.0', prerelease: true }
    ]).tag_name).toBe('zh-CN-v1.10.0')
    expect(chineseReleaseVersion('v1.4.4-zh-CN-beta.1')).toBeNull()
    expect(chineseReleaseVersion('zh-CN-v1.0.0-beta.1')).toBeNull()
  })
  it('requires the exact Chinese APK, its checksum and repository download paths', () => {
    const apk = { name: 'openGym-zh-CN-1.0.0-android.apk', browser_download_url: 'https://github.com/Coney97/openGym-/releases/download/zh-CN-v1.0.0/openGym-zh-CN-1.0.0-android.apk' }
    const hash = { name: `${apk.name}.sha256`, browser_download_url: `${apk.browser_download_url}.sha256` }
    expect(pickChineseApk([apk, hash], '1.0.0').apk).toEqual(apk)
    expect(pickChineseApk([apk], '1.0.0').apk).toBeNull()
    expect(pickChineseApk([{ ...apk, browser_download_url: 'https://example.com/file.apk' }, hash], '1.0.0').apk).toBeNull()
    expect(pickChineseApk([{ ...apk, name: 'openGym-1.0.0.apk' }, hash], '1.0.0').apk).toBeNull()
  })
  it('writes and reads Chinese routine and NFC links while keeping upstream links readable', async () => {
    vi.stubEnv('VITE_ZH_CN_EDITION', '1')
    vi.resetModules()
    const { tagUrl, parseTagUrl } = await import('./nfc-tags.js')
    const { linkFor, routinePayloadFromUrl } = await import('./routine-link.js')
    const tag = { kind: 'exercise', id: '0025' }
    expect(tagUrl(tag)).toBe('opengymzh://nfc?ex=0025')
    expect(parseTagUrl(tagUrl(tag))).toEqual(tag)
    expect(parseTagUrl('https://opengym.ch/nfc?ex=0025')).toEqual(tag)
    const payload = '1.j.e30'
    expect(linkFor(payload)).toBe(`opengymzh://r#${payload}`)
    expect(routinePayloadFromUrl(linkFor(payload))).toBe(payload)
    expect(routinePayloadFromUrl(`https://opengym.ch/r#${payload}`)).toBe(payload)
    expect(parseTagUrl('opengym://nfc?ex=0025')).toBeNull()
    expect(routinePayloadFromUrl(`opengym://r#${payload}`)).toBeNull()
  })
})
