export default defineNuxtRouteMiddleware(async (to) => {
  if (to.path === '/login') {
    return
  }
  const session = await $fetch<{ authenticated: boolean }>('/api/auth/session', {
    headers: import.meta.server ? useRequestHeaders(['cookie']) : undefined
  })
  if (!session.authenticated) {
    return navigateTo('/login')
  }
})
