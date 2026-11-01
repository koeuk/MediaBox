<script setup lang="ts">
import type { SaveMode } from '~/composables/useSavePrefs'

definePageMeta({ middleware: 'auth' })

const { user, fetchUser, updateProfile, uploadAvatar, removeAvatar, setHiddenPassword, removeHiddenPassword } = useAuth()
const { src: avatarSrc, initials } = useAvatar()
const { markUnlocked, lock: lockHidden } = useHiddenLock()

const photoInput = ref<HTMLInputElement>()
const photoBusy = ref(false)
const photoErr = ref('')

async function onPhotoPicked(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  // reset first, so picking the same file twice still fires a change event
  input.value = ''
  if (!file) return

  photoErr.value = ''
  photoBusy.value = true
  try {
    await uploadAvatar(file)
  } catch (err) {
    photoErr.value = errorMessage(err, 'Could not upload that image.')
  } finally {
    photoBusy.value = false
  }
}

async function clearPhoto() {
  photoErr.value = ''
  photoBusy.value = true
  try {
    await removeAvatar()
  } catch (err) {
    photoErr.value = errorMessage(err, 'Could not remove the photo.')
  } finally {
    photoBusy.value = false
  }
}

/** Which panel the tabs are showing. Mirrored into `?tab=` so a reload — or a
 *  link straight to one section — lands where you expect. */
type ProfileTab = 'account' | 'password' | 'hidden' | 'saving' | 'branding'
const route = useRoute()
const router = useRouter()
const queryTab = route.query.tab as ProfileTab
const tab = ref<ProfileTab>(
  queryTab === 'password' || queryTab === 'hidden' || queryTab === 'saving' || queryTab === 'branding'
    ? queryTab
    : 'account'
)

watch(tab, (value) => {
  router.replace({ query: value === 'account' ? {} : { tab: value } })
})

watch(user, (u) => {
  if (tab.value === 'branding' && !u?.is_admin) {
    tab.value = 'account'
  }
})

const username = ref('')
const email = ref('')
const profileMsg = ref('')
const profileErr = ref('')
const savingProfile = ref(false)

// save-location preference (persisted per browser by useSavePrefs)
const savePrefs = useSavePrefs()
const saveMode = ref<SaveMode>('default')
const savePath = ref('')
const saveMsg = ref('')
const saveErr = ref('')
const pickerSupported = ref(true)

onMounted(() => {
  saveMode.value = savePrefs.mode.value
  savePath.value = savePrefs.customPath.value
  pickerSupported.value = 'showSaveFilePicker' in window
})

function saveSavePrefs() {
  saveMsg.value = ''
  saveErr.value = ''
  if (saveMode.value === 'custom' && !savePath.value.trim().startsWith('/')) {
    saveErr.value = 'Enter an absolute folder path, e.g. /home/you/Videos'
    return
  }
  savePrefs.save(saveMode.value, savePath.value.trim())
  saveMsg.value = 'Save location updated'
}

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
  } catch (e) {
    profileErr.value = errorMessage(e, 'Could not update profile.')
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
  } catch (e) {
    pwErr.value = errorMessage(
      e,
      'Could not change password.',
      'New password must be at least 6 characters.'
    )
  } finally {
    savingPw.value = false
  }
}

// Hidden section password state
const hiddenCurrentPassword = ref('')
const hiddenNewPassword = ref('')
const hiddenConfirmPassword = ref('')
const hiddenRemovePassword = ref('')
const hiddenMsg = ref('')
const hiddenErr = ref('')
const savingHidden = ref(false)
const removingHidden = ref(false)

async function handleSetHiddenPassword() {
  hiddenMsg.value = ''
  hiddenErr.value = ''
  if (!hiddenNewPassword.value) {
    hiddenErr.value = 'Please enter a password'
    return
  }
  if (hiddenNewPassword.value !== hiddenConfirmPassword.value) {
    hiddenErr.value = 'Passwords do not match'
    return
  }
  savingHidden.value = true
  try {
    await setHiddenPassword({
      current_password: user.value?.has_hidden_password ? hiddenCurrentPassword.value : undefined,
      new_password: hiddenNewPassword.value,
    })
    markUnlocked()
    hiddenMsg.value = user.value?.has_hidden_password
      ? 'Hidden password updated'
      : 'Hidden section password set'
    hiddenCurrentPassword.value = ''
    hiddenNewPassword.value = ''
    hiddenConfirmPassword.value = ''
  } catch (e: any) {
    hiddenErr.value = errorMessage(e, 'Could not save hidden password.')
  } finally {
    savingHidden.value = false
  }
}

async function handleRemoveHiddenPassword() {
  hiddenMsg.value = ''
  hiddenErr.value = ''
  if (!hiddenRemovePassword.value) {
    hiddenErr.value = 'Please enter your password to remove protection'
    return
  }
  removingHidden.value = true
  try {
    await removeHiddenPassword(hiddenRemovePassword.value)
    lockHidden()
    hiddenMsg.value = 'Hidden section password protection removed'
    hiddenRemovePassword.value = ''
  } catch (e: any) {
    hiddenErr.value = errorMessage(e, 'Incorrect password. Could not remove protection.')
  } finally {
    removingHidden.value = false
  }
}
</script>

<template>
  <div>
    <AppNavbar />

    <main class="page">
      <header class="head reveal">
        <input ref="photoInput" type="file" accept="image/*" hidden @change="onPhotoPicked" />

        <button
          class="avatar"
          :class="{ busy: photoBusy }"
          :title="user?.has_avatar ? 'Change photo' : 'Upload a photo'"
          :disabled="photoBusy"
          @click="photoInput?.click()"
        >
          <img v-if="avatarSrc" :src="avatarSrc" :alt="user?.username" />
          <span v-else class="initials display">{{ initials }}</span>
          <span class="avatar-hint">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2Z" />
              <circle cx="12" cy="13" r="3.5" />
            </svg>
          </span>
        </button>

        <div class="head-text">
          <h1 class="display page-title">Settings</h1>
          <p class="sub mono">
            {{ user?.email }}
            <span v-if="user?.is_admin" class="admin-tag">admin</span>
            <span class="dot">·</span> joined {{ joined }}
          </p>

          <p v-if="photoErr" class="msg err mono photo-msg">{{ photoErr }}</p>
          <div v-else class="photo-actions">
            <button class="btn btn-ghost photo-btn" :disabled="photoBusy" @click="photoInput?.click()">
              {{ photoBusy ? 'Working…' : user?.has_avatar ? 'Change photo' : 'Upload photo' }}
            </button>
            <button
              v-if="user?.has_avatar"
              class="btn btn-ghost photo-btn"
              :disabled="photoBusy"
              @click="clearPhoto"
            >
              Remove
            </button>
          </div>
        </div>
      </header>

      <div class="filters tabs reveal" role="tablist" aria-label="Settings sections">
        <button
          v-for="t in (['account', 'password', 'hidden', 'saving', ...(user?.is_admin ? ['branding'] : [])] as ProfileTab[])"
          :key="t"
          :id="`tab-${t}`"
          class="filter-btn"
          :class="{ on: tab === t }"
          type="button"
          role="tab"
          :aria-selected="tab === t"
          :aria-controls="`panel-${t}`"
          @click="tab = t"
        >
          {{ t === 'account' ? 'Account details' : t === 'password' ? 'Change password' : t === 'hidden' ? 'Hidden lock' : t === 'saving' ? 'Save location' : 'Branding' }}
        </button>
      </div>

      <div class="cards">
        <form
          v-show="tab === 'account'"
          id="panel-account"
          role="tabpanel"
          aria-labelledby="tab-account"
          class="panel panel-hover card reveal"
          @submit.prevent="saveProfile"
        >
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

        <form
          v-show="tab === 'password'"
          id="panel-password"
          role="tabpanel"
          aria-labelledby="tab-password"
          class="panel panel-hover card reveal"
          @submit.prevent="changePassword"
        >
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

        <div
          v-show="tab === 'hidden'"
          id="panel-hidden"
          role="tabpanel"
          aria-labelledby="tab-hidden"
          class="panel panel-hover card reveal"
        >
          <div class="card-header-row">
            <div>
              <h2 class="card-title">Hidden section lock</h2>
              <p class="save-hint">
                Protect private media items in your Hidden collection with a password.
              </p>
            </div>
            <span
              class="status-badge"
              :class="user?.has_hidden_password ? 'badge-protected' : 'badge-unprotected'"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path v-if="user?.has_hidden_password" d="M7 11V7a5 5 0 0 1 10 0v4" />
                <path v-else d="M7 11V7a5 5 0 0 1 9.9-1" />
              </svg>
              {{ user?.has_hidden_password ? 'Protected' : 'Not protected' }}
            </span>
          </div>

          <p v-if="hiddenErr" class="msg err mono">{{ hiddenErr }}</p>
          <p v-else-if="hiddenMsg" class="msg ok mono">{{ hiddenMsg }}</p>

          <form class="hidden-pw-form" @submit.prevent="handleSetHiddenPassword">
            <h3 class="section-subtitle">
              {{ user?.has_hidden_password ? 'Change hidden password' : 'Set a hidden password' }}
            </h3>

            <template v-if="user?.has_hidden_password">
              <label class="label" for="hidden-current">Current password</label>
              <PasswordInput
                id="hidden-current"
                v-model="hiddenCurrentPassword"
                autocomplete="current-password"
                placeholder="Current hidden or account password"
              />
            </template>

            <label class="label" for="hidden-new">
              {{ user?.has_hidden_password ? 'New password' : 'Password' }}
            </label>
            <PasswordInput
              id="hidden-new"
              v-model="hiddenNewPassword"
              autocomplete="new-password"
              placeholder="Enter password"
            />

            <label class="label" for="hidden-confirm">Confirm password</label>
            <PasswordInput
              id="hidden-confirm"
              v-model="hiddenConfirmPassword"
              autocomplete="new-password"
              placeholder="Confirm password"
            />

            <button class="btn btn-accent" type="submit" :disabled="savingHidden">
              {{ savingHidden ? 'Saving…' : user?.has_hidden_password ? 'Update hidden password' : 'Set hidden password' }}
            </button>
          </form>

          <div v-if="user?.has_hidden_password" class="remove-protection-section">
            <div class="divider" />
            <h3 class="section-subtitle danger-text">Remove password protection</h3>
            <p class="save-hint">
              Turn off password protection to allow direct access to hidden items.
            </p>

            <form class="remove-pw-form" @submit.prevent="handleRemoveHiddenPassword">
              <label class="label" for="hidden-remove">Enter password to remove</label>
              <PasswordInput
                id="hidden-remove"
                v-model="hiddenRemovePassword"
                autocomplete="current-password"
                placeholder="Current hidden or account password"
              />
              <button class="btn btn-danger" type="submit" :disabled="removingHidden || !hiddenRemovePassword">
                {{ removingHidden ? 'Removing…' : 'Remove password protection' }}
              </button>
            </form>
          </div>
        </div>

        <form
          v-show="tab === 'saving'"
          id="panel-saving"
          role="tabpanel"
          aria-labelledby="tab-saving"
          class="panel panel-hover card reveal"
          @submit.prevent="saveSavePrefs"
        >
          <h2 class="card-title">Save location</h2>
          <p class="save-hint">Where files go when you click Save or queue a download.</p>

          <p v-if="saveErr" class="msg err mono">{{ saveErr }}</p>
          <p v-else-if="saveMsg" class="msg ok mono">{{ saveMsg }}</p>

          <label class="save-option" :class="{ on: saveMode === 'default' }">
            <input v-model="saveMode" type="radio" value="default" name="save-mode" />
            <span>
              <strong>Default</strong>
              <small>Files download to your browser's Downloads folder.</small>
            </span>
          </label>

          <label class="save-option" :class="{ on: saveMode === 'custom' }">
            <input v-model="saveMode" type="radio" value="custom" name="save-mode" />
            <span>
              <strong>Custom folder</strong>
              <small>Files are placed straight into a folder you choose below.</small>
            </span>
          </label>

          <input
            v-if="saveMode === 'custom'"
            v-model="savePath"
            class="input mono save-path"
            type="text"
            placeholder="/home/you/Videos"
            spellcheck="false"
          />

          <label class="save-option" :class="{ on: saveMode === 'ask' }">
            <input v-model="saveMode" type="radio" value="ask" name="save-mode" />
            <span>
              <strong>Ask every time</strong>
              <small>
                A save dialog opens on each Save or Download click.
                <template v-if="!pickerSupported"> Not supported by this browser — Chrome or Edge needed.</template>
              </small>
            </span>
          </label>

          <button class="btn btn-accent" type="submit">Save preference</button>
        </form>

        <AdminBranding
          v-if="user?.is_admin"
          v-show="tab === 'branding'"
          id="panel-branding"
          role="tabpanel"
          aria-labelledby="tab-branding"
          class="reveal"
        />
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
  display: flex;
  align-items: center;
  gap: 1.1rem;
  margin-bottom: 1.8rem;
}

.head-text {
  min-width: 0;
}

.avatar {
  position: relative;
  flex: none;
  display: grid;
  place-items: center;
  width: 84px;
  height: 84px;
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--line-strong);
  border-radius: 50%;
  background: var(--bg-raised);
  cursor: pointer;
  transition: border-color 0.15s, opacity 0.15s;
}

.avatar:hover {
  border-color: var(--accent);
}

.avatar.busy {
  opacity: 0.6;
  cursor: progress;
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.initials {
  font-size: 1.6rem;
  color: var(--text-faint);
  letter-spacing: 0.02em;
}

/* the camera badge only appears on hover, so the picture reads cleanly */
.avatar-hint {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: #fff;
  background: color-mix(in srgb, #000 45%, transparent);
  opacity: 0;
  transition: opacity 0.15s;
}

.avatar:hover .avatar-hint {
  opacity: 1;
}

.photo-actions {
  display: flex;
  gap: 0.4rem;
  margin-top: 0.6rem;
}

.photo-btn {
  padding: 0.4rem 0.7rem;
  font-size: 0.68rem;
}

.photo-msg {
  margin-top: 0.6rem;
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

/* the tab bar sits inline rather than stretching, so it reads as a control
   rather than a header rule */
.tabs {
  display: inline-flex;
  margin-bottom: 1.1rem;
}

/* One panel shows at a time, so the old two-column grid is gone. Capped rather
   than filling the 900px page — a login form stretched that wide is unpleasant
   to read and to fill in. */
.cards {
  max-width: 480px;
}

.card {
  padding: 1.6rem;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
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

.save-hint {
  margin: -0.4rem 0 1rem;
  color: var(--text-dim, #9a9a9a);
  font-size: 0.85rem;
}

.save-option {
  display: flex;
  align-items: flex-start;
  gap: 0.7rem;
  padding: 0.75rem 0.9rem;
  margin-bottom: 0.6rem;
  border: 1px solid var(--border, #2c2c2e);
  border-radius: 10px;
  cursor: pointer;
  transition: border-color 0.15s;
}

.save-option.on {
  border-color: var(--accent, #f0a832);
}

.save-option input {
  margin-top: 0.2rem;
  accent-color: var(--accent, #f0a832);
}

.save-option strong {
  display: block;
  font-size: 0.9rem;
}

.save-option small {
  color: var(--text-dim, #9a9a9a);
  font-size: 0.8rem;
}

.save-path {
  margin: -0.2rem 0 0.6rem;
  font-size: 0.85rem;
}

.card-header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.74rem;
  font-weight: 600;
  padding: 0.3rem 0.65rem;
  border-radius: 999px;
  white-space: nowrap;
}

.badge-protected {
  background: color-mix(in srgb, var(--accent) 15%, transparent);
  color: var(--accent);
  border: 1px solid color-mix(in srgb, var(--accent) 30%, transparent);
}

.badge-unprotected {
  background: var(--surface, #1e1e20);
  color: var(--text-dim, #9a9a9a);
  border: 1px solid var(--border, #2c2c2e);
}

.section-subtitle {
  margin: 1.1rem 0 0.4rem;
  font-size: 0.92rem;
  font-weight: 600;
}

.danger-text {
  color: var(--err);
}

.divider {
  height: 1px;
  background: var(--border, #2c2c2e);
  margin: 1.6rem 0 1rem;
}

.hidden-pw-form,
.remove-pw-form {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.btn-danger {
  background: var(--err);
  border-color: var(--err);
  color: #fff;
}

.btn-danger:hover:not(:disabled) {
  filter: brightness(1.12);
}
</style>\n