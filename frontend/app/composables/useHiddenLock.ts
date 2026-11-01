/**
 * Tracks the unlocked state of the hidden media section.
 *
 * If the user has a hidden password configured (`user.has_hidden_password`),
 * the hidden section remains locked (`isLocked === true`) until verified.
 */
export function useHiddenLock() {
  const { user } = useAuth()
  const { request } = useApi()

  // State is per-session in memory; auto-locks on navigation or setting update
  const isUnlocked = useState<boolean>('hidden-is-unlocked', () => false)
  const isPromptOpen = useState<boolean>('hidden-unlock-prompt-open', () => false)

  const isProtected = computed(() => Boolean(user.value?.has_hidden_password))
  const isLocked = computed(() => isProtected.value && !isUnlocked.value)

  async function unlock(password: string) {
    await request<{ unlocked: boolean }>('/auth/verify-hidden-password', {
      method: 'POST',
      body: { password },
    })
    isUnlocked.value = true
    isPromptOpen.value = false
    return true
  }

  function lock() {
    isUnlocked.value = false
    isPromptOpen.value = false
    if (import.meta.client) {
      try {
        sessionStorage.removeItem('mb_hidden_unlocked')
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
    openUnlockModal,
    closeUnlockModal,
  }
}
