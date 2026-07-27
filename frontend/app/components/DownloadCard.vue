<script setup lang="ts">
import type { Download } from '~/types'

const props = defineProps<{ download: Download }>()
const emit = defineEmits<{
  favorite: [id: number]
  remove: [id: number]
  retry: [id: number]
  convert: [payload: { id: number; target: string }]
  preview: [id: number]
  cancel: [id: number]
  info: [id: number]
  hide: [id: number]
  setCategory: [payload: { id: number; category: string | null }]
}>()

const { fileUrl, mediaToken } = useApi()
const { categories, loaded: catsLoaded, tint, colorOf } = useCategories()

const thumbBroken = ref(false)
// a fresh media token may fix a thumbnail that 401'd on an expired one
watch(mediaToken, () => (thumbBroken.value = false))

const name = computed(
  () => props.download.title || props.download.filename || props.download.url
)

const kind = computed(() => mediaKind(props.download.content_type))

const slideCount = computed(() => props.download.slide_count ?? 1)

const active = computed(
  () => props.download.status === 'queued' || props.download.status === 'downloading'
)

const previewable = computed(
  () => props.download.status === 'completed' && kind.value !== 'file'
)

function onThumbClick() {
  if (previewable.value) emit('preview', props.download.id)
}

const targets = computed(() => convertTargets(kind.value))

// cutouts are transparent PNGs — show a checkerboard so the alpha is legible
const transparent = computed(
  () => props.download.job_kind === 'cutout' || props.download.content_type === 'image/png'
)

const catOpen = ref(false)
const catAnchor = ref<HTMLElement>()
const catMenu = ref<HTMLElement>()
const menuPos = ref({ top: 0, left: 0 })
// hides the menu for the one frame between mount and measurement
const menuPlaced = ref(false)

// .cat-menu is position:fixed, so these are viewport coords — never add scrollY/scrollX
function placeCatMenu() {
  const anchor = catAnchor.value
  const menu = catMenu.value
  if (!anchor || !menu) return

  const rect = anchor.getBoundingClientRect()
  const { offsetHeight: h, offsetWidth: w } = menu
  const gap = 4
  const pad = 8

  // flip above the pill when there isn't room below
  let top = rect.bottom + gap
  if (top + h > window.innerHeight - pad) {
    top = Math.max(pad, rect.top - gap - h)
  }

  // keep it inside the right edge
  let left = rect.left
  if (left + w > window.innerWidth - pad) {
    left = Math.max(pad, window.innerWidth - pad - w)
  }

  menuPos.value = { top, left }
  menuPlaced.value = true
}

async function toggleCatMenu() {
  if (catOpen.value) {
    catOpen.value = false
    return
  }
  menuPlaced.value = false
  catOpen.value = true
  await nextTick()
  placeCatMenu()
}

function pickCategory(cat: string | null) {
  emit('setCategory', { id: props.download.id, category: cat })
  catOpen.value = false
}

// Close on outside click — the menu is teleported, so it needs its own containment check
function onDocClick(e: MouseEvent) {
  if (!catOpen.value) return
  const target = e.target as Node
  if (catAnchor.value?.contains(target) || catMenu.value?.contains(target)) return
  catOpen.value = false
}

// a fixed menu would detach from its card on scroll
function onScroll() {
  catOpen.value = false
}

onMounted(() => {
  document.addEventListener('click', onDocClick, true)
  window.addEventListener('scroll', onScroll, true)
  window.addEventListener('resize', onScroll)
})
onUnmounted(() => {
  document.removeEventListener('click', onDocClick, true)
  window.removeEventListener('scroll', onScroll, true)
  window.removeEventListener('resize', onScroll)
})

// a download can carry a tag whose category row was deleted — still show it,
// but only once the list has actually loaded, or every tag flashes as orphaned
const orphanTag = computed(
  () => catsLoaded.value && !!props.download.category && !colorOf(props.download.category)
)
</script>

<template>
  <article class="card panel" :class="{ active }">
    <div
      class="thumb"
      :class="{ clickable: previewable, 'alpha-grid': transparent }"
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

      <!-- a photo post is many images under one record; say so up front -->
      <span v-if="slideCount > 1" class="badge slides mono" :title="`${slideCount} photos`">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" aria-hidden="true">
          <rect x="8" y="3" width="13" height="13" rx="2" />
          <path d="M16 20H5a2 2 0 0 1-2-2V7" />
        </svg>
        {{ slideCount }}
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

      <Teleport to="body">
        <Transition name="cat-drop">
          <div
            v-if="catOpen"
            ref="catMenu"
            class="cat-menu panel"
            role="menu"
            :style="{
              top: menuPos.top + 'px',
              left: menuPos.left + 'px',
              visibility: menuPlaced ? 'visible' : 'hidden',
            }"
          >
            <button
              v-for="c in categories"
              :key="c.id"
              class="cat-opt mono"
              :class="{ active: download.category === c.name }"
              :style="{ color: c.color }"
              role="menuitem"
              @click.stop="pickCategory(c.name)"
            >
              <span class="cat-dot" :style="{ background: c.color }" />
              {{ c.name }}
            </button>

            <p v-if="!categories.length" class="cat-empty mono">
              No categories yet
            </p>

            <div class="cat-sep" />
            <button
              class="cat-opt cat-clear"
              role="menuitem"
              @click.stop="pickCategory(null)"
            >
              ✕ Clear
            </button>
            <NuxtLink to="/categories" class="cat-opt cat-manage" role="menuitem">
              ⚙ Manage…
            </NuxtLink>
          </div>
        </Transition>
      </Teleport>

      <div class="actions">
        <!-- Save lives in the ⋮ menu — CardMenu shows it under the same condition -->
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
          v-if="download.status === 'completed' && targets.length"
          :targets="targets"
          @pick="(target) => emit('convert', { id: download.id, target })"
        />

        <!-- Category tag pill; its dropdown is teleported to escape overflow:hidden -->
        <div class="cat-wrap">
          <button
            ref="catAnchor"
            class="cat-pill mono"
            :class="{ 'cat-none': !download.category, 'cat-orphan': orphanTag }"
            :style="tint(download.category)"
            :title="
              orphanTag
                ? `Category: ${download.category} (no longer in your list)`
                : download.category
                  ? `Category: ${download.category}`
                  : 'Set category'
            "
            @click.stop="toggleCatMenu"
          >
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 2H2v10l9.29 9.29a1 1 0 0 0 1.41 0l7.29-7.29a1 1 0 0 0 0-1.41L12 2Z" />
              <circle cx="7" cy="7" r="1.5" fill="currentColor" stroke="none" />
            </svg>
            <span class="cat-name">{{ download.category || 'Tag' }}</span>
            <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
              <path d="m6 9 6 6 6-6" />
            </svg>
          </button>
        </div>

        <CardMenu
          class="card-menu"
          :download="download"
          hideable
          @info="emit('info', download.id)"
          @hide="emit('hide', download.id)"
          @remove="emit('remove', download.id)"
        />
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
  /* background-color, not the shorthand — .alpha-grid supplies the layers */
  background-color: var(--bg-raised);
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

/* bottom-left, clear of the status badge above and the star opposite */
.slides {
  position: absolute;
  bottom: 0.6rem;
  left: 0.6rem;
  gap: 0.25rem;
  background: color-mix(in srgb, #000 62%, transparent);
  color: #fff;
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

/* The menu sits at the right edge, on the same row as Convert/Retry */
.card-menu {
  margin-left: auto;
}

.card-menu :deep(.kebab) {
  color: var(--text-faint);
  border: 1px solid var(--line-strong);
  border-radius: 6px;
}

.card-menu :deep(.kebab:hover) {
  color: var(--text);
  border-color: var(--text-faint);
}

/* ── Category pill & dropdown ── */
.cat-wrap {
  position: relative;
  /* lets the pill shrink instead of pushing the kebab out of the row */
  min-width: 0;
}

.cat-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  max-width: 100%;
  /* geometry mirrors ConvertMenu's .cm-trigger so the action row reads as one bar */
  gap: 0.35rem;
  padding: 0.5rem 0.7rem;
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  border-radius: 6px;
  border: 1px solid var(--line-strong);
  background: var(--surface);
  color: var(--text-dim);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}

.cat-pill svg {
  flex: none;
}

.cat-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cat-pill:hover {
  border-color: var(--accent);
  color: var(--text);
}

/* tag colours now come from the category record — see useCategories().tint */
.cat-none { color: var(--text-faint); }

/* a tag whose category was deleted: readable, but visibly not a live one */
.cat-orphan {
  border-style: dashed;
  opacity: 0.75;
}

.cat-menu {
  position: fixed;
  z-index: 9999;
  min-width: 140px;
  padding: 0.3rem;
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  box-shadow: 0 8px 24px rgba(0,0,0,0.25);
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

.cat-sep {
  height: 1px;
  background: var(--line);
  margin: 0.2rem 0.3rem;
}

.cat-clear,
.cat-manage {
  font-size: 0.65rem;
  color: var(--text-faint);
}

.cat-manage:hover {
  color: var(--accent);
}

.cat-empty {
  margin: 0;
  padding: 0.5rem 0.6rem;
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
