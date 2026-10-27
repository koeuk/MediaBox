<script setup lang="ts">
import type { AdminMonthStats } from '~/types'

const props = defineProps<{
  months: AdminMonthStats[]
  metric: 'downloads' | 'new_users'
  label: string
  kind: 'bar' | 'line'
}>()

const active = ref<number | null>(null)
watch(() => props.months, () => { active.value = null })

const total = computed(() => props.months.reduce((sum, month) => sum + month[props.metric], 0))
const maximum = computed(() => Math.max(1, ...props.months.map(month => month[props.metric])))
const step = computed(() => {
  const rough = maximum.value / 4
  const power = 10 ** Math.floor(Math.log10(rough))
  const factor = [1, 2, 5, 10].find(value => value * power >= rough) || 10
  return Math.max(1, factor * power)
})
const ceiling = computed(() => Math.ceil(maximum.value / step.value) * step.value)
const ticks = computed(() => Array.from(
  { length: Math.round(ceiling.value / step.value) + 1 }, (_, i) => i * step.value,
))
const slot = computed(() => 534 / Math.max(1, props.months.length))
const points = computed(() => props.months.map((month, i) => ({
  ...month,
  value: month[props.metric],
  x: 48 + slot.value * (i + 0.5),
  y: 198 - month[props.metric] / ceiling.value * 176,
})))
const line = computed(() => points.value.map(point => `${point.x},${point.y}`).join(' '))
const area = computed(() => points.value.length
  ? `${points.value[0]!.x},198 ${line.value} ${points.value.at(-1)!.x},198`
  : '')
const highlighted = computed(() => active.value === null ? null : points.value[active.value])
const labelEvery = computed(() => Math.max(1, Math.ceil(props.months.length / 6)))
const count = new Intl.NumberFormat('en-US')
const axisCount = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 })
const monthLabel = (month: string, long = false) => new Date(`${month}T00:00:00Z`).toLocaleDateString('en-US', {
  month: long ? 'long' : 'short', year: long ? 'numeric' : '2-digit', timeZone: 'UTC',
})
</script>

<template>
  <article class="panel chart-card" :class="{ registrations: kind === 'line' }">
    <div class="chart-heading">
      <div>
        <h3 class="label">{{ label }}</h3>
        <p class="chart-total display">{{ count.format(total) }}</p>
      </div>
      <span class="chart-legend mono"><span />{{ kind === 'bar' ? 'All statuses' : 'New registrations' }}</span>
    </div>

    <div class="chart-wrap" @mouseleave="active = null">
      <svg viewBox="0 0 600 240" role="group" :aria-label="label" class="chart">
        <g v-for="tick in ticks" :key="tick" class="chart-grid">
          <line x1="48" x2="582" :y1="198 - tick / ceiling * 176" :y2="198 - tick / ceiling * 176" />
          <text x="35" :y="202 - tick / ceiling * 176" text-anchor="end">{{ axisCount.format(tick) }}</text>
        </g>

        <template v-if="kind === 'line'">
          <polygon :points="area" class="chart-area" />
          <polyline :points="line" class="chart-line" />
        </template>

        <g
          v-for="(point, i) in points"
          :key="point.month"
          class="month-point"
          :class="{ active: active === i }"
          tabindex="0"
          role="img"
          :aria-label="`${monthLabel(point.month, true)}: ${count.format(point.value)} ${label.toLowerCase()}`"
          @mouseenter="active = i"
          @focus="active = i"
          @blur="active = null"
        >
          <rect :x="point.x - slot / 2" y="18" :width="slot" height="184" class="chart-hit" />
          <line v-if="active === i" :x1="point.x" :x2="point.x" y1="18" y2="198" class="chart-guide" />
          <rect
            v-if="kind === 'bar'"
            :x="point.x - Math.min(32, slot * 0.58) / 2"
            :y="point.y"
            :width="Math.min(32, slot * 0.58)"
            :height="Math.max(0, 198 - point.y)"
            rx="3"
            class="chart-bar"
          />
          <circle v-else :cx="point.x" :cy="point.y" :r="active === i ? 5 : 3.5" class="chart-dot" />
          <text
            v-if="i % labelEvery === 0 || i === points.length - 1"
            :x="point.x"
            y="225"
            text-anchor="middle"
            class="month-label"
          >{{ monthLabel(point.month) }}</text>
        </g>
      </svg>

      <div
        v-if="highlighted"
        class="chart-tooltip mono"
        :style="{ left: `${Math.max(18, Math.min(82, highlighted.x / 6))}%` }"
        aria-hidden="true"
      >
        <span>{{ monthLabel(highlighted.month, true) }}</span>
        <strong>{{ count.format(highlighted.value) }} {{ metric === 'downloads' ? 'downloads' : 'new users' }}</strong>
      </div>
    </div>

    <p class="chart-note mono">
      <template v-if="total === 0">No {{ metric === 'downloads' ? 'downloads' : 'new users' }} in this date range.</template>
      <template v-else>{{ kind === 'bar' ? 'Downloads created' : 'Accounts created' }} within the selected dates.</template>
    </p>
  </article>
</template>

<style scoped>
.chart-card { --chart-color: var(--accent); padding: 1.2rem 1.2rem 0.9rem; min-width: 0; }
.registrations { --chart-color: var(--ok); }
.chart-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; }
h3 { margin: 0 0 0.6rem; }
.chart-total { font-size: 2rem; line-height: 1; margin: 0; }
.chart-legend { display: flex; align-items: center; gap: 0.4rem; font-size: 0.6rem; color: var(--text-dim); padding-top: 0.15rem; }
.chart-legend span { width: 7px; height: 7px; border-radius: 2px; background: var(--chart-color); flex-shrink: 0; }
.chart-wrap { position: relative; margin-top: 1.2rem; }
.chart { width: 100%; height: auto; display: block; overflow: visible; }
.chart-grid line { stroke: var(--line); stroke-dasharray: 3 5; }
.chart-grid text, .month-label { fill: var(--text-dim); font: 11px 'IBM Plex Mono', monospace; }
.chart-bar { fill: var(--chart-color); opacity: 0.8; }
.active .chart-bar { opacity: 1; }
.chart-area { fill: var(--chart-color); opacity: 0.08; }
.chart-line { fill: none; stroke: var(--chart-color); stroke-width: 2.5; stroke-linejoin: round; stroke-linecap: round; }
.chart-dot { fill: var(--chart-color); stroke: var(--surface); stroke-width: 2; }
.chart-hit { fill: transparent; }
.chart-guide { stroke: var(--chart-color); opacity: 0.25; stroke-dasharray: 3 4; }
.month-point { outline: none; }
.month-point:focus-visible .chart-hit { stroke: var(--chart-color); stroke-width: 1; }
.chart-tooltip { position: absolute; top: 0; transform: translateX(-50%); padding: 0.65rem 0.8rem; background: var(--surface); border: 1px solid var(--line-strong); border-radius: 6px; box-shadow: var(--shadow); font-size: 0.65rem; white-space: nowrap; pointer-events: none; z-index: 1; }
.chart-tooltip span { display: block; color: var(--text-dim); margin-bottom: 0.3rem; }
.chart-tooltip strong { color: var(--chart-color); font-weight: 500; }
.chart-note { margin: 0.4rem 0 0; color: var(--text-dim); font-size: 0.62rem; line-height: 1.6; }
@media (max-width: 480px) {
  .chart-card { padding: 1rem 0.8rem 0.8rem; }
  .chart-legend { max-width: 110px; line-height: 1.5; }
}
</style>
