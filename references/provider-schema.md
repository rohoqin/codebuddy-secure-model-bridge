# Provider Manifest Schema

> **Adapted from** [`zjp1997720/zhijian-skills/skills/workbuddy-cli-model-bridge`](https://github.com/zjp1997720/zhijian-skills/tree/main/skills/workbuddy-cli-model-bridge) (`references/provider-schema.md`). This CodeBuddy version uses the capability block key **`codebuddy`** (upstream uses `workbuddy`), and `model_catalogs` here supports **JSON only** (TOML is intentionally unsupported to avoid a `tomllib` dependency on Python 3.10). Everything else follows the upstream contract. Run `python3 <skill-dir>/scripts/bridge.py validate-provider <file>` before committing any manifest.

A provider manifest declares "which models are actually available in this subscription" plus the CLI/CLIProxyAPI wiring and the CodeBuddy capability hints. Sync only registers models that genuinely appear in the proxy `/v1/models` catalog; unmatched entries go to `missing_recommendations` and never raise.

## Top Level

| Field | Type | Notes |
|-------|------|-------|
| `schema_version` | int | Must equal the script's `SCHEMA_VERSION` (currently `1`). |
| `id` | str | kebab-case, e.g. `codex`, `xai-grok`, `antigravity`. Used as the model `owned_by`. |
| `display_name` | str | Human label. |
| `cli` | object | `{ commands: string[], auth_hints: string[] }`. `auth_hints` are relative paths under the user home; no `..` and no absolute paths. |
| `cliproxy` | object (optional) | `{ provider, login_flag?, auth_file_prefixes? }`. `login_flag` must be a single `--kebab-case` flag, passed as one subprocess argument, never via shell. |
| `model_catalogs` | array (optional) | Declarative model catalogs. See below. |
| `models` | array | Recommendations. See below. |

## `model_catalogs` (optional)

Each entry tells the script where to read **exact** per-model token limits, by model ID:

```json
"model_catalogs": [
  {
    "path": ".codex/cliproxyapi-catalog.json",
    "format": "json",
    "id_fields": ["id"],
    "input_fields": ["context_window"],
    "output_fields": ["max_output_tokens"]
  }
]
```

- `format` must be `"json"` for this skill.
- `path` is relative to the user home and must not be absolute or contain `..`.
- `sources` evidence URLs in `limits_by_model` must be `http(s)://`.

## `models[]` Recommendations

| Field | Type | Notes |
|-------|------|-------|
| `key` | str | Stable recommendation name; unique within the manifest. |
| `candidates` | string[] | Model IDs to try, in order. |
| `patterns` | string[] (optional) | Regex fallbacks matched against live `/v1/models` IDs. Must be valid regex. |
| `optional` | bool (optional) | `true` marks a **Fast** or auxiliary variant; its absence does not block the main model. |
| `codebuddy` | object | Capability hints (below). |
| `limits_by_model` | object (optional) | `{ "<exact-model-id>": { maxInputTokens, maxOutputTokens, sources? } }`. Highest-precedence token-limit source. |
| `reasoning` | object (optional) | `{ defaultEffort, supportedEfforts[], canDisableThinking }`. |
| `useCustomProtocol` | bool (optional) | Route this model through CLIProxyAPI's provider-native protocol. |
| `onlyReasoning` | bool (optional) | Model supports reasoning only, not plain chat. |

### `codebuddy` capability block

| Field | Type | Notes |
|-------|------|-------|
| `supportsToolCall` | bool | |
| `supportsImages` | bool | Image **input/understanding**; does not imply image generation. |
| `supportsReasoning` | bool | |
| `maxInputTokens` | int (optional) | Fallback token limit when no catalog/limits_by_model match. Must be `> 0`. |
| `maxOutputTokens` | int (optional) | Fallback token limit. Must be `> 0`. |

`validate-provider` rejects unknown `codebuddy` keys and non-positive or non-int limits. Resolution order at sync time: `limits_by_model[exact id]` → `model_catalogs[exact id]` → `codebuddy.maxInputTokens/OutputTokens`.

## Example

```json
{
  "schema_version": 1,
  "id": "codex",
  "display_name": "OpenAI Codex",
  "cli": { "commands": ["codex"], "auth_hints": [".codex/auth.json"] },
  "cliproxy": { "provider": "codex", "login_flag": "--codex-login", "auth_file_prefixes": ["codex-"] },
  "model_catalogs": [
    { "path": ".codex/cliproxyapi-catalog.json", "format": "json", "id_fields": ["id"], "input_fields": ["context_window"], "output_fields": ["max_output_tokens"] }
  ],
  "models": [
    {
      "key": "gpt-5.6-sol",
      "candidates": ["gpt-5.6-sol"],
      "codebuddy": { "supportsToolCall": true, "supportsImages": true, "supportsReasoning": true },
      "limits_by_model": {
        "gpt-5.6-sol": { "maxInputTokens": 1050000, "maxOutputTokens": 128000, "sources": { "context_window": "https://help.openai.com/en/articles/9624314" } }
      },
      "reasoning": { "defaultEffort": "high", "supportedEfforts": ["low", "medium", "high"], "canDisableThinking": true },
      "useCustomProtocol": true
    },
    {
      "key": "gpt-5.6-sol-fast",
      "candidates": ["gpt-5.6-sol-fast"],
      "optional": true,
      "codebuddy": { "supportsToolCall": true, "supportsImages": true, "supportsReasoning": true }
    }
  ]
}
```
