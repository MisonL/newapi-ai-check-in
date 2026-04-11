# 当前状态审计 2026-04-11

## 范围

- 控制面认证与会话边界
- 仪表盘与调度页观测信息
- WebUI 中英文文案完整性
- 本地调度与 GitHub Actions 双调度风险
- Docker 默认配置中的敏感信息口径

## 发现

- 仓库同时存在本地 APScheduler 与 GitHub Actions 定时 workflow，存在重复执行风险。
- `docker-compose.yml` 原先内置固定管理员密码、会话密钥和内部令牌，不符合安全基线。
- 状态接口原先未暴露本地调度开关，页面只能通过文案提示风险，无法反映真实运行模式。
- 英文环境下部分空状态和设置说明文案存在回落到中文的问题。
- 部署入口原先只有 `CONTROL_PLANE_SCHEDULER_ENABLED` 布尔开关，缺少面向运维的显式双模式口径，容易误配。

## 已处理

- 新增 `CONTROL_PLANE_SCHEDULER_ENABLED`，可显式关闭本地调度。
- 状态接口新增 `scheduler_enabled`，仪表盘与调度页展示当前本地调度状态。
- 调度关闭时，`next_run_times()` 返回空计划，避免 UI 显示虚假的下次触发时间。
- `require_internal_token` 在内部令牌未配置时返回显式错误，避免空令牌绕过。
- `docker-compose.yml` 改为从环境变量读取敏感配置，不再在源码中硬编码。
- 新增 `.env.example` 作为本地部署模板。
- 新增 `CONTROL_PLANE_DEPLOY_MODE`，显式支持 `control_plane` 与 `github_actions` 两种部署模式。
- 新增 `.env.control-plane.example` 与 `.env.github-actions.example`，分别对应两种部署模式。
- README 增补 `.env` 启动方式与调度模式说明。
- 补齐中英文文案缺口，并修复侧栏副标题 `Operations Console` 在中文界面未本地化的问题。

## 验证记录

- 命令：`npm --prefix web run build`
  - 退出码：0
  - 结论：通过
- 命令：`.venv/bin/pytest tests/test_control_plane_api.py tests/test_job_service.py tests/test_control_plane_storage.py tests/test_notify.py`
  - 退出码：0
  - 结论：19 通过，1 跳过
- 命令：`env CONTROL_PLANE_ADMIN_PASSWORD=admin123 CONTROL_PLANE_SESSION_SECRET=test-session-secret CONTROL_PLANE_INTERNAL_TOKEN=test-internal-token CONTROL_PLANE_SCHEDULER_ENABLED=false HOST_PORT=3300 sh -c 'docker compose up -d --build && for i in $(seq 1 20); do status=$(docker inspect -f "{{.State.Health.Status}}" newapi-ai-check-in-app-1 2>/dev/null || true); echo "health=$status"; if [ "$status" = healthy ]; then break; fi; sleep 2; done; docker compose ps'`
  - 退出码：0
  - 结论：镜像重建成功，容器健康检查为 `healthy`，`3300 -> 3000` 端口映射正常
- 命令：`env CONTROL_PLANE_DEPLOY_MODE=control_plane CONTROL_PLANE_ADMIN_PASSWORD=admin123 CONTROL_PLANE_SESSION_SECRET=test-session-secret CONTROL_PLANE_INTERNAL_TOKEN=test-internal-token HOST_PORT=3301 sh -c 'docker compose up -d --build && for i in $(seq 1 20); do status=$(docker inspect -f "{{.State.Health.Status}}" newapi-ai-check-in-app-1 2>/dev/null || true); echo "health=$status"; if [ "$status" = healthy ]; then break; fi; sleep 2; done; curl -sf http://127.0.0.1:3301/api/auth/session && docker compose down'`
  - 退出码：0
  - 结论：`control_plane` 模式可正常启动，健康检查通过
- 命令：`env CONTROL_PLANE_DEPLOY_MODE=github_actions CONTROL_PLANE_ADMIN_PASSWORD=admin123 CONTROL_PLANE_SESSION_SECRET=test-session-secret CONTROL_PLANE_INTERNAL_TOKEN=test-internal-token HOST_PORT=3300 sh -c 'docker compose up -d --build && for i in $(seq 1 20); do status=$(docker inspect -f "{{.State.Health.Status}}" newapi-ai-check-in-app-1 2>/dev/null || true); echo "health=$status"; if [ "$status" = healthy ]; then break; fi; sleep 2; done; docker compose ps'`
  - 退出码：0
  - 结论：`github_actions` 模式可正常启动，健康检查通过
- 浏览器回归：
  - 范围：`/login`、`/dashboard`、`/main-checkin`、`/aux-jobs`、`/schedules`、`/settings`
  - 结论：通过；已验证登录、英文与中文切换、本地调度禁用态文案、部署模式显示、空状态展示与设置页本地化修复，控制台 `error/warn = 0`

## 剩余关注点

- 若生产环境继续使用 GitHub Actions，应明确关闭本地调度。
- 若生产环境仅使用本地控制面调度，应停用仓库 workflow 的定时触发。
