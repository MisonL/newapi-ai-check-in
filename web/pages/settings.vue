<script setup lang="ts">
const api = useControlPlane()

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
    message.value = 'Settings saved'
  } catch (error: any) {
    message.value = error?.data?.message || error?.message || 'Settings save failed'
  }
}

const savePassword = async () => {
  passwordMessage.value = ''
  if (!passwordForm.password) {
    passwordMessage.value = 'Password is required'
    return
  }
  if (passwordForm.password !== passwordForm.confirmPassword) {
    passwordMessage.value = 'Passwords do not match'
    return
  }
  try {
    await api.updateAdminPassword(passwordForm.password)
    passwordForm.password = ''
    passwordForm.confirmPassword = ''
    await refreshSystem()
    await refreshStatus()
    passwordMessage.value = 'Admin password updated'
  } catch (error: any) {
    passwordMessage.value = error?.data?.message || error?.message || 'Admin password update failed'
  }
}
</script>

<template>
  <AppShell>
    <div class="panel-grid panel-grid--two">
      <section class="card">
        <h2 class="card__title">Admin access</h2>
        <div class="status-list">
          <span class="status-pill">Stored password: {{ appStatus?.admin_password_configured ? 'yes' : 'no' }}</span>
          <span class="status-pill">Bootstrap password: {{ appStatus?.bootstrap_password_enabled ? 'enabled' : 'disabled' }}</span>
        </div>
        <div class="field" style="margin-top: 16px;">
          <label class="field__label">New admin password</label>
          <input v-model="passwordForm.password" class="input" type="password">
        </div>
        <div class="field">
          <label class="field__label">Confirm password</label>
          <input v-model="passwordForm.confirmPassword" class="input" type="password">
        </div>
        <div class="button-row">
          <button class="button button--primary" @click="savePassword">Update password</button>
        </div>
        <p class="muted">{{ passwordMessage }}</p>
      </section>
      <section class="card">
        <h2 class="card__title">System</h2>
        <div class="field">
          <label class="field__label">Debug</label>
          <select v-model="system.debug" class="select">
            <option :value="true">true</option>
            <option :value="false">false</option>
          </select>
        </div>
        <div class="field">
          <label class="field__label">Browser strategy</label>
          <select v-model="system.browser_strategy" class="select">
            <option value="legacy">legacy</option>
            <option value="http_only">http_only</option>
          </select>
        </div>
        <div class="field">
          <label class="field__label">Browser enabled</label>
          <select v-model="system.browser_enabled" class="select">
            <option :value="true">true</option>
            <option :value="false">false</option>
          </select>
        </div>
      </section>
      <section class="card">
        <h2 class="card__title">Notifications</h2>
        <div v-for="(value, key) in notifications" :key="key" class="field">
          <label class="field__label">{{ key }}</label>
          <input v-model="notifications[key]" class="input" :type="key.includes('pass') ? 'password' : 'text'">
        </div>
      </section>
    </div>
    <div class="button-row" style="margin-top: 20px;">
      <button class="button button--primary" @click="save">Save settings</button>
    </div>
    <p class="muted">{{ message }}</p>
  </AppShell>
</template>
