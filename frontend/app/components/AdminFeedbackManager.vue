<script setup lang="ts">
import type { Feedback } from '~/types'

type FeedbackPayload = {
  author_name: string
  author_email: string | null
  category: string
  rating: number
  body: string
  is_published: boolean
}

const { request } = useApi()

const feedbacks = ref<Feedback[]>([])
const loading = ref(true)
const error = ref('')
const notice = ref('')
const saving = ref(false)
const editingId = ref<number | null>(null)
const pendingDelete = ref<Feedback | null>(null)
const statusFilter = ref<'all' | 'published' | 'draft'>('all')
const categoryFilter = ref('all')

const CATEGORIES = [
  { id: 'all', label: 'All Categories' },
  { id: 'suggestion', label: 'Suggestions' },
  { id: 'bug', label: 'Bugs' },
  { id: 'general', label: 'General' },
  { id: 'praise', label: 'Praise' },
]

const draft = reactive({
  author_name: '',
  author_email: '',
  category: 'general',
  rating: 5,
  body: '',
  is_published: true,
})

const publishedCount = computed(() => feedbacks.value.filter((f) => f.is_published).length)
const modeLabel = computed(() => (editingId.value ? 'Edit feedback' : 'Add feedback'))
const submitLabel = computed(() => {
  if (saving.value) return editingId.value ? 'Saving...' : 'Adding...'
  return editingId.value ? 'Save' : 'Add'
})

const filteredFeedbacks = computed(() => {
  return feedbacks.value.filter((f) => {
    if (statusFilter.value === 'published' && !f.is_published) return false
    if (statusFilter.value === 'draft' && f.is_published) return false
    if (categoryFilter.value !== 'all' && f.category !== categoryFilter.value) return false
    return true
  })
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
  draft.author_email = ''
  draft.category = 'general'
  draft.rating = 5
  draft.body = ''
  draft.is_published = true
}

function ratingDots(rating: number) {
  return Array.from({ length: 5 }, (_, i) => i < rating)
}

function payload(): FeedbackPayload | null {
  const authorName = draft.author_name.trim()
  const body = draft.body.trim()
  if (!authorName || !body) {
    error.value = 'Name and message are required.'
    return null
  }
  const rating = Math.min(5, Math.max(1, Number(draft.rating) || 5))
  return {
    author_name: authorName,
    author_email: draft.author_email.trim() || null,
    category: draft.category,
    rating,
    body,
    is_published: draft.is_published,
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    feedbacks.value = await request<Feedback[]>('/admin/feedback')
  } catch (e) {
    error.value = errorMessage(e, 'Could not load feedback.')
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
      const updated = await request<Feedback>(`/admin/feedback/${editingId.value}`, {
        method: 'PATCH',
        body,
      })
      feedbacks.value = feedbacks.value.map((f) => (f.id === updated.id ? updated : f))
      flash('Saved')
    } else {
      const created = await request<Feedback>('/admin/feedback', {
        method: 'POST',
        body,
      })
      feedbacks.value = [created, ...feedbacks.value]
      flash('Added')
    }
    resetDraft()
  } catch (e) {
    error.value = fieldErrorMessage(e, 'Could not save that feedback.')
  } finally {
    saving.value = false
  }
}

function startEdit(feedback: Feedback) {
  editingId.value = feedback.id
  draft.author_name = feedback.author_name
  draft.author_email = feedback.author_email || ''
  draft.category = feedback.category || 'general'
  draft.rating = feedback.rating
  draft.body = feedback.body
  draft.is_published = feedback.is_published
  error.value = ''
}

async function togglePublish(feedback: Feedback) {
  try {
    const updated = await request<Feedback>(`/admin/feedback/${feedback.id}`, {
      method: 'PATCH',
      body: { is_published: !feedback.is_published },
    })
    feedbacks.value = feedbacks.value.map((f) => (f.id === updated.id ? updated : f))
    flash(updated.is_published ? 'Published' : 'Unpublished')
  } catch (e) {
    error.value = errorMessage(e, 'Could not change publication status.')
  }
}

async function confirmDelete() {
  const feedback = pendingDelete.value
  if (!feedback) return
  pendingDelete.value = null
  error.value = ''
  try {
    await request(`/admin/feedback/${feedback.id}`, { method: 'DELETE' })
    feedbacks.value = feedbacks.value.filter((f) => f.id !== feedback.id)
    if (editingId.value === feedback.id) resetDraft()
    flash('Deleted')
  } catch (e) {
    error.value = errorMessage(e, 'Could not delete that feedback.')
  }
}

function categoryBadgeClass(category: string) {
  switch (category) {
    case 'bug':
      return 'badge-bug'
    case 'suggestion':
      return 'badge-suggestion'
    case 'praise':
      return 'badge-praise'
    default:
      return 'badge-general'
  }
}

const deleteMessage = computed(() => {
  const feedback = pendingDelete.value
  if (!feedback) return ''
  return `Feedback from "${feedback.author_name}" will be permanently removed.`
})
</script>

<template>
  <section class="panel feedback-panel reveal" style="animation-delay: 0.24s">
    <header class="section-head">
      <div>
        <h2 class="label table-title">User Feedback</h2>
        <p class="meta mono">
          {{ feedbacks.length }} total <span class="dot">/</span>
          {{ publishedCount }} published
        </p>
      </div>
      <NuxtLink to="/feedback" class="btn btn-ghost btn-sm" title="Open public Feedback page">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M7 17 17 7" />
          <path d="M8 7h9v9" />
        </svg>
        View Public Page
      </NuxtLink>
    </header>

    <p v-if="error" class="msg err mono">{{ error }}</p>
    <p v-else-if="notice" class="msg ok mono">{{ notice }}</p>

    <!-- Create / Edit Form -->
    <form class="feedback-form" @submit.prevent="submit">
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
            placeholder="Author name"
          />
        </label>

        <label class="field">
          <span class="label">Email</span>
          <input
            v-model="draft.author_email"
            class="input"
            maxlength="120"
            type="email"
            autocomplete="off"
            placeholder="author@example.com"
          />
        </label>

        <label class="field">
          <span class="label">Category</span>
          <select v-model="draft.category" class="input select">
            <option value="general">General</option>
            <option value="suggestion">Suggestion</option>
            <option value="bug">Bug Report</option>
            <option value="praise">Appreciation</option>
          </select>
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
          <span class="label">Feedback Message</span>
          <textarea
            v-model="draft.body"
            class="input textarea"
            maxlength="1000"
            rows="3"
            placeholder="Feedback content..."
          />
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

    <!-- Filter toolbar -->
    <div class="table-toolbar">
      <div class="filter-group">
        <span class="label">Status:</span>
        <div class="filters">
          <button
            type="button"
            class="filter-btn"
            :class="{ on: statusFilter === 'all' }"
            @click="statusFilter = 'all'"
          >
            All
          </button>
          <button
            type="button"
            class="filter-btn"
            :class="{ on: statusFilter === 'published' }"
            @click="statusFilter = 'published'"
          >
            Published
          </button>
          <button
            type="button"
            class="filter-btn"
            :class="{ on: statusFilter === 'draft' }"
            @click="statusFilter = 'draft'"
          >
            Draft
          </button>
        </div>
      </div>

      <div class="filter-group">
        <span class="label">Category:</span>
        <select v-model="categoryFilter" class="input select-sm">
          <option v-for="c in CATEGORIES" :key="c.id" :value="c.id">
            {{ c.label }}
          </option>
        </select>
      </div>
    </div>

    <p v-if="loading" class="state mono">Loading...</p>
    <p v-else-if="!filteredFeedbacks.length" class="state mono">No feedback found.</p>

    <div v-else class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Author</th>
            <th>Category</th>
            <th>Rating</th>
            <th>Feedback</th>
            <th>Status</th>
            <th class="actions-col">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in filteredFeedbacks" :key="item.id">
            <td>
              <span class="author-name">{{ item.author_name }}</span>
              <span v-if="item.author_email" class="email mono">{{ item.author_email }}</span>
            </td>
            <td>
              <span class="cat-badge" :class="categoryBadgeClass(item.category)">
                {{ item.category }}
              </span>
            </td>
            <td>
              <span class="rating" :aria-label="`${item.rating} out of 5`">
                <span
                  v-for="(on, i) in ratingDots(item.rating)"
                  :key="i"
                  class="rating-dot"
                  :class="{ on }"
                />
              </span>
            </td>
            <td class="quote">{{ item.body }}</td>
            <td>
              <button
                type="button"
                class="badge-btn"
                :title="item.is_published ? 'Click to unpublish' : 'Click to publish'"
                @click="togglePublish(item)"
              >
                <span v-if="item.is_published" class="badge badge-completed">published</span>
                <span v-else class="badge badge-queued">draft</span>
              </button>
            </td>
            <td>
              <div class="row-actions">
                <button class="btn btn-ghost btn-sm" type="button" @click="startEdit(item)">
                  Edit
                </button>
                <button
                  class="btn btn-ghost btn-sm danger"
                  type="button"
                  @click="pendingDelete = item"
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
      :title="`Delete feedback from ${pendingDelete?.author_name || ''}?`"
      :message="deleteMessage"
      confirm-label="Delete"
      danger
      @confirm="confirmDelete"
      @cancel="pendingDelete = null"
    />
  </section>
</template>

<style scoped>
.feedback-panel {
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

.feedback-form {
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
  grid-template-columns: minmax(130px, 1fr) minmax(160px, 1.2fr) 130px 90px auto;
  gap: 0.75rem;
  align-items: end;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  min-width: 0;
}

.select {
  cursor: pointer;
  padding-right: 1.8rem;
}

.body-field {
  grid-column: 1 / -1;
}

.textarea {
  resize: vertical;
  min-height: 80px;
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

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.8rem 1.2rem;
  background: var(--surface);
  border-bottom: 1px solid var(--line);
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.select-sm {
  width: auto;
  min-width: 140px;
  padding: 0.35rem 0.65rem;
  font-size: 0.78rem;
  cursor: pointer;
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

.author-name {
  display: block;
  font-weight: 700;
}

.email {
  display: block;
  margin-top: 0.18rem;
  color: var(--text-dim);
  font-size: 0.68rem;
}

.cat-badge {
  display: inline-block;
  font-size: 0.65rem;
  font-family: 'IBM Plex Mono', monospace;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-weight: 600;
}

.badge-suggestion {
  background: rgba(34, 211, 238, 0.12);
  color: #22d3ee;
}

.badge-bug {
  background: var(--err-soft);
  color: var(--err);
}

.badge-praise {
  background: var(--accent-soft);
  color: var(--accent);
}

.badge-general {
  background: var(--surface-hover);
  color: var(--text-dim);
}

.badge-btn {
  background: transparent;
  border: none;
  padding: 0;
  cursor: pointer;
}

.badge-btn:hover {
  opacity: 0.8;
}

.quote {
  min-width: 240px;
  max-width: 440px;
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

@media (max-width: 860px) {
  .form-grid {
    grid-template-columns: 1fr;
  }

  .rating-field {
    max-width: 140px;
  }
}
</style>
