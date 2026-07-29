/**
 * The current user's profile picture, ready to drop into an <img>.
 *
 * Lives here rather than in useApi because it needs three things stitched
 * together — the media token, `has_avatar`, and the cache-busting version —
 * and both the navbar and the profile page want the same result.
 */
export function useAvatar() {
  const config = useRuntimeConfig()
  const { user, avatarVersion } = useAuth()
  const { mediaToken, refreshMediaToken } = useApi()

  /** null when there is no picture, or no token to fetch it with yet. */
  const src = computed(() => {
    if (!user.value?.has_avatar || !mediaToken.value) return null
    const base = config.public.apiBase
    return `${base}/auth/me/avatar?token=${mediaToken.value}&v=${avatarVersion.value}`
  })

  /** Fallback shown in place of a picture: one or two letters from the name. */
  const initials = computed(() => {
    const name = (user.value?.username || user.value?.email || '').trim()
    if (!name) return '?'
    const words = name.split(/[\s._-]+/).filter(Boolean)
    const letters = words.length > 1 ? words[0]![0]! + words[1]![0]! : name.slice(0, 2)
    return letters.toUpperCase()
  })

  // Pages that don't otherwise touch media still need a token to show the
  // picture. This has to be reactive, not a one-shot check on mount: `user` is
  // usually still null then (the page fetches it asynchronously), and
  // has_avatar also flips to true mid-session on the first upload.
  // shared, not a local: the navbar, app.vue and the profile page each hold an
  // instance of this composable and would otherwise all mint at once
  const minting = useState('avatar-token-minting', () => false)

  async function ensureToken() {
    // also guarded because refreshMediaToken nulls the token when it fails,
    // which would otherwise retrigger this watcher forever
    if (minting.value || mediaToken.value) return
    minting.value = true
    try {
      await refreshMediaToken()
    } finally {
      minting.value = false
    }
  }

  if (import.meta.client) {
    watch(
      () => user.value?.has_avatar,
      (has) => {
        if (has) ensureToken()
      },
      { immediate: true }
    )
  }

  return { src, initials }
}
