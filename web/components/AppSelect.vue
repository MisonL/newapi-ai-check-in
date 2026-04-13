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
  disabled?: boolean
  size?: 'md' | 'sm'
}>(), {
  id: '',
  label: '',
  name: '',
  placeholder: '',
  disabled: false,
  size: 'md',
})

const model = defineModel<SelectValue>({ required: true })
const { t } = useAppI18n()

const open = ref(false)
const root = ref<HTMLElement | null>(null)
const trigger = ref<HTMLButtonElement | null>(null)
const optionRefs = ref<HTMLButtonElement[]>([])

const selectedOption = computed(() => props.options.find((item) => item.value === model.value) || null)
const selectedIndex = computed(() => props.options.findIndex((item) => item.value === model.value))
const triggerLabel = computed(() => selectedOption.value?.label || props.placeholder)
const menuId = computed(() => props.id ? `${props.id}-menu` : undefined)
const activeIndex = ref(-1)
const isDisabled = computed(() => props.disabled || !props.options.length)

const setOptionRef = (element: HTMLButtonElement | null, index: number) => {
  if (!element) {
    return
  }
  optionRefs.value[index] = element
}

const focusOption = (index: number) => {
  nextTick(() => {
    optionRefs.value[index]?.focus()
  })
}

const syncActiveIndex = () => {
  if (!props.options.length) {
    activeIndex.value = -1
    return
  }
  activeIndex.value = selectedIndex.value >= 0 ? selectedIndex.value : 0
}

const close = (focusTrigger = false) => {
  open.value = false
  activeIndex.value = -1
  if (focusTrigger) {
    nextTick(() => {
      trigger.value?.focus()
    })
  }
}

const openMenu = (focusSelected = false) => {
  if (open.value || isDisabled.value) {
    return
  }
  open.value = true
  syncActiveIndex()
  if (focusSelected && activeIndex.value >= 0) {
    focusOption(activeIndex.value)
  }
}

const toggle = () => {
  if (isDisabled.value) {
    return
  }
  if (open.value) {
    close()
    return
  }
  openMenu(false)
}

const selectOption = (value: SelectValue) => {
  model.value = value
  close(true)
}

const moveActiveOption = (direction: 1 | -1) => {
  if (isDisabled.value) {
    return
  }
  if (!open.value) {
    openMenu(true)
    return
  }
  const startIndex = activeIndex.value >= 0 ? activeIndex.value : 0
  const nextIndex = (startIndex + direction + props.options.length) % props.options.length
  activeIndex.value = nextIndex
  focusOption(nextIndex)
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
  if (isDisabled.value) {
    return
  }
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    if (open.value) {
      close()
      return
    }
    openMenu(true)
    return
  }
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    moveActiveOption(1)
    return
  }
  if (event.key === 'ArrowUp') {
    event.preventDefault()
    moveActiveOption(-1)
    return
  }
  if (event.key === 'Escape') {
    close()
  }
}

const onOptionKeydown = (event: KeyboardEvent, index: number, value: SelectValue) => {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    moveActiveOption(1)
    return
  }
  if (event.key === 'ArrowUp') {
    event.preventDefault()
    moveActiveOption(-1)
    return
  }
  if (event.key === 'Home') {
    event.preventDefault()
    activeIndex.value = 0
    focusOption(0)
    return
  }
  if (event.key === 'End') {
    event.preventDefault()
    activeIndex.value = props.options.length - 1
    focusOption(activeIndex.value)
    return
  }
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    selectOption(value)
    return
  }
  if (event.key === 'Escape') {
    event.preventDefault()
    close(true)
    return
  }
  if (event.key === 'Tab') {
    close()
    return
  }
  activeIndex.value = index
}

watchEffect(() => {
  if (isDisabled.value && open.value) {
    close()
  }
})

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
      ref="trigger"
      type="button"
      :id="props.id"
      class="app-select__trigger"
      :disabled="isDisabled"
      :aria-expanded="open ? 'true' : 'false'"
      aria-haspopup="listbox"
      :aria-controls="menuId"
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
    <div v-if="open" :id="menuId" class="app-select__menu" role="listbox">
      <button
        v-for="(item, index) in props.options"
        :key="`${item.label}-${String(item.value)}`"
        type="button"
        class="app-select__option"
        :class="{ 'app-select__option--active': item.value === model }"
        role="option"
        :aria-selected="item.value === model ? 'true' : 'false'"
        :tabindex="activeIndex === index ? 0 : -1"
        @focus="activeIndex = index"
        :ref="(element) => setOptionRef(element as HTMLButtonElement | null, index)"
        @click="selectOption(item.value)"
        @keydown="onOptionKeydown($event, index, item.value)"
      >
        {{ t(item.label) }}
      </button>
    </div>
  </div>
</template>
