<script setup lang="ts">
import type { Download } from '~/types'

definePageMeta({ middleware: 'auth' })

const { refreshMediaToken } = useApi()
const { user, fetchUser } = useAuth()
const { fetchCategories } = useCategories()

const {
  downloads,
  loaded,
  refresh,
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

/** Everything hidden from the media grid ends up here. */
const hidden = computed(() => downloads.value.filter((d) => d.is_hidden))

const search = ref('')
const onlyFavorites = ref(false)

const visible = computed(() => {
  const q = search.value.trim().toLowerCase()
  return hidden.value.filter((d) => {
    if (onlyFavorites.value && !d.is_favorite) return false
    if (!q) return true
    const haystack = `${d.title || ''} ${d.filename || ''} ${d.url}`.toLowerCase()
    return haystack.includes(q)
  })
})

const favoriteCount = computed(() => hidden.value.filter((d) => d.is_favorite).length)

// ── Dialogs ───────────────────────────────────────────────────────────

const previewTarget = ref<Download | null>(null)
const deleteTarget = ref<Download | null>(null)
const infoTarget = ref<Download | null>(null)

const isStill = (d: Download | null) => !!d && mediaKind(d.content_type) === 'image'
const previewImage = computed(() => (isStill(previewTarget.value) ? previewTarget.value : null))
const previewMedia = computed(() => (isStill(previewTarget.value) ? null : previewTarget.value))

async function confirmRemove() {
  const target = deleteTarget.value
  if (!target) return
  deleteTarget.value = null
  await remove(target.id)
}

onMounted(async () => {
  if (!user.value) await fetchUser()
  await Promise.all([refresh(), refreshMediaToken(), fetchCategories()])
  startLive()
})
</script>

<template>
  <div>
    <AppNavbar />

    <main class="page">
      <section class="head panel panel-hover reveal">
        <div class="head-top">
          <div>
            <h1 class="display hero-title">Hidden</h1>
            <p class="hero-hint">
              {{ hidden.length }} item{{ hidden.length === 1 ? '' : 's' }} kept out of your media
              grid<template v-if="favoriteCount"> · {{ favoriteCount }} favorited</template>
            </p>
          </div>

          <div class="controls">
            <label class="search">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
                <circle cx="11" cy="11" r="7" />
                <path d="m20 20-3.5-3.5" />
              </svg>
              <input v-model="search" type="search" placeholder="Search title or source" aria-label="Search hidden items" />
            </label>

            <button
              class="btn btn-ghost filter"
              :class="{ on: onlyFavorites }"
              :aria-pressed="onlyFavorites"
              @click="onlyFavorites = !onlyFavorites"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" :fill="onlyFavorites ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2" stroke-linejoin="round" aria-hidden="true">
                <path d="M12 2l3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1L12 2Z" />
              </svg>
              Favorites
            </button>
          </div>
        </div>
      </section>

      <section v-if="loaded && visible.length === 0" class="empty reveal" style="animation-delay: 0.1s">
        <p class="display empty-title">
          {{ hidden.length ? 'Nothing matches' : 'Nothing hidden' }}
        </p>
        <p class="empty-hint">
          {{
            hidden.length
              ? 'Try a different search, or clear the favorites filter.'
              : 'Use Hide on a card’s ⋮ menu to keep it out of your media grid — it lands here.'
          }}
        </p>
      </section>

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
          @preview="previewTarget = find($event)"
          @info="infoTarget = find($event)"
          @hide="toggleHidden"
          @cancel="cancel"
          @set-category="setCategory"
        />
      </section>
    </main>

    <MediaPreview
      :download="previewMedia"
      :downloads="hidden"
      @select="(d) => (previewTarget = d)"
      @close="previewTarget = null"
    />

    <ImagePreview
      :download="previewImage"
      :images="hidden"
      @select="(d) => (previewTarget = d)"
      @close="previewTarget = null"
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

.head {
  padding: 1.5rem;
  margin-bottom: 1.6rem;
}

.head-top {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1.2rem;
  flex-wrap: wrap;
}

.hero-title {
  font-size: clamp(1.6rem, 4vw, 2.4rem);
  margin: 0 0 0.4rem;
}

.hero-hint {
  margin: 0;
  font-size: 0.8rem;
  color: var(--text-faint);
}

.controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.search {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0 0.7rem;
  border: 1px solid var(--line-strong);
  border-radius: 7px;
  background: var(--bg-raised);
  color: var(--text-faint);
  transition: border-color 0.15s, box-shadow 0.15s;
}

.search:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

.search input {
  width: 210px;
  padding: 0.5rem 0;
  border: none;
  background: transparent;
  color: var(--text);
  font: 400 0.8rem 'Archivo', sans-serif;
  outline: none;
}

.search input::placeholder {
  color: var(--text-faint);
}

.filter.on {
  color: var(--accent);
  background: var(--accent-soft);
  border-color: color-mix(in srgb, var(--accent) 30%, transparent);
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1rem;
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
  .head {
    padding: 1.1rem;
  }

  .search input {
    width: 100%;
  }
}
</style>
