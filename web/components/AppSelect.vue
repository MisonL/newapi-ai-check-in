<script setup lang="ts">
type SelectValue = string | number | boolean | null
type SelectOption = {
  label: string
  value: SelectValue
}

const props = withDefaults(defineProps<{
  id?: string
  options: SelectOption[]
  label?: string
  name?: string
  placeholder?: string
  size?: 'md' | 'sm'
}>(), {
  id: '',
  label: '',
  name: '',
  placeholder: '',
  size: 'md',
})

const model = defineModel<SelectValue>({ required: true })
const { t } = useAppI18n()

const open = ref(false)
const root = ref<HTMLElement | null>(null)

const selectedOption = computed(() => props.options.find((item) => item.value === model.value) || null)
const triggerLabel = computed(() => selectedOption.value?.label || props.placeholder)

const close = () => {
  open.value = false
}

const toggle = () => {
  open.value = !open.value
}

const selectOption = (value: SelectValue) => {
  model.value = value
  close()
}

const onDocumentPointerDown = (event: Event) => {
  if (!root.value) {
    return
  }
  if (!root.value.contains(event.target as Node)) {
    close()
  }
}

const onTriggerKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    toggle()
    return
  }
  if (event.key === 'Escape') {
    close()
  }
}

onMounted(() => {
  document.addEventListener('pointerdown', onDocumentPointerDown)
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onDocumentPointerDown)
})
</script>

<template>
  <div ref="root" class="app-select" :class="`app-select--${props.size}`">
    <input v-if="props.name" type="hidden" :name="props.name" :value="model == null ? '' : String(model)">
    <button
      type="button"
      :id="props.id"
      class="app-select__trigger"
      :aria-expanded="open ? 'true' : 'false'"
      @click="toggle"
      @keydown="onTriggerKeydown"
    >
      <span v-if="props.label" class="app-select__sr">{{ t(props.label) }}</span>
      <span v-if="$slots.prefix" class="app-select__prefix">
        <slot name="prefix" />
      </span>
      <span class="app-select__value">{{ t(triggerLabel) }}</span>
      <span class="app-select__chevron" aria-hidden="true" />
    </button>
    <div v-if="open" class="app-select__menu">
      <button
        v-for="item in props.options"
        :key="`${item.label}-${String(item.value)}`"
        type="button"
        class="app-select__option"
        :class="{ 'app-select__option--active': item.value === model }"
        @click="selectOption(item.value)"
      >
        {{ t(item.label) }}
      </button>
    </div>
  </div>
</template>
