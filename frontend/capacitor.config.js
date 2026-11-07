import { readFileSync } from 'node:fs'
const base = JSON.parse(readFileSync(new URL('./capacitor.config.json', import.meta.url), 'utf8'))
const edition = JSON.parse(readFileSync(new URL('./chinese-edition.json', import.meta.url), 'utf8'))
const chinese = process.env.VITE_ZH_CN_EDITION === '1'
// Named exports are the config object consumed by Capacitor's Node ESM require support.
export const appId = chinese ? edition.appId : base.appId
export const appName = chinese ? edition.appName : base.appName
export const webDir = base.webDir
export const backgroundColor = base.backgroundColor
export const android = base.android
export const plugins = base.plugins
