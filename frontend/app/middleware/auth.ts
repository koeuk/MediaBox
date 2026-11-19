export default defineNuxtRouteMiddleware((to) => {
  const token = useCookie<string | null>('mediabox_token')
  if (!token.value) {
    return navigateTo(to.path === '/' ? '/free' : '/login')
  }
})
