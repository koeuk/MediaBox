/**
 * Saving files where the user wants them, driven by the Profile-page
 * preference (see useSavePrefs):
 *
 *   default — anchors keep their normal `href download` behavior
 *   custom  — the backend copies the file into the configured folder
 *             (browser pages can't write to a pasted path themselves;
 *             backend and browser run on the same machine, so it can)
 *   ask     — Chromium's File System Access API (`showSaveFilePicker`)
 *             opens the native dialog and the file streams straight into
 *             the picked location; browsers without it fall back to
 *             `default` behavior
 */

/**
 * Queued downloads picked a destination before the file existed; the targets
 * wait here (by download id) until the live feed reports them completed.
 * A string is a folder for the backend to copy into; a handle is a location
 * picked in the save dialog. Module scope on purpose: submit and the socket
 * run in different composable instances, and a page navigation must not drop
 * an armed save.
 */
const pendingSaves = new Map<number, FileSystemFileHandle | string>()

/** Tiny transient confirmation, since the app has no toast system. */
function toast(text: string, isError = false) {
  const el = document.createElement('div')
  el.textContent = text
  el.style.cssText =
    'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);' +
    'background:#1c1c1e;color:#f5f5f5;border:1px solid #3a3a3c;padding:10px 16px;' +
    'border-radius:8px;font:500 13px system-ui;z-index:9999;max-width:80vw;' +
    'box-shadow:0 4px 24px rgba(0,0,0,.4);transition:opacity .35s'
  if (isError) el.style.borderColor = '#b3403f'
  document.body.appendChild(el)
  setTimeout(() => {
    el.style.opacity = '0'
    setTimeout(() => el.remove(), 400)
  }, 3200)
}

export function useSaveFile() {
  const pickerSupported = typeof window !== 'undefined' && 'showSaveFilePicker' in window
  const { request } = useApi()
  const { mode, customPath } = useSavePrefs()

  async function exportTo(id: number, path: string) {
    const res = await request<{ saved_to: string }>(`/downloads/${id}/export`, {
      method: 'POST',
      body: { path },
    })
    return res.saved_to
  }

  async function saveAs(url: string, suggestedName: string) {
    // the picker must open inside the user gesture, before any await on fetch
    let handle: FileSystemFileHandle
    try {
      handle = await (window as any).showSaveFilePicker({ suggestedName })
    } catch (err: any) {
      if (err?.name === 'AbortError') return // user closed the dialog
      throw err
    }
    const res = await fetch(url)
    if (!res.ok || !res.body) throw new Error(`Download failed (${res.status})`)
    // pipeTo closes the writable once the stream ends
    await res.body.pipeTo(await handle.createWritable())
  }

  /**
   * Click handler for save anchors. Depending on the preference it either
   * lets the click fall through (default), copies server-side (custom, when
   * the caller can name the download id), or takes over with the picker (ask).
   */
  function interceptSave(event: MouseEvent, url: string, suggestedName: string, id?: number) {
    if (mode.value === 'custom' && customPath.value && id != null) {
      event.preventDefault()
      exportTo(id, customPath.value)
        .then((savedTo) => toast(`Saved to ${savedTo}`))
        .catch((err) => {
          console.error('Save failed:', err)
          toast(err?.data?.detail || 'Could not save to your folder', true)
        })
      return
    }
    if (mode.value !== 'ask' || !pickerSupported) return // plain browser download
    event.preventDefault()
    saveAs(url, suggestedName).catch((err) => {
      console.error('Save failed:', err)
      // the picker path failed mid-way; fall back to a plain download so the
      // user still gets the file
      const a = document.createElement('a')
      a.href = url
      a.download = suggestedName
      a.click()
    })
  }

  /**
   * Destination for a download that is about to be queued, decided inside the
   * click that queues it (the 'ask' dialog needs that gesture). Returns null
   * when the download should stay library-only.
   */
  async function pickQueueTarget(suggestedName: string): Promise<FileSystemFileHandle | string | null> {
    if (mode.value === 'custom' && customPath.value) return customPath.value
    if (mode.value !== 'ask' || !pickerSupported) return null
    try {
      return await (window as any).showSaveFilePicker({ suggestedName })
    } catch (err: any) {
      if (err?.name === 'AbortError') return null
      throw err
    }
  }

  /** Arm an auto-save: when download `id` completes, write it to `target`. */
  function armPendingSave(id: number, target: FileSystemFileHandle | string) {
    pendingSaves.set(id, target)
  }

  /**
   * Called with every fresh snapshot of the download list: sends finished
   * downloads to their chosen destinations, forgets failed/deleted ones.
   */
  function flushPendingSaves(
    items: { id: number; status: string }[],
    urlFor: (id: number) => string
  ) {
    for (const [id, target] of pendingSaves) {
      const d = items.find((x) => x.id === id)
      if (!d || d.status === 'failed') {
        pendingSaves.delete(id)
        continue
      }
      if (d.status !== 'completed') continue
      pendingSaves.delete(id)
      const done = typeof target === 'string'
        ? exportTo(id, target).then((savedTo) => toast(`Saved to ${savedTo}`))
        : fetch(urlFor(id)).then(async (res) => {
            if (!res.ok || !res.body) throw new Error(`fetch failed (${res.status})`)
            await res.body.pipeTo(await target.createWritable())
          })
      done.catch((err) => {
        console.error('Auto-save failed:', err)
        toast('Could not save the finished download to your folder', true)
      })
    }
  }

  return { pickerSupported, saveAs, interceptSave, pickQueueTarget, armPendingSave, flushPendingSaves }
}
