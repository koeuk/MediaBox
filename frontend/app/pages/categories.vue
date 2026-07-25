<script setup lang="ts">
import type { Category } from '~/composables/useCategories'

definePageMeta({ middleware: 'auth' })

const {
  categories,
  fetchCategories,
  createCategory,
  updateCategory,
  deleteCategory,
  reorderCategories,
} = useCategories()

const PRESETS = [
  '#6c8cff', '#3dca72', '#f5a623', '#e879f9', '#22d3ee',
  '#ef4444', '#eab308', '#f97316', '#ec4899', '#a78bfa',
]

const loading = ref(true)
const error = ref('')
const notice = ref('')

// create form
const newName = ref('')
const newColor = ref(PRESETS[0]!)
const creating = ref(false)

// inline edit
const editingId = ref<number | null>(null)
const editName = ref('')
const editColor = ref('')
const saving = ref(false)

// delete confirmation
const pendingDelete = ref<Category | null>(null)

onMounted(async () => {
  try {
    await fetchCategories(true)
  } catch (e: any) {
    error.value = e?.data?.detail || 'Could not load categories.'
  } finally {
    loading.value = false
  }
})

const totalTagged = computed(() =>
  categories.value.reduce((sum, c) => sum + c.download_count, 0)
)

function flash(msg: string) {
  notice.value = msg
  setTimeout(() => {
    if (notice.value === msg) notice.value = ''
  }, 2500)
}

function describe(e: any, fallback: string) {
  const detail = e?.data?.detail
  if (typeof detail === 'string') return detail
  // pydantic validation errors arrive as an array of objects
  if (Array.isArray(detail)) return detail[0]?.msg || fallback
  return fallback
}

async function add() {
  const name = newName.value.trim()
  if (!name || creating.value) return
  error.value = ''
  creating.value = true
  try {
    await createCategory(name, newColor.value)
    newName.value = ''
    flash(`Added "${name}"`)
  } catch (e: any) {
    error.value = describe(e, 'Could not create that category.')
  } finally {
    creating.value = false
  }
}

function startEdit(cat: Category) {
  editingId.value = cat.id
  editName.value = cat.name
  editColor.value = cat.color
  error.value = ''
}

function cancelEdit() {
  editingId.value = null
}

async function saveEdit() {
  const cat = categories.value.find((c) => c.id === editingId.value)
  if (!cat || saving.value) return
  const name = editName.value.trim()
  if (!name) {
    error.value = 'Name cannot be blank.'
    return
  }
  // nothing changed — just close the row
  if (name === cat.name && editColor.value === cat.color) {
    editingId.value = null
    return
  }
  error.value = ''
  saving.value = true
  try {
    await updateCategory(cat.id, { name, color: editColor.value })
    editingId.value = null
    flash(
      name !== cat.name && cat.download_count
        ? `Renamed — ${cat.download_count} download${cat.download_count === 1 ? '' : 's'} retagged`
        : 'Saved'
    )
  } catch (e: any) {
    error.value = describe(e, 'Could not save that category.')
  } finally {
    saving.value = false
  }
}

async function move(index: number, delta: number) {
  const target = index + delta
  if (target < 0 || target >= categories.value.length) return
  const ids = categories.value.map((c) => c.id)
  const [moved] = ids.splice(index, 1)
  ids.splice(target, 0, moved!)
  // reflect the new order immediately, then persist
  const before = categories.value
  categories.value = ids.map((id) => before.find((c) => c.id === id)!)
  try {
    await reorderCategories(ids)
  } catch (e: any) {
    categories.value = before
    error.value = describe(e, 'Could not reorder categories.')
  }
}

async function confirmDelete() {
  const cat = pendingDelete.value
  if (!cat) return
  pendingDelete.value = null
  error.value = ''
  try {
    await deleteCategory(cat.id)
    flash(
      cat.download_count
        ? `Deleted "${cat.name}" — ${cat.download_count} download${cat.download_count === 1 ? '' : 's'} untagged`
        : `Deleted "${cat.name}"`
    )
  } catch (e: any) {
    error.value = describe(e, 'Could not delete that category.')
  }
}

const deleteMessage = computed(() => {
  const cat = pendingDelete.value
  if (!cat) return ''
  if (!cat.download_count) return `"${cat.name}" isn't used by any download.`
  const n = cat.download_count
  return `${n} download${n === 1 ? '' : 's'} tagged "${cat.name}" will be untagged. The files themselves are not deleted.`
})
</script>

<template>
  <div>
    <AppNavbar />

    <main class="page">
      <header class="head reveal">
        <h1 class="display page-title">Categories</h1>
        <p class="sub mono">
          {{ categories.length }} categor{{ categories.length === 1 ? 'y' : 'ies' }}
          <span class="dot">·</span> {{ totalTagged }} tagged download{{ totalTagged === 1 ? '' : 's' }}
        </p>
      </header>

      <p v-if="error" class="msg err mono">{{ error }}</p>
      <p v-else-if="notice" class="msg ok mono">{{ notice }}</p>

      <form class="panel add-form reveal" style="animation-delay: 0.05s" @submit.prevent="add">
        <div class="swatches" role="group" aria-label="Category colour">
          <button
            v-for="p in PRESETS"
            :key="p"
            type="button"
            class="swatch"
            :class="{ on: newColor === p }"
            :style="{ background: p }"
            :title="p"
            :aria-label="`Use colour ${p}`"
            :aria-pressed="newColor === p"
            @click="newColor = p"
          />
          <label class="swatch custom" :style="{ background: newColor }" title="Custom colour">
            <input v-model="newColor" type="color" />
          </label>
        </div>

        <input
          v-model="newName"
          class="input"
          type="text"
          maxlength="50"
          placeholder="New category name…"
          aria-label="New category name"
        />
        <button class="btn btn-accent" type="submit" :disabled="creating || !newName.trim()">
          {{ creating ? 'Adding…' : 'Add' }}
        </button>
      </form>

      <p v-if="loading" class="state mono">Loading…</p>

      <p v-else-if="!categories.length" class="state mono">
        No categories yet — add your first one above.
      </p>

      <ul v-else class="list reveal" style="animation-delay: 0.1s">
        <li v-for="(cat, i) in categories" :key="cat.id" class="row panel">
          <div class="reorder">
            <button
              type="button"
              class="move"
              :disabled="i === 0"
              title="Move up"
              aria-label="Move up"
              @click="move(i, -1)"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
                <path d="m6 15 6-6 6 6" />
              </svg>
            </button>
            <button
              type="button"
              class="move"
              :disabled="i === categories.length - 1"
              title="Move down"
              aria-label="Move down"
              @click="move(i, 1)"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
                <path d="m6 9 6 6 6-6" />
              </svg>
            </button>
          </div>

          <!-- edit mode -->
          <template v-if="editingId === cat.id">
            <label class="swatch custom edit-swatch" :style="{ background: editColor }" title="Category colour">
              <input v-model="editColor" type="color" />
            </label>
            <input
              v-model="editName"
              class="input edit-name"
              type="text"
              maxlength="50"
              aria-label="Category name"
              @keyup.enter="saveEdit"
              @keyup.esc="cancelEdit"
            />
            <div class="row-actions">
              <button class="btn btn-accent btn-sm" :disabled="saving" @click="saveEdit">
                {{ saving ? 'Saving…' : 'Save' }}
              </button>
              <button class="btn btn-ghost btn-sm" @click="cancelEdit">Cancel</button>
            </div>
          </template>

          <!-- read mode -->
          <template v-else>
            <span
              class="pill mono"
              :style="{ borderColor: `${cat.color}55`, color: cat.color, background: `${cat.color}1a` }"
            >
              <span class="pill-dot" :style="{ background: cat.color }" />
              {{ cat.name }}
            </span>

            <NuxtLink
              v-if="cat.download_count"
              class="count mono"
              :to="{ path: '/', query: { category: cat.name } }"
              :title="`Show downloads tagged ${cat.name}`"
            >
              {{ cat.download_count }} download{{ cat.download_count === 1 ? '' : 's' }}
            </NuxtLink>
            <span v-else class="count mono empty">unused</span>

            <div class="row-actions">
              <button class="btn btn-ghost btn-sm" @click="startEdit(cat)">Edit</button>
              <button class="btn btn-ghost btn-sm danger" @click="pendingDelete = cat">
                Delete
              </button>
            </div>
          </template>
        </li>
      </ul>
    </main>

    <ConfirmDialog
      :open="!!pendingDelete"
      :title="`Delete ${pendingDelete?.name || ''}?`"
      :message="deleteMessage"
      confirm-label="Delete"
      danger
      @confirm="confirmDelete"
      @cancel="pendingDelete = null"
    />
  </div>
</template>

<style scoped>
.page {
  max-width: 820px;
  margin: 0 auto;
  padding: 2.2rem 1.5rem 4rem;
}

.head {
  margin-bottom: 1.4rem;
}

.page-title {
  font-size: clamp(1.6rem, 4vw, 2.2rem);
  margin: 0 0 0.4rem;
}

.sub {
  margin: 0;
  font-size: 0.78rem;
  color: var(--text-dim);
}

.dot {
  margin: 0 0.35rem;
  color: var(--text-faint);
}

.msg {
  margin: 0 0 1rem;
  padding: 0.55rem 0.75rem;
  border-radius: 6px;
  font-size: 0.76rem;
}

.msg.err {
  background: var(--err-soft);
  color: var(--err);
}

.msg.ok {
  background: var(--ok-soft);
  color: var(--ok);
}

.add-form {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.9rem 1rem;
  margin-bottom: 1.2rem;
  flex-wrap: wrap;
}

.add-form .input {
  flex: 1 1 200px;
  min-width: 0;
}

.swatches {
  display: flex;
  align-items: center;
  gap: 0.28rem;
  flex-wrap: wrap;
}

.swatch {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 2px solid transparent;
  box-shadow: 0 0 0 1px var(--line);
  cursor: pointer;
  padding: 0;
  transition: transform 0.12s, box-shadow 0.12s;
}

.swatch:hover {
  transform: scale(1.15);
}

.swatch.on {
  box-shadow: 0 0 0 2px var(--bg), 0 0 0 4px currentColor;
  transform: scale(1.1);
}

.swatch.custom {
  display: grid;
  place-items: center;
  overflow: hidden;
  position: relative;
  border-style: dashed;
  border-color: var(--line);
}

/* the native colour input is the click target, kept invisible over the dot */
.swatch.custom input[type='color'] {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  border: none;
  padding: 0;
  cursor: pointer;
}

.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.row {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 0.6rem 0.9rem;
}

.reorder {
  display: flex;
  flex-direction: column;
  gap: 1px;
  flex: none;
}

.move {
  display: grid;
  place-items: center;
  width: 20px;
  height: 15px;
  border: none;
  background: transparent;
  color: var(--text-faint);
  border-radius: 4px;
  cursor: pointer;
  transition: color 0.15s, background 0.15s;
}

.move:hover:not(:disabled) {
  color: var(--accent);
  background: var(--surface-hover);
}

.move:disabled {
  opacity: 0.3;
  cursor: default;
}

.pill {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.25rem 0.65rem;
  border-radius: 20px;
  border: 1px solid;
  font-size: 0.66rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  flex: none;
}

.pill-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.count {
  font-size: 0.7rem;
  color: var(--text-dim);
  margin-right: auto;
  border-bottom: 1px dashed transparent;
  transition: color 0.15s, border-color 0.15s;
}

a.count:hover {
  color: var(--accent);
  border-bottom-color: currentColor;
}

.count.empty {
  color: var(--text-faint);
}

.row-actions {
  display: flex;
  gap: 0.3rem;
  flex: none;
}

.btn-sm {
  padding: 0.32rem 0.65rem;
  font-size: 0.72rem;
}

.btn-ghost.danger:hover {
  color: var(--err);
  background: var(--err-soft);
}

.edit-swatch {
  width: 26px;
  height: 26px;
  flex: none;
}

.edit-name {
  flex: 1 1 auto;
  min-width: 0;
  padding: 0.35rem 0.6rem;
  font-size: 0.82rem;
}

.state {
  padding: 2rem 0;
  text-align: center;
  color: var(--text-dim);
  font-size: 0.8rem;
}

@media (max-width: 560px) {
  .row {
    flex-wrap: wrap;
  }

  .count {
    margin-right: 0;
  }

  .row-actions {
    margin-left: auto;
  }
}
</style>
