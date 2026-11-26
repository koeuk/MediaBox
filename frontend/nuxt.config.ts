import { realpathSync } from 'node:fs'

export default defineNuxtConfig({
  telemetry: false,
  compatibilityDate: '2025-07-15',
  devtools: { enabled: false },

  experimental: {
    defaults: {
      nuxtLink: {
        // Prepare the destination on hover/focus without fetching every visible page.
        prefetchOn: { visibility: false, interaction: true },
      },
    },
  },

  vite: {
    server: {
      fs: {
        // Dependencies may be symlinked to an external cache on noexec drives.
        allow: [realpathSync(new URL('./node_modules', import.meta.url))],
      },
    },
  },

  css: ['~/assets/css/fonts.css', '~/assets/css/main.css'],

  runtimeConfig: {
    public: {
      // Default; override in .env with NUXT_PUBLIC_API_BASE
      // (e.g. http://localhost:8001/api locally, or "/api" behind nginx)
      apiBase: 'http://localhost:8000/api',
      cookieSecure: false,
    },
  },

  app: {
    head: {
      title: 'MediaBox',
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'description', content: 'Download, organize, and manage your media.' },
      ],
    },
  },
})
