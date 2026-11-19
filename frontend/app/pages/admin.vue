<script setup lang="ts">
import type {
  AdminAnalytics,
  AdminDateRange,
  AdminDownload,
  AdminDownloadPage,
  AdminStats,
  AdminUser,
  DownloadStatus,
} from '~/types'

definePageMeta({ middleware: 'auth' })

const { request } = useApi()
const { user, fetchUser } = useAuth()

const stats = ref<AdminStats | null>(null)
const users = ref<AdminUser[]>([])
const recent = ref<AdminDownload[]>([])
const denied = ref(false)
const analytics = ref<AdminAnalytics | null>(null)
const activityRange = ref<AdminDateRange>(adminDateRange())
const activityLoading = ref(false)
const activityError = ref('')

// Downloads tab state & pagination
const downloadsList = ref<AdminDownload[]>([])
const downloadsTotal = ref(0)
const downloadsPage = ref(1)
const downloadsLimit = ref(20)
const downloadsLoading = ref(false)
const downloadsError = ref('')
const downloadsTotalPages = ref(1)
const statusFilter = ref<DownloadStatus | ''>('')
const PAGE_SIZE_OPTIONS = [20, 50, 100]

async function loadActivity(range: AdminDateRange) {
  if (activityLoading.value) return
  activityLoading.value = true
  activityError.value = ''
  try {
    const [activity, downloads] = await Promise.all([
      request<AdminAnalytics>('/admin/analytics', { params: range }),
      request<AdminDownload[]>('/admin/downloads', { params: { ...range, limit: 20 } }),
    ])
    analytics.value = activity
    recent.value = downloads
    activityRange.value = { start_date: activity.start_date, end_date: activity.end_date }
  } catch (e) {
    activityError.value = errorMessage(e, 'Could not load activity. Please try again.')
  } finally {
    activityLoading.value = false
  }
}

async function loadDownloads(page: number = downloadsPage.value) {
  if (downloadsLoading.value) return
  downloadsLoading.value = true
  downloadsError.value = ''
  downloadsPage.value = page
  try {
    const res = await request<AdminDownloadPage>('/admin/downloads', {
      params: {
        paginate: true,
        page: downloadsPage.value,
        limit: downloadsLimit.value,
        ...(statusFilter.value ? { status: statusFilter.value } : {}),
      },
    })
    downloadsList.value = res.items
    downloadsTotal.value = res.total
    downloadsTotalPages.value = res.total_pages
  } catch (e) {
    downloadsError.value = errorMessage(e, 'Could not load downloads.')
  } finally {
    downloadsLoading.value = false
  }
}

function changeLimit(newLimit: number) {
  if (downloadsLimit.value === newLimit) return
  downloadsLimit.value = newLimit
  downloadsPage.value = 1
  loadDownloads(1)
}

function goToPage(page: number) {
  if (page < 1 || page > downloadsTotalPages.value || page === downloadsPage.value) return
  loadDownloads(page)
}

function setStatusFilter(s: DownloadStatus | '') {
  statusFilter.value = statusFilter.value === s ? '' : s
  downloadsPage.value = 1
  loadDownloads(1)
}

const paginationStart = computed(() => {
  if (downloadsTotal.value === 0) return 0
  return (downloadsPage.value - 1) * downloadsLimit.value + 1
})

const paginationEnd = computed(() => {
  return Math.min(downloadsPage.value * downloadsLimit.value, downloadsTotal.value)
})

const displayedPages = computed(() => {
  const current = downloadsPage.value
  const total = downloadsTotalPages.value
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1)
  }
  const pages: (number | string)[] = []
  if (current <= 4) {
    for (let i = 1; i <= 5; i++) pages.push(i)
    pages.push('...')
    pages.push(total)
  } else if (current >= total - 3) {
    pages.push(1)
    pages.push('...')
    for (let i = total - 4; i <= total; i++) pages.push(i)
  } else {
    pages.push(1)
    pages.push('...')
    pages.push(current - 1)
    pages.push(current)
    pages.push(current + 1)
    pages.push('...')
    pages.push(total)
  }
  return pages
})

/** Which panel the tabs are showing. Mirrored into `?tab=` so a reload — or a
 *  link straight to one section — lands where you expect. */
type AdminTab = 'dashboard' | 'feedback' | 'payments' | 'plans' | 'users' | 'downloads'
const TABS: { id: AdminTab; label: string }[] = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'feedback', label: 'Feedback' },
  { id: 'payments', label: 'Payments' },
  { id: 'plans', label: 'Plans' },
  { id: 'users', label: 'Users' },
  { id: 'downloads', label: 'Downloads' },
]

const route = useRoute()
const router = useRouter()
const queryTab = TABS.find((t) => t.id === route.query.tab)?.id
const tab = ref<AdminTab>(queryTab || 'dashboard')

/** Pull the user list again — an approved payment changes someone's expiry. */
async function reloadUsers() {
  try {
    users.value = await request<AdminUser[]>('/admin/users')
  } catch {
    // the queue already reported success; a stale row is not worth an error
  }
}

watch(tab, (value) => {
  router.replace({ query: value === 'dashboard' ? {} : { tab: value } })
  if (value === 'downloads' && !downloadsList.value.length) {
    loadDownloads(1)
  }
})

watch(
  () => route.query.tab,
  (newTab) => {
    const matched = TABS.find((t) => t.id === newTab)?.id
    if (matched && matched !== tab.value) {
      tab.value = matched
      if (matched === 'downloads' && !downloadsList.value.length) {
        loadDownloads(1)
      }
    } else if (!newTab && tab.value !== 'dashboard') {
      tab.value = 'dashboard'
    }
  },
)

onMounted(async () => {
  if (!user.value) await fetchUser()
  if (!user.value?.is_admin) {
    denied.value = true
    return navigateTo('/')
  }
  const [s, u] = await Promise.all([
    request<AdminStats>('/admin/stats'),
    request<AdminUser[]>('/admin/users'),
    loadActivity(activityRange.value),
    loadDownloads(1),
  ])
  stats.value = s
  users.value = u
})
</script>

<template>
  <div>
    <AppNavbar />

    <main v-if="!denied" class="page">
      <h1 class="display page-title reveal">Admin</h1>

      <div class="filters tabs reveal" role="tablist" aria-label="Admin sections" style="animation-delay: 0.05s">
        <button
          v-for="t in TABS"
          :id="`tab-${t.id}`"
          :key="t.id"
          class="filter-btn"
          :class="{ on: tab === t.id }"
          type="button"
          role="tab"
          :aria-selected="tab === t.id"
          :aria-controls="`panel-${t.id}`"
          @click="tab = t.id"
        >
          {{ t.label }}
        </button>
      </div>

      <!-- DASHBOARD TAB -->
      <section
        v-if="stats"
        v-show="tab === 'dashboard'"
        id="panel-dashboard"
        role="tabpanel"
        aria-labelledby="tab-dashboard"
      >
        <p class="label totals-label">All-time totals</p>
        <div class="tiles">
          <div
            v-for="(tile, i) in [
              { label: 'Users', value: String(stats.users) },
              { label: 'Downloads', value: String(stats.downloads) },
              { label: 'Feedback', value: String(stats.feedback) },
              { label: 'Storage used', value: formatBytes(stats.bytes_stored) },
              { label: 'Favorites', value: String(stats.favorites) },
            ]"
            :key="tile.label"
            class="tile panel reveal"
            :style="{ animationDelay: `${i * 0.05}s` }"
          >
            <span class="label">{{ tile.label }}</span>
            <span class="tile-value display">{{ tile.value }}</span>
          </div>
        </div>

        <div class="status-row reveal" style="animation-delay: 0.15s">
          <span class="badge badge-queued"><span class="dot" /> queued {{ stats.queued }}</span>
          <span class="badge badge-downloading"><span class="dot" /> downloading {{ stats.downloading }}</span>
          <span class="badge badge-completed">✓ completed {{ stats.completed }}</span>
          <span class="badge badge-failed">✕ failed {{ stats.failed }}</span>
        </div>

        <AdminAnalytics
          :data="analytics"
          :range="activityRange"
          :loading="activityLoading"
          :error="activityError"
          @apply="loadActivity"
        />

        <div class="panel table-panel reveal" style="animation-delay: 0.2s">
          <div class="dash-table-head">
            <div>
              <h2 class="label table-title">Recent downloads</h2>
              <p class="table-note mono">Latest 20 within the selected dates · UTC</p>
            </div>
            <button class="btn btn-ghost view-all-btn" type="button" @click="tab = 'downloads'">
              View tab →
            </button>
          </div>
          <div class="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>User</th>
                  <th>Status</th>
                  <th class="num">Size</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!recent.length">
                  <td colspan="5" class="empty-row dim">{{ activityError ? 'Downloads could not be loaded. Apply a date range to try again.' : 'No downloads in this date range.' }}</td>
                </tr>
                <tr v-for="d in recent" :key="d.id">
                  <td class="clip" :title="d.title || d.filename || d.url">{{ d.title || d.filename || d.url }}</td>
                  <td class="dim">{{ d.username }}</td>
                  <td><span class="badge" :class="`badge-${d.status}`">{{ d.status }}</span></td>
                  <td class="num mono">{{ formatBytes(d.total_bytes) }}</td>
                  <td class="dim">{{ adminActivityDate(d.created_at) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- FEEDBACK TAB -->
      <AdminFeedbackManager
        v-if="stats"
        v-show="tab === 'feedback'"
        id="panel-feedback"
        role="tabpanel"
        aria-labelledby="tab-feedback"
      />

      <!-- PAYMENTS TAB -->
      <AdminPaymentQueue
        v-show="tab === 'payments'"
        id="panel-payments"
        role="tabpanel"
        aria-labelledby="tab-payments"
        @granted="reloadUsers"
      />

      <!-- PLANS TAB -->
      <AdminPlanManager
        v-show="tab === 'plans'"
        id="panel-plans"
        role="tabpanel"
        aria-labelledby="tab-plans"
      />

      <!-- USERS TAB -->
      <AdminUserManager
        v-show="tab === 'users'"
        id="panel-users"
        role="tabpanel"
        aria-labelledby="tab-users"
        :users="users"
        :current-user-id="user?.id"
        @changed="users = $event"
      />

      <!-- DOWNLOADS TAB -->
      <section
        v-show="tab === 'downloads'"
        id="panel-downloads"
        role="tabpanel"
        aria-labelledby="tab-downloads"
      >
        <div v-if="stats" class="status-row status-filter-row" style="margin-top: 0">
          <button
            type="button"
            class="status-filter-btn mono"
            :class="{ active: statusFilter === '' }"
            @click="setStatusFilter('')"
          >
            All ({{ stats.downloads }})
          </button>
          <button
            type="button"
            class="badge badge-queued status-badge-btn"
            :class="{ active: statusFilter === 'queued' }"
            @click="setStatusFilter('queued')"
          >
            <span class="dot" /> queued {{ stats.queued }}
          </button>
          <button
            type="button"
            class="badge badge-downloading status-badge-btn"
            :class="{ active: statusFilter === 'downloading' }"
            @click="setStatusFilter('downloading')"
          >
            <span class="dot" /> downloading {{ stats.downloading }}
          </button>
          <button
            type="button"
            class="badge badge-completed status-badge-btn"
            :class="{ active: statusFilter === 'completed' }"
            @click="setStatusFilter('completed')"
          >
            ✓ completed {{ stats.completed }}
          </button>
          <button
            type="button"
            class="badge badge-failed status-badge-btn"
            :class="{ active: statusFilter === 'failed' }"
            @click="setStatusFilter('failed')"
          >
            ✕ failed {{ stats.failed }}
          </button>
        </div>

        <div class="panel table-panel">
          <div class="dash-table-head">
            <div>
              <h2 class="label table-title">Downloads</h2>
              <p class="table-note mono">
                {{ downloadsLoading ? 'Loading downloads…' : (downloadsTotal === 0 ? '0 downloads' : `Showing ${paginationStart}–${paginationEnd} of ${downloadsTotal} downloads`) }}
              </p>
            </div>
            <button
              class="btn btn-ghost refresh-btn mono"
              type="button"
              :disabled="downloadsLoading"
              title="Refresh downloads"
              @click="loadDownloads()"
            >
              ↻ Refresh
            </button>
          </div>

          <div class="table-scroll">
            <table :class="{ loading: downloadsLoading }">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>User</th>
                  <th>Status</th>
                  <th class="num">Size</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!downloadsList.length && !downloadsLoading">
                  <td colspan="5" class="empty-row dim">
                    {{ downloadsError || (statusFilter ? `No ${statusFilter} downloads found.` : 'No downloads recorded yet.') }}
                  </td>
                </tr>
                <tr v-for="d in downloadsList" :key="d.id">
                  <td class="clip" :title="d.title || d.filename || d.url">{{ d.title || d.filename || d.url }}</td>
                  <td class="dim">{{ d.username }}</td>
                  <td><span class="badge" :class="`badge-${d.status}`">{{ d.status }}</span></td>
                  <td class="num mono">{{ formatBytes(d.total_bytes) }}</td>
                  <td class="dim">{{ adminActivityDate(d.created_at) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Pagination Bar -->
          <div class="pagination-bar">
            <div class="pagination-size">
              <span class="label pagination-label">Rows per page:</span>
              <div class="filters size-presets" role="group" aria-label="Rows per page">
                <button
                  v-for="size in PAGE_SIZE_OPTIONS"
                  :key="size"
                  type="button"
                  class="filter-btn mono"
                  :class="{ on: downloadsLimit === size }"
                  :disabled="downloadsLoading"
                  @click="changeLimit(size)"
                >
                  {{ size }}
                </button>
              </div>
            </div>

            <span class="pagination-summary mono dim">
              {{ downloadsTotal === 0 ? '0 of 0' : `${paginationStart}–${paginationEnd} of ${downloadsTotal}` }}
            </span>

            <div class="pagination-controls" role="navigation" aria-label="Pagination">
              <button
                type="button"
                class="filter-btn nav-btn mono"
                :disabled="downloadsPage <= 1 || downloadsLoading"
                title="First page"
                aria-label="First page"
                @click="goToPage(1)"
              >
                «
              </button>
              <button
                type="button"
                class="filter-btn nav-btn mono"
                :disabled="downloadsPage <= 1 || downloadsLoading"
                title="Previous page"
                aria-label="Previous page"
                @click="goToPage(downloadsPage - 1)"
              >
                ‹ Prev
              </button>

              <div class="page-numbers">
                <template v-for="(p, idx) in displayedPages" :key="idx">
                  <span v-if="p === '...'" class="page-ellipsis mono dim">…</span>
                  <button
                    v-else
                    type="button"
                    class="filter-btn page-btn mono"
                    :class="{ on: downloadsPage === p }"
                    :disabled="downloadsLoading"
                    :aria-current="downloadsPage === p ? 'page' : undefined"
                    @click="goToPage(p as number)"
                  >
                    {{ p }}
                  </button>
                </template>
              </div>

              <button
                type="button"
                class="filter-btn nav-btn mono"
                :disabled="downloadsPage >= downloadsTotalPages || downloadsLoading"
                title="Next page"
                aria-label="Next page"
                @click="goToPage(downloadsPage + 1)"
              >
                Next ›
              </button>
              <button
                type="button"
                class="filter-btn nav-btn mono"
                :disabled="downloadsPage >= downloadsTotalPages || downloadsLoading"
                title="Last page"
                aria-label="Last page"
                @click="goToPage(downloadsTotalPages)"
              >
                »
              </button>
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 2.2rem 1.5rem 4rem;
}

.page-title {
  font-size: clamp(1.6rem, 4vw, 2.4rem);
  margin: 0 0 1rem;
}

.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
}

.totals-label {
  margin: 0 0 0.6rem;
  font-size: 0.6rem;
}

.tile {
  padding: 1.1rem 1.2rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.tile-value {
  font-size: 1.7rem;
  line-height: 1;
}

.status-row {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin: 1.2rem 0 1.8rem;
}

.status-filter-row {
  align-items: center;
}

.status-badge-btn {
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s ease;
  font-family: inherit;
}

.status-badge-btn:hover {
  transform: translateY(-1px);
}

.status-badge-btn.active {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}

.status-filter-btn {
  font-size: 0.72rem;
  padding: 0.25rem 0.65rem;
  border-radius: var(--radius-sm, 6px);
  background: var(--surface);
  border: 1px solid var(--line);
  color: var(--text-dim);
  cursor: pointer;
  transition: all 0.15s ease;
}

.status-filter-btn:hover,
.status-filter-btn.active {
  color: var(--text);
  border-color: var(--line-strong);
  background: var(--surface-hover);
}

.status-filter-btn.active {
  border-color: var(--accent);
  color: var(--accent);
  font-weight: 600;
}

.table-panel {
  margin-bottom: 1.4rem;
  overflow: hidden;
}

.dash-table-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.9rem 1.2rem 0;
}

.dash-table-head .table-title {
  padding: 0;
}

.dash-table-head .table-note {
  margin: 0.35rem 0 0;
}

.view-all-btn {
  font-size: 0.72rem;
  padding: 0.3rem 0.65rem;
  color: var(--text-dim);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  white-space: nowrap;
}

.view-all-btn:hover {
  color: var(--text);
  border-color: var(--line-strong);
}

.refresh-btn {
  font-size: 0.72rem;
  padding: 0.3rem 0.65rem;
  border: 1px solid var(--line);
  border-radius: var(--radius);
}

.refresh-btn:hover:not(:disabled) {
  border-color: var(--line-strong);
}

.table-title {
  margin: 0;
  padding: 0.9rem 1.2rem 0;
}

.table-scroll {
  overflow-x: auto;
}

.table-note {
  color: var(--text-dim);
  font-size: 0.62rem;
  margin: 0.55rem 1.2rem 0;
}

.empty-row {
  padding: 2rem 1.2rem;
  text-align: center;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}

table.loading {
  opacity: 0.6;
  pointer-events: none;
  transition: opacity 0.15s ease;
}

th {
  text-align: left;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.62rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--text-faint);
  font-weight: 500;
  padding: 0.8rem 1.2rem 0.5rem;
}

td {
  padding: 0.55rem 1.2rem;
  border-top: 1px solid var(--line);
}

th.num,
td.num {
  text-align: right;
}

.dim {
  color: var(--text-dim);
}

.clip {
  max-width: 320px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* inline rather than stretching, so the bar reads as a control not a header */
.tabs {
  display: inline-flex;
  margin-bottom: 1.4rem;
  max-width: 100%;
  overflow-x: auto;
}

/* Pagination Bar */
.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.85rem 1.2rem;
  border-top: 1px solid var(--line);
  background: var(--surface);
  flex-wrap: wrap;
}

.pagination-size {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.pagination-label {
  font-size: 0.62rem;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.size-presets {
  display: inline-flex;
}

.size-presets .filter-btn {
  padding: 0.25rem 0.55rem;
  font-size: 0.72rem;
}

.pagination-summary {
  font-size: 0.75rem;
}

.pagination-controls {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

.nav-btn {
  padding: 0.28rem 0.6rem;
  font-size: 0.72rem;
}

.page-numbers {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

.page-btn {
  min-width: 1.8rem;
  padding: 0.28rem 0.45rem;
  font-size: 0.72rem;
  text-align: center;
}

.page-ellipsis {
  padding: 0 0.25rem;
  font-size: 0.75rem;
}
</style>
