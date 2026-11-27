export const GUEST_QUALITY_OPTIONS = [
  { value: '', label: 'Best', hint: 'auto' },
  { value: '2160', label: '4K', hint: '2160p' },
  { value: '1440', label: '1440p' },
  { value: '1080', label: '1080p' },
  { value: '720', label: '720p' },
  { value: '480', label: '480p' },
]

export interface GuestQualitySettings {
  qualities: string[]
  default_quality: string
}

export function guestQualityLabel(value: string): string {
  return GUEST_QUALITY_OPTIONS.find(option => option.value === value)?.label || value
}
