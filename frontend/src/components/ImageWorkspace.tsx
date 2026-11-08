import { useEffect, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useIsMutating, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { contentQuery, contentsQuery, imageQuery, imagesQuery } from '../queries'
import { getInterfaceLocale, t, useInterfaceLanguage } from '../i18n'
import { clearImageAttempt, createImageAttempt, generateImage, imageRequestSchema, loadImageAttempt, saveImageAttempt } from '../services/images'
import type { ImageAttempt } from '../services/images'
import type { Campaign, ImageGenerationRequest } from '../services/types'
import { ApiError } from '../services/api'
import { ErrorNotice } from './Feedback'
import ImageCard from './ImageCard'
import { imageStateLabel } from './image-labels'

const PAGE_SIZE = 20

export function ImageBriefForm({ sourceId, busy, disabled, submit }: {
  sourceId: number, busy: boolean, disabled: boolean, submit: (request: ImageGenerationRequest) => Promise<void>,
}) {
  useInterfaceLanguage()
  const { register, handleSubmit, setValue, setError, formState: { errors, isSubmitting } } = useForm<ImageGenerationRequest>({
    resolver: zodResolver(imageRequestSchema), defaultValues: { source_content_id: sourceId, visual_brief: '', style: 'illustration' },
  })
  useEffect(() => { setValue('source_content_id', sourceId) }, [sourceId, setValue])
  const send = async (data: ImageGenerationRequest) => {
    try { await submit(data) } catch (error) {
      if (error instanceof ApiError) for (const field of error.fields) {
        if (field.path === 'visual_brief' || field.path === 'style') setError(field.path, { message: field.message })
      }
    }
  }
  return <form onSubmit={(event) => { void handleSubmit(send)(event) }} noValidate aria-busy={busy}>
    <fieldset disabled={busy || disabled || isSubmitting}>
      <legend className="visually-hidden">{t('إعدادات توليد الصورة')}</legend>
      <input type="hidden" {...register('source_content_id', { valueAsNumber: true })} />
      <div className="form-field">
        <label htmlFor="image-brief">{t('وصف المشهد (مطلوب)')}</label>
        <textarea id="image-brief" dir="auto" rows={4} {...register('visual_brief')} aria-invalid={!!errors.visual_brief} aria-describedby="image-brief-help image-brief-error" />
        <small id="image-brief-help">{t('مثال: عربية واقفة في مصر، سواق وراكب بالغين لابسين الحزام صح، من غير كتابة أو شعارات. الحد الأقصى ٢٠٠٠ حرف؛ الوصف الطويل مع النص ممكن يترفض.')}</small>
        <span className="field-error" id="image-brief-error" role={errors.visual_brief ? 'alert' : undefined}>{t(errors.visual_brief?.message)}</span>
      </div>
      <div className="form-field">
        <label htmlFor="image-style">{t('شكل الصورة')}</label>
        <select id="image-style" {...register('style')}><option value="illustration">{t('رسم توضيحي')}</option><option value="photorealistic">{t('واقعية')}</option></select>
      </div>
      <button className="button" type="submit">{busy ? t('جاري توليد الصورة') : t('توليد صورة جديدة')}</button>
    </fieldset>
    <p className="form-note">{t('الصورة مربعة ومن غير كتابة. التوليد بيستخدم حصة المزوّد وبيتخزن كمسودة؛ جودة المشهد محتاجة مراجعة بشرية.')}</p>
  </form>
}

export default function ImageWorkspace({ campaign }: { campaign: Campaign }) {
  useInterfaceLanguage()
  const client = useQueryClient()
  const [sourcePage, setSourcePage] = useState(0)
  const [page, setPage] = useState(0)
  const [attempt, setAttempt] = useState<ImageAttempt | null>(() => loadImageAttempt(campaign.id))
  const [sourceId, setSourceId] = useState(() => attempt?.request.source_content_id ?? 0)
  const [persisted, setPersisted] = useState(true)
  const [acknowledged, setAcknowledged] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)
  const submitted = useRef(false)
  const mutationKey = ['generate-image', campaign.id]
  const pending = useIsMutating({ mutationKey }) > 0
  const sources = useQuery(contentsQuery(campaign.id, sourcePage * PAGE_SIZE, PAGE_SIZE))
  const source = useQuery(contentQuery(sourceId))
  const history = useQuery(imagesQuery(campaign.id, page * PAGE_SIZE, PAGE_SIZE))
  const active = useQuery({ ...imageQuery(attempt?.image_id ?? 0), staleTime: 0,
    refetchInterval: (query) => ['reserved', 'generating'].includes(query.state.data?.request_state ?? '') ? 5000 : false,
  })
  const activeRecord = active.data?.campaign_id === campaign.id ? active.data : history.data?.find((item) => item.idempotency_key === attempt?.key)
  const approved = source.data?.campaign_id === campaign.id && source.data.review_status === 'approved'
  const supported = campaign.domain === 'traffic_safety'
  const mutation = useMutation({ mutationKey, retry: false,
    mutationFn: (saved: ImageAttempt) => generateImage(campaign.id, saved.request, saved.key),
    onSuccess: (saved, input) => {
      const next = { ...input, image_id: saved.id }
      setPersisted(saveImageAttempt(next)); setAttempt(next)
      client.setQueryData(['image', saved.id], saved)
      setPage(0)
      void client.invalidateQueries({ queryKey: ['campaign-images', campaign.id] })
    },
    onError: () => { void client.invalidateQueries({ queryKey: ['campaign-images', campaign.id] }) },
  })
  const send = async (data?: ImageGenerationRequest) => {
    if (submitted.current || client.isMutating({ mutationKey }) || !supported) return
    if (!attempt && !approved) return
    submitted.current = true
    setLocalError(null)
    try {
      const saved = attempt ?? createImageAttempt(campaign.id, data!)
      // Save the original identity and inputs before sending. Replays never get a new key.
      setPersisted(saveImageAttempt(saved)); setAttempt(saved)
      await mutation.mutateAsync(saved)
    } catch (error) {
      if (!mutation.isError && !(error instanceof ApiError)) setLocalError(t('مقدرناش نكمل طلب الصورة. راجع الصور المحفوظة قبل المتابعة.'))
      throw error
    } finally { submitted.current = false }
  }
  const startNew = () => {
    if (!acknowledged || pending || submitted.current) return
    clearImageAttempt(campaign.id); setAttempt(null); setAcknowledged(false); setLocalError(null); mutation.reset()
  }
  const refresh = async () => {
    await client.invalidateQueries({ queryKey: ['campaign-images', campaign.id] })
    if (attempt?.image_id) await client.invalidateQueries({ queryKey: ['image', attempt.image_id] })
    await client.invalidateQueries({ queryKey: ['campaign-contents', campaign.id] })
    if (sourceId) await client.invalidateQueries({ queryKey: ['content', sourceId] })
  }
  return <section className="image-workspace" aria-labelledby="image-workspace-heading">
    <h2 id="image-workspace-heading">{t('صور الحملة')}</h2>
    <p>{t('اختار نص معتمد، اوصف المشهد، وبعد التوليد راجع الصورة بشكل مستقل.')}</p>
    {!supported && <p className="notice error-notice">{t('توليد الصور متاح لحملات السلامة المرورية بس.')}</p>}
    <section className="panel campaign-form" aria-labelledby="image-source-heading">
      <h3 id="image-source-heading">{t('اختيار النص المعتمد')}</h3>
      <p>{t('بنراجع النصوص المحفوظة صفحة بصفحة. المعروض للاختيار هو النص المعتمد في الصفحة دي بس.')}</p>
      {sources.isPending && <p role="status">{t('بنحمّل المحتوى…')}</p>}
      {sources.isError && <ErrorNotice error={sources.error} retry={() => { void sources.refetch() }} />}
      {sources.data && <>
        <div className="image-source-list">{sources.data.filter((item) => item.review_status === 'approved').map((item) => <button className="button secondary" type="button" key={item.id}
          disabled={pending || !!attempt || !supported} aria-pressed={sourceId === item.id} onClick={() => setSourceId(item.id)}>
          <bdi>{item.content.headline}</bdi><span>{item.language === 'arabic' ? t('عربي مصري') : t('إنجليزي')} · {item.id}</span>
        </button>)}</div>
        {!sources.data.some((item) => item.review_status === 'approved') && <p>{t('مفيش نص معتمد في الصفحة دي. جرّب صفحة تانية أو راجع واعتمد نص من المحتوى المحفوظ.')}</p>}
        <nav className="pagination" aria-label={t('صفحات النصوص لاختيار الصورة')}>
          <button className="button secondary" disabled={sourcePage === 0 || pending || !!attempt} onClick={() => setSourcePage(sourcePage - 1)}>{t('السابق')}</button>
          <span>{t('صفحة ')}{(sourcePage + 1).toLocaleString(getInterfaceLocale())}</span>
          <button className="button secondary" disabled={sources.data.length < PAGE_SIZE || pending || !!attempt} onClick={() => setSourcePage(sourcePage + 1)}>{t('التالي')}</button>
        </nav>
      </>}
      {sourceId > 0 && <p><Link className="text-link" to={`/contents/${sourceId}`}>{t('راجع النص الأصلي رقم ')}{sourceId}</Link></p>}
      {source.isError && <ErrorNotice error={source.error} retry={() => { void source.refetch() }} />}
      {source.isSuccess && <p role="status">{approved ? t('النص المختار معتمد. راجعه قبل توليد الصورة.') : t('النص المختار مش معتمد دلوقتي. راجعه واعتمده الأول.')}</p>}
      {!attempt && <ImageBriefForm sourceId={sourceId} busy={pending} disabled={!supported || !approved || source.isFetching} submit={send} />}
      {!attempt && localError && <p className="notice error-notice" role="alert">{t(localError)}</p>}
    </section>
    {attempt && <section className="panel image-attempt" aria-labelledby="image-attempt-heading">
      <h3 id="image-attempt-heading">{t('آخر طلب صورة في التبويب ده')}</h3>
      <p dir="auto">{attempt.request.visual_brief}</p>
      <p>{activeRecord ? imageStateLabel(activeRecord.request_state) : t('راجع الصور المحفوظة لمعرفة نتيجة الطلب.')}</p>
      <p>{t('الطلب محفوظ في التبويب ده للمتابعة بعد تحديث الصفحة. متبدأش طلب جديد لمجرد إن الاتصال اتقطع.')}</p>
      {!persisted && <p className="notice error-notice">{t('المتصفح مش سامح بحفظ الطلب بعد إعادة التحميل. انسخ مفتاح الطلب وراجع السجل قبل أي محاولة جديدة.')}</p>}
      <p>{t('مفتاح الطلب')}: <bdi>{attempt.key}</bdi></p>
      {pending && <p role="status">{t('التوليد شغال. متعيدش الطلب. الخروج من الصفحة مش بيلغيه على السيرفر.')}</p>}
      <div className="form-actions">
        <button className="button secondary" type="button" disabled={pending || history.isFetching} onClick={() => { void refresh() }}>{t('تحديث سجل الصور')}</button>
        <button className="button secondary" type="button" disabled={pending || activeRecord?.request_state === 'ready'}
          onClick={() => { void send().catch(() => {}) }}>{t('استرجاع أو استكمال نفس الطلب')}</button>
      </div>
      <p className="form-note">{t('المتابعة بتستخدم نفس الطلب. لو وصل قبل كده مش بيتولد تاني؛ لو السيرفر ماستلموش، ممكن يبدأ ويستهلك من الحصة دلوقتي.')}</p>
      {active.isError && <p className="notice error-notice" role="alert">{t(active.error.message)}</p>}
      {mutation.isError && <p className="notice error-notice" role="alert">{t(mutation.error.message)}</p>}
      {localError && <p className="notice error-notice" role="alert">{t(localError)}</p>}
      <label className="image-check"><input type="checkbox" checked={acknowledged} disabled={pending} onChange={(event) => setAcknowledged(event.target.checked)} />
        {t('راجعت الطلب والسجل، وفاهم إن طلب صورة جديدة ممكن يستهلك حصة إضافية حتى لو نتيجة الطلب السابق لسه غير مؤكدة.')}</label>
      <button className="button secondary" type="button" disabled={pending || !acknowledged || history.isFetching} onClick={startNew}>{t('تجهيز طلب صورة جديد')}</button>
    </section>}
    <section className="content-history" aria-labelledby="image-history-heading">
      <div className="history-heading"><h3 id="image-history-heading">{t('سجل الصور المحفوظة')}</h3>
        <button className="button secondary" disabled={history.isFetching || pending} onClick={() => { void refresh() }}>{t('تحديث سجل الصور')}</button></div>
      <p>{t('كل صورة ليها مراجعة مستقلة. تحميل الصورة أو اعتمادها مش بينشر الحملة.')}</p>
      {history.isPending && <p role="status">{t('جاري تحميل الصور…')}</p>}
      {history.isError && <ErrorNotice error={history.error} retry={() => { void history.refetch() }} />}
      {activeRecord && !history.data?.some((item) => item.id === activeRecord.id) && <ImageCard key={activeRecord.id} item={activeRecord} />}
      {history.data && <>
        {history.data.length === 0 && <p className="panel">{t('مفيش صور محفوظة في الصفحة دي.')}</p>}
        <div className="image-grid">{history.data.map((item) => <ImageCard key={item.id} item={item} />)}</div>
        <nav className="pagination" aria-label={t('صفحات الصور')}>
          <button className="button secondary" disabled={page === 0} onClick={() => setPage(page - 1)}>{t('السابق')}</button>
          <span aria-live="polite">{t('صفحة ')}{(page + 1).toLocaleString(getInterfaceLocale())}</span>
          <button className="button secondary" disabled={history.data.length < PAGE_SIZE} onClick={() => setPage(page + 1)}>{t('التالي')}</button>
        </nav>
      </>}
    </section>
  </section>
}
