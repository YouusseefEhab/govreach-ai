import { t, useInterfaceLanguage } from '../i18n'
import { useEffect, useRef } from 'react';
import { useBeforeUnload, useBlocker } from 'react-router-dom';
export default function UnsavedChanges({ dirty, busy }: {
    dirty: boolean;
    busy: boolean;
}) {
    useInterfaceLanguage();
    const when = dirty || busy;
    const blocker = useBlocker(when);
    const headingRef = useRef<HTMLHeadingElement>(null);
    useBeforeUnload((event) => {
        if (when) {
            event.preventDefault();
            event.returnValue = '';
        }
    });
    useEffect(() => {
        if (!when && blocker.state === 'blocked')
            blocker.reset();
    }, [when, blocker]);
    useEffect(() => {
        if (blocker.state === 'blocked')
            headingRef.current?.focus();
    }, [blocker.state]);
    if (blocker.state !== 'blocked')
        return null;
    return (<section className="notice error-notice" role="alert" aria-label={t("تأكيد مغادرة المحرر")}>
      <h2 ref={headingRef} tabIndex={-1}>{t("قبل ما تسيب الصفحة")}</h2>
      <p>{busy ? t('في طلب لسه بيتحفظ. استنى لحد ما يخلص قبل ما تسيب الصفحة.') : t('في تعديلات لسه متحفظتش. لو خرجت دلوقتي هتفقدها.')}</p>
      <div className="form-actions">
        <button className="button secondary" onClick={() => { blocker.reset(); document.getElementById('content-editor-heading')?.focus(); }}>{t("كمّل المراجعة")}</button>
        <button className="button danger" disabled={busy} onClick={() => blocker.proceed()}>{t("اخرج من غير حفظ")}</button>
      </div>
    </section>);
}
