<script setup lang="ts">
/**
 * A horizontally-scrollable row group for media cards.
 * Has a title header with count, left/right navigation controls,
 * edge gradient fade indicators, and touch scroll-snap support.
 */
const props = withDefaults(
  defineProps<{
    title: string
    count?: number
    color?: string
    icon?: string
    href?: string
  }>(),
  {
    count: 0,
    color: '',
    icon: '',
    href: '',
  }
)

const track = ref<HTMLElement>()
const overflow = ref(false)
const atStart = ref(true)
const atEnd = ref(false)

function syncScroll() {
  const el = track.value
  if (!el) return
  const slack = 4
  const max = el.scrollWidth - el.clientWidth
  overflow.value = max > slack
  atStart.value = el.scrollLeft <= slack
  atEnd.value = el.scrollLeft >= max - slack
}

function scroll(direction: 'prev' | 'next') {
  const el = track.value
  if (!el) return
  // scroll roughly 2 cards width
  const offset = Math.max(el.clientWidth * 0.75, 280)
  el.scrollBy({
    left: direction === 'next' ? offset : -offset,
    behavior: 'smooth',
  })
}

let observer: ResizeObserver | undefined

onMounted(async () => {
  await nextTick()
  syncScroll()
  if (track.value) {
    observer = new ResizeObserver(syncScroll)
    observer.observe(track.value)
  }
})

onUnmounted(() => {
  observer?.disconnect()
})
</script>

<template>
  <section class="row-group" :class="{ 'is-overflow': overflow, 'at-start': atStart, 'at-end': atEnd }">
    <div class="row-header">
      <div class="header-left">
        <span
          v-if="color"
          class="group-dot"
          :style="{ background: color, boxShadow: `0 0 8px ${color}66` }"
        />
        <span v-else-if="icon" class="group-icon">{{ icon }}</span>

        <h2 class="group-title">{{ title }}</h2>

        <span v-if="count > 0" class="group-count mono">{{ count }}</span>
      </div>

      <div v-if="overflow" class="header-controls">
        <button
          type="button"
          class="nav-btn"
          :disabled="atStart"
          :aria-label="`Scroll ${title} left`"
          title="Scroll left"
          @click="scroll('prev')"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
            <path d="m15 18-6-6 6-6" />
          </svg>
        </button>
        <button
          type="button"
          class="nav-btn"
          :disabled="atEnd"
          :aria-label="`Scroll ${title} right`"
          title="Scroll right"
          @click="scroll('next')"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
            <path d="m9 18 6-6-6-6" />
          </svg>
        </button>
      </div>
    </div>

    <div class="track-wrapper">
      <div ref="track" class="row-track" @scroll.passive="syncScroll">
        <slot />
      </div>
    </div>
  </section>
</template>

<style scoped>
.row-group {
  margin-bottom: 2rem;
  position: relative;
}

.row-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.85rem;
  padding: 0 0.2rem;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.group-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex-shrink: 0;
}

.group-icon {
  font-size: 0.95rem;
  line-height: 1;
}

.group-title {
  font-size: 1.15rem;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--text);
  margin: 0;
}

.group-count {
  font-size: 0.72rem;
  padding: 0.15rem 0.45rem;
  border-radius: 12px;
  background: var(--surface-hover);
  color: var(--text-dim);
  border: 1px solid var(--line);
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.nav-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid var(--line);
  background: var(--surface-2, rgba(127, 127, 127, 0.08));
  color: var(--text-dim);
  cursor: pointer;
  transition: all 0.15s ease;
}

.nav-btn:hover:not(:disabled) {
  background: var(--surface-hover);
  color: var(--text);
  border-color: var(--line-strong);
}

.nav-btn:disabled {
  opacity: 0.25;
  cursor: default;
}

.track-wrapper {
  position: relative;
  width: 100%;
}

.row-track {
  display: flex;
  gap: 1rem;
  overflow-x: auto;
  scroll-behavior: smooth;
  scroll-snap-type: x mandatory;
  -webkit-overflow-scrolling: touch;
  padding: 0.35rem 0.2rem 0.85rem;
  scrollbar-width: thin;
  scrollbar-color: var(--line-strong) transparent;
}

.row-track::-webkit-scrollbar {
  height: 6px;
}

.row-track::-webkit-scrollbar-track {
  background: transparent;
}

.row-track::-webkit-scrollbar-thumb {
  background: var(--line-strong);
  border-radius: 4px;
}

.row-track::-webkit-scrollbar-thumb:hover {
  background: var(--text-faint);
}

/* Children in slot (DownloadCards) get a fixed responsive width and snap alignment */
.row-track > :deep(*) {
  flex: 0 0 260px;
  min-width: 240px;
  max-width: 280px;
  scroll-snap-align: start;
}

@media (max-width: 640px) {
  .row-group {
    margin-bottom: 1.6rem;
  }

  .group-title {
    font-size: 1.02rem;
  }

  .row-track {
    gap: 0.75rem;
    padding-bottom: 0.6rem;
  }

  .row-track > :deep(*) {
    flex: 0 0 215px;
    min-width: 195px;
    max-width: 235px;
  }

  .header-controls {
    display: none;
  }
}
</style>
