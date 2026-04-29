<script setup lang="ts">
const props = defineProps<{
  siteCount: number
  enabledSiteCount: number
  accountCount: number
  enabledAccountCount: number
  todayTaskCount: number
}>()

const { t } = useAppI18n()

const readiness = computed(() => [
  {
    title: t('保存后测试站点'),
    description: props.enabledSiteCount
      ? t('已有 {count} 个启用站点，可以继续录入账号', { count: props.enabledSiteCount })
      : t('先创建一个标准 NewAPI 站点并执行探测'),
    state: props.enabledSiteCount ? 'success' : 'unconfigured',
    to: '/sites',
    action: t('去配置站点'),
  },
  {
    title: t('保存后测试账号'),
    description: props.enabledAccountCount
      ? t('已有 {count} 个启用账号，可以生成今日任务', { count: props.enabledAccountCount })
      : t('为站点录入密码或 Cookie 账号后执行账号测试'),
    state: props.enabledAccountCount ? 'success' : 'unconfigured',
    to: '/accounts',
    action: t('去配置账号'),
  },
  {
    title: t('生成今日任务'),
    description: props.todayTaskCount
      ? t('今日已生成 {count} 条任务，可进入任务页执行', { count: props.todayTaskCount })
      : t('站点和账号就绪后生成今天的签到任务'),
    state: props.todayTaskCount ? 'configured' : 'neutral',
    to: '/today',
    action: t('去今日任务'),
  },
])

const providerTemplates = computed(() => [
  {
    title: t('标准 NewAPI'),
    description: t('适合原生 new-api 或 OneAPI 兼容站点，优先走 HTTP 接口签到。'),
  },
  {
    title: t('NewAPI + WAF'),
    description: t('适合有 WAF Cookie 的站点，先保存站点，再用 Cookie 或浏览器回退账号验证。'),
  },
  {
    title: t('自定义兼容'),
    description: t('用于接口路径或登录策略不固定的站点，先保留备注再做预检。'),
  },
])
</script>

<template>
  <section class="onboarding-guide surface-card" data-testid="setup-onboarding-guide">
    <div class="section-head">
      <div>
        <p class="workflow-console__eyebrow">{{ t('接入向导') }}</p>
        <h2 class="card__title">{{ t('按 Provider 模板完成一次可执行接入') }}</h2>
      </div>
      <StatusBadge
        :label="t('站点 {sites} 个，账号 {accounts} 个', { sites: props.siteCount, accounts: props.accountCount })"
        :state="props.enabledSiteCount && props.enabledAccountCount ? 'success' : 'unconfigured'"
        :dot="false"
      />
    </div>
    <div class="onboarding-guide__providers">
      <article v-for="provider in providerTemplates" :key="provider.title" class="onboarding-guide__provider">
        <strong>{{ provider.title }}</strong>
        <p>{{ provider.description }}</p>
      </article>
    </div>
    <div class="onboarding-guide__steps">
      <NuxtLink v-for="item in readiness" :key="item.title" class="onboarding-guide__step" :to="item.to">
        <div>
          <strong>{{ item.title }}</strong>
          <p>{{ item.description }}</p>
        </div>
        <StatusBadge :label="item.action" :state="item.state" :dot="false" />
      </NuxtLink>
    </div>
  </section>
</template>
