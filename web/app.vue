<script setup lang="ts">
const route = useRoute()
const { locale, t } = useAppI18n()

const routeTitleMap: Record<string, string> = {
  '/dashboard': '首页',
  '/sites': '站点',
  '/accounts': '账号',
  '/today': '今日任务',
  '/reports': '历史与报表',
  '/incidents': '异常处理',
  '/main-checkin': '主链路配置',
  '/aux-jobs': '补充任务',
  '/schedules': '执行计划',
  '/settings': '系统设置',
  '/login': '登录',
}

useHead(() => ({
  title: `newapi.ai check-in · ${t(routeTitleMap[route.path] || '任务中心')}`,
  htmlAttrs: {
    lang: locale.value,
  },
  meta: [
    {
      name: 'description',
      content: t('管理多站点、多账号的每日签到任务与收益结果'),
    },
  ],
}))
</script>

<template>
  <NuxtPage />
</template>
