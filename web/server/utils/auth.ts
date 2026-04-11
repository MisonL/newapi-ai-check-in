import { createHmac, randomBytes, timingSafeEqual } from 'node:crypto'
import type { H3Event } from 'h3'

const COOKIE_NAME = 'control_plane_session'
const TOKEN_VERSION = 'v1'

type SessionPayload = {
  exp: number
  iat: number
  nonce: string
}

export function sessionCookieName() {
  return COOKIE_NAME
}

function encodeBase64Url(value: string) {
  return Buffer.from(value, 'utf8').toString('base64url')
}

function decodeBase64Url(value: string) {
  return Buffer.from(value, 'base64url').toString('utf8')
}

function signToken(encodedPayload: string, secret: string) {
  return createHmac('sha256', secret).update(`${TOKEN_VERSION}.${encodedPayload}`).digest('base64url')
}

function parseSession(value: string | undefined, secret: string): SessionPayload | null {
  if (!value) {
    return null
  }
  const [version, encodedPayload, signature] = value.split('.', 3)
  if (!version || !encodedPayload || !signature || version !== TOKEN_VERSION) {
    return null
  }
  const expectedSignature = signToken(encodedPayload, secret)
  const expected = Buffer.from(expectedSignature)
  const actual = Buffer.from(signature)
  if (expected.length !== actual.length || !timingSafeEqual(expected, actual)) {
    return null
  }
  try {
    return JSON.parse(decodeBase64Url(encodedPayload)) as SessionPayload
  } catch {
    return null
  }
}

export function issueSession(secret: string, maxAgeSeconds: number) {
  if (!secret) {
    throw createError({ statusCode: 500, statusMessage: 'Session secret is not configured' })
  }
  const now = Math.floor(Date.now() / 1000)
  const payload = encodeBase64Url(JSON.stringify({
    exp: now + maxAgeSeconds,
    iat: now,
    nonce: randomBytes(12).toString('hex'),
  }))
  return `${TOKEN_VERSION}.${payload}.${signToken(payload, secret)}`
}

export function isSessionValid(value: string | undefined, secret: string) {
  const session = parseSession(value, secret)
  return Boolean(session && session.exp > Math.floor(Date.now() / 1000))
}

export function sessionExpiresAt(value: string | undefined, secret: string) {
  const session = parseSession(value, secret)
  if (!session || session.exp <= Math.floor(Date.now() / 1000)) {
    return null
  }
  return new Date(session.exp * 1000).toISOString()
}

export function assertAuthenticated(event: H3Event) {
  const config = useRuntimeConfig(event)
  if (!config.sessionSecret) {
    throw createError({ statusCode: 500, statusMessage: 'Session secret is not configured' })
  }
  const value = getCookie(event, sessionCookieName())
  if (!isSessionValid(value, config.sessionSecret)) {
    throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
  }
}
