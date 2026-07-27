import type { CutoutQuality, Download } from '~/types'

/**
 * The download list and everything that mutates it: queueing, uploading,
 * per-card actions, and the live feed that keeps progress bars moving.
 *
 * Intended to be called once, by the media page. It owns network state only —
 * which tab is selected and which category is filtered are view concerns and
 * stay in the page.
 */
/** Rows produced by the background-removal page — its uploads and its results. */
const CUTOUT_KINDS = ['cutout', 'cutout_src']

export function useDownloads(scope: 'media' | 'cutout' = 'media') {
  const { request, wsUrl, refreshMediaToken } = useApi()

  /** Everything the server sent. The list endpoint and the live snapshot are
   *  both unscoped, so the split happens here. */
  const all = ref<Download[]>([])
  const loaded = ref(false)
  const live = ref(false)

  function inScope(d: Download) {
    const belongsToCutouts = CUTOUT_KINDS.includes(d.job_kind || '')
    return scope === 'cutout' ? belongsToCutouts : !belongsToCutouts
  }

  /** What this page should show. */
  const downloads = computed(() => all.value.filter(inScope))

  // form state for the submit bar, bound with v-model
  const url = ref('')
  const quality = ref('')
  const submitting = ref(false)
  const uploading = ref(false)

  const error = ref('')
  const note = ref('')

  // server-side filter, so a change has to round-trip
  const search = ref('')

  const activeCount = computed(() => downloads.value.filter(isActive).length)

  function isActive(d: Download) {
    return d.status === 'queued' || d.status === 'downloading'
  }

  /** Swap one row in place, keeping list order. */
  function replace(updated: Download) {
    const i = all.value.findIndex((d) => d.id === updated.id)
    if (i !== -1) all.value[i] = updated
  }

  function clearMessages() {
    error.value = ''
    note.value = ''
  }

  async function refresh() {
    const params: Record<string, string> = {}
    if (search.value) params.search = search.value
    all.value = await request<Download[]>('/downloads', { params })
    loaded.value = true
  }

  // ── Queueing ──────────────────────────────────────────────────────────

  async function submit() {
    const urls = url.value.split(/[\s,]+/).filter(Boolean)
    if (!urls.length) return
    clearMessages()
    submitting.value = true
    try {
      const q = quality.value || undefined
      if (urls.length === 1) {
        await request<Download>('/downloads', { method: 'POST', body: { url: urls[0], quality: q } })
      } else {
        await request<Download[]>('/downloads/batch', { method: 'POST', body: { urls, quality: q } })
        note.value = `${urls.length} downloads queued`
      }
      url.value = ''
      await refresh()
    } catch (e) {
      error.value = errorMessage(
        e,
        'Failed to queue download.',
        'Please enter valid URLs (each must start with http:// or https://)'
      )
    } finally {
      submitting.value = false
    }
  }

  /** Returns the records that were created, so callers can act on them. */
  async function upload(files: File[]): Promise<Download[]> {
    if (!files.length) return []
    clearMessages()
    uploading.value = true
    const created: Download[] = []
    try {
      // one request per file so a single rejected file doesn't lose the batch
      for (const f of files) {
        const form = new FormData()
        form.append('file', f)
        created.push(
          await request<Download>('/downloads/upload', {
            method: 'POST',
            body: form,
            // keeps cutout sources out of the media list
            params: scope === 'cutout' ? { scope: 'cutout' } : {},
          })
        )
      }
      note.value =
        files.length === 1
          ? 'Uploaded — use Convert… on the card to change format'
          : `${files.length} files uploaded`
      await refresh()
    } catch (e) {
      error.value = errorMessage(e, 'Upload failed.')
    } finally {
      uploading.value = false
    }
    return created
  }

  // ── Per-card actions ──────────────────────────────────────────────────

  async function toggleFavorite(id: number) {
    replace(await request<Download>(`/downloads/${id}/favorite`, { method: 'PATCH' }))
  }

  /** Keep a download out of the default views without deleting it. */
  async function toggleHidden(id: number) {
    try {
      replace(await request<Download>(`/downloads/${id}/hide`, { method: 'PATCH' }))
    } catch (e) {
      error.value = errorMessage(e, 'Could not hide that download.')
    }
  }

  async function setCategory(payload: { id: number; category: string | null }) {
    try {
      replace(
        await request<Download>(`/downloads/${payload.id}/category`, {
          method: 'PATCH',
          body: { category: payload.category },
        })
      )
    } catch (e) {
      error.value = errorMessage(e, 'Failed to update category.')
    }
  }

  async function retry(id: number) {
    try {
      replace(await request<Download>(`/downloads/${id}/retry`, { method: 'POST' }))
    } catch (e) {
      error.value = errorMessage(e, 'Retry failed.')
    }
  }

  async function cancel(id: number) {
    try {
      await request<Download>(`/downloads/${id}/cancel`, { method: 'POST' })
    } catch (e) {
      error.value = errorMessage(e, 'Could not stop the download.')
    }
  }

  async function convert(payload: { id: number; target: string }) {
    try {
      const created = await request<Download>(`/downloads/${payload.id}/convert`, {
        method: 'POST',
        body: { target: payload.target },
      })
      all.value = [created, ...all.value]
    } catch (e) {
      error.value = errorMessage(e, 'Conversion failed to start.')
    }
  }

  /** Queue a transparent-PNG cutout of an image already in the box. */
  async function removeBackground(id: number, cutoutQuality: CutoutQuality) {
    clearMessages()
    try {
      const created = await request<Download>(`/downloads/${id}/remove-background`, {
        method: 'POST',
        body: { quality: cutoutQuality },
      })
      all.value = [created, ...all.value]
      return created
    } catch (e) {
      error.value = errorMessage(e, 'Could not start background removal.')
      return null
    }
  }

  async function remove(id: number) {
    try {
      await request(`/downloads/${id}`, { method: 'DELETE' })
      all.value = all.value.filter((d) => d.id !== id)
    } catch (e) {
      error.value = errorMessage(e, 'Failed to delete — check that the server is running.')
    }
  }

  function find(id: number) {
    return all.value.find((d) => d.id === id) || null
  }

  // ── Live updates: WebSocket first, 2s polling as fallback ─────────────

  let ws: WebSocket | undefined
  let stopped = false
  let pollTimer: ReturnType<typeof setInterval> | undefined
  let tokenTimer: ReturnType<typeof setInterval> | undefined

  function connect() {
    if (stopped) return
    try {
      ws = new WebSocket(wsUrl())
    } catch {
      return
    }
    ws.onopen = () => (live.value = true)
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data)
        // ignore pushes while a server-side search filter is active
        if (msg.type === 'snapshot' && !search.value) {
          all.value = msg.items
          loaded.value = true
        }
      } catch {}
    }
    ws.onclose = () => {
      live.value = false
      if (!stopped) setTimeout(connect, 3000)
    }
  }

  /**
   * Call after the media token exists — the socket URL carries it, so
   * connecting earlier just burns a failed handshake and a 3s backoff.
   */
  function startLive() {
    connect()
    pollTimer = setInterval(() => {
      if (!live.value && activeCount.value > 0) refresh()
    }, 2000)
    // media tokens expire after 10 min — renew ahead of that
    tokenTimer = setInterval(refreshMediaToken, 8 * 60 * 1000)
  }

  function stopLive() {
    stopped = true
    ws?.close()
    clearInterval(pollTimer)
    clearInterval(tokenTimer)
  }

  onUnmounted(stopLive)

  // typing shouldn't fire a request per keystroke
  let searchDebounce: ReturnType<typeof setTimeout> | undefined
  watch(search, () => {
    clearTimeout(searchDebounce)
    searchDebounce = setTimeout(refresh, 300)
  })

  return {
    downloads,
    loaded,
    live,
    url,
    quality,
    submitting,
    uploading,
    error,
    note,
    search,
    activeCount,
    isActive,
    refresh,
    submit,
    upload,
    toggleFavorite,
    toggleHidden,
    setCategory,
    retry,
    cancel,
    convert,
    removeBackground,
    remove,
    find,
    startLive,
    stopLive,
  }
}
