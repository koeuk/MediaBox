<script setup lang="ts">
import type { Download, DownloadFilter } from '~/types'

definePageMeta({ middleware: 'auth' })

const { refreshMediaToken } = useApi()
const { user, fetchUser } = useAuth()
const { paidMode, fetchAccessSettings } = useAccessSettings()
const { fetchCategories } = useCategories()

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
  removeMany,
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

// ── Pagination: show 20 cards, click more to show more ──────────────
const PAGE_SIZE = 20
const limit = ref(PAGE_SIZE)

// Reset pagination when switching filters, categories, or search
watch([filter, categoryFilter, search], () => {
  limit.value = PAGE_SIZE
})

const displayedCards = computed(() => visible.value.slice(0, limit.value))
const hasMore = computed(() => limit.value < visible.value.length)
const remainingCount = computed(() => visible.value.length - displayedCards.value.length)

const selecting = ref(false)
const selectedIds = ref<number[]>([])
const deleting = ref(false)
const bulkDeleteOpen = ref(false)
const allSelected = computed(() => visible.value.length > 0 && selectedIds.value.length === visible.value.length)

function endSelection() {
  selecting.value = false
  selectedIds.value = []
  bulkDeleteOpen.value = false
}

function toggleSelection(id: number) {
  if (deleting.value) return
  selectedIds.value = selectedIds.value.includes(id)
    ? selectedIds.value.filter((selected) => selected !== id)
    : [...selectedIds.value, id]
}

function toggleSelectAll() {
  if (deleting.value) return
  selectedIds.value = allSelected.value ? [] : visible.value.map((d) => d.id)
}

watch([filter, categoryFilter, search], endSelection)
watch(visible, (items) => {
  const ids = new Set(items.map((d) => d.id))
  selectedIds.value = selectedIds.value.filter((id) => ids.has(id))
  if (!selectedIds.value.length) bulkDeleteOpen.value = false
})

async function confirmBulkRemove() {
  if (deleting.value || !selectedIds.value.length) return
  const ids = [...selectedIds.value]
  bulkDeleteOpen.value = false
  deleting.value = true
  try {
    const deleted = new Set(await removeMany(ids))
    selectedIds.value = selectedIds.value.filter((id) => !deleted.has(id))
    if (!selectedIds.value.length) endSelection()
  } finally {
    deleting.value = false
  }
}

function loadMore() {
  limit.value += PAGE_SIZE
}

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
  [user, paidMode],
  ([u, paid]) => {
    if (!paid) upgradeOpen.value = false
    if (paid && u && !u.is_premium && !u.is_admin && isPaidQuality(quality.value)) {
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
  await Promise.all([fetchUser(), fetchAccessSettings()])
  window.addEventListener('focus', fetchAccessSettings)
  // the socket URL carries the media token, so mint it before connecting
  await Promise.all([refresh(), refreshMediaToken(), fetchCategories()])
  startLive()
})
onUnmounted(() => window.removeEventListener('focus', fetchAccessSettings))
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
          :premium="!paidMode || user?.is_premium || user?.is_admin"
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
          :counts="counts"
          :live="live"
          class="toolbar"
        />

        <div v-if="loaded && (visible.length || selecting)" class="selection-bar" :aria-busy="deleting">
          <button v-if="!selecting" type="button" class="btn" @click="selecting = true">
            Select downloads
          </button>
          <template v-else>
            <label class="select-all mono">
              <input
                type="checkbox"
                :checked="allSelected"
                :indeterminate="selectedIds.length > 0 && !allSelected"
                :disabled="deleting || !visible.length"
                @change="toggleSelectAll"
              />
              Select all ({{ visible.length }})
            </label>
            <span class="selection-count mono" role="status" aria-live="polite">
              {{ selectedIds.length }} selected{{ hasMore ? ' · includes results on all pages' : '' }}
            </span>
            <button
              type="button"
              class="btn delete-selected"
              :disabled="deleting || !selectedIds.length"
              @click="bulkDeleteOpen = true"
            >
              {{ deleting ? 'Deleting…' : `Delete selected (${selectedIds.length})` }}
            </button>
            <button type="button" class="btn btn-ghost" :disabled="deleting" @click="endSelection">Cancel</button>
          </template>
        </div>
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

      <!-- Standard Grid layout: lists all cards cleanly with pagination -->
      <section v-else>
        <div class="grid">
          <DownloadCard
            v-for="(d, i) in displayedCards"
            :key="d.id"
            :download="d"
            :selecting="selecting"
            :selected="selectedIds.includes(d.id)"
            :selection-disabled="deleting"
            class="reveal"
            :style="{ animationDelay: `${Math.min((i % PAGE_SIZE) * 0.03, 0.25)}s` }"
            @favorite="toggleFavorite"
            @retry="retry"
            @convert="convert"
            @remove="deleteTarget = find($event)"
            @preview="openPreview(find($event), visible)"
            @info="infoTarget = find($event)"
            @hide="toggleHidden"
            @cancel="cancel"
            @set-category="setCategory"
            @select="toggleSelection"
          />
        </div>

        <div v-if="hasMore" class="load-more-wrap">
          <button type="button" class="load-more-btn" @click="loadMore">
            More ({{ remainingCount }})...
          </button>
        </div>
      </section>
    </main>

    <UpgradeDialog
      :open="upgradeOpen"
      :quality="upgradeQuality"
      @close="upgradeOpen = false; fetchUser()"
    />

    <InfoDialog :download="infoTarget" @close="infoTarget = null" />

    <ConfirmDialog
      :open="bulkDeleteOpen"
      :title="`Delete ${selectedIds.length} selected download${selectedIds.length === 1 ? '' : 's'}?`"
      message="The selected downloads and their files will be permanently removed. This cannot be undone."
      :confirm-label="`Delete ${selectedIds.length}`"
      danger
      @confirm="confirmBulkRemove"
      @cancel="bulkDeleteOpen = false"
    />

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

.selection-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--line);
}

.select-all {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text);
  font-size: 0.75rem;
  cursor: pointer;
}

.select-all input {
  width: 18px;
  height: 18px;
  accent-color: var(--accent);
}

.selection-count {
  flex: 1;
  font-size: 0.7rem;
  color: var(--text-dim);
}

.delete-selected {
  border-color: var(--err);
  color: var(--err);
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

.load-more-wrap {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 1.8rem;
  padding-bottom: 0.5rem;
}

.load-more-btn {
  background: none;
  background-color: transparent;
  border: none;
  box-shadow: none;
  outline: none;
  padding: 0.5rem 1rem;
  font-family: inherit;
  font-size: 0.88rem;
  font-weight: 500;
  color: var(--text-dim);
  cursor: pointer;
  transition: color 0.15s ease;
}

.load-more-btn:hover {
  color: var(--accent);
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
