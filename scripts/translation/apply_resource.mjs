#!/usr/bin/env node
import { readFileSync, writeFileSync, renameSync } from 'node:fs'
import { resolve, join } from 'node:path'
import { parse } from '../../frontend/node_modules/@babel/parser/lib/index.js'
const root = resolve(process.argv[2]), updates = JSON.parse(readFileSync(0, 'utf8'))
for (const file of [...new Set(updates.map(u => u.locator.file))]) {
  const nativeFile = 'frontend/android/app/src/main/java/ch/duartesantos/opengym/NativeWords.java'
  if (!['frontend/scripts/chinese-html.mjs', 'frontend/src/lib/backup-media.js', nativeFile].includes(file)) throw new Error('Unexpected text resource')
  const path = join(root, file), code = readFileSync(path, 'utf8'), edits = []
  const ast = file === nativeFile ? null : parse(code, { sourceType: 'module' })
  for (const update of updates.filter(u => u.locator.file === file)) {
    let found = false
    if (file === nativeFile) {
      if (update.kind !== 'native_fallback') throw new Error('Unexpected native text resource kind')
      for (const match of code.matchAll(/case ("(?:\\.|[^"\\])*"): return ("(?:\\.|[^"\\])*");/g)) {
        if (JSON.parse(match[1]) !== update.locator.key) continue
        const start = match.index + 'case '.length + match[1].length + ': return '.length
        edits.push({ start, end: start + match[2].length, text: JSON.stringify(update.target) })
        found = true
      }
    }
    function visit(node) {
      if (node.type === 'VariableDeclarator' && update.kind === 'boot' && node.id.name === 'messages') {
        const p = node.init.properties.find(p => p.key.value === update.locator.key)
        if (p) { edits.push({ start: p.value.start, end: p.value.end, text: JSON.stringify(update.target) }); found = true }
      }
      if (node.type === 'VariableDeclarator' && update.kind === 'export' && node.id.name === 'README') {
        const value = node.init.consequent
        // Retain a no-substitution template literal, escaping interpolation syntax.
        edits.push({ start: value.start, end: value.end, text: '`' + update.target.replaceAll('\\', '\\\\').replaceAll('`', '\\`').replaceAll('${', '\\${') + '`' })
        found = true
      }
      for (const value of Object.values(node)) {
        if (Array.isArray(value)) value.forEach(v => v?.type && visit(v))
        else if (value?.type) visit(value)
      }
    }
    if (ast) visit(ast)
    if (!found) throw new Error('Text resource removed or changed')
  }
  let output = code
  for (const edit of edits.sort((a, b) => b.start - a.start)) output = output.slice(0, edit.start) + edit.text + output.slice(edit.end)
  const temporary = `${path}.translation-${process.pid}.tmp`
  writeFileSync(temporary, output, { flag: 'wx' })
  renameSync(temporary, path)
}
