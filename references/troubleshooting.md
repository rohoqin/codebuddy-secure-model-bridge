# 排障与回滚

先定位故障层，再修改凭据或重装软件。

## `codebuddy_stale_system_proxy` / CodeBuddy 错误 3002

这表示正在运行的 CodeBuddy 进程可能缓存了一个已不可达的本地系统代理。它会同时影响 CodeBuddy 内置模型，但与自定义模型条目是否正确无关。

处理顺序：

1. 记下当前系统代理的实际地址和端口，只读检查端口是否有监听。
2. 完全退出 CodeBuddy，确认后台 `codebuddy --serve` 进程退出，再重新打开。
3. 重新执行 `audit`，确认 `codebuddy.network.stale` 为 `false`。
4. 用内置模型发送一句最小文本测试。

不要删除 `models.json`，不要重建内置模型，也不要让 CLIProxyAPI 接管系统代理。若重启后仍失败，再结合 CodeBuddy 日志中的请求目标和错误码判断是网络、登录态还是官方服务异常。

## `cliproxy_missing`

- macOS：执行 `bootstrap --apply`。若缺少 Homebrew，只从 `brew.sh` 官方来源交互安装，再重试。
- Windows：执行 `bootstrap --apply`。脚本会下载官方 Release、校验 `checksums.txt`，并安装到当前用户目录。

不要从网盘、论坛附件或未知镜像下载 CLIProxyAPI。

## `public_bind_requires_approval`

现有配置没有明确绑定回环地址。先确认是否有局域网或远程客户端依赖。若远程访问并非有意，运行：

```bash
python3 <skill-dir>/scripts/bridge.py bootstrap --apply --allow-rebind-local
```

若远程访问是有意的，停止。本 Skill 不管理对外暴露的代理。

## `bridge_secret_missing`

运行 `bootstrap --apply`，创建独立本地客户端 Key，并在不替换其他 Key 的前提下追加到 CLIProxyAPI 顶层 `api-keys`。

Provider OAuth 变化不要求创建新 Key。

## 服务在运行但 `/v1/models` 失败

依次检查：

1. 活跃配置中的端口
2. 独立客户端 Key 是否同时存在于 Skill 状态和 CLIProxyAPI 配置
3. 活跃进程是否使用审计报告的配置文件
4. 配置是否合法，服务日志是否显示加载成功

避免编辑第二份未生效配置。Homebrew、手工 LaunchAgent 和 Windows 便携安装常使用不同路径。

## Provider 模型缺失

只有 Provider 没有授权文件或已认证请求失败时，才重新运行 `authorize <provider>`。CLIProxyAPI 之外的 CLI 已登录，不代表代理已经获得授权。

授权后重新查询 `/v1/models`。预期模型仍不存在，可能是账号未开放、上游改名、被现有配置排除或处于冷却状态。不要为不存在的模型伪造别名。

## 文本可用，但图片、工具或推理失败

保留文本与流式均成功的模型，把失败的可选能力降级为 `false`。检查：

- CodeBuddy 是否按兼容协议发送 `image_url`、`tool_choice` 或推理参数
- CLIProxyAPI 是否选中了预期 Provider 路由
- 模型 ID 是否与其他 Provider 冲突
- 该能力是否真的能通过当前兼容协议使用

图片输入成功只证明模型能理解图片，不代表模型能生成图片。

## 手工 CodeBuddy 模型冲突

本 Skill 拒绝覆盖它未管理的同 ID 条目。保留手工条目；如需迁移，先逐字段比较并备份，或创建已验证且不冲突的别名。

## CodeBuddy 没显示新模型

确认 `models.json` 是数组，或是包含 `models` 数组的对象。打开模型设置或新建任务触发加载；仍未刷新时完全退出并重开 CodeBuddy。重复写入相同 JSON 不能修复应用缓存。

## Windows 启动项问题

本 Skill 管理的启动项位于当前用户的：

```text
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\codebuddy-gpt-gemini-bridge.cmd
```

若同名文件不是由本 Skill 创建，脚本会报告 `startup_conflict` 并停止。不要覆盖未知启动项。回滚时可先结束 `cli-proxy-api.exe`，再移除这个带有 `Managed by codebuddy-gpt-gemini-bridge` 标记的文件；不要删除其他 Startup 项。

## 回滚

凭据相关备份格式为：

```text
<filename>.backup-YYYYMMDD-HHMMSS
```

回滚步骤：

1. 停止当前写入或服务重启。
2. 核对备份确实属于当前源文件。
3. 将失败版本保留下来诊断，但不要放入仓库。
4. 原子恢复备份；macOS 保持 `0600`。
5. 重启或等待热加载。
6. 重新执行 `audit`、内置模型测试和自定义模型文本测试。

OAuth 文件不从其他 CLI 或其他电脑复制；需要时通过 Provider 原生流程重新授权。
