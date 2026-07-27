<script setup lang="ts">
/**
 * Category filter tabs. Turns into a scrolling carousel with arrows and edge
 * fades once the tabs outgrow the space the toolbar can give them.
 */
const selected = defineModel<string | null>({ required: true })

const { categories, solid } = useCategories()

const track = ref<HTMLElement>()
const overflow = ref(false)
const atStart = ref(true)
const atEnd = ref(false)

function syncScroll() {
  const el = track.value
  if (!el) return
  // sub-pixel widths round unpredictably, so allow a small slack
  const slack = 2
  const max = el.scrollWidth - el.clientWidth
  overflow.value = max > slack
  atStart.value = el.scrollLeft <= slack
  atEnd.value = el.scrollLeft >= max - slack
}

function scrollBy(offset: number) {
  track.value?.scrollBy({ left: offset, behavior: 'smooth' })
}

// a category deleted or renamed on the manage page leaves the filter pointing
// at a name that no longer exists — that would just show an empty grid
watch(categories, (list) => {
  if (selected.value && !list.some((c) => c.name === selected.value)) {
    selected.value = null
  }
  nextTick(syncScroll)
})

// keep the active tab in view when the filter changes from elsewhere
watch(selected, () => {
  nextTick(() => {
    track.value
      ?.querySelector('.filter-btn.on')
      ?.scrollIntoView({ behavior: 'smooth', inline: 'nearest', block: 'nearest' })
  })
})

let observer: ResizeObserver | undefined
onMounted(async () => {
  // the tab row can only measure its overflow once the tabs are rendered
  await nextTick()
  syncScroll()
  if (track.value) {
    observer = new ResizeObserver(syncScroll)
    observer.observe(track.value)
  }
})
onUnmounted(() => observer?.disconnect())

defineExpose({ syncScroll })
</script>

<template>
  <div
    class="filters cat-filters"
    :class="{ scrollable: overflow, 'at-start': atStart, 'at-end': atEnd }"
  >
    <button
      v-if="overflow"
      type="button"
      class="cat-nav prev"
      :disabled="atStart"
      title="Scroll categories left"
      aria-label="Scroll categories left"
      @click="scrollBy(-180)"
    >
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
        <path d="m15 18-6-6 6-6" />
      </svg>
    </button>

    <div ref="track" class="cat-track" @scroll.passive="syncScroll">
      <button class="filter-btn mono" :class="{ on: selected === null }" @click="selected = null">
        All
      </button>
      <button
        v-for="c in categories"
        :key="c.id"
        class="filter-btn mono"
        :class="{ on: selected === c.name }"
        :style="selected === c.name ? solid(c.name) : { color: c.color }"
        @click="selected = c.name"
      >
        {{ c.name }}
      </button>
    </div>

    <button
      v-if="overflow"
      type="button"
      class="cat-nav next"
      :disabled="atEnd"
      title="Scroll categories right"
      aria-label="Scroll categories right"
      @click="scrollBy(180)"
    >
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
        <path d="m9 18 6-6-6-6" />
      </svg>
    </button>
  </div>
</template>

<style scoped>
.cat-filters {
  border-color: var(--line);
  min-width: 0;
  /* only the category row gives up width when the toolbar gets tight */
  flex: 0 1 auto;
}

.cat-track {
  display: flex;
  gap: 0.3rem;
  /* min-width:0 overrides the flex default of `auto`, which would refuse to
     shrink past the tabs' natural width and defeat the scrolling entirely */
  flex: 1 1 auto;
  min-width: 0;
  overflow-x: auto;
  scroll-behavior: smooth;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.cat-track::-webkit-scrollbar {
  display: none;
}

.cat-nav {
  flex: none;
  display: grid;
  place-items: center;
  width: 20px;
  align-self: stretch;
  border: none;
  background: transparent;
  color: var(--text-dim);
  border-radius: 5px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, opacity 0.15s;
}

.cat-nav:hover:not(:disabled) {
  background: var(--surface-2, rgba(127, 127, 127, 0.14));
  color: var(--text);
}

.cat-nav:disabled {
  opacity: 0.25;
  cursor: default;
}

/* fade the tabs out toward whichever edge still has more to scroll */
.cat-filters.scrollable .cat-track {
  --fade-l: 14px;
  --fade-r: 14px;
  mask-image: linear-gradient(
    90deg,
    transparent,
    #000 var(--fade-l),
    #000 calc(100% - var(--fade-r)),
    transparent
  );
}

.cat-filters.at-start .cat-track {
  --fade-l: 0px;
}

.cat-filters.at-end .cat-track {
  --fade-r: 0px;
}

@media (prefers-reduced-motion: reduce) {
  .cat-track {
    scroll-behavior: auto;
  }
}
</style>
