import axios from 'axios'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20_000,
  headers: { 'Content-Type': 'application/json' },
})

interface Envelope {
  error?: { message?: string; details?: unknown }
}

/** Turn any Axios error into a readable message, using the backend's error envelope when present. */
export function toErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const envelope = error.response?.data as Envelope | undefined
    if (envelope?.error?.message) return envelope.error.message
    if (!error.response) return `Cannot reach the API at ${API_BASE_URL}. Is the backend running?`
    return `Request failed with status ${error.response.status}`
  }
  return error instanceof Error ? error.message : 'Unknown error'
}

export function errorDetails(error: unknown): unknown {
  if (axios.isAxiosError(error)) return (error.response?.data as Envelope | undefined)?.error?.details
  return undefined
}
