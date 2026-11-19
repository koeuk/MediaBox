/**
 * Where saved/downloaded files should land, chosen on the Profile page.
 *
 *   default — the browser's normal download (its Downloads folder)
 *   custom  — the backend copies finished files into a fixed folder
 *   ask     — a save dialog opens each time (Chromium only)
 *
 * Stored in localStorage: the choice is inherently per-browser — 'ask'
 * depends on this browser's picker support, 'default' on its settings.
 */
export type SaveMode = 'default' | 'custom' | 'ask'

const KEY = 'mediabox-save-prefs'

export function useSavePrefs() {
  const mode = useState<SaveMode>('save-mode', () => 'default')
  const customPath = useState<string>('save-custom-path', () => '')
  const hydrated = useState<boolean>('save-prefs-hydrated', () => false)

  if (import.meta.client && !hydrated.value) {
    hydrated.value = true
    try {
      const raw = localStorage.getItem(KEY)
      if (raw) {
        const p = JSON.parse(raw)
        if (p.mode === 'default' || p.mode === 'custom' || p.mode === 'ask') mode.value = p.mode
        if (typeof p.customPath === 'string') customPath.value = p.customPath
      }
    } catch {}
  }

  function save(nextMode: SaveMode, nextPath: string) {
    mode.value = nextMode
    customPath.value = nextPath
    try {
      localStorage.setItem(KEY, JSON.stringify({ mode: nextMode, customPath: nextPath }))
    } catch {}
  }

  return { mode, customPath, save }
}
