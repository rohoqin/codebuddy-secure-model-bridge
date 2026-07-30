# CodeBuddy 多模型安全接入

把你自己拥有的 **OpenAI Codex / ChatGPT** 与 **Google Antigravity / Gemini** 订阅，通过一台只监听本机回环地址（`127.0.0.1:8317`）的 [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI) 代理，安全接入 **CodeBuddy CN**。

> 本技能是 [WorkBuddy 多模型安全接入](https://github.com/router-for-me) 的 CodeBuddy 适配版。主要差异：
> - 模型写入路径由 `~/.workbuddy/models.json` 改为 **`~/.codebuddy/models.json`**
> - 自定义模型 `vendor` 字段使用 CodeBuddy 实际的 **`"user"`**（而非 `"Custom"`）
> - 写入字段精简为 CodeBuddy 真实 schema：`id / name / vendor / url / apiKey / supportsToolCall / supportsImages / supportsReasoning`
> - 失效代理检测改为端口探测（CodeBuddy CN 是 Electron 应用，不会在进程参数里暴露 `HTTP(S)_PROXY`）
> - 环境变量由 `WORKBUDDY_BRIDGE_API_KEY` 改为 **`CODEBUDDY_BRIDGE_API_KEY`**

## 能力

- 安装 / 审计 / 修复 / 管理回环代理
- 只注册**真实存在且探测通过**的模型，不把模型名或宣传页当能力证明
- 保护 CodeBuddy 内置模型与你的手动自定义条目（增量合并，冲突告警，绝不覆盖）
- 兼容迁移旧版 `codebuddy-cli-model-bridge` 的本地 Key 与管理清单
- 支持 macOS 与 Windows

## 要求

- **CodeBuddy CN** 已安装并至少打开过一次（生成 `~/.codebuddy/models.json`）
- **CLIProxyAPI** 代理：通过 Homebrew（`brew install router-for-me/tap/cliproxyapi`）安装，或让技能从 [GitHub Release](https://github.com/router-for-me/CLIProxyAPI/releases) 自动下载
- 订阅 CLI（任选）：
  - OpenAI Codex：`codex`（`npm i -g @openai/codex` 或官方安装方式），认证写入 `~/.codex/auth.json`
  - Google Antigravity：`antigravity` / `agy`，认证写入 `~/.config/antigravity`

## 安装到 CodeBuddy

把本仓库作为技能目录放入 CodeBuddy 的 skills 路径（仓库根目录即技能根目录，需包含 `SKILL.md`）：

```bash
mkdir -p ~/.codebuddy/skills
cp -R codebuddy-secure-model-bridge ~/.codebuddy/skills/
```

重启 CodeBuddy 后，技能即出现在可用技能列表中。

## 使用

所有命令统一入口为技能内的 `scripts/bridge.py`：

```bash
python3 <skill-dir>/scripts/bridge.py audit      # 先审计，不写配置
python3 <skill-dir>/scripts/bridge.py bootstrap   # 预览本地桥接
python3 <skill-dir>/scripts/bridge.py sync        # 把目录里存在的模型同步进 models.json

# 配额/限流容错：模型只要出现在代理 /v1/models 目录里就注册，实时探测只用来细化能力；
# 429/5xx/超时这类瞬时失败不会丢模型（回退到 provider 默认能力）。
python3 <skill-dir>/scripts/bridge.py sync --skip-probes   # 完全跳过探测，直接按清单注册全部目录模型（配额耗尽时推荐）
python3 <skill-dir>/scripts/bridge.py sync --strict        # 恢复原始严格行为：探测不过就跳过该模型
python3 <skill-dir>/scripts/bridge.py validate-provider providers/codex.json
```

> 若出现 `codebuddy_stale_system_proxy`，说明检测到 8080/8081 上有遗留代理。请完全退出并重新打开 CodeBuddy 后再重试，**不要**去改系统代理或内置模型来绕过。

更完整的安全边界与排错指南见 `references/security-boundaries.md` 与 `references/troubleshooting.md`。

## 安全模型（要点）

- 代理**仅监听回环地址**，不暴露到局域网/公网
- 模型 Key 只统计存在性，不读取、不上传
- 内置模型与手动自定义条目采用增量合并，永不直接覆盖
- 不修改系统代理、不拦截 CodeBuddy 对外流量

## 安装来源与信任等级

两个平台的代理安装信任链**并不对称**，使用前应了解：

| 平台 | 安装来源 | 校验方式 |
|------|----------|----------|
| Windows | `router-for-me/CLIProxyAPI` 官方 GitHub Release | 下载同 Release 的 `checksums.txt`，校验 SHA-256；不匹配即停止 |
| macOS | 第三方 Homebrew tap `router-for-me/tap` 的 `cliproxyapi` Formula | 仅 `brew install`，**无版本锁定、无 checksum** |

macOS 的 tap 由第三方维护，`brew update` 后可能静默拉取到 Formula 指向的新内容。这与本项目强调的“安装来源”安全边界存在落差。缓解建议：

- 尽量锁定 Formula 版本（若该版本化 Formula 可用），或在 `brew` 之外固定 tap/commit 状态；
- 安装后用 `brew info router-for-me/tap/cliproxyapi` 记录实际版本，并核对 `cli-proxyapi --version`；
- 如可用，对本地已安装的二进制做一次独立 checksum / 签名核对；
- 更保守的场景可改为从官方 Release 手动下载 macOS 资产，按 Windows 相同流程校验后落地。

`audit` 会报告当前安装的代理版本（`cliproxy.version`），建议每次更新后核对。

## Provider 清单维护

`providers/*.json` 是“按订阅实际可用模型”的推荐清单。清单里可以列出**预期未来会开放**的型号（如 `gpt-5.6-sol`、`gemini-3.6-flash-high`），这没问题——`sync` 只会注册真实出现在代理 `/v1/models` 目录里的模型，未命中的型号会进入 `missing_recommendations` 而**不会报错**。

但清单本身会随订阅可用模型变化而脱节，建议：

- 订阅新增/下线模型时，同步更新对应 `providers/*.json`；
- 提交前用 `python3 <skill-dir>/scripts/bridge.py validate-provider providers/<id>.json` 校验 schema；
- 不要把未经 `validate-provider` 校验的清单直接发布。

## 许可

[MIT](./LICENSE.md) — 基于 Zhijian AI 的 WorkBuddy 原版改编。
