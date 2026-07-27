import type { Category } from '~/types'

/**
 * Shared category list. The tag dropdown on every card, the filter carousel
 * and the manage page all read the same `useState` entry, so a rename or a
 * colour change shows up everywhere without a refetch.
 */
export function useCategories() {
  const { request } = useApi()

  const categories = useState<Category[]>('categories', () => [])
  const loaded = useState<boolean>('categories-loaded', () => false)
  const pending = useState<boolean>('categories-pending', () => false)

  async function fetchCategories(force = false) {
    if (pending.value) return
    if (loaded.value && !force) return
    pending.value = true
    try {
      categories.value = await request<Category[]>('/categories')
      loaded.value = true
    } finally {
      pending.value = false
    }
  }

  async function createCategory(name: string, color: string) {
    const created = await request<Category>('/categories', {
      method: 'POST',
      body: { name, color },
    })
    categories.value = [...categories.value, created]
    return created
  }

  async function updateCategory(
    id: number,
    patch: { name?: string; color?: string; position?: number }
  ) {
    const updated = await request<Category>(`/categories/${id}`, {
      method: 'PATCH',
      body: patch,
    })
    categories.value = categories.value.map((c) => (c.id === id ? updated : c))
    return updated
  }

  async function deleteCategory(id: number) {
    await request(`/categories/${id}`, { method: 'DELETE' })
    categories.value = categories.value.filter((c) => c.id !== id)
  }

  async function reorderCategories(ids: number[]) {
    // optimistic — the list is already in the new order on screen
    categories.value = await request<Category[]>('/categories/reorder', {
      method: 'PUT',
      body: ids,
    })
  }

  const names = computed(() => categories.value.map((c) => c.name))

  const colorByName = computed(() =>
    Object.fromEntries(categories.value.map((c) => [c.name, c.color]))
  )

  /** Tag colour, falling back to a neutral tone for names with no category row
   *  (a download tagged before its category was deleted, say). */
  function colorOf(name: string | null | undefined) {
    return (name && colorByName.value[name]) || null
  }

  /** Inline style for a tinted pill/tab, mirroring the old hardcoded CSS. */
  function tint(name: string | null | undefined) {
    const c = colorOf(name)
    if (!c) return {}
    return {
      // 8-digit hex: the last pair is alpha
      borderColor: `${c}55`,
      color: c,
      background: `${c}1a`,
    }
  }

  /** Black or white text for a solid swatch, by perceived luminance. */
  function inkOn(hex: string) {
    const h = hex.replace('#', '')
    const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255)
    // sRGB relative luminance (WCAG)
    const lin = (v: number) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)
    const L = 0.2126 * lin(r!) + 0.7152 * lin(g!) + 0.0722 * lin(b!)
    return L > 0.45 ? '#000' : '#fff'
  }

  /** Inline style for a *selected* tab — solid fill, readable text. */
  function solid(name: string | null | undefined) {
    const c = colorOf(name)
    if (!c) return {}
    return { background: c, color: inkOn(c), borderColor: c }
  }

  return {
    categories,
    names,
    loaded,
    pending,
    fetchCategories,
    createCategory,
    updateCategory,
    deleteCategory,
    reorderCategories,
    colorOf,
    tint,
    solid,
    inkOn,
  }
}
