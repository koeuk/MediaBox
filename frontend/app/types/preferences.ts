/**
 * Scaffold shape for the Preferences listing.
 *
 * Deliberately kept out of `types/index.ts` — that file holds shapes the API
 * actually returns, and this one is placeholder data. When the real endpoint
 * lands, move the interface there and delete this file.
 */

export interface VideoItem {
  id: number
  title: string
  source: string
  /** Pre-formatted "m:ss" — the real payload will send seconds instead. */
  duration: string
  size: string
  /** ISO date; rendered relative in the card. */
  added: string
  quality: string
  favorite: boolean
}
