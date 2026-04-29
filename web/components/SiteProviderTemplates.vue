<script setup lang="ts">
export type SiteProviderTemplateId = 'standard' | 'browser' | 'legacy'

const emit = defineEmits<{
  select: [template: SiteProviderTemplateId]
}>()

const { t } = useAppI18n()

const templates = computed<Array<{
  id: SiteProviderTemplateId
  title: string
  description: string
  meta: string
}>>(() => [
  {
    id: 'standard',
    title: t('标准 NewAPI'),
    description: t('原生 new-api 签到接口，优先使用密码账号和 HTTP-only 执行链。'),
    meta: t('登录 /login，签到 /api/user/checkin'),
  },
  {
    id: 'browser',
    title: t('NewAPI + WAF'),
    description: t('目标站点存在 WAF Cookie 或前端挑战时，使用浏览器回退兼容链。'),
    meta: t('需要 WAF Cookie、Cookie 会话或浏览器登录态'),
  },
  {
    id: 'legacy',
    title: t('自定义兼容'),
    description: t('用于接口差异较大的站点，先记录差异，再通过探测确认能力。'),
    meta: t('适合迁移旧配置和人工排障'),
  },
])
</script>

<template>
  <section class="provider-template-panel">
    <div class="section-head">
      <div>
        <p class="workflow-console__eyebrow">{{ t('Provider 模板') }}</p>
        <h2 class="card__title">{{ t('先选站点类型，再填写地址') }}</h2>
      </div>
    </div>
    <div class="provider-template-panel__grid">
      <button
        v-for="template in templates"
        :key="template.id"
        type="button"
        class="provider-template-card"
        :data-testid="`site-provider-template-${template.id}`"
        @click="emit('select', template.id)"
      >
        <strong>{{ template.title }}</strong>
        <span>{{ template.description }}</span>
        <small>{{ template.meta }}</small>
      </button>
    </div>
  </section>
</template>
