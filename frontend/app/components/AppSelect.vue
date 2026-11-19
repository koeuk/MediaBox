<script setup lang="ts">
export interface AppSelectOption {
  value: string
  label: string
  hint?: string
}

const props = defineProps<{
  modelValue: string
  options: AppSelectOption[]
  ariaLabel?: string
}>()

const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()

const open = ref(false)
const highlighted = ref(-1)
const root = ref<HTMLElement>()
const listEl = ref<HTMLElement>()
const triggerEl = ref<HTMLButtonElement>()
// the menu is teleported to <body>, so it needs explicit fixed coordinates
const menuStyle = ref<Record<string, string>>({})

const selected = computed(() => props.options.find((o) => o.value === props.modelValue))

function updatePosition() {
  const r = triggerEl.value?.getBoundingClientRect()
  if (!r) return
  menuStyle.value = {
    top: `${r.bottom + 6}px`,
    left: `${r.left}px`,
    minWidth: `${r.width}px`,
  }
}

function toggle() {
  open.value ? close() : show()
}

function show() {
  open.value = true
  highlighted.value = Math.max(
    0,
    props.options.findIndex((o) => o.value === props.modelValue)
  )
  nextTick(updatePosition)
  window.addEventListener('scroll', updatePosition, true)
  window.addEventListener('resize', updatePosition)
}

function close() {
  open.value = false
  highlighted.value = -1
  window.removeEventListener('scroll', updatePosition, true)
  window.removeEventListener('resize', updatePosition)
}

function pick(option: AppSelectOption) {
  emit('update:modelValue', option.value)
  close()
}

function move(delta: number) {
  if (!open.value) {
    show()
    return
  }
  const n = props.options.length
  highlighted.value = (highlighted.value + delta + n) % n
  nextTick(() => {
    listEl.value
      ?.querySelectorAll('.opt')
      [highlighted.value]?.scrollIntoView({ block: 'nearest' })
  })
}

function onKeydown(e: KeyboardEvent) {
  switch (e.key) {
    case 'ArrowDown':
      e.preventDefault()
      move(1)
      break
    case 'ArrowUp':
      e.preventDefault()
      move(-1)
      break
    case 'Home':
      if (open.value) {
        e.preventDefault()
        highlighted.value = 0
      }
      break
    case 'End':
      if (open.value) {
        e.preventDefault()
        highlighted.value = props.options.length - 1
      }
      break
    case 'Enter':
    case ' ':
      e.preventDefault()
      if (open.value && highlighted.value >= 0) pick(props.options[highlighted.value]!)
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
  const target = e.target as Node
  // the menu lives in <body> now, so it isn't inside root — check both
  if (root.value?.contains(target) || listEl.value?.contains(target)) return
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
  <div ref="root" class="select" @keydown="onKeydown">
    <button
      ref="triggerEl"
      type="button"
      class="trigger mono"
      :class="{ open }"
      role="combobox"
      :aria-expanded="open"
      aria-haspopup="listbox"
      :aria-label="ariaLabel"
      @click="toggle"
    >
      <span class="value">{{ selected?.label ?? '—' }}</span>
      <svg class="chevron" width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
        <path d="M2 3.5 5 6.5 8 3.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </button>

    <Teleport to="body">
      <Transition name="pop">
        <ul v-if="open" ref="listEl" class="menu mono" :style="menuStyle" role="listbox">
          <li
            v-for="(o, i) in options"
            :key="o.value"
            class="opt mono"
            :class="{ hl: i === highlighted, sel: o.value === modelValue }"
            role="option"
            :aria-selected="o.value === modelValue"
            @pointerenter="highlighted = i"
            @click="pick(o)"
          >
            <span class="opt-label">{{ o.label }}</span>
            <span v-if="o.hint" class="opt-hint">{{ o.hint }}</span>
            <svg v-if="o.value === modelValue" class="check" width="11" height="11" viewBox="0 0 11 11" fill="none" aria-hidden="true">
              <path d="M2 5.8 4.4 8.2 9 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </li>
        </ul>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.select {
  position: relative;
  flex: 0 0 auto;
}

.trigger {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  padding: 0.7rem 0.85rem;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  background: var(--bg-raised);
  color: var(--text);
  font-size: 0.78rem;
  cursor: pointer;
  white-space: nowrap;
  transition: border-color 0.15s, box-shadow 0.15s, background 0.15s;
}

.trigger:hover {
  background: var(--surface-hover);
}

.trigger:focus-visible {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

.trigger.open {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

.chevron {
  color: var(--text-faint);
  transition: transform 0.18s ease;
}

.trigger.open .chevron {
  transform: rotate(180deg);
  color: var(--accent);
}

/* teleported to <body>; top/left/min-width come from inline menuStyle */
.menu {
  position: fixed;
  z-index: 90;
  margin: 0;
  padding: 0.3rem;
  list-style: none;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: var(--shadow);
}

.opt {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.48rem 0.65rem;
  border-radius: 5px;
  font-size: 0.74rem;
  color: var(--text-dim);
  cursor: pointer;
  white-space: nowrap;
}

.opt.hl {
  background: var(--surface-hover);
  color: var(--text);
}

.opt.sel {
  color: var(--accent);
  font-weight: 600;
}

.opt-label {
  flex: 1;
}

.opt-hint {
  font-size: 0.62rem;
  color: var(--text-faint);
  letter-spacing: 0.05em;
}

.check {
  color: var(--accent);
}

.pop-enter-active,
.pop-leave-active {
  transition: opacity 0.14s ease, transform 0.14s ease;
}

.pop-enter-from,
.pop-leave-to {
  opacity: 0;
  transform: translateY(-4px) scale(0.98);
}
</style>
