<script setup lang="ts">
const { request } = useApi()
const email = ref('')
const busy = ref(false)
const error = ref('')
const message = ref('')

async function submit() {
  if (busy.value || message.value) return
  busy.value = true
  error.value = ''
  try {
    const result = await request<{ message: string }>('/auth/forgot-password', {
      method: 'POST', body: { email: email.value.trim() },
    })
    message.value = result.message
  } catch (e) {
    error.value = fieldErrorMessage(e, 'Could not request a reset link. Please try again.')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AuthCard tagline="Account recovery" title="Forgot password?" :error="error" @submit="submit">
    <template v-if="!message">
      <p class="reset-copy">Enter your account email. We’ll send a link to choose a new password.</p>
      <label class="label" for="reset-email">Email</label>
      <input id="reset-email" v-model="email" class="input" type="email" required autocomplete="email" placeholder="you@example.com" :disabled="busy" />
      <button class="btn btn-accent" type="submit" :disabled="busy">{{ busy ? 'Requesting…' : 'Send reset link' }}</button>
    </template>
    <template v-else>
      <p class="reset-copy" role="status">{{ message }}</p>
      <button class="btn btn-ghost" type="button" @click="message = ''">Use another email</button>
    </template>
    <template #footer><NuxtLink to="/login">Back to sign in</NuxtLink></template>
  </AuthCard>
</template>

<style scoped>
.reset-copy { margin: 0; color: var(--text-dim); font-size: 0.85rem; line-height: 1.6; }
</style>
