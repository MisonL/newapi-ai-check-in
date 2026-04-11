import { controlPlaneHeaders, controlPlaneUrl } from '../../utils/controlPlane'
import { assertAuthenticated } from '../../utils/auth'

export default defineEventHandler(async (event) => {
  assertAuthenticated(event)
  const config = useRuntimeConfig(event)
  try {
    return await $fetch(controlPlaneUrl(config, '/api/dashboard'), {
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
