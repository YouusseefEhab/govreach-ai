import { useSyncExternalStore } from 'react'
import { english } from './translations.ts'

export type InterfaceLanguage = 'ar' | 'en'
const storageKey = 'govreach-interface-language'
export function readInterfaceLanguage(storage?: Pick<Storage, 'getItem'>): InterfaceLanguage {
  try { return storage?.getItem(storageKey) === 'en' ? 'en' : 'ar' } catch { return 'ar' }
}
function initialLanguage(): InterfaceLanguage {
  try { return readInterfaceLanguage(typeof window === 'undefined' ? undefined : window.localStorage) } catch { return 'ar' }
}
let current: InterfaceLanguage = initialLanguage()
const listeners = new Set<() => void>()
const reverse = Object.fromEntries(Object.entries(english).map(([ar, en]) => [en, ar]))

export function setInterfaceLanguage(language: InterfaceLanguage) {
  current = language
  try { window.localStorage.setItem(storageKey, language) } catch { /* Preference is still kept for this session. */ }
  listeners.forEach((listener) => listener())
}
export function useInterfaceLanguage() {
  return useSyncExternalStore((listener) => { listeners.add(listener); return () => listeners.delete(listener) }, () => current, () => current)
}
export function getInterfaceLocale() { return current === 'ar' ? 'ar-EG' : 'en-GB' }

export function t(value: string | null | undefined): string {
  if (!value) return ''
  const key = value.replace(/\s+/g, ' ').trim()
  const englishLimit = /^Maximum (\d+) characters\.$/.exec(key)
  const canonical = reverse[key] ?? (englishLimit ? `الحد الأقصى ${englishLimit[1]} حرف.` : key)
  const limit = /^الحد الأقصى (\d+) حرف\.$/.exec(canonical)
  const serverLimit = /^String should have at most (\d+) characters$/.exec(key)
  const serverRequired = key === 'String should have at least 1 character'
  const translated = current === 'en'
    ? english[canonical] ?? (limit ? `Maximum ${limit[1]} characters.` : key)
    : serverRequired ? 'الحقل ده مطلوب.' : serverLimit ? `الحد الأقصى ${serverLimit[1]} حرف.` : canonical
  return `${/^\s/.test(value) ? ' ' : ''}${translated}${/\s$/.test(value) ? ' ' : ''}`
}
