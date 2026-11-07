import { afterEach, describe, expect, it, vi } from 'vitest'

describe('Chinese names for newly created starter plans', () => {
  afterEach(() => { vi.unstubAllEnvs(); vi.resetModules() })
  it('localizes new routine names and preserves the training prescription', async () => {
    vi.stubEnv('VITE_ZH_CN_EDITION', '1'); vi.resetModules()
    const { _setLangState } = await import('./i18n-core.js')
    const zh = (await import('../locales-extra/zh.js')).default
    _setLangState('zh', zh, null, null, false, false)
    const { buildStarterPlan, buildStarterProgramme } = await import('./starter.js')
    const plan = buildStarterPlan('full-body')
    expect(plan.routines.map(r => r.name)).toEqual(['全身训练一', '全身训练二', '全身训练三'])
    expect(plan.routines[0].ex).toEqual([
      { id: '0043', sets: 3, reps: 8, weight: 0 }, { id: '0025', sets: 3, reps: 8, weight: 0 },
      { id: '2330', sets: 3, reps: 10, weight: 0 }, { id: '0586', sets: 3, reps: 12, weight: 0 },
      { id: '0334', sets: 2, reps: 12, weight: 0 }, { id: '0031', sets: 2, reps: 12, weight: 0 },
    ])
    expect(plan.schedule.map(d => d.day)).toEqual([1, 3, 5])
    expect(plan.schedule.map(d => d.routineId)).toEqual(plan.routines.map(r => r.id))
    const programme = buildStarterProgramme('strength-4', '我的阶段计划', 123)
    expect(programme.programme.name).toBe('我的阶段计划')
    expect(programme.routines.map(r => r.name)).toEqual(['5×5训练一', '5×5训练二', '5×5训练三'])
    expect(programme.programme.weeks[0].t['0043'].pct).toBe(72.5)
    expect(programme.programme.weeks[3].deload).toBe(true)
  })
})
