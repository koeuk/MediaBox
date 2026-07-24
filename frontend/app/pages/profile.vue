<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const { user, fetchUser, updateProfile } = useAuth()

const username = ref('')
const email = ref('')
const profileMsg = ref('')
const profileErr = ref('')
const savingProfile = ref(false)

const currentPassword = ref('')
const newPassword = ref('')
const pwMsg = ref('')
const pwErr = ref('')
const savingPw = ref(false)

onMounted(async () => {
  if (!user.value) await fetchUser()
  username.value = user.value?.username || ''
  email.value = user.value?.email || ''
})

const joined = computed(() =>
  user.value ? new Date(user.value.created_at).toLocaleDateString() : ''
)

async function saveProfile() {
  profileMsg.value = ''
  profileErr.value = ''
  savingProfile.value = true
  try {
    await updateProfile({ username: username.value, email: email.value })
    profileMsg.value = 'Profile updated'
  } catch (e: any) {
    profileErr.value = e?.data?.detail || 'Could not update profile.'
  } finally {
    savingProfile.value = false
  }
}

async function changePassword() {
  pwMsg.value = ''
  pwErr.value = ''
  savingPw.value = true
  try {
    await updateProfile({
      current_password: currentPassword.value,
      new_password: newPassword.value,
    })
    pwMsg.value = 'Password changed'
    currentPassword.value = ''
    newPassword.value = ''
  } catch (e: any) {
    const detail = e?.data?.detail
    pwErr.value = Array.isArray(detail)
      ? 'New password must be at least 6 characters.'
      : detail || 'Could not change password.'
  } finally {
    savingPw.value = false
  }
}
</script>

<template>
  <div>
    <AppNavbar />

    <main class="page">
      <header class="head reveal">
        <h1 class="display page-title">Profile</h1>
        <p class="sub mono">
          {{ user?.email }}
          <span v-if="user?.is_admin" class="admin-tag">admin</span>
          <span class="dot">·</span> joined {{ joined }}
        </p>
      </header>

      <div class="cards">
        <form class="panel card reveal" style="animation-delay: 0.05s" @submit.prevent="saveProfile">
          <h2 class="card-title">Account details</h2>

          <p v-if="profileErr" class="msg err mono">{{ profileErr }}</p>
          <p v-else-if="profileMsg" class="msg ok mono">{{ profileMsg }}</p>

          <label class="label" for="username">Username</label>
          <input id="username" v-model="username" class="input" type="text" required minlength="2" maxlength="80" />

          <label class="label" for="email">Email</label>
          <input id="email" v-model="email" class="input" type="email" required />

          <button class="btn btn-accent" type="submit" :disabled="savingProfile">
            {{ savingProfile ? 'Saving…' : 'Save changes' }}
          </button>
        </form>

        <form class="panel card reveal" style="animation-delay: 0.1s" @submit.prevent="changePassword">
          <h2 class="card-title">Change password</h2>

          <p v-if="pwErr" class="msg err mono">{{ pwErr }}</p>
          <p v-else-if="pwMsg" class="msg ok mono">{{ pwMsg }}</p>

          <label class="label" for="current">Current password</label>
          <PasswordInput id="current" v-model="currentPassword" autocomplete="current-password" placeholder="••••••••" />

          <label class="label" for="new">New password</label>
          <PasswordInput id="new" v-model="newPassword" :minlength="6" autocomplete="new-password" placeholder="Min. 6 characters" />

          <button class="btn btn-accent" type="submit" :disabled="savingPw">
            {{ savingPw ? 'Updating…' : 'Update password' }}
          </button>
        </form>
      </div>
    </main>
  </div>
</template>

<style scoped>
.page {
  max-width: 900px;
  margin: 0 auto;
  padding: 2.2rem 1.5rem 4rem;
}

.head {
  margin-bottom: 1.8rem;
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

.admin-tag {
  margin-left: 0.4rem;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 0.62rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.dot {
  margin: 0 0.35rem;
  color: var(--text-faint);
}

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1.2rem;
}

.card {
  padding: 1.6rem;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  box-shadow: var(--shadow);
}

.card-title {
  margin: 0 0 0.6rem;
  font-size: 1rem;
  font-weight: 600;
}

.card .btn {
  margin-top: 0.8rem;
  align-self: flex-start;
}

.msg {
  margin: 0;
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
</style>
