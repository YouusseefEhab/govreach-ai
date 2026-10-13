
const API_BASE_URL = "http://localhost:8000"

export async function checkBackend() {
  const response = await fetch(`${API_BASE_URL}/health`)

  if (!response.ok) {
    throw new Error("Backend health check failed")
  }

  return response.json() as Promise<{ status: string }>
}
