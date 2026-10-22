<script setup lang="ts">
import type { Feedback } from '~/types'

const { request } = useApi()
const { user } = useAuth()

const feedbacks = ref<Feedback[]>([])
const loading = ref(true)
const submitting = ref(false)
const error = ref('')
const submitError = ref('')
const successNotice = ref('')
const showForm = ref(false)
const activeCategory = ref('all')

const CATEGORIES = [
  { id: 'all', label: 'All', icon: '✦' },
  { id: 'suggestion', label: 'Suggestion', icon: '💡' },
  { id: 'bug', label: 'Bug Report', icon: '🐛' },
  { id: 'general', label: 'General', icon: '💬' },
  { id: 'praise', label: 'Appreciation', icon: '⭐' },
]

const draft = reactive({
  category: 'suggestion',
  rating: 5,
  body: '',
  author_name: '',
  author_email: '',
})

const hoveredRating = ref<number | null>(null)

const ratingLabels: Record<number, string> = {
  1: 'Poor',
  2: 'Fair',
  3: 'Good',
  4: 'Very Good',
  5: 'Excellent',
}

onMounted(async () => {
  await loadFeedback()
})

async function loadFeedback() {
  loading.value = true
  error.value = ''
  try {
    const params = activeCategory.value !== 'all' ? { category: activeCategory.value } : undefined
    feedbacks.value = await request<Feedback[]>('/feedback', { params })
  } catch (e) {
    error.value = errorMessage(e, 'Could not load feedback.')
  } finally {
    loading.value = false
  }
}

watch(activeCategory, () => {
  loadFeedback()
})

function setCategoryFilter(id: string) {
  activeCategory.value = id
}

function ratingDots(rating: number) {
  return Array.from({ length: 5 }, (_, i) => i < rating)
}

function resetForm() {
  draft.category = 'suggestion'
  draft.rating = 5
  draft.body = ''
  draft.author_name = ''
  draft.author_email = ''
  submitError.value = ''
}

async function submitFeedback() {
  if (submitting.value) return
  const bodyText = draft.body.trim()
  if (!bodyText) {
    submitError.value = 'Please provide your feedback message.'
    return
  }

  submitting.value = true
  submitError.value = ''

  try {
    const payload = {
      category: draft.category,
      rating: draft.rating,
      body: bodyText,
      author_name: draft.author_name.trim() || (user.value ? user.value.username : 'Anonymous'),
      author_email: draft.author_email.trim() || (user.value ? user.value.email : undefined),
    }

    const created = await request<Feedback>('/feedback', {
      method: 'POST',
      body: payload,
    })

    feedbacks.value = [created, ...feedbacks.value]
    resetForm()
    showForm.value = false
    successNotice.value = 'Thank you! Your feedback has been submitted.'
    setTimeout(() => {
      successNotice.value = ''
    }, 4000)
  } catch (e) {
    submitError.value = errorMessage(e, 'Could not submit feedback.')
  } finally {
    submitting.value = false
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

function categoryIcon(category: string) {
  switch (category) {
    case 'bug':
      return '🐛'
    case 'suggestion':
      return '💡'
    case 'praise':
      return '⭐'
    default:
      return '💬'
  }
}

function formatDateDisplay(iso: string) {
  try {
    const d = new Date(iso)
    return d.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  } catch {
    return iso
  }
}
</script>

<template>
  <div>
    <AppNavbar />

    <main class="page">
      <header class="head reveal">
        <div>
          <h1 class="display page-title">Feedback</h1>
          <p class="sub">
            Help us improve MediaBox. Share your ideas, report issues, or tell us what you think.
          </p>
        </div>
        <button
          class="btn btn-accent action-btn"
          type="button"
          @click="showForm = !showForm"
        >
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path v-if="!showForm" d="M12 5v14M5 12h14" />
            <path v-else d="M18 6 6 18M6 6l12 12" />
          </svg>
          {{ showForm ? 'Close Form' : 'Give Feedback' }}
        </button>
      </header>

      <!-- Success notification -->
      <Transition name="slide">
        <div v-if="successNotice" class="notice panel ok mono reveal">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M20 6 9 17l-5-5" />
          </svg>
          {{ successNotice }}
        </div>
      </Transition>

      <!-- Feedback submission card -->
      <Transition name="expand">
        <section v-if="showForm" class="form-card panel reveal">
          <div class="form-header">
            <div>
              <h2 class="display form-title">Share Your Thoughts</h2>
              <p class="sub mono">Your suggestions and reports help us build a better experience.</p>
            </div>
            <span v-if="user" class="user-badge mono">
              Posting as <strong>@{{ user.username }}</strong>
            </span>
          </div>

          <form @submit.prevent="submitFeedback">
            <div class="form-section">
              <label class="label">Feedback Category</label>
              <div class="cat-picker">
                <button
                  v-for="cat in CATEGORIES.filter((c) => c.id !== 'all')"
                  :key="cat.id"
                  type="button"
                  class="cat-chip"
                  :class="{ on: draft.category === cat.id }"
                  @click="draft.category = cat.id"
                >
                  <span class="chip-icon">{{ cat.icon }}</span>
                  <span class="chip-label">{{ cat.label }}</span>
                </button>
              </div>
            </div>

            <div class="form-section">
              <div class="rating-header">
                <label class="label">Experience Rating</label>
                <span class="rating-hint mono">
                  {{ ratingLabels[hoveredRating || draft.rating] }}
                </span>
              </div>
              <div class="star-picker" role="radiogroup" aria-label="Rating">
                <button
                  v-for="star in 5"
                  :key="star"
                  type="button"
                  class="star-btn"
                  :class="{ active: star <= (hoveredRating || draft.rating) }"
                  :aria-label="`${star} stars`"
                  @click="draft.rating = star"
                  @mouseenter="hoveredRating = star"
                  @mouseleave="hoveredRating = null"
                >
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.5">
                    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                  </svg>
                </button>
              </div>
            </div>

            <div v-if="!user" class="form-row">
              <label class="field">
                <span class="label">Your Name (optional)</span>
                <input
                  v-model="draft.author_name"
                  type="text"
                  class="input"
                  placeholder="Anonymous"
                  maxlength="80"
                />
              </label>
              <label class="field">
                <span class="label">Email Address (optional)</span>
                <input
                  v-model="draft.author_email"
                  type="email"
                  class="input"
                  placeholder="name@example.com"
                  maxlength="120"
                />
              </label>
            </div>

            <label class="field message-field">
              <div class="textarea-head">
                <span class="label">Message</span>
                <span class="char-count mono">{{ draft.body.length }} / 1000</span>
              </div>
              <textarea
                v-model="draft.body"
                class="input textarea"
                rows="4"
                maxlength="1000"
                placeholder="What's working well? What could we improve or add? Any bugs you encountered?"
                required
              />
            </label>

            <p v-if="submitError" class="err-text mono">{{ submitError }}</p>

            <div class="form-footer">
              <button
                type="button"
                class="btn btn-ghost"
                @click="showForm = false"
              >
                Cancel
              </button>
              <button
                type="submit"
                class="btn btn-accent"
                :disabled="submitting || !draft.body.trim()"
              >
                <svg
                  v-if="!submitting"
                  width="15"
                  height="15"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
                {{ submitting ? 'Submitting...' : 'Send Feedback' }}
              </button>
            </div>
          </form>
        </section>
      </Transition>

      <!-- Category Filter Tabs -->
      <div class="filters-row reveal">
        <div class="filters" role="tablist" aria-label="Feedback category filters">
          <button
            v-for="cat in CATEGORIES"
            :key="cat.id"
            type="button"
            class="filter-btn"
            :class="{ on: activeCategory === cat.id }"
            @click="setCategoryFilter(cat.id)"
          >
            <span class="tab-icon">{{ cat.icon }}</span>
            {{ cat.label }}
          </button>
        </div>

        <span class="count-tag mono">
          {{ feedbacks.length }} item{{ feedbacks.length === 1 ? '' : 's' }}
        </span>
      </div>

      <!-- Feedbacks Grid -->
      <div v-if="loading" class="state panel mono reveal">
        Loading feedback...
      </div>
      <div v-else-if="error" class="state panel err mono reveal">
        {{ error }}
      </div>
      <div v-else-if="!feedbacks.length" class="empty-card panel reveal">
        <span class="empty-icon">💬</span>
        <h3 class="display empty-title">No feedback yet</h3>
        <p class="empty-sub">
          Be the first to share your experience, feature ideas, or bug reports!
        </p>
        <button
          class="btn btn-accent"
          type="button"
          @click="showForm = true"
        >
          Leave First Feedback
        </button>
      </div>

      <section v-else class="feedback-grid">
        <article
          v-for="(item, i) in feedbacks"
          :key="item.id"
          class="feedback-card panel reveal"
          :style="{ animationDelay: `${Math.min(i * 0.05, 0.3)}s` }"
        >
          <header class="card-head">
            <span class="cat-badge" :class="categoryBadgeClass(item.category)">
              <span class="badge-icon">{{ categoryIcon(item.category) }}</span>
              {{ item.category }}
            </span>

            <div class="rating" :aria-label="`${item.rating} out of 5 stars`">
              <span
                v-for="(on, n) in ratingDots(item.rating)"
                :key="n"
                class="rating-dot"
                :class="{ on }"
              />
            </div>
          </header>

          <p class="body-text">{{ item.body }}</p>

          <footer class="card-foot">
            <div class="author-info">
              <span class="author-name">{{ item.author_name || 'Anonymous' }}</span>
              <span class="date-tag mono">{{ formatDateDisplay(item.created_at) }}</span>
            </div>
          </footer>
        </article>
      </section>
    </main>
  </div>
</template>

<style scoped>
.page {
  max-width: 1040px;
  margin: 0 auto;
  padding: 2.2rem 1.5rem 4rem;
}

.head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1.2rem;
  margin-bottom: 1.8rem;
}

.page-title {
  font-size: clamp(1.8rem, 4vw, 2.6rem);
  margin: 0 0 0.35rem;
}

.sub {
  margin: 0;
  color: var(--text-dim);
  font-size: 0.88rem;
  line-height: 1.45;
  max-width: 620px;
}

.action-btn {
  flex-shrink: 0;
}

.notice {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.85rem 1.1rem;
  margin-bottom: 1.4rem;
  font-size: 0.82rem;
  border-radius: 8px;
}

.notice.ok {
  background: var(--ok-soft);
  color: var(--ok);
  border: 1px solid var(--ok);
}

.form-card {
  padding: 1.4rem 1.6rem;
  margin-bottom: 2rem;
  border: 1px solid var(--line-strong);
  box-shadow: var(--shadow);
}

.form-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1.3rem;
  border-bottom: 1px solid var(--line);
  padding-bottom: 1rem;
}

.form-title {
  font-size: 1.25rem;
  margin: 0 0 0.25rem;
}

.user-badge {
  font-size: 0.72rem;
  background: var(--surface-hover);
  padding: 0.35rem 0.7rem;
  border-radius: 6px;
  border: 1px solid var(--line);
  color: var(--text-dim);
}

.user-badge strong {
  color: var(--accent);
}

.form-section {
  margin-bottom: 1.2rem;
}

.cat-picker {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.4rem;
}

.cat-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 0.9rem;
  border-radius: 6px;
  background: var(--bg-raised);
  border: 1px solid var(--line);
  color: var(--text-dim);
  font-size: 0.82rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.cat-chip:hover {
  background: var(--surface-hover);
  color: var(--text);
  border-color: var(--text-faint);
}

.cat-chip.on {
  background: var(--accent-soft);
  border-color: var(--accent);
  color: var(--accent);
  font-weight: 700;
}

.rating-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.4rem;
}

.rating-hint {
  font-size: 0.75rem;
  color: var(--accent);
  font-weight: 600;
}

.star-picker {
  display: inline-flex;
  gap: 0.35rem;
}

.star-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0.2rem;
  color: var(--line-strong);
  transition: color 0.15s, transform 0.1s;
}

.star-btn:hover {
  transform: scale(1.15);
}

.star-btn.active {
  color: var(--accent);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-bottom: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.message-field {
  margin-bottom: 1rem;
}

.textarea-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.char-count {
  font-size: 0.7rem;
  color: var(--text-faint);
}

.textarea {
  min-height: 110px;
  resize: vertical;
  line-height: 1.5;
}

.err-text {
  color: var(--err);
  font-size: 0.78rem;
  margin-bottom: 0.8rem;
}

.form-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.8rem;
  margin-top: 1rem;
}

.filters-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.3rem;
  gap: 1rem;
  flex-wrap: wrap;
}

.tab-icon {
  margin-right: 0.2rem;
}

.count-tag {
  color: var(--text-dim);
  font-size: 0.76rem;
}

.state {
  margin: 0;
  padding: 1.2rem;
  color: var(--text-dim);
  font-size: 0.8rem;
  text-align: center;
}

.state.err {
  color: var(--err);
  background: var(--err-soft);
}

.empty-card {
  padding: 3rem 1.5rem;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.8rem;
}

.empty-icon {
  font-size: 2.4rem;
}

.empty-title {
  margin: 0;
  font-size: 1.3rem;
}

.empty-sub {
  margin: 0;
  color: var(--text-dim);
  font-size: 0.88rem;
  max-width: 420px;
}

.feedback-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
  gap: 1rem;
}

.feedback-card {
  display: flex;
  flex-direction: column;
  padding: 1.25rem;
  min-height: 190px;
  border: 1px solid var(--line);
  transition: transform 0.15s ease, border-color 0.15s ease;
}

.feedback-card:hover {
  transform: translateY(-2px);
  border-color: var(--line-strong);
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem;
  margin-bottom: 0.9rem;
}

.cat-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.68rem;
  font-family: 'IBM Plex Mono', monospace;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 0.25rem 0.55rem;
  border-radius: 4px;
  font-weight: 600;
}

.badge-suggestion {
  background: rgba(34, 211, 238, 0.12);
  color: #22d3ee;
  border: 1px solid rgba(34, 211, 238, 0.25);
}

.badge-bug {
  background: var(--err-soft);
  color: var(--err);
  border: 1px solid rgba(229, 72, 77, 0.25);
}

.badge-praise {
  background: var(--accent-soft);
  color: var(--accent);
  border: 1px solid rgba(242, 163, 60, 0.25);
}

.badge-general {
  background: var(--surface-hover);
  color: var(--text-dim);
  border: 1px solid var(--line-strong);
}

.rating {
  display: inline-flex;
  gap: 0.22rem;
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

.body-text {
  margin: 0;
  color: var(--text);
  line-height: 1.55;
  font-size: 0.92rem;
  white-space: pre-line;
  word-break: break-word;
}

.card-foot {
  margin-top: auto;
  padding-top: 1.2rem;
  border-top: 1px solid var(--line);
}

.author-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem;
}

.author-name {
  font-weight: 700;
  font-size: 0.85rem;
  color: var(--text);
}

.date-tag {
  color: var(--text-faint);
  font-size: 0.7rem;
}

@media (max-width: 680px) {
  .head {
    flex-direction: column;
    align-items: flex-start;
  }

  .action-btn {
    width: 100%;
  }

  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
