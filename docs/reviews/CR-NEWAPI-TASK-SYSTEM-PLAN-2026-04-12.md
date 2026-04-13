# new-api 多站点签到任务系统改造方案 2026-04-12

## 1. 目标重定义

当前项目的产品中心仍是“控制面 + 配置域 + 脚本运行”，而目标产品应重定义为“多站点多账号 new-api 自动签到任务系统”。

目标系统的核心对象应为：

- 站点 Site：一个具体的 new-api 实例
- 账号 Account：属于某个站点的登录账号
- 日任务 DailyTask：某个账号在某一天的签到任务
- 签到结果 CheckinResult：某次签到的状态、奖励与原始返回
- 异常 Incident：登录失败、验证码、2FA、站点不兼容等问题

主目标不是“统一维护脚本配置”，而是：

- 管理多个 new-api 站点
- 管理多个站点账号
- 每日自动执行签到
- 汇总签到收益、成功率和异常
- 提供可批量处理的任务中心界面

## 2. 当前系统与目标系统的偏差

### 2.1 产品层偏差

当前一级导航为：

- Dashboard
- Main Check-in
- Aux Jobs
- Schedules
- Settings

这是一套“运维控制台”信息架构，不是“签到任务中心”信息架构。

当前主功能仍围绕：

- 配置 JSON
- 手动运行批处理任务
- 查看批次日志

而不是围绕：

- 站点资产
- 账号资产
- 今日应签任务
- 今日收益
- 今日异常

### 2.2 执行模型偏差

当前执行模型以脚本执行器为主：

- `main_checkin`
- `checkin_996`
- `checkin_qaq_al`
- `linuxdo_read`

目标系统的主执行链应为“标准 new-api 签到链路”：

1. 登录
2. 查询签到状态
3. 判定是否已签到
4. 执行签到
5. 写入奖励与任务结果
6. 汇总当天任务完成情况

### 2.3 领域模型偏差

当前模型以配置域为核心：

- `system`
- `main_checkin`
- `checkin_996`
- `checkin_qaq_al`
- `linuxdo_read`
- `notifications`

目标模型应以任务系统领域对象为核心：

- `sites`
- `accounts`
- `daily_tasks`
- `checkin_results`
- `incidents`
- `notifications`
- `system_settings`

## 3. 上游 new-api 签到机制事实基线

基于上游 `QuantumNous/new-api` 源码，签到主链存在以下事实：

### 3.1 登录口径

上游使用用户登录会话，而不是 API Token 作为签到入口。

- 登录接口：`POST /api/user/login`
- 登出接口：`GET /api/user/logout`

### 3.2 签到口径

- 查询签到状态：`GET /api/user/checkin?month=YYYY-MM`
- 执行签到：`POST /api/user/checkin`

### 3.3 签到设置口径

上游签到配置包含：

- `enabled`
- `min_quota`
- `max_quota`

### 3.4 签到状态和结果口径

查询接口返回的关键语义包括：

- `checked_in_today`
- `total_checkins`
- `total_quota`
- `records`

执行接口返回的关键语义包括：

- `quota_awarded`
- `checkin_date`

### 3.5 设计含义

这说明本项目未来的默认主链必须是“API-first”的 new-api 签到系统，而不是把浏览器脚本和站外任务当主链。

## 4. 新的顶层设计

## 4.1 产品信息架构

新的一级导航定义为：

- 首页
- 站点
- 账号
- 今日任务
- 历史与报表
- 异常处理
- 系统设置

辅助任务不再出现在产品主导航中，而应退居插件区或扩展区。

## 4.2 控制面 / 数据面 / 状态面

### 控制面

负责：

- 站点管理
- 账号管理
- 调度策略
- 通知策略
- 重试策略
- 人工干预入口

### 数据面

负责：

- 登录
- 查询签到状态
- 执行签到
- 记录签到结果
- 汇总当日任务状态

### 状态面

负责：

- 站点定义
- 账号定义
- 会话状态
- 任务实例
- 奖励记录
- 异常记录
- 报表聚合

## 4.3 主执行链

每日签到主链固定为：

1. 站点探测
2. 登录建立会话
3. 查询签到状态
4. 已签则跳过
5. 未签则执行签到
6. 写入奖励记录
7. 更新账号累计值
8. 更新当日任务视图
9. 发送汇总通知

## 5. 新领域模型设计

## 5.1 Site

字段建议：

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
- `last_probe_message`
- `created_at`
- `updated_at`

### 兼容等级

- `standard_api`
- `api_with_extra_verification`
- `browser_fallback`
- `unsupported`

## 5.2 Account

字段建议：

- `id`
- `site_id`
- `username`
- `password`
- `enabled`
- `status`
- `session_status`
- `last_login_at`
- `last_checkin_date`
- `last_checkin_status`
- `last_quota_awarded`
- `total_checkins`
- `total_quota_awarded`
- `last_error_code`
- `last_error_message`
- `created_at`
- `updated_at`

## 5.3 DailyTask

字段建议：

- `id`
- `task_date`
- `site_id`
- `account_id`
- `status`
- `stage`
- `trigger_type`
- `attempt_count`
- `started_at`
- `finished_at`
- `error_code`
- `error_message`
- `created_at`
- `updated_at`

### 状态建议

- `pending`
- `running`
- `success`
- `skipped`
- `failed`
- `blocked`

### 阶段建议

- `probing`
- `logging_in`
- `checking_status`
- `signing`
- `persisting`
- `notifying`

## 5.4 CheckinResult

字段建议：

- `id`
- `daily_task_id`
- `site_id`
- `account_id`
- `checkin_date`
- `checked_in_today_before_run`
- `quota_awarded`
- `status_payload_json`
- `checkin_payload_json`
- `created_at`

## 5.5 Incident

字段建议：

- `id`
- `site_id`
- `account_id`
- `daily_task_id`
- `type`
- `severity`
- `resolved`
- `summary`
- `detail`
- `first_seen_at`
- `last_seen_at`
- `resolved_at`

### 异常类型建议

- `site_unreachable`
- `login_failed`
- `password_invalid`
- `turnstile_required`
- `two_factor_required`
- `site_checkin_disabled`
- `api_incompatible`
- `unexpected_response`
- `rate_limited`

## 6. 页面设计

## 6.1 首页

首页必须从“运行状态仪表盘”改造成“今日签到战情板”。

第一屏核心指标：

- 今日应签到账号数
- 今日已成功签到账号数
- 今日已跳过账号数
- 今日异常账号数
- 今日累计获得额度
- 站点健康状态

第二屏：

- 今日任务进度
- 异常分布
- 站点成功率排行
- 最近失败账号

第三屏：

- 今日任务列表
- 支持按状态快速筛选

## 6.2 站点页

展示：

- 站点名称
- 地址
- 是否启用
- 兼容等级
- 是否探测到签到能力
- 奖励区间
- 账号数
- 最近成功率
- 最近异常

操作：

- 新增站点
- 探测站点
- 启停站点
- 查看详情

## 6.3 账号页

展示：

- 所属站点
- 用户名
- 当前状态
- 今日签到状态
- 最近成功时间
- 累计签到次数
- 累计获得额度
- 最近错误

操作：

- 新增账号
- 批量导入
- 更新密码
- 测试登录
- 立即签到
- 停用账号

## 6.4 今日任务页

这是未来的主工作页。

展示：

- 任务日期
- 站点
- 账号
- 当前阶段
- 最终状态
- 奖励额度
- 错误原因
- 执行时长

筛选：

- 全部
- 待执行
- 成功
- 已跳过
- 阻塞
- 失败

## 6.5 历史与报表页

展示：

- 账号月历签到
- 站点维度收益趋势
- 每日成功率趋势
- 每日累计奖励趋势

## 6.6 异常处理页

展示：

- 认证异常
- 验证码异常
- 2FA 异常
- 站点不兼容
- 站点关闭签到
- 连续失败账号

每条异常提供建议动作。

## 6.7 系统设置页

保留系统级能力：

- 管理员登录
- 调度模式
- 通知渠道
- 浏览器执行策略
- 重试策略
- 运行参数

不再把任务主配置放在系统设置页。

## 7. UI/UX 设计原则

### 7.1 任务优先

用户打开系统后首先看到的应该是：

- 今天还有多少账号没签
- 哪些账号失败了
- 今天一共拿了多少额度

而不是：

- 存储模式
- 内部调度状态
- 技术配置域

### 7.2 结构化输入优先

- 普通表单优先
- JSON 输入退到高级设置
- 用户不应把主工作流理解成“编辑配置 JSON”

### 7.3 异常语言业务化

避免只展示日志原文，应转译成业务状态：

- 今日已签到
- 站点未开启签到
- 登录失败
- 需要验证码
- 需要 2FA
- 站点接口不兼容

### 7.4 可批量处理

站点、账号、任务都必须支持批量操作。

## 8. 视觉设计原则

### 8.1 从运维后台改成任务中心

视觉定位应从：

- control plane
- operations console

转向：

- task center
- check-in operations hub

### 8.2 视觉层级

第一层：

- 今日成果
- 今日异常
- 今日完成度

第二层：

- 站点
- 账号
- 任务清单

第三层：

- 技术日志
- 调试细节

### 8.3 组件建议

- KPI 卡片
- 任务进度条
- 站点卡片
- 账号状态行
- 月历热力图
- 异常队列

### 8.4 颜色约定

- 成功：绿色
- 已跳过：蓝灰
- 待处理：琥珀
- 阻塞：橙色
- 失败：红色
- 禁用：灰色

## 9. 后端改造设计

## 9.1 从配置域转向领域服务

当前服务中心是：

- `app_state`
- `job_service`
- `scheduler_service`

后续应演化为：

- `site_service`
- `account_service`
- `task_center_service`
- `site_probe_service`
- `checkin_service`
- `incident_service`
- `report_service`

## 9.2 API 设计方向

新增只读 API：

- `/api/task-center/overview`
- `/api/task-center/sites`
- `/api/task-center/accounts`
- `/api/task-center/today`
- `/api/task-center/incidents`
- `/api/task-center/history`

新增写 API：

- `/api/sites`
- `/api/accounts`
- `/api/accounts/{id}/test-login`
- `/api/accounts/{id}/checkin`
- `/api/tasks/{id}/retry`
- `/api/incidents/{id}/resolve`

## 9.3 存储设计方向

当前 SQLite 仅存：

- configs
- schedules
- job_runs
- job_logs

后续应新增：

- `sites`
- `accounts`
- `daily_tasks`
- `checkin_results`
- `incidents`

## 10. 迁移策略

## 10.1 保留项

保留当前能力：

- 管理员登录
- 调度器
- 通知能力
- 任务日志
- Docker 双部署模式

## 10.2 收缩项

以下能力不再作为产品主线：

- `checkin_996`
- `checkin_qaq_al`
- `linuxdo_read`

它们应迁入插件区或扩展区。

## 10.3 第一阶段落地策略

第一阶段不直接完成全量重构，而是先完成以下内容：

1. 改造前端信息架构与文案
2. 提供新的任务中心型首页
3. 提供站点页和账号页的第一版可视化
4. 用现有主签到配置推导出“站点视图”和“账号视图”只读模型
5. 为后端引入新的 task center read model 预留结构

## 11. 第一阶段开发切入点

第一阶段本轮直接开始编码，限定为“可见结构重排 + 只读任务中心视图”。

### 11.1 前端

- 将一级导航重构为新的任务中心结构
- 新增：`首页 / 站点 / 账号 / 今日任务 / 历史与报表 / 异常处理`
- 将旧页面中的配置型内容收缩到二级层或兼容页
- 用当前已有配置和运行数据生成第一版任务中心只读视图

### 11.2 后端

- 暂不一次性替换执行链
- 先增加 task center read model 聚合服务
- 从现有 `main_checkin` 配置与 `job_runs` 中推导：
  - 站点视图
  - 账号视图
  - 概览指标
  - 失败事件视图

### 11.3 验证

第一阶段验收口径：

- 用户进入后看到的是“签到任务中心”而不是“控制面”
- 用户可以看到按站点和账号组织的信息
- 首页指标以“今日签到任务”为核心
- 非 `new-api` 任务不再占据主导航

## 12. 第二阶段与第三阶段

## 第二阶段

- 后端持久化引入 `sites/accounts/daily_tasks/incidents/checkin_results`
- 站点探测落地
- 登录测试和签到主链改造成 API-first
- 账号级任务明细落地

## 第三阶段

- 浏览器回退链路
- 异常修复工作流
- 报表与收益趋势完整化
- 插件区承接旧辅助任务

## 13. 风险与控制

### 风险 1：现有主功能被过快打散

缓解：

- 保留旧 API 和旧兼容页
- 新增 task center 读模型而非立即删旧结构

### 风险 2：账号级任务粒度与现有批量执行模型不一致

缓解：

- 第一阶段先做只读聚合视图
- 第二阶段再切执行模型

### 风险 3：站点兼容性差异导致执行链复杂化

缓解：

- 先分兼容等级
- 先支持标准 API 站点
- 浏览器回退作为后续阶段能力

## 14. 本轮实现决策

本轮开发将按照以下顺序开始：

1. 先写入本方案文档
2. 重构前端导航与页面命名
3. 落地第一版任务中心首页
4. 落地第一版站点页与账号页
5. 让现有系统在视觉和信息架构上先转向目标产品

