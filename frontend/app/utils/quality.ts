/**
 * Which rungs of the quality ladder are behind the paid tier.
 *
 * Mirrors `PAID_QUALITIES` in the backend's library service, which is what
 * actually enforces this — anything here is a UI convenience, not a boundary.
 * '' means "best available", so it is the most expensive option rather than a
 * neutral default.
 */
export const PAID_QUALITIES = ['', '1080', '1440', '2160']

/** What a free account is defaulted to, and falls back to. */
export const FREE_QUALITY = '720'

export function isPaidQuality(quality: string | undefined | null): boolean {
  return PAID_QUALITIES.includes(quality || '')
}
