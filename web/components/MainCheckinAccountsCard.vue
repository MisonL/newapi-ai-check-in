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

const addAccount = () => {
  accounts.value = [...accounts.value, createAccount()]
}

const removeAccount = (index: number) => {
  accounts.value = accounts.value.filter((_, currentIndex) => currentIndex !== index)
  if (!accounts.value.length) {
    accounts.value = [createAccount()]
  }
}
</script>

<template>
  <section class="card">
    <div class="section-head">
      <h2 class="card__title">Accounts</h2>
      <button class="button button--secondary" @click="addAccount">Add account</button>
    </div>
    <div class="stack-list">
      <article v-for="(account, index) in accounts" :key="index" class="subcard">
        <div class="section-head">
          <strong>Account {{ index + 1 }}</strong>
          <button class="button button--danger" @click="removeAccount(index)">Remove</button>
        </div>
        <div class="panel-grid panel-grid--two">
          <div class="field">
            <label class="field__label">Name</label>
            <input v-model="account.name" class="input">
          </div>
          <div class="field">
            <label class="field__label">Provider</label>
            <input v-model="account.provider" class="input" placeholder="anyrouter">
          </div>
          <div class="field">
            <label class="field__label">API user</label>
            <input v-model="account.api_user" class="input">
          </div>
          <div class="field">
            <label class="field__label">Linux.do mode</label>
            <select v-model="account.linux_mode" class="select">
              <option value="none">none</option>
              <option value="global">global</option>
              <option value="single">single</option>
            </select>
          </div>
          <div v-if="account.linux_mode === 'single'" class="field">
            <label class="field__label">Linux.do username</label>
            <input v-model="account.linux_user" class="input">
          </div>
          <div v-if="account.linux_mode === 'single'" class="field">
            <label class="field__label">Linux.do password</label>
            <input v-model="account.linux_pass" class="input" type="password">
          </div>
          <div class="field">
            <label class="field__label">GitHub mode</label>
            <select v-model="account.github_mode" class="select">
              <option value="none">none</option>
              <option value="global">global</option>
              <option value="single">single</option>
            </select>
          </div>
          <div v-if="account.github_mode === 'single'" class="field">
            <label class="field__label">GitHub username</label>
            <input v-model="account.github_user" class="input">
          </div>
          <div v-if="account.github_mode === 'single'" class="field">
            <label class="field__label">GitHub password</label>
            <input v-model="account.github_pass" class="input" type="password">
          </div>
        </div>
        <div class="panel-grid panel-grid--two">
          <div class="field">
            <label class="field__label">Cookies JSON</label>
            <textarea v-model="account.cookies_json" class="textarea textarea--compact" placeholder='{"session":"..."}' />
          </div>
          <div class="field">
            <label class="field__label">Proxy JSON</label>
            <textarea v-model="account.proxy_json" class="textarea textarea--compact" placeholder='{"server":"http://proxy.example.com:8080"}' />
          </div>
          <div class="field">
            <label class="field__label">Extra JSON</label>
            <textarea v-model="account.extra_json" class="textarea textarea--compact" placeholder='{"get_cdk_cookies":{"session":"..."}}' />
          </div>
        </div>
      </article>
    </div>
  </section>
</template>
