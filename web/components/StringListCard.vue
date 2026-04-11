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

const fieldId = (index: number) => `${props.title}-${props.label}-${index}`.replaceAll(' ', '-')
</script>

<template>
  <section class="card surface-card">
    <div class="section-head">
      <h2 class="card__title">{{ t(props.title) }}</h2>
      <button type="button" class="button button--secondary" @click="addItem">{{ t('新增') }}</button>
    </div>
    <div class="stack-list">
      <article v-for="(_, index) in items" :key="`${props.title}-${index}`" class="subcard">
        <div class="section-head">
          <strong>{{ t(props.label) }} {{ index + 1 }}</strong>
          <ConfirmButton label="移除" confirm-label="确认移除" @confirm="removeItem(index)" />
        </div>
        <div class="field">
          <label class="field__label" :for="fieldId(index)">{{ t(props.label) }}</label>
          <input :id="fieldId(index)" v-model="items[index]" class="input" :placeholder="props.placeholder">
        </div>
      </article>
    </div>
  </section>
</template>
