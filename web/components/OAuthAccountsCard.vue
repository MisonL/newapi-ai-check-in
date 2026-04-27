<script setup lang="ts">
type OAuthRow = { username: string; password: string }

const props = defineProps<{ title: string }>()
const accounts = defineModel<OAuthRow[]>({ required: true })
const { t } = useAppI18n()

const createAccount = (): OAuthRow => ({ username: '', password: '' })

const addAccount = () => {
  accounts.value = [...accounts.value, createAccount()]
}

const removeAccount = (index: number) => {
  accounts.value = accounts.value.filter((_, currentIndex) => currentIndex !== index)
}

const fieldId = (index: number, name: string) => `${props.title}-${index}-${name}`.replaceAll(' ', '-')
</script>

<template>
  <section class="card surface-card">
    <div class="section-head">
      <h2 class="card__title">{{ t(props.title) }}</h2>
      <button type="button" class="button button--secondary" @click="addAccount">{{ t('新增') }}</button>
    </div>
    <div class="stack-list">
      <form v-for="(item, index) in accounts" :key="`${props.title}-${index}`" class="subcard" @submit.prevent>
        <div class="panel-grid panel-grid--two">
          <div class="field">
            <label class="field__label" :for="fieldId(index, 'username')">{{ t('用户名') }}</label>
            <input :id="fieldId(index, 'username')" v-model="item.username" :name="fieldId(index, 'username')" autocomplete="off" class="input" spellcheck="false">
          </div>
          <div class="field">
            <label class="field__label" :for="fieldId(index, 'password')">{{ t('密码') }}</label>
            <PasswordField
              :id="fieldId(index, 'password')"
              v-model="item.password"
              :name="fieldId(index, 'password')"
              autocomplete="off"
            />
          </div>
        </div>
        <ConfirmButton label="移除" confirm-label="确认移除" @confirm="removeAccount(index)" />
      </form>
    </div>
  </section>
</template>
