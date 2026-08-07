<script setup lang="ts">
import type { AdminDownload, AdminStats, AdminUser } from '~/types'

definePageMeta({ middleware: 'auth' })

const { request } = useApi()
const { user, fetchUser } = useAuth()

const stats = ref<AdminStats | null>(null)
const users = ref<AdminUser[]>([])
const recent = ref<AdminDownload[]>([])
const denied = ref(false)

onMounted(async () => {
  if (!user.value) await fetchUser()
  if (!user.value?.is_admin) {
    denied.value = true
    return navigateTo('/')
  }
  const [s, u, d] = await Promise.all([
    request<AdminStats>('/admin/stats'),
    request<AdminUser[]>('/admin/users'),
    request<AdminDownload[]>('/admin/downloads', { params: { limit: 20 } }),
  ])
  stats.value = s
  users.value = u
  recent.value = d
})
</script>

<template>
  <div>
    <AppNavbar />

    <main v-if="!denied" class="page">
      <h1 class="display page-title reveal">Admin</h1>

      <section v-if="stats" class="tiles">
        <div v-for="(tile, i) in [
            { label: 'Users', value: String(stats.users) },
            { label: 'Downloads', value: String(stats.downloads) },
            { label: 'Reviews', value: String(stats.reviews) },
            { label: 'Storage used', value: formatBytes(stats.bytes_stored) },
            { label: 'Favorites', value: String(stats.favorites) },
          ]" :key="tile.label" class="tile panel reveal" :style="{ animationDelay: `${i * 0.05}s` }">
          <span class="label">{{ tile.label }}</span>
          <span class="tile-value display">{{ tile.value }}</span>
        </div>
      </section>

      <section v-if="stats" class="status-row reveal" style="animation-delay: 0.2s">
        <span class="badge badge-queued"><span class="dot" /> queued {{ stats.queued }}</span>
        <span class="badge badge-downloading"><span class="dot" /> downloading {{ stats.downloading }}</span>
        <span class="badge badge-completed">✓ completed {{ stats.completed }}</span>
        <span class="badge badge-failed">✕ failed {{ stats.failed }}</span>
      </section>

      <AdminReviewManager v-if="stats" />

      <section class="panel table-panel reveal" style="animation-delay: 0.3s">
        <h2 class="label table-title">Users</h2>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>User</th>
                <th>Email</th>
                <th>Role</th>
                <th class="num">Downloads</th>
                <th class="num">Storage</th>
                <th>Joined</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="u in users" :key="u.id">
                <td>{{ u.username }}</td>
                <td class="mono dim">{{ u.email }}</td>
                <td>
                  <span v-if="u.is_admin" class="badge badge-downloading">admin</span>
                  <span v-else class="dim">member</span>
                </td>
                <td class="num mono">{{ u.download_count }}</td>
                <td class="num mono">{{ formatBytes(u.bytes_stored) }}</td>
                <td class="dim">{{ formatDate(u.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="panel table-panel reveal" style="animation-delay: 0.32s">
        <h2 class="label table-title">Recent downloads</h2>
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
              <tr v-for="d in recent" :key="d.id">
                <td class="clip" :title="d.title || d.filename || d.url">{{ d.title || d.filename || d.url }}</td>
                <td class="dim">{{ d.username }}</td>
                <td><span class="badge" :class="`badge-${d.status}`">{{ d.status }}</span></td>
                <td class="num mono">{{ formatBytes(d.total_bytes) }}</td>
                <td class="dim">{{ formatDate(d.created_at) }}</td>
              </tr>
            </tbody>
          </table>
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
  margin: 0 0 1.4rem;
}

.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
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

.table-panel {
  margin-bottom: 1.4rem;
  overflow: hidden;
}

.table-title {
  margin: 0;
  padding: 0.9rem 1.2rem 0;
}

.table-scroll {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
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
</style>
