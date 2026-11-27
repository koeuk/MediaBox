<script setup lang="ts">
import { GUEST_QUALITY_OPTIONS, guestQualityLabel } from '~/utils/guestQualities'
/**
 * Downloading without an account.
 *
 * Deliberately not part of the library flow: there is no job to poll and no
 * row to show, because the server streams the file back and keeps nothing.
 * That also means the page has to hold the request open itself — hence the
 * "this can take a while" wording rather than a progress bar it cannot fill.
 */
const config = useRuntimeConfig()

interface GuestLimits {
  qualities: string[]
  default_quality: string
  max_size_mb: number
  rate_limit: number
  rate_window_seconds: number
}

// Served by the API so the allowed qualities live in exactly one place. A
// failure here must not blank the page — the form falls back to the defaults
// below and the server revalidates the choice anyway.
const { data: limits } = await useAsyncData(
  'guest-limits',
  () =>
    $fetch<GuestLimits>('/public/limits', {
      baseURL: config.public.apiBase,
      // a slow or down API must not hold the form hostage
      timeout: 5000,
    }).catch(() => null),
  // client-only: these values are cosmetic labels, and blocking the server
  // render on a reachable API would take the whole page down with it
  { server: false }
)

const { logoUrl, hasLogo, siteTitle, titleParts } = useBranding()

const url = ref('')
const picked = ref('480')
const touched = ref(false)
const busy = ref(false)
const error = ref('')
const readyFile = shallowRef<File | null>(null)
const sharing = ref(false)
const shareError = ref('')
const canShare = computed(() => {
  if (!readyFile.value || typeof navigator === 'undefined') return false
  try {
    return !!navigator.share && !!navigator.canShare?.({ files: [readyFile.value] })
  } catch {
    return false
  }
})

// The guest endpoint streams generic binary data. Native photo apps need the
// actual media type, which we can recover from the server's filename.
function mediaFile(blob: Blob, name: string) {
  const types: Record<string, string> = {
    mp4: 'video/mp4', mov: 'video/quicktime', m4v: 'video/mp4', webm: 'video/webm',
    jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png', gif: 'image/gif', webp: 'image/webp',
    mp3: 'audio/mpeg', m4a: 'audio/mp4',
  }
  const extension = name.split('.').pop()?.toLowerCase() || ''
  return new File([blob], name, { type: types[extension] || blob.type })
}

function downloadFile() {
  if (!readyFile.value) return
  const objectUrl = URL.createObjectURL(readyFile.value)
  const a = document.createElement('a')
  a.href = objectUrl
  a.download = readyFile.value.name
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(objectUrl), 10_000)
}

async function shareFile() {
  if (!readyFile.value || !canShare.value || sharing.value) return
  shareError.value = ''
  sharing.value = true
  try {
    // Called directly from a second tap: fetching first would lose the user
    // activation required to open the phone's native share sheet.
    await navigator.share({ files: [readyFile.value] })
  } catch (e: any) {
    if (e?.name !== 'AbortError') {
      shareError.value = 'Could not open sharing. Use Download file, then share it from your Files app.'
    }
  } finally {
    sharing.value = false
  }
}

// The members' full ladder, shown to guests as well. The ones a guest cannot
// have stay visible but locked: hiding them would leave no hint that signing up
// buys anything, which is the point of showing them.
/** What the server says a guest may have — everything else is locked. */
const allowed = computed(() => limits.value?.qualities || ['720', '480'])

const options = computed(() =>
  GUEST_QUALITY_OPTIONS.map((q) => {
    const open = allowed.value.includes(q.value)
    return {
      value: q.value,
      label: q.label,
      hint: open ? q.hint : 'Sign in',
    }
  })
)

// limits arrive after the first render (client-only fetch), so adopt the
// server's default once it does — unless the visitor already chose something
watch(limits, (value) => {
  if (value && (!touched.value || !value.qualities.includes(picked.value))) {
    picked.value = value.default_quality
  }
}, { immediate: true })

const qualitySummary = computed(() => allowed.value.includes('')
  ? 'Guests can download at the best available quality'
  : `Guests download at up to ${guestQualityLabel(allowed.value[0] || '720')}`)

/**
 * Picking a locked quality is a signup prompt, not a selection: send them to
 * register and leave the dropdown where it was, so coming back to this tab
 * does not show a quality the server would refuse anyway.
 */
const quality = computed({
  get: () => picked.value,
  set: (value: string) => {
    if (!allowed.value.includes(value)) {
      navigateTo('/register')
      return
    }
    picked.value = value
    touched.value = true
  },
})

/** Pull the server's filename out of Content-Disposition, falling back to a
 *  generic one so the save never lands as "download". */
function filenameFrom(header: string | null): string {
  const match = header?.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i)
  return match?.[1] ? decodeURIComponent(match[1]) : 'mediabox-video.mp4'
}

async function submit() {
  if (!url.value.trim() || busy.value || sharing.value) return
  error.value = ''
  busy.value = true
  try {
    const res = await fetch(`${config.public.apiBase}/public/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url.value.trim(), quality: quality.value }),
    })

    if (!res.ok) {
      const detail = await res.json().catch(() => null)
      throw new Error(detail?.detail || `Download failed (${res.status})`)
    }

    // the response *is* the file — hand it to the browser as a blob, since
    // there is no stored URL to link to
    const name = filenameFrom(res.headers.get('content-disposition'))
    const blob = await res.blob()
    readyFile.value = mediaFile(blob, name)
    shareError.value = ''
    downloadFile()
    url.value = ''
  } catch (e: any) {
    error.value = e?.message || 'Could not download that link.'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="wrap">
    <header class="topbar">
      <NuxtLink to="/free" class="topbar-brand" :aria-label="siteTitle">
        <img class="mark" :src="hasLogo ? logoUrl : '/logo.svg'" alt="" />
      </NuxtLink>
    </header>

    <div class="brand reveal">
      <div class="wordmark display">
        {{ titleParts.first }}<span v-if="titleParts.highlight">{{ titleParts.highlight }}</span>
      </div>
      <p class="label">Download · No account needed</p>
    </div>

    <main class="page">
      <section class="panel panel-hover manage reveal" style="animation-delay: 0.08s">
        <h1 class="display hero-title">Quick download</h1>

        <!-- one row, same shape as the members' submit bar; stacks on narrow
             screens where a three-up row would squeeze the URL field -->
        <form class="submit-bar" @submit.prevent="submit">
          <input
            id="guest-url"
            v-model="url"
            class="input submit-input mono"
            type="url"
            required
            placeholder="https:// — paste a supported video link or direct media URL"
          />
          <AppSelect v-model="quality" :options="options" aria-label="Download quality" />
          <button class="btn btn-accent submit-btn" type="submit" :disabled="busy || sharing || !url.trim()">
            {{ busy ? 'Downloading…' : 'Download' }}
          </button>
        </form>

        <p v-if="error" class="submit-error">{{ error }}</p>
        <p v-else-if="busy" class="submit-note">
          Fetching the video — this can take a minute for longer clips. Keep this tab open.
        </p>

        <div v-if="readyFile" class="download-ready">
          <div class="ready-copy" role="status">
            <p class="ready-title">Your file is ready</p>
            <p class="ready-name mono">{{ readyFile.name }}</p>
            <p v-if="canShare" class="note">
              Tap Save / Share, then choose Save Video, Save Image, or a photo app if your phone offers it.
            </p>
            <p v-else class="note">
              Open the downloaded file in Files, then use Share to save it to Photos or Gallery if available.
            </p>
          </div>
          <div class="ready-actions">
            <button v-if="canShare" type="button" class="btn btn-accent" :disabled="sharing || busy" @click="shareFile">
              {{ sharing ? 'Sharing…' : 'Save / Share' }}
            </button>
            <button type="button" class="btn" @click="downloadFile">Download file</button>
          </div>
          <p v-if="shareError" class="submit-error" role="alert">{{ shareError }}</p>
        </div>

        <div class="footer">
          <p class="note mono">
            {{ qualitySummary }}, and
            {{ limits?.rate_limit ?? 5 }} videos per
            {{ Math.round((limits?.rate_window_seconds ?? 600) / 60) }} minutes.
            Nothing is saved on the server. An account adds your own library and conversions.
          </p>

          <!-- buttons rather than inline links: these are the two ways off this
               page, and they were getting lost inside the paragraph -->
          <div class="footer-actions">
            <NuxtLink to="/login" class="btn btn-ghost">Sign in</NuxtLink>
            <NuxtLink to="/register" class="btn btn-accent">Create account</NuxtLink>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.download-ready {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1rem;
  margin-top: 1.2rem;
  padding: 1rem;
  border: 1px solid var(--line);
  border-left: 3px solid var(--accent);
  border-radius: 6px;
  background: var(--bg-raised);
}

.ready-copy { flex: 1; min-width: 0; }
.ready-title { margin: 0 0 0.35rem; font-weight: 600; }
.ready-name { margin: 0 0 0.5rem; font-size: 0.75rem; color: var(--accent); overflow-wrap: anywhere; }
.ready-actions { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.download-ready .submit-error { flex-basis: 100%; margin: 0; }

.wrap {
  position: relative;
  min-height: 100vh;
  padding: 3rem 0 4rem;
}

/* the mark sits in the corner like a site header, leaving the wordmark to
   carry the centred brand block on its own */
.topbar {
  position: absolute;
  top: 1.1rem;
  left: 1.5rem;
}

.topbar-brand {
  display: inline-flex;
}

.mark {
  /* height-driven: the viewBox is taller than it is wide, so a fixed width
     would letterbox the mark */
  width: auto;
  height: 60px;
  display: block;
}

.brand {
  text-align: center;
  margin-bottom: 1.8rem;
}

.wordmark {
  font-size: clamp(2rem, 7vw, 3.2rem);
  letter-spacing: -0.02em;
  line-height: 1;
}

.wordmark span {
  color: var(--accent);
}

.brand .label {
  margin: 0.5rem 0 0;
}

.page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 1.5rem;
}

.manage {
  padding: 1.5rem;
}

.hero-title {
  font-size: clamp(1.6rem, 4vw, 2.4rem);
  margin: 0 0 1.1rem;
}

.submit-bar {
  display: flex;
  gap: 0.6rem;
}

.submit-input {
  flex: 1;
  font-size: 0.85rem;
}

.submit-btn {
  white-space: nowrap;
}

.submit-error {
  margin: 0.6rem 0 0;
  font-size: 0.75rem;
  color: var(--err);
}

.submit-note {
  margin: 0.6rem 0 0;
  font-size: 0.75rem;
  color: var(--ok);
}

.footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.2rem;
  flex-wrap: wrap;
  margin-top: 1.1rem;
}

.note {
  margin: 0;
  max-width: 62ch;
  font-size: 0.7rem;
  line-height: 1.6;
  color: var(--text-dim);
}

.footer-actions {
  display: flex;
  gap: 0.5rem;
  flex: none;
}

/* NuxtLink renders an <a>, which does not inherit the button's centring */
.footer-actions .btn {
  display: inline-flex;
  align-items: center;
  text-decoration: none;
}

@media (max-width: 560px) {
  .submit-bar {
    flex-direction: column;
  }

  .footer-actions {
    width: 100%;
  }

  .footer-actions .btn {
    flex: 1;
    justify-content: center;
  }
}
</style>
