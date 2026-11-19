<script setup lang="ts">
import type { PaymentRequest } from '~/types'

/**
 * A record of every upgrade taken, newest first.
 *
 * Payments apply themselves, so nothing here needs approving — this is the
 * receipt log, plus the switch for whether cash is offered at all. Any row
 * still marked pending predates that change and can be approved by hand.
 */
const emit = defineEmits<{ granted: [] }>()

const { request } = useApi()

const rows = ref<PaymentRequest[]>([])
/** Only rows from before payments became automatic still need a decision. */
const pendingCount = computed(() => rows.value.filter((r) => r.status === 'pending').length)
const busyId = ref<number | null>(null)
const cashEnabled = ref(true)
const savingCash = ref(false)
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
    const [queue, settings] = await Promise.all([
      request<PaymentRequest[]>('/admin/payments', { params: { pending_only: false } }),
      request<{ cash_enabled: boolean }>('/admin/payment-settings'),
    ])
    rows.value = queue
    cashEnabled.value = settings.cash_enabled
  } catch (e) {
    error.value = errorMessage(e, 'Could not load payments.')
  }
}

async function review(row: PaymentRequest, action: 'approve' | 'reject') {
  error.value = ''
  busyId.value = row.id
  try {
    await request(`/admin/payments/${row.id}/${action}`, { method: 'POST' })
    await load()
    flash(action === 'approve' ? `${row.username} upgraded` : 'Request rejected')
    // the users table shows the new expiry, so it has to reload too
    if (action === 'approve') emit('granted')
  } catch (e) {
    error.value = errorMessage(e, `Could not ${action} that request.`)
  } finally {
    busyId.value = null
  }
}

/** Turning cash off hides it in the upgrade dialog and refuses new cash claims. */
async function toggleCash() {
  savingCash.value = true
  error.value = ''
  try {
    const next = !cashEnabled.value
    const saved = await request<{ cash_enabled: boolean }>('/admin/payment-settings', {
      method: 'PATCH',
      body: { cash_enabled: next },
    })
    cashEnabled.value = saved.cash_enabled
    flash(saved.cash_enabled ? 'Cash payments on' : 'Cash payments off')
  } catch (e) {
    error.value = errorMessage(e, 'Could not change that setting.')
  } finally {
    savingCash.value = false
  }
}

defineExpose({ load })
onMounted(load)
</script>

<template>
  <section class="panel table-panel">
    <div class="head">
      <h2 class="label table-title">
        Payments
        <span v-if="pendingCount" class="count mono">{{ pendingCount }} to review</span>
      </h2>

      <label class="cash-toggle">
        <input
          type="checkbox"
          :checked="cashEnabled"
          :disabled="savingCash"
          @change="toggleCash"
        />
        <span class="mono">Offer cash</span>
      </label>
    </div>

    <p v-if="error" class="msg err mono">{{ error }}</p>
    <p v-else-if="notice" class="msg ok mono">{{ notice }}</p>

    <p v-if="!rows.length" class="empty mono">No payments yet.</p>

    <div v-else class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>User</th>
            <th>Plan</th>
            <th>Method</th>
            <th class="num">Amount</th>
            <th>Status</th>
            <th>When</th>
            <th class="actions-col">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.id">
            <td>{{ r.username }}</td>
            <td>{{ r.plan_label }}</td>
            <td class="mono dim">{{ r.method }}</td>
            <td class="num mono">{{ r.amount.toFixed(2) }}</td>
            <td>
              <span
                class="badge"
                :class="r.status === 'pending' ? 'badge-downloading' : 'badge-completed'"
              >{{ r.status }}</span>
            </td>
            <td class="dim">{{ formatDate(r.created_at) }}</td>
            <td class="actions-col">
              <div v-if="r.status === 'pending'" class="actions">
                <button
                  class="link-btn"
                  :disabled="busyId === r.id"
                  @click="review(r, 'approve')"
                >
                  Approve
                </button>
                <button
                  class="link-btn danger"
                  :disabled="busyId === r.id"
                  @click="review(r, 'reject')"
                >
                  Reject
                </button>
              </div>
              <span v-else class="dim mono done-mark">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.table-panel {
  margin-bottom: 1.4rem;
  overflow: hidden;
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.9rem 1.2rem 0;
}

.table-title {
  margin: 0;
}

.count {
  margin-left: 0.5rem;
  color: var(--accent);
  text-transform: none;
  letter-spacing: 0;
}

.cash-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.66rem;
  color: var(--text-dim);
  cursor: pointer;
}

.done-mark {
  font-size: 0.7rem;
}

.empty {
  margin: 0;
  padding: 0.9rem 1.2rem 1.1rem;
  font-size: 0.72rem;
  color: var(--text-faint);
}

.table-scroll {
  overflow-x: auto;
  margin-top: 0.6rem;
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
  padding: 0.5rem 1.2rem;
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

.actions-col {
  text-align: right;
  white-space: nowrap;
}

.actions {
  display: inline-flex;
  gap: 0.75rem;
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
  opacity: 0.45;
  cursor: default;
}

.link-btn.danger {
  color: var(--err);
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
