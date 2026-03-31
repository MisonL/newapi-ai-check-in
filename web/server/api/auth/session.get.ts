import { isSessionValid, sessionCookieName } from '../../utils/auth'

export default defineEventHandler((event) => {
  const config = useRuntimeConfig(event)
  const value = getCookie(event, sessionCookieName())
  return { authenticated: isSessionValid(value, config.sessionSecret) }
})
