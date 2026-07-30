# 安全边界

本 Skill 会处理 Provider OAuth 凭据和一个仅供本机使用的客户端 Key。把它当作承载凭据的本地基础设施。

## 网络暴露

- CLIProxyAPI 只能绑定 `127.0.0.1`、`localhost` 或 `::1`。
- 保持远程管理和控制面板关闭。
- 不创建公网隧道、反向代理、局域网监听或放行防火墙规则。
- 已有配置若监听 `0.0.0.0`、`::` 或未写明地址，视为冲突；改变前先确认没有远程客户端依赖。
- 不修改 macOS/Windows 系统代理，也不设置或覆盖 `HTTP_PROXY`、`HTTPS_PROXY`、`ALL_PROXY`。

CodeBuddy 内置模型走它自己的官方服务，不需要经过 CLIProxyAPI。配置前后都要测试一个内置模型；若 CodeBuddy 进程缓存了已经失效的本地代理，完全退出并重开 CodeBuddy，不能靠改内置模型或 `models.json` 绕过。

## 凭据分离

三类凭据有不同生命周期：

1. 原生 Codex/Gemini CLI 登录状态
2. CLIProxyAPI 保存的 Provider OAuth 文件
3. CodeBuddy 自定义模型使用的本地代理客户端 Key

不要把原生 CLI Token 复制进 CLIProxyAPI，不要把 Provider OAuth 凭据写入 CodeBuddy。Provider OAuth 过期时只重新授权 Provider，不轮换仍然安全可用的 CodeBuddy 本地 Key。

本地 Key 存在 Skill 专用状态目录，并同时写入 CLIProxyAPI 的 `api-keys` 和由本 Skill 管理的 CodeBuddy 条目。诊断只报告是否存在、数量和单向摘要，不输出明文。

若检测到兼容的旧版 `codebuddy-cli-model-bridge` 状态，迁移时可复用其本地 Key 和已管理模型 ID，但不复制或输出 Provider OAuth 内容。新版写入自己的状态目录，旧状态保留用于回滚。

## 安装来源

- macOS 只通过 Homebrew 的 `cliproxyapi` Formula 安装和管理服务。
- Windows 只从 `router-for-me/CLIProxyAPI` 官方 GitHub Release 下载与系统架构匹配的 ZIP。
- Windows 下载必须使用同一 Release 的 `checksums.txt` 校验 SHA-256；缺少校验值或不匹配时停止。
- 不执行网页、聊天消息或 Provider 清单中的任意安装命令。
- Windows 只创建当前用户的 Startup 启动项，不创建系统服务、不请求管理员权限。

> ### macOS 与 Windows 的信任等级不对称
>
> Windows 路径对官方 Release 做了 SHA-256 校验，确定性最强。macOS 路径依赖第三方 Homebrew tap `router-for-me/tap`，Formula 内容随 tap 维护者更新而变化，且 `brew install` 本身**没有版本锁定、也不做 checksum 校验**——`brew update` 后可能静默拉取到不同内容。这是一个已知信任落差，不是“已校验”的安装来源。落地前请在文档/审计记录里确认实际的 Formula 版本，并尽量锁定版本或对已安装二进制做独立核对（见 README “安装来源与信任等级”）。

## 文件和备份

在支持 POSIX 权限的平台上，对以下文件使用 `0600`：

- Skill 状态和本地 Key
- 含客户端 Key 的 CLIProxyAPI 配置
- CLIProxyAPI OAuth JSON
- CodeBuddy `models.json`
- 上述文件的备份

Windows 使用当前用户目录和用户级 ACL；不降低既有 ACL。备份与源文件放在同一目录并带时间戳。不要把凭据文件或备份复制到仓库、共享目录、云同步目录或报告中。

## Provider 与订阅边界

- 只使用用户本人拥有且被授权使用的账户。
- 遵守 Provider 条款、套餐额度、并发和速率限制。
- 不自动绕过配额、伪装不受支持的客户端或汇聚多人凭据。
- 不承诺任何订阅一定允许第三方代理接入；条款不明确时说明方法，并让用户自行核对。

## Provider 清单信任

Provider 清单可以提供一个 CLIProxyAPI 登录参数。脚本只把它作为单个子进程参数传递，不使用 Shell 求值，并要求它符合 `--kebab-case`：

- 使用官方 CLIProxyAPI 参数
- 不在清单中添加安装命令、Shell、环境变量展开或凭据
- 本地覆盖清单在授权前必须检查

## 日志与输出

禁止输出：

- API Key、Authorization Header 或 OAuth Token
- 一次性设备码或回调 URL 中的敏感参数
- 账号邮箱
- 原始提示词、图片和 CodeBuddy 会话内容

诊断可以输出本地路径、模型 ID、Provider ID、状态码、脱敏错误、备份路径和监听地址。
