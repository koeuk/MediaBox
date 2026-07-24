<script setup lang="ts">
import type { Download } from '~/composables/useApi'

const props = defineProps<{ download: Download | null }>()
const emit = defineEmits<{ close: [] }>()

const { fileUrl } = useApi()

const kind = computed(() => {
  const ct = props.download?.content_type || ''
  if (ct.startsWith('video/')) return 'video'
  if (ct.startsWith('audio/')) return 'audio'
  if (ct.startsWith('image/')) return 'image'
  return 'file'
})

const name = computed(
  () => props.download?.title || props.download?.filename || props.download?.url || ''
)

// captured once per open — a reactive fileUrl would swap src on every
// media-token refresh and restart playback
const src = ref('')
watch(
  () => props.download,
  (d) => {
    if (d) src.value = fileUrl(d.id, 'file')
  },
  { immediate: true }
)

const isZooming = ref(false)
let zoomTimeout: ReturnType<typeof setTimeout> | undefined

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
  if (props.download && e.key === 'Escape') emit('close')
}
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <Transition name="preview">
      <div v-if="download" class="overlay" @click.self="handleOverlayClick">
        <div
          class="frame panel"
          :class="{ 'is-zooming': isZooming }"
          role="dialog"
          aria-modal="true"
          :aria-label="name"
        >
          <header class="head">
            <h3 class="head-name" :title="name">{{ name }}</h3>
            <a
              class="btn btn-ghost head-btn"
              :href="fileUrl(download.id, 'file')"
              :download="download.filename || true"
            >
              Save
            </a>
            <button class="btn btn-ghost head-btn" aria-label="Close" @click="emit('close')">
              ✕
            </button>
          </header>

          <video v-if="kind === 'video'" class="media" :src="src" controls autoplay playsinline />
          <audio v-else-if="kind === 'audio'" class="media media-audio" :src="src" controls autoplay />
          <img v-else-if="kind === 'image'" class="media" :src="src" :alt="name" />
          <p v-else class="no-preview mono">No preview for this file type — use Save.</p>
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
  background: color-mix(in srgb, var(--bg) 78%, transparent);
  backdrop-filter: blur(6px);
}

.frame {
  width: min(920px, 100%);
  max-height: calc(100vh - 3rem);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: var(--shadow);
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.frame.is-zooming {
  transform: scale(1.04);
}

.head {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.65rem 0.65rem 0.65rem 1rem;
  border-bottom: 1px solid var(--line);
}

.head-name {
  flex: 1;
  margin: 0;
  font-size: 0.88rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.head-btn {
  padding: 0.4rem 0.7rem;
  font-size: 0.72rem;
}

.media {
  display: block;
  width: 100%;
  max-height: calc(100vh - 9rem);
  background: #000;
  object-fit: contain;
}

.media-audio {
  background: transparent;
  padding: 2.2rem 1.2rem;
}

.no-preview {
  margin: 0;
  padding: 2.5rem 1rem;
  text-align: center;
  font-size: 0.78rem;
  color: var(--text-dim);
}

.preview-enter-active,
.preview-leave-active {
  transition: opacity 0.15s ease;
}

.preview-enter-active .frame,
.preview-leave-active .frame {
  transition: transform 0.15s ease;
}

.preview-enter-from,
.preview-leave-to {
  opacity: 0;
}

.preview-enter-from .frame,
.preview-leave-to .frame {
  transform: translateY(10px) scale(0.98);
}
</style>
