# CodeBuddy Multi-Model Secure Bridge

Bridge your own **OpenAI Codex / ChatGPT**, **Google Antigravity / Gemini**, and **xAI Grok** subscriptions into **CodeBuddy CN** through a loopback-only CLIProxyAPI proxy listening on `127.0.0.1:8317`.

> **macOS-first.** The best-tested path is Homebrew (`brew install router-for-me/tap/cliproxyapi`). Windows is supported too: it installs from the official `router-for-me/CLIProxyAPI` GitHub Release and verifies SHA-256 against `checksums.txt`.

> **Provenance.** This skill adapts the WorkBuddy multi-model secure bridge by Zhijian AI ([`zjp1997720/zhijian-skills/skills/workbuddy-cli-model-bridge`](https://github.com/zjp1997720/zhijian-skills/tree/main/skills/workbuddy-cli-model-bridge)); provider manifests and reference docs follow the upstream schema. CodeBuddy-specific adaptations (write path `~/.codebuddy/models.json`, vendor `user`, loopback port probing, Windows SHA-256 verification) are noted inline.

> This skill is a CodeBuddy adaptation of the [WorkBuddy multi-model secure bridge](https://github.com/router-for-me). Key differences:
> - Model write path changed from `~/.workbuddy/models.json` to **`~/.codebuddy/models.json`**
> - Custom model `vendor` uses CodeBuddy's actual **`"user"`** (instead of `"Custom"`)
> - Written fields trimmed to CodeBuddy's real schema: `id / name / vendor / url / apiKey / supportsToolCall / supportsImages / supportsReasoning`
> - Stale proxy detection switched to port probing (CodeBuddy CN is an Electron app and does not expose `HTTP(S)_PROXY` in process args)
> - Env var changed from `WORKBUDDY_BRIDGE_API_KEY` to **`CODEBUDDY_BRIDGE_API_KEY`**

## Capabilities

- Install / audit / repair / manage a loopback proxy
- Register only models that genuinely exist and pass probing; never treat a model name or marketing page as proof of capability
- Protect CodeBuddy built-in models and your manual custom entries (incremental merge, conflict warnings, never overwrite)
- Migrate state from the legacy `codebuddy-cli-model-bridge`
- Supports macOS and Windows

## Requirements

- **CodeBuddy CN** installed and opened at least once (generates `~/.codebuddy/models.json`)
- **CLIProxyAPI** proxy: install via Homebrew (`brew install router-for-me/tap/cliproxyapi`) or let the skill auto-download from the [GitHub Release](https://github.com/router-for-me/CLIProxyAPI/releases)
- A subscription CLI (any one):
  - OpenAI Codex: `codex` (`npm i -g @openai/codex` or the official installer), auth written to `~/.codex/auth.json`
  - Google Antigravity: `antigravity` / `agy`, auth written to `~/.config/antigravity`

## Install into CodeBuddy

Place this repository as a skill directory into CodeBuddy's skills path (the repo root is the skill root and must contain `SKILL.md`):

```bash
mkdir -p ~/.codebuddy/skills
cp -R codebuddy-secure-model-bridge ~/.codebuddy/skills/
```

Restart CodeBuddy; the skill then appears in the available skills list.

## Usage

All commands go through the skill's `scripts/bridge.py`:

```bash
python3 <skill-dir>/scripts/bridge.py audit      # audit first, write nothing
python3 <skill-dir>/scripts/bridge.py bootstrap   # preview the local bridge
python3 <skill-dir>/scripts/bridge.py sync        # sync catalog models into models.json

# Quota/rate-limit tolerance: a model is registered as long as it appears in the proxy's
# /v1/models catalog; live probing only refines capabilities. Transient failures (429/5xx/timeout)
# never drop a model (fall back to manifest-default capabilities).
python3 <skill-dir>/scripts/bridge.py sync --skip-probes   # skip probes entirely, register all catalog models (recommended when quota is exhausted)
python3 <skill-dir>/scripts/bridge.py sync --strict        # restore original strict behavior: drop a model if its probe fails
python3 <skill-dir>/scripts/bridge.py validate-provider providers/codex.json
```

> If `codebuddy_stale_system_proxy` appears, a leftover proxy was detected on 8080/8081. Fully quit and reopen CodeBuddy before retrying — do **not** change the system proxy or built-in models to work around it.

See `references/security-boundaries.md` and `references/troubleshooting.md` for the full security boundaries and troubleshooting guide.

## Security Model (Key Points)

- The proxy listens **only on the loopback address**, never exposed to LAN/public networks
- Model keys are counted by existence only — never read, never uploaded
- Built-in models and manual custom entries use incremental merge, never overwritten directly
- Does not modify the system proxy or intercept CodeBuddy's outbound traffic

## Install Source & Trust Level

The two platforms' proxy install trust chains are **not symmetric**; understand this before use:

| Platform | Install source | Verification |
|----------|----------------|--------------|
| Windows | `router-for-me/CLIProxyAPI` official GitHub Release | Download the same Release's `checksums.txt` and verify SHA-256; stop on mismatch |
| macOS | Third-party Homebrew tap `router-for-me/tap`'s `cliproxyapi` Formula | `brew install` only — **no version pinning, no checksum** |

The macOS tap is maintained by a third party and may silently pull different Formula content after `brew update`. This is a known trust gap versus the "install source" security boundary we emphasize. Mitigations:

- Pin the Formula version where possible, or pin the tap/commit state outside `brew`
- After install, record the actual version via `brew info router-for-me/tap/cliproxyapi` and verify `cli-proxyapi --version`
- If available, independently checksum / signature-check the installed binary
- For a stricter setup, download the macOS asset from the official Release and verify it using the same flow as Windows

`audit` reports the currently installed proxy version (`cliproxy.version`); verify it after every update.

## Provider Manifest Maintenance

`providers/*.json` is a recommended manifest of "models actually available in your subscription". It may list expected-future model names (e.g. `gpt-5.6-sol`, `gemini-3.6-flash-high`) — that is fine, because `sync` only registers models that genuinely appear in the proxy `/v1/models` catalog; unmatched models go into `missing_recommendations` and **never raise an error**.

But the manifest itself drifts as subscription-available models change; we recommend:

- Update the corresponding `providers/*.json` when your subscription adds/removes models
- Run `python3 <skill-dir>/scripts/bridge.py validate-provider providers/<id>.json` before committing to check the schema
- Do not publish a manifest that has not passed `validate-provider`

## License

[MIT](./LICENSE.md).

---

# CodeBuddy 多模型安全接入

把你自己拥有的 **OpenAI Codex / ChatGPT**、**Google Antigravity / Gemini** 与 **xAI Grok** 订阅，通过一台只监听本机回环地址（`127.0.0.1:8317`）的 [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI) 代理，安全接入 **CodeBuddy CN**。

> **macOS 优先**。最佳验证路径是 Homebrew（`brew install router-for-me/tap/cliproxyapi`）。Windows 也支持：从官方 `router-for-me/CLIProxyAPI` GitHub Release 安装，并用 `checksums.txt` 校验 SHA-256。

> **来源说明**。本技能改编自 Zhijian AI 的 WorkBuddy 多模型安全接入（[`zjp1997720/zhijian-skills/skills/workbuddy-cli-model-bridge`](https://github.com/zjp1997720/zhijian-skills/tree/main/skills/workbuddy-cli-model-bridge)）；provider 清单与参考文档沿用上游 schema。CodeBuddy 专属适配（写入路径 `~/.codebuddy/models.json`、vendor `user`、回环端口探测、Windows SHA-256 校验）已在正文标注。

> 本技能是 [WorkBuddy 多模型安全接入](https://github.com/router-for-me) 的 CodeBuddy 适配版。主要差异：
> - 模型写入路径由 `~/.workbuddy/models.json` 改为 **`~/.codebuddy/models.json`**
> - 自定义模型 `vendor` 字段使用 CodeBuddy 实际的 **`"user"`**（而非 `"Custom"`）
> - 写入字段精简为 CodeBuddy 真实 schema：`id / name / vendor / url / apiKey / supportsToolCall / supportsImages / supportsReasoning`
> - 失效代理检测改为端口探测（CodeBuddy CN 是 Electron 应用，不会在进程参数里暴露 `HTTP(S)_PROXY`）
> - 环境变量由 `WORKBUDDY_BRIDGE_API_KEY` 改为 **`CODEBUDDY_BRIDGE_API_KEY`**

## 能力

- 安装、审计、修复、管理回环代理
- 只注册**真实存在且探测通过**的模型，不把模型名或宣传页当能力证明
- 保护 CodeBuddy 内置模型与你的手动自定义条目（增量合并，冲突告警，绝不覆盖）
- 兼容迁移旧版 `codebuddy-cli-model-bridge` 的本地 Key 与管理清单
- 支持 macOS 与 Windows

## 要求

- **CodeBuddy CN** 已安装并至少打开过一次（生成 `~/.codebuddy/models.json`）
- **CLIProxyAPI** 代理：通过 Homebrew（`brew install router-for-me/tap/cliproxyapi`）安装，或让技能从 [GitHub Release](https://github.com/router-for-me/CLIProxyAPI/releases) 自动下载
- 订阅 CLI（任选其一）：
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

macOS 的 tap 由第三方维护，`brew update` 后可能静默拉取到 Formula 指向的新内容。这与本项目强调的"安装来源"安全边界存在落差。缓解建议：

- 尽量锁定 Formula 版本（若该版本化 Formula 可用），或在 `brew` 之外固定 tap/commit 状态
- 安装后用 `brew info router-for-me/tap/cliproxyapi` 记录实际版本，并核对 `cli-proxyapi --version`
- 如可用，对本地已安装的二进制做一次独立 checksum / 签名核对
- 更保守的场景可改为从官方 Release 手动下载 macOS 资产，按 Windows 相同流程校验后落地

`audit` 会报告当前安装的代理版本（`cliproxy.version`），建议每次更新后核对。

## Provider 清单维护

`providers/*.json` 是"按订阅实际可用模型"的推荐清单。清单里可以列出**预期未来会开放**的型号（如 `gpt-5.6-sol`、`gemini-3.6-flash-high`），这没问题——`sync` 只会注册真实出现在代理 `/v1/models` 目录里的模型，未命中的型号会进入 `missing_recommendations` 而**不会报错**。

但清单本身会随订阅可用模型变化而脱节，建议：

- 订阅新增/下线模型时，同步更新对应 `providers/*.json`
- 提交前用 `python3 <skill-dir>/scripts/bridge.py validate-provider providers/<id>.json` 校验 schema
- 不要把未经 `validate-provider` 校验的清单直接发布

## 许可

[MIT](./LICENSE.md) — 版权信息见 LICENSE.md。
