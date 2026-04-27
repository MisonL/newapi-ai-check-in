import { messages, supportedLocales, type AppLocale } from '../locales/messages'

const serverMessageKeys: Record<string, string> = {
  Unauthorized: '未授权',
  'Invalid password': '密码错误',
  'Admin password is not configured': '管理员密码未配置',
  'Internal token is not configured': '内部令牌未配置',
  'Session secret is not configured': '会话密钥未配置',
  'Control plane URL is not configured': '控制面地址未配置',
  'Domain mismatch': '配置域不匹配',
  'Job run not found': '未找到任务运行记录',
  'Unknown API path': '未知 API 路径',
  'Control plane request failed': '控制面请求失败',
  'Field required': '必填项',
  'Password is required': '密码不能为空',
  'Login failed': '登录失败',
  'Config save failed': '配置保存失败',
  'Settings save failed': '设置保存失败',
  'Admin password update failed': '管理员密码更新失败',
  'Schedule save failed': '调度保存失败',
  'Run failed': '任务执行失败',
  'A job of the same type is already running': '同类型任务已在运行中',
  'No account configuration available': '没有可用的主签到账号配置',
  'No 996 accounts configured': '未配置 996 账号',
  'No qaq.al accounts configured': '未配置 qaq.al 账号',
  'No Linux.do read accounts configured': '未配置 Linux.do 阅读账号',
  'Username or password is incorrect, or user has been banned': '用户名或密码错误，或账号已被封禁',
  'Missing New-Api-User context': '缺少 New-Api-User 上下文，请检查 Cookie 会话配置',
  'qaq.al check-in requires browser support. Enable browser execution first.': 'qaq.al 签到依赖浏览器支持，请先启用浏览器执行',
  'Linux.do read requires browser support. Enable browser execution first.': 'Linux.do 阅读依赖浏览器支持，请先启用浏览器执行',
  'Provider anyrouter requires browser support. Enable browser execution or switch to cookie-only accounts.':
    '提供商 anyrouter 依赖浏览器支持，请启用浏览器执行或改用仅 cookies 账号',
  'Site URL must start with http:// or https://': '站点地址必须以 http:// 或 https:// 开头',
  'Site URL must include a valid host': '站点地址必须包含有效域名',
  'Site base URL already exists': '该站点地址已存在，请直接编辑已有站点',
  'Account already exists for this site and auth mode': '同一站点下已存在相同认证方式和用户名的账号',
}

const jobTypeKeys: Record<string, string> = {
  main_checkin: '主签到任务',
  checkin_996: '996 hub',
  checkin_qaq_al: 'qaq.al 签到',
  linuxdo_read: 'Linux.do 阅读',
}

const jobStatusKeys: Record<string, string> = {
  queued: '已入队',
  running: '运行中',
  success: '成功',
  failed: '失败',
  skipped: '已跳过',
}

const triggerKeys: Record<string, string> = {
  manual: '手动',
  scheduled: '调度',
  retry: '重试',
}

const notificationKeys: Record<string, string> = {
  dingding_webhook: '钉钉 Webhook',
  email_user: '邮箱用户名',
  email_pass: '邮箱密码',
  email_to: '收件人',
  custom_smtp_server: '自定义 SMTP 服务器',
  pushplus_token: 'PushPlus Token',
  server_push_key: 'Server Push Key',
  feishu_webhook: '飞书 Webhook',
  weixin_webhook: '企业微信 Webhook',
  telegram_bot_token: 'Telegram Bot Token',
  telegram_chat_id: 'Telegram Chat ID',
}

const deployModeKeys: Record<string, string> = {
  control_plane: '控制面调度',
  github_actions: 'GitHub Actions 驱动',
}

const fieldLabelKeys: Record<string, string> = {
  name: '站点名称',
  base_url: '站点地址',
  site_id: '站点',
  username: '用户名',
  password: '密码',
  api_user: 'API User',
  session_cookies: 'Cookies',
}

function render(template: string, params?: Record<string, string | number>) {
  if (!params) {
    return template
  }
  return Object.entries(params).reduce(
    (result, [key, value]) => result.replaceAll(`{${key}}`, String(value)),
    template,
  )
}

function normalizeLocale(value?: string): AppLocale {
  return supportedLocales.includes(value as AppLocale) ? (value as AppLocale) : 'zh-CN'
}

function normalizeServerMessage(message: string) {
  const normalizedMessage = message
    .replace(/[\u200B-\u200D\uFEFF]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
  const normalizedWithoutPunctuation = normalizedMessage.replace(/[.!。！？]+$/, '').trim()
  if (/^Username or password is incorrect, or user has been banned$/i.test(normalizedWithoutPunctuation)) {
    return { key: '用户名或密码错误，或账号已被封禁' }
  }
  if (/^No Linux\.do read accounts configured$/i.test(normalizedWithoutPunctuation)) {
    return { key: '未配置 Linux.do 阅读账号' }
  }
  if (/^No qaq\.al accounts configured$/i.test(normalizedWithoutPunctuation)) {
    return { key: '未配置 qaq.al 账号' }
  }
  if (/^Missing New-Api-User context$/i.test(normalizedWithoutPunctuation)) {
    return { key: '缺少 New-Api-User 上下文，请检查 Cookie 会话配置' }
  }
  if (serverMessageKeys[normalizedMessage]) {
    return { key: serverMessageKeys[normalizedMessage] }
  }
  if (serverMessageKeys[normalizedWithoutPunctuation]) {
    return { key: serverMessageKeys[normalizedWithoutPunctuation] }
  }
  if (normalizedMessage.startsWith('Value error, ')) {
    return normalizeServerMessage(normalizedMessage.slice('Value error, '.length))
  }
  if (normalizedMessage.startsWith('Invalid JSON response:')) {
    return { key: '站点返回的不是有效的 new-api 响应，请检查站点地址、反向代理或登录态' }
  }
  if (normalizedMessage === 'Unexpected response payload') {
    return { key: '站点响应结构异常，请确认目标站点兼容 new-api 接口' }
  }
  if (normalizedMessage === 'Task center engine requires at least one enabled site') {
    return { key: '任务中心至少需要一个已启用站点' }
  }
  if (normalizedMessage === 'Legacy OAuth executor returned no result') {
    return { key: '兼容登录链未返回有效结果，请检查站点登录流程或浏览器策略' }
  }
  if (normalizedMessage === 'Task requires review') {
    return { key: '任务结果需要人工复核' }
  }
  const failuresMatch = normalizedMessage.match(/^(.+?) completed with failures: (\d+)\/(\d+) succeeded$/)
  if (failuresMatch) {
    return {
      key: '任务执行完成，但有账号失败：成功 {success} / 总数 {total}',
      params: {
        success: Number(failuresMatch[2]),
        total: Number(failuresMatch[3]),
      },
    }
  }
  return { key: normalizedMessage }
}

export function useAppI18n() {
  const localeCookie = useCookie<AppLocale>('app-locale', {
    default: () => 'zh-CN',
    sameSite: 'lax',
    path: '/',
  })
  const locale = useState<AppLocale>('app-locale', () => normalizeLocale(localeCookie.value))

  const syncLocale = (value?: string) => {
    const normalized = normalizeLocale(value)
    if (locale.value !== normalized) {
      locale.value = normalized
    }
    if (localeCookie.value !== normalized) {
      localeCookie.value = normalized
    }
    if (import.meta.client) {
      document.documentElement.lang = normalized
    }
  }

  syncLocale(localeCookie.value)

  watch(localeCookie, (value) => {
    syncLocale(value)
  })

  watch(locale, (value) => {
    syncLocale(value)
  })

  const setLocale = (value: AppLocale) => {
    syncLocale(value)
  }

  const t = (key: string, params?: Record<string, string | number>) => {
    const template = messages[locale.value]?.[key] || messages['zh-CN'][key] || key
    return render(template, params)
  }

  const translateError = (message?: string, fallbackKey = '任务执行失败') => {
    if (!message) {
      return t(fallbackKey)
    }
    const normalized = normalizeServerMessage(message)
    return messages['zh-CN'][normalized.key]
      ? t(normalized.key, normalized.params)
      : message
  }

  const translateRequestError = (error: any, fallbackKey = '任务执行失败') => {
    const directMessage = error?.data?.message || error?.data?.detail || error?.data?.statusMessage || error?.statusMessage
    if (typeof directMessage === 'string' && directMessage.trim()) {
      return translateError(directMessage, fallbackKey)
    }
    if (Array.isArray(error?.data?.detail) && error.data.detail.length) {
      const lines = error.data.detail
        .map((item: any) => {
          const field = Array.isArray(item?.loc) ? String(item.loc[item.loc.length - 1] || '').trim() : ''
          const label = fieldLabelKeys[field] ? t(fieldLabelKeys[field]) : field
          const message = typeof item?.msg === 'string' ? translateError(item.msg, fallbackKey) : t(fallbackKey)
          return label ? `${label}: ${message}` : message
        })
        .filter(Boolean)
      if (lines.length) {
        return lines.join('；')
      }
    }
    return translateError(error?.message, fallbackKey)
  }

  return {
    locale,
    locales: supportedLocales,
    setLocale,
    t,
    translateError,
    translateRequestError,
    formatJobType: (value: string) => t(jobTypeKeys[value] || value),
    formatJobStatus: (value: string) => t(jobStatusKeys[value] || value),
    formatTrigger: (value: string) => t(triggerKeys[value] || value),
    formatBoolean: (value: boolean) => t(value ? '已启用' : '已禁用'),
    formatConfigured: (value: boolean) => t(value ? '已配置' : '未配置'),
    formatTheme: (value: 'light' | 'dark' | 'auto') =>
      t(value === 'light' ? '亮色' : value === 'dark' ? '暗色' : '跟随系统'),
    formatNotificationField: (value: string) => t(notificationKeys[value] || value),
    formatBrowserStrategy: (value: string) => t(value === 'http_only' ? '仅 HTTP' : '传统浏览器'),
    formatMainCheckinEngine: (value: string) => t(value === 'task_center' ? '任务中心引擎' : '旧脚本主链'),
    formatDeployMode: (value?: string) => t(deployModeKeys[value || ''] || value || '-'),
  }
}
