<script setup lang="ts">
const props = withDefaults(defineProps<{
  id: string
  name?: string
  autocomplete?: string
  autofocus?: boolean
  placeholder?: string
  disabled?: boolean
  spellcheck?: boolean
}>(), {
  name: '',
  autocomplete: 'off',
  autofocus: false,
  placeholder: '',
  disabled: false,
  spellcheck: false,
})

const model = defineModel<string>({ required: true })
const visible = ref(false)
const { t } = useAppI18n()
</script>

<template>
  <div class="input-group">
    <input
      :id="props.id"
      v-model="model"
      :name="props.name || undefined"
      :autocomplete="props.autocomplete"
      :autofocus="props.autofocus"
      class="input input-group__control"
      :type="visible ? 'text' : 'password'"
      :placeholder="props.placeholder"
      :disabled="props.disabled"
      :spellcheck="props.spellcheck"
    >
    <button
      type="button"
      class="input-group__action"
      :aria-label="t(visible ? '隐藏密码' : '显示密码')"
      :aria-pressed="visible ? 'true' : 'false'"
      :disabled="props.disabled"
      @click="visible = !visible"
    >
      <AppIcon :name="visible ? 'eye-off' : 'eye'" :size="16" />
    </button>
  </div>
</template>
