<script setup lang="ts">
import type { Download } from '~/types'

const theme = useCookie<string>('mediabox_theme', {
  default: () => 'dark',
  maxAge: 60 * 60 * 24 * 365,
})

// the profile picture doubles as the tab icon; falls back to the default when
// no photo is set, so the tab never goes blank
const { src: avatarSrc } = useAvatar()

useHead(() => ({
  htmlAttrs: { 'data-theme': theme.value },
  link: avatarSrc.value ? [{ rel: 'icon', href: avatarSrc.value }] : [],
}))

provide('theme', theme)

// The preview dialogs sit beside <NuxtPage>, not inside it, so a route change
// leaves the player mounted and the mini-player keeps playing.
const { target: previewTarget, playlist, close: closePreview } = usePlayer()

// stills get a lightbox, playable media gets the player — they want opposite
// affordances, so each is its own dialog and only one is ever mounted
const isStill = (d: Download | null) => !!d && mediaKind(d.content_type) === 'image'
const previewImage = computed(() => (isStill(previewTarget.value) ? previewTarget.value : null))
const previewMedia = computed(() => (isStill(previewTarget.value) ? null : previewTarget.value))
</script>

<template>
  <div>
    <NuxtPage />

    <MediaPreview
      :download="previewMedia"
      :downloads="playlist"
      @select="(d) => (previewTarget = d)"
      @close="closePreview"
    />

    <ImagePreview
      :download="previewImage"
      :images="playlist"
      @select="(d) => (previewTarget = d)"
      @close="closePreview"
    />

    <BackToTop />
  </div>
</template>
