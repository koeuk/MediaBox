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

interface MediaRowGroupItem {
  id: string
  title: string
  color?: string
  icon?: string
  items: Download[]
}

/** Group visible downloads into rows (by Category or Status/Date) */
const rowGroups = computed<MediaRowGroupItem[]>(() => {
  const list = visible.value
  if (!list.length) return []

  // If a category filter is specifically selected
  if (categoryFilter.value) {
    const cat = categories.value.find((c) => c.name === categoryFilter.value)
    return [
      {
        id: `cat-${categoryFilter.value}`,
        title: categoryFilter.value,
        color: cat?.color || colorOf(categoryFilter.value),
        items: list,
      },
    ]
  }

  if (filter.value === 'active') {
    return [
      {
        id: 'active',
        title: 'Active Downloads',
        icon: '⚡',
        items: list,
      },
    ]
  }

  if (filter.value === 'failed') {
    return [
      {
        id: 'failed',
        title: 'Failed Downloads',
        icon: '⚠️',
        items: list,
      },
    ]
  }

  const groups: MediaRowGroupItem[] = []

  // In 'all' view: show active downloads row if any exist
  if (filter.value === 'all') {
    const activeItems = list.filter(isActive)
    if (activeItems.length > 0) {
      groups.push({
        id: 'active',
        title: 'In Progress',
        icon: '⚡',
        items: activeItems,
      })
    }
  }

  // In 'all' view: show favorites row if any exist
  if (filter.value === 'all') {
    const favItems = list.filter((d) => d.is_favorite)
    if (favItems.length > 0) {
      groups.push({
        id: 'favorites',
        title: 'Favorites',
        icon: '⭐',
        color: '#f5a623',
        items: favItems,
      })
    }
  }

  // Group by Category if items have categories
  const hasCategories = list.some((d) => !!d.category)

  if (hasCategories) {
    for (const cat of categories.value) {
      const catItems = list.filter((d) => d.category === cat.name)
      if (catItems.length > 0) {
        groups.push({
          id: `cat-${cat.id}`,
          title: cat.name,
          color: cat.color,
          items: catItems,
        })
      }
    }

    const uncategorized = list.filter((d) => !d.category)
    if (uncategorized.length > 0) {
      groups.push({
        id: 'uncategorized',
        title: 'Other Media',
        icon: '📁',
        items: uncategorized,
      })
    }
  } else {
    // If no downloads have categories assigned at all, group by Date/Timeline
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)
    const thisWeek = new Date(today)
    thisWeek.setDate(thisWeek.getDate() - 7)

    const todayItems: Download[] = []
    const yesterdayItems: Download[] = []
    const thisWeekItems: Download[] = []
    const earlierItems: Download[] = []

    for (const d of list) {
      if (!d.created_at) {
        earlierItems.push(d)
        continue
      }
      const itemDate = new Date(d.created_at)
      if (itemDate >= today) {
        todayItems.push(d)
      } else if (itemDate >= yesterday) {
        yesterdayItems.push(d)
      } else if (itemDate >= thisWeek) {
        thisWeekItems.push(d)
      } else {
        earlierItems.push(d)
      }
    }

    if (todayItems.length > 0) {
      groups.push({ id: 'date-today', title: 'Added Today', icon: '🕒', items: todayItems })
    }
    if (yesterdayItems.length > 0) {
      groups.push({ id: 'date-yesterday', title: 'Yesterday', icon: '📅', items: yesterdayItems })
    }
    if (thisWeekItems.length > 0) {
      groups.push({ id: 'date-week', title: 'This Week', icon: '📆', items: thisWeekItems })
    }
    if (earlierItems.length > 0) {
      groups.push({ id: 'date-earlier', title: 'Earlier', icon: '📦', items: earlierItems })
    }
  }

  // Fallback if no specific groups were created
  if (!groups.length) {
    groups.push({
      id: 'all',
      title: filter.value === 'favorites' ? 'Favorites' : 'All Media',
      items: list,
    })
  }

  return groups
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

      <!-- Scrollable Row Groups layout -->
      <section v-else-if="layout === 'rows'" class="row-groups">
        <MediaRowGroup
          v-for="group in rowGroups"
          :key="group.id"
          :title="group.title"
          :count="group.items.length"
          :color="group.color"
          :icon="group.icon"
        >
          <DownloadCard
            v-for="(d, i) in group.items"
            :key="d.id"
            :download="d"
            class="reveal"
            :style="{ animationDelay: `${Math.min(i * 0.03, 0.2)}s` }"
            @favorite="toggleFavorite"
            @retry="retry"
            @convert="convert"
            @remove="deleteTarget = find($event)"
            @preview="openPreview(find($event), group.items)"
            @info="infoTarget = find($event)"
            @hide="toggleHidden"
            @cancel="cancel"
            @set-category="setCategory"
          />
        </MediaRowGroup>
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

.row-groups {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
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
