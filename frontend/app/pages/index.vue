<script setup lang="ts">
import type { Download } from '~/composables/useApi'

definePageMeta({ middleware: 'auth' })

const { request, wsUrl, refreshMediaToken } = useApi()
const { user, fetchUser } = useAuth()

const downloads = ref<Download[]>([])
const url = ref('')
const quality = ref('')
const qualityOptions = [
  { value: '', label: 'Best', hint: 'auto' },
  { value: '2160', label: '4K', hint: '2160p' },
  { value: '1440', label: '1440p' },
  { value: '1080', label: '1080p' },
  { value: '720', label: '720p' },
  { value: '480', label: '480p' },
]
const search = ref('')
const filter = ref<'all' | 'favorites' | 'active'>('all')
const { categories, fetchCategories, solid } = useCategories()
// deep-linkable: /?category=Coding (the manage page links here)
const route = useRoute()
const categoryFilter = ref<string | null>(
  typeof route.query.category === 'string' ? route.query.category : null
)
const submitError = ref('')
const submitNote = ref('')
const submitting = ref(false)
const loaded = ref(false)
const live = ref(false)

const visible = computed(() => {
  let list = downloads.value
  if (filter.value === 'favorites') list = list.filter((d) => d.is_favorite)
  if (filter.value === 'active')
    list = list.filter((d) => d.status === 'queued' || d.status === 'downloading')
  if (categoryFilter.value)
    list = list.filter((d) => d.category === categoryFilter.value)
  return list
})

const activeCount = computed(
  () => downloads.value.filter((d) => d.status === 'queued' || d.status === 'downloading').length
)

// Category tabs turn into a carousel once they outgrow the toolbar
const catTrack = ref<HTMLElement>()
const catOverflow = ref(false)
const catAtStart = ref(true)
const catAtEnd = ref(false)

function syncCatScroll() {
  const el = catTrack.value
  if (!el) return
  // sub-pixel widths round unpredictably, so allow a small slack
  const slack = 2
  const max = el.scrollWidth - el.clientWidth
  catOverflow.value = max > slack
  catAtStart.value = el.scrollLeft <= slack
  catAtEnd.value = el.scrollLeft >= max - slack
}

function scrollCats(offset: number) {
  catTrack.value?.scrollBy({ left: offset, behavior: 'smooth' })
}

// a category deleted or renamed on the manage page leaves the filter pointing
// at a name that no longer exists — that would just show an empty grid
watch(categories, (list) => {
  if (categoryFilter.value && !list.some((c) => c.name === categoryFilter.value)) {
    categoryFilter.value = null
  }
})

// keep the active tab in view when the filter changes from elsewhere
watch(categoryFilter, () => {
  nextTick(() => {
    catTrack.value
      ?.querySelector('.filter-btn.on')
      ?.scrollIntoView({ behavior: 'smooth', inline: 'nearest', block: 'nearest' })
  })
})

let catObserver: ResizeObserver | undefined
onMounted(() => {
  syncCatScroll()
  if (catTrack.value) {
    catObserver = new ResizeObserver(syncCatScroll)
    catObserver.observe(catTrack.value)
  }
})
onUnmounted(() => catObserver?.disconnect())

async function refresh() {
  const params: Record<string, string> = {}
  if (search.value) params.search = search.value
  downloads.value = await request<Download[]>('/downloads', { params })
  loaded.value = true
}

async function submit() {
  const urls = url.value.split(/[\s,]+/).filter(Boolean)
  if (!urls.length) return
  submitError.value = ''
  submitNote.value = ''
  submitting.value = true
  try {
    const q = quality.value || undefined
    if (urls.length === 1) {
      await request<Download>('/downloads', { method: 'POST', body: { url: urls[0], quality: q } })
    } else {
      await request<Download[]>('/downloads/batch', { method: 'POST', body: { urls, quality: q } })
      submitNote.value = `${urls.length} downloads queued`
    }
    url.value = ''
    await refresh()
  } catch (e: any) {
    const detail = e?.data?.detail
    submitError.value = Array.isArray(detail)
      ? 'Please enter valid URLs (each must start with http:// or https://)'
      : detail || 'Failed to queue download.'
  } finally {
    submitting.value = false
  }
}

async function toggleFavorite(id: number) {
  const updated = await request<Download>(`/downloads/${id}/favorite`, { method: 'PATCH' })
  const i = downloads.value.findIndex((d) => d.id === id)
  if (i !== -1) downloads.value[i] = updated
}

async function setCategory(payload: { id: number; category: string | null }) {
  try {
    const updated = await request<Download>(`/downloads/${payload.id}/category`, {
      method: 'PATCH',
      body: { category: payload.category },
    })
    const i = downloads.value.findIndex((d) => d.id === payload.id)
    if (i !== -1) downloads.value[i] = updated
  } catch (e: any) {
    submitError.value = e?.data?.detail || 'Failed to update category.'
  }
}

async function retry(id: number) {
  try {
    const updated = await request<Download>(`/downloads/${id}/retry`, { method: 'POST' })
    const i = downloads.value.findIndex((d) => d.id === id)
    if (i !== -1) downloads.value[i] = updated
  } catch (e: any) {
    submitError.value = e?.data?.detail || 'Retry failed.'
  }
}

async function cancel(id: number) {
  try {
    await request<Download>(`/downloads/${id}/cancel`, { method: 'POST' })
  } catch (e: any) {
    submitError.value = e?.data?.detail || 'Could not stop the download.'
  }
}

async function convert(payload: { id: number; target: string }) {
  try {
    const created = await request<Download>(`/downloads/${payload.id}/convert`, {
      method: 'POST',
      body: { target: payload.target },
    })
    downloads.value = [created, ...downloads.value]
  } catch (e: any) {
    submitError.value = e?.data?.detail || 'Conversion failed to start.'
  }
}

const fileInput = ref<HTMLInputElement>()
const uploading = ref(false)

async function onFilesPicked(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  if (!files.length) return
  uploading.value = true
  submitError.value = ''
  submitNote.value = ''
  try {
    for (const f of files) {
      const form = new FormData()
      form.append('file', f)
      await request<Download>('/downloads/upload', { method: 'POST', body: form })
    }
    submitNote.value =
      files.length === 1
        ? 'Uploaded — use Convert… on the card to change format'
        : `${files.length} files uploaded`
    await refresh()
  } catch (e: any) {
    submitError.value = e?.data?.detail || 'Upload failed.'
  } finally {
    uploading.value = false
  }
}

const previewTarget = ref<Download | null>(null)

function preview(id: number) {
  previewTarget.value = downloads.value.find((d) => d.id === id) || null
}

const deleteTarget = ref<Download | null>(null)

function remove(id: number) {
  deleteTarget.value = downloads.value.find((d) => d.id === id) || null
}

async function confirmRemove() {
  const target = deleteTarget.value
  if (!target) return
  deleteTarget.value = null
  try {
    await request(`/downloads/${target.id}`, { method: 'DELETE' })
    downloads.value = downloads.value.filter((d) => d.id !== target.id)
  } catch (e: any) {
    submitError.value =
      e?.data?.detail || 'Failed to delete — check that the server is running.'
  }
}

// ── Live updates: WebSocket first, 2s polling as fallback ──
let ws: WebSocket | undefined
let closed = false

function connectWs() {
  if (closed) return
  try {
    ws = new WebSocket(wsUrl())
  } catch {
    return
  }
  ws.onopen = () => (live.value = true)
  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data)
      // ignore pushes while a server-side search filter is active
      if (msg.type === 'snapshot' && !search.value) {
        downloads.value = msg.items
        loaded.value = true
      }
    } catch {}
  }
  ws.onclose = () => {
    live.value = false
    if (!closed) setTimeout(connectWs, 3000)
  }
}

let timer: ReturnType<typeof setInterval> | undefined
let mediaTimer: ReturnType<typeof setInterval> | undefined
onMounted(async () => {
  if (!user.value) await fetchUser()
  await Promise.all([refresh(), refreshMediaToken(), fetchCategories()])
  // the tab row can only measure its overflow once the tabs are rendered
  await nextTick()
  syncCatScroll()
  connectWs()
  timer = setInterval(() => {
    if (!live.value && activeCount.value > 0) refresh()
  }, 2000)
  // media tokens expire after 10 min — renew ahead of that
  mediaTimer = setInterval(refreshMediaToken, 8 * 60 * 1000)
})
onUnmounted(() => {
  closed = true
  ws?.close()
  clearInterval(timer)
  clearInterval(mediaTimer)
})

let searchDebounce: ReturnType<typeof setTimeout> | undefined
watch(search, () => {
  clearTimeout(searchDebounce)
  searchDebounce = setTimeout(refresh, 300)
})
</script>

<template>
  <div>
    <AppNavbar />

    <main class="page">
      <section class="hero reveal">
        <h1 class="display hero-title">Add to your box</h1>
        <form class="submit-bar" @submit.prevent="submit">
          <input
            v-model="url"
            class="input submit-input mono"
            type="text"
            placeholder="https:// — paste direct media URLs or TikTok/Facebook video links (authorized content only)"
            required
          />
          <AppSelect
            v-model="quality"
            :options="qualityOptions"
            aria-label="Max resolution for TikTok/Facebook/YouTube links (direct file URLs are unaffected)"
          />
          <button class="btn btn-accent submit-btn" type="submit" :disabled="submitting">
            {{ submitting ? 'Queuing…' : 'Download' }}
          </button>
          <input
            ref="fileInput"
            type="file"
            accept="video/*,audio/*,image/*"
            multiple
            hidden
            @change="onFilesPicked"
          />
          <button
            type="button"
            class="btn submit-btn"
            :disabled="uploading"
            title="Upload media from your computer to preview or convert (webm → mp4, …)"
            @click="fileInput?.click()"
          >
            {{ uploading ? 'Uploading…' : 'Upload' }}
          </button>
        </form>
        <p v-if="submitError" class="submit-error mono">{{ submitError }}</p>
        <p v-else-if="submitNote" class="submit-note mono">{{ submitNote }}</p>
      </section>

      <section class="toolbar reveal" style="animation-delay: 0.06s">
        <div class="toolbar-left">
          <div class="filters">
            <button
              v-for="f in (['all', 'favorites', 'active'] as const)"
              :key="f"
              class="filter-btn mono"
              :class="{ on: filter === f }"
              @click="filter = f"
            >
              {{ f }}<span v-if="f === 'active' && activeCount"> ({{ activeCount }})</span>
            </button>
          </div>
          <!-- Category filter tabs — scrolls as a carousel when it overflows -->
          <div
            class="filters cat-filters"
            :class="{ scrollable: catOverflow, 'at-start': catAtStart, 'at-end': catAtEnd }"
          >
            <button
              v-if="catOverflow"
              type="button"
              class="cat-nav prev"
              :disabled="catAtStart"
              title="Scroll categories left"
              aria-label="Scroll categories left"
              @click="scrollCats(-180)"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
                <path d="m15 18-6-6 6-6" />
              </svg>
            </button>

            <div ref="catTrack" class="cat-track" @scroll.passive="syncCatScroll">
              <button
                class="filter-btn mono"
                :class="{ on: categoryFilter === null }"
                @click="categoryFilter = null"
              >
                All
              </button>
              <button
                v-for="c in categories"
                :key="c.id"
                class="filter-btn mono"
                :class="{ on: categoryFilter === c.name }"
                :style="categoryFilter === c.name ? solid(c.name) : { color: c.color }"
                @click="categoryFilter = c.name"
              >
                {{ c.name }}
              </button>
            </div>

            <button
              v-if="catOverflow"
              type="button"
              class="cat-nav next"
              :disabled="catAtEnd"
              title="Scroll categories right"
              aria-label="Scroll categories right"
              @click="scrollCats(180)"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
                <path d="m9 18 6-6-6-6" />
              </svg>
            </button>
          </div>
          <span class="live mono" :class="{ on: live }" :title="live ? 'WebSocket connected' : 'Polling fallback'">
            ● {{ live ? 'live' : 'polling' }}
          </span>
        </div>
        <input v-model="search" class="input search" type="search" placeholder="Search downloads…" />
      </section>

      <section v-if="loaded && visible.length === 0" class="empty reveal" style="animation-delay: 0.1s">
        <p class="display empty-title">Nothing here yet</p>
        <p class="empty-hint">
          {{ filter === 'all' && !search ? 'Paste a URL above to start your first download.' : 'No downloads match this view.' }}
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
          @remove="remove"
          @preview="preview"
          @cancel="cancel"
          @set-category="setCategory"
        />
      </section>
    </main>

    <MediaPreview
      :download="previewTarget"
      :downloads="downloads"
      @select="(d) => (previewTarget = d)"
      @close="previewTarget = null"
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

.hero-title {
  font-size: clamp(1.6rem, 4vw, 2.4rem);
  margin: 0 0 1.1rem;
}

.submit-bar {
  display: flex;
  gap: 0.6rem;
}

.submit-input {
  flex: 1;
  font-size: 0.85rem;
}

.submit-btn {
  white-space: nowrap;
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

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin: 2rem 0 1.2rem;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  /* lets .cat-filters shrink below its content width instead of overflowing */
  min-width: 0;
}

.filters {
  display: flex;
  gap: 0.3rem;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 7px;
  padding: 0.25rem;
}

.filter-btn {
  border: none;
  background: transparent;
  color: var(--text-dim);
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  padding: 0.42rem 0.8rem;
  border-radius: 5px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  flex: none;
  white-space: nowrap;
}

.filter-btn:hover {
  color: var(--text);
}

.filter-btn.on {
  background: var(--accent);
  color: var(--accent-ink);
  font-weight: 600;
}

.live {
  font-size: 0.64rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--text-faint);
}

.live.on {
  color: var(--ok);
}

.search {
  max-width: 260px;
  font-size: 0.85rem;
}

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

/* tab colours are inline now, driven by each category's stored colour —
   see useCategories().solid */

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
  .submit-bar {
    flex-direction: column;
  }

  .search {
    max-width: none;
    width: 100%;
  }
}
</style>
