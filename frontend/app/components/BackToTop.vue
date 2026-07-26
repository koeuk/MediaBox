<script setup lang="ts">
const visible = ref(false)

function syncVisibility() {
  visible.value = window.scrollY > 520
}

function scrollTop() {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' })
}

onMounted(() => {
  syncVisibility()
  window.addEventListener('scroll', syncVisibility, { passive: true })
})

onUnmounted(() => {
  window.removeEventListener('scroll', syncVisibility)
})
</script>

<template>
  <button
    type="button"
    class="back-top"
    :class="{ show: visible }"
    aria-label="Back to top"
    title="Back to top"
    @click="scrollTop"
  >
    <svg
      width="19"
      height="19"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2.3"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <path d="m18 15-6-6-6 6" />
    </svg>
  </button>
</template>

<style scoped>
.back-top {
  position: fixed;
  right: max(1.25rem, env(safe-area-inset-right));
  bottom: max(1.25rem, env(safe-area-inset-bottom));
  z-index: 1001;
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border: 1px solid color-mix(in srgb, var(--accent) 48%, var(--line-strong));
  border-radius: 7px;
  background: color-mix(in srgb, var(--surface) 90%, transparent);
  color: var(--accent);
  box-shadow: var(--shadow);
  backdrop-filter: blur(10px);
  cursor: pointer;
  opacity: 0;
  pointer-events: none;
  transform: translateY(12px);
  transition:
    opacity 0.18s ease,
    transform 0.18s ease,
    background 0.15s,
    border-color 0.15s,
    color 0.15s;
}

.back-top.show {
  opacity: 1;
  pointer-events: auto;
  transform: translateY(0);
}

.back-top:hover {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--accent-ink);
}

.back-top:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px var(--accent-soft), var(--shadow);
}

.back-top:active {
  transform: translateY(1px);
}

@media (max-width: 560px) {
  .back-top {
    right: max(0.9rem, env(safe-area-inset-right));
    bottom: max(0.9rem, env(safe-area-inset-bottom));
    width: 42px;
    height: 42px;
  }
}
</style>
