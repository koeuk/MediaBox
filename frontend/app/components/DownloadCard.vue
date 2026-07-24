<script setup lang="ts">
import type { Download } from '~/composables/useApi'

const CATEGORIES = ['Coding', 'Fresh', 'Fun', 'View'] as const
type Category = (typeof CATEGORIES)[number]

const props = defineProps<{ download: Download }>()
const emit = defineEmits<{
  favorite: [id: number]
  remove: [id: number]
  retry: [id: number]
  convert: [payload: { id: number; target: string }]
  preview: [id: number]
  cancel: [id: number]
  setCategory: [payload: { id: number; category: string | null }]
}>()

const { fileUrl, mediaToken } = useApi()

const thumbBroken = ref(false)
// a fresh media token may fix a thumbnail that 401'd on an expired one
watch(mediaToken, () => (thumbBroken.value = false))

const name = computed(
  () => props.download.title || props.download.filename || props.download.url
)

const kind = computed(() => {
  const ct = props.download.content_type || ''
  if (ct.startsWith('video/')) return 'video'
  if (ct.startsWith('audio/')) return 'audio'
  if (ct.startsWith('image/')) return 'image'
  return 'file'
})

const active = computed(
  () => props.download.status === 'queued' || props.download.status === 'downloading'
)

function formatBytes(n: number) {
  if (!n) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.min(Math.floor(Math.log(n) / Math.log(1024)), units.length - 1)
  return `${(n / 1024 ** i).toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

const previewable = computed(
  () =>
    props.download.status === 'completed' &&
    ['video', 'audio', 'image'].includes(kind.value)
)

function onThumbClick() {
  if (previewable.value) emit('preview', props.download.id)
}

const convertTargets = computed(() =>
  kind.value === 'video'
    ? ['mp4', 'webm', 'gif', 'mp3', 'm4a', 'wav']
    : kind.value === 'audio'
      ? ['mp3', 'm4a', 'wav']
      : []
)

const catOpen = ref(false)
const catAnchor = ref<HTMLElement>()

function toggleCatMenu() {
  catOpen.value = !catOpen.value
}

function pickCategory(cat: Category | null) {
  emit('setCategory', { id: props.download.id, category: cat })
  catOpen.value = false
}

// Close on outside click
function onDocClick(e: MouseEvent) {
  if (catAnchor.value && !catAnchor.value.contains(e.target as Node)) {
    catOpen.value = false
  }
}
onMounted(() => document.addEventListener('click', onDocClick, true))
onUnmounted(() => document.removeEventListener('click', onDocClick, true))

const categoryColor: Record<string, string> = {
  Coding: 'cat-coding',
  Fresh: 'cat-fresh',
  Fun: 'cat-fun',
  View: 'cat-view',
}
</script>

<template>
  <article class="card panel" :class="{ active }">
    <div
      class="thumb"
      :class="{ clickable: previewable }"
      :title="previewable ? 'Click to preview' : undefined"
      @click="onThumbClick"
    >
      <span v-if="previewable" class="play-hint" aria-hidden="true">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
          <path d="m8 5 12 7-12 7V5Z" />
        </svg>
      </span>
      <img
        v-if="download.has_thumbnail && !thumbBroken && mediaToken"
        :src="fileUrl(download.id, 'thumbnail')"
        :alt="name"
        loading="lazy"
        @error="thumbBroken = true"
      />
      <div v-else class="thumb-fallback">
        <svg v-if="kind === 'video'" width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round">
          <rect x="2" y="4" width="20" height="16" rx="2" />
          <path d="m10 9 5 3-5 3V9Z" fill="currentColor" />
        </svg>
        <svg v-else-if="kind === 'audio'" width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 18V5l12-2v13" />
          <circle cx="6" cy="18" r="3" />
          <circle cx="18" cy="16" r="3" />
        </svg>
        <svg v-else-if="kind === 'image'" width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <circle cx="9" cy="9" r="2" />
          <path d="m21 15-4.5-4.5L6 21" />
        </svg>
        <svg v-else width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8L14 2Z" />
          <path d="M14 2v6h6" />
        </svg>
      </div>

      <span class="badge status" :class="`badge-${download.status}`">
        <span v-if="active" class="dot" />
        {{ download.status }}
      </span>

      <button
        class="fav"
        :class="{ on: download.is_favorite }"
        :title="download.is_favorite ? 'Unfavorite' : 'Favorite'"
        @click.stop="emit('favorite', download.id)"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" :fill="download.is_favorite ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2" stroke-linejoin="round">
          <path d="M12 2l3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1L12 2Z" />
        </svg>
      </button>
    </div>

    <div class="body">
      <h3 class="name" :title="name">{{ name }}</h3>
      <p class="url mono" :title="download.url">{{ download.url }}</p>

      <div v-if="active" class="progress">
        <div class="progress-track">
          <div class="progress-fill" :style="{ width: `${Math.max(download.progress, 2)}%` }" />
        </div>
        <div class="progress-meta mono">
          <span>{{ download.progress.toFixed(0) }}%</span>
          <span v-if="download.total_bytes">
            {{ formatBytes(download.downloaded_bytes) }} / {{ formatBytes(download.total_bytes) }}
          </span>
          <span v-else>{{ formatBytes(download.downloaded_bytes) }}</span>
        </div>
      </div>

      <p v-else-if="download.status === 'failed'" class="error mono" :title="download.error || ''">
        {{ download.error || 'Download failed' }}
      </p>

      <p v-else class="meta mono">
        {{ formatBytes(download.total_bytes) }}
        <span v-if="download.content_type"> · {{ download.content_type }}</span>
      </p>

      <!-- Category tag pill + dropdown -->
      <div class="cat-wrap" ref="catAnchor">
        <button
          class="cat-pill mono"
          :class="download.category ? categoryColor[download.category] : 'cat-none'"
          :title="download.category ? `Category: ${download.category}` : 'Set category'"
          @click.stop="toggleCatMenu"
        >
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2H2v10l9.29 9.29a1 1 0 0 0 1.41 0l7.29-7.29a1 1 0 0 0 0-1.41L12 2Z" />
            <circle cx="7" cy="7" r="1.5" fill="currentColor" stroke="none" />
          </svg>
          {{ download.category || 'Tag' }}
          <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
            <path d="m6 9 6 6 6-6" />
          </svg>
        </button>
        <Transition name="cat-drop">
          <div v-if="catOpen" class="cat-menu panel" role="menu">
            <button
              v-for="c in CATEGORIES"
              :key="c"
              class="cat-opt mono"
              :class="[categoryColor[c], { active: download.category === c }]"
              role="menuitem"
              @click.stop="pickCategory(c)"
            >
              <span class="cat-dot" />
              {{ c }}
            </button>
            <div class="cat-sep" />
            <button
              class="cat-opt cat-clear"
              role="menuitem"
              @click.stop="pickCategory(null)"
            >
              ✕ Clear
            </button>
          </div>
        </Transition>
      </div>

      <div class="actions">
        <a
          v-if="download.status === 'completed' && mediaToken"
          class="btn btn-accent"
          :href="fileUrl(download.id, 'file')"
          :download="download.filename || true"
        >
          Save
        </a>
        <button
          v-if="download.status === 'failed' && download.can_retry"
          class="btn btn-accent"
          @click="emit('retry', download.id)"
        >
          Retry
        </button>
        <button
          v-if="active"
          class="btn"
          title="Stop — you can resume with Retry"
          @click="emit('cancel', download.id)"
        >
          Stop
        </button>
        <ConvertMenu
          v-if="download.status === 'completed' && convertTargets.length"
          :targets="convertTargets"
          @pick="(target) => emit('convert', { id: download.id, target })"
        />
        <button
          class="btn btn-ghost btn-icon delete-btn"
          title="Delete"
          aria-label="Delete"
          @click="emit('remove', download.id)"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M3 6h18M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2m2 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
            <path d="M10 11v6M14 11v6" />
          </svg>
        </button>
      </div>
    </div>
  </article>
</template>

<style scoped>
.card {
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: border-color 0.15s, transform 0.15s, box-shadow 0.15s;
}

.card:hover {
  border-color: var(--line-strong);
  transform: translateY(-2px);
  box-shadow: var(--shadow);
}

.card.active {
  border-color: color-mix(in srgb, var(--accent) 45%, var(--line));
}

.thumb {
  position: relative;
  aspect-ratio: 16 / 9;
  background: var(--bg-raised);
  overflow: hidden;
}

.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.thumb.clickable {
  cursor: pointer;
}

.play-hint {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: grid;
  place-items: center;
  color: #fff;
  background: color-mix(in srgb, var(--bg) 35%, transparent);
  opacity: 0;
  transition: opacity 0.15s;
  pointer-events: none;
}

.play-hint svg {
  padding: 10px;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--accent) 90%, transparent);
  color: var(--accent-ink);
}

.thumb.clickable:hover .play-hint {
  opacity: 1;
}

.thumb-fallback {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  color: var(--text-faint);
  background:
    repeating-linear-gradient(-45deg, transparent 0 14px, color-mix(in srgb, var(--line) 45%, transparent) 14px 15px);
}

.status {
  position: absolute;
  top: 0.6rem;
  left: 0.6rem;
  backdrop-filter: blur(6px);
}

.fav {
  position: absolute;
  top: 0.45rem;
  right: 0.45rem;
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 6px;
  background: color-mix(in srgb, var(--bg) 62%, transparent);
  backdrop-filter: blur(6px);
  color: var(--text-dim);
  cursor: pointer;
  transition: color 0.15s, transform 0.12s;
}

.fav:hover {
  color: var(--accent);
  transform: scale(1.08);
}

.fav.on {
  color: var(--accent);
}

.body {
  padding: 0.9rem 1rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  flex: 1;
}

.name {
  margin: 0;
  font-size: 0.92rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.url {
  margin: 0;
  font-size: 0.68rem;
  color: var(--text-faint);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.progress {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-top: 0.2rem;
}

.progress-track {
  height: 6px;
  border-radius: 3px;
  background: var(--bg-raised);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
  background: repeating-linear-gradient(
    -55deg,
    var(--accent) 0 8px,
    var(--accent-strong) 8px 16px
  );
  background-size: 200% 100%;
  animation: slide 1.1s linear infinite;
  transition: width 0.4s ease;
}

@keyframes slide {
  to {
    background-position: -23px 0;
  }
}

.progress-meta {
  display: flex;
  justify-content: space-between;
  font-size: 0.66rem;
  color: var(--text-dim);
}

.meta {
  margin: 0;
  font-size: 0.68rem;
  color: var(--text-dim);
}

.error {
  margin: 0;
  font-size: 0.68rem;
  color: var(--err);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.actions {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 0.25rem;
  margin-top: auto;
  padding-top: 0.5rem;
}

.actions .btn {
  padding: 0.5rem 0.7rem;
  font-size: 0.72rem;
}

/* Delete pushed to the right edge, kept on the same row */
.delete-btn {
  margin-left: auto;
  color: var(--text-faint);
  border-color: var(--line-strong);
}

.delete-btn:hover {
  color: var(--err);
  border-color: var(--err);
  background: var(--err-soft);
}

/* ── Category pill & dropdown ── */
.cat-wrap {
  position: relative;
}

.cat-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.22rem 0.55rem;
  font-size: 0.62rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  border-radius: 20px;
  border: 1px solid var(--line);
  background: var(--surface);
  color: var(--text-dim);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}

.cat-pill:hover {
  border-color: var(--accent);
  color: var(--text);
}

.cat-none { color: var(--text-faint); }
.cat-coding { border-color: #6c8cff44; color: #7b9fff; background: #6c8cff14; }
.cat-fresh  { border-color: #40c97044; color: #3dca72; background: #40c97014; }
.cat-fun    { border-color: #f59e0b44; color: #f5a623; background: #f59e0b14; }
.cat-view   { border-color: #e879f944; color: #e879f9; background: #e879f914; }

.cat-menu {
  position: absolute;
  left: 0;
  top: calc(100% + 4px);
  z-index: 50;
  min-width: 130px;
  padding: 0.3rem;
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  box-shadow: var(--shadow);
}

.cat-opt {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.4rem 0.6rem;
  font-size: 0.7rem;
  font-weight: 500;
  border-radius: 5px;
  border: none;
  background: transparent;
  color: var(--text-dim);
  cursor: pointer;
  text-align: left;
  transition: background 0.12s, color 0.12s;
}

.cat-opt:hover {
  background: var(--surface-hover);
  color: var(--text);
}

.cat-opt.active {
  background: var(--surface-hover);
  font-weight: 700;
}

.cat-opt .cat-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}

.cat-coding .cat-dot { background: #7b9fff; }
.cat-fresh  .cat-dot { background: #3dca72; }
.cat-fun    .cat-dot { background: #f5a623; }
.cat-view   .cat-dot { background: #e879f9; }

.cat-sep {
  height: 1px;
  background: var(--line);
  margin: 0.2rem 0.3rem;
}

.cat-clear {
  font-size: 0.65rem;
  color: var(--text-faint);
}

.cat-drop-enter-active,
.cat-drop-leave-active {
  transition: opacity 0.12s, transform 0.12s;
}

.cat-drop-enter-from,
.cat-drop-leave-to {
  opacity: 0;
  transform: translateY(-4px) scale(0.97);
}

</style>
