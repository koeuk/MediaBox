export default defineNuxtRouteMiddleware(() => {
  const token = useCookie<string | null>('mediabox_token')
  if (!token.value) {
    return navigateTo('/login')
  }
})
