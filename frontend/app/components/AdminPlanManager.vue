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
const { can } = usePermissions()
const { paidMode } = useAccessSettings()
const modeLoaded = ref(false)
const savingMode = ref(false)

const plans = ref<Plan[]>([])
const drafts = reactive<Record<string, string>>({})
const freeDrafts = reactive<Record<string, boolean>>({})
const savingCode = ref<string | null>(null)
const error = ref('')
const notice = ref('')
const createOpen = ref(false)
const creating = ref(false)
const deletingCode = ref<string | null>(null)
const pendingDelete = ref<Plan | null>(null)
const newPlan = reactive({ code: '', label: '', days: 30, price: 0, is_free: false })

let noticeTimer: ReturnType<typeof setTimeout> | undefined
function flash(msg: string) {
  notice.value = msg
  clearTimeout(noticeTimer)
  noticeTimer = setTimeout(() => (notice.value = ''), 2500)
}

async function load() {
  try {
    const [loadedPlans, settings] = await Promise.all([
      request<Plan[]>('/admin/plans'),
      request<{ paid_mode: boolean }>('/admin/access-settings'),
    ])
    plans.value = loadedPlans
    paidMode.value = settings.paid_mode
    modeLoaded.value = true
    for (const p of plans.value) {
      drafts[p.code] = String(p.price)
      freeDrafts[p.code] = p.is_free
    }
  } catch (e) {
    error.value = errorMessage(e, 'Could not load plans.')
  }
}

async function toggleMode() {
  if (!modeLoaded.value || savingMode.value) return
  error.value = ''
  savingMode.value = true
  try {
    const settings = await request<{ paid_mode: boolean }>('/admin/access-settings', {
      method: 'PATCH',
      body: { paid_mode: !paidMode.value },
    })
    paidMode.value = settings.paid_mode
    flash(settings.paid_mode ? 'Paid mode enabled' : 'Free mode enabled')
  } catch (e) {
    error.value = errorMessage(e, 'Could not update access mode.')
  } finally {
    savingMode.value = false
  }
}

/** Unsaved edits are what the Save button acts on, so compare against the row. */
function changed(plan: Plan) {
  return drafts[plan.code] !== String(plan.price) || freeDrafts[plan.code] !== plan.is_free
}

async function save(plan: Plan) {
  if (savingCode.value) return
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
      body: { price, is_free: freeDrafts[plan.code] },
    })
    plans.value = plans.value.map((p) => (p.code === plan.code ? updated : p))
    drafts[plan.code] = String(updated.price)
    freeDrafts[plan.code] = updated.is_free
    flash(`${updated.label} updated`)
  } catch (e) {
    error.value = errorMessage(e, 'Could not save that price.')
  } finally {
    savingCode.value = null
  }
}

function startCreate() {
  error.value = ''
  Object.assign(newPlan, { code: '', label: '', days: 30, price: 0, is_free: false })
  createOpen.value = true
}

async function createPlan() {
  if (creating.value) return
  creating.value = true
  error.value = ''
  try {
    const plan = await request<Plan>('/admin/plans', { method: 'POST', body: { ...newPlan, code: newPlan.code.trim(), label: newPlan.label.trim() } })
    plans.value = [...plans.value, plan]
    drafts[plan.code] = String(plan.price)
    freeDrafts[plan.code] = plan.is_free
    createOpen.value = false
    flash(`${plan.label} created`)
  } catch (e) {
    error.value = fieldErrorMessage(e, 'Could not create that plan.')
  } finally {
    creating.value = false
  }
}

async function deletePlan() {
  const plan = pendingDelete.value
  if (!plan || deletingCode.value) return
  pendingDelete.value = null
  deletingCode.value = plan.code
  error.value = ''
  try {
    await request(`/admin/plans/${plan.code}`, { method: 'DELETE' })
    plans.value = plans.value.filter(p => p.code !== plan.code)
    delete drafts[plan.code]
    delete freeDrafts[plan.code]
    flash(`${plan.label} deleted`)
  } catch (e) {
    error.value = errorMessage(e, 'Could not delete that plan.')
  } finally {
    deletingCode.value = null
  }
}

onMounted(load)
onUnmounted(() => clearTimeout(noticeTimer))
</script>

<template>
  <section class="panel table-panel">
    <div class="access-mode">
      <div>
        <h2 class="label">Download access</h2>
        <p class="mode-description">
          {{ !modeLoaded ? 'Loading access mode…' : paidMode
            ? 'Paid — members need an active subscription for Best, 1080p, and higher.'
            : 'Free — every signed-in member can download at any quality.' }}
        </p>
      </div>
      <div class="mode-control" :aria-busy="savingMode">
        <span class="mono mode-label" :class="{ selected: modeLoaded && !paidMode }">Free</span>
        <button
          class="mode-switch"
          type="button"
          role="switch"
          aria-label="Require paid subscriptions for premium download qualities"
          :aria-checked="paidMode"
          :disabled="!can('plans.edit') || !modeLoaded || savingMode"
          @click="toggleMode"
        >
          <span class="mode-thumb" />
        </button>
        <span class="mono mode-label" :class="{ selected: modeLoaded && paidMode }">Paid</span>
      </div>
    </div>
    <p class="mode-footnote mono">Saved plan prices and existing subscriptions are kept when switching modes.</p>
    <div class="plans-heading">
      <h2 class="label table-title">Plans &amp; pricing</h2>
      <button v-if="can('plans.create')" class="btn btn-accent" type="button" @click="startCreate">Create plan</button>
    </div>

    <p v-if="error" class="msg err mono">{{ error }}</p>
    <p v-else-if="notice" class="msg ok mono" role="status">{{ notice }}</p>

    <form v-if="createOpen" class="create-plan" @submit.prevent="createPlan">
      <h3 class="label">Create plan</h3>
      <fieldset class="plan-fields" :disabled="creating">
        <label><span class="label">Code</span><input v-model="newPlan.code" class="input" required maxlength="16" pattern="[a-z0-9][a-z0-9_-]{0,15}" placeholder="e.g. quarterly" /></label>
        <label><span class="label">Label</span><input v-model="newPlan.label" class="input" required maxlength="40" placeholder="e.g. 3 months" /></label>
        <label><span class="label">Days</span><input v-model.number="newPlan.days" class="input" type="number" required min="1" max="3650" step="1" /></label>
        <label><span class="label">Price</span><input v-model.number="newPlan.price" class="input" type="number" required min="0" max="99999999.99" step="0.01" :disabled="newPlan.is_free" /></label>
        <label class="free-plan"><input v-model="newPlan.is_free" type="checkbox" /> Free plan</label>
      </fieldset>
      <div class="create-actions">
        <button class="btn btn-ghost" type="button" :disabled="creating" @click="createOpen = false">Cancel</button>
        <button class="btn btn-accent" type="submit" :disabled="creating">{{ creating ? 'Creating…' : 'Create plan' }}</button>
      </div>
    </form>

    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Plan</th>
            <th class="num">Days</th>
            <th>Access</th>
            <th class="num">Price</th>
            <th class="actions-col">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in plans" :key="p.code">
            <td>{{ p.label }}</td>
            <td class="num mono dim">{{ p.days }}</td>
            <td>
              <div class="mode-control">
                <span class="mono mode-label" :class="{ selected: freeDrafts[p.code] }">Free</span>
                <button
                  class="mode-switch"
                  type="button"
                  role="switch"
                  :aria-label="`Require payment for ${p.label}`"
                  :aria-checked="!freeDrafts[p.code]"
                  :disabled="!can('plans.edit') || savingCode === p.code"
                  @click="freeDrafts[p.code] = !freeDrafts[p.code]"
                >
                  <span class="mode-thumb" />
                </button>
                <span class="mono mode-label" :class="{ selected: !freeDrafts[p.code] }">Paid</span>
              </div>
            </td>
            <td class="num">
              <input
                v-model="drafts[p.code]"
                class="input price-input mono"
                type="number"
                min="0"
                step="0.01"
                :aria-label="`Price for ${p.label}`"
                :disabled="!can('plans.edit') || freeDrafts[p.code] || savingCode === p.code"
              />
            </td>
            <td class="actions-col">
              <button
                v-if="can('plans.edit')"
                class="link-btn"
                :disabled="!can('plans.edit') || !changed(p) || savingCode !== null"
                @click="save(p)"
              >
                {{ savingCode === p.code ? 'Saving…' : 'Save' }}
              </button>
              <button v-if="can('plans.delete')" type="button" class="link-btn danger delete-plan" :aria-label="`Delete ${p.label}`" :disabled="deletingCode !== null || savingCode === p.code" @click="pendingDelete = p">{{ deletingCode === p.code ? 'Deleting…' : 'Delete' }}</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <p class="hint mono">
      Save each row to apply its Free/Paid setting. Free plans activate without payment;
      their saved prices are kept. A paid plan priced at 0 shows as “Ask admin”.
      The Download access switch above applies to all downloads.
    </p>
    <ConfirmDialog :open="!!pendingDelete" title="Delete this plan?" :message="`Remove “${pendingDelete?.label}” from available plans? Existing subscriptions and payment history are kept.`" confirm-label="Delete plan" danger @confirm="deletePlan" @cancel="pendingDelete = null" />
  </section>
</template>

<style scoped>
.plans-heading { display: flex; justify-content: space-between; align-items: center; gap: 1rem; padding: 0.9rem 1.2rem 0; }
.plans-heading .table-title { padding: 0; }
.plans-heading .btn { font-size: 0.72rem; }
.create-plan { margin: 1rem 1.2rem; padding: 1rem; border: 1px solid var(--line); border-radius: 6px; }
.create-plan h3 { margin: 0 0 0.8rem; }
.plan-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.8rem; border: 0; padding: 0; margin: 0; min-width: 0; }
.plan-fields .label { display: block; margin-bottom: 0.3rem; }
.free-plan { display: flex; align-items: center; gap: 0.4rem; font-size: 0.78rem; }
.create-actions { display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 1rem; }
.delete-plan { margin-left: 0.7rem; color: var(--err); }
@media (max-width: 480px) { .plan-fields { grid-template-columns: 1fr; } }

.access-mode {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
  padding: 1.2rem 1.2rem 0.6rem;
}

.access-mode h2 { margin: 0; }
.mode-description { margin: 0.55rem 0 0; font-size: 0.8rem; color: var(--text-dim); }
.mode-control { display: flex; align-items: center; gap: 0.65rem; }
.mode-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-faint); }
.mode-label.selected { color: var(--accent); }
.mode-switch { width: 46px; height: 26px; padding: 3px; border: 1px solid var(--line); border-radius: 20px; background: var(--line); cursor: pointer; }
.mode-switch[aria-checked="true"] { background: var(--accent); border-color: var(--accent); }
.mode-switch:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
.mode-switch:disabled { opacity: 0.5; cursor: wait; }
.mode-thumb { display: block; width: 18px; height: 18px; background: var(--bg, #fff); border-radius: 50%; transition: transform 150ms ease; }
.mode-switch[aria-checked="true"] .mode-thumb { transform: translateX(20px); }
.mode-footnote { margin: 0; padding: 0 1.2rem 1.1rem; color: var(--text-faint); font-size: 0.66rem; border-bottom: 1px solid var(--line); }
@media (prefers-reduced-motion: reduce) { .mode-thumb { transition: none; } }

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
