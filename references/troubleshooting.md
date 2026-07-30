# Troubleshooting and Rollback

Locate the failing layer before changing credentials or reinstalling.

## `codebuddy_stale_system_proxy` / CodeBuddy Error 3002

This means the running CodeBuddy process may have cached a now-unreachable local system proxy. It affects CodeBuddy built-in models too, but has nothing to do with whether a custom model entry is correct.

Handling order:

1. Note the actual address and port of the current system proxy; read-only check whether anything is listening on the port.
2. Fully quit CodeBuddy, confirm the background `codebuddy --serve` process has exited, then reopen.
3. Re-run `audit` and confirm `codebuddy.network.stale` is `false`.
4. Send one minimal text test with a built-in model.

Do not delete `models.json`, do not rebuild built-in models, and do not let CLIProxyAPI take over the system proxy. If it still fails after restart, combine the request target and error code from CodeBuddy's logs to judge whether it is a network, login-state, or official-service problem.

## `cliproxy_missing`

- macOS: run `bootstrap --apply`. If Homebrew is missing, only install it interactively from the official `brew.sh` source, then retry.
- Windows: run `bootstrap --apply`. The script downloads the official Release, verifies `checksums.txt`, and installs to the current user directory.

Do not download CLIProxyAPI from a cloud drive, forum attachment, or unknown mirror.

## `public_bind_requires_approval`

The existing config does not explicitly bind the loopback address. First confirm whether LAN or remote clients depend on it. If remote access is not intended, run:

```bash
python3 <skill-dir>/scripts/bridge.py bootstrap --apply --allow-rebind-local
```

If remote access is intended, stop. This skill does not manage an outward-facing proxy.

## `bridge_secret_missing`

Run `bootstrap --apply` to create a distinct local client key and append it to CLIProxyAPI's top-level `api-keys` without replacing other keys.

A change in Provider OAuth does not require creating a new key.

## Service Running but `/v1/models` Fails

Check in order:

1. The port in the active config
2. Whether the distinct client key exists in both the skill state and the CLIProxyAPI config
3. Whether the active process uses the config reported by the audit
4. Whether the config is valid and the service log shows a successful load

Avoid editing a second, non-effective config. Homebrew, a manual LaunchAgent, and a Windows portable install often use different paths.

## Provider Model Missing

Only re-run `authorize <provider>` when the Provider has no auth file or an authenticated request fails. A CLI login outside CLIProxyAPI does not mean the proxy is authorized.

Re-query `/v1/models` after authorization. An expected model that still does not appear may be unopened on the account, renamed upstream, excluded by the current config, or in a cooldown. Do not fabricate an alias for a non-existent model.

## Text Works but Image, Tool, or Reasoning Fails

Keep models whose text and streaming both succeeded, and downgrade the failed optional capability to `false`. Check:

- Whether CodeBuddy sends `image_url`, `tool_choice`, or reasoning parameters on a compatible protocol
- Whether CLIProxyAPI selected the expected Provider route
- Whether the model ID conflicts with another Provider
- Whether the capability can actually be used through the current compatible protocol

Successful image input only proves the model can understand images, not that it can generate them.

## Manual CodeBuddy Model Conflict

This skill refuses to overwrite a same-ID entry it does not manage. Preserve the manual entry; to migrate, compare field by field and back up first, or create a verified, non-conflicting alias.

## CodeBuddy Does Not Show New Models

Confirm `models.json` is an array, or an object containing a `models` array. Open model settings or start a new task to trigger loading; if it still does not refresh, fully quit and reopen CodeBuddy. Repeatedly writing the same JSON does not fix the app cache.

## Windows Startup Item Issues

The startup item managed by this skill lives in the current user's:

```text
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\codebuddy-gpt-gemini-bridge.cmd
```

If a same-named file was not created by this skill, the script reports `startup_conflict` and stops. Do not overwrite an unknown startup item. To roll back, first end `cli-proxy-api.exe`, then remove this file tagged `Managed by codebuddy-gpt-gemini-bridge`; do not delete other Startup items.

## Rollback

Credential-related backups use the format:

```text
<filename>.backup-YYYYMMDD-HHMMSS
```

Rollback steps:

1. Stop the current write or restart the service.
2. Confirm the backup really belongs to the current source file.
3. Keep the failed version for diagnosis, but do not put it in the repository.
4. Restore the backup atomically; keep `0600` on macOS.
5. Restart or wait for hot reload.
6. Re-run `audit`, a built-in model test, and a custom model text test.

Do not copy OAuth files from another CLI or another machine; re-authorize through the Provider's native flow when needed.
