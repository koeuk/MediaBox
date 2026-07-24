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
  } catch (e: any) {
    error.value = e?.data?.detail || 'Login failed. Check your credentials.'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="auth-wrap">
    <div class="auth-brand reveal">
      <div class="wordmark display">Media<span>Box</span></div>
      <p class="label">Download · Organize · Manage</p>
    </div>

    <form class="panel auth-card reveal" style="animation-delay: 0.08s" @submit.prevent="submit">
      <h1 class="display auth-title">Sign in</h1>

      <p v-if="error" class="auth-error mono">{{ error }}</p>

      <label class="label" for="email">Email</label>
      <input id="email" v-model="email" class="input" type="email" required autocomplete="email" placeholder="you@example.com" />

      <label class="label" for="password">Password</label>
      <PasswordInput id="password" v-model="password" autocomplete="current-password" placeholder="••••••••" />

      <button class="btn btn-accent" type="submit" :disabled="busy">
        {{ busy ? 'Signing in…' : 'Sign in' }}
      </button>

      <p class="auth-alt">
        No account?
        <NuxtLink to="/register">Create one</NuxtLink>
      </p>
    </form>
  </div>
</template>

<style scoped>
.auth-wrap {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2.2rem;
  padding: 1.5rem;
}

.auth-brand {
  text-align: center;
}

.wordmark {
  font-size: clamp(2.4rem, 6vw, 3.6rem);
  line-height: 1;
}

.wordmark span {
  color: var(--accent);
}

.auth-brand .label {
  margin-top: 0.6rem;
}

.auth-card {
  width: 100%;
  max-width: 380px;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  box-shadow: var(--shadow);
}

.auth-title {
  margin: 0 0 0.4rem;
  font-size: 1.15rem;
}

.auth-error {
  margin: 0;
  padding: 0.6rem 0.8rem;
  border-radius: 6px;
  background: var(--err-soft);
  color: var(--err);
  font-size: 0.78rem;
}

.auth-card .btn {
  margin-top: 0.6rem;
}

.auth-alt {
  margin: 0.4rem 0 0;
  font-size: 0.85rem;
  color: var(--text-dim);
  text-align: center;
}

.auth-alt a {
  color: var(--accent);
  font-weight: 600;
}
</style>
