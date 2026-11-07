import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import { MOBILE } from './lib/mobile.js'
import { useStore } from './store/useStore.js'
import { startMediaSync } from './lib/media-sync.js'
import { startNativeKeyboard } from './lib/native-keyboard.js'
// The Coach's and the admin dashboard's styles stay in the main stylesheet, in the place they
// always had (before index.css), although their screens are now loaded on demand (App.jsx).
import './admin.css'
import './coach.css'
import './index.css'
import { hideBoot, handOverFromLaunchScreen } from './lib/boot.js'
import { guardFocusZoom } from './lib/viewport-zoom.js'
import { CHINESE_EDITION } from './lib/chinese-edition.js'

// App.jsx restores per-route scroll itself; the browser's own attempt races it.
// A script that dies before the app draws would otherwise leave the boot logo lifting forever.
window.addEventListener('error', hideBoot, { once: true })
handOverFromLaunchScreen()

if ('scrollRestoration' in history) history.scrollRestoration = 'manual'

// The web build lets people pinch to zoom; on iOS a focused small field must not zoom the page.
if (!MOBILE) guardFocusZoom()

async function mountApp() {
  if (CHINESE_EDITION) {
    const { setLang, t } = await import('./lib/i18n.js')
    await setLang('zh', false, false)
    if (t('Settings') === 'Settings') throw new Error('中文语言包加载失败')
  }
  createRoot(document.getElementById('root')).render(<StrictMode><App /></StrictMode>)
}
mountApp().catch(error => {
  hideBoot()
  const root = document.getElementById('root')
  root.textContent = CHINESE_EDITION ? '无法加载中文界面，请关闭应用后重试。' : String(error)
})

// The photos and videos of custom exercises, in every build (the phone and the demo included):
// uploads of what the server lacks, the local clean-up, and the plan's files kept offline.
startMediaSync(useStore)

// Android 15 does not resize the page for the soft keyboard; the app says how much it covers and
// this keeps the focused field above it. Idle everywhere else.
startNativeKeyboard()

// Not in the mobile build: the native shell already serves everything from disk.
if (!MOBILE && 'serviceWorker' in navigator && location.protocol === 'https:') {
  navigator.serviceWorker.register('sw.js').catch(() => {})
  // The plan's exercise media, kept by the worker for a workout opened without a network (#281).
  // It only fetches ahead while the page runs as the installed app; a tab keeps what it has shown.
  import('./lib/media-prefetch.js').then(m => m.startMediaPrefetch(useStore)).catch(() => {})
}
