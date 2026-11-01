<script setup lang="ts">
import type { Download } from '~/types'

definePageMeta({ middleware: 'auth' })

const { refreshMediaToken } = useApi()
const { user, fetchUser } = useAuth()
const { fetchCategories } = useCategories()
const { isLocked, isProtected, lock, unlock } = useHiddenLock()

const unlockPassword = ref('')
const unlockBusy = ref(false)
const unlockErr = ref('')

async function handleUnlockPage() {
  if (!unlockPassword.value || unlockBusy.value) return
  unlockErr.value = ''
  unlockBusy.value = true
  try {
    await unlock(unlockPassword.value)
    unlockPassword.value = ''
  } catch (e: any) {
    unlockErr.value = errorMessage(e, 'Incorrect password. Please try again.')
  } finally {
    unlockBusy.value = false
  }
}

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

const deleteTarget = ref<Download | null>(null)
const infoTarget = ref<Download | null>(null)

// player lives in app.vue so it survives navigation — see usePlayer()
const { target: previewTarget, playlist, open: openPreview } = usePlayer()
watch(hidden, (items) => {
  if (previewTarget.value) playlist.value = [...items]
})

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
      <!-- Locked Screen State -->
      <section v-if="isLocked" class="locked-container reveal">
        <div class="locked-card panel panel-hover">
          <div class="locked-icon-badge">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
          </div>
          <h2 class="locked-title display">Hidden Media Locked</h2>
          <p class="locked-desc">
            This collection is protected with a password. Enter your password to view hidden items.
          </p>

          <form class="locked-form" @submit.prevent="handleUnlockPage">
            <p v-if="unlockErr" class="msg err mono">{{ unlockErr }}</p>

            <label class="label sr-only" for="hidden-page-pw">Password</label>
            <PasswordInput
              id="hidden-page-pw"
              v-model="unlockPassword"
              placeholder="Enter password"
              autocomplete="current-password"
            />

            <button
              class="btn btn-accent unlock-btn"
              type="submit"
              :disabled="unlockBusy || !unlockPassword"
            >
              {{ unlockBusy ? 'Unlocking…' : 'Unlock Collection' }}
            </button>
          </form>
        </div>
      </section>

      <!-- Unlocked Content -->
      <template v-else>
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

              <button
                v-if="isProtected"
                class="btn btn-ghost filter"
                title="Lock hidden media"
                @click="lock"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
                Lock
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
            @preview="openPreview(find($event), hidden)"
            @info="infoTarget = find($event)"
            @hide="toggleHidden"
            @cancel="cancel"
            @set-category="setCategory"
          />
        </section>
      </template>
    </main>

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

.locked-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 4rem 1rem 6rem;
}

.locked-card {
  width: 100%;
  max-width: 420px;
  padding: 2.2rem 2rem 2rem;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.locked-icon-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 54px;
  height: 54px;
  border-radius: 14px;
  background: color-mix(in srgb, var(--accent) 15%, transparent);
  color: var(--accent);
  margin-bottom: 1.2rem;
}

.locked-title {
  font-size: 1.3rem;
  margin: 0 0 0.4rem;
  letter-spacing: -0.01em;
}

.locked-desc {
  margin: 0 0 1.4rem;
  font-size: 0.88rem;
  line-height: 1.5;
  color: var(--text-dim);
}

.locked-form {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.unlock-btn {
  width: 100%;
  margin-top: 0.3rem;
}

.msg {
  margin: 0;
  padding: 0.55rem 0.75rem;
  border-radius: 6px;
  font-size: 0.76rem;
  text-align: left;
}

.msg.err {
  background: var(--err-soft);
  color: var(--err);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
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
