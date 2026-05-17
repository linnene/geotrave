const DEFAULT_API_BASE_URL = 'http://localhost:8000'

export const apiConfig = {
  baseUrl: import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL,
}
