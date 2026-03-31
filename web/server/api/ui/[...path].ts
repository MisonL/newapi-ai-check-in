import { controlPlaneHeaders, controlPlaneUrl } from '../../utils/controlPlane'
import { assertAuthenticated } from '../../utils/auth'

function mapPath(segments: string[]) {
  if (segments.length === 1 && segments[0] === 'status') {
    return '/api/status'
  }
  if (segments[0] === 'config' && segments[1]) {
    return `/api/config/${segments[1]}`
  }
  if (segments[0] === 'jobs') {
    if (segments.length === 3 && segments[2] === 'run') {
      return `/api/jobs/${segments[1]}/run`
    }
    if (segments.length === 3 && segments[2] === 'logs') {
      return `/api/jobs/${segments[1]}/logs`
    }
    if (segments.length === 2) {
      return `/api/jobs/${segments[1]}`
    }
    return '/api/jobs'
  }
  if (segments[0] === 'schedules') {
    if (segments[1]) {
      return `/api/schedules/${segments[1]}`
    }
    return '/api/schedules'
  }
  if (segments[0] === 'system' && segments[1] === 'admin-password') {
    return '/api/system/admin-password'
  }
  throw createError({ statusCode: 404, statusMessage: 'Unknown API path' })
}

export default defineEventHandler(async (event) => {
  assertAuthenticated(event)
  const config = useRuntimeConfig(event)
  const path = getRouterParam(event, 'path')
  const segments = (Array.isArray(path) ? path : String(path || '').split('/')).filter(Boolean)
  const targetPath = mapPath(segments)
  const query = getQuery(event)
  const method = event.node.req.method || 'GET'
  const body = ['POST', 'PUT', 'PATCH'].includes(method) ? await readBody(event) : undefined
  try {
    return await $fetch(controlPlaneUrl(config, targetPath), {
      method,
      query,
      body,
      headers: controlPlaneHeaders(config)
    })
  } catch (error: any) {
    throw createError({
      statusCode: error?.response?.status || 500,
      statusMessage: error?.response?._data?.detail || error?.message || 'Control plane request failed',
      data: error?.response?._data
    })
  }
})
