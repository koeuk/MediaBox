<script setup lang="ts">
/**
 * Shown when a free account picks a paid rung of the quality ladder.
 *
 * Pressing "I paid" applies the plan immediately — there is no verification
 * step, so this is an honour system: the record it writes is a receipt of what
 * was granted, not a request for someone to approve.
 */
import type { Plan } from '~/types'

const props = defineProps<{ open: boolean; quality?: string }>()
const emit = defineEmits<{ close: [] }>()

type Method = 'qr' | 'cash'
const method = ref<Method>('qr')

const config = useRuntimeConfig()
const plans = ref<Plan[]>([])
const chosen = ref<string>('')

// Prices are set by the admin, so they are fetched rather than hardcoded. The
// endpoint is public — it is a price list, and the dialog must still render
// if it fails.
async function loadPlans() {
  if (plans.value.length) return
  try {
    plans.value = await $fetch<Plan[]>('/public/plans', {
      baseURL: config.public.apiBase,
      timeout: 5000,
    })
    chosen.value = plans.value[0]?.code || ''
  } catch {
    plans.value = []
  }
}

/** Cash can be switched off by an admin, in which case the tab is not offered. */
async function loadSettings() {
  try {
    const s = await $fetch<{ cash_enabled: boolean }>('/public/payment-settings', {
      baseURL: config.public.apiBase,
      timeout: 5000,
    })
    cashEnabled.value = s.cash_enabled
    if (!cashEnabled.value && method.value === 'cash') method.value = 'qr'
  } catch {
    // leave cash visible: a settings blip should not remove a payment option
  }
}

/** Apply the plan. Refreshes the user so the picker unlocks without a reload. */
async function submitPaid() {
  if (!amount.value) {
    sendError.value = 'That plan has no price set yet.'
    return
  }
  sendError.value = ''
  sending.value = true
  try {
    await request('/payments', {
      method: 'POST',
      body: { plan_code: chosen.value, method: method.value },
    })
    sent.value = true
    await fetchUser()
  } catch (e) {
    sendError.value = errorMessage(e, 'Could not send that. Try again.')
  } finally {
    sending.value = false
  }
}

/** An unpriced plan is one the admin has not filled in yet. */
function priceLabel(plan: Plan) {
  return plan.price > 0 ? plan.price.toFixed(2) : 'Ask admin'
}

const QR_IMAGE = '/payment-qr.svg'

const { request } = useApi()
const { fetchUser } = useAuth()
const cashEnabled = ref(true)
const sending = ref(false)
const sent = ref(false)
const sendError = ref('')

/** The selected plan, which is what both payment tabs quote a price for. */
const selected = computed(() => plans.value.find((p) => p.code === chosen.value) || null)

const amount = computed(() => {
  const price = selected.value?.price
  return price && price > 0 ? price.toFixed(2) : null
})

const label = computed(() => {
  if (!props.quality) return 'Best quality'
  return props.quality === '2160' ? '4K' : `${props.quality}p`
})

// reopening should always land on the same first choice
watch(
  () => props.open,
  (open) => {
    if (!open) return
    method.value = 'qr'
    sent.value = false
    sendError.value = ''
    loadPlans()
    loadSettings()
  },
  { immediate: true }
)

function onKey(e: KeyboardEvent) {
  if (props.open && e.key === 'Escape') emit('close')
}
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <Transition name="dlg">
      <div v-if="open" class="overlay" @click.self="emit('close')">
        <div class="panel card" role="dialog" aria-modal="true" aria-labelledby="upgrade-title">
          <h2 id="upgrade-title" class="display title">Upgrade for {{ label }}</h2>
          <p class="sub">
            Downloads above 720p need an upgraded account. Pay with either method
            below, then press “I paid” to unlock it.
          </p>

          <div v-if="plans.length" class="plans">
            <label
              v-for="p in plans"
              :key="p.code"
              class="plan"
              :class="{ on: chosen === p.code }"
            >
              <input v-model="chosen" type="radio" :value="p.code" name="plan" />
              <span class="plan-label">{{ p.label }}</span>
              <span class="plan-price mono">{{ priceLabel(p) }}</span>
            </label>
          </div>

          <div class="filters methods" role="tablist" aria-label="Payment method">
            <button
              class="filter-btn"
              :class="{ on: method === 'qr' }"
              type="button"
              role="tab"
              :aria-selected="method === 'qr'"
              @click="method = 'qr'"
            >
              QR code
            </button>
            <button
              v-if="cashEnabled"
              class="filter-btn"
              :class="{ on: method === 'cash' }"
              type="button"
              role="tab"
              :aria-selected="method === 'cash'"
              @click="method = 'cash'"
            >
              Cash
            </button>
          </div>

          <div v-if="method === 'qr'" class="body">
            <img class="qr" :src="QR_IMAGE" alt="Payment QR code" />
            <p v-if="amount" class="amount mono">{{ amount }}</p>
          </div>

          <div v-else class="body">
            <p v-if="amount" class="amount mono amount-lg">{{ amount }}</p>
            <p v-else class="hint mono">No price set for this plan yet.</p>
          </div>

          <template v-if="sent">
            <p class="done mono">
              Upgraded. High quality is unlocked on your account — close this and
              pick the quality you want.
            </p>
          </template>

          <template v-else>
            <div class="paid-row">
              <div class="paid-total">
                <span class="label">Total</span>
                <span class="paid-amount mono">{{ amount ?? '—' }}</span>
              </div>
              <button
                class="btn btn-accent"
                type="button"
                :disabled="sending || !chosen || !amount"
                @click="submitPaid"
              >
                {{ sending ? 'Sending…' : 'I paid' }}
              </button>
            </div>

            <p v-if="sendError" class="err-note mono">{{ sendError }}</p>
            <p v-else class="pending mono">
              Pressing “I paid” unlocks high quality straight away.
            </p>
          </template>

          <div class="actions">
            <button class="btn" type="button" @click="emit('close')">
              {{ sent ? 'Done' : 'Close' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 900;
  display: grid;
  place-items: center;
  padding: 1.2rem;
  background: color-mix(in srgb, #000 55%, transparent);
  backdrop-filter: blur(2px);
}

.card {
  width: min(420px, 100%);
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.title {
  margin: 0;
  font-size: 1.15rem;
}

.sub {
  margin: 0;
  font-size: 0.8rem;
  line-height: 1.55;
  color: var(--text-dim);
}

.plans {
  display: grid;
  gap: 0.35rem;
}

.plan {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.5rem 0.7rem;
  border: 1px solid var(--line);
  border-radius: 7px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.plan:hover {
  border-color: var(--accent);
}

.plan.on {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.plan-label {
  flex: 1;
  font-size: 0.85rem;
}

.plan-price {
  font-size: 0.8rem;
  color: var(--accent);
}

.methods {
  align-self: flex-start;
}

.body {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.6rem;
  padding: 0.9rem;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--bg-raised);
}

.qr {
  width: 180px;
  height: 180px;
  display: block;
  /* a QR must stay high-contrast to scan, so it keeps its own white ground
     rather than inheriting the dark theme */
  background: #fff;
  border-radius: 6px;
  padding: 8px;
}

.amount {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--accent);
}

/* on the cash tab the amount is the whole content, so it carries the panel */
.amount-lg {
  font-size: 1.9rem;
  padding: 0.6rem 0;
}

.hint {
  margin: 0;
  font-size: 0.66rem;
  color: var(--text-faint);
  text-align: center;
}

.done {
  margin: 0;
  padding: 0.55rem 0.7rem;
  border-radius: 6px;
  background: var(--ok-soft);
  color: var(--ok);
  font-size: 0.7rem;
  line-height: 1.5;
}

.pending {
  margin: 0;
  padding: 0.55rem 0.7rem;
  border-radius: 6px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 0.68rem;
  line-height: 1.5;
}

.paid-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.6rem 0.75rem;
  border: 1px solid var(--line);
  border-radius: 7px;
}

.paid-total {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
}

.paid-amount {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--accent);
}

.err-note {
  margin: 0;
  padding: 0.5rem 0.7rem;
  border-radius: 6px;
  background: var(--err-soft);
  color: var(--err);
  font-size: 0.68rem;
}

.actions {
  display: flex;
  justify-content: flex-end;
}

.dlg-enter-active,
.dlg-leave-active {
  transition: opacity 0.16s;
}

.dlg-enter-from,
.dlg-leave-to {
  opacity: 0;
}
</style>
