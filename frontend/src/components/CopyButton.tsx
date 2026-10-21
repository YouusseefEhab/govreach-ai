import { useRef, useState } from 'react'
import { t, useInterfaceLanguage } from '../i18n'
import { copyText } from '../services/clipboard'

export default function CopyButton({ text, label = 'نسخ' }: { text: string; label?: string }) {
  useInterfaceLanguage()
  const lock = useRef(false)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<{ text: string; ok: boolean } | null>(null)
  const copy = async () => {
    if (lock.current) return
    lock.current = true
    setBusy(true)
    try {
      await copyText(text, navigator.clipboard)
      setResult({ text, ok: true })
    } catch { setResult({ text, ok: false }) }
    finally { lock.current = false; setBusy(false) }
  }
  return (
    <span className="copy-control">
      <button className="button secondary copy-button" type="button" disabled={busy} onClick={() => { void copy() }}>{busy ? t('جاري النسخ…') : t(label)}</button>
      <span role="status" className="copy-feedback">{!busy && result?.text === text ? t(result.ok ? 'تم النسخ.' : 'مقدرناش ننسخ تلقائياً. حدّد النص وانسخه يدوياً.') : ''}</span>
    </span>
  )
}
