# new-api 多站点签到任务系统重构设计

## 1. 背景与结论

当前仓库已经具备 Docker 部署、登录保护、任务调度、运行日志和通知能力，但产品主线仍然围绕“控制台配置”和“脚本执行”展开。现有一级信息架构是：

- Dashboard
- Main Check-in
- Aux Jobs
- Schedules
- Settings

这与目标产品存在根本偏差。目标产品应是“为多站点、多账号 `new-api` 自动签到专门设计的任务系统”，核心对象应是：

- 站点
- 账号
- 今日签到任务
- 签到结果
- 累计额度
- 异常处理

因此，本轮重构不是局部页面美化，而是产品对象模型、顶层设计、执行主链和 UI 语义的整体纠偏。

## 2. 目标产品定义

产品定位：

- 面向多个 `new-api` 站点
- 管理多个站点账号
- 每日自动完成签到
- 汇总签到结果、额度收益与异常

非目标：

- 不是通用爬虫调度平台
- 不是以 JSON 配置为中心的脚本控制台
- 不是把任意第三方任务都塞进主导航的大杂烩

## 3. 设计依据

基于上游 `new-api` 源码，签到主链是平台内用户签到，而不是 API token 或通用 provider 脚本：

- 登录：`POST /api/user/login`
- 查询签到状态：`GET /api/user/checkin`
- 执行签到：`POST /api/user/checkin`

相关源码依据：

- `https://github.com/QuantumNous/new-api/blob/main/router/api-router.go`
- `https://github.com/QuantumNous/new-api/blob/main/controller/user.go`
- `https://github.com/QuantumNous/new-api/blob/main/controller/checkin.go`
- `https://github.com/QuantumNous/new-api/blob/main/model/checkin.go`
- `https://github.com/QuantumNous/new-api/blob/main/setting/operation_setting/checkin_setting.go`

上游签到返回的关键业务事实包括：

- 是否已签到
- 当月签到记录
- 本月签到次数
- 累计签到次数
- 累计获得额度
- 单次签到获得额度

这决定了本项目未来的主链必须采用“登录会话 + 查签到状态 + 再执行签到 + 记录收益”的 API-first 模式。

## 4. 当前系统问题

### 4.1 产品层问题

- 一级导航仍然是控制台语义，而不是任务中心语义。
- 首页展示的是运行状态和调度指标，而不是“今日应签、已签、异常、收益”。
- 主签到页仍然要求用户直接编辑账号 JSON、Provider JSON、代理 JSON。
- `996`、`qaq.al`、`Linux.do` 被放在主产品一级入口，稀释了 `new-api` 多站点签到主线。

### 4.2 架构层问题

- 当前后端核心对象仍是 `ConfigDomain` 配置域，而不是站点、账号、任务和签到结果。
- 任务执行器按“脚本类型”路由，而不是按“站点兼容等级”和“签到生命周期”执行。
- 运行日志存在，但缺少“任务阶段语义”和“异常类型语义”。

### 4.3 UI/UX 问题

- 页面语义围绕“配置”和“控制面”，不围绕“今日任务”。
- 状态标签很多，但关键 KPI 不清晰。
- 用户需要理解太多底层术语，才能完成日常使用。
- 视觉风格偏“运维后台”，不够“签到任务中心”。

## 5. 新的产品对象模型

### 5.1 Site

表示一个 `new-api` 实例。

建议字段：

- `id`
- `name`
- `base_url`
- `enabled`
- `compatibility_level`
- `checkin_enabled_detected`
- `checkin_min_quota_detected`
- `checkin_max_quota_detected`
- `login_mode`
- `turnstile_required`
- `two_factor_possible`
- `last_probe_at`
- `last_probe_status`

### 5.2 Account

表示站点下的一个用户账号。

建议字段：

- `id`
- `site_id`
- `username`
- `password`
- `status`
- `session_status`
- `last_login_at`
- `last_checkin_date`
- `last_checkin_status`
- `total_checkins`
- `total_quota_awarded`

### 5.3 DailyTask

表示某站点某账号在某一天的签到任务。

建议字段：

- `id`
- `site_id`
- `account_id`
- `task_date`
- `status`
- `trigger_type`
- `attempt_count`
- `started_at`
- `finished_at`
- `error_code`
- `error_message`

### 5.4 CheckinResult

表示一次签到结果。

建议字段：

- `task_id`
- `checked_in_today_before_run`
- `quota_awarded`
- `checkin_date`
- `raw_status_payload`
- `raw_checkin_payload`

### 5.5 Incident

表示需要人工或系统处理的异常。

建议字段：

- `id`
- `site_id`
- `account_id`
- `type`
- `severity`
- `resolved`
- `resolution_action`
- `first_seen_at`
- `last_seen_at`

## 6. 新的顶层信息架构

一级导航重构为：

- `首页`
- `站点`
- `账号`
- `今日任务`
- `历史与报表`
- `异常处理`
- `系统设置`

旧页面迁移策略：

- `dashboard`：升级为新首页
- `main-checkin`：降级为高级配置页
- `aux-jobs`：降级为插件或扩展页
- `schedules`：降级为自动执行策略页
- `settings`：保留为系统设置页

## 7. 签到机制重构

### 7.1 标准主链

每个账号每日签到任务按如下流程执行：

1. 站点探测
2. 用户名密码登录
3. 获取会话 cookie
4. 查询签到状态
5. 判断是否已签
6. 未签则执行签到
7. 记录奖励结果
8. 更新日报和通知

### 7.2 结果分类

结果状态必须业务化，不允许只保留原始日志：

- `success`
- `already_checked`
- `site_checkin_disabled`
- `login_failed`
- `password_invalid`
- `turnstile_required`
- `two_factor_required`
- `session_expired`
- `api_incompatible`
- `site_unreachable`
- `unexpected_response`
- `rate_limited`

### 7.3 兼容等级

站点分层处理：

- `L1` 标准兼容：标准登录 + 标准签到接口
- `L2` 轻度兼容：有少量差异，但仍可 API 驱动
- `L3` 浏览器兼容：需要浏览器辅助
- `L4` 不兼容：不进入自动签到主链

## 8. 前端改造方案

### 8.1 首页

首页应改造成“今日签到任务战情板”，第一屏只保留：

- 今日应签到账号数
- 今日已成功
- 今日已跳过
- 今日异常
- 今日累计额度

第二屏展示：

- 今日任务列表
- 异常类型分布
- 站点成功率
- 最近失败账号

### 8.2 站点页

展示：

- 站点名称
- 域名
- 兼容等级
- 是否启用签到
- 奖励区间
- 账号数量
- 最近状态

### 8.3 账号页

展示：

- 所属站点
- 用户名
- 登录状态
- 今日状态
- 最近成功
- 累计签到
- 累计额度

### 8.4 今日任务页

这是未来主工作页，应支持：

- 全部 / 待执行 / 成功 / 跳过 / 阻塞 / 失败筛选
- 任务阶段展示
- 单任务详情抽屉
- 手动重试

### 8.5 历史与报表页

展示：

- 月历签到
- 按账号收益趋势
- 按站点成功率趋势
- 每日累计额度

### 8.6 异常处理页

聚合：

- 登录失败
- 验证码阻塞
- 2FA 阻塞
- 接口不兼容
- 站点关闭签到

## 9. 视觉设计方向

视觉目标：

- 从“控制台”升级为“任务中心”
- 从“配置编辑器”升级为“今日任务面板”

建议：

- 强化首屏 KPI
- 减少 JSON 主交互
- 使用任务卡片、状态阶段条、异常列表
- 成功、跳过、待处理、失败采用清晰语义色

## 10. 后端架构改造方向

当前的 `control_plane` 应从“配置域中心”转向“任务域中心”。

建议新增或重构的领域服务：

- `site_service`
- `account_service`
- `site_probe_service`
- `checkin_task_service`
- `checkin_runtime_service`
- `incident_service`
- `report_service`

执行器层建议改为：

- `standard_newapi_adapter`
- `browser_fallback_adapter`
- `legacy_plugin_adapter`

## 11. 迁移策略

### Phase 1

- 先改前端信息架构
- 首页改造成任务中心
- 新增站点、账号、今日任务、报表、异常页骨架
- 旧页面降级但暂不删除

### Phase 2

- 引入 `Site`、`Account`、`DailyTask` 等新对象
- 增加站点探测与签到主链 API
- 逐步弱化 `main_checkin` 配置页

### Phase 3

- 上线标准 API-first 签到主链
- 浏览器兼容链只保留为回退层
- 辅助任务迁移为插件区

## 12. 本轮开发切入点

本轮直接开始的第一阶段改造范围：

- 编写本设计文档
- 改造一级导航和页面命名
- 将 `dashboard` 改造成“首页”
- 新增以下页面骨架：
  - `sites`
  - `accounts`
  - `today`
  - `reports`
  - `incidents`
- 将旧页面降级为二级或兼容入口

## 13. 验收标准

第一阶段验收标准：

- 用户进入系统后，首页语义已是“签到任务中心”
- 一级导航不再出现“Main Check-in / Aux Jobs / Schedules”作为主产品主线
- 新页面骨架可访问
- 登录页与全局标题文案已切换到新产品定位
- 旧页面仍可访问，但其角色已降级为高级配置或扩展能力

## 14. 实施级领域模型落地规范

本节将“建议字段”收束为后端可执行 schema 约束，避免后续实现阶段反复改表。

### 14.1 Site 落地字段

- `id`: 主键
- `name`: 站点显示名称
- `base_url`: 站点根地址，去除尾部 `/`
- `enabled`: 是否参与任务生成
- `compatibility_level`: `standard | browser | legacy | unsupported`
- `last_probe_status`: `unknown | healthy | degraded | unreachable | unsupported`
- `checkin_enabled_detected`: 最近一次探测到的签到开关
- `checkin_min_quota_detected`
- `checkin_max_quota_detected`
- `turnstile_required`
- `two_factor_possible`
- `last_probe_at`
- `last_probe_message`
- `created_at`
- `updated_at`

唯一约束：

- `base_url` 全局唯一

### 14.2 Account 落地字段

- `id`: 主键
- `site_id`: 外键
- `display_name`: 展示名称，可为空
- `username`
- `password_encrypted`: 加密存储后的密码
- `enabled`
- `session_status`: `unknown | valid | expired | invalid`
- `last_login_at`
- `last_checkin_status`: `pending | success | skipped | failed | blocked | unknown`
- `last_checkin_date`
- `last_checkin_at`
- `last_quota_awarded`
- `total_checkins`
- `total_quota_awarded`
- `last_error_code`
- `last_error_message`
- `created_at`
- `updated_at`

唯一约束：

- `(site_id, username)` 唯一

### 14.3 DailyTask 落地字段

- `id`: 主键
- `site_id`
- `account_id`
- `task_date`
- `status`
- `trigger_type`
- `attempt_count`
- `executor_type`
- `started_at`
- `finished_at`
- `error_code`
- `error_message`
- `created_at`
- `updated_at`

唯一约束：

- `(account_id, task_date)` 唯一

说明：

- 每个账号每天只允许一个主任务实例
- 重试不新建第二条主任务，而是提升 `attempt_count`

### 14.4 CheckinResult 落地字段

- `id`
- `task_id`
- `site_id`
- `account_id`
- `checked_in_today_before_run`
- `quota_awarded`
- `checkin_date`
- `total_checkins`
- `total_quota_awarded`
- `raw_status_payload`
- `raw_checkin_payload`
- `created_at`

唯一约束：

- `task_id` 唯一，一条任务最多一条结果

### 14.5 Incident 落地字段

- `id`
- `site_id`
- `account_id`
- `task_id`
- `type`
- `severity`
- `resolved`
- `resolution_action`
- `dedupe_key`
- `first_seen_at`
- `last_seen_at`
- `detail`

唯一约束：

- `dedupe_key` 在未解决范围内唯一

## 15. 任务状态机与幂等规则

### 15.1 DailyTask 状态机

状态枚举：

- `pending`
- `probing`
- `logging_in`
- `checking`
- `checking_in`
- `success`
- `skipped`
- `failed`
- `blocked`

状态迁移：

- `pending -> probing`
- `probing -> logging_in`
- `logging_in -> checking`
- `checking -> skipped`
- `checking -> checking_in`
- `checking_in -> success`
- 任意执行中状态 -> `failed`
- 任意执行中状态 -> `blocked`

### 15.2 幂等规则

- 幂等主键为 `(account_id, task_date)`
- 同一天重复触发“生成今日任务”时，不重复创建主任务
- 已完成任务允许“人工重试”，但表现为同一 `DailyTask` 的 `attempt_count + 1`
- `CheckinResult` 只保留最新一次成功或最终失败上下文

### 15.3 并发规则

- 同一 `account_id` 任一时刻最多一个运行态任务
- 同一 `site_id` 可配置并发上限，默认串行
- 全局执行并发由控制面统一限制，避免多站点并发压垮目标站点

## 16. 执行主链设计

### 16.1 Phase 2 主执行链

主链不再直接调用旧 `CheckIn` 脚本，而是改为：

1. 读取当日待执行 `DailyTask`
2. 读取对应 `Site` 与 `Account`
3. 执行站点探测
4. 执行 `POST /api/user/login`
5. 执行 `GET /api/user/checkin`
6. 若已签则标记 `skipped`
7. 若未签则执行 `POST /api/user/checkin`
8. 回写 `CheckinResult`
9. 更新 `Account` 汇总字段
10. 更新 `Incident`

### 16.2 适配器分层

- `standard_newapi_adapter`: 标准 API-first 主链
- `browser_fallback_adapter`: 仅处理明确标记为浏览器兼容的站点
- `legacy_plugin_adapter`: 仅为历史兼容保留，不作为默认主链

### 16.3 与当前代码的过渡关系

当前实际执行仍由 `control_plane/executors/main_checkin.py` 驱动旧脚本链。

Phase 2 不直接删除该入口，而是：

- 保留 `JobType.MAIN_CHECKIN`
- 保留 `/api/jobs/main_checkin/run`
- 将 `execute_main_checkin` 内部逐步改为委托 `newapi_checkin_service`

这样可以保持调度器、运行日志、前端触发入口不变，只替换执行核心。

## 17. API 合同设计

### 17.1 保留现有兼容接口

- `GET /api/sites`
- `POST /api/sites`
- `PUT /api/sites/{site_id}`
- `GET /api/accounts`
- `POST /api/accounts`
- `PUT /api/accounts/{account_id}`
- `GET /api/task-center/summary`
- `POST /api/jobs/main_checkin/run`

### 17.2 Phase 2 新增只读接口

- `GET /api/task-center/today?date=YYYY-MM-DD`
  - 返回当日任务列表、聚合指标、阶段分布
- `GET /api/task-center/incidents`
  - 返回异常列表，支持 `status/type/site_id/account_id` 过滤
- `GET /api/task-center/reports?from=YYYY-MM-DD&to=YYYY-MM-DD`
  - 返回按日额度、按站点成功率、按账号趋势
- `GET /api/task-center/sites/{site_id}/probe`
  - 返回最近一次探测结果

### 17.3 Phase 2 新增操作接口

- `POST /api/task-center/sites/{site_id}/probe`
  - 手动探测站点签到能力
- `POST /api/task-center/tasks/generate-today`
  - 为今天生成缺失的主任务
- `POST /api/task-center/tasks/{task_id}/retry`
  - 人工重试单账号任务
- `POST /api/task-center/accounts/{account_id}/run-today`
  - 对单账号立即执行今日任务

### 17.4 返回口径要求

- 所有任务类接口必须返回结构化状态，不允许只返回日志字符串
- 所有错误必须给出 `error_code`
- 所有列表接口必须稳定排序，默认按最近更新时间倒序

## 18. 探测机制设计

### 18.1 探测目标

探测的目的不是签到，而是识别站点兼容性与风险：

- 站点是否可达
- 登录接口是否存在
- 签到接口是否存在
- 是否启用了签到
- 奖励区间是否可读取
- 是否存在 WAF / Turnstile / 2FA 风险

### 18.2 探测结果分层

- `healthy`: 可直接进入标准签到主链
- `degraded`: 可访问但接口语义不完整
- `unreachable`: 站点不可达或超时
- `unsupported`: 明确不兼容

### 18.3 探测触发时机

- 新增站点后首次探测
- 站点编辑保存后自动探测
- 连续失败达到阈值后自动重探测
- 用户在站点页手动触发探测

## 19. 凭据与安全设计

### 19.1 凭据存储

- 明文密码不得长期以 `password` 字段持久化
- 存储层应切换为 `password_encrypted`
- UI 读取账号详情时不回传真实密码

### 19.2 凭据展示

- 列表页只展示账号名和状态
- 编辑页密码默认空白，占位表示“保持不变”
- 明确区分“未设置新密码”和“清空密码”两个动作

### 19.3 审计要求

- 记录谁修改了站点
- 记录谁修改了账号
- 记录谁执行了重试
- 记录谁手动触发了站点探测

## 20. 数据迁移策略

### 20.1 Phase 1 到 Phase 2 过渡

以现有 `ConfigDomain.MAIN_CHECKIN` 为兼容数据源，生成影子领域对象：

- `providers` 映射为影子 `Site`
- `accounts` 映射为影子 `Account`

此阶段：

- 页面优先读取显式 `Site / Account`
- 若为空，可从旧配置导入一次
- 导入动作必须显式，不做静默自动覆盖

### 20.2 主链切换顺序

1. 新增 `Site / Account / DailyTask / CheckinResult / Incident` 存储
2. 新增探测与 today/incidents/reports 接口
3. 保持 `MAIN_CHECKIN` 触发入口不变
4. 将 `MAIN_CHECKIN` 内部执行改为新服务
5. 旧 `main_checkin` 页面继续保留为兼容配置入口
6. 当新主链稳定后，逐步下线旧 JSON 主配置

### 20.3 回滚策略

- 若 API-first 主链异常率高于阈值，可切回旧执行器
- 切回时不删除新领域表，只暂停写入
- 回滚开关必须显式配置，不允许自动静默回退

## 21. Phase 2 交付门禁

进入 Phase 2 开发前，规划必须以以下门禁为准：

- 已定义 `DailyTask / CheckinResult / Incident` 最终字段
- 已定义 today/incidents/reports/probe/retry 的 API 合同
- 已定义 `MAIN_CHECKIN` 到新主链的切换顺序
- 已定义幂等、并发、重试规则
- 已定义凭据加密与 UI 展示规则
- 已定义失败回滚策略

Phase 2 完成判定：

- `POST /api/jobs/main_checkin/run` 已走 API-first 主链
- 至少一个标准 `new-api` 站点可完成真实签到闭环
- 首页、今日任务、异常处理、历史报表均不再依赖旧 `main_checkin` JSON 映射视图
- 失败结果具备结构化 `error_code`
- 任务与结果已持久化到新领域模型

## 22. 与上游 new-api 源码的强耦合事实映射

本节不是“方向性理解”，而是直接约束后续实现的源码级事实。

### 22.1 认证与会话事实

上游登录入口为：

- `POST /api/user/login`

源码事实：

- 登录成功后，上游通过 session 写入 `id / username / role / status / group`，而不是返回长期 token，见 `controller/user.go`
- 若用户开启 2FA，登录不会直接完成，而是返回 `require_2fa=true`，并在 session 中写入 `pending_user_id`，见 `controller/user.go`
- 2FA 验证入口为 `POST /api/user/login/2fa`，验证成功后才真正完成登录，见 `controller/twofa.go`

因此本项目执行器必须支持三态认证结果：

- `login_success`
- `two_factor_required`
- `login_failed`

不能把“用户名密码登录”简化为单步成功假设。

### 22.2 自身接口访问契约

上游 `GET /api/user/checkin` 与 `POST /api/user/checkin` 均位于 `selfRoute.Use(middleware.UserAuth())` 下，见 `router/api-router.go`

而 `UserAuth()` 的真实约束不只是“带 cookie 会话”：

- 还要求请求头中存在 `New-Api-User`
- 且该值必须与 session 中的 `id` 一致

源码依据见 `middleware/auth.go`。

因此本项目后续 `newapi_client` 必须在登录成功后同时保存：

- 会话 cookie jar
- 用户 `id`

并在每次调用 `/api/user/self/*` 接口时自动附带：

- `New-Api-User: <user_id>`

如果缺少这一层，标准登录后仍会在签到接口被拒绝。

### 22.3 Turnstile 约束

上游以下入口受 `TurnstileCheck()` 影响：

- `POST /api/user/login`
- `POST /api/user/checkin`

源码见 `router/api-router.go` 与 `middleware/turnstile-check.go`。

关键事实：

- Turnstile 开关由 `common.TurnstileCheckEnabled` 控制
- 校验通过后，session 内会写入 `turnstile=true`
- 之后同会话可跳过再次校验
- 若未携带 `turnstile` 参数，会直接返回失败

因此探测与执行必须区分：

- `turnstile_disabled`
- `turnstile_required_but_unsolved`
- `turnstile_session_already_verified`

不能只把 Turnstile 视为“可能存在的风险”，而要把它做成明确的状态判断与错误码。

### 22.4 签到关闭与已签到语义

上游 `GET /api/user/checkin` 和 `POST /api/user/checkin` 都会先检查签到功能是否启用，见 `controller/checkin.go`

上游 `UserCheckin()` 还会先检查“今日是否已签到”，若已签到直接返回错误，见 `model/checkin.go`

因此本项目需要区分两个不同业务结果：

- `site_checkin_disabled`
- `already_checked`

它们都不能简单并入通用 `failed`。

### 22.5 上游真实幂等锚点

上游签到记录的数据库唯一键是：

- `(user_id, checkin_date)`

源码见 `model/checkin.go`。

这说明上游对“每日一次签到”的最终真实锚点是“账号 + 日期”，不是一次 HTTP 调用、不是一次日志记录。

因此本项目的 `DailyTask` 唯一约束 `(account_id, task_date)` 不是拍脑袋设计，而是刻意与上游真实语义同构。

### 22.6 统计字段映射

上游 `GetUserCheckinStats()` 返回：

- `total_quota`
- `total_checkins`
- `checkin_count`
- `checked_in_today`
- `records`

源码见 `model/checkin.go`

本项目字段映射必须固定为：

- `Account.total_checkins <- total_checkins`
- `Account.total_quota_awarded <- total_quota`
- `CheckinResult.checked_in_today_before_run <- checked_in_today`
- `CheckinResult.raw_status_payload <- stats 全量返回`
- `CheckinResult.raw_checkin_payload <- do_checkin 全量返回`

这样做可以避免“页面展示字段”和“运行引擎回写字段”出现双真相。

## 23. 错误码与结果码映射表

### 23.1 认证阶段

- `login_failed`
  - 用户名密码错误或登录接口失败
- `two_factor_required`
  - 上游返回 `require_2fa=true`
- `session_save_failed`
  - 上游无法保存 session

### 23.2 反机器人阶段

- `turnstile_required`
  - 站点开启 Turnstile，当前会话未完成校验
- `turnstile_verify_failed`
  - Turnstile 参数存在但校验失败

### 23.3 签到阶段

- `site_checkin_disabled`
  - 上游签到功能关闭
- `already_checked`
  - 今日已签到
- `unexpected_response`
  - 返回结构缺字段或语义不符合预期
- `site_unreachable`
  - 网络不可达、超时、DNS 失败

### 23.4 兼容阶段

- `api_incompatible`
  - 登录、用户态、签到链任一环节与上游契约不兼容
- `auth_contract_mismatch`
  - 缺少 `New-Api-User` 或会话与 header 不一致

## 24. 探测器设计补丁

探测器不能只看“站点能不能打开”，而要按上游源码契约分层探测：

### 24.1 L0 无认证探测

- 站点可达
- 基础状态接口可达
- 是否暴露 Turnstile 开关信息

### 24.2 L1 认证契约探测

- 登录接口是否存在
- 登录成功后是否返回用户 `id`
- 是否存在 `require_2fa`

### 24.3 L2 用户态契约探测

- 带会话后访问 `/api/user/checkin` 是否还要求 `New-Api-User`
- `GET /api/user/checkin` 是否返回 `enabled/min_quota/max_quota/stats`

### 24.4 L3 执行契约探测

- `POST /api/user/checkin` 是否受 Turnstile 约束
- 成功后是否返回 `quota_awarded/checkin_date`

探测输出不得只写成一个 `healthy/unhealthy` 布尔值，至少要返回：

- `auth_contract_ok`
- `new_api_user_header_required`
- `turnstile_required`
- `two_factor_possible`
- `checkin_enabled_detected`
- `quota_range_detected`

## 25. Phase 2 控制合同

### 25.1 Primary Setpoint

在保持现有 `MAIN_CHECKIN` 入口不变的前提下，让一个标准 `new-api` 站点完成“登录 -> 查状态 -> 执行签到 -> 回写任务结果”的真实闭环。

### 25.2 Acceptance

- `POST /api/jobs/main_checkin/run` 走新主链
- 至少一个标准站点在真实环境完成签到
- `today` 读模型可看到结构化任务状态
- 失败时能看到结构化 `error_code`

### 25.3 Guardrail Metrics

- 不破坏现有调度入口
- 不破坏现有登录保护
- 不破坏现有运行日志
- 不引入静默自动回退

### 25.4 Sampling Plan

- L0：单元和存储契约测试
- L1：本地集成接口测试
- L2：真实 `new-api` 站点联调验证

### 25.5 Known Delays

- 真实站点响应时间
- Turnstile 与 2FA 人工介入时滞
- 调度器触发周期

### 25.6 Rollback Trigger

出现以下任一情况立即停止切流并回滚到旧执行器：

- 新主链无法生成结构化 `error_code`
- 标准站点成功率连续低于旧链路
- 任务创建与回写出现双写不一致

### 25.7 Boundary

Phase 2 允许触碰：

- `task_center_models`
- `storage`
- `task_center_service`
- `api/app.py`
- `executors/main_checkin.py`
- 新增 `newapi_client` 与 `newapi_checkin_service`

Phase 2 默认不触碰：

- 非 `new-api` 扩展任务执行器主逻辑
- 前端扩展任务插件区逻辑
