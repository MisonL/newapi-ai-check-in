export function useThemeMode() {
  const theme = useState<'light' | 'dark' | 'auto'>('theme-mode', () => 'auto')

  const applyTheme = () => {
    if (!import.meta.client) {
      return
    }
    const resolved = theme.value === 'auto'
      ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
      : theme.value
    document.documentElement.classList.toggle('dark', resolved === 'dark')
    localStorage.setItem('theme-mode', theme.value)
  }

  const setTheme = (value: 'light' | 'dark' | 'auto') => {
    theme.value = value
    applyTheme()
  }

  if (import.meta.client) {
    const saved = localStorage.getItem('theme-mode') as 'light' | 'dark' | 'auto' | null
    if (saved) {
      theme.value = saved
    }
    applyTheme()
  }

  return { theme, setTheme }
}
