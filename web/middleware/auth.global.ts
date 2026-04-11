export default defineNuxtRouteMiddleware(async (to) => {
  const authState = useAuthState()
  const authExpiresAt = useAuthExpiresAt()
  if (to.path === '/login') {
    return
  }
  if (
    import.meta.client
    && authState.value === true
    && authExpiresAt.value
    && new Date(authExpiresAt.value).getTime() > Date.now()
  ) {
    return
  }
  const session = await $fetch<{ authenticated: boolean, expires_at: string | null }>('/api/auth/session', {
    headers: import.meta.server ? useRequestHeaders(['cookie']) : undefined
  })
  authState.value = session.authenticated
  authExpiresAt.value = session.expires_at
  if (!session.authenticated) {
    return navigateTo('/login')
  }
})
