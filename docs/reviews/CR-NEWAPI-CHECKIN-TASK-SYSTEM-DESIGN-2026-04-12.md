# new-api 多站点签到任务系统改造设计 2026-04-12

## 1. 目标重定义

本项目应从“脚本控制台”重构为“多站点多账号 new-api 自动签到专用任务系统”。

系统主目标：
- 管理多个 new-api 站点
- 管理每个站点下的多个账号
- 每日自动完成签到
- 汇总签到结果、额度收益与异常
- 提供可追踪、可重试、可通知的任务闭环

非目标：
- 不再以通用脚本配置为产品核心
- 不再把非 new-api 任务放在一级主线
- 不再以大段 JSON 作为普通用户主交互方式

## 2. 当前问题

当前实现更偏向“控制面 + 脚本执行器”：
- 一级导航围绕 Dashboard、Main Check-in、Aux Jobs、Schedules、Settings 组织
- 后端对象围绕 system/main_checkin/checkin_996/checkin_qaq_al/linuxdo_read 等配置域组织
- 首页指标围绕运行次数和调度状态，不围绕“今日应签、已签、异常、累计额度”
- 主操作依赖 providers/proxy/extra JSON，普通用户心智负担高
- 996、qaq.al、Linux.do 等非主线任务稀释了 new-api 自动签到主产品定位

## 3. 上游 new-api 事实约束

依据上游仓库 https://github.com/QuantumNous/new-api：
- 登录主链为 `POST /api/user/login`
- 查询签到状态为 `GET /api/user/checkin?month=YYYY-MM`
- 执行签到为 `POST /api/user/checkin`
- 签到配置为 `checkin_setting.enabled/min_quota/max_quota`
- 签到结果包含 `checked_in_today`、`total_checkins`、`total_quota`、`records`、`quota_awarded`

因此本项目的签到机制必须改为 API-first：
1. 登录站点用户账号
2. 查询签到状态
3. 若今日已签则跳过
4. 若未签则执行签到
5. 记录奖励额度、日期、状态与异常

浏览器能力只能作为回退链路，不应继续作为默认主链。

## 4. 新的产品信息架构

一级导航应改为：
- 首页
- 站点
- 账号
- 今日任务
- 历史与报表
- 异常处理
- 系统设置

导航目标：
- 首页：今天整体战情
- 站点：外部 new-api 实例资产
- 账号：签到执行主体资产
- 今日任务：当前日任务明细与操作中心
- 历史与报表：日历、趋势、累计收益
- 异常处理：登录失败、验证码、兼容性问题收口
- 系统设置：调度、通知、管理员与浏览器策略

## 5. 核心领域模型

### 5.1 Site
- id
- name
- base_url
- enabled
- compatibility_level
- checkin_enabled_detected
- checkin_min_quota_detected
- checkin_max_quota_detected
- login_mode
- turnstile_required
- two_factor_possible
- last_probe_at
- last_probe_status

### 5.2 Account
- id
- site_id
- username
- password
- enabled
- session_status
- last_login_at
- last_checkin_date
- last_checkin_status
- total_checkins
- total_quota_awarded

### 5.3 DailyTask
- id
- site_id
- account_id
- task_date
- trigger_type
- status
- attempt_count
- started_at
- finished_at
- error_code
- error_message

### 5.4 CheckinResult
- task_id
- checked_in_today_before_run
- quota_awarded
- checkin_date
- raw_status_payload
- raw_checkin_payload

### 5.5 Incident
- id
- site_id
- account_id
- task_id
- type
- severity
- resolved
- resolution_action
- first_seen_at
- last_seen_at

## 6. 任务状态机

任务状态建议统一为：
- pending
- probing
- logging_in
- checking_status
- signing
- success
- skipped
- failed
- blocked

错误码建议至少覆盖：
- already_checked
- site_checkin_disabled
- login_failed
- password_invalid
- turnstile_required
- two_factor_required
- session_expired
- api_incompatible
- site_unreachable
- unexpected_response
- rate_limited

## 7. 签到执行架构

### 7.1 控制面
负责：
- 站点管理
- 账号管理
- 调度策略
- 通知策略
- 人工干预与异常处理

### 7.2 执行面
负责：
- 标准 new-api API 适配执行
- 浏览器回退执行
- 旧脚本插件兼容执行

执行适配器分层：
- standard_newapi_adapter
- browser_fallback_adapter
- legacy_plugin_adapter

### 7.3 状态面
负责存储：
- 站点
- 账号
- 每日任务
- 签到结果
- 异常记录
- 通知摘要

## 8. 页面设计要求

### 8.1 首页
第一屏只保留核心指标：
- 今日应签到账号数
- 今日已成功
- 今日已跳过
- 今日异常
- 今日累计额度
- 异常站点数

第二屏展示：
- 今日任务进度
- 失败类型分布
- 站点成功率排行
- 最近异常账号

### 8.2 站点页
展示：
- 站点名
- 地址
- 兼容等级
- 签到是否启用
- 奖励区间
- 账号数
- 今日成功率
- 最近异常

### 8.3 账号页
展示：
- 所属站点
- 用户名
- 登录状态
- 今日签到状态
- 最近成功时间
- 累计签到次数
- 累计获得额度

### 8.4 今日任务页
展示：
- 站点
- 账号
- 当前阶段
- 最终状态
- 奖励额度
- 错误原因
- 开始/结束时间

支持筛选：
- 全部
- 待执行
- 成功
- 已跳过
- 阻塞
- 失败

### 8.5 历史与报表页
展示：
- 账号月历签到视图
- 站点趋势视图
- 全局每日累计收益趋势
- 成功率与失败率趋势

### 8.6 异常处理页
聚焦：
- 认证异常
- 验证码异常
- 站点兼容异常
- 站点关闭签到
- 连续失败异常

每条异常需提供：
- 原因
- 影响范围
- 最近发生时间
- 建议动作
- 是否已处理

## 9. UI / UX 原则

- 主界面从“运维控制台”改为“任务中心”
- 用户先看到今日结果，再进入技术细节
- 普通用户主交互禁止依赖 JSON 编辑
- JSON 仅保留在高级设置抽屉或专家模式
- 错误信息必须转换为可执行的人话
- 日志不再是唯一真相，任务阶段和异常分类必须结构化展示

## 10. 视觉方向

- 首页为任务战情板，不再是运行状态面板
- 强调“今日完成度”和“异常数量”
- 视觉语义：
  - 成功：绿色
  - 跳过：蓝灰
  - 待处理：琥珀
  - 阻塞：橙色
  - 失败：红色
  - 禁用/不兼容：灰色
- 减少密集 badge 堆叠和说明文字
- 弱化部署、存储、时区等运维细节在首屏中的权重

## 11. 非主线能力处置

以下功能不应继续作为一级主线：
- checkin_996
- checkin_qaq_al
- linuxdo_read

处理原则：
- 迁移到“插件”或“扩展任务”区域
- 不参与首页主指标
- 不干扰站点/账号/今日任务主线

## 12. 第一阶段实施范围

### 12.1 文档与命名
- 统一将产品语言从 control plane 改为 task center / check-in task system
- 完成信息架构与页面文案重命名

### 12.2 前端第一阶段
- 新一级导航落地
- Dashboard 改为“首页”
- Main Check-in 拆为“站点”和“账号”两个视图
- 新增“今日任务”和“异常处理”页面骨架
- 用现有数据先构造第一版任务中心视图

### 12.3 后端第一阶段
- 在现有存储层引入 site/account/task/result/incident 领域对象
- 保留旧配置域，作为迁移过渡输入源
- 新增站点和账号读接口
- 新增任务汇总接口与异常汇总接口
- 暂不立即删除旧 job 模型，先桥接

### 12.4 执行第一阶段
- 先实现标准 new-api API-first 探测与签到主链
- 将浏览器执行降为回退路径
- 对不兼容站点给出显式兼容等级与异常说明

## 13. 迁移策略

- 保留现有调度、通知、Docker 双部署能力
- 旧 `main_checkin` 配置优先迁移到 `site/account` 结构
- 旧辅助任务保留但降级为插件
- 旧运行日志保留，只是不再作为新主模型的唯一结果载体

## 14. 验收口径

功能验收：
- 用户能按“站点-账号-今日任务”理解系统
- 用户能看见今日应签、已签、异常与累计额度
- 用户能按站点和账号定位问题
- 标准 new-api 站点签到链路以 API-first 正常工作

设计验收：
- 首页首屏不再是纯运维指标
- 一级导航不再暴露 Aux Jobs 等非主线对象
- 普通操作不需要编辑 JSON

架构验收：
- 领域模型从配置域转向任务域
- 执行链路支持标准适配器与回退适配器分层
- 异常分类与结果记录结构化
