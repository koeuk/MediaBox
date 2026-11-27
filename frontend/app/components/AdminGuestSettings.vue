<script setup lang="ts">
import { GUEST_QUALITY_OPTIONS, guestQualityLabel, type GuestQualitySettings } from '~/utils/guestQualities'

const { request } = useApi()
const loaded = ref(false)
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const message = ref('')
const allowed = ref<string[]>([])
const defaultQuality = ref('480')
const saved = ref('')
const defaultOptions = computed(() => GUEST_QUALITY_OPTIONS.filter(option => allowed.value.includes(option.value)))
const payload = computed<GuestQualitySettings>(() => ({
  qualities: GUEST_QUALITY_OPTIONS.filter(option => allowed.value.includes(option.value)).map(option => option.value),
  default_quality: defaultQuality.value,
}))
const dirty = computed(() => JSON.stringify(payload.value) !== saved.value)

function adopt(value: GuestQualitySettings) {
  allowed.value = [...value.qualities]
  defaultQuality.value = value.default_quality
  saved.value = JSON.stringify(payload.value)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    adopt(await request<GuestQualitySettings>('/admin/guest-settings'))
    loaded.value = true
  } catch (e) {
    error.value = errorMessage(e, 'Could not load guest download settings.')
  } finally {
    loading.value = false
  }
}

function toggleQuality(value: string) {
  message.value = ''
  if (allowed.value.includes(value)) {
    if (allowed.value.length === 1) return
    allowed.value = allowed.value.filter(quality => quality !== value)
  } else {
    allowed.value = [...allowed.value, value]
  }
  if (!allowed.value.includes(defaultQuality.value)) {
    defaultQuality.value = defaultOptions.value[0]!.value
  }
}

async function save() {
  saving.value = true
  error.value = ''
  message.value = ''
  try {
    adopt(await request<GuestQualitySettings>('/admin/guest-settings', { method: 'PUT', body: payload.value }))
    message.value = 'Guest download settings saved.'
  } catch (e) {
    error.value = errorMessage(e, 'Could not save guest download settings.')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="panel guest-settings">
    <header class="settings-header">
      <p class="label">Public download page</p>
      <h2 class="display">Guest downloads</h2>
      <p class="description">Choose the qualities visitors can download without an account.</p>
    </header>

    <p v-if="loading" class="description" role="status">Loading settings…</p>
    <p v-if="error" class="message error" role="alert">{{ error }}</p>
    <button v-if="!loaded && !loading" type="button" class="btn" @click="load">Try again</button>

    <form v-if="loaded" @submit.prevent="save">
      <fieldset :disabled="saving" class="quality-fieldset">
        <legend class="field-label">Allowed qualities</legend>
        <div class="quality-grid">
          <label
            v-for="option in GUEST_QUALITY_OPTIONS"
            :key="option.value"
            class="quality-option"
            :class="{ selected: allowed.includes(option.value) }"
          >
            <input
              type="checkbox"
              :value="option.value"
              :checked="allowed.includes(option.value)"
              :disabled="allowed.length === 1 && allowed.includes(option.value)"
              @change="toggleQuality(option.value)"
            />
            <span>{{ option.label }}<small v-if="option.hint">{{ option.hint }}</small></span>
          </label>
        </div>
        <p class="description">Keep at least one enabled. Other qualities will show “Sign in” on the public page.</p>

        <label for="guest-default-quality" class="field-label default-label">Default selection</label>
        <select id="guest-default-quality" v-model="defaultQuality" class="input default-select" @change="message = ''">
          <option v-for="option in defaultOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
        <p class="selection-note mono">Visitors start with {{ guestQualityLabel(defaultQuality) }} selected.</p>
      </fieldset>

      <div class="actions">
        <button type="submit" class="btn btn-accent" :disabled="saving || !dirty">
          {{ saving ? 'Saving…' : 'Save guest settings' }}
        </button>
        <NuxtLink to="/free" class="btn btn-ghost">Open public page ↗</NuxtLink>
      </div>
      <p v-if="message" class="message success" role="status">{{ message }}</p>
    </form>
  </section>
</template>

<style scoped>
.guest-settings { padding: 1.5rem; }
.settings-header .label { margin: 0 0 0.5rem; color: var(--accent); }
.settings-header h2 { margin: 0 0 0.6rem; font-size: 1.6rem; }
.description { color: var(--text-dim); font-size: 0.8rem; line-height: 1.6; }
.quality-fieldset { border: 0; padding: 0; margin: 1.6rem 0 0; min-width: 0; }
.field-label { display: block; padding: 0; font-size: 0.8rem; font-weight: 600; margin-bottom: 0.7rem; }
.quality-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0.6rem; }
.quality-option { display: flex; align-items: center; gap: 0.7rem; padding: 0.9rem; border: 1px solid var(--line); border-radius: var(--radius); cursor: pointer; }
.quality-option.selected { border-color: var(--accent); background: var(--accent-soft); }
.quality-option:focus-within { outline: 2px solid var(--accent); outline-offset: 3px; }
.quality-option input { accent-color: var(--accent); width: 1rem; height: 1rem; flex-shrink: 0; }
.quality-option span { font-size: 0.9rem; font-weight: 600; }
.quality-option small { display: block; color: var(--text-dim); font-size: 0.65rem; font-weight: 400; margin-top: 0.2rem; }
.default-label { margin-top: 1.5rem; }
.default-select { width: 100%; max-width: 16rem; }
.selection-note { color: var(--text-dim); font-size: 0.7rem; margin: 0.7rem 0 0; }
.actions { display: flex; flex-wrap: wrap; align-items: center; gap: 0.6rem; margin-top: 1.5rem; }
.actions a { text-decoration: none; }
.message { font-size: 0.8rem; margin: 1rem 0 0; }
.error { color: var(--err); }
.success { color: var(--ok); }
@media (max-width: 420px) {
  .guest-settings { padding: 1.1rem; }
  .quality-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
