# CR-UI-VISUAL-2026-04-19-R5

## 目标
按“四项收口”完成 UI 最后一轮优化：
1) 移动端密度回弹
2) 长列表/数据行可读性
3) 暗色主题对比度
4) 登录页与业务页层级一致性

## 本轮改动
- `web/assets/css/control-plane-refresh-pages.css`
  - 收紧移动端 `@media (max-width: 960px/640px)` 的 topbar、标题、状态胶囊、容器内边距、登录区块尺寸。
  - 长列表行 `task-row/asset-row` 增加紧凑字体与省略处理，缩小行内 status-pill 尺寸。
  - 登录页标题字号 `24 -> 22`，并同步下调 feature 字号。
- `web/assets/css/control-plane-polish.css`
  - 修正移动端 `field-block` 回弹：`12x14 -> 8x9`。
  - 增加暗色对比度覆盖：`muted/caption/description` 文本与 `task/asset/report` 行背景边框增强。
  - 补充暗色 `status-note` 背景与边框可见度。
- `web/assets/css/control-plane-enhancements.css`
  - 移动端 `<=640` 下调辅助区块间距/内边距，移除大尺寸回弹源。

## 构建与部署验证
1. `npm --prefix web run build` -> `exit 0`
2. `docker compose up -d --build app` -> `exit 0`
3. `docker compose ps` -> `newapi-ai-check-in-app-1 Up (healthy)`

## 抽样结果
- Desktop `/dashboard`
  - 侧栏宽度 `196`
  - 顶栏高度 `50`
  - 按钮高度 `28`
  - 输入高度 `28`
  - 状态胶囊高度 `24`
- Desktop `/login`
  - 标题字号 `22`
  - 登录壳体 padding(top) `8`
  - 输入高度 `32`
  - 按钮高度 `28`
- Mobile `/dashboard` (390x844)
  - topbar padding(top/left) `8/10`
  - 移动导航触发器高度 `34`
  - 退出按钮尺寸 `30x30`
  - 页面标题字号 `19`
- Dark `/reports`
  - 列表行背景 `rgba(15, 23, 42, 0.74)`
  - 列表行边框 `rgba(148, 163, 184, 0.22)`
  - muted 文本 `rgba(226, 232, 240, 0.84)`

## 控制台检查
- 抽检页面无 `warn/error`：`/dashboard` `/main-checkin` `/schedules` `/aux-jobs` `/settings` `/login` `/reports`

## E2E 回归
- 命令：`npm --prefix web run test:e2e -- tests/e2e/task-center-density.desktop.spec.ts tests/e2e/task-center-shell-density.desktop.spec.ts tests/e2e/mobile-navigation.mobile.spec.ts`
- 结果：`6 passed (1.2m)`

## 追加复核（2026-04-19）
- 命令：`npm --prefix web run build`
  - 结果：`exit 0`
- 命令：`npm --prefix web run test:e2e`
  - 结果：`12 passed (1.3m)`
- 命令：`.venv/bin/pytest tests/test_control_plane_api.py tests/test_job_service.py`
  - 结果：`24 passed`
- 命令：`.venv/bin/ruff check .`
  - 结果：`All checks passed`
- 命令：`docker compose ps`
  - 结果：`newapi-ai-check-in-app-1 Up (healthy)`，端口 `39327`

## 视觉证据
- `docs/reviews/artifacts/ui-visual-review-2026-04-19-round2-optimize/dashboard-desktop.png`
- `docs/reviews/artifacts/ui-visual-review-2026-04-19-round2-optimize/main-checkin-desktop.png`
- `docs/reviews/artifacts/ui-visual-review-2026-04-19-round2-optimize/schedules-desktop.png`
- `docs/reviews/artifacts/ui-visual-review-2026-04-19-round2-optimize/aux-jobs-desktop.png`
- `docs/reviews/artifacts/ui-visual-review-2026-04-19-round2-optimize/settings-desktop.png`
- `docs/reviews/artifacts/ui-visual-review-2026-04-19-round2-optimize/login-desktop.png`
- `docs/reviews/artifacts/ui-visual-review-2026-04-19-round2-optimize/dashboard-mobile.png`
- `docs/reviews/artifacts/ui-visual-review-2026-04-19-round2-optimize/dashboard-dark.png`
- `docs/reviews/artifacts/ui-visual-review-2026-04-19-round2-optimize/reports-dark.png`
