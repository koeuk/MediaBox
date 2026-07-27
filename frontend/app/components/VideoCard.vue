<script setup lang="ts">
import type { VideoItem } from '~/types/preferences'

const props = defineProps<{ item: VideoItem }>()
const emit = defineEmits<{ favorite: [id: number]; play: [id: number] }>()

/**
 * No real thumbnails yet, so each card gets a deterministic gradient poster.
 * Built from theme tokens so it reads correctly in light and dark.
 */
const POSTERS = [
  'linear-gradient(135deg, color-mix(in srgb, var(--accent) 34%, var(--bg-raised)), var(--bg-raised))',
  'linear-gradient(135deg, color-mix(in srgb, var(--ok) 28%, var(--bg-raised)), var(--bg-raised))',
  'linear-gradient(135deg, color-mix(in srgb, var(--err) 24%, var(--bg-raised)), var(--bg-raised))',
  'linear-gradient(135deg, color-mix(in srgb, var(--line-strong) 80%, var(--bg-raised)), var(--bg-raised))',
]

const poster = computed(() => POSTERS[props.item.id % POSTERS.length])

// sliced off the ISO string rather than parsed — a Date would render in the
// server's timezone during SSR and the browser's on hydration, which mismatches
const added = computed(() => props.item.added.slice(0, 10))
</script>

<template>
  <article class="card panel">
    <div class="thumb" :style="{ background: poster }" title="Play" @click="emit('play', item.id)">
      <span class="play-hint" aria-hidden="true">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
          <path d="m8 5 12 7-12 7V5Z" />
        </svg>
      </span>

      <svg class="poster-glyph" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round" aria-hidden="true">
        <rect x="2" y="4" width="20" height="16" rx="2" />
        <path d="m10 9 5 3-5 3V9Z" fill="currentColor" />
      </svg>

      <span class="badge quality mono">{{ item.quality }}</span>
      <span class="badge duration mono">{{ item.duration }}</span>

      <button
        class="fav"
        :class="{ on: item.favorite }"
        :title="item.favorite ? 'Unfavorite' : 'Favorite'"
        @click.stop="emit('favorite', item.id)"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" :fill="item.favorite ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2" stroke-linejoin="round">
          <path d="M12 2l3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1L12 2Z" />
        </svg>
      </button>
    </div>

    <div class="body">
      <h3 class="name" :title="item.title">{{ item.title }}</h3>
      <p class="source mono" :title="item.source">{{ item.source }}</p>

      <div class="meta mono">
        <span>{{ item.size }}</span>
        <span class="sep">·</span>
        <span>{{ added }}</span>
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

.thumb {
  position: relative;
  aspect-ratio: 16 / 9;
  background-color: var(--bg-raised);
  overflow: hidden;
  cursor: pointer;
}

.poster-glyph {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 34px;
  height: 34px;
  transform: translate(-50%, -50%);
  color: var(--text-faint);
  opacity: 0.7;
  transition: opacity 0.15s;
}

.play-hint {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: grid;
  place-items: center;
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

.thumb:hover .play-hint {
  opacity: 1;
}

.thumb:hover .poster-glyph {
  opacity: 0;
}

.badge {
  position: absolute;
  z-index: 2;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  font-size: 0.62rem;
  letter-spacing: 0.04em;
  background: color-mix(in srgb, #000 62%, transparent);
  color: #fff;
}

.quality {
  top: 0.5rem;
  left: 0.5rem;
  text-transform: uppercase;
}

.duration {
  right: 0.5rem;
  bottom: 0.5rem;
}

.fav {
  position: absolute;
  z-index: 2;
  top: 0.5rem;
  right: 0.5rem;
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  padding: 0;
  border: none;
  border-radius: 6px;
  background: color-mix(in srgb, #000 55%, transparent);
  color: #fff;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s, color 0.15s;
}

.card:hover .fav,
.fav.on,
.fav:focus-visible {
  opacity: 1;
}

.fav.on {
  color: var(--accent-strong);
}

.body {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding: 0.8rem 0.9rem 0.9rem;
}

.name {
  margin: 0;
  font-size: 0.85rem;
  font-weight: 600;
  line-height: 1.35;
  /* two lines then ellipsis, so uneven titles don't desync the grid rows */
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.source {
  margin: 0;
  font-size: 0.7rem;
  color: var(--text-dim);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.meta {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.15rem;
  font-size: 0.68rem;
  color: var(--text-faint);
}

.sep {
  opacity: 0.6;
}
</style>
