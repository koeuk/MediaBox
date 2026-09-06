<script setup lang="ts">
import type { Plan } from '~/types'

/**
 * What each subscription length costs.
 *
 * Prices are rows in the database rather than constants in the code, so the
 * admin can change them here without a deploy — and the upgrade dialog reads
 * the same numbers from the public endpoint.
 */
const { request } = useApi()

const plans = ref<Plan[]>([])
const drafts = reactive<Record<string, string>>({})
const savingCode = ref<string | null>(null)
const error = ref('')
const notice = ref('')

let noticeTimer: ReturnType<typeof setTimeout> | undefined
function flash(msg: string) {
  notice.value = msg
  clearTimeout(noticeTimer)
  noticeTimer = setTimeout(() => (notice.value = ''), 2500)
}

async function load() {
  try {
    plans.value = await request<Plan[]>('/admin/plans')
    for (const p of plans.value) drafts[p.code] = String(p.price)
  } catch (e) {
    error.value = errorMessage(e, 'Could not load plans.')
  }
}

/** Unsaved edits are what the Save button acts on, so compare against the row. */
function changed(plan: Plan) {
  return drafts[plan.code] !== String(plan.price)
}

async function save(plan: Plan) {
  const price = Number(drafts[plan.code])
  if (!Number.isFinite(price) || price < 0) {
    error.value = 'Price must be a number, and not negative.'
    return
  }
  error.value = ''
  savingCode.value = plan.code
  try {
    const updated = await request<Plan>(`/admin/plans/${plan.code}`, {
      method: 'PATCH',
      body: { price },
    })
    plans.value = plans.value.map((p) => (p.code === plan.code ? updated : p))
    drafts[plan.code] = String(updated.price)
    flash(`${updated.label} updated`)
  } catch (e) {
    error.value = errorMessage(e, 'Could not save that price.')
  } finally {
    savingCode.value = null
  }
}

onMounted(load)
</script>

<template>
  <section class="panel table-panel">
    <h2 class="label table-title">Plans &amp; pricing</h2>

    <p v-if="error" class="msg err mono">{{ error }}</p>
    <p v-else-if="notice" class="msg ok mono">{{ notice }}</p>

    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Plan</th>
            <th class="num">Days</th>
            <th class="num">Price</th>
            <th class="actions-col">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in plans" :key="p.code">
            <td>{{ p.label }}</td>
            <td class="num mono dim">{{ p.days }}</td>
            <td class="num">
              <input
                v-model="drafts[p.code]"
                class="input price-input mono"
                type="number"
                min="0"
                step="0.01"
                :aria-label="`Price for ${p.label}`"
              />
            </td>
            <td class="actions-col">
              <button
                class="link-btn"
                :disabled="!changed(p) || savingCode === p.code"
                @click="save(p)"
              >
                {{ savingCode === p.code ? 'Saving…' : 'Save' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <p class="hint mono">
      A price of 0 shows as “Ask admin” in the upgrade dialog. Renewing extends
      an active subscription rather than restarting it.
    </p>
  </section>
</template>

<style scoped>
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

.price-input {
  width: 110px;
  padding: 0.3rem 0.45rem;
  font-size: 0.8rem;
  text-align: right;
}

.actions-col {
  text-align: right;
  white-space: nowrap;
}

.link-btn {
  border: none;
  background: none;
  padding: 0;
  color: var(--accent);
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  cursor: pointer;
}

.link-btn:hover:not(:disabled) {
  text-decoration: underline;
}

.link-btn:disabled {
  opacity: 0.4;
  cursor: default;
}

.hint {
  margin: 0;
  padding: 0.6rem 1.2rem 1rem;
  font-size: 0.66rem;
  color: var(--text-faint);
}

.msg {
  margin: 0.8rem 1.2rem 0;
  padding: 0.5rem 0.7rem;
  border-radius: 6px;
  font-size: 0.74rem;
}

.msg.err {
  background: var(--err-soft);
  color: var(--err);
}

.msg.ok {
  background: var(--ok-soft);
  color: var(--ok);
}
</style>
