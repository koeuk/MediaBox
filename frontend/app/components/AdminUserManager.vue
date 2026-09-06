<script setup lang="ts">
import type { AdminUser, Plan } from '~/types'

/**
 * The admin users table and everything that mutates it.
 *
 * Split out of the admin page for the same reason AdminReviewManager was: the
 * page is a dashboard of read-only panels, and the editing state here (a row
 * being renamed, a pending deletion) has no business leaking into it.
 */
const props = defineProps<{ users: AdminUser[]; currentUserId?: number }>()
const emit = defineEmits<{ changed: [users: AdminUser[]] }>()

const { request } = useApi()
const { open: menuOpen, anchor, menu, pos, placed, toggle, close: closeMenu } = usePopMenu()

/** Which row's menu is showing — usePopMenu only tracks open/closed. */
const menuFor = ref<AdminUser | null>(null)

function openMenu(event: MouseEvent, u: AdminUser) {
  // Every row renders the same button, so a template `ref` here would collect
  // them into an array and positioning would read the wrong element (or none).
  // The clicked button is the anchor.
  const sameRow = menuFor.value?.id === u.id
  if (menuOpen.value && !sameRow) closeMenu()
  menuFor.value = u
  anchor.value = event.currentTarget as HTMLElement
  toggle()
}

/** Run an action and shut the menu, so it never lingers over the result. */
function pick(fn: () => void) {
  closeMenu()
  fn()
}

// plan codes for the grant dropdown; prices are managed in AdminPlanManager
const plans = ref<Plan[]>([])
onMounted(async () => {
  try {
    plans.value = await request<Plan[]>('/admin/plans')
  } catch {
    // the grant control just stays empty — not worth an error banner here
  }
})

/** Grant or extend a subscription. '' ends it immediately. */
async function setPlan(u: AdminUser, code: string) {
  if (!code && !u.is_premium) return
  await patch(
    u,
    { plan: code },
    code ? `${u.username} extended` : `${u.username} downgraded`
  )
}

/**
 * Deleting an empty account is a small mistake; deleting one with files, or a
 * subscription someone paid for, is not recoverable. Those get the stricter
 * confirmation where the username has to be typed out.
 */
const deleteNeedsTyping = computed(() => {
  const u = pendingDelete.value
  // `premium_until` rather than `is_premium`: a lapsed plan still means money
  // changed hands, and that history goes too
  return !!u && (u.download_count > 0 || u.bytes_stored > 0 || !!u.premium_until)
})

/** Spells out what is actually being destroyed, rather than just "are you sure". */
const deleteHint = computed(() => {
  const u = pendingDelete.value
  if (!u) return ''
  const parts: string[] = []
  if (u.download_count > 0) {
    parts.push(`${u.download_count} download${u.download_count === 1 ? '' : 's'}`)
  }
  if (u.bytes_stored > 0) parts.push(formatBytes(u.bytes_stored))
  if (u.premium_until) {
    parts.push(
      u.is_premium ? `a paid plan running to ${expiryLabel(u)}` : 'a past paid plan'
    )
  }
  return parts.length ? `This account has ${parts.join(' · ')}. None of it can be recovered.` : ''
})

function expiryLabel(u: AdminUser) {
  if (!u.premium_until) return null
  return new Date(u.premium_until).toLocaleDateString()
}

const rows = computed(() => props.users)
/** The account open in the edit dialog, or null when it is closed. */
const editing = ref<AdminUser | null>(null)
const pendingDelete = ref<AdminUser | null>(null)
/** Set while a suspend/restore waits on its confirm dialog. */
const pendingSuspend = ref<AdminUser | null>(null)
/** Whose password is being changed — its own flow, separate from Edit. */
const pwTarget = ref<AdminUser | null>(null)
const pwValue = ref('')
const pwError = ref('')
/** Set while that password change waits on its confirm dialog. */
const pendingPassword = ref<AdminUser | null>(null)
const busyId = ref<number | null>(null)
const error = ref('')
const notice = ref('')

const draft = reactive({ username: '', email: '', is_admin: false })

let noticeTimer: ReturnType<typeof setTimeout> | undefined
function flash(msg: string) {
  notice.value = msg
  clearTimeout(noticeTimer)
  noticeTimer = setTimeout(() => (notice.value = ''), 3000)
}

/** Your own row is guarded server-side too — this just hides the buttons that
 *  would only come back as an error. */
function isSelf(u: AdminUser) {
  return u.id === props.currentUserId
}

function startEdit(u: AdminUser) {
  error.value = ''
  editing.value = u
  draft.username = u.username
  draft.email = u.email
  draft.is_admin = u.is_admin
  // never prefilled — the current password is not knowable, and a blank field
  // is what "leave it alone" looks like
}

function cancelEdit() {
  editing.value = null
  error.value = ''
}

/** Replace one row in place, so sort order and the rest of the table hold. */
function merge(updated: AdminUser) {
  emit('changed', rows.value.map((u) => (u.id === updated.id ? updated : u)))
}

async function patch(u: AdminUser, body: Record<string, unknown>, done: string) {
  error.value = ''
  busyId.value = u.id
  try {
    const updated = await request<AdminUser>(`/admin/users/${u.id}`, {
      method: 'PATCH',
      body,
    })
    merge(updated)
    flash(done)
    return true
  } catch (e) {
    error.value = errorMessage(e, 'Could not update that account.')
    return false
  } finally {
    busyId.value = null
  }
}

/** Send the edit. Password is included only once confirmed. */
async function applyEdit(u: AdminUser) {
  const ok = await patch(
    u,
    {
      username: draft.username.trim(),
      email: draft.email.trim(),
      is_admin: draft.is_admin,
    },
    'Account updated'
  )
  if (ok) editing.value = null
}

function saveEdit(u: AdminUser) {
  error.value = ''
  if (draft.username.trim().length < 2) {
    error.value = 'Username must be at least 2 characters.'
    return
  }
  if (!draft.email.trim()) {
    error.value = 'Email cannot be blank.'
    return
  }
  return applyEdit(u)
}

/** Open the password flow. Kept apart from Edit so a rename cannot quietly
 *  reset someone's password, and so the confirm step only guards the thing
 *  that actually needs guarding. */
function startPassword(u: AdminUser) {
  pwTarget.value = u
  pwValue.value = ''
  pwError.value = ''
}

function submitPassword() {
  pwError.value = ''
  if (pwValue.value.length < 6) {
    pwError.value = 'New password must be at least 6 characters.'
    return
  }
  pendingPassword.value = pwTarget.value
}

async function applyPassword() {
  const u = pendingPassword.value
  pendingPassword.value = null
  if (!u) return
  const ok = await patch(u, { new_password: pwValue.value }, 'Password changed')
  if (ok) {
    pwTarget.value = null
    pwValue.value = ''
  }
}

function confirmSuspend() {
  const u = pendingSuspend.value
  pendingSuspend.value = null
  if (!u) return
  patch(
    u,
    { is_suspended: !u.is_suspended },
    u.is_suspended ? 'Account restored' : 'Account suspended'
  )
}

async function confirmDelete() {
  const u = pendingDelete.value
  if (!u) return
  pendingDelete.value = null
  error.value = ''
  busyId.value = u.id
  try {
    await request(`/admin/users/${u.id}`, { method: 'DELETE' })
    emit('changed', rows.value.filter((r) => r.id !== u.id))
    flash(`${u.username} deleted`)
  } catch (e) {
    error.value = errorMessage(e, 'Could not delete that account.')
  } finally {
    busyId.value = null
  }
}
</script>

<template>
  <section class="panel table-panel">
    <h2 class="label table-title">Users</h2>

    <p v-if="error" class="msg err mono">{{ error }}</p>
    <p v-else-if="notice" class="msg ok mono">{{ notice }}</p>

    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>User</th>
            <th>Email</th>
            <th>Status</th>
            <th class="num">Downloads</th>
            <th class="num">Storage</th>
            <th class="joined-col">Joined</th>
            <th class="actions-col">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in rows" :key="u.id" :class="{ suspended: u.is_suspended }">
              <td>
                {{ u.username }}
                <span v-if="isSelf(u)" class="you mono">you</span>
              </td>
              <td class="mono dim">{{ u.email }}</td>
              <td>
                <div class="chips">
                  <span v-if="u.is_admin" class="badge badge-downloading">admin</span>
                  <span v-else class="badge badge-member">member</span>
                  <span
                    v-if="u.is_premium"
                    class="badge badge-completed"
                    :title="`Paid until ${expiryLabel(u)}`"
                  >paid · {{ expiryLabel(u) }}</span>
                  <span v-if="u.is_suspended" class="badge badge-failed">suspended</span>
                </div>
              </td>

            <td class="num mono">{{ u.download_count }}</td>
            <td class="num mono">{{ formatBytes(u.bytes_stored) }}</td>
            <td class="dim joined-col">{{ formatDate(u.created_at) }}</td>

            <td class="actions-col">
              <button
                class="btn btn-ghost btn-icon kebab"
                :class="{ on: menuOpen && menuFor?.id === u.id }"
                :disabled="busyId === u.id"
                title="Account actions"
                :aria-label="`Actions for ${u.username}`"
                aria-haspopup="menu"
                :aria-expanded="menuOpen && menuFor?.id === u.id"
                @click.stop="openMenu($event, u)"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <circle cx="12" cy="5" r="1.8" />
                  <circle cx="12" cy="12" r="1.8" />
                  <circle cx="12" cy="19" r="1.8" />
                </svg>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- editing is a dialog rather than inline inputs: the row is too narrow
         for an email field plus a password reset, and a half-edited row that
         scrolls out of view is easy to lose track of -->
    <Teleport to="body">
      <Transition name="dialog">
        <div v-if="editing" class="overlay" @click.self="cancelEdit">
          <form
            class="dialog panel"
            role="dialog"
            aria-modal="true"
            aria-label="Edit account"
            @submit.prevent="saveEdit(editing)"
          >
            <h3 class="dialog-title">Edit account</h3>
            <p class="dialog-message">{{ editing.email }}</p>

            <p v-if="error" class="msg err mono dialog-msg">{{ error }}</p>

            <label class="label" for="edit-username">Username</label>
            <input
              id="edit-username"
              v-model="draft.username"
              class="input"
              maxlength="80"
              autocomplete="off"
            />

            <label class="label" for="edit-email">Email</label>
            <input id="edit-email" v-model="draft.email" class="input" type="email" autocomplete="off" />

            <label class="role-toggle edit-role">
              <input v-model="draft.is_admin" type="checkbox" :disabled="isSelf(editing)" />
              <span>Administrator</span>
            </label>

            <div class="dialog-actions">
              <button type="button" class="btn btn-ghost" @click="cancelEdit">Cancel</button>
              <button type="submit" class="btn btn-accent" :disabled="busyId === editing.id">
                {{ busyId === editing.id ? 'Saving…' : 'Save changes' }}
              </button>
            </div>
          </form>
        </div>
      </Transition>
    </Teleport>

    <!-- teleported: the table scrolls horizontally and would clip this -->
    <Teleport to="body">
      <Transition name="pop">
        <div
          v-if="menuOpen && menuFor"
          ref="menu"
          class="pop-menu panel"
          role="menu"
          :style="{ top: `${pos.top}px`, left: `${pos.left}px`, visibility: placed ? 'visible' : 'hidden' }"
          @click.stop
        >
          <button class="pop-item" role="menuitem" @click="pick(() => startEdit(menuFor!))">
            Edit account
          </button>

          <button
            v-if="!isSelf(menuFor)"
            class="pop-item"
            role="menuitem"
            @click="pick(() => startPassword(menuFor!))"
          >
            Change password
          </button>

          <div class="pop-sep" />

          <p class="pop-label mono">{{ menuFor.is_premium ? 'Extend plan' : 'Give plan' }}</p>
          <button
            v-for="p in plans"
            :key="p.code"
            class="pop-item"
            role="menuitem"
            @click="pick(() => setPlan(menuFor!, p.code))"
          >
            +{{ p.label }}
          </button>
          <button
            v-if="menuFor.premium_until"
            class="pop-item"
            role="menuitem"
            @click="pick(() => setPlan(menuFor!, ''))"
          >
            End plan
          </button>

          <template v-if="!isSelf(menuFor)">
            <div class="pop-sep" />
            <button class="pop-item" role="menuitem" @click="pick(() => (pendingSuspend = menuFor))">
              {{ menuFor.is_suspended ? 'Restore access' : 'Suspend' }}
            </button>
            <button
              class="pop-item danger"
              role="menuitem"
              @click="pick(() => (pendingDelete = menuFor))"
            >
              Delete account
            </button>
          </template>
        </div>
      </Transition>
    </Teleport>

    <Teleport to="body">
      <Transition name="dialog">
        <div v-if="pwTarget" class="overlay" @click.self="pwTarget = null">
          <form
            class="dialog panel"
            role="dialog"
            aria-modal="true"
            aria-label="Change password"
            @submit.prevent="submitPassword"
          >
            <h3 class="dialog-title">Change password</h3>
            <p class="dialog-message">
              Set a new password for “{{ pwTarget.username }}”. They are not
              notified — pass it on yourself.
            </p>

            <p v-if="pwError" class="msg err mono pw-msg">{{ pwError }}</p>

            <label class="label" for="new-password">New password</label>
            <PasswordInput
              id="new-password"
              v-model="pwValue"
              :minlength="6"
              autocomplete="new-password"
              placeholder="Min. 6 characters"
            />

            <div class="dialog-actions">
              <button type="button" class="btn btn-ghost" @click="pwTarget = null">
                Cancel
              </button>
              <button type="submit" class="btn btn-accent" :disabled="busyId === pwTarget.id">
                {{ busyId === pwTarget.id ? 'Saving…' : 'Change password' }}
              </button>
            </div>
          </form>
        </div>
      </Transition>
    </Teleport>

    <ConfirmDialog
      :open="!!pendingSuspend"
      :title="pendingSuspend?.is_suspended ? 'Restore this account?' : 'Suspend this account?'"
      :message="pendingSuspend?.is_suspended
        ? `“${pendingSuspend?.username}” will be able to sign in and use the API again.`
        : `“${pendingSuspend?.username}” keeps their downloads but cannot sign in or use the API until you restore them.`"
      :confirm-label="pendingSuspend?.is_suspended ? 'Restore' : 'Suspend'"
      :danger="!pendingSuspend?.is_suspended"
      @confirm="confirmSuspend"
      @cancel="pendingSuspend = null"
    />

    <ConfirmDialog
      :open="!!pendingPassword"
      title="Reset this password?"
      :message="`“${pendingPassword?.username}” will be signed out of the password they know and must use the new one. They are not notified — you will need to pass it on yourself.`"
      confirm-label="Reset password"
      @confirm="applyPassword"
      @cancel="pendingPassword = null"
    />

    <ConfirmDialog
      :open="!!pendingDelete"
      title="Delete this account?"
      :message="`“${pendingDelete?.username}” and all ${pendingDelete?.download_count ?? 0} of their downloads will be permanently removed.`"
      :require-text="deleteNeedsTyping ? pendingDelete?.username : undefined"
      :require-hint="deleteNeedsTyping ? deleteHint : undefined"
      confirm-label="Delete"
      danger
      @confirm="confirmDelete"
      @cancel="pendingDelete = null"
    />
  </section>
</template>

<style scoped>
/* Table shell copied from the admin page rather than shared: these are scoped
   styles there, so moving the markup into this component moved it out of their
   reach. Kept identical so the two tables on the page still line up. */
.table-panel {
  margin-bottom: 1.4rem;
  overflow: hidden;
}

.table-title {
  margin: 0;
  padding: 0.9rem 1.2rem 0;
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
  padding: 0.55rem 1.2rem;
  border-top: 1px solid var(--line);
}

th.num,
td.num {
  text-align: right;
}

.dim {
  color: var(--text-dim);
}

/* a suspended account should read as switched-off at a glance, but its
   actions must stay legible enough to click Restore */
tr.suspended td {
  opacity: 0.62;
}

tr.suspended .kebab.on {
  color: var(--text);
  background: var(--surface-hover);
}

/* section heading inside the menu, e.g. "Give plan" */
.pop-label {
  margin: 0.2rem 0 0.15rem;
  padding: 0 0.6rem;
  font-size: 0.58rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--text-faint);
}

.actions-col {
  opacity: 1;
}

tbody tr:hover td {
  background: var(--surface-hover);
}

/* one chip row, so a paid or suspended account keeps the row height of a
   plain one instead of wrapping onto a second line */
.chips {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  white-space: nowrap;
}

/* member is a chip too — a bare word beside a badge read as a missing value */
.badge-member {
  background: var(--bg-raised);
  color: var(--text-faint);
}

/* short values that wrapped mid-cell at narrow widths */
td.num,
.joined-col {
  white-space: nowrap;
}

.you {
  margin-left: 0.4rem;
  font-size: 0.6rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-faint);
}

.actions-col {
  text-align: right;
  white-space: nowrap;
}

.actions {
  display: inline-flex;
  align-items: center;
  gap: 0.7rem;
}

/* dialog shell copied from ConfirmDialog for the same reason the table shell
   was copied from the admin page: those styles are scoped to that component */
.overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: grid;
  place-items: center;
  padding: 1.5rem;
  background: color-mix(in srgb, var(--bg) 65%, transparent);
  backdrop-filter: blur(4px);
}

.dialog {
  width: 100%;
  max-width: 400px;
  padding: 1.4rem 1.5rem 1.3rem;
  box-shadow: var(--shadow);
}

.dialog-title {
  margin: 0 0 0.3rem;
  font-size: 1.05rem;
  font-weight: 600;
}

.dialog-message {
  margin: 0 0 1rem;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.78rem;
  color: var(--text-dim);
  overflow-wrap: anywhere;
}

.dialog .label {
  display: block;
  margin: 0.9rem 0 0.3rem;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1.3rem;
}

/* the password confirm opens on top of this one */
.dialog-msg {
  margin: 0;
}

.edit-role {
  margin-top: 0.9rem;
}

/* a native select here rather than AppSelect: it lives inside a dense table
   row and acts as a menu of one-shot actions, not a bound value */

.role-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.72rem;
  color: var(--text-dim);
  cursor: pointer;
}

.pw-row td {
  padding-top: 0.15rem;
  padding-bottom: 0.8rem;
  border-top: none;
}

.pw-label {
  display: block;
  margin-bottom: 0.3rem;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.62rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--text-faint);
}

.pw-msg {
  margin: 0 0 0.2rem;
}

.pw-hint {
  margin-left: 0.5rem;
  text-transform: none;
  letter-spacing: 0;
  color: var(--text-dim);
}

.pw-input {
  max-width: 280px;
}

.msg {
  margin: 0.8rem 1.2rem 0;
  padding: 0.5rem 0.7rem;
  border-radius: 6px;
  font-size: 0.74rem;
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
