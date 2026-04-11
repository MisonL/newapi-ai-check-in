function assertControlPlaneConfig(config: ReturnType<typeof useRuntimeConfig>) {
  if (!config.controlPlaneUrl) {
    throw createError({ statusCode: 500, statusMessage: 'Control plane URL is not configured' })
  }
  if (!config.controlPlaneToken) {
    throw createError({ statusCode: 500, statusMessage: 'Internal token is not configured' })
  }
}

export function controlPlaneHeaders(config: ReturnType<typeof useRuntimeConfig>) {
  assertControlPlaneConfig(config)
  return {
    'x-internal-token': config.controlPlaneToken
  }
}

export function controlPlaneUrl(config: ReturnType<typeof useRuntimeConfig>, path: string) {
  assertControlPlaneConfig(config)
  return `${config.controlPlaneUrl}${path}`
}
