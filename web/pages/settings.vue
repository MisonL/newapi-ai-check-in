<script setup lang="ts">
const api = useControlPlane()
const { formatBoolean, formatBrowserStrategy, formatConfigured, formatMainCheckinEngine, formatNotificationField, t, translateRequestError } = useAppI18n()

const system = reactive({
  debug: false,
  browser_strategy: 'http_only',
  browser_enabled: false,
  main_checkin_engine: 'task_center'
})
const notifications = reactive({
  dingding_webhook: '',
  email_user: '',
  email_pass: '',
  email_to: '',
  custom_smtp_server: '',
  pushplus_token: '',
  server_push_key: '',
  feishu_webhook: '',
  weixin_webhook: '',
  telegram_bot_token: '',
  telegram_chat_id: ''
})
const appStatus = ref<any>(null)
const passwordForm = reactive({
  password: '',
  confirmPassword: ''
})
const message = ref('')
const passwordMessage = ref('')
const booleanOptions = computed(() => [
  { label: t('已启用'), value: true },
  { label: t('已禁用'), value: false },
])
const browserStrategyOptions = computed(() => [
  { label: formatBrowserStrategy('legacy'), value: 'legacy' },
  { label: formatBrowserStrategy('http_only'), value: 'http_only' },
])
const mainEngineOptions = computed(() => [
  { label: formatMainCheckinEngine('task_center'), value: 'task_center' },
  { label: formatMainCheckinEngine('legacy'), value: 'legacy' },
])
const notificationEntries = computed(() => Object.entries(notifications))
const notificationCount = computed(() => notificationEntries.value.filter(([, value]) => String(value).trim()).length)
const adminStatusLabel = computed(() => `${t('管理员')} ${formatConfigured(Boolean(appStatus.value?.admin_password_configured))}`)
const engineStatusLabel = computed(() => `${t('主签到引擎')} ${formatMainCheckinEngine(system.main_checkin_engine)}`)
const browserStatusLabel = computed(() => `${t('浏览器')} ${formatBrowserStrategy(system.browser_strategy)}`)
const notificationStatusLabel = computed(() => `${t('通知项')} ${notificationCount.value}`)
const secretNotificationKeys = new Set([
  'dingding_webhook',
  'email_pass',
  'pushplus_token',
  'server_push_key',
  'feishu_webhook',
  'weixin_webhook',
  'telegram_bot_token',
])

const [
  { data: statusResponse, refresh: refreshStatus },
  { data: systemResponse, refresh: refreshSystem },
  { data: notificationsResponse, refresh: refreshNotifications }
] = await Promise.all([
  useAsyncData('app-status', () => api.getStatus()),
  useAsyncData('system-config', () => api.getConfig('system')),
  useAsyncData('notifications-config', () => api.getConfig('notifications'))
])

watchEffect(() => {
  appStatus.value = statusResponse.value
  Object.assign(system, systemResponse.value?.payload || {})
  Object.assign(notifications, notificationsResponse.value?.payload || {})
})

const save = async () => {
  message.value = ''
  try {
    await api.saveConfig('system', { ...system })
    await api.saveConfig('notifications', { ...notifications })
    await refreshSystem()
    await refreshNotifications()
    await refreshStatus()
    message.value = t('设置已保存')
  } catch (error: any) {
    message.value = translateRequestError(error, '设置保存失败')
  }
}

const savePassword = async () => {
  passwordMessage.value = ''
  if (!passwordForm.password) {
    passwordMessage.value = t('密码不能为空')
    return
  }
  if (passwordForm.password !== passwordForm.confirmPassword) {
    passwordMessage.value = t('两次输入的密码不一致')
    return
  }
  try {
    await api.updateAdminPassword(passwordForm.password)
    passwordForm.password = ''
    passwordForm.confirmPassword = ''
    await refreshSystem()
    await refreshStatus()
    passwordMessage.value = t('管理员密码已更新')
  } catch (error: any) {
    passwordMessage.value = translateRequestError(error, '管理员密码更新失败')
  }
}

const isSecretNotificationField = (key: string) => secretNotificationKeys.has(key)
</script>

<template>
  <AppShell>
    <PageHeader
      :title="t('系统设置')"
      :description="t('统一管理管理员访问、浏览器策略和通知通道')"
      :eyebrow="t('工作台')"
    />
    <div class="button-row page-summary-strip">
      <StatusBadge :label="adminStatusLabel" :state="appStatus?.admin_password_configured ? 'configured' : 'unconfigured'" />
      <StatusBadge :label="engineStatusLabel" state="configured" />
      <StatusBadge :label="browserStatusLabel" state="info" />
      <StatusBadge :label="notificationStatusLabel" state="neutral" />
    </div>
    <div class="panel-grid panel-grid--two settings-grid">
      <form class="card surface-card settings-card settings-card--security" @submit.prevent="savePassword">
        <input
          aria-hidden="true"
          autocomplete="username"
          name="username"
          style="position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none;"
          tabindex="-1"
          type="text"
          value="admin"
        >
        <h2 class="card__title">{{ t('管理员访问') }}</h2>
        <div class="status-list">
          <StatusBadge
            :label="t('已存储密码：{value}', { value: formatConfigured(Boolean(appStatus?.admin_password_configured)) })"
            :state="appStatus?.admin_password_configured ? 'configured' : 'unconfigured'"
          />
          <StatusBadge
            :label="t('引导密码：{value}', { value: formatBoolean(Boolean(appStatus?.bootstrap_password_enabled)) })"
            :state="appStatus?.bootstrap_password_enabled ? 'enabled' : 'disabled'"
          />
        </div>
        <FieldBlock
          for-id="settings-admin-password"
          :label="t('新管理员密码')"
          :description="t('写入后 bootstrap 管理员密码立即失效')"
          style="margin-top: 16px;"
        >
          <PasswordField
            id="settings-admin-password"
            v-model="passwordForm.password"
            autocomplete="new-password"
          />
        </FieldBlock>
        <FieldBlock
          for-id="settings-admin-password-confirm"
          :label="t('确认密码')"
          :description="t('再次输入相同密码，避免误修改')"
        >
          <PasswordField
            id="settings-admin-password-confirm"
            v-model="passwordForm.confirmPassword"
            autocomplete="new-password"
          />
        </FieldBlock>
        <div class="button-row">
          <button class="button button--primary" type="submit">{{ t('更新密码') }}</button>
        </div>
        <p v-if="passwordMessage" class="status-note" role="status" aria-live="polite">{{ passwordMessage }}</p>
      </form>
      <section class="card surface-card settings-card settings-card--system">
        <div class="section-head">
          <h2 class="card__title">{{ t('系统') }}</h2>
          <StatusBadge :label="formatMainCheckinEngine(system.main_checkin_engine)" state="configured" />
        </div>
        <FieldBlock
          for-id="settings-debug"
          :label="t('调试模式')"
          :description="t('仅在排障时开启，用于保留更多运行细节')"
        >
          <AppSelect
            id="settings-debug"
            :model-value="system.debug"
            :options="booleanOptions"
            @update:model-value="system.debug = $event as boolean"
          />
        </FieldBlock>
        <FieldBlock
          for-id="settings-main-engine"
          :label="t('主签到引擎')"
          :description="t('默认使用任务中心引擎，只有历史站点仍依赖旧脚本时才切回旧链路')"
        >
          <AppSelect
            id="settings-main-engine"
            :model-value="system.main_checkin_engine"
            :options="mainEngineOptions"
            @update:model-value="system.main_checkin_engine = $event as string"
          />
        </FieldBlock>
        <FieldBlock
          for-id="settings-browser-strategy"
          :label="t('浏览器策略')"
          :description="t('默认优先 HTTP-only，需要真实浏览器能力时再切回传统浏览器')"
        >
          <AppSelect
            id="settings-browser-strategy"
            :model-value="system.browser_strategy"
            :options="browserStrategyOptions"
            @update:model-value="system.browser_strategy = $event as string"
          />
        </FieldBlock>
        <FieldBlock
          for-id="settings-browser-enabled"
          :label="t('启用浏览器')"
          :description="t('关闭后仅执行无需浏览器上下文的任务')"
        >
          <AppSelect
            id="settings-browser-enabled"
            :model-value="system.browser_enabled"
            :options="booleanOptions"
            @update:model-value="system.browser_enabled = $event as boolean"
          />
        </FieldBlock>
      </section>
      <form class="card surface-card settings-card settings-card--notifications" @submit.prevent="save">
        <div class="section-head">
          <h2 class="card__title">{{ t('通知设置') }}</h2>
          <StatusBadge :label="String(notificationCount)" state="neutral" />
        </div>
        <p class="muted" style="margin: 0 0 18px;">{{ t('密钥类字段默认遮罩，地址、收件人与 Chat ID 保持明文，便于核对') }}</p>
        <div class="settings-form-grid">
          <div v-for="[key] in notificationEntries" :key="key" class="field">
            <label class="field__label" :for="`notification-${key}`">{{ formatNotificationField(key) }}</label>
            <PasswordField
              v-if="isSecretNotificationField(key)"
              :id="`notification-${key}`"
              v-model="notifications[key]"
              autocomplete="off"
            />
            <input v-else :id="`notification-${key}`" v-model="notifications[key]" class="input" type="text">
          </div>
        </div>
        <div class="button-row" style="margin-top: 20px;">
          <button class="button button--primary" type="submit">{{ t('保存设置') }}</button>
        </div>
        <p v-if="message" class="status-note" role="status" aria-live="polite">{{ message }}</p>
      </form>
    </div>
  </AppShell>
</template>
