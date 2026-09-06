<script setup lang="ts">
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

const url = ref('')
const picked = ref('480')
const touched = ref(false)
const busy = ref(false)
const error = ref('')

// The members' full ladder, shown to guests as well. The ones a guest cannot
// have stay visible but locked: hiding them would leave no hint that signing up
// buys anything, which is the point of showing them.
const QUALITY_LADDER = [
  { value: '', label: 'Best', hint: 'auto' },
  { value: '2160', label: '4K', hint: '2160p' },
  { value: '1440', label: '1440p' },
  { value: '1080', label: '1080p' },
  { value: '720', label: '720p' },
  { value: '480', label: '480p' },
]

/** What the server says a guest may have — everything else is locked. */
const allowed = computed(() => limits.value?.qualities || ['720', '480'])

const options = computed(() =>
  QUALITY_LADDER.map((q) => {
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
  if (value?.default_quality && !touched.value) picked.value = value.default_quality
})

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
  if (!url.value.trim() || busy.value) return
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
    const objectUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = objectUrl
    a.download = name
    document.body.appendChild(a)
    a.click()
    a.remove()
    // revoke late: Safari needs the URL alive past the click
    setTimeout(() => URL.revokeObjectURL(objectUrl), 10_000)
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
      <NuxtLink to="/free" class="topbar-brand" aria-label="MediaBox">
        <img class="mark" src="/logo.svg" alt="" />
      </NuxtLink>
    </header>

    <div class="brand reveal">
      <div class="wordmark display">Media<span>Box</span></div>
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
            placeholder="https:// — paste a TikTok/Facebook link or a direct media URL"
          />
          <AppSelect v-model="quality" :options="options" aria-label="Download quality" />
          <button class="btn btn-accent submit-btn" type="submit" :disabled="busy || !url.trim()">
            {{ busy ? 'Downloading…' : 'Download' }}
          </button>
        </form>

        <p v-if="error" class="submit-error">{{ error }}</p>
        <p v-else-if="busy" class="submit-note">
          Fetching the video — this can take a minute for longer clips. Keep this tab open.
        </p>

        <div class="footer">
          <p class="note mono">
            Guests download at up to {{ (limits?.qualities || ['720'])[0] }}p, and
            {{ limits?.rate_limit ?? 5 }} videos per
            {{ Math.round((limits?.rate_window_seconds ?? 600) / 60) }} minutes.
            Nothing is saved on the server. An account adds your own library,
            higher quality and conversions.
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
