<script setup lang="ts">
const { login } = useAuth()
const route = useRoute()

const email = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  error.value = ''
  busy.value = true
  try {
    await login(email.value, password.value)
    await navigateTo('/')
  } catch (e) {
    error.value = errorMessage(e, 'Login failed. Check your credentials.')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AuthCard flat tagline="Download · Organize · Manage" title="Sign in" :error="error" @submit="submit">
    <p v-if="route.query.password_changed === '1'" class="password-changed" role="status">Password updated. Sign in again with your new password.</p>
    <label class="label" for="email">Email</label>
    <input id="email" v-model="email" class="input" type="email" required autocomplete="email" placeholder="you@example.com" />

    <label class="label" for="password">Password</label>
    <PasswordInput id="password" v-model="password" autocomplete="current-password" placeholder="••••••••" />

    <NuxtLink to="/forgot-password" class="forgot-link">Forgot password?</NuxtLink>

    <button class="btn btn-accent" type="submit" :disabled="busy">
      {{ busy ? 'Signing in…' : 'Sign in' }}
    </button>

    <NuxtLink to="/free" class="btn btn-ghost guest-link">Download without signing in</NuxtLink>

    <template #footer>
      No account?
      <NuxtLink to="/register">Create one</NuxtLink>
    </template>
  </AuthCard>
</template>

<style scoped>
.password-changed { margin: 0; color: var(--text-dim); font-size: 0.82rem; line-height: 1.5; }
.forgot-link { align-self: flex-end; font-size: 0.78rem; color: var(--accent); }
.guest-link {
  display: flex;
  justify-content: center;
  text-decoration: none;
}
</style>
