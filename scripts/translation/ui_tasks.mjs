#!/usr/bin/env node
import { resolve, join } from 'node:path'
import { pathToFileURL } from 'node:url'
const root = resolve(process.argv[2])
const { default: zh } = await import(pathToFileURL(join(root, 'frontend/src/locales/zh.js')))
const { existsSync } = await import('node:fs')
const extraFile = 'frontend/src/locales-extra/zh.js'
const extra = existsSync(join(root, extraFile)) ? (await import(pathToFileURL(join(root, extraFile)))).default : {}
console.log(JSON.stringify([
  ...Object.entries(zh).filter(([key]) => !Object.hasOwn(extra, key)).map(([source, target]) => ({ source, target, pack: 'frontend/src/locales/zh.js' })),
  ...Object.entries(extra).map(([source, target]) => ({ source, target, pack: extraFile }))
]))
