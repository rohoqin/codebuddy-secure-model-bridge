#!/usr/bin/env python3
"""Minimal regression tests for scripts/bridge.py.

Run from the repo root:

    python3 tests/test_bridge.py

Only the standard library is used so the suite runs anywhere Python 3.10+ is available.
"""

import argparse
import io
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import bridge  # noqa: E402


class YamlHelpersTest(unittest.TestCase):
    def test_top_level_scalar(self):
        text = 'host: "127.0.0.1"\nport: 8317\nfoo: bar\n'
        self.assertEqual(bridge.top_level_scalar(text, "host"), "127.0.0.1")
        self.assertEqual(bridge.top_level_scalar(text, "port"), "8317")
        self.assertIsNone(bridge.top_level_scalar(text, "missing"))

    def test_replace_top_level_scalar(self):
        text = 'host: "0.0.0.0"\nport: 8317\n'
        updated = bridge.replace_top_level_scalar(text, "host", "127.0.0.1")
        self.assertIn('host: "127.0.0.1"', updated)
        self.assertNotIn("0.0.0.0", updated)

    def test_yaml_list_values(self):
        text = "api-keys:\n  - a\n  - b\n"
        self.assertEqual(bridge.yaml_list_values(text, "api-keys"), ["a", "b"])

    def test_ensure_yaml_list_value_idempotent(self):
        text = "api-keys:\n  - existing\n"
        out, changed = bridge.ensure_yaml_list_value(text, "api-keys", "existing")
        self.assertFalse(changed)
        out2, changed2 = bridge.ensure_yaml_list_value(text, "api-keys", "new")
        self.assertTrue(changed2)
        self.assertIn("new", bridge.yaml_list_values(out2, "api-keys"))


class ConfigFactsTest(unittest.TestCase):
    def test_loopback_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.yaml"
            path.write_text('host: "127.0.0.1"\nport: 8317\n', encoding="utf-8")
            facts = bridge.config_facts(path, Path.home())
        self.assertTrue(facts["loopback_only"])
        self.assertEqual(facts["port"], 8317)

    def test_lan_config_not_loopback(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.yaml"
            path.write_text('host: "192.168.1.10"\nport: 8317\n', encoding="utf-8")
            facts = bridge.config_facts(path, Path.home())
        self.assertFalse(facts["loopback_only"])


class BootstrapPreflightTest(unittest.TestCase):
    def _write(self, tmp, text):
        path = Path(tmp) / "config.yaml"
        path.write_text(text, encoding="utf-8")
        return path

    def test_loopback_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, 'host: "127.0.0.1"\n')
            self.assertIsNotNone(bridge.bootstrap_config_preflight(path, allow_rebind_local=False))

    def test_unspecified_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, 'host: "0.0.0.0"\n')
            self.assertIsNotNone(bridge.bootstrap_config_preflight(path, allow_rebind_local=False))

    def test_lan_requires_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, 'host: "192.168.1.10"\n')
            with self.assertRaises(bridge.BridgeError):
                bridge.bootstrap_config_preflight(path, allow_rebind_local=False)

    def test_lan_allowed_with_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, 'host: "192.168.1.10"\n')
            self.assertIsNotNone(bridge.bootstrap_config_preflight(path, allow_rebind_local=True))


class MergeModelsTest(unittest.TestCase):
    def test_unmanaged_entry_protected(self):
        existing = [{"id": "manual-model", "name": "manual"}]
        incoming = [("codex", {"id": "manual-model", "name": "hijack"})]
        merged, changes, _ = bridge.merge_codebuddy_models(existing, incoming, set())
        self.assertEqual(changes["conflicts"], ["manual-model"])
        self.assertEqual(merged[0]["name"], "manual")

    def test_managed_entry_updated(self):
        existing = [{"id": "m", "name": "old"}]
        incoming = [("codex", {"id": "m", "name": "new", "vendor": "user"})]
        merged, changes, _ = bridge.merge_codebuddy_models(existing, incoming, {"m"})
        self.assertEqual(changes["updated"], ["m"])
        self.assertEqual(merged[0]["name"], "new")


class ProxyDetectionTest(unittest.TestCase):
    def test_looks_like_proxy_process(self):
        self.assertTrue(bridge.looks_like_proxy_process("charles"))
        self.assertTrue(bridge.looks_like_proxy_process("clashx"))
        self.assertFalse(bridge.looks_like_proxy_process("node"))
        self.assertFalse(bridge.looks_like_proxy_process(None))

    def test_active_proxy_flags_proxy_like(self):
        with mock.patch.object(bridge, "platform") as mp, \
                mock.patch.object(bridge, "shutil") as ms, \
                mock.patch.object(bridge, "loopback_port_open", return_value=True), \
                mock.patch.object(bridge, "listening_proxy_name", return_value="charles"):
            mp.system.return_value = "Darwin"
            ms.which.return_value = "/usr/sbin/lsof"
            result = bridge.active_codebuddy_proxy()
        self.assertTrue(result.get("stale"))
        self.assertEqual(result["listening_port"], 8080)

    def test_active_proxy_ignores_unrelated_service(self):
        with mock.patch.object(bridge, "platform") as mp, \
                mock.patch.object(bridge, "shutil") as ms, \
                mock.patch.object(bridge, "loopback_port_open", return_value=True), \
                mock.patch.object(bridge, "listening_proxy_name", return_value="node"):
            mp.system.return_value = "Darwin"
            ms.which.return_value = "/usr/sbin/lsof"
            result = bridge.active_codebuddy_proxy()
        self.assertEqual(result, {})


class ValidateProviderTest(unittest.TestCase):
    def _valid(self) -> dict:
        return {
            "schema_version": bridge.SCHEMA_VERSION,
            "id": "example",
            "display_name": "Example Provider",
            "cli": {"commands": ["example"], "auth_hints": ["auth"]},
            "cliproxy": {
                "provider": "example",
                "login_flag": "--login",
                "auth_file_prefixes": ["example"],
            },
            "models": [
                {
                    "key": "example-1",
                    "candidates": ["Example 1"],
                    "patterns": ["^example"],
                    "codebuddy": {"supportsToolCall": True, "maxInputTokens": 128000},
                }
            ],
        }

    def test_valid_provider(self):
        self.assertEqual(bridge.validate_provider(self._valid()), [])

    def test_bundled_providers_are_valid(self):
        for name in ("codex.json", "antigravity.json"):
            path = bridge.BUNDLED_PROVIDER_DIR / name
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertEqual(bridge.validate_provider(data, source=name), [], name)

    def test_bad_schema_version(self):
        payload = self._valid()
        payload["schema_version"] = 2
        self.assertTrue(bridge.validate_provider(payload))

    def test_bad_id(self):
        payload = self._valid()
        payload["id"] = "Example"
        self.assertTrue(any("id" in e for e in bridge.validate_provider(payload)))

    def test_missing_display_name(self):
        payload = self._valid()
        del payload["display_name"]
        self.assertTrue(bridge.validate_provider(payload))

    def test_bad_cli_commands(self):
        payload = self._valid()
        payload["cli"]["commands"] = []
        self.assertTrue(bridge.validate_provider(payload))
        payload = self._valid()
        payload["cli"]["commands"] = ["../evil"]
        self.assertTrue(bridge.validate_provider(payload))

    def test_auth_hint_traversal(self):
        payload = self._valid()
        payload["cli"]["auth_hints"] = ["../secret"]
        self.assertTrue(bridge.validate_provider(payload))
        payload = self._valid()
        payload["cli"]["auth_hints"] = ["/abs/secret"]
        self.assertTrue(bridge.validate_provider(payload))

    def test_cliproxy_missing(self):
        payload = self._valid()
        del payload["cliproxy"]
        self.assertTrue(bridge.validate_provider(payload))

    def test_login_flag_not_kebab(self):
        payload = self._valid()
        payload["cliproxy"]["login_flag"] = "login"
        self.assertTrue(bridge.validate_provider(payload))

    def test_models_empty(self):
        payload = self._valid()
        payload["models"] = []
        self.assertTrue(bridge.validate_provider(payload))

    def test_duplicate_model_key(self):
        payload = self._valid()
        payload["models"] = [dict(payload["models"][0]), dict(payload["models"][0])]
        self.assertTrue(any("duplicated" in e for e in bridge.validate_provider(payload)))

    def test_bad_model_key(self):
        payload = self._valid()
        payload["models"][0]["key"] = ""
        self.assertTrue(bridge.validate_provider(payload))

    def test_bad_candidates(self):
        payload = self._valid()
        payload["models"][0]["candidates"] = []
        self.assertTrue(bridge.validate_provider(payload))

    def test_bad_pattern(self):
        payload = self._valid()
        payload["models"][0]["patterns"] = ["(["]
        self.assertTrue(any("regex" in e for e in bridge.validate_provider(payload)))

    def test_codebuddy_unknown_key(self):
        payload = self._valid()
        payload["models"][0]["codebuddy"]["bogus"] = True
        self.assertTrue(bridge.validate_provider(payload))

    def test_codebuddy_bad_bool(self):
        payload = self._valid()
        payload["models"][0]["codebuddy"]["supportsToolCall"] = "yes"
        self.assertTrue(bridge.validate_provider(payload))

    def test_codebuddy_bad_limit(self):
        payload = self._valid()
        payload["models"][0]["codebuddy"]["maxInputTokens"] = -5
        self.assertTrue(bridge.validate_provider(payload))
        payload = self._valid()
        payload["models"][0]["codebuddy"]["maxInputTokens"] = 0
        self.assertTrue(bridge.validate_provider(payload))


class ChecksumTest(unittest.TestCase):
    SHA256 = "deadbeef" * 8  # 64 hex chars, valid SHA-256 length

    def test_two_column(self):
        self.assertEqual(bridge.checksum_for_asset(f"{self.SHA256}  cli.zip\n", "cli.zip"), self.SHA256)

    def test_lowercases(self):
        self.assertEqual(bridge.checksum_for_asset(f"{self.SHA256.upper()}  cli.zip\n", "cli.zip"), self.SHA256)

    def test_crlf(self):
        self.assertEqual(bridge.checksum_for_asset(f"{self.SHA256}  cli.zip\r\n", "cli.zip"), self.SHA256)

    def test_leading_star(self):
        self.assertEqual(bridge.checksum_for_asset(f"{self.SHA256}  *cli.zip\n", "cli.zip"), self.SHA256)

    def test_missing_asset(self):
        self.assertIsNone(bridge.checksum_for_asset(f"{self.SHA256}  other.zip\n", "cli.zip"))


class SafeExtractTest(unittest.TestCase):
    def _make_zip(self, names):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            for name in names:
                zf.writestr(name, b"payload")
        buf.seek(0)
        return zipfile.ZipFile(buf)

    def test_normal_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = self._make_zip(["cli-proxy-api.exe", "readme.txt"])
            bridge.safe_extract_zip(bundle, root)
            self.assertTrue((root / "cli-proxy-api.exe").is_file())
            self.assertTrue((root / "readme.txt").is_file())

    def test_traversal_raises(self):
        bundle = self._make_zip(["../evil.txt"])
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(bridge.BridgeError):
                bridge.safe_extract_zip(bundle, Path(tmp))

    def test_absolute_path_raises(self):
        bundle = self._make_zip(["/abs.txt"])
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(bridge.BridgeError):
                bridge.safe_extract_zip(bundle, Path(tmp))


class SyncOfflineE2ETest(unittest.TestCase):
    def _write_provider(self, providers_dir: Path) -> None:
        providers_dir.mkdir(parents=True, exist_ok=True)
        provider = {
            "schema_version": bridge.SCHEMA_VERSION,
            "id": "fixture",
            "display_name": "Fixture Provider",
            "cli": {"commands": ["fixture"], "auth_hints": []},
            "cliproxy": {"provider": "fixture", "auth_file_prefixes": ["fixture"]},
            "models": [
                {
                    "key": "fixture-model",
                    "candidates": ["fixture-model"],
                    "patterns": ["^fixture-"],
                    "codebuddy": {"supportsToolCall": True},
                }
            ],
        }
        (providers_dir / "fixture.json").write_text(json.dumps(provider), encoding="utf-8")

    def test_apply_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            home = tmp_path / "home"
            home.mkdir()
            self._write_provider(bridge.state_paths(home)["providers"])
            models_file = tmp_path / "models.json"
            models_file.write_text(json.dumps([{"id": "fixture-model", "owned_by": "fixture"}]), encoding="utf-8")
            codebuddy_file = tmp_path / "codebuddy_models.json"
            codebuddy_file.write_text("[]", encoding="utf-8")

            args = argparse.Namespace(
                home=str(home),
                codebuddy=str(codebuddy_file),
                models_file=str(models_file),
                apply=True,
                skip_probes=True,
                strict=False,
                force=False,
                providers="fixture",
                proxy_url="http://127.0.0.1:8317",
            )
            old_key = os.environ.get("CODEBUDDY_BRIDGE_API_KEY")
            os.environ["CODEBUDDY_BRIDGE_API_KEY"] = "test-key-" + "x" * 30
            try:
                rc = bridge.cmd_sync(args)
            finally:
                if old_key is None:
                    os.environ.pop("CODEBUDDY_BRIDGE_API_KEY", None)
                else:
                    os.environ["CODEBUDDY_BRIDGE_API_KEY"] = old_key
            self.assertEqual(rc, 0)
            written = json.loads(codebuddy_file.read_text(encoding="utf-8"))
            ids = {model["id"] for model in written}
            self.assertIn("fixture-model", ids)
            self.assertTrue(list(codebuddy_file.parent.glob("codebuddy_models.json.backup-*")))


if __name__ == "__main__":
    unittest.main(verbosity=2)

