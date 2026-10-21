import { useEffect, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { deleteCampaign } from '../services/api'
import { campaignQuery } from '../queries'
import type { Campaign } from '../services/types'

export function DeleteConfirmation({ title, busy, error, confirm, cancel }: {
  title: string; busy: boolean; error?: Error; confirm: () => void; cancel: () => void
}) {
  const cancelRef = useRef<HTMLButtonElement>(null)
  useEffect(() => { cancelRef.current?.focus() }, [])
  return (
    <section className="notice error-notice" aria-labelledby="delete-heading" aria-busy={busy}>
      <h2 id="delete-heading">متأكد إنك عايز تحذف الحملة؟</h2>
      <p>حذف <bdi>{title}</bdi> هيمسح كل المحتوى المتولّد وسجل التوليد المرتبط بالحملة دي. مش هتقدر ترجعهم من التطبيق.</p>
      {error && <p role="alert">{error.message} لو الاتصال اتقطع، راجع قائمة الحملات للتأكد من النتيجة.</p>}
      <div className="form-actions">
        <button ref={cancelRef} className="button secondary" disabled={busy} onClick={cancel}>إلغاء الحذف</button>
        <button className="button danger" disabled={busy} onClick={confirm}>{busy ? 'بنحذف الحملة…' : 'أيوه، احذف الحملة ومحتواها'}</button>
      </div>
    </section>
  )
}

export default function DeleteCampaign({ campaign }: { campaign: Campaign }) {
  const [confirming, setConfirming] = useState(false)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const submitted = useRef(false)
  const client = useQueryClient()
  const navigate = useNavigate()
  const mutation = useMutation({
    mutationFn: () => deleteCampaign(campaign.id),
    retry: false,
    onSuccess: async () => {
      await client.cancelQueries({ queryKey: campaignQuery(campaign.id).queryKey })
      client.removeQueries({ queryKey: campaignQuery(campaign.id).queryKey })
      await client.invalidateQueries({ queryKey: ['campaigns'] })
    },
  })
  const confirm = () => {
    if (submitted.current) return
    submitted.current = true
    mutation.mutate(undefined, {
      onSuccess: () => navigate('/campaigns', { replace: true, state: { deleted: true } }),
      onSettled: () => { submitted.current = false },
    })
  }
  const cancel = () => {
    setConfirming(false)
    mutation.reset()
    requestAnimationFrame(() => triggerRef.current?.focus())
  }
  return (
    <div className="delete-campaign">
      <button ref={triggerRef} className="button secondary" disabled={confirming} onClick={() => setConfirming(true)}>حذف الحملة</button>
      {confirming && <DeleteConfirmation title={campaign.title} busy={mutation.isPending} error={mutation.error ?? undefined} confirm={confirm} cancel={cancel} />}
    </div>
  )
}
