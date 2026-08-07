/**
 * Shapes returned by the API. Types live here rather than next to the
 * composable that fetches them so a component can import `Download` without
 * dragging in `useApi`, and so both sides of a rename are in one file.
 */

export type DownloadStatus = 'queued' | 'downloading' | 'completed' | 'failed'

export interface Download {
  id: number
  url: string
  title: string | null
  filename: string | null
  status: DownloadStatus
  progress: number
  total_bytes: number
  downloaded_bytes: number
  content_type: string | null
  quality: string | null
  category?: string | null
  /** "cutout" for background removal; null for downloads and conversions. */
  job_kind?: string | null
  /** >1 for a multi-image post (a TikTok photo slideshow), else 1. */
  slide_count?: number
  error: string | null
  is_favorite: boolean
  /** Kept out of the default views without being deleted. */
  is_hidden?: boolean
  has_thumbnail: boolean
  can_retry: boolean
  created_at: string
  completed_at: string | null
}

export interface Category {
  id: number
  name: string
  color: string
  position: number
  created_at: string
  download_count: number
}

export interface User {
  id: number
  email: string
  username: string
  is_admin: boolean
  /** Whether a profile picture is set; fetch it from /auth/me/avatar. */
  has_avatar?: boolean
  created_at: string
}

/** Which pane of the grid is showing — not a server-side filter. */
export type DownloadFilter = 'all' | 'favorites' | 'active' | 'failed'

/** Background-removal quality tier; see backend services/bgremove.py. */
export type CutoutQuality = 'fast' | 'good' | 'best'

export interface Review {
  id: number
  author_name: string
  author_title: string | null
  rating: number
  body: string
  is_published: boolean
  created_at: string
  updated_at: string
}

export interface AdminStats {
  users: number
  downloads: number
  reviews: number
  queued: number
  downloading: number
  completed: number
  failed: number
  favorites: number
  bytes_stored: number
}

export interface AdminUser {
  id: number
  email: string
  username: string
  is_admin: boolean
  created_at: string
  download_count: number
  bytes_stored: number
}

export interface AdminDownload {
  id: number
  username: string
  title: string | null
  filename: string | null
  url: string
  status: DownloadStatus
  total_bytes: number
  created_at: string
}
