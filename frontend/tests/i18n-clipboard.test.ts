import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'
import fs from 'node:fs'
import path from 'node:path'
import ts from 'typescript'
import { english } from '../src/translations.ts'
import { getInterfaceLocale, readInterfaceLanguage, setInterfaceLanguage, t } from '../src/i18n.ts'
import { copyText, packageText } from '../src/services/clipboard.ts'

afterEach(() => setInterfaceLanguage('ar'))

test('interface preference defaults to Arabic and safely handles unavailable storage', () => {
  assert.equal(readInterfaceLanguage(), 'ar')
  assert.equal(readInterfaceLanguage({ getItem: () => 'en' }), 'en')
  assert.equal(readInterfaceLanguage({ getItem: () => 'invalid' }), 'ar')
  assert.equal(readInterfaceLanguage({ getItem: () => { throw new Error('Blocked storage') } }), 'ar')
})

test('a language choice persists only the public interface preference', () => {
  const descriptor = Object.getOwnPropertyDescriptor(globalThis, 'window')
  const writes: [string, string][] = []
  Object.defineProperty(globalThis, 'window', { configurable: true, value: { localStorage: { setItem: (key: string, value: string) => writes.push([key, value]) } } })
  try {
    setInterfaceLanguage('en')
    assert.deepEqual(writes, [['govreach-interface-language', 'en']])
  } finally {
    if (descriptor) Object.defineProperty(globalThis, 'window', descriptor)
    else Reflect.deleteProperty(globalThis, 'window')
  }
})

test('labels, validation messages, dates and stored feedback follow interface preference', () => {
  setInterfaceLanguage('en')
  assert.equal(t('احفظ التعديلات'), 'Save changes')
  assert.equal(t('الحقل ده مطلوب.'), 'This field is required.')
  assert.equal(t('الحد الأقصى 120 حرف.'), 'Maximum 120 characters.')
  assert.equal(getInterfaceLocale(), 'en-GB')
  const feedback = t('تم اعتماد النسخة دي.')
  setInterfaceLanguage('ar')
  assert.equal(t(feedback), 'تم اعتماد النسخة دي.')
  assert.equal(t('Maximum 120 characters.'), 'الحد الأقصى 120 حرف.')
  assert.equal(getInterfaceLocale(), 'ar-EG')
})

test('every literal Arabic UI translation has an English catalogue entry', () => {
  const root = path.resolve('src')
  const files = [path.join(root, 'App.tsx'), ...['components', 'pages'].flatMap((dir) => fs.readdirSync(path.join(root, dir)).filter((file) => file.endsWith('.tsx')).map((file) => path.join(root, dir, file)))]
  const missing = new Set<string>()
  for (const file of files) {
    const source = ts.createSourceFile(file, fs.readFileSync(file, 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)
    function visit(node: ts.Node) {
      if (ts.isCallExpression(node) && node.expression.getText(source) === 't' && node.arguments[0] && ts.isStringLiteral(node.arguments[0])) {
        const key = node.arguments[0].text.replace(/\s+/g, ' ').trim()
        if (/[\u0600-\u06ff]/.test(key) && !english[key]) missing.add(key)
      }
      ts.forEachChild(node, visit)
    }
    visit(source)
  }
  assert.deepEqual([...missing], [])
})

test('copy preserves exact Arabic and English text and the five-field package order', async () => {
  const content = { headline: 'حزامك أمانك', slogan: 'Buckle up', awareness_message: 'رسالة\nسطر تاني', social_caption: ' Caption 🚗 ', call_to_action: 'اربط الحزام.' }
  const full = packageText(content)
  assert.equal(full, 'حزامك أمانك\n\nBuckle up\n\nرسالة\nسطر تاني\n\n Caption 🚗 \n\nاربط الحزام.')
  const copied: string[] = []
  await copyText(full, { writeText: async (text) => { copied.push(text) } })
  assert.deepEqual(copied, [full])
  await copyText(content.awareness_message, { writeText: async (text) => { copied.push(text) } })
  assert.equal(copied[1], content.awareness_message)
})

test('unavailable or denied clipboard reports failure rather than claiming success', async () => {
  await assert.rejects(copyText('Text'), /unavailable/)
  let calls = 0
  await assert.rejects(copyText('Text', { writeText: async () => { calls++; throw new Error('Permission denied') } }), /Permission denied/)
  assert.equal(calls, 1)
})
