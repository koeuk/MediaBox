<script setup lang="ts">
import type { Download } from '~/types'

const props = withDefaults(
  defineProps<{
    download: Download | null
    downloads?: Download[]
  }>(),
  {
    downloads: () => [],
  }
)

const emit = defineEmits<{
  close: []
  select: [download: Download]
}>()

const { fileUrl, mediaToken } = useApi()
const autoNext = useCookie<'on' | 'off'>('mediabox_auto_next', {
  default: () => 'on',
  maxAge: 60 * 60 * 24 * 365,
})

const autoNextEnabled = computed({
  get: () => autoNext.value !== 'off',
  set: (enabled: boolean) => {
    autoNext.value = enabled ? 'on' : 'off'
  },
})

// Playlist of completed media items
const playlist = computed(() => {
  if (!props.downloads || props.downloads.length === 0) {
    return props.download ? [props.download] : []
  }
  const items = props.downloads.filter((d) => d.status === 'completed')
  if (!items.some((d) => d.id === props.download?.id) && props.download) {
    return [props.download, ...items]
  }
  return items.length > 0 ? items : (props.download ? [props.download] : [])
})

const currentIndex = computed(() => {
  if (!props.download) return -1
  return playlist.value.findIndex((d) => d.id === props.download!.id)
})

const mediaRef = ref<HTMLMediaElement>()
let replayAfterSelect = false

async function replayMediaFromStart() {
  await nextTick()
  const media = mediaRef.value
  if (!media) return

  media.pause()
  try {
    media.currentTime = 0
  } catch {
    // Some media formats reject seeking before metadata is ready.
  }
  media.load()
  void media.play().catch(() => {})
}

function selectAndReplay(item: Download) {
  if (item.id === props.download?.id) {
    void replayMediaFromStart()
    return
  }
  replayAfterSelect = true
  emit('select', item)
}

function selectItem(item: Download) {
  selectAndReplay(item)
}

function prevItem() {
  if (!playlist.value.length) return
  const prevIdx = currentIndex.value > 0 ? currentIndex.value - 1 : playlist.value.length - 1
  selectAndReplay(playlist.value[prevIdx]!)
}

function nextItem() {
  if (!playlist.value.length) return
  const nextIdx = currentIndex.value < playlist.value.length - 1 ? currentIndex.value + 1 : 0
  selectAndReplay(playlist.value[nextIdx]!)
}

/** Auto next advances through the playlist; Manual loops the current item.
 *
 * Deliberately stops on the last item instead of reusing nextItem()'s wrap —
 * the Next button cycling back to the start is a nudge, but autoplay doing it
 * would run the whole playlist forever.
 */
function onEnded() {
  if (!autoNextEnabled.value) {
    void replayMediaFromStart()
    return
  }
  if (currentIndex.value < 0) return
  const next = playlist.value[currentIndex.value + 1]
  if (next) selectAndReplay(next)
}

const kind = computed(() => mediaKind(props.download?.content_type))

const name = computed(
  () => props.download?.title || props.download?.filename || props.download?.url || ''
)

// captured per download open/change
const src = ref('')
watch(
  () => props.download,
  (d) => {
    if (d) src.value = fileUrl(d.id, 'file')
  },
  { immediate: true }
)

// Auto-scroll slider to active item
const sliderRef = ref<HTMLElement>()
const activeCardRef = ref<HTMLElement>()

function scrollSlider(offset: number) {
  if (sliderRef.value) {
    sliderRef.value.scrollBy({ left: offset, behavior: 'smooth' })
  }
}

watch(
  () => props.download?.id,
  () => {
    nextTick(() => {
      if (activeCardRef.value && sliderRef.value) {
        activeCardRef.value.scrollIntoView({
          behavior: 'smooth',
          inline: 'center',
          block: 'nearest',
        })
      }
    })
    if (replayAfterSelect) {
      replayAfterSelect = false
      void replayMediaFromStart()
    }
  }
)

/** Collapsed into the floating mini-player in the corner.
 *
 * Only ever toggles CSS classes and the *surrounding* markup — the <video>
 * node itself is never swapped out, so playback continues across the toggle.
 */
const minimized = ref(false)

// always reopen full-size for a newly opened item
watch(
  () => props.download?.id,
  (id) => {
    if (!id) minimized.value = false
  }
)

const isZooming = ref(false)
let zoomTimeout: ReturnType<typeof setTimeout> | undefined

function handleOverlayClick() {
  // no backdrop to click while minimized
  if (minimized.value) return
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
  if (!props.download) return
  if (e.key === 'Escape') {
    emit('close')
  } else if (e.key === 'ArrowLeft') {
    prevItem()
  } else if (e.key === 'ArrowRight') {
    nextItem()
  }
}

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <Transition name="preview">
      <div
        v-if="download"
        class="overlay"
        :class="{ minimized }"
        @click.self="handleOverlayClick"
      >
        <div
          class="frame panel"
          :class="{ 'is-zooming': isZooming, minimized }"
          role="dialog"
          :aria-modal="!minimized"
          :aria-label="name"
        >
          <header class="head">
            <h3 class="head-name" :title="name">{{ name }}</h3>

            <button
              class="btn btn-ghost head-btn head-icon"
              :title="minimized ? 'Expand to full view' : 'Collapse to mini player'"
              :aria-label="minimized ? 'Expand to full view' : 'Collapse to mini player'"
              :aria-expanded="!minimized"
              @click="minimized = !minimized"
            >
              <svg v-if="minimized" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
              </svg>
              <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M4 14h6v6M20 10h-6V4M14 10l7-7M3 21l7-7" />
              </svg>
            </button>

            <a
              v-if="download && !minimized"
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

          <div class="media-body">
            <video
              v-if="kind === 'video'"
              ref="mediaRef"
              class="media"
              :src="src"
              controls
              autoplay
              :loop="!autoNextEnabled"
              playsinline
              @ended="onEnded"
            />
            <audio
              v-else-if="kind === 'audio'"
              ref="mediaRef"
              class="media media-audio"
              :src="src"
              controls
              autoplay
              :loop="!autoNextEnabled"
              @ended="onEnded"
            />
            <img v-else-if="kind === 'image'" class="media" :src="src" :alt="name" />
            <p v-else class="no-preview mono">No preview for this file type — use Save.</p>
          </div>

          <!-- Bottom Card with Back/Next controls and Thumbnail Slider -->
          <div v-if="playlist.length > 0" class="bottom-card">
            <div class="nav-controls">
              <button
                class="btn btn-ghost nav-ctrl-btn"
                :disabled="playlist.length <= 1"
                title="Previous video (←)"
                @click="prevItem"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="m15 18-6-6 6-6" />
                </svg>
                Back
              </button>

              <div class="playback-options">
                <div class="playlist-counter mono" v-if="currentIndex !== -1">
                  {{ currentIndex + 1 }} / {{ playlist.length }}
                </div>

                <label
                  class="auto-next-toggle"
                  :class="{ on: autoNextEnabled }"
                  :title="autoNextEnabled ? 'Auto next is on' : 'Manual next only'"
                >
                  <input
                    v-model="autoNextEnabled"
                    type="checkbox"
                    aria-label="Automatically play the next video"
                  />
                  <span class="toggle-track" aria-hidden="true">
                    <span class="toggle-thumb" />
                  </span>
                  <span class="auto-next-label">
                    {{ autoNextEnabled ? 'Auto next' : 'Manual' }}
                  </span>
                </label>
              </div>

              <button
                class="btn btn-ghost nav-ctrl-btn"
                :disabled="playlist.length <= 1"
                title="Next video (→)"
                @click="nextItem"
              >
                Next
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="m9 18 6-6-6-6" />
                </svg>
              </button>
            </div>

            <div v-if="!minimized" class="slider-wrapper">
              <button
                type="button"
                class="slider-scroll-btn prev"
                title="Scroll carousel left"
                aria-label="Scroll carousel left"
                @click="scrollSlider(-240)"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="m15 18-6-6 6-6" />
                </svg>
              </button>

              <div class="slider-container" ref="sliderRef">
                <div
                  v-for="item in playlist"
                  :key="item.id"
                  class="slider-item"
                  :class="{ active: item.id === download?.id }"
                  :ref="(el) => { if (download && item.id === download.id) activeCardRef = el as HTMLElement }"
                  @click="selectItem(item)"
                >
                  <div class="slider-thumb">
                    <img
                      v-if="item.has_thumbnail && mediaToken"
                      :src="fileUrl(item.id, 'thumbnail')"
                      :alt="item.title || item.filename || ''"
                      loading="lazy"
                    />
                    <div v-else class="slider-thumb-fallback">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                        <rect x="2" y="4" width="20" height="16" rx="2" />
                        <path d="m10 9 5 3-5 3V9Z" fill="currentColor" />
                      </svg>
                    </div>
                    <span v-if="download && item.id === download.id" class="active-badge mono">Playing</span>
                  </div>
                  <div class="slider-title" :title="item.title || item.filename || item.url">
                    {{ item.title || item.filename || item.url }}
                  </div>
                </div>
              </div>

              <button
                type="button"
                class="slider-scroll-btn next"
                title="Scroll carousel right"
                aria-label="Scroll carousel right"
                @click="scrollSlider(240)"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="m9 18 6-6-6-6" />
                </svg>
              </button>
            </div>
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
  background: color-mix(in srgb, var(--bg) 78%, transparent);
  backdrop-filter: blur(6px);
}

.frame {
  width: min(920px, 100%);
  max-height: calc(100vh - 2.5rem);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: var(--shadow);
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), width 0.22s ease;
}

@media (prefers-reduced-motion: reduce) {
  .frame {
    transition: none;
  }
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

.head-icon {
  display: grid;
  place-items: center;
  padding: 0.4rem 0.5rem;
}

/* ---- collapsed mini player -------------------------------------------- */

/* the backdrop stops existing when collapsed, so the page underneath stays
   scrollable and clickable; the card itself opts back into pointer events */
.overlay.minimized {
  place-items: end;
  padding: 1rem;
  background: transparent;
  backdrop-filter: none;
  pointer-events: none;
}

.overlay.minimized .frame {
  pointer-events: auto;
}

.frame.minimized {
  width: min(340px, calc(100vw - 2rem));
  max-height: none;
  border: 1px solid var(--line);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.4);
}

.frame.minimized .head {
  padding: 0.4rem 0.4rem 0.4rem 0.75rem;
}

.frame.minimized .head-name {
  font-size: 0.74rem;
}

.frame.minimized .head-btn {
  padding: 0.3rem 0.45rem;
  font-size: 0.68rem;
}

.frame.minimized .media {
  max-height: 190px;
}

.frame.minimized .media-audio {
  padding: 0.9rem 0.6rem;
}

.frame.minimized .bottom-card {
  padding: 0.4rem 0.5rem;
  gap: 0;
}

.frame.minimized .nav-ctrl-btn {
  padding: 0.3rem 0.55rem;
  font-size: 0.68rem;
}

.frame.minimized .playlist-counter {
  font-size: 0.68rem;
}

.frame.minimized .nav-controls {
  gap: 0.4rem;
}

.frame.minimized .nav-ctrl-btn {
  min-width: 66px;
}

.frame.minimized .auto-next-toggle {
  min-height: 26px;
  padding: 0.2rem 0.35rem;
}

.frame.minimized .auto-next-label {
  display: none;
}

.media-body {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
}

.media {
  display: block;
  width: 100%;
  max-height: calc(100vh - 17rem);
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

.bottom-card {
  background: var(--surface);
  border-top: 1px solid var(--line);
  padding: 0.75rem 1rem 0.85rem;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.nav-controls {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: 0.75rem;
}

.nav-ctrl-btn:first-child {
  justify-self: start;
}

.nav-ctrl-btn:last-child {
  justify-self: end;
}

.playback-options {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  min-width: 0;
}

.nav-ctrl-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.35rem 0.8rem;
  font-size: 0.78rem;
  font-weight: 500;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--bg);
  min-width: 86px;
  justify-content: center;
}

.nav-ctrl-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.playlist-counter {
  flex: 0 0 auto;
  font-size: 0.72rem;
  color: var(--text-dim);
  background: var(--bg);
  padding: 0.25rem 0.7rem;
  border-radius: 12px;
  border: 1px solid var(--line);
}

.auto-next-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  min-height: 28px;
  padding: 0.2rem 0.55rem 0.2rem 0.35rem;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--bg);
  color: var(--text-dim);
  font-size: 0.7rem;
  font-weight: 600;
  line-height: 1;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
  transition: color 0.15s, background 0.15s, border-color 0.15s;
}

.auto-next-toggle:hover {
  color: var(--text);
  background: var(--surface-hover);
}

.auto-next-toggle input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.auto-next-toggle:focus-within {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.auto-next-toggle.on {
  border-color: color-mix(in srgb, var(--accent) 65%, var(--line));
  color: var(--text);
}

.toggle-track {
  position: relative;
  width: 30px;
  height: 16px;
  border-radius: 999px;
  background: var(--line-strong);
  transition: background 0.15s;
}

.auto-next-toggle.on .toggle-track {
  background: var(--accent);
}

.toggle-thumb {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--bg-raised);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.24);
  transition: transform 0.15s;
}

.auto-next-toggle.on .toggle-thumb {
  transform: translateX(14px);
}

.auto-next-label {
  width: auto;
  text-align: left;
}

.slider-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.45rem;
  width: 100%;
}

.slider-scroll-btn {
  flex: 0 0 32px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid var(--line);
  background: var(--bg);
  color: var(--text-dim);
  cursor: pointer;
  display: grid;
  place-items: center;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
  transition: color 0.15s, background 0.15s, border-color 0.15s, transform 0.15s;
  z-index: 2;
}

.slider-scroll-btn:hover {
  color: var(--text);
  background: var(--surface-hover);
  border-color: var(--accent);
  transform: scale(1.08);
}

.slider-scroll-btn:active {
  transform: scale(0.95);
}

.slider-container {
  flex: 1;
  min-width: 0;
  display: flex;
  gap: 0.65rem;
  overflow-x: auto;
  padding-bottom: 0.3rem;
  scrollbar-width: thin;
  scrollbar-color: var(--line-strong) transparent;
}

.slider-item {
  flex: 0 0 135px;
  cursor: pointer;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: var(--bg);
  overflow: hidden;
  transition: border-color 0.18s, transform 0.18s, box-shadow 0.18s;
  display: flex;
  flex-direction: column;
}

.slider-item:hover {
  border-color: var(--accent);
  transform: translateY(-2px);
}

.slider-item.active {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--accent-soft);
  background: var(--surface-hover);
}

.slider-thumb {
  position: relative;
  aspect-ratio: 16 / 9;
  background: #000;
  overflow: hidden;
}

.slider-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.slider-thumb-fallback {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  color: var(--text-faint);
  background: repeating-linear-gradient(-45deg, transparent 0 10px, color-mix(in srgb, var(--line) 45%, transparent) 10px 11px);
}

.active-badge {
  position: absolute;
  bottom: 3px;
  right: 3px;
  font-size: 0.58rem;
  font-weight: 600;
  padding: 1px 4px;
  border-radius: 3px;
  background: var(--accent);
  color: var(--accent-ink);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.slider-title {
  font-size: 0.7rem;
  padding: 0.35rem 0.5rem;
  color: var(--text-dim);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.slider-item.active .slider-title {
  color: var(--text);
  font-weight: 600;
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

@media (max-width: 560px) {
  .overlay {
    padding: 0.75rem;
  }

  .nav-controls {
    grid-template-columns: auto minmax(0, 1fr) auto;
    gap: 0.45rem;
  }

  .nav-ctrl-btn {
    min-width: 0;
    padding: 0.35rem 0.55rem;
  }

  .playback-options {
    gap: 0.35rem;
  }

  .playlist-counter {
    padding: 0.25rem 0.55rem;
  }

  .auto-next-toggle {
    padding: 0.2rem 0.35rem;
  }

  .auto-next-label {
    display: none;
  }
}
</style>
