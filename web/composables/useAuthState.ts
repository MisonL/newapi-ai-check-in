export function useAuthState() {
  return useState<boolean | null>('control-plane-authenticated', () => null)
}

export function useAuthExpiresAt() {
  return useState<string | null>('control-plane-authenticated-expires-at', () => null)
}
