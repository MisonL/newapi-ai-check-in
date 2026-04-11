<script setup lang="ts">
const props = withDefaults(defineProps<{
  label: string
  confirmLabel?: string
  timeoutMs?: number
}>(), {
  confirmLabel: '确认移除',
  timeoutMs: 3000,
})

const emit = defineEmits<{
  confirm: []
}>()

const { t } = useAppI18n()
const armed = ref(false)
let timer: ReturnType<typeof setTimeout> | null = null

const reset = () => {
  if (timer) {
    clearTimeout(timer)
    timer = null
  }
  armed.value = false
}

const handleClick = () => {
  if (!armed.value) {
    armed.value = true
    timer = setTimeout(reset, props.timeoutMs)
    return
  }
  reset()
  emit('confirm')
}

onBeforeUnmount(reset)
</script>

<template>
  <button type="button" class="button confirm-button" :class="{ 'confirm-button--armed': armed }" @click="handleClick">
    {{ t(armed ? props.confirmLabel : props.label) }}
  </button>
</template>
