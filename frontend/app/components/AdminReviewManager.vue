<script setup lang="ts">
import type { Review } from '~/types'

type ReviewPayload = {
  author_name: string
  author_title: string | null
  rating: number
  body: string
  is_published: boolean
}

const { request } = useApi()

const reviews = ref<Review[]>([])
const loading = ref(true)
const error = ref('')
const notice = ref('')
const saving = ref(false)
const editingId = ref<number | null>(null)
const pendingDelete = ref<Review | null>(null)

const draft = reactive({
  author_name: '',
  author_title: '',
  rating: 5,
  body: '',
  is_published: true,
})

const publishedCount = computed(() => reviews.value.filter((r) => r.is_published).length)
const modeLabel = computed(() => (editingId.value ? 'Edit review' : 'New review'))
const submitLabel = computed(() => {
  if (saving.value) return editingId.value ? 'Saving...' : 'Adding...'
  return editingId.value ? 'Save' : 'Add'
})

onMounted(load)

function flash(msg: string) {
  notice.value = msg
  setTimeout(() => {
    if (notice.value === msg) notice.value = ''
  }, 2500)
}

function resetDraft() {
  editingId.value = null
  draft.author_name = ''
  draft.author_title = ''
  draft.rating = 5
  draft.body = ''
  draft.is_published = true
}

function ratingDots(rating: number) {
  return Array.from({ length: 5 }, (_, i) => i < rating)
}

function payload(): ReviewPayload | null {
  const authorName = draft.author_name.trim()
  const body = draft.body.trim()
  if (!authorName || !body) {
    error.value = 'Name and review text are required.'
    return null
  }
  const rating = Math.min(5, Math.max(1, Number(draft.rating) || 5))
  return {
    author_name: authorName,
    author_title: draft.author_title.trim() || null,
    rating,
    body,
    is_published: draft.is_published,
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    reviews.value = await request<Review[]>('/admin/reviews')
  } catch (e) {
    error.value = errorMessage(e, 'Could not load reviews.')
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (saving.value) return
  const body = payload()
  if (!body) return
  saving.value = true
  error.value = ''
  try {
    if (editingId.value) {
      const updated = await request<Review>(`/admin/reviews/${editingId.value}`, {
        method: 'PATCH',
        body,
      })
      reviews.value = reviews.value.map((r) => (r.id === updated.id ? updated : r))
      flash('Saved')
    } else {
      const created = await request<Review>('/admin/reviews', {
        method: 'POST',
        body,
      })
      reviews.value = [created, ...reviews.value]
      flash('Added')
    }
    resetDraft()
  } catch (e) {
    error.value = fieldErrorMessage(e, 'Could not save that review.')
  } finally {
    saving.value = false
  }
}

function startEdit(review: Review) {
  editingId.value = review.id
  draft.author_name = review.author_name
  draft.author_title = review.author_title || ''
  draft.rating = review.rating
  draft.body = review.body
  draft.is_published = review.is_published
  error.value = ''
}

async function confirmDelete() {
  const review = pendingDelete.value
  if (!review) return
  pendingDelete.value = null
  error.value = ''
  try {
    await request(`/admin/reviews/${review.id}`, { method: 'DELETE' })
    reviews.value = reviews.value.filter((r) => r.id !== review.id)
    if (editingId.value === review.id) resetDraft()
    flash('Deleted')
  } catch (e) {
    error.value = errorMessage(e, 'Could not delete that review.')
  }
}

const deleteMessage = computed(() => {
  const review = pendingDelete.value
  if (!review) return ''
  return `"${review.author_name}" will be removed from the Reviews page.`
})
</script>

<template>
  <section class="panel reviews-panel reveal" style="animation-delay: 0.24s">
    <header class="section-head">
      <div>
        <h2 class="label table-title">Reviews</h2>
        <p class="meta mono">
          {{ reviews.length }} total <span class="dot">/</span>
          {{ publishedCount }} published
        </p>
      </div>
      <NuxtLink to="/reviews" class="btn btn-ghost btn-sm" title="Open Reviews page">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M7 17 17 7" />
          <path d="M8 7h9v9" />
        </svg>
        View
      </NuxtLink>
    </header>

    <p v-if="error" class="msg err mono">{{ error }}</p>
    <p v-else-if="notice" class="msg ok mono">{{ notice }}</p>

    <form class="review-form" @submit.prevent="submit">
      <div class="form-head">
        <span class="label">{{ modeLabel }}</span>
        <button
          v-if="editingId"
          type="button"
          class="btn btn-ghost btn-sm"
          @click="resetDraft"
        >
          Cancel
        </button>
      </div>

      <div class="form-grid">
        <label class="field">
          <span class="label">Name</span>
          <input
            v-model="draft.author_name"
            class="input"
            maxlength="80"
            type="text"
            autocomplete="off"
          />
        </label>

        <label class="field">
          <span class="label">Title</span>
          <input
            v-model="draft.author_title"
            class="input"
            maxlength="120"
            type="text"
            autocomplete="off"
          />
        </label>

        <label class="field rating-field">
          <span class="label">Rating</span>
          <input v-model.number="draft.rating" class="input" type="number" min="1" max="5" />
        </label>

        <label class="publish-toggle">
          <input v-model="draft.is_published" type="checkbox" />
          <span class="switch" aria-hidden="true" />
          <span class="label">Published</span>
        </label>

        <label class="field body-field">
          <span class="label">Review</span>
          <textarea v-model="draft.body" class="input textarea" maxlength="1000" rows="4" />
        </label>
      </div>

      <div class="form-actions">
        <button class="btn btn-accent" type="submit" :disabled="saving">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M12 5v14" />
            <path d="M5 12h14" />
          </svg>
          {{ submitLabel }}
        </button>
      </div>
    </form>

    <p v-if="loading" class="state mono">Loading...</p>

    <p v-else-if="!reviews.length" class="state mono">No reviews yet.</p>

    <div v-else class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Reviewer</th>
            <th>Rating</th>
            <th>Review</th>
            <th>Status</th>
            <th class="actions-col">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="review in reviews" :key="review.id">
            <td>
              <span class="reviewer">{{ review.author_name }}</span>
              <span v-if="review.author_title" class="title mono">{{ review.author_title }}</span>
            </td>
            <td>
              <span class="rating" :aria-label="`${review.rating} out of 5`">
                <span
                  v-for="(on, i) in ratingDots(review.rating)"
                  :key="i"
                  class="rating-dot"
                  :class="{ on }"
                />
              </span>
            </td>
            <td class="quote">{{ review.body }}</td>
            <td>
              <span v-if="review.is_published" class="badge badge-completed">published</span>
              <span v-else class="badge badge-queued">draft</span>
            </td>
            <td>
              <div class="row-actions">
                <button class="btn btn-ghost btn-sm" type="button" @click="startEdit(review)">
                  Edit
                </button>
                <button
                  class="btn btn-ghost btn-sm danger"
                  type="button"
                  @click="pendingDelete = review"
                >
                  Delete
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <ConfirmDialog
      :open="!!pendingDelete"
      :title="`Delete ${pendingDelete?.author_name || ''}?`"
      :message="deleteMessage"
      confirm-label="Delete"
      danger
      @confirm="confirmDelete"
      @cancel="pendingDelete = null"
    />
  </section>
</template>

<style scoped>
.reviews-panel {
  margin-bottom: 1.4rem;
  overflow: hidden;
}

.section-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.9rem 1.2rem 0;
}

.table-title {
  margin: 0 0 0.35rem;
}

.meta {
  margin: 0;
  color: var(--text-dim);
  font-size: 0.75rem;
}

.dot {
  color: var(--text-faint);
  margin: 0 0.35rem;
}

.msg {
  margin: 0.9rem 1.2rem 0;
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

.review-form {
  padding: 1rem 1.2rem 1.2rem;
  border-bottom: 1px solid var(--line);
}

.form-head,
.form-actions,
.row-actions {
  display: flex;
  align-items: center;
}

.form-head {
  justify-content: space-between;
  margin-bottom: 0.8rem;
}

.form-grid {
  display: grid;
  grid-template-columns: minmax(140px, 1fr) minmax(160px, 1.2fr) 96px auto;
  gap: 0.75rem;
  align-items: end;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  min-width: 0;
}

.body-field {
  grid-column: 1 / -1;
}

.textarea {
  resize: vertical;
  min-height: 90px;
  line-height: 1.45;
}

.publish-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 42px;
  cursor: pointer;
}

.publish-toggle input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.switch {
  position: relative;
  width: 36px;
  height: 20px;
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  background: var(--bg-raised);
  transition: background 0.15s, border-color 0.15s;
}

.switch::after {
  content: '';
  position: absolute;
  top: 3px;
  left: 3px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--text-faint);
  transition: transform 0.15s, background 0.15s;
}

.publish-toggle input:checked + .switch {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.publish-toggle input:checked + .switch::after {
  transform: translateX(16px);
  background: var(--accent);
}

.form-actions {
  justify-content: flex-end;
  margin-top: 0.8rem;
}

.btn-sm {
  padding: 0.45rem 0.7rem;
  font-size: 0.68rem;
}

.danger {
  color: var(--err);
}

.table-scroll {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}

th {
  text-align: left;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.62rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--text-faint);
  font-weight: 500;
  padding: 0.8rem 1.2rem 0.5rem;
}

td {
  vertical-align: top;
  padding: 0.65rem 1.2rem;
  border-top: 1px solid var(--line);
}

.reviewer,
.title {
  display: block;
}

.reviewer {
  font-weight: 700;
}

.title {
  margin-top: 0.18rem;
  color: var(--text-dim);
  font-size: 0.68rem;
}

.quote {
  min-width: 260px;
  max-width: 460px;
  color: var(--text-dim);
  line-height: 1.45;
}

.rating {
  display: inline-flex;
  gap: 0.18rem;
  width: 70px;
}

.rating-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--line-strong);
}

.rating-dot.on {
  background: var(--accent);
}

.actions-col {
  text-align: right;
}

.row-actions {
  justify-content: flex-end;
  gap: 0.35rem;
}

.state {
  margin: 0;
  padding: 1.1rem 1.2rem;
  color: var(--text-dim);
  font-size: 0.76rem;
}

@media (max-width: 760px) {
  .section-head {
    align-items: flex-start;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .rating-field {
    max-width: 140px;
  }

  .publish-toggle {
    justify-content: flex-start;
  }
}
</style>
