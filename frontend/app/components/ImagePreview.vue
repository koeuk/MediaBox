<script setup lang="ts">
import type { Download } from '~/types'

/**
 * Lightbox for still images.
 *
 * Deliberately separate from MediaPreview: a picture has no playback, so the
 * mini-player, auto-next and "Playing" badge are all meaningless for it. What
 * a picture does want — zoom, pan, and a checkerboard for transparency — has
 * no place in the video player either.
 */
const props = withDefaults(
  defineProps<{ download: Download | null; images?: Download[] }>(),
  { images: () => [] }
)

const emit = defineEmits<{ close: []; select: [download: Download] }>()

const { fileUrl } = useApi()

const name = computed(
  () => props.download?.title || props.download?.filename || props.download?.url || ''
)

const src = computed(() => (props.download ? fileUrl(props.download.id, 'file') : ''))

/** Other stills to step through, current one included. */
const gallery = computed(() => {
  const list = props.images.filter(
    (d) => d.status === 'completed' && (d.content_type || '').startsWith('image/')
  )
  if (props.download && !list.some((d) => d.id === props.download!.id)) {
    return [props.download, ...list]
  }
  return list
})

const index = computed(() =>
  props.download ? gallery.value.findIndex((d) => d.id === props.download!.id) : -1
)

function step(delta: number) {
  const list = gallery.value
  if (list.length < 2 || index.value < 0) return
  const next = (index.value + delta + list.length) % list.length
  emit('select', list[next]!)
}

// ── Zoom & pan ────────────────────────────────────────────────────────

const ZOOM_MIN = 1
const ZOOM_MAX = 8

const zoom = ref(1)
const pan = reactive({ x: 0, y: 0 })

function reset() {
  zoom.value = 1
  pan.x = 0
  pan.y = 0
}

function zoomBy(factor: number) {
  const next = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, zoom.value * factor))
  zoom.value = next
  // back at fit, a leftover offset would strand the image off-centre
  if (next === 1) {
    pan.x = 0
    pan.y = 0
  }
}

function onWheel(e: WheelEvent) {
  e.preventDefault()
  zoomBy(e.deltaY < 0 ? 1.15 : 1 / 1.15)
}

let dragging = false
let start = { x: 0, y: 0 }

function onPointerDown(e: PointerEvent) {
  if (zoom.value === 1) return
  dragging = true
  start = { x: e.clientX - pan.x, y: e.clientY - pan.y }
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
}

function onPointerMove(e: PointerEvent) {
  if (!dragging) return
  pan.x = e.clientX - start.x
  pan.y = e.clientY - start.y
}

function onPointerUp(e: PointerEvent) {
  dragging = false
  ;(e.currentTarget as HTMLElement).releasePointerCapture?.(e.pointerId)
}

// a different picture starts fresh rather than inheriting the last zoom
watch(() => props.download?.id, reset)

// transparency is the point of a cutout, so show it against a checkerboard
const checkered = ref(true)
const maybeTransparent = computed(
  () =>
    props.download?.job_kind === 'cutout' ||
    props.download?.content_type === 'image/png' ||
    props.download?.content_type === 'image/webp'
)

function onKey(e: KeyboardEvent) {
  if (!props.download) return
  if (e.key === 'Escape') emit('close')
  else if (e.key === 'ArrowLeft') step(-1)
  else if (e.key === 'ArrowRight') step(1)
  else if (e.key === '+' || e.key === '=') zoomBy(1.25)
  else if (e.key === '-') zoomBy(1 / 1.25)
  else if (e.key === '0') reset()
}

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <Transition name="preview">
      <div v-if="download" class="overlay" @click.self="emit('close')">
        <div class="frame panel" role="dialog" aria-modal="true" :aria-label="name">
          <header class="head">
            <h3 class="head-name" :title="name">{{ name }}</h3>

            <span v-if="gallery.length > 1" class="counter mono">
              {{ index + 1 }} / {{ gallery.length }}
            </span>

            <button
              v-if="maybeTransparent"
              class="btn btn-ghost head-btn"
              :title="checkered ? 'Hide the transparency checkerboard' : 'Show the transparency checkerboard'"
              :aria-pressed="checkered"
              @click="checkered = !checkered"
            >
              Alpha
            </button>

            <a
              class="btn btn-ghost head-btn"
              :href="src"
              :download="download.filename || true"
            >
              Save
            </a>
            <button class="btn btn-ghost head-btn" aria-label="Close" @click="emit('close')">
              ✕
            </button>
          </header>

          <div
            class="canvas"
            :class="{ 'alpha-grid': maybeTransparent && checkered, grabbable: zoom > 1 }"
            @wheel="onWheel"
            @pointerdown="onPointerDown"
            @pointermove="onPointerMove"
            @pointerup="onPointerUp"
            @pointercancel="onPointerUp"
            @dblclick="zoom > 1 ? reset() : zoomBy(2)"
          >
            <img
              class="shot"
              :src="src"
              :alt="name"
              :style="{
                transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                cursor: zoom > 1 ? (dragging ? 'grabbing' : 'grab') : 'zoom-in',
              }"
              draggable="false"
            />

            <button
              v-if="gallery.length > 1"
              class="step prev"
              title="Previous image (←)"
              aria-label="Previous image"
              @click.stop="step(-1)"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="m15 18-6-6 6-6" />
              </svg>
            </button>
            <button
              v-if="gallery.length > 1"
              class="step next"
              title="Next image (→)"
              aria-label="Next image"
              @click.stop="step(1)"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="m9 18 6-6-6-6" />
              </svg>
            </button>
          </div>

          <footer class="foot">
            <div class="zoom-group">
              <button class="btn btn-ghost btn-icon" title="Zoom out (−)" :disabled="zoom <= 1" @click="zoomBy(1 / 1.25)">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                  <circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5M8 11h6" />
                </svg>
              </button>
              <button class="zoom-level mono" title="Reset to fit (0)" @click="reset">
                {{ Math.round(zoom * 100) }}%
              </button>
              <button class="btn btn-ghost btn-icon" title="Zoom in (+)" :disabled="zoom >= 8" @click="zoomBy(1.25)">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                  <circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5M8 11h6M11 8v6" />
                </svg>
              </button>
            </div>

            <p class="meta mono">
              {{ download.content_type }}
              <span v-if="download.total_bytes"> · {{ formatBytes(download.total_bytes) }}</span>
            </p>
          </footer>
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
  background: color-mix(in srgb, #000 62%, transparent);
  backdrop-filter: blur(4px);
}

.frame {
  display: flex;
  flex-direction: column;
  width: min(1100px, 100%);
  max-height: 100%;
  overflow: hidden;
  box-shadow: var(--shadow);
}

.head {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 0.7rem 0.6rem 1rem;
  border-bottom: 1px solid var(--line);
}

.head-name {
  flex: 1;
  min-width: 0;
  margin: 0;
  font-size: 0.9rem;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.counter {
  font-size: 0.68rem;
  color: var(--text-faint);
  white-space: nowrap;
}

.head-btn {
  padding: 0.45rem 0.7rem;
  font-size: 0.72rem;
}

.canvas {
  position: relative;
  flex: 1;
  min-height: 0;
  display: grid;
  place-items: center;
  overflow: hidden;
  background-color: var(--bg);
  touch-action: none;
}

.canvas.grabbable {
  cursor: grab;
}

.shot {
  max-width: 100%;
  max-height: min(72vh, 760px);
  object-fit: contain;
  display: block;
  transition: transform 0.12s ease-out;
  user-select: none;
  -webkit-user-drag: none;
}

.step {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border: 1px solid var(--line);
  border-radius: 50%;
  background: color-mix(in srgb, var(--bg) 75%, transparent);
  color: var(--text);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}

.step:hover {
  background: var(--bg);
  border-color: var(--accent);
  color: var(--accent);
}

.step.prev {
  left: 0.7rem;
}

.step.next {
  right: 0.7rem;
}

.foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.55rem 1rem;
  border-top: 1px solid var(--line);
}

.zoom-group {
  display: flex;
  align-items: center;
  gap: 0.15rem;
}

.zoom-level {
  min-width: 56px;
  padding: 0.35rem 0.4rem;
  border: none;
  border-radius: 5px;
  background: transparent;
  color: var(--text-dim);
  font-size: 0.7rem;
  cursor: pointer;
}

.zoom-level:hover {
  color: var(--text);
  background: var(--surface-hover);
}

.meta {
  margin: 0;
  font-size: 0.68rem;
  color: var(--text-faint);
}

.preview-enter-active,
.preview-leave-active {
  transition: opacity 0.18s ease;
}

.preview-enter-active .frame,
.preview-leave-active .frame {
  transition: transform 0.18s cubic-bezier(0.2, 0.7, 0.2, 1);
}

.preview-enter-from,
.preview-leave-to {
  opacity: 0;
}

.preview-enter-from .frame,
.preview-leave-to .frame {
  transform: scale(0.97);
}

@media (max-width: 560px) {
  .overlay {
    padding: 0.6rem;
  }

  .meta {
    display: none;
  }
}
</style>
