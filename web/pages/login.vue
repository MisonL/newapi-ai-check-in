<script setup lang="ts">
const route = useRoute()
const password = ref('')
const errorMessage = ref('')
const isSubmitting = ref(false)
const authState = useAuthState()
const authExpiresAt = useAuthExpiresAt()
const { t, translateRequestError } = useAppI18n()

const nextPath = computed(() => {
  const value = route.query.next
  if (typeof value === 'string' && value.startsWith('/')) {
    return value
  }
  return '/dashboard'
})

const submit = async () => {
  if (isSubmitting.value) {
    return
  }
  errorMessage.value = ''
  if (!password.value) {
    errorMessage.value = t('密码不能为空')
    return
  }
  isSubmitting.value = true
  try {
    const response = await $fetch<{ authenticated: boolean, expires_at: string | null }>('/api/auth/login', {
      method: 'POST',
      body: { password: password.value },
    })
    authState.value = true
    authExpiresAt.value = response.expires_at
    await navigateTo(nextPath.value)
  } catch (error: any) {
    authState.value = false
    authExpiresAt.value = null
    errorMessage.value = translateRequestError(error, '登录失败')
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <main class="login-page login-page--console">
    <form class="login-console surface-card" @submit.prevent="submit">
      <input
        autocomplete="username"
        class="login-console__username-proxy"
        name="username"
        type="text"
        value="admin"
      >
      <div class="login-console__topbar">
        <div class="login-console__brand">
          <span class="login-console__brand-mark" />
          <div class="login-console__brand-copy">
            <span class="login-console__eyebrow">{{ t('任务中心') }}</span>
            <strong>newapi.ai check-in</strong>
          </div>
        </div>
        <div class="button-row">
          <LocaleToggle />
          <ThemeToggle />
        </div>
      </div>

      <div class="login-console__body">
        <p class="login-console__kicker">{{ t('控制台入口') }}</p>
        <h1 class="login-console__title">{{ t('登录签到平台') }}</h1>
        <p class="login-console__subtitle">{{ t('统一管理多渠道、多账号的自动签到任务与执行状态') }}</p>

        <div class="field login-console__field">
          <label class="field__label" for="password">{{ t('管理员密码') }}</label>
          <PasswordField
            id="password"
            v-model="password"
            name="password"
            autocomplete="current-password"
            autofocus
          />
        </div>

        <p v-if="errorMessage" class="status-note" role="alert">{{ errorMessage }}</p>

        <button class="button button--primary login-console__submit" type="submit" :disabled="isSubmitting">
          {{ t(isSubmitting ? '登录中' : '登录') }}
        </button>
      </div>
    </form>
  </main>
</template>
