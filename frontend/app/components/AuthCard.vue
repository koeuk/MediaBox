<script setup lang="ts">
/**
 * Centred brand + form shell for /login and /register. The two pages differ
 * only in their fields and footer link, so everything else lives here.
 */
defineProps<{ tagline: string; title: string; error?: string }>()
const emit = defineEmits<{ submit: [] }>()
</script>

<template>
  <div class="auth-wrap">
    <div class="auth-brand reveal">
      <div class="wordmark display">Media<span>Box</span></div>
      <p class="label">{{ tagline }}</p>
    </div>

    <form
      class="panel panel-hover auth-card reveal"
      style="animation-delay: 0.08s"
      @submit.prevent="emit('submit')"
    >
      <h1 class="display auth-title">{{ title }}</h1>

      <p v-if="error" class="auth-error mono">{{ error }}</p>

      <slot />

      <p class="auth-alt">
        <slot name="footer" />
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

/* the submit button is the last thing before the footer link, whatever the
   page slots in above it */
.auth-card :deep(.btn) {
  margin-top: 0.6rem;
}

.auth-alt {
  margin: 0.4rem 0 0;
  font-size: 0.85rem;
  color: var(--text-dim);
  text-align: center;
}

.auth-alt :deep(a) {
  color: var(--accent);
  font-weight: 600;
}
</style>
