<script setup lang="ts">
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
</script>

<template>
  <div>
    <NuxtPage />
    <BackToTop />
  </div>
</template>
