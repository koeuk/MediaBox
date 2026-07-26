<script setup lang="ts">
const theme = useCookie<string>('mediabox_theme', {
  default: () => 'dark',
  maxAge: 60 * 60 * 24 * 365,
})

useHead({
  htmlAttrs: { 'data-theme': theme },
})

provide('theme', theme)
</script>

<template>
  <div>
    <NuxtPage />
    <BackToTop />
  </div>
</template>
