import { afterEach, describe, expect, it, vi } from 'vitest'

describe('Beta backup migration into the independent Chinese app', () => {
  afterEach(() => { vi.unstubAllEnvs(); vi.resetModules() })
  const betaState = () => ({
    lang: 'en', unit: 'lb', routines: [{ id: 'r1', name: 'My own routine', ex: [{ id: '0025', sets: 3, reps: 8 }] }],
    workouts: [{ id: 'w1', name: 'My own workout', d: '2026-11-05', entries: [{ id: '0025', sets: [{ w: 135, r: 8 }] }] }],
    bodyweight: [{ d: '2026-11-05', w: 180 }], customEx: [],
  })
  it('imports JSON without changing weights, IDs or user-authored names; the interface uses Chinese', async () => {
    vi.stubEnv('VITE_ZH_CN_EDITION', '1')
    vi.resetModules()
    const { readBackupFile } = await import('./backup-media.js')
    const { effectiveLang } = await import('./default-lang.js')
    const original = betaState()
    const { state } = await readBackupFile(new Blob([JSON.stringify(original)], { type: 'application/json' }))
    expect(state).toEqual(original)
    expect(effectiveLang(state, null, ['en-US'])).toBe('zh')
  })
  it('round-trips ZIP backups with original data and a Chinese migration guide', async () => {
    vi.stubEnv('VITE_ZH_CN_EDITION', '1')
    vi.resetModules()
    const { exportBackupZip, readBackupFile } = await import('./backup-media.js')
    const { readZip } = await import('./zip.js')
    const original = betaState()
    const { createMediaStore, memoryBackend } = await import('./media-store.js')
    const { jpeg } = await import('./media-samples.test-util.js')
    const { sha256Hex } = await import('./sha256.js')
    const photo = jpeg()
    const hash = await sha256Hex(photo)
    original.customEx = [{ id: 'custom-1', n: 'My own photo exercise', media: { kind: 'image', hash, mime: 'image/jpeg', size: photo.length, width: 4, height: 3, at: 1 } }]
    const media = createMediaStore(memoryBackend())
    await media.put(hash, new Blob([photo]), { mime: 'image/jpeg' })
    const { blob } = await exportBackupZip(original, { media })
    const restored = await readBackupFile(blob)
    expect(restored.state).toEqual(original)
    expect(restored.files).toHaveLength(1)
    expect(restored.files[0].hash).toBe(hash)
    expect(new Uint8Array(await restored.files[0].entry.blob.arrayBuffer())).toEqual(photo)
    const entries = await readZip(blob)
    const guide = await entries.find(e => e.name === 'README.txt').blob.text()
    expect(guide).toContain('从 Beta 迁移')
    expect(guide).toContain('opengym-backup.json')
  })
})
