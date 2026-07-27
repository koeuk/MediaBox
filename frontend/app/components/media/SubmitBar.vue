<script setup lang="ts">
/** URL box + quality picker + upload button. Purely presentational. */
defineProps<{ submitting: boolean; uploading: boolean }>()
const emit = defineEmits<{ submit: []; upload: [files: File[]] }>()

const url = defineModel<string>('url', { required: true })
const quality = defineModel<string>('quality', { required: true })

const qualityOptions = [
  { value: '', label: 'Best', hint: 'auto' },
  { value: '2160', label: '4K', hint: '2160p' },
  { value: '1440', label: '1440p' },
  { value: '1080', label: '1080p' },
  { value: '720', label: '720p' },
  { value: '480', label: '480p' },
]

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
