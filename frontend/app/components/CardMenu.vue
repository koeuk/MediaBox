<script setup lang="ts">
import type { Download } from '~/types'

/** Kebab menu collapsing a card's actions into one control. */
const props = withDefaults(
  defineProps<{
    download: Download
    /** Offer Hide/Unhide. Off where hiding makes no sense, e.g. cutouts. */
    hideable?: boolean
  }>(),
  { hideable: false }
)
const emit = defineEmits<{ info: []; hide: []; remove: [] }>()

const { fileUrl, mediaToken } = useApi()
const { open, anchor, menu, pos, placed, toggle, close } = usePopMenu()

const saveable = computed(() => props.download.status === 'completed' && !!mediaToken.value)

function pick(fn: () => void) {
  fn()
  close()
}
</script>

<template>
  <div class="menu-wrap">
    <button
      ref="anchor"
      class="btn btn-ghost btn-icon kebab"
      :class="{ on: open }"
      title="More actions"
      aria-label="More actions"
      :aria-expanded="open"
      aria-haspopup="menu"
      @click.stop="toggle"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <circle cx="12" cy="5" r="1.8" />
        <circle cx="12" cy="12" r="1.8" />
        <circle cx="12" cy="19" r="1.8" />
      </svg>
    </button>

    <!-- teleported so the card's overflow:hidden can't clip it -->
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
          <a
            v-if="saveable"
            class="pop-item"
            role="menuitem"
            :href="fileUrl(download.id, 'file')"
            :download="download.filename || true"
            @click="close"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
            </svg>
            Save
          </a>

          <button class="pop-item" role="menuitem" @click="pick(() => emit('info'))">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="9" />
              <path d="M12 16v-4M12 8h.01" />
            </svg>
            Info
          </button>

          <button
            v-if="hideable"
            class="pop-item"
            role="menuitem"
            @click="pick(() => emit('hide'))"
          >
            <svg v-if="download.is_hidden" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8Z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
            <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
              <path d="M1 1l22 22" />
            </svg>
            {{ download.is_hidden ? 'Unhide' : 'Hide' }}
          </button>

          <div class="pop-sep" />

          <button class="pop-item danger" role="menuitem" @click="pick(() => emit('remove'))">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M3 6h18M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2m2 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
              <path d="M10 11v6M14 11v6" />
            </svg>
            Delete
          </button>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.menu-wrap {
  position: relative;
  display: inline-flex;
}

.kebab.on {
  color: var(--text);
  background: var(--surface-hover);
}

.pop-menu {
  position: fixed;
  z-index: 60;
  min-width: 150px;
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
</style>
