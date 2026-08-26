import type { Download } from '~/types'

/**
 * What the preview dialogs are showing, shared across the whole app.
 *
 * The dialogs are mounted once in `app.vue` rather than per page, so the
 * mini-player keeps playing while you move between Media, Reviews, Settings
 * and the rest — navigating away unmounts the page, not the <video> node.
 * Pages only say what to play; they never own the player.
 */
export function usePlayer() {
  const target = useState<Download | null>('player-target', () => null)

  /** The list the player steps through with Back/Next. Copied from the page's
   *  current view so it outlives that view: leaving the page keeps the
   *  playlist you were walking instead of emptying it. */
  const playlist = useState<Download[]>('player-playlist', () => [])

  /** Start playing `download`, stepping through `items`. */
  function open(download: Download | null, items: Download[] = []) {
    playlist.value = [...items]
    target.value = download
  }

  function close() {
    target.value = null
  }

  return { target, playlist, open, close }
}
