<script setup lang="ts">
/**
 * Site branding settings — configure the brand name/title wordmark and
 * upload the logo image that appears in the navbar and browser tab favicon.
 */
const { request } = useApi()
const { logoUrl, hasLogo, siteTitle, refresh } = useBranding()

const fileInput = ref<HTMLInputElement>()
const logoBusy = ref(false)
const logoErr = ref('')
const logoMsg = ref('')

const titleDraft = ref(siteTitle.value)
const titleSaving = ref(false)
const titleErr = ref('')
const titleMsg = ref('')

watch(
  siteTitle,
  (val) => {
    titleDraft.value = val
  },
  { immediate: true }
)

const previewParts = computed(() => formatTitleParts(titleDraft.value || siteTitle.value))
const isTitleDirty = computed(() => titleDraft.value.trim() !== siteTitle.value.trim())

async function onPicked(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  // reset so picking the same file twice still fires a change event
  input.value = ''
  if (!file) return
  logoErr.value = ''
  logoMsg.value = ''
  logoBusy.value = true
  try {
    const body = new FormData()
    body.append('file', file)
    await request('/admin/logo', { method: 'PUT', body })
    refresh(true)
    logoMsg.value = 'Logo uploaded successfully.'
    setTimeout(() => {
      if (logoMsg.value === 'Logo uploaded successfully.') logoMsg.value = ''
    }, 3500)
  } catch (e) {
    logoErr.value = errorMessage(e, 'Could not upload that image.')
  } finally {
    logoBusy.value = false
  }
}

async function removeLogo() {
  logoErr.value = ''
  logoMsg.value = ''
  logoBusy.value = true
  try {
    await request('/admin/logo', { method: 'DELETE' })
    refresh(false)
    logoMsg.value = 'Logo removed. Using default mark.'
    setTimeout(() => {
      if (logoMsg.value === 'Logo removed. Using default mark.') logoMsg.value = ''
    }, 3500)
  } catch (e) {
    logoErr.value = errorMessage(e, 'Could not remove the logo.')
  } finally {
    logoBusy.value = false
  }
}

async function saveTitle() {
  const clean = titleDraft.value.trim()
  if (!clean) {
    titleErr.value = 'Site title cannot be empty.'
    return
  }
  titleErr.value = ''
  titleMsg.value = ''
  titleSaving.value = true
  try {
    const res = await request<{ site_title: string; has_logo: boolean }>('/admin/branding/title', {
      method: 'PUT',
      body: { site_title: clean },
    })
    refresh(undefined, res.site_title)
    titleDraft.value = res.site_title
    titleMsg.value = 'Site title saved successfully.'
    setTimeout(() => {
      if (titleMsg.value === 'Site title saved successfully.') titleMsg.value = ''
    }, 3500)
  } catch (e) {
    titleErr.value = errorMessage(e, 'Could not update site title.')
  } finally {
    titleSaving.value = false
  }
}

async function resetTitle() {
  titleErr.value = ''
  titleMsg.value = ''
  titleSaving.value = true
  try {
    const res = await request<{ site_title: string; has_logo: boolean }>('/admin/branding/title', {
      method: 'DELETE',
    })
    refresh(undefined, res.site_title || 'MediaBox')
    titleDraft.value = res.site_title || 'MediaBox'
    titleMsg.value = 'Site title restored to default.'
    setTimeout(() => {
      if (titleMsg.value === 'Site title restored to default.') titleMsg.value = ''
    }, 3500)
  } catch (e) {
    titleErr.value = errorMessage(e, 'Could not reset site title.')
  } finally {
    titleSaving.value = false
  }
}
</script>

<template>
  <section class="panel panel-hover card branding-card">
    <div class="card-header">
      <h2 class="card-title">Site branding</h2>
      <p class="card-desc">
        Customize the name, title wordmark, and logo displayed in the navigation bar and browser tabs.
      </p>
    </div>

    <!-- Live Preview Banner -->
    <div class="preview-box">
      <span class="preview-tag">Navbar Preview</span>
      <div class="preview-brand">
        <img
          class="preview-logo"
          :class="{ 'is-mark': !hasLogo }"
          :src="hasLogo ? logoUrl : '/logo.svg'"
          alt="Site logo preview"
        />
        <span class="wordmark display">
          {{ previewParts.first }}<span v-if="previewParts.highlight">{{ previewParts.highlight }}</span>
        </span>
      </div>
    </div>

    <!-- Site Title Section -->
    <div class="branding-section">
      <div class="section-head">
        <label for="site-title-input" class="section-title">Brand name / Title</label>
        <span v-if="siteTitle !== 'MediaBox'" class="badge-custom">Customized</span>
      </div>
      <p class="branding-hint">
        Sets the main wordmark in the top-left navigation bar and browser tab title.
      </p>

      <p v-if="titleErr" class="msg err mono">{{ titleErr }}</p>
      <p v-else-if="titleMsg" class="msg ok mono">{{ titleMsg }}</p>

      <div class="title-input-row">
        <input
          id="site-title-input"
          v-model="titleDraft"
          type="text"
          class="input"
          placeholder="MediaBox"
          maxlength="60"
          :disabled="titleSaving"
          @keydown.enter.prevent="saveTitle"
        />
        <button
          type="button"
          class="btn btn-accent"
          :disabled="titleSaving || !isTitleDirty || !titleDraft.trim()"
          @click="saveTitle"
        >
          {{ titleSaving ? 'Saving…' : 'Save title' }}
        </button>
        <button
          v-if="siteTitle !== 'MediaBox'"
          type="button"
          class="btn btn-ghost"
          :disabled="titleSaving"
          title="Revert back to default 'MediaBox'"
          @click="resetTitle"
        >
          Reset default
        </button>
      </div>
    </div>

    <hr class="branding-divider" />

    <!-- Site Logo Section -->
    <div class="branding-section">
      <input ref="fileInput" type="file" accept="image/*" hidden @change="onPicked" />
      <span class="section-title">Site logo & icon</span>
      <p class="branding-hint">
        Upload one square image (around 128×128 works best) to use as the navbar icon and browser favicon.
      </p>

      <p v-if="logoErr" class="msg err mono">{{ logoErr }}</p>
      <p v-else-if="logoMsg" class="msg ok mono">{{ logoMsg }}</p>

      <div class="logo-row">
        <div class="logo-box">
          <img v-if="hasLogo" :src="logoUrl" alt="Site logo" />
          <img v-else src="/logo.svg" alt="Default logo" class="default-mark" />
        </div>

        <div class="logo-actions">
          <button class="btn btn-accent" :disabled="logoBusy" @click="fileInput?.click()">
            {{ logoBusy ? 'Working…' : hasLogo ? 'Change logo' : 'Upload logo' }}
          </button>
          <button v-if="hasLogo" class="btn btn-ghost" :disabled="logoBusy" @click="removeLogo">
            Remove logo
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.branding-card {
  padding: 1.6rem;
  display: flex;
  flex-direction: column;
  gap: 1.2rem;
}

.card-header {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.card-title {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 600;
}

.card-desc {
  margin: 0;
  color: var(--text-dim);
  font-size: 0.85rem;
}

.preview-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 1.2rem;
  background: var(--surface-hover);
  border: 1px solid var(--line);
  border-radius: 9px;
}

.preview-tag {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
  color: var(--text-faint);
}

.preview-brand {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
}

.preview-logo {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  object-fit: cover;
  border: 1px solid var(--line);
}

.preview-logo.is-mark {
  width: auto;
  height: 30px;
  border: none;
  border-radius: 0;
  object-fit: contain;
}

.wordmark {
  font-size: 1.25rem;
}

.wordmark span {
  color: var(--accent);
}

.branding-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.section-head {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.section-title {
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--text);
}

.badge-custom {
  font-size: 0.7rem;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 500;
}

.branding-hint {
  margin: 0;
  color: var(--text-dim, #9a9a9a);
  font-size: 0.84rem;
  line-height: 1.45;
}

.title-input-row {
  display: flex;
  gap: 0.6rem;
  align-items: center;
  flex-wrap: wrap;
}

.title-input-row .input {
  flex: 1;
  min-width: 200px;
}

.branding-divider {
  border: 0;
  border-top: 1px solid var(--line);
  margin: 0.2rem 0;
}

.logo-row {
  display: flex;
  align-items: center;
  gap: 1.2rem;
  flex-wrap: wrap;
}

.logo-box {
  width: 76px;
  height: 76px;
  display: grid;
  place-items: center;
  border: 1px dashed var(--line-strong, #2c2c2e);
  border-radius: 12px;
  overflow: hidden;
  flex-shrink: 0;
  background: var(--surface-hover);
}

.logo-box img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.logo-box .default-mark {
  height: 40px;
  width: auto;
}

.logo-actions {
  display: flex;
  gap: 0.6rem;
  align-items: center;
  flex-wrap: wrap;
}

.msg {
  margin: 0;
  padding: 0.55rem 0.75rem;
  border-radius: 6px;
  font-size: 0.78rem;
}

.msg.err {
  background: var(--err-soft);
  color: var(--err);
}

.msg.ok {
  background: var(--accent-soft);
  color: var(--accent);
}
</style>

