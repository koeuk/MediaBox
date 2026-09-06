<script setup lang="ts">
/** Site logo upload — one image that becomes both the navbar logo and the
 *  favicon for every visitor. */
const { request } = useApi()
const { logoUrl, hasLogo, refresh } = useBranding()

const fileInput = ref<HTMLInputElement>()
const busy = ref(false)
const err = ref('')

async function onPicked(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  // reset so picking the same file twice still fires a change event
  input.value = ''
  if (!file) return
  err.value = ''
  busy.value = true
  try {
    const body = new FormData()
    body.append('file', file)
    await request('/admin/logo', { method: 'PUT', body })
    refresh(true)
  } catch (e) {
    err.value = errorMessage(e, 'Could not upload that image.')
  } finally {
    busy.value = false
  }
}

async function removeLogo() {
  err.value = ''
  busy.value = true
  try {
    await request('/admin/logo', { method: 'DELETE' })
    refresh(false)
  } catch (e) {
    err.value = errorMessage(e, 'Could not remove the logo.')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="panel branding-panel">
    <h2 class="label table-title">Site branding</h2>
    <input ref="fileInput" type="file" accept="image/*" hidden @change="onPicked" />

    <div class="branding-row">
      <div class="logo-box">
        <img v-if="hasLogo" :src="logoUrl" alt="Site logo" />
        <span v-else class="wordmark display">Media<span>Box</span></span>
      </div>

      <div class="branding-text">
        <p class="branding-hint">
          Upload one image to use as the navbar logo and the browser-tab icon
          (favicon) for everyone. A square image around 128×128 works best.
        </p>
        <p v-if="err" class="msg err mono">{{ err }}</p>
        <div class="branding-actions">
          <button class="btn btn-accent" :disabled="busy" @click="fileInput?.click()">
            {{ busy ? 'Working…' : hasLogo ? 'Change logo' : 'Upload logo' }}
          </button>
          <button v-if="hasLogo" class="btn btn-ghost" :disabled="busy" @click="removeLogo">
            Remove
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.branding-panel {
  padding: 1.1rem 1.3rem;
}

.branding-row {
  display: flex;
  align-items: center;
  gap: 1.2rem;
  flex-wrap: wrap;
}

.logo-box {
  width: 84px;
  height: 84px;
  display: grid;
  place-items: center;
  border: 1px dashed var(--border, #2c2c2e);
  border-radius: 12px;
  overflow: hidden;
  flex-shrink: 0;
}

.logo-box img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.logo-box .wordmark {
  font-size: 0.8rem;
}

.branding-text {
  flex: 1;
  min-width: 220px;
}

.branding-hint {
  margin: 0 0 0.6rem;
  color: var(--text-dim, #9a9a9a);
  font-size: 0.85rem;
}

.branding-actions {
  display: flex;
  gap: 0.6rem;
}
</style>
