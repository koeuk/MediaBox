export interface Download {
  id: number
  url: string
  title: string | null
  filename: string | null
  status: 'queued' | 'downloading' | 'completed' | 'failed'
  progress: number
  total_bytes: number
  downloaded_bytes: number
  content_type: string | null
  quality: string | null
  error: string | null
  is_favorite: boolean
  has_thumbnail: boolean
  can_retry: boolean
  created_at: string
  completed_at: string | null
}

export function useApi() {
  const config = useRuntimeConfig()
  const { token } = useAuth()
  // short-lived, media-scoped token — the only one allowed to appear in URLs
  const mediaToken = useState<string | null>('media-token', () => null)

  function request<T>(path: string, opts: Record<string, any> = {}) {
    return $fetch<T>(path, {
      baseURL: config.public.apiBase,
      ...opts,
      headers: {
        ...(token.value ? { Authorization: `Bearer ${token.value}` } : {}),
        ...(opts.headers || {}),
      },
    })
  }

  /** Mint a fresh media token; call on page load and every few minutes. */
  async function refreshMediaToken() {
    if (!token.value) return
    try {
      const res = await request<{ token: string; expires_in: number }>('/auth/media-token', {
        method: 'POST',
      })
      mediaToken.value = res.token
    } catch {
      mediaToken.value = null
    }
  }

  /** URL for <img>/<a> tags — auth via a short-lived ?token= since headers can't be set there. */
  function fileUrl(id: number, kind: 'file' | 'thumbnail') {
    return `${config.public.apiBase}/downloads/${id}/${kind}?token=${mediaToken.value}`
  }

  /** ws:// URL for the live-progress socket, derived from the API base. */
  function wsUrl() {
    const base = config.public.apiBase
    const abs = base.startsWith('http') ? base : `${location.origin}${base}`
    return `${abs.replace(/^http/, 'ws')}/ws/progress?token=${mediaToken.value}`
  }

  return { request, fileUrl, wsUrl, mediaToken, refreshMediaToken }
}
