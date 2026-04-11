<script setup lang="ts">
const route = useRoute()
const { locale, t } = useAppI18n()

const routeTitleMap: Record<string, string> = {
  '/dashboard': '仪表盘',
  '/main-checkin': '主签到',
  '/aux-jobs': '辅助任务',
  '/schedules': '调度计划',
  '/settings': '系统设置',
  '/login': '登录',
}

useHead(() => ({
  title: `newapi.ai check-in · ${t(routeTitleMap[route.path] || '控制台')}`,
  htmlAttrs: {
    lang: locale.value,
  },
  meta: [
    {
      name: 'description',
      content: t('统一管理签到配置、调度计划和运行日志'),
    },
  ],
}))
</script>

<template>
  <NuxtPage />
</template>
