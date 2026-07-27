import type { User } from '~/types'

interface TokenOut {
  access_token: string
  token_type: string
  user: User
}

export function useAuth() {
  const token = useCookie<string | null>('mediabox_token', {
    maxAge: 60 * 60 * 24 * 7,
    sameSite: 'lax',
  })
  const user = useState<User | null>('auth-user', () => null)
  const config = useRuntimeConfig()

  async function login(email: string, password: string) {
    const res = await $fetch<TokenOut>('/auth/login', {
      baseURL: config.public.apiBase,
      method: 'POST',
      body: { email, password },
    })
    token.value = res.access_token
    user.value = res.user
  }

  async function register(email: string, username: string, password: string) {
    const res = await $fetch<TokenOut>('/auth/register', {
      baseURL: config.public.apiBase,
      method: 'POST',
      body: { email, username, password },
    })
    token.value = res.access_token
    user.value = res.user
  }

  async function fetchUser() {
    if (!token.value) return
    try {
      user.value = await $fetch<User>('/auth/me', {
        baseURL: config.public.apiBase,
        headers: { Authorization: `Bearer ${token.value}` },
      })
    } catch {
      token.value = null
      user.value = null
    }
  }

  async function updateProfile(payload: {
    username?: string
    email?: string
    current_password?: string
    new_password?: string
  }) {
    user.value = await $fetch<User>('/auth/me', {
      baseURL: config.public.apiBase,
      method: 'PATCH',
      headers: { Authorization: `Bearer ${token.value}` },
      body: payload,
    })
  }

  function logout() {
    token.value = null
    user.value = null
    return navigateTo('/login')
  }

  return { token, user, login, register, fetchUser, updateProfile, logout }
}
