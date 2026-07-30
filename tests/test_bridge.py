#!/usr/bin/env python3
"""Minimal regression tests for scripts/bridge.py.

Run from the repo root:

    python3 tests/test_bridge.py

Only the standard library is used so the suite runs anywhere Python 3.10+ is available.
"""

import sys
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
