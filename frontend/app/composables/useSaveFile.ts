/**
 * "Save As" with a real location picker where the browser has one.
 *
 * Chromium exposes the File System Access API (`showSaveFilePicker`), which
 * opens the native save dialog and lets the user pick folder + filename; the
 * file is then streamed straight from the API into that location. Firefox and
 * Safari don't have it, so the save anchors keep their normal `href download`
 * behavior there — `interceptSave` simply lets the click fall through.
 */
export function useSaveFile() {
  const supported = typeof window !== 'undefined' && 'showSaveFilePicker' in window

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
   * Click handler for save anchors. With the picker available it takes over
   * the click; without it, it does nothing and the anchor downloads normally.
   */
  function interceptSave(event: MouseEvent, url: string, suggestedName: string) {
    if (!supported) return
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

  return { supported, saveAs, interceptSave }
}
