# Onboarding a New CLI Provider

> **Adapted from** [`zjp1997720/zhijian-skills/skills/workbuddy-cli-model-bridge`](https://github.com/zjp1997720/zhijian-skills/tree/main/skills/workbuddy-cli-model-bridge) (`references/onboarding-new-cli.md`), with CodeBuddy-specific paths and the `codebuddy` capability key. Local machine overrides live in `~/.config/codebuddy-gpt-gemini-bridge/providers.d/` on this skill.

Use a local machine manifest first, verify with `validate-provider`, then contribute the manifest back to the bundled `providers/` once it is proven.

## Step 1: Local Override Manifest

Create a file named `<id>.json` in the machine-local providers directory:

```bash
mkdir -p ~/.config/codebuddy-gpt-gemini-bridge/providers.d
"$EDITOR" ~/.config/codebuddy-gpt-gemini-bridge/providers.d/<id>.json
```

The local manifest **overrides** the bundled manifest with the same `id`. Fields and the schema follow [`provider-schema.md`](provider-schema.md); the capability block uses the key `codebuddy`.

Fill in:

- `cli.commands`: the CLI you will run to check login (e.g. `mycli`).
- `cli.auth_hints`: relative paths under the user home that indicate a logged-in state (no `..`, no absolute paths).
- `cliproxy.provider`: the upstream provider tag understood by CLIProxyAPI.
- `cliproxy.login_flag` (optional): a single `--kebab-case` flag for CLIProxyAPI's native OAuth flow, passed as one subprocess argument.
- `models[]`: recommendation list with `codebuddy` capability hints.

## Step 2: Validate

```bash
python3 <skill-dir>/scripts/bridge.py validate-provider ~/.config/codebuddy-gpt-gemini-bridge/providers.d/<id>.json
```

`validate-provider` rejects:

- unknown top-level keys
- unsafe `model_catalogs` paths (absolute or traversal) or a non-`json` format
- invalid `sources` evidence URLs
- non-kebab `id` or `login_flag`
- malformed `patterns` regex
- unknown `codebuddy` keys or non-positive token limits
- duplicate recommendation `key`s

## Step 3: Try a Local Sync

```bash
python3 <skill-dir>/scripts/bridge.py authorize <id>
python3 <skill-dir>/scripts/bridge.py sync --providers <id> --skip-probes --apply
```

Use `--skip-probes` only for offline validation; real installs must probe.

## Step 4: Contribute Back

Once the local manifest is proven, copy it into the bundled `providers/<id>.json`, re-run `validate-provider`, and submit it. Keep `auth_hints` relative and minimal.

## Adapter Minimum Bar

A CLI is worth onboarding only if it:

- Has a stable CLI subcommand the script can detect login from
- Has a CLIProxyAPI `provider` tag
- Exposes models that genuinely appear in the proxy `/v1/models` catalog
- Does not require reusing another CLI's OAuth tokens or writing Provider credentials into CodeBuddy
