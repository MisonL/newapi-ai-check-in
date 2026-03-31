<script setup lang="ts">
const password = ref('')
const errorMessage = ref('')
const { t, translateError } = useAppI18n()

const submit = async () => {
  errorMessage.value = ''
  try {
    await $fetch('/api/auth/login', { method: 'POST', body: { password: password.value } })
    await navigateTo('/dashboard')
  } catch (error: any) {
    errorMessage.value = translateError(error?.data?.statusMessage || error?.statusMessage, '登录失败')
  }
}
</script>

<template>
  <div class="login-page">
    <div class="card login-card">
      <div class="brand">
        <div class="brand__mark" />
        <div>
          <div>newapi.ai check-in</div>
          <div class="muted">{{ t('单管理员入口') }}</div>
        </div>
      </div>
      <div class="button-row" style="margin-top: 16px;">
        <LocaleToggle />
      </div>
      <div class="field" style="margin-top: 24px;">
        <label class="field__label" for="password">{{ t('管理员密码') }}</label>
        <input id="password" v-model="password" class="input" type="password" @keyup.enter="submit">
      </div>
      <p v-if="errorMessage" class="muted" style="color: var(--semi-color-danger);">{{ errorMessage }}</p>
      <div class="button-row">
        <button class="button button--primary" @click="submit">{{ t('登录') }}</button>
      </div>
    </div>
  </div>
</template>
