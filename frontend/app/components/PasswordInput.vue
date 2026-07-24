<script setup lang="ts">
defineProps<{
  id?: string
  placeholder?: string
  autocomplete?: string
  minlength?: number
}>()
const model = defineModel<string>({ required: true })
const show = ref(false)
</script>

<template>
  <div class="pw-wrap">
    <input
      :id="id"
      v-model="model"
      class="input pw-input"
      :type="show ? 'text' : 'password'"
      required
      :minlength="minlength"
      :autocomplete="autocomplete"
      :placeholder="placeholder"
    />
    <button
      type="button"
      class="pw-toggle"
      :title="show ? 'Hide password' : 'Show password'"
      :aria-label="show ? 'Hide password' : 'Show password'"
      @click="show = !show"
    >
      <svg v-if="show" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
        <line x1="1" y1="1" x2="23" y2="23" />
      </svg>
      <svg v-else width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8Z" />
        <circle cx="12" cy="12" r="3" />
      </svg>
    </button>
  </div>
</template>

<style scoped>
.pw-wrap {
  position: relative;
}

.pw-input {
  width: 100%;
  padding-right: 2.6rem;
}

.pw-toggle {
  position: absolute;
  top: 50%;
  right: 0.45rem;
  transform: translateY(-50%);
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 5px;
  background: transparent;
  color: var(--text-faint);
  cursor: pointer;
  transition: color 0.15s, background 0.15s;
}

.pw-toggle:hover {
  color: var(--text);
  background: var(--surface-hover);
}
</style>
