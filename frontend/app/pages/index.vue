<script setup lang="ts">
import type { Download, DownloadFilter } from '~/types'

definePageMeta({ middleware: 'auth' })

const { refreshMediaToken } = useApi()
const { user, fetchUser } = useAuth()
const { categories, fetchCategories, colorOf } = useCategories()

const {
  downloads,
  loaded,
  live,
  url,
  quality,
  submitting,
  uploading,
  error,
  note,
  search,
  isActive,
  refresh,
  submit,
  upload,
  toggleFavorite,
  toggleHidden,
  setCategory,
  retry,
  cancel,
  convert,
  remove,
  find,
  startLive,
} = useDownloads()

// ── View state ────────────────────────────────────────────────────────

const filter = ref<DownloadFilter>('all')
// deep-linkable: /?category=Coding (the manage page links here)
const route = useRoute()
const categoryFilter = ref<string | null>(
  typeof route.query.category === 'string' ? route.query.category : null
)
const layout = useCookie<'rows' | 'grid'>('mediabox_layout', {
  default: () => 'rows',
  maxAge: 60 * 60 * 24 * 365,
})

/** Hidden rows live on /hidden — this page never shows them anywhere. */
const unhidden = computed(() => downloads.value.filter((d) => !d.is_hidden))

/** The grid, and equally the playlist the preview dialogs step through: pick a
 *  tag and the player walks only that tag, so a view stays a view. */
const visible = computed(() => {
  let list = unhidden.value
  if (filter.value === 'favorites') list = list.filter((d) => d.is_favorite)
  if (filter.value === 'active') list = list.filter(isActive)
  if (filter.value === 'failed') list = list.filter((d) => d.status === 'failed')
  if (categoryFilter.value) list = list.filter((d) => d.category === categoryFilter.value)
  return list
})

const scrollTrack = ref<HTMLElement>()
const overflow = ref(false)
const atStart = ref(true)
const atEnd = ref(false)

function syncScroll() {
  const el = scrollTrack.value
  if (!el) return
  const slack = 4
  const max = el.scrollWidth - el.clientWidth
  overflow.value = max > slack
  atStart.value = el.scrollLeft <= slack
  atEnd.value = el.scrollLeft >= max - slack
}

function scrollRow(direction: 'prev' | 'next') {
  const el = scrollTrack.value
  if (!el) return
  const offset = Math.max(el.clientWidth * 0.75, 280)
  el.scrollBy({
    left: direction === 'next' ? offset : -offset,
    behavior: 'smooth',
  })
}

let resizeObserver: ResizeObserver | undefined

watch(visible, () => {
  nextTick(syncScroll)
})

watch(layout, () => {
  nextTick(syncScroll)
})

/** Tab counts, narrowed the same way `visible` is — minus the tab's own rule —
 *  so each number is exactly how many cards clicking it shows. `search` is
 *  applied server-side, so `downloads` already reflects it. */
const counts = computed<Record<DownloadFilter, number>>(() => {
  let list = unhidden.value
  if (categoryFilter.value) list = list.filter((d) => d.category === categoryFilter.value)
  return {
    all: list.length,
    favorites: list.filter((d) => d.is_favorite).length,
    active: list.filter(isActive).length,
    failed: list.filter((d) => d.status === 'failed').length,
  }
})

// ── Modals ────────────────────────────────────────────────────────────

// upgrade prompt for the paid rungs of the quality ladder
const upgradeOpen = ref(false)
const upgradeQuality = ref<string>('')

// The picker defaults to "Best", which is a paid rung — leaving a free account
// there would fail on their first download with a 402 they never asked for.
watch(
  user,
  (u) => {
    if (u && !u.is_premium && !u.is_admin && isPaidQuality(quality.value)) {
      quality.value = FREE_QUALITY
    }
  },
  { immediate: true }
)

const deleteTarget = ref<Download | null>(null)
const infoTarget = ref<Download | null>(null)

// The player itself is mounted in app.vue so it survives navigation; this page
// only says what to play. Retagging or filtering while it is open should still
// re-aim the playlist, hence the watch.
const { target: previewTarget, playlist, open: openPreview } = usePlayer()
watch(visible, (items) => {
  if (previewTarget.value) playlist.value = [...items]
})

async function confirmRemove() {
  const target = deleteTarget.value
  if (!target) return
  deleteTarget.value = null
  await remove(target.id)
}

onMounted(async () => {
  // Always refetch, not just when it is missing: `user` is cached from login,
  // so an upgrade approved since then would otherwise stay invisible until the
  // next sign-in and high quality would look broken.
  await fetchUser()
  // the socket URL carries the media token, so mint it before connecting
  await Promise.all([refresh(), refreshMediaToken(), fetchCategories()])
  startLive()
  await nextTick()
  syncScroll()
  if (scrollTrack.value) {
    resizeObserver = new ResizeObserver(syncScroll)
    resizeObserver.observe(scrollTrack.value)
  }
})

onUnmounted(() => {
  resizeObserver?.disconnect()
})
</script>

<template>
  <div>
    <AppNavbar />

    <main class="page">
      <!-- Submit bar and filters share one card so they read as a single
           control surface sitting above the results grid. -->
      <section class="manage panel panel-hover reveal">
        <h1 class="display hero-title">Add to your box</h1>

        <MediaSubmitBar
          :premium="user?.is_premium || user?.is_admin"
          @locked="upgradeQuality = $event; upgradeOpen = true"
          v-model:url="url"
          v-model:quality="quality"
          :submitting="submitting"
          :uploading="uploading"
          @submit="submit"
          @upload="upload"
        />

        <p v-if="error" class="submit-error mono">{{ error }}</p>
        <p v-else-if="note" class="submit-note mono">{{ note }}</p>

        <MediaToolbar
          v-model:filter="filter"
          v-model:category="categoryFilter"
          v-model:search="search"
          v-model:layout="layout"
          :counts="counts"
          :live="live"
          class="toolbar"
        />
      </section>

      <section v-if="loaded && visible.length === 0" class="empty reveal" style="animation-delay: 0.1s">
        <p class="display empty-title">
          {{ filter === 'failed' && !search ? 'Nothing failed' : 'Nothing here yet' }}
        </p>
        <p class="empty-hint">
          <template v-if="filter === 'failed' && !search">Every download so far has gone through.</template>
          <template v-else-if="filter === 'all' && !search">Paste a URL above to start your first download.</template>
          <template v-else>No downloads match this view.</template>
        </p>
      </section>

      <!-- Scrollable Row layout (all cards in one row, horizontally scrollable) -->
      <section v-else-if="layout === 'rows'" class="scroll-row-wrap">
        <button
          v-if="overflow && !atStart"
          type="button"
          class="scroll-arrow prev"
          aria-label="Scroll left"
          title="Scroll left"
          @click="scrollRow('prev')"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="m15 18-6-6 6-6" />
          </svg>
        </button>

        <div ref="scrollTrack" class="scroll-row" @scroll.passive="syncScroll">
          <DownloadCard
            v-for="(d, i) in visible"
            :key="d.id"
            :download="d"
            class="reveal"
            :style="{ animationDelay: `${Math.min(i * 0.04, 0.3)}s` }"
            @favorite="toggleFavorite"
            @retry="retry"
            @convert="convert"
            @remove="deleteTarget = find($event)"
            @preview="openPreview(find($event), visible)"
            @info="infoTarget = find($event)"
            @hide="toggleHidden"
            @cancel="cancel"
            @set-category="setCategory"
          />
        </div>

        <button
          v-if="overflow && !atEnd"
          type="button"
          class="scroll-arrow next"
          aria-label="Scroll right"
          title="Scroll right"
          @click="scrollRow('next')"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="m9 18 6-6-6-6" />
          </svg>
        </button>
      </section>

      <!-- Standard Grid layout -->
      <section v-else class="grid">
        <DownloadCard
          v-for="(d, i) in visible"
          :key="d.id"
          :download="d"
          class="reveal"
          :style="{ animationDelay: `${Math.min(i * 0.04, 0.3)}s` }"
          @favorite="toggleFavorite"
          @retry="retry"
          @convert="convert"
          @remove="deleteTarget = find($event)"
          @preview="openPreview(find($event), visible)"
          @info="infoTarget = find($event)"
          @hide="toggleHidden"
          @cancel="cancel"
          @set-category="setCategory"
        />
      </section>
    </main>

    <UpgradeDialog
      :open="upgradeOpen"
      :quality="upgradeQuality"
      @close="upgradeOpen = false; fetchUser()"
    />

    <InfoDialog :download="infoTarget" @close="infoTarget = null" />

    <ConfirmDialog
      :open="!!deleteTarget"
      title="Delete download?"
      :message="`“${deleteTarget?.title || deleteTarget?.filename || deleteTarget?.url}” and its files will be permanently removed.`"
      confirm-label="Delete"
      danger
      @confirm="confirmRemove"
      @cancel="deleteTarget = null"
    />
  </div>
</template>

<style scoped>
.page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 2.2rem 1.5rem 4rem;
}

.manage {
  padding: 1.5rem;
  margin-bottom: 1.6rem;
}

.hero-title {
  font-size: clamp(1.6rem, 4vw, 2.4rem);
  margin: 0 0 1.1rem;
}

.toolbar {
  margin-top: 1.3rem;
}

.submit-error {
  margin: 0.6rem 0 0;
  font-size: 0.75rem;
  color: var(--err);
}

.submit-note {
  margin: 0.6rem 0 0;
  font-size: 0.75rem;
  color: var(--ok);
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1rem;
}

.scroll-row-wrap {
  position: relative;
  width: 100%;
}

.scroll-row {
  display: flex;
  gap: 1rem;
  overflow-x: auto;
  scroll-behavior: smooth;
  scroll-snap-type: x mandatory;
  -webkit-overflow-scrolling: touch;
  padding: 0.35rem 0.2rem 1rem;
  scrollbar-width: thin;
  scrollbar-color: var(--line-strong) transparent;
}

.scroll-row::-webkit-scrollbar {
  height: 6px;
}

.scroll-row::-webkit-scrollbar-thumb {
  background: var(--line-strong);
  border-radius: 4px;
}

.scroll-row::-webkit-scrollbar-thumb:hover {
  background: var(--text-faint);
}

.scroll-row > * {
  flex: 0 0 260px;
  min-width: 240px;
  max-width: 280px;
  scroll-snap-align: start;
}

.scroll-arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 8;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: 1px solid var(--line-strong);
  background: color-mix(in srgb, var(--bg) 85%, transparent);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  color: var(--text);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s ease;
}

.scroll-arrow:hover {
  background: var(--surface-hover);
  color: var(--accent);
  transform: translateY(-50%) scale(1.08);
  border-color: var(--accent);
}

.scroll-arrow.prev {
  left: -14px;
}

.scroll-arrow.next {
  right: -14px;
}

@media (max-width: 640px) {
  .scroll-row {
    gap: 0.75rem;
    padding-bottom: 0.6rem;
  }

  .scroll-row > * {
    flex: 0 0 215px;
    min-width: 195px;
    max-width: 235px;
  }

  .scroll-arrow {
    display: none;
  }
}

.empty {
  text-align: center;
  padding: 4.5rem 1rem;
  border: 1px dashed var(--line-strong);
  border-radius: 10px;
}

.empty-title {
  font-size: 1.1rem;
  color: var(--text-dim);
  margin: 0 0 0.5rem;
}

.empty-hint {
  margin: 0;
  font-size: 0.85rem;
  color: var(--text-faint);
}

@media (max-width: 560px) {
  .manage {
    padding: 1.1rem;
  }
}
</style>
