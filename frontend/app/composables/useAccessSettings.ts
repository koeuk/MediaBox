export function useAccessSettings() {
  const paidMode = useState<boolean>('access-paid-mode', () => true)
  const config = useRuntimeConfig()

  async function fetchAccessSettings() {
    try {
      const settings = await $fetch<{ paid_mode: boolean }>('/public/access-settings', {
        baseURL: config.public.apiBase,
        timeout: 5000,
      })
      paidMode.value = settings.paid_mode
    } catch {
      // Keep the last known mode; the backend enforces the current setting.
    }
  }

  return { paidMode, fetchAccessSettings }
}
