const DEFAULT_API_BASE_URL = ''

export const apiConfig = {
  baseUrl: import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL,
}
