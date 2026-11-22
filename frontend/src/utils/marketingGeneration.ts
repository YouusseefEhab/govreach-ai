import type { TextGenerationRequest } from '../types/api'

export function marketingGenerationRequest(override: string): TextGenerationRequest {
  const audience = override.trim()
  return audience ? { audience } : {}
}
