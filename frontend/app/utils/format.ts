/** Display formatters. Auto-imported by Nuxt from `app/utils/`. */

const BYTE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB']

/** `1536` → `"1.5 KB"`. Whole bytes stay integral; everything else gets 1 dp. */
export function formatBytes(n: number) {
  if (!n) return '0 B'
  const i = Math.min(Math.floor(Math.log(n) / Math.log(1024)), BYTE_UNITS.length - 1)
  return `${(n / 1024 ** i).toFixed(i === 0 ? 0 : 1)} ${BYTE_UNITS[i]}`
}

/** ISO timestamp → `"27 Jul 2026"`, in the viewer's locale. */
export function formatDate(s: string) {
  return new Date(s).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}
