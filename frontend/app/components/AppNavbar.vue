<script setup lang="ts">
import type { Ref } from 'vue'

const { user, logout } = useAuth()
const theme = inject<Ref<string>>('theme')!

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
}
</script>

<template>
  <header class="nav">
    <NuxtLink to="/" class="wordmark display">Media<span>Box</span></NuxtLink>

    <div class="nav-right">
      <NuxtLink to="/" class="nav-link">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <rect x="3" y="3" width="7" height="7" rx="1" />
          <rect x="14" y="3" width="7" height="7" rx="1" />
          <rect x="3" y="14" width="7" height="7" rx="1" />
          <rect x="14" y="14" width="7" height="7" rx="1" />
        </svg>
        Media
      </NuxtLink>
      <NuxtLink v-if="user?.is_admin" to="/admin" class="nav-link">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M12 2 4 5v6c0 5 3.4 8.3 8 10 4.6-1.7 8-5 8-10V5l-8-3Z" />
        </svg>
        Admin
      </NuxtLink>
      <NuxtLink v-if="user" to="/profile" class="nav-user mono" title="Edit your profile">
        {{ user.username }}
      </NuxtLink>

      <button class="btn btn-ghost btn-icon" :title="`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`" @click="toggleTheme">
        <svg v-if="theme === 'dark'" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
        <svg v-else width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />
        </svg>
      </button>

      <button class="btn btn-ghost" @click="logout">Logout</button>
    </div>
  </header>
</template>

<style scoped>
.nav {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.9rem 1.5rem;
  background: color-mix(in srgb, var(--bg) 86%, transparent);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--line);
}

.nav-link {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.5rem 0.9rem;
  border: 1px solid transparent;
  border-radius: 7px;
  color: var(--text-dim);
  font-size: 0.82rem;
  font-weight: 500;
  transition: color 0.15s, background 0.15s, border-color 0.15s;
}

.nav-link svg {
  color: var(--text-faint);
  transition: color 0.15s;
}

.nav-link:hover {
  color: var(--text);
  background: var(--surface-hover);
}

.nav-link:hover svg {
  color: var(--accent);
}

/* NuxtLink adds this class when the route matches exactly */
.nav-link.router-link-exact-active {
  color: var(--accent);
  background: var(--accent-soft);
  border-color: color-mix(in srgb, var(--accent) 30%, transparent);
}

.nav-link.router-link-exact-active svg {
  color: var(--accent);
}

.wordmark {
  font-size: 1.25rem;
}

.wordmark span {
  color: var(--accent);
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.nav-user {
  font-size: 0.75rem;
  color: var(--text-dim);
  padding: 0.4rem 0.6rem;
  border-radius: 6px;
  transition: color 0.15s, background 0.15s;
}

.nav-user:hover {
  color: var(--text);
  background: var(--surface-hover);
}

.nav-user.router-link-exact-active {
  color: var(--accent);
  background: var(--accent-soft);
}

@media (max-width: 640px) {
  .nav-link {
    padding: 0.5rem 0.7rem;
  }
}

@media (max-width: 560px) {
  .nav-user {
    display: none;
  }
}
</style>
