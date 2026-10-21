import { useRef } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError, createCampaign, updateCampaign } from '../services/api'
import { campaignFormSchema, changedCampaignFields } from '../services/campaign-form'
import type { CampaignFormValues } from '../services/campaign-form'
import type { Campaign, CampaignLanguage } from '../services/types'
import { campaignQuery } from '../queries'

export default function CampaignForm({ campaign: original }: { campaign?: Campaign }) {
  const navigate = useNavigate()
  const client = useQueryClient()
  const submitting = useRef(false)
  const { register, handleSubmit, setError, formState: { errors, isSubmitting, isDirty } } = useForm<CampaignFormValues>({
    resolver: zodResolver(campaignFormSchema),
    defaultValues: { title: original?.title ?? '', objective: original?.objective ?? '', language: (original?.language as CampaignLanguage) ?? 'both' },
  })
  const mutation = useMutation({
    mutationFn: (values: CampaignFormValues) => original
      ? updateCampaign(original.id, changedCampaignFields(original, values))
      : createCampaign({ ...values, domain: 'traffic_safety' }),
    retry: false,
  })

  const submit = async (values: CampaignFormValues) => {
    if (submitting.current) return
    if (original && Object.keys(changedCampaignFields(original, values)).length === 0) {
      setError('root', { message: 'مفيش تغييرات جديدة للحفظ.' })
      return
    }
    submitting.current = true
    try {
      const campaign = await mutation.mutateAsync(values)
      client.setQueryData(campaignQuery(campaign.id).queryKey, campaign)
      void client.invalidateQueries({ queryKey: ['campaigns'] })
      navigate(`/campaigns/${campaign.id}`, { replace: true, state: original ? { updated: true } : { created: true } })
    } catch (error) {
      if (error instanceof ApiError) {
        for (const field of error.fields) {
          if (field.path === 'title' || field.path === 'objective' || field.path === 'language') {
            setError(field.path, { message: field.message }, { shouldFocus: true })
          }
        }
      }
    } finally {
      submitting.current = false
    }
  }

  const busy = isSubmitting || mutation.isPending

  return (
    <section aria-labelledby="campaign-form-heading">
      <Link className="text-link" to="/campaigns">← كل الحملات</Link>
      <div className="page-heading">
        <p className="eyebrow">{original ? 'حدّث بيانات الحملة' : 'أول خطوة لرسالة تفرق'}</p>
        <h1 id="campaign-form-heading">{original ? 'تعديل الحملة' : 'حملة جديدة'}</h1>
        <p>{original ? 'تعديل البيانات مش بيغيّر المسودات القديمة أو سجل التوليد. استخدم البيانات الجديدة في التوليدات الجاية.' : 'حدّد اسم الحملة وهدفها ولغة المحتوى. تقدر تولّد المسودات في خطوة منفصلة.'}</p>
      </div>
      <form className="panel campaign-form" onSubmit={(event) => { void handleSubmit(submit)(event) }} noValidate aria-busy={busy}>
        <fieldset disabled={busy}>
          <legend className="visually-hidden">بيانات الحملة</legend>
          <div className="form-field">
            <label htmlFor="title">اسم الحملة <span>(مطلوب)</span></label>
            <input id="title" dir="auto" defaultValue={original?.title ?? ''} {...register('title')} aria-invalid={!!errors.title} aria-describedby="title-help title-error" />
            <small id="title-help">اسم قصير وواضح، بحد أقصى ٢٥٥ حرف.</small>
            <span id="title-error" className="field-error" role={errors.title ? 'alert' : undefined}>{errors.title?.message}</span>
          </div>
          <div className="form-field">
            <label htmlFor="objective">هدف الحملة <span>(مطلوب)</span></label>
            <textarea id="objective" dir="auto" rows={5} defaultValue={original?.objective ?? ''} {...register('objective')} aria-invalid={!!errors.objective} aria-describedby="objective-help objective-error" />
            <small id="objective-help">مثال: تشجيع السواقين والركاب في مصر على ربط حزام الأمان في كل مشوار.</small>
            <span id="objective-error" className="field-error" role={errors.objective ? 'alert' : undefined}>{errors.objective?.message}</span>
          </div>
          <div className="form-field">
            <label htmlFor="language">لغة المحتوى <span>(مطلوب)</span></label>
            <select id="language" defaultValue={original?.language ?? 'both'} {...register('language')} aria-invalid={!!errors.language} aria-describedby="language-help language-error">
              <option value="both">عربي مصري وإنجليزي</option>
              <option value="arabic">عربي مصري</option>
              <option value="english">إنجليزي</option>
            </select>
            <small id="language-help">لغة محتوى الحملة مستقلة عن لغة الواجهة.</small>
            <span id="language-error" className="field-error" role={errors.language ? 'alert' : undefined}>{errors.language?.message}</span>
          </div>
          <div className="form-field"><span className="field-label">المجال</span><p><bdi>{!original || original.domain === 'traffic_safety' ? 'السلامة المرورية' : original.domain}</bdi></p></div>
        </fieldset>
        {mutation.isError && <div className="notice error-notice" role="alert">
          <p>{mutation.error.message}</p>
          <span>بياناتك لسه موجودة هنا. لو الاتصال اتقطع، راجع <Link className="text-link" to={original ? `/campaigns/${original.id}` : '/campaigns'}>{original ? 'بيانات الحملة المحفوظة' : 'قائمة الحملات'}</Link> قبل ما تعيد الحفظ.</span>
        </div>}
        {errors.root && <p className="field-error" role="alert">{errors.root.message}</p>}
        <div className="form-actions">
          <button className="button" type="submit" disabled={busy || (!!original && !isDirty)}>{busy ? 'بنحفظ الحملة…' : original ? 'احفظ التعديلات' : 'احفظ الحملة'}</button>
          {!busy && <Link className="button secondary" to={original ? `/campaigns/${original.id}` : '/campaigns'}>إلغاء</Link>}
        </div>
        <p className="form-note" role="status">{busy ? 'استنى لحد ما الحفظ يخلص.' : original ? 'التعديلات بتتحفظ على بيانات الحملة بس؛ المحتوى القديم بيفضل زي ما هو.' : 'الحفظ بينشئ حملة بحالة مسودة؛ مش بيولّد محتوى أو ينشره.'}</p>
      </form>
    </section>
  )
}
