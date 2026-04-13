import { controlPlaneHeaders, controlPlaneUrl } from '../../utils/controlPlane'
import { assertAuthenticated } from '../../utils/auth'

function taskCenterPath(segments: string[]) {
  if (segments[1] === 'summary') {
    return '/api/task-center/summary'
  }
  if (segments[1] === 'today') {
    return '/api/task-center/today'
  }
  if (segments[1] === 'incidents') {
    return '/api/task-center/incidents'
  }
  if (segments[1] === 'reports') {
    return '/api/task-center/reports'
  }
  if (segments[1] === 'imports' && segments[2] === 'main-checkin') {
    return '/api/task-center/imports/main-checkin'
  }
  if (segments[1] === 'tasks' && segments[2] === 'generate-today') {
    return '/api/task-center/tasks/generate-today'
  }
  if (segments[1] === 'tasks' && segments[2] === 'execute-today') {
    return '/api/task-center/tasks/execute-today'
  }
  if (segments[1] === 'tasks' && segments[2] && segments[3] === 'retry') {
    return `/api/task-center/tasks/${segments[2]}/retry`
  }
  if (segments[1] === 'tasks' && segments[2] && segments[3] === 'execute') {
    return `/api/task-center/tasks/${segments[2]}/execute`
  }
  return ''
}

function errorMessageFrom(error: any) {
  const detail = error?.response?._data?.detail
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((item) => {
        if (typeof item?.msg === 'string' && item.msg.trim()) {
          return item.msg
        }
        return JSON.stringify(item)
      })
      .join('; ')
  }
  if (detail && typeof detail === 'object') {
    return JSON.stringify(detail)
  }
  if (typeof error?.message === 'string' && error.message.trim()) {
    return error.message
  }
  return 'Control plane request failed'
}

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
  if (segments[0] === 'task-center') {
    const mapped = taskCenterPath(segments)
    if (mapped) {
      return mapped
    }
  }
  if (segments[0] === 'sites') {
    if (segments[1]) {
      return `/api/sites/${segments[1]}`
    }
    return '/api/sites'
  }
  if (segments[0] === 'accounts') {
    if (segments[1]) {
      return `/api/accounts/${segments[1]}`
    }
    return '/api/accounts'
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
      statusMessage: errorMessageFrom(error),
      data: error?.response?._data
    })
  }
})
