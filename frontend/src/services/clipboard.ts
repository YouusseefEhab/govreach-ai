import type { TextPackage } from './types.ts'

// Preserve text and field order; copying never modifies content or review status.
export function packageText(content: TextPackage): string {
  return [content.headline, content.slogan, content.awareness_message, content.social_caption, content.call_to_action].join('\n\n')
}

export async function copyText(text: string, clipboard?: Pick<Clipboard, 'writeText'>): Promise<void> {
  if (!clipboard) throw new Error('Clipboard unavailable')
  await clipboard.writeText(text)
}
