import { messages } from '../messages'

export function ErrorNotice({ error, retry }: { error: Error; retry: () => void }) {
  return (
    <div className="notice error-notice" role="alert">
      <p>{error.message}</p>
      <button className="button secondary" onClick={retry}>{messages.retry}</button>
    </div>
  )
}
