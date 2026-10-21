import { t, useInterfaceLanguage, getInterfaceLocale } from '../i18n'
import { useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { ApiError, updateContent } from '../services/api';
import { changedTextFields, contentFormSchema, textFields } from '../services/content-form';
import type { ContentUpdate, StoredContent, TextPackage } from '../services/types';
import { contentQuery } from '../queries';
import { ErrorNotice } from '../components/Feedback';
import ContentCard from '../components/ContentCard';
import UnsavedChanges from '../components/UnsavedChanges';
export function ReviewActions({ dirty, busy, status, review }: {
    dirty: boolean;
    busy: boolean;
    status: StoredContent['review_status'];
    review: (status: 'approved' | 'rejected') => void;
}) {
    useInterfaceLanguage();
    return (<section className="review-actions" aria-labelledby="review-heading">
      <h2 id="review-heading">{t("قرار المراجعة")}</h2>
      <p>{t("راجع الصياغة والحقائق والمصادر. القرار للنسخة دي بس؛ مش بينشر المحتوى أو بيعتمد اللغة التانية.")}</p>
      {dirty && <p role="status">{t("احفظ التعديلات الأول عشان تقدر تعتمد أو ترفض النسخة.")}</p>}
      <div className="form-actions">
        <button type="button" className="button" disabled={dirty || busy || status === 'approved'} onClick={() => review('approved')}>{t("اعتماد النسخة")}</button>
        <button type="button" className="button secondary" disabled={dirty || busy || status === 'rejected'} onClick={() => review('rejected')}>{t("رفض النسخة")}</button>
      </div>
    </section>);
}
function EditorForm({ initial }: {
    initial: StoredContent;
}) {
    useInterfaceLanguage();
    const [saved, setSaved] = useState(initial);
    const [notice, setNotice] = useState('');
    const lock = useRef(false);
    const client = useQueryClient();
    const { register, handleSubmit, getValues, setError, reset, formState: { errors, isDirty, isSubmitting } } = useForm<TextPackage>({
        resolver: zodResolver(contentFormSchema), defaultValues: initial.content,
    });
    const mutation = useMutation({ mutationFn: (data: ContentUpdate) => updateContent(saved.id, data), retry: false });
    const busy = mutation.isPending || isSubmitting;
    const persist = async (data: ContentUpdate) => {
        if (lock.current)
            return;
        lock.current = true;
        setNotice('');
        try {
            const response = await mutation.mutateAsync(data);
            setSaved(response);
            reset(response.content);
            client.setQueryData(contentQuery(response.id).queryKey, response);
            void client.invalidateQueries({ queryKey: ['campaign-contents', response.campaign_id] });
            setNotice(data.content ? t('تم حفظ التعديلات. النسخة رجعت لمسودة للمراجعة.') : response.review_status === 'approved' ? t('تم اعتماد النسخة دي.') : t('تم رفض النسخة دي.'));
        }
        catch (error) {
            if (error instanceof ApiError)
                for (const field of error.fields) {
                    const name = field.path.replace(/^content\./, '');
                    if (Object.hasOwn(textFields, name))
                        setError(name as keyof TextPackage, { message: t(field.message) }, { shouldFocus: true });
                }
        }
        finally {
            lock.current = false;
        }
    };
    const save = async (values: TextPackage) => {
        const changes = changedTextFields(saved.content, values);
        if (!Object.keys(changes).length) {
            reset(saved.content);
            return;
        }
        await persist({ content: changes });
    };
    const review = (status: 'approved' | 'rejected') => {
        if (lock.current || Object.keys(changedTextFields(saved.content, getValues())).length)
            return;
        void persist({ review_status: status });
    };
    return (<>
      <UnsavedChanges dirty={isDirty} busy={busy}/>
      <Link className="text-link" to={`/campaigns/${saved.campaign_id}`}>{t("← ارجع للحملة")}</Link>
      <div className="page-heading"><h1 id="content-editor-heading" tabIndex={-1}>{t("تعديل ومراجعة المحتوى")}</h1><p>{t("نسخة ")}{saved.language === 'arabic' ? t('عربي مصري') : t('إنجليزي')}{t(" · رقم ")}<bdi>{saved.id}</bdi></p></div>
      <div className="editor-grid">
        <section className="panel">
          <h2>{t("تعديل النص")}</h2>
          <p>{t("الحفظ بيرجّع النسخة لمسودة. اعتماد المحتوى خطوة منفصلة بعد الحفظ.")}</p>
          <form onChange={() => setNotice('')} onSubmit={(event) => { void handleSubmit(save)(event); }} noValidate aria-busy={busy}>
            <fieldset disabled={busy}>
              <legend className="visually-hidden">{t("حقول المحتوى")}</legend>
              {(Object.keys(textFields) as (keyof TextPackage)[]).map((field) => (<div className="form-field" key={field}>
                  <label htmlFor={`text-${field}`}>{t(textFields[field].label)}</label>
                  <textarea id={`text-${field}`} lang={saved.language === 'arabic' ? 'ar-EG' : 'en'} dir={saved.language === 'arabic' ? 'rtl' : 'ltr'} rows={field === 'awareness_message' ? 6 : 3} defaultValue={initial.content[field]} {...register(field)} aria-invalid={!!errors[field]} aria-describedby={`${field}-help ${field}-error`}/>
                  <small id={`${field}-help`}>{t("مطلوب، بحد أقصى ")}{textFields[field].limit.toLocaleString(getInterfaceLocale())}{t(" حرف.")}</small>
                  <span id={`${field}-error`} className="field-error" role={errors[field] ? 'alert' : undefined}>{t(errors[field]?.message)}</span>
                </div>))}
              <button className="button" type="submit" disabled={!isDirty}>{t("احفظ التعديلات")}</button>
            </fieldset>
          </form>
          {mutation.isError && <p className="notice error-notice" role="alert">{t(mutation.error.message)}{t(" تعديلاتك لسه موجودة هنا؛ الحالة المعروضة هي آخر نتيجة مؤكدة من السيرفر.")}</p>}
          {notice && <p className="notice success-notice" role="status">{t(notice)}</p>}
          {busy && <p role="status">{t("بنحفظ الطلب…")}</p>}
          <ReviewActions dirty={isDirty} busy={busy} status={saved.review_status} review={review}/>
        </section>
        <aside aria-label={t("النسخة المحفوظة والمصادر")}><h2>{t("آخر نسخة محفوظة")}</h2><p>{t("المصادر المحفوظة بتفضل من التوليد الأصلي حتى بعد تعديل النص.")}</p><ContentCard item={saved} showEditorLink={false}/></aside>
      </div>
    </>);
}
export default function ContentEditor() {
    useInterfaceLanguage();
    const { contentId = '' } = useParams();
    const id = /^\d+$/.test(contentId) ? Number(contentId) : 0;
    const valid = Number.isSafeInteger(id) && id > 0;
    const query = useQuery(contentQuery(id));
    if (!valid)
        return <section className="panel"><h1>{t("رقم المحتوى غير صحيح")}</h1><Link to="/campaigns">{t("كل الحملات")}</Link></section>;
    if (query.isPending)
        return <p role="status">{t("بنحمّل المحتوى…")}</p>;
    if (query.isError)
        return <><Link className="text-link" to="/campaigns">{t("كل الحملات")}</Link><ErrorNotice error={query.error} retry={() => { void query.refetch(); }}/></>;
    return <EditorForm key={id} initial={query.data}/>;
}
