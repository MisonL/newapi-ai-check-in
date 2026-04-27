export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  if (!config.controlPlaneUrl) {
    throw createError({ statusCode: 500, statusMessage: 'Control plane URL is not configured' })
  }
  const controlPlane = await $fetch<{ status: string }>(`${config.controlPlaneUrl}/health`)
  return {
    status: 'ok',
    control_plane: controlPlane.status
  }
})
