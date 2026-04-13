type UiDateTimeValue = string | Date | null | undefined

function normalizeDate(value: UiDateTimeValue) {
  if (!value) {
    return null
  }
  return value instanceof Date ? value : new Date(value)
}

export function useUiDateTime() {
  const { locale, t } = useAppI18n()
  const config = useRuntimeConfig()
  const timeZone = computed(() => config.public.appTimezone || 'Asia/Shanghai')

  const formatDateTime = (value: UiDateTimeValue, fallbackKey = '未安排') => {
    const date = normalizeDate(value)
    if (!date) {
      return t(fallbackKey)
    }
    return new Intl.DateTimeFormat(locale.value, {
      timeZone: timeZone.value,
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date)
  }

  const formatDate = (value: UiDateTimeValue, fallbackKey = '未安排') => {
    const date = normalizeDate(value)
    if (!date) {
      return t(fallbackKey)
    }
    return new Intl.DateTimeFormat(locale.value, {
      timeZone: timeZone.value,
      month: '2-digit',
      day: '2-digit',
    }).format(date)
  }

  const formatDateInput = (value: UiDateTimeValue) => {
    const date = normalizeDate(value)
    if (!date) {
      return ''
    }
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone: timeZone.value,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).formatToParts(date)
    const year = parts.find((part) => part.type === 'year')?.value || '0000'
    const month = parts.find((part) => part.type === 'month')?.value || '01'
    const day = parts.find((part) => part.type === 'day')?.value || '01'
    return `${year}-${month}-${day}`
  }

  return {
    timeZone,
    formatDate,
    formatDateInput,
    formatDateTime,
  }
}
