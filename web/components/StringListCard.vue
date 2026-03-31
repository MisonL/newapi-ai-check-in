<script setup lang="ts">
const props = defineProps<{
  title: string
  label: string
  placeholder?: string
}>()

const items = defineModel<string[]>({ required: true })
const { t } = useAppI18n()

const addItem = () => {
  items.value = [...items.value, '']
}

const removeItem = (index: number) => {
  items.value = items.value.filter((_, currentIndex) => currentIndex !== index)
  if (!items.value.length) {
    items.value = ['']
  }
}
</script>

<template>
  <section class="card">
    <div class="section-head">
      <h2 class="card__title">{{ t(props.title) }}</h2>
      <button class="button button--secondary" @click="addItem">{{ t('新增') }}</button>
    </div>
    <div class="stack-list">
      <article v-for="(_, index) in items" :key="`${props.title}-${index}`" class="subcard">
        <div class="section-head">
          <strong>{{ t(props.label) }} {{ index + 1 }}</strong>
          <button class="button button--danger" @click="removeItem(index)">{{ t('移除') }}</button>
        </div>
        <div class="field">
          <label class="field__label">{{ t(props.label) }}</label>
          <input v-model="items[index]" class="input" :placeholder="props.placeholder">
        </div>
      </article>
    </div>
  </section>
</template>
