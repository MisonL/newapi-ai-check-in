<script setup lang="ts">
const props = withDefaults(defineProps<{
  label: string
  state?: string
  dot?: boolean
}>(), {
  state: 'neutral',
  dot: true,
})

const stateMeta: Record<string, { tone: string; pulse?: boolean }> = {
  neutral: { tone: 'neutral' },
  info: { tone: 'info' },
  running: { tone: 'info', pulse: true },
  queued: { tone: 'warn' },
  success: { tone: 'success' },
  failed: { tone: 'danger' },
  skipped: { tone: 'neutral' },
  enabled: { tone: 'success' },
  disabled: { tone: 'neutral' },
  configured: { tone: 'success' },
  unconfigured: { tone: 'warn' },
  idle: { tone: 'neutral' },
}

const meta = computed(() => stateMeta[props.state] || stateMeta.neutral)
</script>

<template>
  <span
    class="status-pill status-pill--semantic"
    :class="[`status-pill--${meta.tone}`, { 'status-pill--pulse': meta.pulse }]"
  >
    <span v-if="props.dot" class="status-pill__dot" aria-hidden="true" />
    <span>{{ props.label }}</span>
  </span>
</template>
