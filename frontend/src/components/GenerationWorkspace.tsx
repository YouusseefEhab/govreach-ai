import { useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useIsMutating, useMutation, useMutationState, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError, generateText } from '../services/api'
import { generationFormSchema } from '../services/generation-form'
import type { Campaign, GenerationRequest } from '../services/types'
import { contentsQuery } from '../queries'
import { ErrorNotice } from './Feedback'
import ContentCard from './ContentCard'

const PAGE_SIZE = 20

export function GenerationForm({ busy, disabled, submit }: {
  busy: boolean; disabled: boolean; submit: (data: GenerationRequest) => Promise<void>
}) {
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<GenerationRequest>({
    resolver: zodResolver(generationFormSchema), defaultValues: { audience: '', tone: 'informative' },
  })
  const send = async (values: GenerationRequest) => {
    try { await submit(values) } catch (error) {
      if (error instanceof ApiError) for (const field of error.fields) {
        if (field.path === 'audience' || field.path === 'tone') setError(field.path, { message: field.message }, { shouldFocus: true })
      }
    }
  }
  return (
    <form onSubmit={(event) => { void handleSubmit(send)(event) }} noValidate aria-busy={busy}>
      <fieldset disabled={busy || disabled || isSubmitting}>
        <legend className="visually-hidden">إعدادات توليد النص</legend>
        <div className="form-field">
          <label htmlFor="audience">الجمهور المستهدف (مطلوب)</label>
          <input id="audience" dir="auto" {...register('audience')} aria-invalid={!!errors.audience} aria-describedby="audience-help audience-error" />
          <small id="audience-help">مثال: السواقين والركاب في مصر. بحد أقصى ٣٠٠ حرف.</small>
          <span className="field-error" id="audience-error" role={errors.audience ? 'alert' : undefined}>{errors.audience?.message}</span>
        </div>
        <div className="form-field">
          <label htmlFor="tone">نبرة الرسالة</label>
          <select id="tone" defaultValue="informative" {...register('tone')} aria-invalid={!!errors.tone} aria-describedby="tone-error">
            <option value="informative">توعوية</option><option value="encouraging">تشجيعية</option><option value="formal">رسمية</option>
          </select>
          <span className="field-error" id="tone-error" role={errors.tone ? 'alert' : undefined}>{errors.tone?.message}</span>
        </div>
        <button className="button" type="submit">{busy ? 'بنجهّز المسودة…' : 'ولّد مسودة جديدة'}</button>
      </fieldset>
      <p className="form-note" role="status">{busy
        ? 'التوليد ممكن ياخد أكتر من دقيقة. استنى؛ متعيدش الطلب. الخروج من الصفحة مش بيلغي التوليد على السيرفر.'
        : 'كل ضغطة بتبدأ توليد جديد وممكن تستهلك من حصة أو رصيد المزوّد. المحتوى بيتحفظ كمسودة للمراجعة.'}</p>
    </form>
  )
}

export default function GenerationWorkspace({ campaign }: { campaign: Campaign }) {
  const [page, setPage] = useState(0)
  const [reviewedAt, setReviewedAt] = useState(0)
  const [checking, setChecking] = useState(false)
  const [checkError, setCheckError] = useState<Error | null>(null)
  const submitted = useRef(false)
  const client = useQueryClient()
  const mutationKey = ['generate-text', campaign.id]
  const pending = useIsMutating({ mutationKey }) > 0
  const attempts = useMutationState({
    filters: { mutationKey },
    select: (attempt) => ({ status: attempt.state.status, error: attempt.state.error, submittedAt: attempt.state.submittedAt }),
  })
  const latest = attempts.at(-1)
  const needsCheck = latest?.status === 'error' && reviewedAt < latest.submittedAt
  const supported = campaign.domain === 'traffic_safety' && ['arabic', 'english', 'both'].includes(campaign.language)
  const history = useQuery(contentsQuery(campaign.id, page * PAGE_SIZE, PAGE_SIZE))
  const mutation = useMutation({
    mutationKey,
    mutationFn: (data: GenerationRequest) => generateText(campaign.id, data),
    retry: false,
    onSuccess: () => {
      setPage(0)
      void client.invalidateQueries({ queryKey: ['campaign-contents', campaign.id] })
    },
  })
  const submit = async (data: GenerationRequest) => {
    if (submitted.current || client.isMutating({ mutationKey }) > 0 || needsCheck || !supported || checking) return
    submitted.current = true
    try { await mutation.mutateAsync(data) } finally { submitted.current = false }
  }
  const checkSaved = async () => {
    if (checking || client.isMutating({ mutationKey }) > 0) return
    setChecking(true)
    setCheckError(null)
    try {
      await client.fetchQuery({ ...contentsQuery(campaign.id), staleTime: 0 })
      setPage(0)
      setReviewedAt(Date.now())
    } catch (error) { setCheckError(error instanceof Error ? error : new Error('مقدرناش نحمّل المحتوى المحفوظ.')) }
    finally { setChecking(false) }
  }
  return (
    <div className="generation-workspace">
      <section className="panel campaign-form" aria-labelledby="generation-heading">
        <h2 id="generation-heading">توليد نص الحملة</h2>
        <p>لغة التوليد بتتحدد من بيانات الحملة: {campaign.language === 'both' ? 'عربي مصري وإنجليزي' : campaign.language === 'arabic' ? 'عربي مصري' : campaign.language === 'english' ? 'إنجليزي' : campaign.language}.</p>
        {!supported && <p className="notice error-notice">توليد النص متاح لحملات السلامة المرورية بالعربي أو الإنجليزي بس. راجع بيانات الحملة.</p>}
        <GenerationForm busy={pending} disabled={!supported || needsCheck || checking} submit={submit} />
        {latest?.status === 'success' && !pending && <p className="notice success-notice" role="status">تم توليد وحفظ المسودات. راجع المحتوى المحفوظ تحت قبل الاستخدام.</p>}
        {latest?.status === 'error' && <div className="notice error-notice" role="alert">
          <p>{latest.error instanceof Error ? latest.error.message : 'التوليد مكملش.'}</p>
          <p>{needsCheck ? 'حدّث المحتوى المحفوظ وراجعه قبل ما تقرر تعيد الطلب. بيانات النموذج لسه موجودة.' : 'المحتوى المحفوظ اتحدّث. راجعه قبل ما تبدأ توليد جديد.'}</p>
          <button className="button secondary" disabled={checking || pending} onClick={() => { void checkSaved() }}>{checking ? 'بنراجع المحتوى…' : 'راجع المحتوى المحفوظ'}</button>
        </div>}
        {checkError && <p role="alert" className="field-error">{checkError.message}</p>}
      </section>
      <section aria-labelledby="history-heading" className="content-history">
        <div className="history-heading"><h2 id="history-heading">المحتوى المحفوظ</h2>
          <button className="button secondary" disabled={checking || pending} onClick={() => { void checkSaved() }}>تحديث المحتوى</button>
        </div>
        <p>كل بطاقة نسخة لغة محفوظة. نسختين من نفس التوليد ممكن يكونوا في صفحتين مختلفتين؛ رقم مجموعة التوليد بيربطهم.</p>
        {history.isPending && <p role="status">بنحمّل المحتوى…</p>}
        {history.isError && <ErrorNotice error={history.error} retry={() => { void history.refetch() }} />}
        {history.data && <>
          {history.data.length === 0 && <p className="panel">{page === 0 ? 'لسه مفيش محتوى محفوظ للحملة دي.' : 'مفيش محتوى تاني في الصفحة دي.'}</p>}
          <div className="content-grid">{history.data.map((item) => <ContentCard key={item.id} item={item} />)}</div>
          <nav className="pagination" aria-label="صفحات المحتوى">
            <button className="button secondary" disabled={page === 0} onClick={() => setPage(page - 1)}>السابق</button>
            <span aria-live="polite">صفحة {(page + 1).toLocaleString('ar-EG')}</span>
            <button className="button secondary" disabled={history.data.length < PAGE_SIZE} onClick={() => setPage(page + 1)}>التالي</button>
          </nav>
        </>}
      </section>
    </div>
  )
}
