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
python3 <skill-dir>/scripts/bridge.py repair      # 仅修复代理与 models.json 权限
python3 <skill-dir>/scripts/bridge.py validate-provider -p providers/codex.json
```

> 若出现 `codebuddy_stale_system_proxy`，说明检测到 8080/8081 上有遗留代理。请完全退出并重新打开 CodeBuddy 后再重试，**不要**去改系统代理或内置模型来绕过。

更完整的安全边界与排错指南见 `references/security-boundaries.md` 与 `references/troubleshooting.md`。

## 安全模型（要点）

- 代理**仅监听回环地址**，不暴露到局域网/公网
- 模型 Key 只统计存在性，不读取、不上传
- 内置模型与手动自定义条目采用增量合并，永不直接覆盖
- 不修改系统代理、不拦截 CodeBuddy 对外流量

## 许可

[MIT](./LICENSE.md) — 基于 Zhijian AI 的 WorkBuddy 原版改编，版权信息见 LICENSE。
