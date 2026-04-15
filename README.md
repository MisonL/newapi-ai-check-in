# newapi.ai 多账号自动签到

用于公益站多账号每日签到。  

Affs:
- [AnyRouter](https://anyrouter.top/register?aff=wJrb)
- [WONG](https://wzw.pp.ua/register?aff=N6Q9)
- [薄荷 API](https://x666.me/register?aff=dgzt)
- [Huan API](https://ai.huan666.de/register?aff=qEnU)
- [KFC API](https://kfc-api.sxxe.net/register?aff=xPnf)
- [HotaruApi](https://hotaruapi.com/register?aff=q6xq)
- [Elysiver](https://elysiver.h-e.top/register?aff=5JsA)

其它使用 `newapi.ai` 功能相似, 可自定义环境变量 `PROVIDERS` 支持或 `PR` 到仓库。

## 功能特性

- ✅ 单个/多账号自动签到
- ✅ 多种机器人通知（可选）
- ✅ linux.do 登录认证
- ✅ github 登录认证 (with OTP)
- ✅ Cloudflare bypass

## 本地部署与 WebUI

当前仓库已支持本地 Docker 部署和 WebUI 管理。

### Docker 启动

```bash
cp .env.example .env
$EDITOR .env
docker compose up -d
docker compose ps
```

说明：
- `HOST_PORT` 可选，默认是 `39327`；如果本机端口冲突，改成别的端口即可。
- `.env` 中至少需要配置 `CONTROL_PLANE_SESSION_SECRET` 和 `CONTROL_PLANE_INTERNAL_TOKEN`；首次部署通常也应设置 `CONTROL_PLANE_ADMIN_PASSWORD`。
- `.env` 中通过 `CONTROL_PLANE_DEPLOY_MODE` 明确部署模式，避免本地调度和 GitHub Actions 双开。
- 数据持久化在 compose 命名卷 `runtime_data` 中，不依赖宿主机目录共享。
- 容器带健康检查；`docker compose ps` 显示 `healthy` 后再访问 WebUI。
- Docker 镜像会预装 Camoufox 浏览器与 Xvfb 运行依赖，避免首次任务现场下载浏览器导致长时间卡顿。
- Docker 默认启用浏览器执行；首次部署后如果需要关闭，可在 WebUI 的 `系统设置` 页面调整。

### 两种部署模式

#### 模式 1：控制面本地调度

适用场景：
- 由当前 Docker 容器负责定时执行任务
- WebUI 除了编辑计划，也负责实际触发

启动方式：

```bash
cp .env.control-plane.example .env
$EDITOR .env
docker compose up -d
```

关键配置：
- `CONTROL_PLANE_DEPLOY_MODE=control_plane`
- 本地 APScheduler 启用
- 仓库内 GitHub Actions 定时任务应关闭

#### 模式 2：GitHub Actions 驱动

适用场景：
- 定时执行仍由 `.github/workflows/*.yml` 负责
- 当前 Docker 只提供 WebUI、配置管理和手动触发

启动方式：

```bash
cp .env.github-actions.example .env
$EDITOR .env
docker compose up -d
```

关键配置：
- `CONTROL_PLANE_DEPLOY_MODE=github_actions`
- 本地 APScheduler 自动关闭
- `Schedules` 页面中的 Cron 仅保留为计划，不在本机自动触发

兼容说明：
- 旧变量 `CONTROL_PLANE_SCHEDULER_ENABLED` 仍兼容。
- 若同时设置 `CONTROL_PLANE_DEPLOY_MODE` 和 `CONTROL_PLANE_SCHEDULER_ENABLED`，且含义冲突，服务会直接启动失败，避免静默误配。

### WebUI 地址

- 默认地址：`http://127.0.0.1:39327`
- 若修改了 `HOST_PORT`，则按你设置的端口访问，例如：`http://127.0.0.1:39331`

### 前端本地开发端口

- `web` 目录下执行 `npm run dev` 或 `npm run start` 时，默认端口固定为 `39327`
- 如需改端口，显式设置 `NUXT_PORT`，例如：`NUXT_PORT=39331 npm run dev`

### 本地登录口径

- bootstrap 管理员密码来自 `.env` 中的 `CONTROL_PLANE_ADMIN_PASSWORD`
- 首次登录后，可在 WebUI 的 `Settings` 页面更新管理员密码。
- 一旦写入持久化管理员密码，bootstrap 密码自动失效。

### 调度模式说明

- 本地控制面调度与 GitHub Actions 定时任务不要同时启用。
- 如果你继续使用仓库内 workflow，请将 `.env` 中的 `CONTROL_PLANE_DEPLOY_MODE=github_actions`。

### WebUI 已支持的管理范围

- `首页`：今日任务、异常和累计收益总览
- `站点`：维护 new-api 站点资产、兼容等级和探测结果
- `账号`：维护站点账号、认证方式、签到状态与累计额度
- `今日任务`：导入主签到配置、生成今日任务、批量执行与单账号重试
- `历史与报表`：按日期范围查看趋势、完成率和站点汇总
- `异常处理`：聚合失败或阻塞账号，便于人工复核
- `Main Check-in / Aux Jobs / Schedules / Settings`：保留为高级配置与兼容链路入口

站点录入约束：
- `站点地址` 支持直接粘贴 `.../api/user/checkin` 或 `.../api/user/login` 完整链接，系统会自动归一化为站点根地址。
- 同一个站点根地址只允许保留一条站点记录，避免重复生成每日任务。
- 同一站点下，相同认证方式和用户名的账号只允许存在一条记录，避免重复签到。
- 服务启动时会自动收敛历史重复站点、重复账号，并同步修正已有任务、结果和异常引用。

### 前端验证命令

```bash
cd web
npm run build
npm run test:e2e
```

说明：
- `npm run test:e2e` 默认会自动拉起后端测试服务和前端构建产物。
- 若你已经在本机手动启动了 `18081` 和 `39329` 对应服务，可用 `PLAYWRIGHT_EXTERNAL_SERVER=1 npm run test:e2e` 复用现有服务。

## 使用方法

### 1. Fork 本仓库

点击右上角的 "Fork" 按钮，将本仓库 fork 到你的账户。

### 2. 设置 GitHub Environment Secret

1. 在你 fork 的仓库中，点击 "Settings" 选项卡
2. 在左侧菜单中找到 "Environments" -> "New environment"
3. 新建一个名为 `production` 的环境
4. 点击新建的 `production` 环境进入环境配置页
5. 点击 "Add environment secret" 创建 secret：
   - Name: `ACCOUNTS`
   - Value: 你的多账号配置数据

#### 2.0 快速生成 JSON（推荐）

仓库根目录提供了一个纯 HTML 生成器：`secret-json-generator.html`。

使用方式：

1. 在本地直接双击打开 `secret-json-generator.html`（或拖进浏览器）
2. 选择要生成的 secret（如 `ACCOUNTS`、`ACCOUNTS_996`、`ACCOUNTS_QAQ_AL`、`PROXY`、`PROVIDERS`）
3. 按页面提示填入参数并点击「产出 JSON」
4. 复制结果，粘贴到 GitHub -> Settings -> Environments -> `production` -> Environment secrets 的 Value

说明：
- 生成器只在浏览器本地运行，不会上传你的账号或密码。
- `PROXY` 类型产出的 JSON 可用于 `PROXY`、`PROXY_996`、`PROXY_QAQ_AL`。
- `ACCOUNTS_LINUX_DO` 与 `ACCOUNTS_GITHUB` 使用相同 JSON 数组格式（`[{"username":"...","password":"..."}]`）。

#### 2.1 全局 OAuth 账号配置（可选）

可以配置全局的 Linux.do 和 GitHub 账号，供多个 provider 共享使用。

##### 2.1.1 ACCOUNTS_LINUX_DO

在仓库的 Settings -> Environments -> production -> Environment secrets 中添加：
   - Name: `ACCOUNTS_LINUX_DO`
   - Value: Linux.do 账号列表

```json
[
  {"username": "用户名1", "password": "密码1"},
  {"username": "用户名2", "password": "密码2"}
]
```

##### 2.1.2 ACCOUNTS_GITHUB

在仓库的 Settings -> Environments -> production -> Environment secrets 中添加：
   - Name: `ACCOUNTS_GITHUB`
   - Value: GitHub 账号列表

```json
[
  {"username": "用户名1", "password": "密码1"},
  {"username": "用户名2", "password": "密码2"}
]
```

### 3 多账号配置格式
> 如果未提供 `name` 字段，会使用 `{provider.name} 1`、`{provider.name} 2` 等默认名称。  
> 配置中 `cookies`、`github`、`linux.do` 必须至少配置 1 个。  
> 使用 `cookies` 设置时，`api_user` 字段必填。  

#### 3.1 OAuth 配置支持三种格式

`github` 和 `linux.do` 字段支持以下三种配置格式：

**1. bool 类型 - 使用全局账号**
```json
{"provider": "anyrouter", "linux.do": true}
```
当设置为 `true` 时，使用 `LINUX_DO_ACCOUNTS` 或 `GITHUB_ACCOUNTS` 中配置的所有账号。

**2. dict 类型 - 单个账号**
```json
{"provider": "anyrouter", "linux.do": {"username": "用户名", "password": "密码"}}
```

**3. array 类型 - 多个账号**
```json
{"provider": "anyrouter", "linux.do": [
  {"username": "用户名1", "password": "密码1"},
  {"username": "用户名2", "password": "密码2"}
]}
```

#### 3.2 完整示例

```json
[
    {
      "name": "我的账号",
      "cookies": {
        "session": "account1_session_value"
      },
      "api_user": "account1_api_user_id",
      "github": {
        "username": "myuser",
        "password": "mypass"
      },
      "linux.do": {
        "username": "myuser",
        "password": "mypass"
      },
      // --- 额外的配置说明 ---
      // 当前账号使用代理
      "proxy": {
        "server": "http://username:password@proxy.example.com:8080"
      },
      //provider: x666 可选配置（自动通过 linux.do 登录获取）
      // "access_token": "来自 https://qd.x666.me/",  // 已废弃，会自动获取
      "get_cdk_cookies": {
        // provider: runawaytime 必须配置
        "session": "来自 https://fuli.hxi.me/",
        // provider: b4u 必须配置
        "__Secure-authjs.session-token": "来自 https://tw.b4u.qzz.io/"
      }
    },
    {
      "name": "使用全局账号",
      "provider": "agentrouter",
      "linux.do": true,
      "github": true
    },
    {
      "name": "多个 OAuth 账号",
      "provider": "wong",
      "linux.do": [
        {"username": "user1", "password": "pass1"},
        {"username": "user2", "password": "pass2"}
      ]
    }
  ]
```

#### 3.3 字段说明：

- `name` (可选)：自定义账号显示名称，用于通知和日志中标识账号
- `provider` (可选)：供应商，内置 `anyrouter`、`wong`、`huan666`、`x666`、`kfc`、`elysiver`、`hotaru`默认使用 `anyrouter`
- `proxy` (可选)：单个账号代理配置，支持 `http`、`socks5` 代理
- `cookies`(可选)：用于身份验证的 cookies 数据
- `api_user`(cookies 设置时必需)：用于请求头的 new-api-user 参数
- `linux.do`(可选)：用于登录身份验证，支持三种格式：
  - `true`：使用 `LINUX_DO_ACCOUNTS` 中的全局账号
  - `{"username": "xxx", "password": "xxx"}`：单个账号
  - `[{"username": "xxx", "password": "xxx"}, ...]`：多个账号
- `github`(可选)：用于登录身份验证，支持三种格式：
  - `true`：使用 `GITHUB_ACCOUNTS` 中的全局账号
  - `{"username": "xxx", "password": "xxx"}`：单个账号
  - `[{"username": "xxx", "password": "xxx"}, ...]`：多个账号

#### 3.4 供应商配置：

在仓库的 Settings -> Environments -> production -> Environment secrets 中添加：
   - Name: `PROVIDERS`
   - Value: 供应商
   - 说明: 自定义的 provider 会自动添加到账号中执行（在账号配置中没有使用自定义 provider 情况下, 详见 [PROVIDERS.json](./PROVIDERS.json)）。


#### 3.5 代理配置
> 应用到所有的账号，如果单个账号需要使用代理，请在单个账号配置中添加 `proxy` 字段。  
> 打开 [webshare](https://dashboard.webshare.io/) 注册账号，获取免费代理

在仓库的 Settings -> Environments -> production -> Environment secrets 中添加：
   - Name: `PROXY`
   - Value: 代理服务器地址


```bash
{
  "server": "http://username:password@proxy.example.com:8080"
}

或者

{
  "server": "http://proxy.example.com:8080",
  "username": "username",
  "password": "password"
}
```


#### 3.6 如何获取 cookies 与 api_user 的值。

通过 F12 工具，切到 Application 面板，Cookies -> session 的值，最好重新登录下，但有可能提前失效，失效后报 401 错误，到时请再重新获取。

![获取 cookies](./assets/request-cookie-session.png)

通过 F12 工具，切到 Application 面板，面板，Local storage -> user 对象中的 id 字段。

![获取 api_user](./assets/request-api-user.png)

#### 3.7 `GitHub` 在新设备上登录会有两次验证

通过打印日志中链接打开并输入验证码。

![输入 OTP](./assets/github-otp.png)

### 4. 启用 GitHub Actions

1. 在你的仓库中，点击 "Actions" 选项卡
2. 如果提示启用 Actions，请点击启用
3. 找到 "newapi.ai 自动签到" workflow
4. 点击 "Enable workflow"

### 5. 测试运行

你可以手动触发一次签到来测试：

1. 在 "Actions" 选项卡中，点击 "newapi.ai 自动签到"
2. 点击 "Run workflow" 按钮
3. 确认运行

![运行结果](./assets/check-in.png)

## 执行时间

- 脚本每 8 小时执行一次（1. action 无法准确触发，基本延时 1~1.5h；2. 目前观测到 anyrouter.top 的签到是每 24h 而不是零点就可签到）
- 你也可以随时手动触发签到

## 注意事项

- 可以在 Actions 页面查看详细的运行日志
- 支持部分账号失败，只要有账号成功签到，整个任务就不会失败
- `GitHub` 新设备 OTP 验证，注意日志中的链接或配置了通知注意接收的链接，访问链接进行输入验证码

## 开启通知

脚本支持多种通知方式，可以通过配置以下环境变量开启，如果 `webhook` 有要求安全设置，例如钉钉，可以在新建机器人时选择自定义关键词，填写 `newapi.ai`。

### 邮箱通知

- `EMAIL_USER`: 发件人邮箱地址
- `EMAIL_PASS`: 发件人邮箱密码/授权码
- `CUSTOM_SMTP_SERVER`: 自定义发件人 SMTP 服务器(可选)
- `EMAIL_TO`: 收件人邮箱地址

### 钉钉机器人

- `DINGDING_WEBHOOK`: 钉钉机器人的 Webhook 地址

### 飞书机器人

- `FEISHU_WEBHOOK`: 飞书机器人的 Webhook 地址

### 企业微信机器人

- `WEIXIN_WEBHOOK`: 企业微信机器人的 Webhook 地址

### PushPlus 推送

- `PUSHPLUS_TOKEN`: PushPlus 的 Token

### Server 酱

- `SERVERPUSHKEY`: Server 酱的 SendKey

### Telegram 机器人

- `TELEGRAM_BOT_TOKEN`: Telegram 机器人的 Token
- `TELEGRAM_CHAT_ID`: 接收消息的 Chat ID

## 防止Action因长时间无活动而自动禁止
- `ACTIONS_TRIGGER_PAT`: 在Github Settings -> Developer Settings -> Personal access tokens -> Tokens(classic) 中新建一个包含repo和workflow的令牌

配置步骤：

1. 在仓库的 Settings -> Environments -> production -> Environment secrets 中添加上述环境变量
2. 每个通知方式都是独立的，可以只配置你需要的推送方式
3. 如果某个通知方式配置不正确或未配置，脚本会自动跳过该通知方式

## 故障排除

如果签到失败，请检查：

1. 账号配置格式是否正确
2. 网站是否更改了签到接口
3. 查看 Actions 运行日志获取详细错误信息

## 本地开发环境设置

如果你需要在本地测试或开发，请按照以下步骤设置：

```bash
# 安装所有依赖
uv sync --dev

# 安装 Camoufox 浏览器
python3 -m camoufox fetch

# 按 .env.example 创建 .env
uv run main.py
```

## 测试

```bash
uv sync --dev

# 安装 Camoufox 浏览器
python3 -m camoufox fetch

# 运行测试
uv run pytest tests/
```

## 免责声明

本脚本仅用于学习和研究目的，使用前请确保遵守相关网站的使用条款.
