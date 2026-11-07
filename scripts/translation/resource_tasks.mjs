#!/usr/bin/env node
import { readFileSync, existsSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { parse } from '../../frontend/node_modules/@babel/parser/lib/index.js'
const root = resolve(process.argv[2])
const rows = []
const nativeFile = 'frontend/android/app/src/main/java/ch/duartesantos/opengym/NativeWords.java'
if (existsSync(join(root, nativeFile))) {
  const code = readFileSync(join(root, nativeFile), 'utf8')
  for (const match of code.matchAll(/case ("(?:\\.|[^"\\])*"): return ("(?:\\.|[^"\\])*");/g)) {
    const source = JSON.parse(match[1])
    rows.push({ kind: 'native_fallback', key: source, source, target: JSON.parse(match[2]), locator: { file: nativeFile, key: source } })
  }
}
for (const [kind, file, identifier] of [
  ['boot', 'frontend/scripts/chinese-html.mjs', 'messages'],
  ['export', 'frontend/src/lib/backup-media.js', 'README']
]) {
  if (!existsSync(join(root, file))) continue
  const ast = parse(readFileSync(join(root, file), 'utf8'), { sourceType: 'module' })
  function visit(node) {
    if (node.type === 'VariableDeclarator' && node.id.name === identifier) {
      if (kind === 'boot' && node.init.type === 'ObjectExpression') {
        for (const p of node.init.properties) rows.push({ kind, key: p.key.value, source: p.key.value, target: p.value.value, locator: { file, key: p.key.value } })
      } else if (kind === 'export' && node.init.type === 'ConditionalExpression'
          && node.init.consequent.type === 'TemplateLiteral' && !node.init.consequent.expressions.length
          && node.init.alternate.type === 'TemplateLiteral' && !node.init.alternate.expressions.length) {
        rows.push({ kind, key: 'backup-readme', source: node.init.alternate.quasis[0].value.cooked,
          target: node.init.consequent.quasis[0].value.cooked, locator: { file, key: identifier } })
      }
    }
    for (const value of Object.values(node)) {
      if (Array.isArray(value)) value.forEach(v => v?.type && visit(v))
      else if (value?.type) visit(value)
    }
  }
  visit(ast)
}
console.log(JSON.stringify(rows))
