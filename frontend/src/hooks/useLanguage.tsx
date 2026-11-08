import { setInterfaceLanguage, useInterfaceLanguage } from '../i18n'
import { messages } from '../i18n/messages'

// Share one persisted preference between the redesigned shell and existing editors.
export function useLanguage() {
  const lang = useInterfaceLanguage()
  return {
    lang,
    dir: lang === 'ar' ? 'rtl' as const : 'ltr' as const,
    setLang: setInterfaceLanguage,
    t: (key: string) => messages[lang][key] ?? messages.en[key] ?? key,
  }
}
