# new-api 多站点签到任务中心改造方案

## 1. 目标重定义

当前项目更像脚本控制台，不是面向普通用户的多站点多账号 `new-api` 自动签到系统。

目标产品重定义为：

- 管理多个 `new-api` 站点
- 管理多个站点账号
- 每日自动完成签到
- 汇总签到收益、任务结果与异常

产品主线改为：

- 站点
- 账号
- 今日任务
- 历史收益
- 异常处理

不再以 `providers / proxy / JSON 配置` 作为核心交互。

## 2. 上游事实约束

基于 `QuantumNous/new-api` 上游源码，标准签到主链为：

- 登录：`POST /api/user/login`
- 查询签到状态：`GET /api/user/checkin`
- 执行签到：`POST /api/user/checkin`

核心返回语义包括：

- `checked_in_today`
- `quota_awarded`
- `checkin_date`
- `records`
- `total_checkins`
- `total_quota`

因此本系统应优先走 API-first 主链，而不是默认走浏览器脚本。

## 3. 顶层设计

### 3.1 控制面

- 站点管理
- 账号管理
- 调度策略
- 通知策略
- 人工干预入口

### 3.2 执行面

- 标准 `new-api` 适配器
- 浏览器回退适配器
- 旧脚本兼容适配器

### 3.3 状态面

- 站点
- 账号
- 每日任务
- 签到结果
- 异常事件

## 4. 领域模型

### 4.1 Site

- 站点名称
- `base_url`
- 是否启用
- 兼容等级
- 最近探测状态
- 探测到的签到配置

### 4.2 Account

- 所属站点
- 用户名密码
- 启用状态
- 会话状态
- 最近签到状态
- 最近签到日期
- 累计签到次数
- 累计获得额度

### 4.3 DailyTask

- 站点账号每日一条任务
- 状态机：待执行 / 登录中 / 查询中 / 签到中 / 成功 / 跳过 / 失败 / 阻塞

### 4.4 CheckinResult

- 是否执行前已签到
- `quota_awarded`
- `checkin_date`
- 原始状态载荷
- 原始签到载荷

### 4.5 Incident

- 登录失败
- 验证码阻塞
- 2FA 阻塞
- 站点未启用签到
- 接口不兼容
- 网络异常

## 5. 信息架构

一级导航重构为：

- 首页
- 站点
- 账号
- 今日任务
- 历史与报表
- 异常处理
- 系统设置

旧的 `Main Check-in / Aux Jobs / Schedules` 退出产品主线：

- `Main Check-in` 被拆成站点与账号
- `Aux Jobs` 降级为扩展能力
- `Schedules` 能力下沉到系统设置与任务调度配置

## 6. 首页指标

首页第一屏只保留任务中心指标：

- 今日应签到账号数
- 今日已成功
- 今日已跳过
- 今日异常
- 今日累计额度
- 异常站点数

第二屏展示：

- 任务完成进度
- 失败类型分布
- 站点成功率
- 最近异常账号

## 7. 标准签到机制

每日签到流程：

1. 站点探测
2. 登录获取会话
3. 查询签到状态
4. 已签到则跳过
5. 未签到则执行签到
6. 落库奖励与状态
7. 汇总通知

异常分类：

- `already_checked`
- `site_checkin_disabled`
- `login_failed`
- `turnstile_required`
- `two_factor_required`
- `api_incompatible`
- `site_unreachable`
- `unexpected_response`

## 8. UI / UX 改造方向

- 从运维控制台改为任务中心
- 从技术配置驱动改为任务结果驱动
- 从大段 JSON 编辑改为结构化表单
- 从日志导向改为异常导向

关键页面：

- 首页：今日任务战情板
- 站点：站点资产与兼容性
- 账号：账号资产与签到状态
- 今日任务：当日执行结果
- 历史与报表：月历与收益趋势
- 异常处理：待修复账号与站点

## 9. 分阶段实施

### Phase 1

- 建立 `site / account / task center summary` 基础领域模型
- 新导航与新页面骨架落地
- 首页改为任务中心首页
- 站点页与账号页可维护基础资产

### Phase 2

- API-first 标准签到主链落地
- 任务状态机与每日任务实例落地
- 异常中心与历史报表增强

### Phase 3

- 浏览器回退机制
- 非标准站点兼容策略
- 扩展任务插件区

## 10. 本轮开发切入点

本轮直接开始编码的最小切入点：

- 后端新增 `site / account / task_center_summary` 模型与存储接口
- 新增对应 API
- 前端新增 `站点 / 账号 / 今日任务 / 历史 / 异常` 页面骨架
- 首页与导航切换到新 IA

## 11. 不在本轮完成的部分

- 完整签到执行引擎
- 浏览器回退链路
- 真实站点探测器
- Incident 持久化实体

这些能力在 Phase 2 / Phase 3 继续推进。

## 12. Phase 2 工作包拆解

### WP-1 领域模型与存储

- 新增 `DailyTask`
- 新增 `CheckinResult`
- 将 `Incident` 从汇总视图补为持久化实体
- 为 `sqlite / memory` 存储补齐对应读写接口

完成判定：

- `(account_id, task_date)` 唯一约束生效
- `task_id -> result` 一对一约束生效

### WP-2 API 合同

- 新增 `today`
- 新增 `incidents`
- 新增 `reports`
- 新增 `probe`
- 新增 `retry`

完成判定：

- 前端不再从旧 `main_checkin` 映射 today 视图

### WP-3 执行主链替换

- 新增 `newapi_client`
- 新增 `newapi_checkin_service`
- 支持 `New-Api-User` 头与 session cookie 联动
- 支持 `require_2fa`、`turnstile_required`、`already_checked` 结构化结果
- `MAIN_CHECKIN` 保持入口不变，但内部改为新服务

完成判定：

- `POST /api/jobs/main_checkin/run` 可对真实标准站点完成签到

### WP-4 状态回写与异常中心

- 回写账号最近签到状态
- 回写累计额度
- 生成结构化异常
- 实现异常聚合与去重
- 将上游 Turnstile / 2FA / 已签到 / 签到关闭映射为稳定错误码

完成判定：

- 异常页不再依赖旧运行日志过滤

### WP-5 安全与运维

- 密码改为加密存储
- UI 不回传真实密码
- 增加手动探测与人工重试审计
- 明确真实环境 gate：至少一条标准站点闭环验证

完成判定：

- 账号读取接口默认不暴露明文密码

## 13. Phase 3 工作包拆解

- 浏览器回退适配器
- 非标准站点兼容策略
- 插件区与扩展任务分区
- 历史旧链路配置逐步下线

## 14. 执行顺序

推荐顺序：

1. 先做存储与 API 合同
2. 再做 today / incidents / reports 读模型
3. 再替换 `MAIN_CHECKIN` 执行主链
4. 最后处理浏览器回退和插件化

原因：

- 先有稳定数据模型和接口，前端与执行器才能围绕同一事实演进
- 若先替换执行器而无新任务模型，后续还会再次重构

## 15. Phase 2 风险点

- 上游 `new-api` 不同分支的签到返回格式可能不完全一致
- 某些站点可能开启 Turnstile 或 2FA，不能直接进入标准主链
- 若不先处理密码存储，会把新模型直接建立在不安全基础上
- 若 today 页继续依赖旧 jobs 视图，后续读模型会再次返工

## 16. Phase 2 进入条件

- 主设计文档已明确字段、状态机、API、迁移和回滚
- 现有站点/账号骨架已稳定
- 旧 `MAIN_CHECKIN` 入口保留不动
- 前端 Phase 1 已通过构建验证
