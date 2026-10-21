import { t, useInterfaceLanguage } from '../i18n'
import { useRef } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { ApiError, createCampaign, updateCampaign } from '../services/api';
import { campaignFormSchema, changedCampaignFields } from '../services/campaign-form';
import type { CampaignFormValues } from '../services/campaign-form';
import type { Campaign, CampaignLanguage } from '../services/types';
import { campaignQuery } from '../queries';
export default function CampaignForm({ campaign: original }: {
    campaign?: Campaign;
}) {
    useInterfaceLanguage();
    const navigate = useNavigate();
    const client = useQueryClient();
    const submitting = useRef(false);
    const { register, handleSubmit, setError, formState: { errors, isSubmitting, isDirty } } = useForm<CampaignFormValues>({
        resolver: zodResolver(campaignFormSchema),
        defaultValues: { title: original?.title ?? '', objective: original?.objective ?? '', language: (original?.language as CampaignLanguage) ?? 'both' },
    });
    const mutation = useMutation({
        mutationFn: (values: CampaignFormValues) => original
            ? updateCampaign(original.id, changedCampaignFields(original, values))
            : createCampaign({ ...values, domain: 'traffic_safety' }),
        retry: false,
    });
    const submit = async (values: CampaignFormValues) => {
        if (submitting.current)
            return;
        if (original && Object.keys(changedCampaignFields(original, values)).length === 0) {
            setError('root', { message: t('مفيش تغييرات جديدة للحفظ.') });
            return;
        }
        submitting.current = true;
        try {
            const campaign = await mutation.mutateAsync(values);
            client.setQueryData(campaignQuery(campaign.id).queryKey, campaign);
            void client.invalidateQueries({ queryKey: ['campaigns'] });
            navigate(`/campaigns/${campaign.id}`, { replace: true, state: original ? { updated: true } : { created: true } });
        }
        catch (error) {
            if (error instanceof ApiError) {
                for (const field of error.fields) {
                    if (field.path === 'title' || field.path === 'objective' || field.path === 'language') {
                        setError(field.path, { message: t(field.message) }, { shouldFocus: true });
                    }
                }
            }
        }
        finally {
            submitting.current = false;
        }
    };
    const busy = isSubmitting || mutation.isPending;
    return (<section aria-labelledby="campaign-form-heading">
      <Link className="text-link" to="/campaigns">{t("← كل الحملات")}</Link>
      <div className="page-heading">
        <p className="eyebrow">{original ? t('حدّث بيانات الحملة') : t('أول خطوة لرسالة تفرق')}</p>
        <h1 id="campaign-form-heading">{original ? t('تعديل الحملة') : t('حملة جديدة')}</h1>
        <p>{original ? t('تعديل البيانات مش بيغيّر المسودات القديمة أو سجل التوليد. استخدم البيانات الجديدة في التوليدات الجاية.') : t('حدّد اسم الحملة وهدفها ولغة المحتوى. تقدر تولّد المسودات في خطوة منفصلة.')}</p>
      </div>
      <form className="panel campaign-form" onSubmit={(event) => { void handleSubmit(submit)(event); }} noValidate aria-busy={busy}>
        <fieldset disabled={busy}>
          <legend className="visually-hidden">{t("بيانات الحملة")}</legend>
          <div className="form-field">
            <label htmlFor="title">{t("اسم الحملة ")}<span>{t("(مطلوب)")}</span></label>
            <input id="title" dir="auto" defaultValue={original?.title ?? ''} {...register('title')} aria-invalid={!!errors.title} aria-describedby="title-help title-error"/>
            <small id="title-help">{t("اسم قصير وواضح، بحد أقصى ٢٥٥ حرف.")}</small>
            <span id="title-error" className="field-error" role={errors.title ? 'alert' : undefined}>{t(errors.title?.message)}</span>
          </div>
          <div className="form-field">
            <label htmlFor="objective">{t("هدف الحملة ")}<span>{t("(مطلوب)")}</span></label>
            <textarea id="objective" dir="auto" rows={5} defaultValue={original?.objective ?? ''} {...register('objective')} aria-invalid={!!errors.objective} aria-describedby="objective-help objective-error"/>
            <small id="objective-help">{t("مثال: تشجيع السواقين والركاب في مصر على ربط حزام الأمان في كل مشوار.")}</small>
            <span id="objective-error" className="field-error" role={errors.objective ? 'alert' : undefined}>{t(errors.objective?.message)}</span>
          </div>
          <div className="form-field">
            <label htmlFor="language">{t("لغة المحتوى ")}<span>{t("(مطلوب)")}</span></label>
            <select id="language" defaultValue={original?.language ?? 'both'} {...register('language')} aria-invalid={!!errors.language} aria-describedby="language-help language-error">
              <option value="both">{t("عربي مصري وإنجليزي")}</option>
              <option value="arabic">{t("عربي مصري")}</option>
              <option value="english">{t("إنجليزي")}</option>
            </select>
            <small id="language-help">{t("لغة محتوى الحملة مستقلة عن لغة الواجهة.")}</small>
            <span id="language-error" className="field-error" role={errors.language ? 'alert' : undefined}>{t(errors.language?.message)}</span>
          </div>
          <div className="form-field"><span className="field-label">{t("المجال")}</span><p><bdi>{!original || original.domain === 'traffic_safety' ? t('السلامة المرورية') : original.domain}</bdi></p></div>
        </fieldset>
        {mutation.isError && <div className="notice error-notice" role="alert">
          <p>{t(mutation.error.message)}</p>
          <span>{t("بياناتك لسه موجودة هنا. لو الاتصال اتقطع، راجع ")}<Link className="text-link" to={original ? `/campaigns/${original.id}` : '/campaigns'}>{original ? t('بيانات الحملة المحفوظة') : t('قائمة الحملات')}</Link>{t(" قبل ما تعيد الحفظ.")}</span>
        </div>}
        {errors.root && <p className="field-error" role="alert">{t(errors.root.message)}</p>}
        <div className="form-actions">
          <button className="button" type="submit" disabled={busy || (!!original && !isDirty)}>{busy ? t('بنحفظ الحملة…') : original ? t('احفظ التعديلات') : t('احفظ الحملة')}</button>
          {!busy && <Link className="button secondary" to={original ? `/campaigns/${original.id}` : '/campaigns'}>{t("إلغاء")}</Link>}
        </div>
        <p className="form-note" role="status">{busy ? t('استنى لحد ما الحفظ يخلص.') : original ? t('التعديلات بتتحفظ على بيانات الحملة بس؛ المحتوى القديم بيفضل زي ما هو.') : t('الحفظ بينشئ حملة بحالة مسودة؛ مش بيولّد محتوى أو ينشره.')}</p>
      </form>
    </section>);
}
