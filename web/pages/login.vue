<script setup lang="ts">
const password = ref('')
const errorMessage = ref('')
const isSubmitting = ref(false)
const authState = useAuthState()
const authExpiresAt = useAuthExpiresAt()
const { t, translateRequestError } = useAppI18n()
const highlights = ['首页', '站点', '账号', '今日任务']

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
    await navigateTo('/dashboard')
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
  <main class="login-page">
    <div class="login-shell surface-card">
      <section class="login-shell__intro">
        <div class="brand">
          <div class="brand__mark" />
          <div>
            <div class="brand__eyebrow">{{ t('任务中心') }}</div>
            <div class="brand__title">newapi.ai check-in</div>
          </div>
        </div>
        <h1 class="login-shell__title">{{ t('多站点多账号签到任务中心') }}</h1>
        <p class="login-shell__description">{{ t('管理多站点、多账号的每日签到任务与收益结果') }}</p>
        <p class="login-shell__meta">{{ t('仅管理员可访问，系统会统一管理多站点、多账号的签到任务、收益结果与异常处理') }}</p>
        <div class="login-shell__chips">
          <StatusBadge v-for="item in highlights" :key="item" :label="t(item)" state="neutral" :dot="false" />
        </div>
      </section>
      <form class="card surface-card login-card" @submit.prevent="submit">
        <input
          aria-hidden="true"
          autocomplete="username"
          name="username"
          style="position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none;"
          tabindex="-1"
          type="text"
          value="admin"
        >
        <div class="login-card__top">
          <div>
            <div class="card__title">{{ t('登录') }}</div>
            <p class="muted login-card__hint">{{ t('单管理员入口') }}</p>
          </div>
          <div class="button-row">
            <LocaleToggle />
            <ThemeToggle />
          </div>
        </div>
        <div class="field" style="margin-top: 24px;">
          <label class="field__label" for="password">{{ t('管理员密码') }}</label>
          <PasswordField
            id="password"
            v-model="password"
            name="password"
            autocomplete="current-password"
          />
        </div>
        <p v-if="errorMessage" class="status-note" role="alert">{{ errorMessage }}</p>
        <div class="button-row">
          <button class="button button--primary login-card__submit" type="submit" :disabled="isSubmitting">
            {{ t(isSubmitting ? '登录中' : '登录') }}
          </button>
        </div>
      </form>
    </div>
  </main>
</template>
