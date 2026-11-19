<script setup lang="ts">
useHead({ meta: [{ name: 'referrer', content: 'no-referrer' }] })
const route = useRoute()
const { request, mediaToken } = useApi()
const { token: accessToken, user } = useAuth()
const resetToken = ref('')
const ready = ref(false)
const password = ref('')
const confirmation = ref('')
const busy = ref(false)
const error = ref('')
const done = ref(false)

function readResetLink(hash = window.location.hash) {
  const incoming = new URLSearchParams(hash.replace(/^#/, '')).get('token')
  if (incoming) {
    resetToken.value = incoming
    password.value = ''
    confirmation.value = ''
    error.value = ''
    done.value = false
    window.history.replaceState(window.history.state, '', window.location.pathname + window.location.search)
  }
  ready.value = true
}

function onHashChange() { readResetLink() }
watch(() => route.hash, hash => {
  if (import.meta.client && hash) readResetLink(hash)
})
onMounted(() => {
  readResetLink()
  window.addEventListener('hashchange', onHashChange)
})
onUnmounted(() => window.removeEventListener('hashchange', onHashChange))

async function submit() {
  if (busy.value || !resetToken.value || done.value) return
  error.value = ''
  if (password.value !== confirmation.value) {
    error.value = 'The passwords do not match.'
    return
  }
  busy.value = true
  const submittedToken = resetToken.value
  try {
    await request('/auth/reset-password', { method: 'POST', body: { token: submittedToken, new_password: password.value } })
    if (resetToken.value !== submittedToken) return
    accessToken.value = null
    user.value = null
    mediaToken.value = null
    resetToken.value = ''
    password.value = ''
    confirmation.value = ''
    done.value = true
  } catch (e) {
    if (resetToken.value === submittedToken) error.value = fieldErrorMessage(e, 'Could not reset your password. Please request a new link.')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AuthCard tagline="Account recovery" title="Reset password" :error="error" @submit="submit">
    <p v-if="!ready" class="reset-copy" role="status">Loading reset link…</p>
    <template v-else-if="done">
      <p class="reset-copy" role="status">Your password has been reset. Sign in with your new password.</p>
      <NuxtLink to="/login" class="btn btn-accent sign-in-link">Sign in</NuxtLink>
    </template>
    <template v-else-if="resetToken">
      <p class="reset-copy">Choose a new password for your account.</p>
      <label class="label" for="reset-password">New password</label>
      <PasswordInput id="reset-password" v-model="password" :minlength="6" :maxlength="128" :disabled="busy" autocomplete="new-password" placeholder="At least 6 characters" />
      <label class="label" for="confirm-reset-password">Confirm password</label>
      <PasswordInput id="confirm-reset-password" v-model="confirmation" :minlength="6" :maxlength="128" :disabled="busy" autocomplete="new-password" />
      <button class="btn btn-accent" type="submit" :disabled="busy">{{ busy ? 'Resetting…' : 'Reset password' }}</button>
    </template>
    <p v-else class="reset-copy">This reset link is missing. Open the link in your email or request a new one.</p>
    <template #footer><NuxtLink to="/forgot-password">Request a new reset link</NuxtLink></template>
  </AuthCard>
</template>

<style scoped>
.reset-copy { margin: 0; color: var(--text-dim); font-size: 0.85rem; line-height: 1.6; }
.sign-in-link { display: flex; justify-content: center; text-decoration: none; }
</style>
