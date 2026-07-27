<script setup lang="ts">
const { login } = useAuth()

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
  <AuthCard tagline="Download · Organize · Manage" title="Sign in" :error="error" @submit="submit">
    <label class="label" for="email">Email</label>
    <input id="email" v-model="email" class="input" type="email" required autocomplete="email" placeholder="you@example.com" />

    <label class="label" for="password">Password</label>
    <PasswordInput id="password" v-model="password" autocomplete="current-password" placeholder="••••••••" />

    <button class="btn btn-accent" type="submit" :disabled="busy">
      {{ busy ? 'Signing in…' : 'Sign in' }}
    </button>

    <template #footer>
      No account?
      <NuxtLink to="/register">Create one</NuxtLink>
    </template>
  </AuthCard>
</template>
