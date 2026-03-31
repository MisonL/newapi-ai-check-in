<script setup lang="ts">
const api = useControlPlane()
const { formatBoolean, formatBrowserStrategy, formatConfigured, formatNotificationField, t, translateError } = useAppI18n()

const system = reactive({
  debug: false,
  browser_strategy: 'legacy',
  browser_enabled: false
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

const { data: statusResponse, refresh: refreshStatus } = await useAsyncData('app-status', () => api.getStatus())
const { data: systemResponse, refresh: refreshSystem } = await useAsyncData('system-config', () => api.getConfig('system'))
const { data: notificationsResponse, refresh: refreshNotifications } = await useAsyncData('notifications-config', () => api.getConfig('notifications'))

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
    message.value = translateError(error?.data?.message || error?.message, '设置保存失败')
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
    passwordMessage.value = translateError(error?.data?.message || error?.message, '管理员密码更新失败')
  }
}
</script>

<template>
  <AppShell>
    <div class="panel-grid panel-grid--two">
      <section class="card">
        <h2 class="card__title">{{ t('管理员访问') }}</h2>
        <div class="status-list">
          <span class="status-pill">{{ t('已存储密码：{value}', { value: formatConfigured(Boolean(appStatus?.admin_password_configured)) }) }}</span>
          <span class="status-pill">{{ t('引导密码：{value}', { value: formatBoolean(Boolean(appStatus?.bootstrap_password_enabled)) }) }}</span>
        </div>
        <div class="field" style="margin-top: 16px;">
          <label class="field__label">{{ t('新管理员密码') }}</label>
          <input v-model="passwordForm.password" class="input" type="password">
        </div>
        <div class="field">
          <label class="field__label">{{ t('确认密码') }}</label>
          <input v-model="passwordForm.confirmPassword" class="input" type="password">
        </div>
        <div class="button-row">
          <button class="button button--primary" @click="savePassword">{{ t('更新密码') }}</button>
        </div>
        <p class="muted">{{ passwordMessage }}</p>
      </section>
      <section class="card">
        <h2 class="card__title">{{ t('系统') }}</h2>
        <div class="field">
          <label class="field__label">{{ t('调试模式') }}</label>
          <select v-model="system.debug" class="select">
            <option :value="true">{{ t('已启用') }}</option>
            <option :value="false">{{ t('已禁用') }}</option>
          </select>
        </div>
        <div class="field">
          <label class="field__label">{{ t('浏览器策略') }}</label>
          <select v-model="system.browser_strategy" class="select">
            <option value="legacy">{{ formatBrowserStrategy('legacy') }}</option>
            <option value="http_only">{{ formatBrowserStrategy('http_only') }}</option>
          </select>
        </div>
        <div class="field">
          <label class="field__label">{{ t('启用浏览器') }}</label>
          <select v-model="system.browser_enabled" class="select">
            <option :value="true">{{ t('已启用') }}</option>
            <option :value="false">{{ t('已禁用') }}</option>
          </select>
        </div>
      </section>
      <section class="card">
        <h2 class="card__title">{{ t('通知设置') }}</h2>
        <div v-for="(value, key) in notifications" :key="key" class="field">
          <label class="field__label">{{ formatNotificationField(key) }}</label>
          <input v-model="notifications[key]" class="input" :type="key.includes('pass') ? 'password' : 'text'">
        </div>
      </section>
    </div>
    <div class="button-row" style="margin-top: 20px;">
      <button class="button button--primary" @click="save">{{ t('保存设置') }}</button>
    </div>
    <p class="muted">{{ message }}</p>
  </AppShell>
</template>
