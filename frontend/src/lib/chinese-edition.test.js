import { afterEach, describe, expect, it, vi } from 'vitest'
import { effectiveLang } from './default-lang.js'

describe('Simplified Chinese edition', () => {
  afterEach(() => vi.unstubAllEnvs())
  it('uses Simplified Chinese even for an existing profile or a different device language', () => {
    vi.stubEnv('VITE_ZH_CN_EDITION', '1')
    expect(effectiveLang({ lang: 'en' }, { default_lang: 'fr' }, ['de'])).toBe('zh')
    expect(effectiveLang({ lang: 'zh-TW', langAuto: true }, null, ['en'])).toBe('zh')
  })
})
