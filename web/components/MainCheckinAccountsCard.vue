<script setup lang="ts">
type AccountMode = 'none' | 'global' | 'single'
type AccountRow = {
  name: string
  provider: string
  api_user: string
  cookies_json: string
  linux_mode: AccountMode
  linux_user: string
  linux_pass: string
  github_mode: AccountMode
  github_user: string
  github_pass: string
  proxy_json: string
  extra_json: string
}

const accounts = defineModel<AccountRow[]>({ required: true })
const { t } = useAppI18n()
const modeOptions = computed(() => [
  { label: t('不使用'), value: 'none' },
  { label: t('全局账号'), value: 'global' },
  { label: t('单账号'), value: 'single' },
])

const createAccount = (): AccountRow => ({
  name: '',
  provider: '',
  api_user: '',
  cookies_json: '',
  linux_mode: 'none',
  linux_user: '',
  linux_pass: '',
  github_mode: 'none',
  github_user: '',
  github_pass: '',
  proxy_json: '',
  extra_json: ''
})

const isBlankAccount = (account: AccountRow) => (
  !account.name.trim()
  && !account.provider.trim()
  && !account.api_user.trim()
  && !account.cookies_json.trim()
  && account.linux_mode === 'none'
  && !account.linux_user.trim()
  && !account.linux_pass.trim()
  && account.github_mode === 'none'
  && !account.github_user.trim()
  && !account.github_pass.trim()
  && !account.proxy_json.trim()
  && !account.extra_json.trim()
)

const addAccount = () => {
  accounts.value = [...accounts.value, createAccount()]
}

const removeAccount = (index: number) => {
  accounts.value = accounts.value.filter((_, currentIndex) => currentIndex !== index)
  if (!accounts.value.length) {
    accounts.value = [createAccount()]
  }
}

const fieldId = (index: number, name: string) => `main-checkin-account-${index}-${name}`
const summaryTags = (account: AccountRow): Array<{ label: string, state: string }> => {
  if (isBlankAccount(account)) {
    return []
  }
  const tags = [{ label: account.provider || 'anyrouter', state: 'info' }]
  if (account.cookies_json.trim()) {
    tags.push({ label: 'Cookies', state: 'configured' })
  }
  if (account.linux_mode !== 'none') {
    tags.push({ label: 'Linux.do', state: 'configured' })
  }
  if (account.github_mode !== 'none') {
    tags.push({ label: 'GitHub', state: 'configured' })
  }
  return tags
}
</script>

<template>
  <section class="card surface-card">
    <div class="section-head">
      <h2 class="card__title">{{ t('账号') }}</h2>
      <button type="button" class="button button--secondary" @click="addAccount">{{ t('新增账号') }}</button>
    </div>
    <div class="stack-list">
      <details
        v-for="(account, index) in accounts"
        :key="index"
        class="subcard account-card"
        :open="index === 0"
      >
        <summary class="account-card__summary">
          <div class="account-card__summary-main">
            <strong>{{ t('账号 {index}', { index: index + 1 }) }}</strong>
            <span class="muted">{{ account.name || account.provider || t('未配置') }}</span>
          </div>
          <div class="account-card__summary-tags">
            <StatusBadge
              v-for="tag in summaryTags(account)"
              :key="tag.label"
              :label="tag.label"
              :state="tag.state"
              :dot="false"
            />
            <span class="fold-hint" aria-hidden="true">{{ t('展开或收起') }}</span>
          </div>
        </summary>
        <div class="account-card__body">
          <div class="section-head">
            <strong>{{ account.name || t('账号 {index}', { index: index + 1 }) }}</strong>
            <ConfirmButton label="移除" confirm-label="确认移除" @confirm="removeAccount(index)" />
          </div>
          <form class="stack-list" @submit.prevent>
            <div class="panel-grid panel-grid--two">
              <div class="field">
                <label class="field__label" :for="fieldId(index, 'name')">{{ t('名称') }}</label>
                <input :id="fieldId(index, 'name')" v-model="account.name" :name="fieldId(index, 'name')" autocomplete="off" class="input">
              </div>
              <div class="field">
                <label class="field__label" :for="fieldId(index, 'provider')">{{ t('提供商') }}</label>
                <input
                  :id="fieldId(index, 'provider')"
                  v-model="account.provider"
                  :name="fieldId(index, 'provider')"
                  autocomplete="off"
                  class="input"
                  placeholder="anyrouter"
                  spellcheck="false"
                >
              </div>
              <div class="field">
                <label class="field__label" :for="fieldId(index, 'api-user')">{{ t('API 用户') }}</label>
                <input
                  :id="fieldId(index, 'api-user')"
                  v-model="account.api_user"
                  :name="fieldId(index, 'api-user')"
                  autocomplete="off"
                  class="input"
                  spellcheck="false"
                >
              </div>
              <div class="field">
                <label class="field__label" :for="fieldId(index, 'linux-mode')">{{ t('Linux.do 模式') }}</label>
                <AppSelect
                  :id="fieldId(index, 'linux-mode')"
                  :model-value="account.linux_mode"
                  :name="fieldId(index, 'linux-mode')"
                  :options="modeOptions"
                  @update:model-value="account.linux_mode = $event as AccountMode"
                />
              </div>
              <div class="field">
                <label class="field__label" :for="fieldId(index, 'github-mode')">{{ t('GitHub 模式') }}</label>
                <AppSelect
                  :id="fieldId(index, 'github-mode')"
                  :model-value="account.github_mode"
                  :name="fieldId(index, 'github-mode')"
                  :options="modeOptions"
                  @update:model-value="account.github_mode = $event as AccountMode"
                />
              </div>
              <div v-if="account.linux_mode === 'single'" class="field">
                <label class="field__label" :for="fieldId(index, 'linux-user')">{{ t('Linux.do 用户名') }}</label>
                <input
                  :id="fieldId(index, 'linux-user')"
                  v-model="account.linux_user"
                  :name="fieldId(index, 'linux-user')"
                  autocomplete="off"
                  class="input"
                  spellcheck="false"
                >
              </div>
              <div v-if="account.linux_mode === 'single'" class="field">
                <label class="field__label" :for="fieldId(index, 'linux-pass')">{{ t('Linux.do 密码') }}</label>
                <PasswordField
                  :id="fieldId(index, 'linux-pass')"
                  v-model="account.linux_pass"
                  :name="fieldId(index, 'linux-pass')"
                  autocomplete="off"
                />
              </div>
              <div v-if="account.github_mode === 'single'" class="field">
                <label class="field__label" :for="fieldId(index, 'github-user')">{{ t('GitHub 用户名') }}</label>
                <input
                  :id="fieldId(index, 'github-user')"
                  v-model="account.github_user"
                  :name="fieldId(index, 'github-user')"
                  autocomplete="off"
                  class="input"
                  spellcheck="false"
                >
              </div>
              <div v-if="account.github_mode === 'single'" class="field">
                <label class="field__label" :for="fieldId(index, 'github-pass')">{{ t('GitHub 密码') }}</label>
                <PasswordField
                  :id="fieldId(index, 'github-pass')"
                  v-model="account.github_pass"
                  :name="fieldId(index, 'github-pass')"
                  autocomplete="off"
                />
              </div>
            </div>
            <div class="panel-grid panel-grid--two">
              <div class="field">
                <label class="field__label" :for="fieldId(index, 'cookies')">{{ t('Cookies JSON') }}</label>
                <textarea
                  :id="fieldId(index, 'cookies')"
                  v-model="account.cookies_json"
                  :name="fieldId(index, 'cookies')"
                  autocomplete="off"
                  class="textarea textarea--compact textarea--code"
                  placeholder='{"session":"…"}'
                  spellcheck="false"
                />
              </div>
              <div class="field">
                <label class="field__label" :for="fieldId(index, 'proxy')">{{ t('代理 JSON') }}</label>
                <textarea
                  :id="fieldId(index, 'proxy')"
                  v-model="account.proxy_json"
                  :name="fieldId(index, 'proxy')"
                  autocomplete="off"
                  class="textarea textarea--compact textarea--code"
                  placeholder='{"server":"http://proxy.example.com:8080"}'
                  spellcheck="false"
                />
              </div>
              <div class="field">
                <label class="field__label" :for="fieldId(index, 'extra')">{{ t('扩展 JSON') }}</label>
                <textarea
                  :id="fieldId(index, 'extra')"
                  v-model="account.extra_json"
                  :name="fieldId(index, 'extra')"
                  autocomplete="off"
                  class="textarea textarea--compact textarea--code"
                  placeholder='{"get_cdk_cookies":{"session":"…"}}'
                  spellcheck="false"
                />
              </div>
            </div>
          </form>
        </div>
      </details>
    </div>
  </section>
</template>
