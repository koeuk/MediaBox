<script setup lang="ts">
const { isPromptOpen, unlock, closeUnlockModal } = useHiddenLock()
const router = useRouter()
const route = useRoute()

const password = ref('')
const busy = ref(false)
const err = ref('')
const isZooming = ref(false)
let zoomTimeout: ReturnType<typeof setTimeout> | undefined

watch(isPromptOpen, async (open) => {
  if (open) {
    password.value = ''
    err.value = ''
    busy.value = false
    await nextTick()
    const input = document.getElementById('modal-hidden-pw')
    input?.focus()
  }
})

function handleOverlayClick() {
  isZooming.value = false
  nextTick(() => {
    isZooming.value = true
    clearTimeout(zoomTimeout)
    zoomTimeout = setTimeout(() => {
      isZooming.value = false
    }, 250)
  })
}

function onKey(e: KeyboardEvent) {
  if (!isPromptOpen.value) return
  if (e.key === 'Escape') {
    close()
  }
}

function close() {
  password.value = ''
  err.value = ''
  closeUnlockModal()
}

async function handleUnlock() {
  if (!password.value || busy.value) return
  err.value = ''
  busy.value = true
  try {
    await unlock(password.value)
    password.value = ''
    if (route.path !== '/hidden') {
      await router.push('/hidden')
    }
  } catch (e: any) {
    err.value = errorMessage(e, 'Incorrect password. Please try again.')
  } finally {
    busy.value = false
  }
}

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <Transition name="dialog">
      <div v-if="isPromptOpen" class="overlay" @click.self="handleOverlayClick">
        <div
          class="dialog panel"
          :class="{ 'is-zooming': isZooming }"
          role="dialog"
          aria-modal="true"
          aria-labelledby="hidden-unlock-title"
        >
          <div class="lock-header">
            <div class="lock-icon-wrap">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
            </div>
            <div>
              <h3 id="hidden-unlock-title" class="dialog-title">Unlock Hidden Media</h3>
              <p class="dialog-message">Enter your password to access hidden items.</p>
            </div>
          </div>

          <form class="unlock-form" @submit.prevent="handleUnlock">
            <p v-if="err" class="msg err mono">{{ err }}</p>

            <label class="label sr-only" for="modal-hidden-pw">Password</label>
            <PasswordInput
              id="modal-hidden-pw"
              v-model="password"
              placeholder="Enter password"
              autocomplete="current-password"
            />

            <div class="dialog-actions">
              <button type="button" class="btn btn-ghost" :disabled="busy" @click="close">
                Cancel
              </button>
              <button
                type="submit"
                class="btn btn-accent"
                :disabled="busy || !password"
              >
                {{ busy ? 'Unlocking…' : 'Unlock' }}
              </button>
            </div>
          </form>
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
  max-width: 420px;
  padding: 1.5rem 1.6rem 1.4rem;
  box-shadow: var(--shadow);
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.dialog.is-zooming {
  transform: scale(1.04);
}

.lock-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.2rem;
}

.lock-icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 10px;
  background: color-mix(in srgb, var(--accent) 15%, transparent);
  color: var(--accent);
  flex-shrink: 0;
}

.dialog-title {
  margin: 0 0 0.25rem;
  font-size: 1.1rem;
  font-weight: 600;
}

.dialog-message {
  margin: 0;
  font-size: 0.85rem;
  line-height: 1.4;
  color: var(--text-dim);
}

.unlock-form {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 0.6rem;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
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
