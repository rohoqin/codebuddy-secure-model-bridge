---
name: codebuddy-secure-model-bridge
description: macOS-first skill that safely installs, audits, repairs, and manages a loopback-only CLIProxyAPI bridge connecting subscription-backed OpenAI Codex/GPT, Google Antigravity/Gemini, and xAI Grok models to CodeBuddy (Windows Release + SHA-256 verification also supported). Use when a CodeBuddy user asks to connect GPT, connect Gemini, connect Grok, use ChatGPT/Gemini/Grok subscription models, install a local model bridge, repair custom GPT/Gemini/Grok, restore CodeBuddy built-in models affected by a proxy, or sync available models into CodeBuddy. Preserves CodeBuddy built-in models and manual custom entries.
---

# CodeBuddy Multi-Model Secure Bridge

> **Provenance.** This skill is a CodeBuddy adaptation of the WorkBuddy multi-model secure bridge by Zhijian AI ([`zjp1997720/zhijian-skills/skills/workbuddy-cli-model-bridge`](https://github.com/zjp1997720/zhijian-skills/tree/main/skills/workbuddy-cli-model-bridge)). Provider manifests and several reference documents follow the upstream schema and guidance; CodeBuddy-specific adaptations are called out inline. Key differences:
> - Model write path `~/.workbuddy/models.json` → **`~/.codebuddy/models.json`**
> - Custom model `vendor` uses CodeBuddy's actual **`"user"`** (not `"Custom"`)
> - Written fields trimmed to CodeBuddy's schema: `id / name / vendor / url / apiKey / supportsToolCall / supportsImages / supportsReasoning` (+ token limits when resolved)
> - Stale proxy detection uses **loopback port probing** (CodeBuddy CN is an Electron app; it does not expose `HTTP(S)_PROXY` in process args)
> - macOS-first; **Windows** installs from the official `router-for-me/CLIProxyAPI` Release with **SHA-256 verification** against `checksums.txt`
> - Capability block key is **`codebuddy`** (mirrors upstream `workbuddy`)

> **Platform support.** This skill is **macOS-first**. The primary, best-tested install path is Homebrew (`router-for-me/tap/cliproxyapi`). Windows is also supported: it downloads the architecture-matched GitHub Release ZIP and verifies SHA-256 before install.

Connect a user's own Codex/ChatGPT and Antigravity/Gemini subscriptions to CodeBuddy through a CLIProxyAPI proxy bound to the local loopback address. Only register models that genuinely exist and pass probing; never treat a model name or marketing page as proof of capability.

## Locate the Skill Directory

Locate the absolute path of the currently loaded skill directory and record it as `<skill-dir>`. Do not assume a fixed install location.

Single entry point:

```bash
python3 <skill-dir>/scripts/bridge.py
```

On Windows, prefer CodeBuddy's bundled Python. If the command is `python`, keep the same arguments.

## Standard Workflow

### 1. Audit First, Don't Write Config Yet

```bash
python3 <skill-dir>/scripts/bridge.py audit
```

Read the JSON result and confirm:

- CLIProxyAPI exists, listens only on the loopback address, and is reachable by config
- CodeBuddy `models.json` exists and how many models it currently holds
- Codex and Antigravity OAuth files are counted only — their contents are never read
- The running CodeBuddy may have cached a stale local system proxy

If `codebuddy_stale_system_proxy` appears, stop modifying models immediately. Ask the user to fully quit and reopen CodeBuddy, then re-run the audit. Do not modify the system proxy, `HTTP_PROXY`, `HTTPS_PROXY`, or the built-in model config to work around the issue.

Establish a baseline where the current CodeBuddy built-in models respond normally. If the current task already runs on a built-in model, that normal reply can serve as the baseline; otherwise ask the user to send one short test message with any built-in model.

### 2. Preview and Deploy the Local Bridge

Preview first:

```bash
python3 <skill-dir>/scripts/bridge.py bootstrap
```

Only apply when the user explicitly asks to install, configure, or repair:

```bash
python3 <skill-dir>/scripts/bridge.py bootstrap --apply
```

On macOS, use Homebrew to install and launch CLIProxyAPI. If Homebrew is missing, only guide the user to install it from the official `brew.sh` source; do not run untrusted install commands.

On Windows, download the architecture-matched ZIP from the `router-for-me/CLIProxyAPI` official GitHub Release, verify its SHA-256 against the same Release's `checksums.txt`, then install it to the user directory and create a user-level startup item. Stop on verification failure; never execute the downloaded content.

Always:

- Bind `127.0.0.1:8317`
- Disable remote management and the control panel
- Create a distinct, random client key
- Preserve existing CLIProxyAPI keys and unrelated config
- Create a timestamped backup before making changes

If an existing config listens on `0.0.0.0`, `::`, or without an explicit loopback address, first explain the impact of a remote client; only allow `--allow-rebind-local` after confirming remote access is not needed.

### 3. Authorize GPT and Gemini Separately

Authorize only the providers the user requests:

```bash
python3 <skill-dir>/scripts/bridge.py authorize codex
python3 <skill-dir>/scripts/bridge.py authorize antigravity
```

Let CLIProxyAPI's native OAuth flow open the browser and have the user complete sign-in, then continue. Do not copy tokens from Codex, the Gemini CLI, or the browser; do not write Provider OAuth credentials into CodeBuddy.

An existing CLI login is only a discovery signal; CLIProxyAPI may still require its own OAuth authorization. Use an account the user owns and is authorized to use, and remind the user to review subscription terms, quotas, and third-party client limits.

### 4. Probe and Sync Models

Connect GPT and Gemini together:

```bash
python3 <skill-dir>/scripts/bridge.py sync --providers codex,antigravity --apply
```

When connecting only one, pass only the corresponding provider.

Sync must:

- Read the account's actually available models from the live `/v1/models`
- Probe text, SSE streaming, tools, image input, and reasoning control separately
- Skip models whose text or streaming probe fails
- Downgrade a failed optional capability to `false`
- Merge into CodeBuddy atomically, preserving manual models and unrelated entries
- Refuse to overwrite a non-Skill-managed entry with the same ID
- Migrate the legacy `codebuddy-cli-model-bridge` local key and managed manifest without re-authorizing or creating conflicts
- Not interpret an image-understanding probe as image-generation capability

Do not use `--skip-probes` in a real install. That flag is only for offline testing.

### 5. Verify CodeBuddy Has No Regression

Run again:

```bash
python3 <skill-dir>/scripts/bridge.py audit
```

Confirm:

- CLIProxyAPI still listens only on the loopback address
- GPT/Gemini models were written with no manual-entry conflicts
- CodeBuddy's network audit shows no stale system proxy
- CodeBuddy has loaded the new `models.json`
- The built-in model used before the install still replies normally
- At least one GPT and one Gemini model each completed one real text call

If CodeBuddy has not refreshed the model list, open model settings or start a new task; if it still does not refresh, fully quit and reopen CodeBuddy. Do not repeatedly overwrite the same JSON.

Report provider, model ID, capability probe results, backup path, and remaining user actions. Do not output API keys, OAuth tokens, one-time authorization codes, account emails, Authorization headers, raw prompts, or image payloads.

## Repair Workflow

When a model fails or CodeBuddy shows `3002`:

1. Run `audit` and distinguish between the bridge service, client key, Provider OAuth, model routing, CodeBuddy cache, and system proxy.
2. If logs point to an unreachable local system proxy port, fully quit and reopen CodeBuddy first; do not modify `models.json`.
3. If CLIProxyAPI is unreachable, prefer restoring the existing service before reinstalling.
4. Re-run `authorize` only when Provider authorization is missing or an auth request fails.
5. Re-run the affected provider's `sync --apply` and verify with a real request.

Provider OAuth renewal does not require rotating the local proxy key used by CodeBuddy. Their lifecycles differ.

Read [troubleshooting.md](references/troubleshooting.md) when classifying errors, handling conflicts, or rolling back. Read [security-boundaries.md](references/security-boundaries.md) before any action involving service exposure, credentials, or install behavior.

## Completion Criteria

Declare completion only when all hold:

- The audit shows no unresolved security errors
- CLIProxyAPI is reachable on the loopback address
- Registered models pass text and streaming probes
- Each enabled optional capability passed its probe
- Manual models and CodeBuddy built-in models are intact
- At least one genuinely available GPT model and one Gemini model exist, or it is explicitly reported that the account has no such model
- Backup and rollback paths have been reported

If any item is not verified, mark the result as "unverified"; do not claim success.
