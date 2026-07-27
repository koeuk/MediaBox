<script setup lang="ts">
import type { DownloadFilter } from '~/types'

/** View tabs, category carousel, live indicator and search box. */
defineProps<{ activeCount: number; live: boolean }>()

const filter = defineModel<DownloadFilter>('filter', { required: true })
const category = defineModel<string | null>('category', { required: true })
const search = defineModel<string>('search', { required: true })

// hidden items have their own page, so there is no tab for them here
const views: DownloadFilter[] = ['all', 'favorites', 'active']
</script>

<template>
  <div class="toolbar">
    <div class="toolbar-left">
      <div class="filters">
        <button
          v-for="f in views"
          :key="f"
          class="filter-btn"
          :class="{ on: filter === f }"
          @click="filter = f"
        >
          {{ f }}<span v-if="f === 'active' && activeCount"> ({{ activeCount }})</span>
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

    <input v-model="search" class="input search" type="search" placeholder="Search downloads…" />
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

@media (max-width: 560px) {
  .search {
    max-width: none;
    width: 100%;
  }
}
</style>
