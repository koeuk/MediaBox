<script setup lang="ts">
const { register } = useAuth()

const email = ref('')
const username = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  error.value = ''
  busy.value = true
  try {
    await register(email.value, username.value, password.value)
    await navigateTo('/')
  } catch (e) {
    error.value = errorMessage(e, 'Registration failed.')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AuthCard
    tagline="Your personal media manager"
    title="Create account"
    :error="error"
    @submit="submit"
  >
    <label class="label" for="email">Email</label>
    <input id="email" v-model="email" class="input" type="email" required autocomplete="email" placeholder="you@example.com" />

    <label class="label" for="username">Username</label>
    <input id="username" v-model="username" class="input" type="text" required minlength="2" maxlength="80" autocomplete="username" placeholder="yourname" />

    <label class="label" for="password">Password</label>
    <PasswordInput id="password" v-model="password" :minlength="6" autocomplete="new-password" placeholder="Min. 6 characters" />

    <button class="btn btn-accent" type="submit" :disabled="busy">
      {{ busy ? 'Creating…' : 'Create account' }}
    </button>

    <template #footer>
      Already registered?
      <NuxtLink to="/login">Sign in</NuxtLink>
    </template>
  </AuthCard>
</template>
