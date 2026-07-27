<script setup lang="ts">
import type { Download } from '~/types'

/**
 * Gallery tile for a cutout: the image and nothing else.
 *
 * A DownloadCard is built around a fixed 16:9 thumb with a meta block under
 * it, which crops the subject and buries the picture. Here the image sets the
 * tile's height and the controls float on top of it.
 */
const props = defineProps<{ download: Download }>()
const emit = defineEmits<{
  favorite: [id: number]
  remove: [id: number]
  retry: [id: number]
  cancel: [id: number]
  preview: [id: number]
  info: [id: number]
}>()

const { fileUrl, mediaToken } = useApi()

const broken = ref(false)
// a fresh media token may fix an image that 401'd on an expired one
watch(mediaToken, () => (broken.value = false))

const name = computed(() => props.download.title || props.download.filename || props.download.url)
const active = computed(
  () => props.download.status === 'queued' || props.download.status === 'downloading'
)
const ready = computed(() => props.download.status === 'completed')
const failed = computed(() => props.download.status === 'failed')
</script>

<template>
  <figure class="tile panel" :class="{ active, failed }">
    <div
      class="shot alpha-grid"
      :class="{ clickable: ready }"
      :title="ready ? name : undefined"
      @click="ready && emit('preview', download.id)"
    >
      <img
        v-if="ready && !broken && mediaToken"
        :src="fileUrl(download.id, 'file')"
        :alt="name"
        loading="lazy"
        @error="broken = true"
      />

      <div v-else class="placeholder">
        <span v-if="active" class="state mono">Removing… {{ download.progress }}%</span>
        <span v-else-if="failed" class="state mono err">{{ download.error || 'Failed' }}</span>
        <span v-else class="state mono">No preview</span>
      </div>

      <div v-if="active" class="bar" :style="{ width: `${download.progress}%` }" />
    </div>

    <div class="controls">
      <button
        class="chip"
        :class="{ on: download.is_favorite }"
        :title="download.is_favorite ? 'Remove from favorites' : 'Add to favorites'"
        :aria-label="download.is_favorite ? 'Remove from favorites' : 'Add to favorites'"
        @click.stop="emit('favorite', download.id)"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" :fill="download.is_favorite ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round">
          <path d="m12 3 2.6 5.6 6 .8-4.4 4.2 1.1 6L12 16.8 6.7 19.6l1.1-6L3.4 9.4l6-.8L12 3Z" />
        </svg>
      </button>

      <button
        v-if="failed && download.can_retry"
        class="chip"
        title="Try again"
        aria-label="Try again"
        @click.stop="emit('retry', download.id)"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 12a9 9 0 1 0 3-6.7M3 4v5h5" />
        </svg>
      </button>

      <button
        v-if="active"
        class="chip"
        title="Stop"
        aria-label="Stop"
        @click.stop="emit('cancel', download.id)"
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
          <rect x="6" y="6" width="12" height="12" rx="2" />
        </svg>
      </button>

      <CardMenu
        class="chip-menu"
        :download="download"
        @info="emit('info', download.id)"
        @remove="emit('remove', download.id)"
      />
    </div>
  </figure>
</template>

<style scoped>
.tile {
  position: relative;
  overflow: hidden;
  /* masonry column child — must not split across columns */
  break-inside: avoid;
  margin-bottom: 1rem;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.tile:hover {
  border-color: var(--line-strong);
  box-shadow: var(--shadow);
}

.tile.active {
  border-color: color-mix(in srgb, var(--accent) 45%, var(--line));
}

.tile.failed {
  border-color: color-mix(in srgb, var(--err) 45%, var(--line));
}

.shot {
  position: relative;
  display: block;
  /* the checkerboard needs a surface under it; .alpha-grid only draws layers */
  background-color: var(--bg-raised);
}

.shot.clickable {
  cursor: zoom-in;
}

.shot img {
  display: block;
  width: 100%;
  /* the image sets the tile's height — no cropping, no letterboxing */
  height: auto;
}

.placeholder {
  display: grid;
  place-items: center;
  /* only the fallback needs a shape of its own */
  aspect-ratio: 4 / 3;
  padding: 1rem;
  text-align: center;
}

.state {
  font-size: 0.7rem;
  color: var(--text-dim);
}

.state.err {
  color: var(--err);
}

.bar {
  position: absolute;
  left: 0;
  bottom: 0;
  height: 3px;
  background: var(--accent);
  transition: width 0.4s ease;
}

.controls {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.3rem;
  opacity: 0;
  transition: opacity 0.15s;
}

/* keep them reachable on touch, where there is no hover */
.tile:hover .controls,
.tile:focus-within .controls,
.tile.active .controls,
.tile.failed .controls {
  opacity: 1;
}

@media (hover: none) {
  .controls {
    opacity: 1;
  }
}

.chip,
.controls :deep(.kebab) {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: color-mix(in srgb, var(--bg) 78%, transparent);
  color: var(--text-dim);
  cursor: pointer;
  transition: color 0.15s, background 0.15s, border-color 0.15s;
}

.chip:hover,
.controls :deep(.kebab:hover) {
  color: var(--text);
  background: var(--bg);
  border-color: var(--line-strong);
}

.chip.on {
  color: var(--accent);
  border-color: color-mix(in srgb, var(--accent) 45%, var(--line));
}
</style>
