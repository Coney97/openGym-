#!/usr/bin/env node
// Static candidates require review. A clean scan cannot replace rendered Android testing.
import { readFileSync, readdirSync, writeFileSync, mkdirSync } from 'node:fs'
import { resolve, join, relative } from 'node:path'
import { pathToFileURL, fileURLToPath } from 'node:url'
import { createHash } from 'node:crypto'
import { parse } from '../../frontend/node_modules/@babel/parser/lib/index.js'

const root = resolve(fileURLToPath(new URL('../..', import.meta.url)))
const state = resolve(process.argv[2] || '/workspace/translation-state')
const zh = { ...(await import(pathToFileURL(join(root, 'frontend/src/locales/zh.js')))).default,
  ...(await import(pathToFileURL(join(root, 'frontend/src/locales-extra/zh.js')))).default }
const issues = []
const seen = new Set()
const add = (type, file, key, text, line = null) => {
  const id = createHash('sha256').update(JSON.stringify([type, file, key, text])).digest('hex')
  if (seen.has(id)) return
  seen.add(id)
  issues.push({ id, type, file, key, text, line, status: 'needs_review' })
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
// Text can hide in ternaries, concatenations and templates. Inspect only displayed branches;
// conditions, event handlers, class names and t() arguments are not rendered copy.
function displayed(node, file, key) {
  if (!node) return
  if (node.type === 'StringLiteral' && latin.test(node.value)) {
    add('jsx_expression_candidate', file, key, node.value, node.loc?.start.line)
  } else if (node.type === 'ConditionalExpression') {
    displayed(node.consequent, file, key); displayed(node.alternate, file, key)
  } else if (node.type === 'LogicalExpression' || (node.type === 'BinaryExpression' && node.operator === '+')) {
    displayed(node.left, file, key); displayed(node.right, file, key)
  } else if (node.type === 'TemplateLiteral') {
    for (const part of node.quasis) if (latin.test(part.value.cooked)) {
      add('jsx_template_candidate', file, key, part.value.cooked, part.loc?.start.line)
    }
  }
}
for (const file of walk(join(root, 'frontend/src'))) {
  if (!/\.(jsx|js)$/.test(file) || /\.test\.|\/locales\/|\/instr\/|\/exercise-names\/|\/exercise-desc\//.test(file)) continue
  const text = readFileSync(file, 'utf8')
  const ast = parse(text, { sourceType: 'module', plugins: ['jsx'] })
  function visit(node, parent) {
    if (!node || typeof node !== 'object') return
    const line = node.loc?.start.line
    if (node.type === 'JSXText' && latin.test(node.value)) {
      add('jsx_text_candidate', relative(root, file), 'text', node.value.replace(/\s+/g, ' ').trim(), line)
    }
    if (node.type === 'JSXAttribute' && ['placeholder', 'title', 'aria-label', 'alt'].includes(node.name?.name)
        && node.value?.type === 'StringLiteral' && latin.test(node.value.value)) {
      add('attribute_candidate', relative(root, file), node.name.name, node.value.value, line)
    }
    if (node.type === 'JSXExpressionContainer' && (parent?.type !== 'JSXAttribute'
        || ['placeholder', 'title', 'aria-label', 'alt', 'label', 'hint', 'subtitle'].includes(parent.name?.name))) {
      displayed(node.expression, relative(root, file), parent?.type === 'JSXAttribute' ? parent.name.name : 'literal')
    }
    if (node.type === 'CallExpression' && ['toast', 'alert', 'confirm'].includes(node.callee?.name)
        && node.arguments[0]?.type === 'StringLiteral' && latin.test(node.arguments[0].value)) {
      add('dynamic_message_candidate', relative(root, file), node.callee.name, node.arguments[0].value, line)
    }
    if (node.type === 'ObjectProperty' && ['title', 'message', 'confirmText', 'cancelText', 'hint'].includes(node.key.name ?? node.key.value)
        && node.value?.type === 'StringLiteral' && latin.test(node.value.value)) {
      add('dialog_candidate', relative(root, file), node.key.name ?? node.key.value, node.value.value, line)
    }
    for (const value of Object.values(node)) {
      if (Array.isArray(value)) value.forEach(v => v?.type && visit(v, node))
      else if (value?.type) visit(value, node)
    }
  }
  visit(ast)
}
// Java fallback messages are candidates, including internal identifiers: no automated edits.
for (const file of ['main', 'sideload', 'gms', 'chinese'].flatMap(set => walk(join(root, 'frontend/android/app/src', set)))) {
  if (!/\.(java|xml)$/.test(file)) continue
  const text = readFileSync(file, 'utf8')
  if (file.endsWith('.xml') && /\/values(?:-zh-rCN)?\//.test(file)) {
    for (const array of text.matchAll(/<string-array\b[^>]*name="([^"]+)"[^>]*>([\s\S]*?)<\/string-array>/g)) {
      let index = 0
      for (const item of array[2].matchAll(/<item\b[^>]*>([\s\S]*?)<\/item>/g)) {
        if (latin.test(item[1])) add('android_array_candidate', relative(root, file), `${array[1]}[${index}]`, item[1].trim())
        index++
      }
    }
  }
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
