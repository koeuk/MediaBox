<script setup lang="ts">
const props = defineProps<{
  open: boolean
  title: string
  message?: string
  confirmLabel?: string
  danger?: boolean
}>()
const emit = defineEmits<{ confirm: []; cancel: [] }>()

const confirmBtn = ref<HTMLButtonElement>()

function onKey(e: KeyboardEvent) {
  if (!props.open) return
  if (e.key === 'Escape') emit('cancel')
}

watch(
  () => props.open,
  async (open) => {
    if (open) {
      await nextTick()
      confirmBtn.value?.focus()
    }
  }
)

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <Transition name="dialog">
      <div v-if="open" class="overlay" @click.self="emit('cancel')">
        <div class="dialog panel" role="dialog" aria-modal="true" :aria-label="title">
          <h3 class="dialog-title">{{ title }}</h3>
          <p v-if="message" class="dialog-message">{{ message }}</p>
          <div class="dialog-actions">
            <button class="btn btn-ghost" @click="emit('cancel')">Cancel</button>
            <button
              ref="confirmBtn"
              class="btn"
              :class="danger ? 'btn-danger' : 'btn-accent'"
              @click="emit('confirm')"
            >
              {{ confirmLabel || 'Confirm' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: grid;
  place-items: center;
  padding: 1.5rem;
  background: color-mix(in srgb, var(--bg) 65%, transparent);
  backdrop-filter: blur(4px);
}

.dialog {
  width: 100%;
  max-width: 400px;
  padding: 1.4rem 1.5rem 1.3rem;
  box-shadow: var(--shadow);
}

.dialog-title {
  margin: 0 0 0.5rem;
  font-size: 1.05rem;
  font-weight: 600;
}

.dialog-message {
  margin: 0;
  font-size: 0.85rem;
  line-height: 1.5;
  color: var(--text-dim);
  overflow-wrap: anywhere;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1.3rem;
}

.btn-danger {
  background: var(--err);
  border-color: var(--err);
  color: #fff;
}

.btn-danger:hover {
  filter: brightness(1.12);
}

.dialog-enter-active,
.dialog-leave-active {
  transition: opacity 0.15s ease;
}

.dialog-enter-active .dialog,
.dialog-leave-active .dialog {
  transition: transform 0.15s ease;
}

.dialog-enter-from,
.dialog-leave-to {
  opacity: 0;
}

.dialog-enter-from .dialog,
.dialog-leave-to .dialog {
  transform: translateY(8px) scale(0.98);
}
</style>
