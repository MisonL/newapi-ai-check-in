import { createHmac, timingSafeEqual } from 'node:crypto'
import type { H3Event } from 'h3'

const COOKIE_NAME = 'control_plane_session'

function buildToken(secret: string) {
  return createHmac('sha256', secret).update('authorized').digest('hex')
}

export function sessionCookieName() {
  return COOKIE_NAME
}

export function issueSession(secret: string) {
  return buildToken(secret)
}

export function isSessionValid(value: string | undefined, secret: string) {
  if (!value) {
    return false
  }
  const expected = Buffer.from(buildToken(secret))
  const actual = Buffer.from(value)
  if (expected.length !== actual.length) {
    return false
  }
  return timingSafeEqual(expected, actual)
}

export function assertAuthenticated(event: H3Event) {
  const config = useRuntimeConfig(event)
  const value = getCookie(event, sessionCookieName())
  if (!isSessionValid(value, config.sessionSecret)) {
    throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
  }
}
