import { t, useInterfaceLanguage } from '../i18n'
import { messages } from '../messages';
export function ErrorNotice({ error, retry }: {
    error: Error;
    retry: () => void;
}) {
    useInterfaceLanguage();
    return (<div className="notice error-notice" role="alert">
      <p>{t(error.message)}</p>
      <button className="button secondary" onClick={retry}>{t(messages.retry)}</button>
    </div>);
}
