# Task Center UI Density Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前 WebUI 从偏展示型管理后台收敛为更紧凑、更高频任务导向的签到工作台，同时保持现有业务流程和接口不变。

**Architecture:** 本次实现只修改 Nuxt WebUI，分成“全局 Shell 与设计 token”、“首页与今日任务主工作台”、“站点与账号资产页”、“异常与报表压缩与回归”四个批次。样式以现有全局 CSS 入口为主，页面只做必要结构调整，避免引入新的复杂组件体系。

**Tech Stack:** Nuxt 3, Vue 3, TypeScript, 全局 CSS, Playwright

---

## File Map

- `web/components/AppShell.vue`
  - 全局工作台框架、主导航、高级配置区、顶栏
- `web/components/PageHeader.vue`
  - 页面标题区与操作区
- `web/assets/css/control-plane-refresh.css`
  - Shell、顶栏、侧栏、全局 surface/card 密度
- `web/assets/css/control-plane-refresh-pages.css`
  - 各页面卡片、摘要条、统计卡、列表密度
- `web/pages/dashboard.vue`
  - 首页战情布局
- `web/pages/today.vue`
  - 今日任务主工作台
- `web/pages/sites.vue`
  - 站点资产页
- `web/pages/accounts.vue`
  - 账号资产页
- `web/pages/incidents.vue`
  - 异常页
- `web/pages/reports.vue`
  - 报表页
- `web/tests/e2e/mobile-navigation.mobile.spec.ts`
  - 移动端页面导航和关键控件回归
- `web/tests/e2e/task-center-density.desktop.spec.ts`
  - 首页与今日任务的桌面端密度回归
- `web/tests/e2e/task-center-proxy.desktop.spec.ts`
  - 代理 API 基本回归
- `web/tests/e2e/sites.desktop.spec.ts`
  - 站点页桌面端回归

---

### Task 1: 收紧全局 Shell 与密度 Token

**Files:**
- Modify: `web/components/AppShell.vue`
- Modify: `web/components/PageHeader.vue`
- Modify: `web/assets/css/control-plane-refresh.css`
- Modify: `web/assets/css/control-plane-refresh-pages.css`
- Test: `web/tests/e2e/mobile-navigation.mobile.spec.ts`

- [ ] **Step 1: 写一个先失败的移动端导航可见性测试**

```ts
test('移动端顶栏与页面导航在紧凑布局下仍可操作', async ({ page }) => {
  await login(page)
  await page.goto('/today')
  await waitForUiReady(page)

  await expect(page.getByRole('button', { name: /页面导航|Page Navigation/ })).toBeVisible()
  await expect(page.getByRole('button', { name: /退出登录|Logout/ })).toBeVisible()
})
```

- [ ] **Step 2: 跑测试确认它先失败或暴露现有布局约束**

Run: `npm --prefix web run test:e2e -- tests/e2e/mobile-navigation.mobile.spec.ts`
Expected: 至少一个断言失败，或现有选择器对重构后的紧凑布局不够稳定。

- [ ] **Step 3: 最小修改 Shell 结构，给后续紧凑布局留下稳定钩子**

```vue
<aside class="page-shell__sidebar">
  <div class="brand brand--panel brand--panel-compact">
    ...
  </div>
  <nav class="sidebar-nav sidebar-nav--compact">
    ...
  </nav>
</aside>

<header class="topbar topbar--compact">
  <div class="topbar__context">
    ...
  </div>
</header>
```

- [ ] **Step 4: 最小修改全局 CSS，先把尺寸压缩到目标区间**

```css
:root {
  --shell-sidebar-width: 240px;
  --shell-radius-xl: 22px;
  --shell-radius-lg: 16px;
  --shell-radius-md: 12px;
}

.sidebar-nav__link {
  min-height: 48px;
  padding: 10px 12px;
}

.topbar {
  height: 68px;
  padding: 0 20px;
}

.content-wrap {
  padding: 22px;
}

.page-summary-strip {
  margin-bottom: 16px;
  padding: 8px;
}
```

- [ ] **Step 5: 跑测试确认紧凑 Shell 通过**

Run: `npm --prefix web run test:e2e -- tests/e2e/mobile-navigation.mobile.spec.ts`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add web/components/AppShell.vue web/components/PageHeader.vue web/assets/css/control-plane-refresh.css web/assets/css/control-plane-refresh-pages.css web/tests/e2e/mobile-navigation.mobile.spec.ts
git commit -m "feat: compact task center shell density"
```

---

### Task 2: 首页与今日任务收敛为主工作台

**Files:**
- Modify: `web/pages/dashboard.vue`
- Modify: `web/pages/today.vue`
- Modify: `web/assets/css/control-plane-refresh-pages.css`
- Create: `web/tests/e2e/task-center-density.desktop.spec.ts`
- Test: `web/tests/e2e/task-center-proxy.desktop.spec.ts`

- [ ] **Step 1: 写一个先失败的桌面端今日任务主线测试**

```ts
test('今日任务页优先展示操作区、摘要条和紧凑任务列表', async ({ page }) => {
  await login(page)
  await page.goto('/today')
  await waitForUiReady(page)

  await expect(page.getByRole('button', { name: /执行待处理任务|Run Pending Tasks/ })).toBeVisible()
  await expect(page.getByText(/今日任务 1|Tasks Today 1/)).toBeVisible()
  await expect(page.getByText(/账号任务列表|Account Task List/)).toBeVisible()
})
```

- [ ] **Step 2: 跑测试确认先失败**

Run: `npm --prefix web run test:e2e -- tests/e2e/task-center-density.desktop.spec.ts`
Expected: 新断言未满足，或当前页面层级不符合新的主工作台结构。

- [ ] **Step 3: 最小修改首页，压低技术态信息，前置今日任务与异常**

```ts
const homeSummary = computed(() => [
  { label: `${t('今日待处理')} ${today.value?.today_pending || 0}`, state: (today.value?.today_pending || 0) > 0 ? 'info' : 'neutral' },
  { label: `${t('今日累计额度')} ${today.value?.today_quota_awarded || 0}`, state: (today.value?.today_quota_awarded || 0) > 0 ? 'configured' : 'neutral' },
  { label: `${t('部署模式')} ${formatDeployMode(status.value?.deploy_mode)}`, state: 'neutral' },
])
```

```vue
<div class="panel-grid dashboard-main-grid">
  <section class="card surface-card dashboard-panel dashboard-panel--wide">
    <div class="section-head">
      <h2 class="card__title">{{ t('今日任务快照') }}</h2>
    </div>
  </section>
  <section class="card surface-card dashboard-panel">
    <div class="section-head">
      <h2 class="card__title">{{ t('最近异常') }}</h2>
    </div>
  </section>
</div>
```

- [ ] **Step 4: 最小修改今日任务页，把任务卡片流收敛为紧凑列表**

```vue
<section class="card surface-card task-table-card">
  <div class="task-table-card__header">
    <h2 class="card__title">{{ t('账号任务列表') }}</h2>
  </div>
  <div class="task-table">
    <article v-for="task in visibleTasks" :key="task.id" class="task-row">
      <div class="task-row__main">
        <strong>{{ task.account_display_name }}</strong>
        <span>{{ task.site_name }}</span>
      </div>
      <div class="task-row__meta">
        <StatusBadge :label="t(task.status)" :state="taskState(task.status)" />
      </div>
    </article>
  </div>
</section>
```

- [ ] **Step 5: 最小修改页面 CSS，压缩统计卡、筛选器和任务列表**

```css
.stat-card {
  padding: 14px 16px;
}

.stat-card__value {
  font-size: 26px;
}

.task-row {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) auto auto;
  gap: 12px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--shell-outline);
}
```

- [ ] **Step 6: 跑桌面端与代理基础回归**

Run: `npm --prefix web run test:e2e -- tests/e2e/task-center-density.desktop.spec.ts tests/e2e/task-center-proxy.desktop.spec.ts`
Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add web/pages/dashboard.vue web/pages/today.vue web/assets/css/control-plane-refresh-pages.css web/tests/e2e/task-center-density.desktop.spec.ts web/tests/e2e/task-center-proxy.desktop.spec.ts
git commit -m "feat: refocus dashboard and today as compact task workspace"
```

---

### Task 3: 站点与账号页改为更实用的高密度资产页

**Files:**
- Modify: `web/pages/sites.vue`
- Modify: `web/pages/accounts.vue`
- Modify: `web/assets/css/control-plane-refresh-pages.css`
- Test: `web/tests/e2e/sites.desktop.spec.ts`
- Test: `web/tests/e2e/mobile-navigation.mobile.spec.ts`

- [ ] **Step 1: 写一个先失败的站点页桌面密度测试**

```ts
test('站点页在桌面端同时展示录入表单和紧凑站点清单', async ({ page }) => {
  await login(page)
  await page.goto('/sites')
  await waitForUiReady(page)

  await expect(page.getByRole('heading', { name: /站点清单|Site List/ })).toBeVisible()
  await expect(page.getByRole('button', { name: /创建站点|Create Site/ })).toBeVisible()
})
```

- [ ] **Step 2: 跑测试确认先失败**

Run: `npm --prefix web run test:e2e -- tests/e2e/sites.desktop.spec.ts`
Expected: 当前布局断言不足或页面结构不满足新的高密资产页目标。

- [ ] **Step 3: 最小修改站点页，把右侧卡片堆叠改成紧凑清单**

```vue
<section class="card surface-card asset-list-card">
  <div class="section-head">
    <h2 class="card__title">{{ t('站点清单') }}</h2>
  </div>
  <div class="asset-list">
    <article v-for="site in sites" :key="site.id" class="asset-row">
      <div class="asset-row__title">
        <strong>{{ site.name }}</strong>
        <span>{{ site.base_url }}</span>
      </div>
      <div class="asset-row__badges">
        <StatusBadge :label="site.enabled ? t('已启用') : t('已禁用')" :state="site.enabled ? 'configured' : 'disabled'" />
      </div>
    </article>
  </div>
</section>
```

- [ ] **Step 4: 最小修改账号页，把账号信息改成紧凑资产列表**

```vue
<section class="card surface-card asset-list-card">
  <div class="section-head">
    <h2 class="card__title">{{ t('账号清单') }}</h2>
  </div>
  <div class="asset-list">
    <article v-for="account in visibleAccounts" :key="account.id" class="asset-row">
      <div class="asset-row__title">
        <strong>{{ account.display_name || account.username }}</strong>
        <span>{{ siteName(account.site_id) }} / {{ accountIdentity(account) }}</span>
      </div>
      <div class="asset-row__stats">
        <StatusBadge :label="authModeLabel(account.auth_mode)" :state="authModeState(account.auth_mode)" />
        <StatusBadge :label="t(account.last_checkin_status)" :state="checkinState(account.last_checkin_status)" />
      </div>
    </article>
  </div>
</section>
```

- [ ] **Step 5: 最小修改资产页 CSS，统一列表行样式**

```css
.asset-list {
  display: grid;
  gap: 8px;
}

.asset-row {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(220px, auto) auto;
  gap: 12px;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid var(--shell-outline);
  border-radius: 12px;
}
```

- [ ] **Step 6: 跑站点与移动端账号回归**

Run: `npm --prefix web run test:e2e -- tests/e2e/sites.desktop.spec.ts tests/e2e/mobile-navigation.mobile.spec.ts`
Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add web/pages/sites.vue web/pages/accounts.vue web/assets/css/control-plane-refresh-pages.css web/tests/e2e/sites.desktop.spec.ts web/tests/e2e/mobile-navigation.mobile.spec.ts
git commit -m "feat: compact site and account asset pages"
```

---

### Task 4: 异常与报表补齐紧凑布局并完成回归

**Files:**
- Modify: `web/pages/incidents.vue`
- Modify: `web/pages/reports.vue`
- Modify: `web/assets/css/control-plane-refresh-pages.css`
- Test: `web/tests/e2e/zz-reports.desktop.spec.ts`
- Test: `web/tests/e2e/task-center-proxy.desktop.spec.ts`

- [ ] **Step 1: 写一个先失败的报表页紧凑信息测试**

```ts
test('报表页保留摘要和站点汇总，同时压缩统计块高度', async ({ page }) => {
  await login(page)
  await page.goto('/reports')
  await waitForUiReady(page)

  await expect(page.getByRole('heading', { name: /站点汇总|Site Summary/ })).toBeVisible()
  await expect(page.getByRole('button', { name: /导出报表 CSV|Export Report CSV/ })).toBeVisible()
})
```

- [ ] **Step 2: 跑测试确认先失败**

Run: `npm --prefix web run test:e2e -- tests/e2e/zz-reports.desktop.spec.ts`
Expected: 当前结构或断言不能稳定表达目标布局。

- [ ] **Step 3: 最小修改异常页，把筛选区和空状态区压缩**

```css
.incident-list-card .panel-grid--two {
  gap: 12px;
}

.dashboard-empty {
  min-height: 140px;
  padding: 16px;
}
```

```vue
<section class="card surface-card incident-list-card">
  <div class="section-head">
    <h2 class="card__title">{{ t('异常列表') }}</h2>
  </div>
</section>
```

- [ ] **Step 4: 最小修改报表页，压缩统计卡和列表区块**

```css
.reports-summary-grid .stat-card {
  padding: 12px 14px;
}

.reports-day-row {
  display: grid;
  grid-template-columns: 120px repeat(5, minmax(0, 1fr));
  gap: 10px;
  padding: 10px 12px;
}
```

```vue
<section class="card surface-card reports-history-card">
  <div class="stack-list">
    <article v-for="day in visibleDays" :key="day.task_date" class="reports-day-row">
      <strong>{{ formatDate(day.task_date) }}</strong>
      <span>{{ day.total_tasks }}</span>
      <span>{{ day.success_tasks }}</span>
      <span>{{ day.failed_tasks }}</span>
      <span>{{ day.total_quota_awarded }}</span>
    </article>
  </div>
</section>
```

- [ ] **Step 5: 跑报表与代理回归**

Run: `npm --prefix web run test:e2e -- tests/e2e/zz-reports.desktop.spec.ts tests/e2e/task-center-proxy.desktop.spec.ts`
Expected: PASS

- [ ] **Step 6: 跑一次完整 WebUI E2E 回归**

Run: `npm --prefix web run test:e2e`
Expected: 全部 PASS

- [ ] **Step 7: 跑一次生产构建验证**

Run: `npm --prefix web run build`
Expected: build 成功，无类型或 SSR 构建错误

- [ ] **Step 8: 提交**

```bash
git add web/pages/incidents.vue web/pages/reports.vue web/assets/css/control-plane-refresh-pages.css web/tests/e2e/zz-reports.desktop.spec.ts web/tests/e2e/task-center-proxy.desktop.spec.ts
git commit -m "feat: compact incidents and reports views"
```

---

## Self-Review

- Spec coverage:
  - 全局 Shell 与 token：Task 1
  - 首页与今日任务：Task 2
  - 站点与账号：Task 3
  - 异常与报表：Task 4
- Placeholder scan:
  - 未使用占位词或“后续再补”表述
  - 每个任务都包含文件、测试和命令
- Type consistency:
  - 计划中使用的页面与测试文件均来自当前代码库
  - 代码片段只围绕现有组件和类名扩展，没有引入新的未定义依赖
