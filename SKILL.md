---
name: codebuddy-gpt-gemini-bridge
description: Safely install, audit, repair, and manage a loopback-only CLIProxyAPI bridge that connects subscription-backed OpenAI Codex/GPT and Google Antigravity/Gemini models to CodeBuddy. Use when a CodeBuddy user asks to 接入 GPT、接入 Gemini、使用 ChatGPT/Gemini 订阅模型、安装本地模型桥接、修复自定义 GPT/Gemini、恢复被代理影响的 CodeBuddy 内置模型，或把可用 GPT/Gemini 模型同步到 CodeBuddy。Supports macOS and Windows and preserves CodeBuddy built-in models and manual custom entries.
---

# CodeBuddy GPT & Gemini Bridge

将用户自己拥有的 Codex/ChatGPT 与 Antigravity/Gemini 订阅，通过本机回环地址上的 CLIProxyAPI 接入 CodeBuddy。只注册真实存在且通过探测的模型，不把模型名称或宣传页当作能力证明。

## 定位 Skill 目录

定位当前已加载 Skill 的绝对目录并记为 `<skill-dir>`。不要假定安装在固定位置。

统一入口：

```bash
python3 <skill-dir>/scripts/bridge.py
```

在 Windows 上优先使用 CodeBuddy 内置 Python；若命令为 `python`，保持相同参数。

## 标准流程

### 1. 先审计，不先写配置

```bash
python3 <skill-dir>/scripts/bridge.py audit
```

读取 JSON 结果并确认：

- CLIProxyAPI 是否存在、是否仅监听回环地址、配置是否可达
- CodeBuddy `models.json` 是否存在以及现有模型数量
- Codex 与 Antigravity OAuth 文件只统计数量，不读取内容
- 正在运行的 CodeBuddy 是否缓存了失效的本地系统代理

若出现 `codebuddy_stale_system_proxy`，立即停止修改模型。让用户完全退出并重新打开 CodeBuddy，再重新执行审计。不要修改系统代理、`HTTP_PROXY`、`HTTPS_PROXY` 或内置模型配置来绕过问题。

将当前 CodeBuddy 内置模型能正常响应作为基线。若当前任务就在内置模型上运行，本次正常回复即可作为基线；否则请用户先用任一内置模型发送一句简短测试。

### 2. 预览并部署本地桥接

先预览：

```bash
python3 <skill-dir>/scripts/bridge.py bootstrap
```

用户明确要求安装、配置或修复时再应用：

```bash
python3 <skill-dir>/scripts/bridge.py bootstrap --apply
```

macOS 使用 Homebrew 安装并启动 CLIProxyAPI。若 Homebrew 不存在，只引导用户从 `brew.sh` 官方来源安装，不执行来历不明的安装命令。

Windows 从 `router-for-me/CLIProxyAPI` 官方 GitHub Release 下载与架构匹配的 ZIP，使用同一 Release 的 `checksums.txt` 校验 SHA-256，再安装到用户目录并创建用户级启动项。校验失败时停止，不执行下载内容。

始终：

- 绑定 `127.0.0.1:8317`
- 关闭远程管理和控制面板
- 创建独立随机客户端 Key
- 保留现有 CLIProxyAPI Key 和无关配置
- 修改前创建时间戳备份

若已有配置监听 `0.0.0.0`、`::` 或未明确回环地址，先说明远程客户端影响；只有确认不需要远程访问后才允许使用 `--allow-rebind-local`。

### 3. 分别授权 GPT 与 Gemini

仅授权用户要求的 Provider：

```bash
python3 <skill-dir>/scripts/bridge.py authorize codex
python3 <skill-dir>/scripts/bridge.py authorize antigravity
```

让 CLIProxyAPI 原生 OAuth 流程打开浏览器，由用户完成登录授权，然后继续。不要复制 Codex、Gemini CLI 或浏览器中的 Token，不要把 Provider OAuth 凭据写入 CodeBuddy。

现有 CLI 登录只是发现信号；CLIProxyAPI 仍可能需要自己的 OAuth 授权。使用用户本人拥有并获授权使用的账户，并提醒用户核对订阅条款、额度和第三方客户端限制。

### 4. 探测并同步模型

同时接入 GPT 与 Gemini：

```bash
python3 <skill-dir>/scripts/bridge.py sync --providers codex,antigravity --apply
```

只接入其中一个时只传对应 Provider。

同步必须：

- 从实时 `/v1/models` 读取账号实际可用模型
- 分别探测文本、SSE 流式、工具、图片输入和推理控制
- 跳过文本或流式探测失败的模型
- 将失败的可选能力降级为 `false`
- 原子合并到 CodeBuddy，保留手工模型和无关条目
- 拒绝覆盖同 ID 的非本 Skill 管理条目
- 兼容迁移旧版 `codebuddy-cli-model-bridge` 的本地 Key 与管理清单，不重新授权或制造冲突
- 不把图片理解探测解释为图片生成能力

不要在真实安装中使用 `--skip-probes`。该选项只用于离线测试。

### 5. 验证 CodeBuddy 没有回归

再次运行：

```bash
python3 <skill-dir>/scripts/bridge.py audit
```

确认：

- CLIProxyAPI 仍仅监听回环地址
- GPT/Gemini 模型已写入且没有手工条目冲突
- CodeBuddy 网络审计没有失效系统代理
- CodeBuddy 已加载新的 `models.json`
- 安装前使用的内置模型仍能正常回复
- 至少一个 GPT 和一个 Gemini 模型各完成一次真实文本调用

若 CodeBuddy 尚未刷新模型列表，先打开模型设置或新建任务；仍未刷新时完全退出并重开 CodeBuddy。不要重复覆盖相同 JSON。

报告 Provider、模型 ID、能力探测结果、备份路径和剩余用户操作。不要输出 API Key、OAuth Token、一次性授权码、账号邮箱、Authorization Header、原始提示词或图片载荷。

## 修复流程

遇到模型失效或 CodeBuddy `3002`：

1. 执行 `audit`，区分桥接服务、客户端 Key、Provider OAuth、模型路由、CodeBuddy 缓存和系统代理。
2. 若日志指向无法连接的本地系统代理端口，先完全退出并重开 CodeBuddy；不要改 `models.json`。
3. 若 CLIProxyAPI 不可达，优先恢复现有服务，不先重装。
4. 仅在 Provider 授权缺失或认证请求失败时重新执行 `authorize`。
5. 重新执行受影响 Provider 的 `sync --apply` 并验证真实请求。

Provider OAuth 更新不要求轮换 CodeBuddy 使用的本地代理 Key。两者生命周期不同。

需要分类错误、处理冲突或回滚时读取 [troubleshooting.md](references/troubleshooting.md)。涉及服务暴露、凭据或安装行为前读取 [security-boundaries.md](references/security-boundaries.md)。

## 完成条件

只有全部满足时才声明完成：

- 审计没有未解决的安全错误
- CLIProxyAPI 在回环地址可达
- 注册模型通过文本和流式探测
- 已启用的可选能力分别通过探测
- 手工模型和 CodeBuddy 内置模型未受破坏
- GPT 与 Gemini 至少各有一个真实可用模型，或明确报告该账号没有对应模型
- 备份与回滚路径已报告

任何一项未证实时，将结果标记为“未验证”，不要宣称成功。
