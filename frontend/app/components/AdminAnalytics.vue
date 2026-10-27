<script setup lang="ts">
import type { AdminAnalytics, AdminDateRange } from '~/types'

const props = defineProps<{
  data: AdminAnalytics | null
  range: AdminDateRange
  loading: boolean
  error: string
}>()
const emit = defineEmits<{ apply: [range: AdminDateRange] }>()
const draft = reactive({ ...props.range })
const validation = ref('')
const presets = [{ months: 1, label: 'This month' }, { months: 6, label: '6 months' }, { months: 12, label: '12 months' }]

watch(() => props.range, range => { Object.assign(draft, range) })
const activePreset = computed(() => presets.find(preset => {
  const range = adminDateRange(preset.months)
  return range.start_date === draft.start_date && range.end_date === draft.end_date
})?.months)

function apply(range: AdminDateRange) {
  validation.value = ''
  if (!range.start_date || !range.end_date || range.start_date > range.end_date) {
    validation.value = 'Choose a start date on or before the end date.'
    return
  }
  const start = new Date(`${range.start_date}T00:00:00Z`)
  const end = new Date(`${range.end_date}T00:00:00Z`)
  const months = (end.getUTCFullYear() - start.getUTCFullYear()) * 12 + end.getUTCMonth() - start.getUTCMonth() + 1
  if (months > 120) {
    validation.value = 'Choose a date range of 10 years or less.'
    return
  }
  Object.assign(draft, range)
  emit('apply', { ...range })
}

const periodLabel = computed(() => {
  const format = (date: string) => new Date(`${date}T00:00:00Z`).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC',
  })
  return `${format(props.range.start_date)} – ${format(props.range.end_date)}`
})
</script>

<template>
  <section class="analytics" aria-labelledby="activity-title" :aria-busy="loading">
    <div class="activity-heading">
      <div>
        <h2 id="activity-title">Activity overview</h2>
        <p>Monthly downloads and new users</p>
      </div>
      <div class="filters presets" role="group" aria-label="Activity date presets">
        <button
          v-for="preset in presets"
          :key="preset.months"
          type="button"
          class="filter-btn"
          :class="{ on: activePreset === preset.months }"
          :aria-pressed="activePreset === preset.months"
          :disabled="loading"
          @click="apply(adminDateRange(preset.months))"
        >{{ preset.label }}</button>
      </div>
    </div>

    <form class="date-filter" @submit.prevent="apply({ ...draft })">
      <div class="date-fields">
        <label class="date-field">
          <span class="label">From</span>
          <input v-model="draft.start_date" class="input mono" type="date" required :max="draft.end_date || undefined" />
        </label>
        <span class="date-arrow" aria-hidden="true">→</span>
        <label class="date-field">
          <span class="label">To</span>
          <input v-model="draft.end_date" class="input mono" type="date" required :min="draft.start_date || undefined" />
        </label>
        <button class="btn btn-accent apply-btn" type="submit" :disabled="loading">{{ loading ? 'Loading…' : 'Apply' }}</button>
      </div>
      <p class="date-hint mono">Dates in UTC · Filters charts &amp; recent downloads</p>
    </form>

    <p v-if="validation || error" class="analytics-error mono" role="alert">{{ validation || error }}</p>

    <div class="chart-period mono" role="status" aria-live="polite">
      <span>{{ loading ? 'Loading activity…' : periodLabel }}</span>
      <span>Grouped by month</span>
    </div>
    <div v-if="data" class="charts" :class="{ loading }">
      <AdminMonthlyChart :months="data.months" metric="downloads" label="Downloads per month" kind="bar" />
      <AdminMonthlyChart :months="data.months" metric="new_users" label="Users per month" kind="line" />
    </div>
    <div v-else class="panel chart-placeholder mono">
      {{ loading ? 'Loading monthly activity…' : 'Monthly activity is unavailable. Apply a date range to try again.' }}
    </div>
  </section>
</template>

<style scoped>
.analytics { margin: 0 0 1.8rem; }
.activity-heading { display: flex; justify-content: space-between; align-items: center; gap: 1rem; margin-bottom: 1rem; }
.activity-heading h2 { font-size: 1.05rem; font-weight: 600; margin: 0 0 0.35rem; }
.activity-heading p { color: var(--text-dim); font-size: 0.78rem; margin: 0; }
.presets { flex-shrink: 0; }
.date-filter { display: flex; align-items: flex-end; justify-content: space-between; flex-wrap: wrap; gap: 0.8rem 1rem; padding: 1rem; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); }
.date-fields { display: flex; align-items: flex-end; gap: 0.7rem; }
.date-field { display: flex; flex-direction: column; gap: 0.45rem; }
.date-field .label { font-size: 0.6rem; }
.date-field input { width: 165px; font-size: 0.75rem; padding: 0.55rem 0.65rem; color-scheme: dark; }
[data-theme='light'] .date-field input { color-scheme: light; }
.date-arrow { color: var(--text-faint); padding-bottom: 0.6rem; }
.apply-btn { padding: 0.6rem 1rem; font-size: 0.7rem; min-height: 36px; }
.date-hint { color: var(--text-dim); font-size: 0.6rem; margin: 0 0 0.65rem; line-height: 1.6; }
.chart-period { display: flex; justify-content: space-between; gap: 1rem; margin: 1rem 0 0.65rem; color: var(--text-dim); font-size: 0.62rem; line-height: 1.6; }
.charts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }
.charts.loading { opacity: 0.5; pointer-events: none; }
.chart-placeholder { padding: 4rem 1.2rem; text-align: center; font-size: 0.75rem; color: var(--text-dim); }
.analytics-error { color: var(--err); font-size: 0.75rem; line-height: 1.6; margin: 0.8rem 0; }
.filter-btn:disabled { cursor: wait; opacity: 0.5; }
@media (max-width: 720px) {
  .charts { grid-template-columns: 1fr; }
  .activity-heading { align-items: flex-start; flex-direction: column; }
  .date-hint { margin-bottom: 0; }
}
@media (max-width: 480px) {
  .date-fields { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); width: 100%; }
  .date-field input { width: 100%; min-width: 0; }
  .date-arrow { display: none; }
  .apply-btn { grid-column: 1 / -1; }
  .chart-period { flex-wrap: wrap; gap: 0.25rem; }
}
</style>
