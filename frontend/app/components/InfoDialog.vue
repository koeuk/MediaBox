<script setup lang="ts">
import type { Download } from '~/types'

/** Read-only detail sheet for one record. */
const props = defineProps<{ download: Download | null }>()
const emit = defineEmits<{ close: [] }>()

const CUTOUT_TIERS: Record<string, string> = {
  fast: 'Fast (u2netp)',
  good: 'Good (u2net)',
  best: 'Best (isnet + alpha matting)',
}

function stamp(s: string | null) {
  return s ? new Date(s).toLocaleString() : '—'
}

const rows = computed(() => {
  const d = props.download
  if (!d) return []

  const isCutout = d.job_kind === 'cutout'
  const out: [string, string][] = [
    ['Name', d.title || d.filename || '—'],
    ['File', d.filename || '—'],
    ['Type', d.content_type || '—'],
    ['Size', d.total_bytes ? formatBytes(d.total_bytes) : '—'],
    ['Status', d.status],
  ]

  if (isCutout) {
    out.push(['Method', 'Background removal'])
    out.push(['Quality', (d.quality && CUTOUT_TIERS[d.quality]) || d.quality || '—'])
  } else if (d.quality) {
    out.push(['Max height', `${d.quality}p`])
  }

  if (d.category) out.push(['Category', d.category])
  out.push(['Source', d.url])
  out.push(['Added', stamp(d.created_at)])
  out.push(['Finished', stamp(d.completed_at)])
  if (d.error) out.push(['Error', d.error])
  return out
})

function onKey(e: KeyboardEvent) {
  if (props.download && e.key === 'Escape') emit('close')
}

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <Transition name="info">
      <div v-if="download" class="overlay" @click.self="emit('close')">
        <div class="sheet panel" role="dialog" aria-modal="true" aria-label="Details">
          <header class="head">
            <h3 class="title display">Details</h3>
            <button class="btn btn-ghost head-btn" aria-label="Close" @click="emit('close')">
              ✕
            </button>
          </header>

          <dl class="rows">
            <template v-for="[label, value] in rows" :key="label">
              <dt class="label">{{ label }}</dt>
              <dd class="value mono" :title="value">{{ value }}</dd>
            </template>
          </dl>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 110;
  display: grid;
  place-items: center;
  padding: 1.5rem;
  background: color-mix(in srgb, #000 55%, transparent);
  backdrop-filter: blur(3px);
}

.sheet {
  width: min(460px, 100%);
  max-height: 100%;
  overflow: auto;
  padding: 1.1rem 1.2rem 1.3rem;
  box-shadow: var(--shadow);
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.9rem;
}

.title {
  margin: 0;
  font-size: 1rem;
}

.head-btn {
  padding: 0.35rem 0.6rem;
}

.rows {
  display: grid;
  grid-template-columns: minmax(72px, auto) 1fr;
  gap: 0.45rem 0.9rem;
  margin: 0;
}

.rows .label {
  margin: 0;
  align-self: center;
}

.value {
  margin: 0;
  min-width: 0;
  font-size: 0.74rem;
  color: var(--text);
  /* a long URL must wrap rather than widen the sheet */
  overflow-wrap: anywhere;
}

.info-enter-active,
.info-leave-active {
  transition: opacity 0.15s ease;
}

.info-enter-active .sheet,
.info-leave-active .sheet {
  transition: transform 0.15s cubic-bezier(0.2, 0.7, 0.2, 1);
}

.info-enter-from,
.info-leave-to {
  opacity: 0;
}

.info-enter-from .sheet,
.info-leave-to .sheet {
  transform: scale(0.97);
}
</style>
