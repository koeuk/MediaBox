/**
 * Anchored dropdown that escapes its container's `overflow: hidden`.
 *
 * The menu is meant to be teleported to <body> and positioned with fixed
 * coordinates, which is what lets a card with clipped overflow still show a
 * menu that spills outside it. Coordinates are viewport-relative — never add
 * scrollY/scrollX to them.
 */
export function usePopMenu() {
  const open = ref(false)
  const anchor = ref<HTMLElement>()
  const menu = ref<HTMLElement>()
  const pos = ref({ top: 0, left: 0 })
  // hides the menu for the one frame between mount and measurement
  const placed = ref(false)

  function place() {
    const a = anchor.value
    const m = menu.value
    if (!a || !m) return

    const rect = a.getBoundingClientRect()
    const { offsetHeight: h, offsetWidth: w } = m
    const gap = 4
    const pad = 8

    // flip above the button when there isn't room below
    let top = rect.bottom + gap
    if (top + h > window.innerHeight - pad) {
      top = Math.max(pad, rect.top - gap - h)
    }

    // right-align to the button, then keep it inside the viewport
    let left = rect.right - w
    if (left + w > window.innerWidth - pad) left = window.innerWidth - pad - w
    if (left < pad) left = pad

    pos.value = { top, left }
    placed.value = true
  }

  async function toggle() {
    if (open.value) {
      open.value = false
      return
    }
    placed.value = false
    open.value = true
    await nextTick()
    place()
  }

  function close() {
    open.value = false
  }

  // the menu is teleported, so it needs its own containment check
  function onDocClick(e: MouseEvent) {
    if (!open.value) return
    const target = e.target as Node
    if (anchor.value?.contains(target) || menu.value?.contains(target)) return
    open.value = false
  }

  // a fixed menu would detach from its button on scroll
  function onScroll() {
    open.value = false
  }

  onMounted(() => {
    document.addEventListener('click', onDocClick, true)
    window.addEventListener('scroll', onScroll, true)
    window.addEventListener('resize', onScroll)
  })
  onUnmounted(() => {
    document.removeEventListener('click', onDocClick, true)
    window.removeEventListener('scroll', onScroll, true)
    window.removeEventListener('resize', onScroll)
  })

  return { open, anchor, menu, pos, placed, toggle, close, place }
}
