import type { AdminUser, User } from '~/types'

export const permissionSections = [
  { key: 'dashboard', label: 'Dashboard', actions: ['view'] },
  { key: 'downloads', label: 'Downloads', actions: ['view'] },
  { key: 'feedback', label: 'Feedback', actions: ['view', 'create', 'edit', 'delete'] },
  { key: 'users', label: 'Users', actions: ['view', 'edit', 'delete'] },
  { key: 'plans', label: 'Plans', actions: ['view', 'edit'] },
  { key: 'payments', label: 'Payments', actions: ['view', 'edit'] },
] as const

export function hasPermission(user: User | AdminUser | null, permission: string): boolean {
  if (!user) return false
  const [section, action] = permission.split('.')
  const allowed = user.permissions?.[permission] ?? user.default_permissions?.[permission] ?? user.is_admin
  return allowed && (action === 'view' || (user.permissions?.[`${section}.view`] ?? user.default_permissions?.[`${section}.view`] ?? user.is_admin))
}

export function usePermissions() {
  const { user } = useAuth()
  const can = (permission: string) => hasPermission(user.value, permission)
  const fullAdmin = computed(() => !!user.value?.is_admin && user.value.permissions == null)
  const canAccessAdmin = computed(() => permissionSections.some(s => can(`${s.key}.view`)))
  return { can, fullAdmin, canAccessAdmin }
}
