<script setup lang="ts">
import type { Review } from '~/types'

const { request } = useApi()

const reviews = ref<Review[]>([])
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    reviews.value = await request<Review[]>('/reviews')
  } catch (e) {
    error.value = errorMessage(e, 'Could not load reviews.')
  } finally {
    loading.value = false
  }
})

function ratingDots(rating: number) {
  return Array.from({ length: 5 }, (_, i) => i < rating)
}
</script>

<template>
  <div>
    <AppNavbar />

    <main class="page">
      <header class="head reveal">
        <h1 class="display page-title">Reviews</h1>
        <p class="sub mono">
          {{ reviews.length }} published review{{ reviews.length === 1 ? '' : 's' }}
        </p>
      </header>

      <p v-if="loading" class="state panel mono reveal">Loading...</p>
      <p v-else-if="error" class="state panel err mono reveal">{{ error }}</p>
      <p v-else-if="!reviews.length" class="state panel mono reveal">No reviews yet.</p>

      <section v-else class="reviews-grid">
        <article
          v-for="(review, i) in reviews"
          :key="review.id"
          class="review panel reveal"
          :style="{ animationDelay: `${Math.min(i * 0.05, 0.3)}s` }"
        >
          <div class="rating" :aria-label="`${review.rating} out of 5`">
            <span
              v-for="(on, n) in ratingDots(review.rating)"
              :key="n"
              class="rating-dot"
              :class="{ on }"
            />
          </div>

          <p class="body">{{ review.body }}</p>

          <footer class="person">
            <span class="name">{{ review.author_name }}</span>
            <span v-if="review.author_title" class="title mono">{{ review.author_title }}</span>
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
  align-items: end;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.4rem;
}

.page-title {
  font-size: clamp(1.6rem, 4vw, 2.4rem);
  margin: 0;
}

.sub {
  margin: 0 0 0.25rem;
  color: var(--text-dim);
  font-size: 0.78rem;
}

.state {
  margin: 0;
  padding: 1rem 1.1rem;
  color: var(--text-dim);
  font-size: 0.76rem;
}

.state.err {
  color: var(--err);
  background: var(--err-soft);
}

.reviews-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 0.9rem;
}

.review {
  display: flex;
  flex-direction: column;
  min-height: 210px;
  padding: 1.1rem;
}

.rating {
  display: inline-flex;
  gap: 0.22rem;
  width: 78px;
  margin-bottom: 1rem;
}

.rating-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--line-strong);
}

.rating-dot.on {
  background: var(--accent);
}

.body {
  margin: 0;
  color: var(--text);
  line-height: 1.55;
}

.person {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  margin-top: auto;
  padding-top: 1.4rem;
}

.name {
  font-weight: 800;
}

.title {
  color: var(--text-dim);
  font-size: 0.7rem;
}

@media (max-width: 680px) {
  .head {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
