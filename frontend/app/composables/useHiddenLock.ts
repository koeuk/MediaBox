/**
 * Tracks the unlocked state of the hidden media section for the current session.
 *
 * If the user has a hidden password configured (`user.has_hidden_password`),
 * the hidden section remains locked (`isLocked === true`) until verified.
 */
export function useHiddenLock() {
  const { user } = useAuth()
  const { request } = useApi()

  const isUnlocked = useState<boolean>('hidden-is-unlocked', () => false)
  const isPromptOpen = useState<boolean>('hidden-unlock-prompt-open', () => false)

  if (import.meta.client && !isUnlocked.value) {
    try {
      if (sessionStorage.getItem('mb_hidden_unlocked') === '1') {
        isUnlocked.value = true
      }
    } catch {}
  }

  const isProtected = computed(() => Boolean(user.value?.has_hidden_password))
  const isLocked = computed(() => isProtected.value && !isUnlocked.value)

  async function unlock(password: string) {
    await request<{ unlocked: boolean }>('/auth/verify-hidden-password', {
      method: 'POST',
      body: { password },
    })
    isUnlocked.value = true
    if (import.meta.client) {
      try {
        sessionStorage.setItem('mb_hidden_unlocked', '1')
      } catch {}
    }
    isPromptOpen.value = false
    return true
  }

  function lock() {
    isUnlocked.value = false
    if (import.meta.client) {
      try {
        sessionStorage.removeItem('mb_hidden_unlocked')
      } catch {}
    }
  }

  function markUnlocked() {
    isUnlocked.value = true
    if (import.meta.client) {
      try {
        sessionStorage.setItem('mb_hidden_unlocked', '1')
      } catch {}
    }
  }

  function openUnlockModal() {
    isPromptOpen.value = true
  }

  function closeUnlockModal() {
    isPromptOpen.value = false
  }

  return {
    isUnlocked,
    isProtected,
    isLocked,
    isPromptOpen,
    unlock,
    lock,
    markUnlocked,
    openUnlockModal,
    closeUnlockModal,
  }
}
