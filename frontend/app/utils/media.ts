/** Media-type helpers shared by the card, the preview and the convert menu. */

export type MediaKind = 'video' | 'audio' | 'image' | 'file'

/** Coarse media class from a MIME type — drives icons, preview and converts. */
export function mediaKind(contentType: string | null | undefined): MediaKind {
  const ct = contentType || ''
  if (ct.startsWith('video/')) return 'video'
  if (ct.startsWith('audio/')) return 'audio'
  if (ct.startsWith('image/')) return 'image'
  return 'file'
}

/** Formats ffmpeg can produce from a given source kind. Images aren't convertible. */
export function convertTargets(kind: MediaKind) {
  if (kind === 'video') return ['mp4', 'webm', 'gif', 'mp3', 'm4a', 'wav']
  if (kind === 'audio') return ['mp3', 'm4a', 'wav']
  return []
}
