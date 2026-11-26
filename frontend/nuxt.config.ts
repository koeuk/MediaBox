import { realpathSync } from 'node:fs'

export default defineNuxtConfig({
  telemetry: false,
  compatibilityDate: '2025-07-15',
  devtools: { enabled: false },

  vite: {
    server: {
      fs: {
        // Dependencies may be symlinked to an external cache on noexec drives.
        allow: [realpathSync(new URL('./node_modules', import.meta.url))],
      },
    },
  },

  css: ['~/assets/css/main.css'],

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
      link: [
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Archivo:ital,wdth,wght@0,62..125,100..900;1,62..125,100..900&family=IBM+Plex+Mono:wght@400;500;600&display=swap',
        },
      ],
    },
  },
})
