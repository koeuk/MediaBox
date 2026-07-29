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

  /**
   * Replace the profile picture.
   *
   * `avatarVersion` bumps on every change: the URL is otherwise identical
   * before and after, so the browser would keep serving the cached old image.
   */
  const avatarVersion = useState('auth-avatar-version', () => 0)

  async function uploadAvatar(file: File) {
    const body = new FormData()
    body.append('file', file)
    user.value = await $fetch<User>('/auth/me/avatar', {
      baseURL: config.public.apiBase,
      method: 'PUT',
      headers: { Authorization: `Bearer ${token.value}` },
      body,
    })
    avatarVersion.value++
  }

  async function removeAvatar() {
    user.value = await $fetch<User>('/auth/me/avatar', {
      baseURL: config.public.apiBase,
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token.value}` },
    })
    avatarVersion.value++
  }

  function logout() {
    token.value = null
    user.value = null
    return navigateTo('/login')
  }

  return {
    token,
    user,
    avatarVersion,
    login,
    register,
    fetchUser,
    updateProfile,
    uploadAvatar,
    removeAvatar,
    logout,
  }
}
