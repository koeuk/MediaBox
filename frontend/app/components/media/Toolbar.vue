<script setup lang="ts">
import type { DownloadFilter } from '~/types'

/** View tabs, category carousel, live indicator and search box. */
defineProps<{ counts: Record<DownloadFilter, number>; live: boolean }>()

const filter = defineModel<DownloadFilter>('filter', { required: true })
const category = defineModel<string | null>('category', { required: true })
const search = defineModel<string>('search', { required: true })
const layout = defineModel<'rows' | 'grid'>('layout', { default: 'rows' })

// hidden items have their own page, so there is no tab for them here
const views: DownloadFilter[] = ['all', 'favorites', 'active', 'failed']
</script>

<template>
  <div class="toolbar">
    <div class="toolbar-left">
      <div class="filters">
        <button
          v-for="f in views"
          :key="f"
          class="filter-btn"
          :class="{ on: filter === f, alert: f === 'failed' && counts.failed > 0 }"
          @click="filter = f"
        >
          {{ f }} <span class="count">({{ counts[f] }})</span>
        </button>
      </div>

      <MediaCategoryTabs v-model="category" />

      <span
        class="live mono"
        :class="{ on: live }"
        :title="live ? 'WebSocket connected' : 'Polling fallback'"
      >
        ● {{ live ? 'live' : 'polling' }}
      </span>
    </div>

    <div class="toolbar-right">
      <div class="layout-toggle" role="group" aria-label="View layout">
        <button
          type="button"
          class="layout-btn"
          :class="{ on: layout === 'rows' }"
          title="Scrollable row groups"
          aria-label="Scrollable row groups"
          @click="layout = 'rows'"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
        <button
          type="button"
          class="layout-btn"
          :class="{ on: layout === 'grid' }"
          title="Grid view"
          aria-label="Grid view"
          @click="layout = 'grid'"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="7" height="7" rx="1" />
            <rect x="14" y="3" width="7" height="7" rx="1" />
            <rect x="14" y="14" width="7" height="7" rx="1" />
            <rect x="3" y="14" width="7" height="7" rx="1" />
          </svg>
        </button>
      </div>

      <input v-model="search" class="input search" type="search" placeholder="Search downloads…" />
    </div>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  /* lets the category carousel shrink below its content width */
  min-width: 0;
}

/* the count is supporting detail — dimmed so the tab name still leads */
.count {
  opacity: 0.65;
}

/* a non-zero failure count is worth noticing — but once the tab is selected
   the accent fill already marks it, and red-on-accent is unreadable */
.filter-btn.alert:not(.on) {
  color: var(--err);
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

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-left: auto;
}

.layout-toggle {
  display: inline-flex;
  align-items: center;
  padding: 2px;
  background: var(--surface-2, rgba(127, 127, 127, 0.08));
  border: 1px solid var(--line);
  border-radius: 7px;
}

.layout-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 5px;
  border: none;
  background: transparent;
  color: var(--text-faint);
  cursor: pointer;
  transition: all 0.15s ease;
}

.layout-btn:hover {
  color: var(--text);
}

.layout-btn.on {
  color: var(--accent);
  background: var(--surface-hover);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.search {
  max-width: 240px;
  font-size: 0.85rem;
}

@media (max-width: 640px) {
  .toolbar-right {
    width: 100%;
    margin-left: 0;
  }

  .search {
    max-width: none;
    flex: 1;
  }
}
</style>
