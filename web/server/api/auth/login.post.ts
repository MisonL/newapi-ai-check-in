import { controlPlaneUrl } from '../../utils/controlPlane'
import { issueSession, sessionCookieName, sessionExpiresAt } from '../../utils/auth'

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  const sessionMaxAgeSeconds = Number(config.sessionMaxAgeSeconds)
  const body = await readBody<{ password?: string }>(event)
  if (!body.password) {
    throw createError({ statusCode: 400, statusMessage: 'Password is required' })
  }
  try {
    await $fetch(controlPlaneUrl(config, '/api/system/login'), {
      method: 'POST',
      body: { password: body.password }
    })
  } catch (error: any) {
    throw createError({
      statusCode: error?.response?.status || 500,
      statusMessage: error?.response?._data?.detail || error?.message || 'Login failed'
    })
  }
  const sessionToken = issueSession(config.sessionSecret, sessionMaxAgeSeconds)
  setCookie(event, sessionCookieName(), sessionToken, {
    httpOnly: true,
    maxAge: sessionMaxAgeSeconds,
    sameSite: 'lax',
    path: '/'
  })
  return {
    authenticated: true,
    expires_at: sessionExpiresAt(sessionToken, config.sessionSecret),
  }
})
