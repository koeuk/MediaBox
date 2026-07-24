<script setup lang="ts">
const props = defineProps<{ targets: string[] }>()
const emit = defineEmits<{ (e: 'pick', target: string): void }>()

interface Fmt {
  ext: string
  label: string
  desc: string
  group: 'Video' | 'Audio' | 'Image'
}

const FORMATS: Record<string, Fmt> = {
  mp4: { ext: 'mp4', label: 'MP4', desc: 'Universal video', group: 'Video' },
  webm: { ext: 'webm', label: 'WebM', desc: 'Web-optimized video', group: 'Video' },
  gif: { ext: 'gif', label: 'GIF', desc: 'Silent animation', group: 'Video' },
  mp3: { ext: 'mp3', label: 'MP3', desc: 'Audio only', group: 'Audio' },
  m4a: { ext: 'm4a', label: 'M4A', desc: 'AAC audio', group: 'Audio' },
  wav: { ext: 'wav', label: 'WAV', desc: 'Lossless audio', group: 'Audio' },
}

// group targets in a stable order, dropping unknowns
const groups = computed(() => {
  const order: Fmt['group'][] = ['Video', 'Audio', 'Image']
  const byGroup = new Map<string, Fmt[]>()
  for (const t of props.targets) {
    const f = FORMATS[t]
    if (!f) continue
    if (!byGroup.has(f.group)) byGroup.set(f.group, [])
    byGroup.get(f.group)!.push(f)
  }
  return order
    .filter((g) => byGroup.has(g))
    .map((g) => ({ name: g, items: byGroup.get(g)! }))
})

const flat = computed(() => groups.value.flatMap((g) => g.items))

const open = ref(false)
const highlighted = ref(-1)
const root = ref<HTMLElement>()
const triggerEl = ref<HTMLButtonElement>()
const menuEl = ref<HTMLElement>()
const menuStyle = ref<Record<string, string>>({})

function updatePosition() {
  const r = triggerEl.value?.getBoundingClientRect()
  if (!r) return
  const mh = menuEl.value?.offsetHeight ?? 0
  const mw = menuEl.value?.offsetWidth ?? r.width
  const spaceBelow = window.innerHeight - r.bottom
  const openUp = spaceBelow < mh + 16 && r.top > spaceBelow
  // keep the menu inside the viewport horizontally (right-column cards)
  const left = Math.max(8, Math.min(r.left, window.innerWidth - mw - 8))
  menuStyle.value = {
    left: `${left}px`,
    ...(openUp
      ? { bottom: `${window.innerHeight - r.top + 6}px` }
      : { top: `${r.bottom + 6}px` }),
  }
}

function show() {
  open.value = true
  highlighted.value = 0
  // measure once hidden layout exists, then correct for flip/clamp
  nextTick(() => {
    updatePosition()
    nextTick(updatePosition)
  })
  window.addEventListener('scroll', updatePosition, true)
  window.addEventListener('resize', updatePosition)
}

function close() {
  open.value = false
  highlighted.value = -1
  window.removeEventListener('scroll', updatePosition, true)
  window.removeEventListener('resize', updatePosition)
}

function toggle() {
  open.value ? close() : show()
}

function pick(ext: string) {
  emit('pick', ext)
  close()
}

function move(delta: number) {
  const n = flat.value.length
  if (!n) return
  highlighted.value = (highlighted.value + delta + n) % n
}

function onKeydown(e: KeyboardEvent) {
  switch (e.key) {
    case 'ArrowDown':
      e.preventDefault()
      open.value ? move(1) : show()
      break
    case 'ArrowUp':
      e.preventDefault()
      open.value ? move(-1) : show()
      break
    case 'Enter':
    case ' ':
      e.preventDefault()
      if (open.value && flat.value[highlighted.value]) pick(flat.value[highlighted.value]!.ext)
      else show()
      break
    case 'Escape':
      if (open.value) {
        e.preventDefault()
        close()
      }
      break
    case 'Tab':
      close()
      break
  }
}

function onDocPointer(e: PointerEvent) {
  if (!open.value) return
  const t = e.target as Node
  if (root.value?.contains(t) || menuEl.value?.contains(t)) return
  close()
}

onMounted(() => document.addEventListener('pointerdown', onDocPointer))
onUnmounted(() => {
  document.removeEventListener('pointerdown', onDocPointer)
  window.removeEventListener('scroll', updatePosition, true)
  window.removeEventListener('resize', updatePosition)
})
</script>

<template>
  <div ref="root" class="cm" @keydown="onKeydown">
    <button
      ref="triggerEl"
      type="button"
      class="btn cm-trigger"
      :class="{ open }"
      aria-haspopup="menu"
      :aria-expanded="open"
      title="Convert with FFmpeg"
      @click="toggle"
    >
      Convert
      <svg class="cm-chev" width="9" height="9" viewBox="0 0 10 10" fill="none" aria-hidden="true">
        <path d="M2 3.5 5 6.5 8 3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </button>

    <Teleport to="body">
      <Transition name="cm-pop">
        <div v-if="open" ref="menuEl" class="cm-menu" :style="menuStyle" role="menu">
          <div v-for="g in groups" :key="g.name" class="cm-group">
            <div class="cm-glabel mono">{{ g.name }}</div>
            <button
              v-for="f in g.items"
              :key="f.ext"
              type="button"
              class="cm-opt"
              :class="{ hl: flat[highlighted]?.ext === f.ext }"
              role="menuitem"
              @pointerenter="highlighted = flat.findIndex((x) => x.ext === f.ext)"
              @click="pick(f.ext)"
            >
              <span class="cm-ext mono">{{ f.label }}</span>
              <span class="cm-desc">{{ f.desc }}</span>
            </button>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.cm {
  display: inline-flex;
}

.cm-trigger {
  gap: 0.35rem;
  padding: 0.45rem 0.6rem;
  font-size: 0.72rem;
  white-space: nowrap;
}

.cm-chev {
  color: var(--text-faint);
  transition: transform 0.18s ease;
}

.cm-trigger.open {
  border-color: var(--accent);
  color: var(--text);
}

.cm-trigger.open .cm-chev {
  transform: rotate(180deg);
  color: var(--accent);
}

.cm-menu {
  position: fixed;
  z-index: 90;
  min-width: 190px;
  padding: 0.35rem;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 9px;
  box-shadow: var(--shadow);
}

.cm-group + .cm-group {
  margin-top: 0.2rem;
  padding-top: 0.2rem;
  border-top: 1px solid var(--line);
}

.cm-glabel {
  padding: 0.35rem 0.6rem 0.2rem;
  font-size: 0.58rem;
  text-transform: uppercase;
  letter-spacing: 0.13em;
  color: var(--text-faint);
}

.cm-opt {
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
  width: 100%;
  padding: 0.44rem 0.6rem;
  border: none;
  border-radius: 6px;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: background 0.12s;
}

.cm-opt.hl {
  background: var(--surface-hover);
}

.cm-ext {
  flex: 0 0 2.7rem;
  font-size: 0.76rem;
  font-weight: 600;
  color: var(--text);
}

.cm-opt.hl .cm-ext {
  color: var(--accent);
}

.cm-desc {
  font-size: 0.68rem;
  color: var(--text-dim);
  white-space: nowrap;
}

.cm-pop-enter-active,
.cm-pop-leave-active {
  transition: opacity 0.14s ease, transform 0.14s ease;
}

.cm-pop-enter-from,
.cm-pop-leave-to {
  opacity: 0;
  transform: translateY(-4px) scale(0.98);
}
</style>
