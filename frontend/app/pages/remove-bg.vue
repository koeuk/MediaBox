<script setup lang="ts">
import type { CutoutQuality, Download } from '~/types'

definePageMeta({ middleware: 'auth' })

const { fileUrl, refreshMediaToken } = useApi()
const { user, fetchUser } = useAuth()

const {
  downloads,
  loaded,
  uploading,
  error,
  note,
  refresh,
  upload,
  toggleFavorite,
  retry,
  cancel,
  convert,
  removeBackground,
  remove,
  find,
  startLive,
} = useDownloads('cutout')

const qualityOptions = [
  { value: 'fast', label: 'Fast', hint: 'seconds' },
  { value: 'good', label: 'Good', hint: 'default' },
  { value: 'best', label: 'Best', hint: 'soft edges' },
]
// AppSelect emits a plain string, so the tier is narrowed where it is used
const quality = ref('good')

/** Originals uploaded here, which a cutout can be made from. */
const sources = computed(() =>
  downloads.value.filter(
    (d) =>
      d.status === 'completed' &&
      (d.content_type || '').startsWith('image/') &&
      d.job_kind === 'cutout_src'
  )
)

const cutouts = computed(() => downloads.value.filter((d) => d.job_kind === 'cutout'))

const selectedId = ref<number | null>(null)
const selected = computed(() => (selectedId.value === null ? null : find(selectedId.value)))

/** The cutout made from the current selection, looked up live so its progress
 *  and status follow the WebSocket feed. */
const resultId = ref<number | null>(null)
const result = computed(() => (resultId.value === null ? null : find(resultId.value)))
const resultReady = computed(() => result.value?.status === 'completed')

/** 0 = all original, 100 = all cutout. */
const compare = ref(100)

/** Thumbnails are already the right size for the stage and much lighter than
 *  the full file; the cutout's is a PNG, so its transparency survives. */
function preview(d: Download) {
  return fileUrl(d.id, d.has_thumbnail ? 'thumbnail' : 'file')
}

function select(id: number) {
  selectedId.value = id
  resultId.value = null
  compare.value = 100
}

// an image deleted elsewhere shouldn't leave the button armed on a dead id
watch(sources, (list) => {
  if (selectedId.value !== null && !list.some((d) => d.id === selectedId.value)) {
    selectedId.value = null
    resultId.value = null
  }
})

// slide the wipe open once the cutout lands, so the result is what you see
watch(resultReady, (ready) => {
  if (ready) compare.value = 100
})

const busy = ref(false)

async function run() {
  if (!selectedId.value || busy.value) return
  busy.value = true
  try {
    const created = await removeBackground(selectedId.value, quality.value as CutoutQuality)
    if (created) {
      resultId.value = created.id
      compare.value = 100
      note.value = 'Working on it — drag the slider to compare when it lands.'
    }
  } finally {
    busy.value = false
  }
}

const fileInput = ref<HTMLInputElement>()
const dragging = ref(false)

/** Upload straight into a cutout: the original lands in the box too. */
async function accept(files: File[]) {
  if (!files.length) return
  const images = files.filter((f) => f.type.startsWith('image/'))
  if (!images.length) {
    error.value = 'Drop an image — PNG, JPEG or WebP.'
    return
  }

  const created = await upload(images)
  const image = created.find((d) => (d.content_type || '').startsWith('image/'))
  if (!image) return
  select(image.id)
  await run()
}

async function onFilesPicked(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files || [])
  // reset so picking the same file twice in a row still fires a change event
  input.value = ''
  await accept(files)
}

async function onDrop(e: DragEvent) {
  dragging.value = false
  await accept(Array.from(e.dataTransfer?.files || []))
}

const previewTarget = ref<Download | null>(null)
const deleteTarget = ref<Download | null>(null)
const infoTarget = ref<Download | null>(null)

async function confirmRemove() {
  const target = deleteTarget.value
  if (!target) return
  deleteTarget.value = null
  await remove(target.id)
}

onMounted(async () => {
  if (!user.value) await fetchUser()
  await Promise.all([refresh(), refreshMediaToken()])
  startLive()
})
</script>

<template>
  <div>
    <AppNavbar />

    <main class="page">
      <section class="manage panel panel-hover reveal">
        <h1 class="display hero-title">Remove background</h1>
        <p class="lead">
          Cuts the subject out of an image and saves a transparent PNG. The original is kept.
        </p>

        <input
          ref="fileInput"
          type="file"
          accept="image/*"
          multiple
          hidden
          @change="onFilesPicked"
        />

        <div class="layout">
          <!-- Drop zone doubles as the click target; dragover must be prevented
               or the browser navigates to the dropped file instead. -->
          <div class="stage-col">
            <div
              class="dropzone"
              :class="{ on: dragging, busy: uploading, filled: !!selected }"
              role="button"
              tabindex="0"
              :aria-label="selected ? 'Replace image' : 'Choose an image'"
              @click="fileInput?.click()"
              @keydown.enter.prevent="fileInput?.click()"
              @keydown.space.prevent="fileInput?.click()"
              @dragover.prevent="dragging = true"
              @dragenter.prevent="dragging = true"
              @dragleave="dragging = false"
              @drop.prevent="onDrop"
            >
              <template v-if="selected">
                <img class="layer" :src="preview(selected)" :alt="selected.title || 'original'" />

                <!-- the cutout wipes across the original from the left -->
                <div
                  v-if="resultReady && result"
                  class="layer cut alpha-grid"
                  :style="{ clipPath: `inset(0 ${100 - compare}% 0 0)` }"
                >
                  <img :src="preview(result)" alt="cutout" />
                </div>
                <div
                  v-if="resultReady"
                  class="divider"
                  :style="{ left: `${compare}%` }"
                  aria-hidden="true"
                />

                <div v-if="result && !resultReady" class="working mono">
                  {{ result.status === 'failed' ? result.error : `Removing… ${result.progress}%` }}
                </div>

                <span class="replace mono">Click or drop to replace</span>
              </template>

              <template v-else>
                <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                  <circle cx="8.5" cy="8.5" r="1.6" />
                  <path d="m21 15-5-5L5 21" />
                </svg>
                <p class="dz-title">
                  {{ uploading ? 'Uploading…' : 'Drop an image here, or click to choose' }}
                </p>
                <p class="dz-sub mono">PNG · JPEG · WebP — the cutout starts automatically</p>
              </template>
            </div>

            <div v-if="resultReady" class="wipe">
              <span class="wipe-end mono">Original</span>
              <input
                v-model.number="compare"
                class="range"
                type="range"
                min="0"
                max="100"
                step="1"
                aria-label="Compare original with cutout"
              />
              <span class="wipe-end mono">Cutout</span>
            </div>
          </div>

          <div class="controls">
            <div class="row">
              <div class="field">
                <label class="label" for="cutout-quality">Quality</label>
                <AppSelect
                  id="cutout-quality"
                  v-model="quality"
                  :options="qualityOptions"
                  aria-label="Cutout quality — higher tiers use a larger model and take longer"
                />
              </div>

              <button
                class="btn btn-accent run-btn"
                type="button"
                :disabled="!selectedId || busy || uploading"
                @click="run"
              >
                {{ busy ? 'Starting…' : 'Remove background' }}
              </button>

              <p v-if="selected" class="chosen mono">
                {{ selected.title || selected.filename }}
              </p>
              <p v-else class="chosen mono dim">or pick one of your images below</p>
            </div>

            <p v-if="error" class="submit-error mono">{{ error }}</p>
            <p v-else-if="note" class="submit-note mono">{{ note }}</p>
            <p class="hint mono">
              First run at a quality downloads its model (4 MB–180 MB) and is slower than the rest.
            </p>
          </div>
        </div>
      </section>

      <section v-if="sources.length" class="picker reveal" style="animation-delay: 0.05s">
        <h2 class="label section-label">Your images</h2>
        <div class="thumbs">
          <button
            v-for="img in sources"
            :key="img.id"
            type="button"
            class="thumb"
            :class="{ on: selectedId === img.id }"
            :title="img.title || img.filename || ''"
            @click="select(img.id)"
          >
            <img
              v-if="img.has_thumbnail"
              :src="fileUrl(img.id, 'thumbnail')"
              :alt="img.title || img.filename || 'image'"
              loading="lazy"
            />
            <span v-else class="thumb-fallback mono">{{ (img.filename || '?').slice(0, 2) }}</span>
          </button>
        </div>
      </section>

      <section v-else-if="loaded" class="empty reveal">
        <p class="display empty-title">No images yet</p>
        <p class="empty-hint">Upload one above to make your first cutout.</p>
      </section>

      <section v-if="cutouts.length" class="results reveal" style="animation-delay: 0.1s">
        <h2 class="label section-label">Cutouts</h2>
        <div class="gallery">
          <CutoutCard
            v-for="d in cutouts"
            :key="d.id"
            :download="d"
            @favorite="toggleFavorite"
            @retry="retry"
            @remove="deleteTarget = find($event)"
            @preview="previewTarget = find($event)"
            @info="infoTarget = find($event)"
            @cancel="cancel"
          />
        </div>
      </section>
    </main>

    <!-- everything on this page is a still, so the lightbox is the only dialog -->
    <ImagePreview
      :download="previewTarget"
      :images="cutouts"
      @select="(d) => (previewTarget = d)"
      @close="previewTarget = null"
    />

    <InfoDialog :download="infoTarget" @close="infoTarget = null" />

    <ConfirmDialog
      :open="!!deleteTarget"
      title="Delete cutout?"
      :message="`“${deleteTarget?.title || deleteTarget?.filename}” and its files will be permanently removed.`"
      confirm-label="Delete"
      danger
      @confirm="confirmRemove"
      @cancel="deleteTarget = null"
    />
  </div>
</template>

<style scoped>
.page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 2.2rem 1.5rem 4rem;
}

.manage {
  padding: 1.5rem;
  margin-bottom: 1.6rem;
}

.hero-title {
  font-size: clamp(1.6rem, 4vw, 2.4rem);
  margin: 0 0 0.5rem;
}

.lead {
  margin: 0 0 1.1rem;
  font-size: 0.88rem;
  color: var(--text-dim);
}

/* Square drop zone on the left, the controls it feeds on the right. */
.layout {
  display: grid;
  grid-template-columns: var(--dz) minmax(0, 1fr);
  gap: 1.2rem;
  align-items: start;
  --dz: 260px;
}

.stage-col {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.dropzone {
  position: relative;
  /* width is fixed by the column, so this keeps it square */
  aspect-ratio: 1 / 1;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 0.35rem;
  padding: 1.2rem 1rem;
  border: 1.5px dashed var(--line-strong);
  border-radius: 10px;
  background-color: var(--bg-raised);
  color: var(--text-dim);
  cursor: pointer;
  text-align: center;
  overflow: hidden;
  transition: border-color 0.15s, background-color 0.15s, color 0.15s;
}

/* once an image is in, the frame reads as a picture rather than a target */
.dropzone.filled {
  border-style: solid;
  border-color: var(--line);
  padding: 0;
}

.layer {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.layer.cut {
  /* the checkerboard rides with the cutout so cleared areas read as empty */
  background-color: var(--bg-raised);
}

.layer.cut img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.divider {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  margin-left: -1px;
  background: var(--accent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--accent) 35%, transparent);
  pointer-events: none;
}

.working {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 0.45rem 0.6rem;
  font-size: 0.68rem;
  color: var(--accent);
  background: color-mix(in srgb, var(--bg) 78%, transparent);
}

.replace {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  padding: 0.4rem;
  font-size: 0.62rem;
  color: var(--text);
  background: color-mix(in srgb, var(--bg) 72%, transparent);
  opacity: 0;
  transition: opacity 0.15s;
}

.dropzone.filled:hover .replace,
.dropzone.filled:focus-visible .replace {
  opacity: 1;
}

.wipe {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.wipe-end {
  font-size: 0.6rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-faint);
  white-space: nowrap;
}

.range {
  flex: 1;
  min-width: 0;
  accent-color: var(--accent);
  cursor: ew-resize;
}

.dropzone:hover,
.dropzone:focus-visible {
  border-color: var(--accent);
  color: var(--text);
  outline: none;
}

.dropzone.on {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--accent);
}

.dropzone.busy {
  cursor: progress;
  opacity: 0.7;
}

.dropzone svg {
  color: var(--text-faint);
}

.dropzone:hover svg,
.dropzone.on svg {
  color: var(--accent);
}

.dz-title {
  margin: 0.3rem 0 0;
  font-size: 0.9rem;
  font-weight: 500;
}

.dz-sub {
  margin: 0;
  font-size: 0.68rem;
  color: var(--text-faint);
}

.controls {
  /* matches the square so the two sides finish level */
  min-height: var(--dz);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

/* quality, action and the chosen filename sit on one line */
.row {
  display: flex;
  align-items: flex-end;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.run-btn {
  white-space: nowrap;
}

.chosen {
  /* sits on the row's baseline next to the button */
  margin: 0 0 0.7rem;
  font-size: 0.72rem;
  color: var(--accent);
  /* a long filename must not stretch the row */
  flex: 1 1 0;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chosen.dim {
  color: var(--text-faint);
}

.submit-error {
  margin: 0.2rem 0 0;
  font-size: 0.75rem;
  color: var(--err);
}

.submit-note {
  margin: 0.2rem 0 0;
  font-size: 0.75rem;
  color: var(--ok);
}

.hint {
  margin: auto 0 0;
  font-size: 0.66rem;
  line-height: 1.5;
  color: var(--text-faint);
}

.section-label {
  display: block;
  margin: 0 0 0.7rem;
}

.picker {
  margin-bottom: 1.8rem;
}

.thumbs {
  display: flex;
  gap: 0.6rem;
  overflow-x: auto;
  padding-bottom: 0.4rem;
  scrollbar-width: thin;
}

.thumb {
  flex: none;
  width: 92px;
  height: 92px;
  padding: 0;
  border: 2px solid var(--line);
  border-radius: 8px;
  background: var(--bg-raised);
  cursor: pointer;
  overflow: hidden;
  display: grid;
  place-items: center;
  transition: border-color 0.15s, transform 0.12s;
}

.thumb:hover {
  border-color: var(--line-strong);
}

.thumb.on {
  border-color: var(--accent);
  transform: translateY(-2px);
}

.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.thumb-fallback {
  font-size: 0.8rem;
  color: var(--text-faint);
  text-transform: uppercase;
}

/* Masonry columns, because each tile is as tall as its own image — a grid
   would pad every row out to its tallest tile. */
/* Four across at full width, folding down to fewer as the window narrows.
   Tiles stretch to the row's height (the default), so the tallest image in a
   row sets the height and the smaller ones fill it rather than leaving gaps. */
.gallery {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 1rem;
}

.empty {
  text-align: center;
  padding: 3.5rem 1rem;
  border: 1px dashed var(--line-strong);
  border-radius: 10px;
  margin-bottom: 1.8rem;
}

.empty-title {
  font-size: 1.1rem;
  color: var(--text-dim);
  margin: 0 0 0.5rem;
}

.empty-hint {
  margin: 0;
  font-size: 0.85rem;
  color: var(--text-faint);
}

@media (max-width: 780px) {
  .layout {
    grid-template-columns: 1fr;
  }

  .dropzone {
    /* a full-width square would be enormous on a phone */
    aspect-ratio: auto;
    min-height: 170px;
  }

  .controls {
    min-height: 0;
  }

  .hint {
    margin-top: 0.3rem;
  }
}

@media (max-width: 560px) {
  .manage {
    padding: 1.1rem;
  }
}
</style>
