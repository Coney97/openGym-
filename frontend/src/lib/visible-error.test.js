import { afterEach, describe, expect, it, vi } from 'vitest'

describe('Chinese remote error display', () => {
  afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); vi.resetModules() })
  async function chinese() {
    vi.stubEnv('VITE_ZH_CN_EDITION', '1'); vi.resetModules()
    const { _setLangState } = await import('./i18n-core.js')
    const zh = (await import('../locales-extra/zh.js')).default
    _setLangState('zh', zh, null, null, false, false)
    return import('./visible-error.js')
  }
  it('translates a known refusal and preserves incoming Chinese explanations', async () => {
    const { visibleError } = await chinese()
    expect(visibleError('only the owner can do this', 403)).toBe('只有所有者可以执行此操作')
    expect(visibleError('请先保存计划', 400)).toBe('请先保存计划')
  })
  it('gives a Chinese explanation for unknown remote diagnostics without modifying the response', async () => {
    const { visibleError } = await chinese()
    const response = { error: 'private provider diagnostic', code: 'provider' }
    expect(visibleError(response.error, 429)).toBe('请求过于频繁，请稍后重试。')
    expect(visibleError(response.error, 503)).toContain('服务器')
    expect(response).toEqual({ error: 'private provider diagnostic', code: 'provider' })
  })
  it('preserves the original error on ordinary builds', async () => {
    vi.stubEnv('VITE_ZH_CN_EDITION', '0'); vi.resetModules()
    const { visibleError } = await import('./visible-error.js')
    expect(visibleError('provider refused', 403)).toBe('provider refused')
  })
  it('keeps API status and diagnostic data when localizing an actual failed request', async () => {
    await chinese()
    const data = { error: 'provider-specific reason', code: 'provider' }
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, status: 403, json: async () => data })))
    const { api } = await import('./api.js')
    await expect(api('/api/test')).rejects.toMatchObject({
      status: 403, data, message: '你没有执行此操作的权限。',
    })
  })
})
