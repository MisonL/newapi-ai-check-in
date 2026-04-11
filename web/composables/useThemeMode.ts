type ThemeMode = 'light' | 'dark' | 'auto'

function normalizeTheme(value?: string | null): ThemeMode {
  return value === 'light' || value === 'dark' || value === 'auto' ? value : 'auto'
}

export function useThemeMode() {
  const themeCookie = useCookie<ThemeMode | null>('theme-mode', {
    default: () => null,
    sameSite: 'lax',
    path: '/',
  })
  const theme = useState<ThemeMode>('theme-mode', () => normalizeTheme(themeCookie.value))

  const applyTheme = (value: ThemeMode) => {
    if (!import.meta.client) {
      return
    }
    const resolved = value === 'auto'
      ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
      : value
    document.documentElement.classList.toggle('dark', resolved === 'dark')
    localStorage.setItem('theme-mode', value)
  }

  watch(themeCookie, (value) => {
    if (value === null) {
      return
    }
    const normalized = normalizeTheme(value)
    if (theme.value !== normalized) {
      theme.value = normalized
      return
    }
    applyTheme(normalized)
  })

  watch(theme, (value) => {
    const normalized = normalizeTheme(value)
    if (themeCookie.value !== normalized) {
      themeCookie.value = normalized
    }
    applyTheme(normalized)
  })

  onMounted(() => {
    const savedTheme = normalizeTheme(themeCookie.value ?? localStorage.getItem('theme-mode'))
    if (theme.value !== savedTheme) {
      theme.value = savedTheme
      return
    }
    applyTheme(savedTheme)
  })

  const setTheme = (value: ThemeMode) => {
    theme.value = normalizeTheme(value)
  }

  return { theme, setTheme }
}
