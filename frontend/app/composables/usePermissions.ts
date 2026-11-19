import type { AdminUser, User } from '~/types'

export const adminPermissionSections = [
  { key: 'dashboard', label: 'Dashboard', actions: ['view'] },
  { key: 'downloads', label: 'All downloads (admin)', actions: ['view'] },
  { key: 'feedback', label: 'Feedback (admin)', actions: ['view', 'create', 'edit', 'delete'] },
  { key: 'users', label: 'Users', actions: ['view', 'create', 'edit', 'delete'] },
  { key: 'plans', label: 'Plans', actions: ['view', 'create', 'edit', 'delete'] },
  { key: 'payments', label: 'Payments', actions: ['view', 'edit'] },
] as const

export const accountPermissionSections = [
  { key: 'media', label: 'Downloads (own media)', actions: ['view', 'create', 'edit', 'delete'] },
  { key: 'categories', label: 'Categories (own)', actions: ['view', 'create', 'edit', 'delete'] },
  { key: 'public_feedback', label: 'Feedback (public)', actions: ['view', 'create'] },
] as const

export const permissionSections = [...accountPermissionSections, ...adminPermissionSections]

export function defaultPermission(permission: string, defaults: Record<string, boolean> = {}, admin = false): boolean {
  return admin || (defaults[permission] ?? accountPermissionSections.some(s => s.key === permission.split('.')[0]))
}

export function hasPermission(user: User | AdminUser | null, permission: string): boolean {
  if (!user) return false
  const [section, action] = permission.split('.')
  const allowed = user.permissions?.[permission] ?? defaultPermission(permission, user.default_permissions, user.is_admin)
  return allowed && (action === 'view' || (user.permissions?.[`${section}.view`] ?? defaultPermission(`${section}.view`, user.default_permissions, user.is_admin)))
}

export function usePermissions() {
  const { user } = useAuth()
  const can = (permission: string) => hasPermission(user.value, permission)
  const fullAdmin = computed(() => !!user.value?.is_admin && user.value.permissions == null)
  const canAccessAdmin = computed(() => adminPermissionSections.some(s => can(`${s.key}.view`)))
  return { can, fullAdmin, canAccessAdmin }
}
