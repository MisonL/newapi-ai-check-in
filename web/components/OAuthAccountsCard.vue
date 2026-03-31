<script setup lang="ts">
type OAuthRow = { username: string; password: string }

const props = defineProps<{ title: string }>()
const accounts = defineModel<OAuthRow[]>({ required: true })

const createAccount = (): OAuthRow => ({ username: '', password: '' })

const addAccount = () => {
  accounts.value = [...accounts.value, createAccount()]
}

const removeAccount = (index: number) => {
  accounts.value = accounts.value.filter((_, currentIndex) => currentIndex !== index)
}
</script>

<template>
  <section class="card">
    <div class="section-head">
      <h2 class="card__title">{{ props.title }}</h2>
      <button class="button button--secondary" @click="addAccount">Add</button>
    </div>
    <div class="stack-list">
      <article v-for="(item, index) in accounts" :key="`${props.title}-${index}`" class="subcard">
        <div class="panel-grid panel-grid--two">
          <div class="field">
            <label class="field__label">Username</label>
            <input v-model="item.username" class="input">
          </div>
          <div class="field">
            <label class="field__label">Password</label>
            <input v-model="item.password" class="input" type="password">
          </div>
        </div>
        <button class="button button--danger" @click="removeAccount(index)">Remove</button>
      </article>
    </div>
  </section>
</template>
