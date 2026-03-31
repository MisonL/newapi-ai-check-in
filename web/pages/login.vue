<script setup lang="ts">
const password = ref('')
const errorMessage = ref('')

const submit = async () => {
  errorMessage.value = ''
  try {
    await $fetch('/api/auth/login', { method: 'POST', body: { password: password.value } })
    await navigateTo('/dashboard')
  } catch (error: any) {
    errorMessage.value = error?.data?.statusMessage || error?.statusMessage || 'Login failed'
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
          <div class="muted">Single admin access</div>
        </div>
      </div>
      <div class="field" style="margin-top: 24px;">
        <label class="field__label" for="password">Admin password</label>
        <input id="password" v-model="password" class="input" type="password" @keyup.enter="submit">
      </div>
      <p v-if="errorMessage" class="muted" style="color: var(--semi-color-danger);">{{ errorMessage }}</p>
      <div class="button-row">
        <button class="button button--primary" @click="submit">Login</button>
      </div>
    </div>
  </div>
</template>
