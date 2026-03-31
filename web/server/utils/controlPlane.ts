export function controlPlaneHeaders(config: ReturnType<typeof useRuntimeConfig>) {
  return {
    'x-internal-token': config.controlPlaneToken
  }
}

export function controlPlaneUrl(config: ReturnType<typeof useRuntimeConfig>, path: string) {
  return `${config.controlPlaneUrl}${path}`
}
