<script setup lang="ts">
/** URL box + quality picker + upload button. Purely presentational. */
const props = defineProps<{ submitting: boolean; uploading: boolean; premium?: boolean }>()
const emit = defineEmits<{ submit: []; upload: [files: File[]]; locked: [quality: string] }>()

const url = defineModel<string>('url', { required: true })
const picked = defineModel<string>('quality', { required: true })

const QUALITY_LADDER = [
  { value: '', label: 'Best', hint: 'auto' },
  { value: '2160', label: '4K', hint: '2160p' },
  { value: '1440', label: '1440p' },
  { value: '1080', label: '1080p' },
  { value: '720', label: '720p' },
  { value: '480', label: '480p' },
]

// computed, not a plain map: `premium` flips the moment an upgrade goes
// through, and a one-shot array would leave "Upgrade" on rungs the account
// has just bought
const qualityOptions = computed(() =>
  QUALITY_LADDER.map((q) => ({
    ...q,
    hint: !props.premium && isPaidQuality(q.value) ? 'Upgrade' : q.hint,
  }))
)

/**
 * Choosing a paid quality on a free account opens the upgrade dialog rather
 * than selecting it, and the picker stays where it was — queuing it would only
 * come back as a 402 from the server.
 */
const quality = computed({
  get: () => picked.value,
  set: (value: string) => {
    if (!props.premium && isPaidQuality(value)) {
      emit('locked', value)
      return
    }
    picked.value = value
  },
})

const fileInput = ref<HTMLInputElement>()

function onFilesPicked(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files || [])
  // reset so picking the same file twice in a row still fires a change event
  input.value = ''
  if (files.length) emit('upload', files)
}
</script>

<template>
  <form class="submit-bar" @submit.prevent="emit('submit')">
    <input
      v-model="url"
      class="input submit-input mono"
      type="text"
      placeholder="https:// — paste direct media URLs or TikTok/Facebook video links (authorized content only)"
      required
    />
    <AppSelect
      v-model="quality"
      :options="qualityOptions"
      aria-label="Max resolution for TikTok/Facebook/YouTube links (direct file URLs are unaffected)"
    />
    <button class="btn btn-accent submit-btn" type="submit" :disabled="submitting">
      {{ submitting ? 'Queuing…' : 'Download' }}
    </button>
    <input
      ref="fileInput"
      type="file"
      accept="video/*,audio/*,image/*"
      multiple
      hidden
      @change="onFilesPicked"
    />
    <button
      type="button"
      class="btn submit-btn"
      :disabled="uploading"
      title="Upload media from your computer to preview or convert (webm → mp4, …)"
      @click="fileInput?.click()"
    >
      {{ uploading ? 'Uploading…' : 'Upload' }}
    </button>
  </form>
</template>

<style scoped>
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

@media (max-width: 560px) {
  .submit-bar {
    flex-direction: column;
  }
}
</style>
