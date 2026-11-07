#!/usr/bin/env node
// Replace only reviewed value spans; preserve English keys, formatting and unrelated entries.
import { readFileSync, writeFileSync, renameSync } from 'node:fs'
import { resolve, join } from 'node:path'
import { pathToFileURL } from 'node:url'
const root = resolve(process.argv[2])
const { parse } = await import('../../frontend/node_modules/@babel/parser/lib/index.js')
const updates = JSON.parse(readFileSync(0, 'utf8'))
for (const pack of [...new Set(updates.map(u => u.pack || 'frontend/src/locales/zh.js'))]) {
  if (!['frontend/src/locales/zh.js', 'frontend/src/locales-extra/zh.js'].includes(pack)) throw new Error('Unknown locale destination')
  const file = join(root, pack)
  const code = readFileSync(file, 'utf8')
  const ast = parse(code, { sourceType: 'module' })
  const dict = ast.program.body.find(n => n.type === 'ExportDefaultDeclaration')?.declaration
  if (dict?.type !== 'ObjectExpression') throw new Error('Unsupported locale pack shape')
  const edits = []
  for (const update of updates.filter(u => (u.pack || 'frontend/src/locales/zh.js') === pack)) {
    const property = dict.properties.find(p => p.type === 'ObjectProperty' && (p.key.value ?? p.key.name) === update.key)
    if (!property) throw new Error('Unknown translation key')
    edits.push({ start: property.value.start, end: property.value.end, text: JSON.stringify(update.target) })
  }
  let output = code
  for (const edit of edits.sort((a, b) => b.start - a.start)) output = output.slice(0, edit.start) + edit.text + output.slice(edit.end)
  const temporary = `${file}.translation-${process.pid}.tmp`
  writeFileSync(temporary, output, { flag: 'wx' })
  renameSync(temporary, file)
}
