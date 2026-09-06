/**
 * The admin-uploaded site logo, used in the navbar and as the favicon.
 * Served unauthenticated from /public/logo; `version` busts caches after an
 * upload or removal so every open tab flips without a reload.
 */
export function useBranding() {
  const config = useRuntimeConfig()
  const version = useState('branding-version', () => Date.now())
  // null = not probed yet; the navbar/favicon only render the logo once true
  const hasLogo = useState<boolean | null>('branding-has-logo', () => null)

  const logoUrl = computed(() => `${config.public.apiBase}/public/logo?v=${version.value}`)

  if (import.meta.client && hasLogo.value === null) {
    hasLogo.value = false // settle a value in case the probe fails
    // GET, not HEAD: FastAPI routes don't answer HEAD; the byte cost is one
    // small image the navbar is about to fetch anyway
    fetch(logoUrl.value)
      .then((res) => (hasLogo.value = res.ok))
      .catch(() => {})
  }

  /** Call after the admin changes the logo, so URLs re-resolve everywhere. */
  function refresh(exists: boolean) {
    version.value = Date.now()
    hasLogo.value = exists
  }

  return { logoUrl, hasLogo, refresh }
}
