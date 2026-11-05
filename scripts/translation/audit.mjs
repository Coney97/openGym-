#!/usr/bin/env node
// Static candidates require review. A clean scan cannot replace rendered Android testing.
import { readFileSync, readdirSync, writeFileSync, mkdirSync } from 'node:fs'
import { resolve, join, relative } from 'node:path'
import { pathToFileURL, fileURLToPath } from 'node:url'
import { createHash } from 'node:crypto'

const root = resolve(fileURLToPath(new URL('../..', import.meta.url)))
const state = resolve(process.argv[2] || '/workspace/translation-state')
const zh = (await import(pathToFileURL(join(root, 'frontend/src/locales/zh.js')))).default
const issues = []
const add = (type, file, key, text) => {
  const id = createHash('sha256').update(JSON.stringify([type, file, key, text])).digest('hex')
  issues.push({ id, type, file, key, text, status: 'needs_review' })
}
const han = /[\u3400-\u9fff]/
const latin = /[A-Za-z]{3,}/
for (const [key, value] of Object.entries(zh)) {
  const forms = typeof value === 'object' ? Object.values(value) : [value]
  for (const text of forms) {
    if (!String(text).trim()) add('blank_ui', 'frontend/src/locales/zh.js', key, text)
    else if (latin.test(text)) add(han.test(text) ? 'mixed_ui' : 'english_ui', 'frontend/src/locales/zh.js', key, text)
  }
}
function walk(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap(e => e.isDirectory() ? walk(join(dir, e.name)) : [join(dir, e.name)])
}
for (const file of walk(join(root, 'frontend/src'))) {
  if (!/\.(jsx|js)$/.test(file) || /\.test\.|\/locales\/|\/instr\/|\/exercise-names\/|\/exercise-desc\//.test(file)) continue
  const text = readFileSync(file, 'utf8')
  // Candidate plain JSX text; excludes text wholly inside JS expressions.
  for (const m of text.matchAll(/>\s*([A-Za-z][^<>{}\n]*[A-Za-z.!?])\s*</g)) {
    const line = text.slice(0, m.index).split('\n').length
    add('jsx_text_candidate', relative(root, file), String(line), m[1].trim())
  }
  for (const m of text.matchAll(/\b(?:placeholder|title|aria-label|alt)\s*=\s*["']([^"']*[A-Za-z]{3,}[^"']*)["']/g)) {
    add('attribute_candidate', relative(root, file), String(text.slice(0, m.index).split('\n').length), m[1])
  }
}
// Java fallback messages are candidates, including internal identifiers: no automated edits.
for (const file of walk(join(root, 'frontend/android/app/src/main'))) {
  if (!/\.(java|xml)$/.test(file)) continue
  const text = readFileSync(file, 'utf8')
  for (const [index, line] of text.split('\n').entries()) {
    if (file.endsWith('.java')) {
      for (const m of line.matchAll(/"([A-Za-z][A-Za-z ,.!?'-]{5,})"/g)) add('native_candidate', relative(root, file), String(index + 1), m[1])
    } else if (/\/values(?:-zh-rCN)?\//.test(file)) {
      for (const m of line.matchAll(/<string\b[^>]*name="([^"]+)"[^>]*>([^<]*)<\/string>/g)) {
        if (latin.test(m[2])) add('android_resource_candidate', relative(root, file), m[1], m[2])
      }
    }
  }
}
mkdirSync(state, { recursive: true })
writeFileSync(join(state, 'audit.json'), JSON.stringify({ generated: new Date().toISOString(), limitations: 'Static candidates only; not exhaustive, include proper names and internal strings. Review actual Android screens, errors, notifications, exports and offline flows.', issues }, null, 2) + '\n')
console.log(`${issues.length} static candidates saved to ${join(state, 'audit.json')}`)
