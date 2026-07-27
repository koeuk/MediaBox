<script setup lang="ts">
import type { Ref } from 'vue'

const { user, logout } = useAuth()
const theme = inject<Ref<string>>('theme')!
const showLogoutConfirm = ref(false)
const { open, anchor, menu, pos, placed, toggle, close } = usePopMenu()

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
}

function handleLogoutClick() {
  close()
  showLogoutConfirm.value = true
}

function confirmLogout() {
  showLogoutConfirm.value = false
  logout()
}
</script>

<template>
  <header class="nav">
    <NuxtLink to="/" class="wordmark display">Media<span>Box</span></NuxtLink>

    <div class="nav-right">
      <NuxtLink to="/remove-bg" class="nav-link">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <!-- a photo frame with the backdrop cut away, subject left standing -->
          <path d="M3 3h5M16 3h5v5M21 16v5h-5M8 21H3v-5" stroke-dasharray="0" />
          <circle cx="12" cy="10" r="2.6" />
          <path d="M7.5 17.5a4.5 4.5 0 0 1 9 0" />
        </svg>
        Remove BG
      </NuxtLink>
      <NuxtLink to="/" class="nav-link">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <rect x="3" y="3" width="7" height="7" rx="1" />
          <rect x="14" y="3" width="7" height="7" rx="1" />
          <rect x="3" y="14" width="7" height="7" rx="1" />
          <rect x="14" y="14" width="7" height="7" rx="1" />
        </svg>
        Media
      </NuxtLink>
      <NuxtLink to="/categories" class="nav-link">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M12 2H2v10l9.29 9.29a1 1 0 0 0 1.41 0l7.29-7.29a1 1 0 0 0 0-1.41L12 2Z" />
          <circle cx="7" cy="7" r="1.5" fill="currentColor" stroke="none" />
        </svg>
        Categories
      </NuxtLink>
      <NuxtLink v-if="user?.is_admin" to="/admin" class="nav-link">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M12 2 4 5v6c0 5 3.4 8.3 8 10 4.6-1.7 8-5 8-10V5l-8-3Z" />
        </svg>
        Admin
      </NuxtLink>
      <div v-if="user" class="menu-wrap">
        <button
          ref="anchor"
          class="nav-link settings-btn"
          :class="{ on: open }"
          title="Settings"
          :aria-expanded="open"
          aria-haspopup="menu"
          @click.stop="toggle"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1.08-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
          </svg>
          Settings
        </button>

        <Teleport to="body">
          <Transition name="pop">
            <div
              v-if="open"
              ref="menu"
              class="pop-menu panel"
              role="menu"
              :style="{ top: `${pos.top}px`, left: `${pos.left}px`, visibility: placed ? 'visible' : 'hidden' }"
              @click.stop
            >
              <NuxtLink to="/profile" class="pop-item" role="menuitem" @click="close">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="8" r="3.5" />
                  <path d="M5 20a7 7 0 0 1 14 0" />
                </svg>
                {{ user.username }}
              </NuxtLink>

              <NuxtLink to="/hidden" class="pop-item" role="menuitem" @click="close">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                  <path d="M1 1l22 22" />
                </svg>
                Hidden
              </NuxtLink>

              <div class="pop-sep" />

              <button class="pop-item danger" role="menuitem" @click="handleLogoutClick">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" />
                </svg>
                Logout
              </button>
            </div>
          </Transition>
        </Teleport>
      </div>

      <button class="btn btn-ghost btn-icon" :title="`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`" @click="toggleTheme">
        <svg v-if="theme === 'dark'" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
        <svg v-else width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />
        </svg>
      </button>
    </div>

    <ConfirmDialog
      :open="showLogoutConfirm"
      title="Confirm Logout"
      message="Are you sure you want to log out?"
      confirm-label="Logout"
      danger
      @confirm="confirmLogout"
      @cancel="showLogoutConfirm = false"
    />
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

.menu-wrap {
  position: relative;
  display: inline-flex;
}

/* a <button> needs the font reset that NuxtLink's .nav-link gets for free */
.settings-btn {
  font-family: inherit;
  background: transparent;
  cursor: pointer;
}

.settings-btn.on {
  color: var(--text);
  background: var(--surface-hover);
}

.settings-btn.on svg {
  color: var(--accent);
}

.pop-menu {
  position: fixed;
  z-index: 60;
  min-width: 160px;
  padding: 0.3rem;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
}

.pop-item {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  width: 100%;
  padding: 0.5rem 0.6rem;
  border: none;
  border-radius: 5px;
  background: transparent;
  color: var(--text);
  font: 500 0.78rem 'Archivo', sans-serif;
  text-align: left;
  cursor: pointer;
  transition: background 0.12s, color 0.12s;
}

.pop-item svg {
  color: var(--text-faint);
  flex: none;
}

.pop-item:hover {
  background: var(--surface-hover);
}

.pop-item:hover svg {
  color: var(--accent);
}

.pop-item.danger:hover {
  color: var(--err);
}

.pop-item.danger:hover svg {
  color: var(--err);
}

.pop-sep {
  height: 1px;
  margin: 0.25rem 0.2rem;
  background: var(--line);
}

.pop-enter-active,
.pop-leave-active {
  transition: opacity 0.12s ease, transform 0.12s ease;
}

.pop-enter-from,
.pop-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

@media (max-width: 640px) {
  .nav-link {
    padding: 0.5rem 0.7rem;
  }
}
</style>
