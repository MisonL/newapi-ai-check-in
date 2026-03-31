import { controlPlaneUrl } from '../../utils/controlPlane'
import { issueSession, sessionCookieName } from '../../utils/auth'

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
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
  setCookie(event, sessionCookieName(), issueSession(config.sessionSecret), {
    httpOnly: true,
    sameSite: 'lax',
    path: '/'
  })
  return { authenticated: true }
})
