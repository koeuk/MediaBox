/**
 * The admin-uploaded site logo and site title, used in the navbar and favicon.
 * Served unauthenticated from /public/branding and /public/logo; `version` busts caches
 * after an update so every open tab updates without a reload.
 */
export function formatTitleParts(title: string): { first: string; highlight: string } {
  const clean = (title || 'MediaBox').trim()
  if (clean === 'MediaBox') {
    return { first: 'Media', highlight: 'Box' }
  }
  const spaceIdx = clean.lastIndexOf(' ')
  if (spaceIdx > 0) {
    return { first: clean.slice(0, spaceIdx + 1), highlight: clean.slice(spaceIdx + 1) }
  }
  return { first: clean, highlight: '' }
}

export function useBranding() {
  const config = useRuntimeConfig()
  const version = useState('branding-version', () => Date.now())
  const hasLogo = useState<boolean | null>('branding-has-logo', () => null)
  const siteTitle = useState<string>('branding-site-title', () => 'MediaBox')
  const probed = useState<boolean>('branding-probed', () => false)

  const logoUrl = computed(() => `${config.public.apiBase}/public/logo?v=${version.value}`)
  const titleParts = computed(() => formatTitleParts(siteTitle.value))

  async function fetchBranding() {
    try {
      const res = await $fetch<{ site_title: string; has_logo: boolean }>(
        `${config.public.apiBase}/public/branding?v=${version.value}`
      )
      siteTitle.value = res.site_title || 'MediaBox'
      hasLogo.value = res.has_logo
      probed.value = true
    } catch {
      // Fallback: probe logo directly
      if (hasLogo.value === null) {
        hasLogo.value = false
        fetch(logoUrl.value)
          .then((res) => (hasLogo.value = res.ok))
          .catch(() => {})
      }
    }
  }

  if (import.meta.client && !probed.value) {
    probed.value = true
    fetchBranding()
  }

  /** Call after the admin changes the logo or title, so state re-resolves everywhere. */
  function refresh(exists?: boolean, newTitle?: string) {
    version.value = Date.now()
    if (typeof exists === 'boolean') hasLogo.value = exists
    if (typeof newTitle === 'string') siteTitle.value = newTitle || 'MediaBox'
    if (exists === undefined && newTitle === undefined) {
      fetchBranding()
    }
  }

  return { logoUrl, hasLogo, siteTitle, titleParts, refresh, fetchBranding }
}
