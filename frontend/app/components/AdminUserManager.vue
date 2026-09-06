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

function expiryLabel(u: AdminUser) {
  if (!u.premium_until) return null
  return new Date(u.premium_until).toLocaleDateString()
}

const rows = computed(() => props.users)
const editingId = ref<number | null>(null)
const pendingDelete = ref<AdminUser | null>(null)
/** Set while a password change waits on the confirm dialog. */
const pendingPassword = ref<AdminUser | null>(null)
const busyId = ref<number | null>(null)
const error = ref('')
const notice = ref('')

const draft = reactive({ username: '', email: '', is_admin: false, new_password: '' })

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
  editingId.value = u.id
  draft.username = u.username
  draft.email = u.email
  draft.is_admin = u.is_admin
  // never prefilled — the current password is not knowable, and a blank field
  // is what "leave it alone" looks like
  draft.new_password = ''
}

function cancelEdit() {
  editingId.value = null
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
async function applyEdit(u: AdminUser, withPassword: boolean) {
  const body: Record<string, unknown> = {
    username: draft.username.trim(),
    email: draft.email.trim(),
    is_admin: draft.is_admin,
  }
  if (withPassword) body.new_password = draft.new_password
  const ok = await patch(
    u,
    body,
    withPassword ? 'Account updated and password reset' : 'Account updated'
  )
  if (ok) {
    editingId.value = null
    draft.new_password = ''
  }
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
  // Resetting someone's password locks them out of the one they know, so it
  // asks first. A plain rename is reversible and saves straight through.
  if (draft.new_password) {
    if (draft.new_password.length < 6) {
      error.value = 'New password must be at least 6 characters.'
      return
    }
    pendingPassword.value = u
    return
  }
  return applyEdit(u, false)
}

function confirmPassword() {
  const u = pendingPassword.value
  pendingPassword.value = null
  if (u) applyEdit(u, true)
}

function toggleSuspend(u: AdminUser) {
  return patch(
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
            <th>Role</th>
            <th class="num">Downloads</th>
            <th class="num">Storage</th>
            <th>Joined</th>
            <th class="actions-col">Actions</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="u in rows" :key="u.id">
          <tr :class="{ suspended: u.is_suspended }">
            <!-- editing swaps the first three cells for inputs, so the row keeps
                 its place in the table instead of opening a dialog -->
            <template v-if="editingId === u.id">
              <td><input v-model="draft.username" class="input cell-input" maxlength="80" /></td>
              <td><input v-model="draft.email" class="input cell-input" type="email" /></td>
              <td>
                <label class="role-toggle">
                  <input v-model="draft.is_admin" type="checkbox" :disabled="isSelf(u)" />
                  <span>admin</span>
                </label>

              </td>
            </template>
            <template v-else>
              <td>
                {{ u.username }}
                <span v-if="isSelf(u)" class="you mono">you</span>
              </td>
              <td class="mono dim">{{ u.email }}</td>
              <td>
                <span v-if="u.is_admin" class="badge badge-downloading">admin</span>
                <span v-else class="dim">member</span>
                <span
                  v-if="u.is_premium"
                  class="badge badge-completed paid-badge"
                  :title="`Paid until ${expiryLabel(u)}`"
                >paid · {{ expiryLabel(u) }}</span>
              </td>
            </template>

            <td class="num mono">{{ u.download_count }}</td>
            <td class="num mono">{{ formatBytes(u.bytes_stored) }}</td>
            <td class="dim">
              <span v-if="u.is_suspended" class="badge badge-failed">suspended</span>
              <span v-else>{{ formatDate(u.created_at) }}</span>
            </td>

            <td class="actions-col">
              <div class="actions">
                <template v-if="editingId === u.id">
                  <button class="link-btn" :disabled="busyId === u.id" @click="saveEdit(u)">
                    {{ busyId === u.id ? 'Saving…' : 'Save' }}
                  </button>
                  <button class="link-btn dim" @click="cancelEdit">Cancel</button>
                </template>
                <template v-else>
                  <button class="link-btn" :disabled="busyId === u.id" @click="startEdit(u)">
                    Edit
                  </button>
                  <button
                    v-if="!isSelf(u)"
                    class="link-btn"
                    :disabled="busyId === u.id"
                    @click="toggleSuspend(u)"
                  >
                    {{ u.is_suspended ? 'Restore' : 'Suspend' }}
                  </button>
                  <select
                    class="plan-select mono"
                    :disabled="busyId === u.id"
                    :aria-label="`Give ${u.username} a plan`"
                    @change="setPlan(u, ($event.target as HTMLSelectElement).value); ($event.target as HTMLSelectElement).value = ''"
                  >
                    <option value="" disabled selected>
                      {{ u.is_premium ? 'Extend…' : 'Give plan…' }}
                    </option>
                    <option v-for="p in plans" :key="p.code" :value="p.code">
                      +{{ p.label }}
                    </option>
                    <option v-if="u.is_premium" value="">End plan</option>
                  </select>
                  <button
                    v-if="!isSelf(u)"
                    class="link-btn danger"
                    :disabled="busyId === u.id"
                    @click="pendingDelete = u"
                  >
                    Delete
                  </button>
                </template>
              </div>
            </td>
          </tr>

          <!-- password gets its own row: the columns above are too narrow for
               it, and it is optional, so it needs room to say so -->
          <tr v-if="editingId === u.id" class="pw-row">
            <td :colspan="7">
              <label class="pw-label" :for="`pw-${u.id}`">
                Reset password
                <span class="pw-hint">optional — leave blank to keep the current one</span>
              </label>
              <PasswordInput
                :id="`pw-${u.id}`"
                v-model="draft.new_password"
                :minlength="6"
                autocomplete="new-password"
                placeholder="Min. 6 characters"
                class="pw-input"
              />
            </td>
          </tr>
          </template>
        </tbody>
      </table>
    </div>

    <ConfirmDialog
      :open="!!pendingPassword"
      title="Reset this password?"
      :message="`“${pendingPassword?.username}” will be signed out of the password they know and must use the new one. They are not notified — you will need to pass it on yourself.`"
      confirm-label="Reset password"
      @confirm="confirmPassword"
      @cancel="pendingPassword = null"
    />

    <ConfirmDialog
      :open="!!pendingDelete"
      title="Delete this account?"
      :message="`“${pendingDelete?.username}” and all ${pendingDelete?.download_count ?? 0} of their downloads will be permanently removed.`"
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

/* a suspended account should read as switched-off at a glance */
tr.suspended td {
  opacity: 0.5;
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
  gap: 0.75rem;
}

.link-btn {
  border: none;
  background: none;
  padding: 0;
  color: var(--accent);
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  cursor: pointer;
}

.link-btn:hover:not(:disabled) {
  text-decoration: underline;
}

.link-btn:disabled {
  opacity: 0.45;
  cursor: default;
}

.link-btn.danger {
  color: var(--err);
}

.link-btn.dim {
  color: var(--text-dim);
}

/* inputs sit inside table cells, so they lose the usual block sizing */
.cell-input {
  width: 100%;
  min-width: 120px;
  padding: 0.3rem 0.45rem;
  font-size: 0.8rem;
}

.paid-badge {
  margin-left: 0.35rem;
}

/* a native select here rather than AppSelect: it lives inside a dense table
   row and acts as a menu of one-shot actions, not a bound value */
.plan-select {
  border: 1px solid var(--line);
  border-radius: 5px;
  background: var(--bg-raised);
  color: var(--accent);
  font-size: 0.66rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 0.15rem 0.3rem;
  cursor: pointer;
}

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
