import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agal.hooks import install_hook, sync_installed_hooks, uninstall_hook
from agal.skills import load_local_state, save_local_state


class TestHooks(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.project = Path(self.td.name) / "project"
        self.project.mkdir()
        self.home_dir = Path(self.td.name) / "home"
        self.home_dir.mkdir()

        self.src = Path(self.td.name) / "fixtures" / "ponytail"
        self.src.mkdir(parents=True)
        plugin_dir = self.src / ".claude-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "marketplace.json").write_text(
            json.dumps({
                "name": "mp",
                "plugins": [{"name": "plug", "source": "./"}],
            }),
            encoding="utf-8",
        )
        (self.src / "hooks").mkdir()

        plugins = self.src / ".opencode" / "plugins"
        plugins.mkdir(parents=True)
        self.opencode_entry = plugins / "index.js"
        self.opencode_entry.write_text("export default {}\n", encoding="utf-8")

        agy_dir = self.src / ".antigravity-plugin"
        agy_dir.mkdir()
        self.agy_hooks = agy_dir / "hooks.json"
        self.agy_hooks.write_text(
            json.dumps({"lint": {"PreToolUse": []}}), encoding="utf-8"
        )

        self.bundles = {
            "ponytail": {
                "name": "ponytail",
                "path": str(self.src),
                "source": "ponytail",
                "adapters": {
                    "claude": {"marketplace": "mp", "plugin": "plug"},
                    "opencode": str(self.opencode_entry.resolve()),
                    "agy": str(self.agy_hooks.resolve()),
                },
            },
            "other": {
                "name": "other",
                "path": str(self.src),
                "source": "ponytail",
                "adapters": {
                    "claude": {"marketplace": "mp", "plugin": "other-plugin"},
                },
            },
        }

    def tearDown(self):
        self.td.cleanup()

    def _set_runtimes(self, *names):
        save_local_state(self.project, {"runtimes": list(names)})

    def _install(self, name="ponytail", scope="local"):
        output = io.StringIO()
        with patch("agal.hooks.get_all_hooks", return_value=self.bundles), \
             contextlib.redirect_stdout(output):
            result = install_hook(name, target_dir=self.project, scope=scope)
        return result, output.getvalue()

    def _settings(self):
        path = self.project / ".claude" / "settings.local.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_claude_install_writes_both_keys_and_keeps_others(self):
        self._set_runtimes("claude")
        settings_path = self.project / ".claude" / "settings.local.json"
        settings_path.parent.mkdir()
        settings_path.write_text(
            json.dumps({"permissions": {"allow": ["Bash"]}}), encoding="utf-8"
        )

        result, _ = self._install()

        data = self._settings()
        self.assertEqual(data["permissions"], {"allow": ["Bash"]})
        self.assertEqual(data["extraKnownMarketplaces"]["mp"], {
            "source": {"source": "directory", "path": str(self.src.resolve())}
        })
        self.assertEqual(data["enabledPlugins"], {"plug@mp": True})
        self.assertEqual(result["adapters"]["claude"], {
            "marketplace": "mp",
            "plugin": "plug",
        })
        state = load_local_state(self.project)
        self.assertEqual(state["hooks"]["ponytail"]["adapters"]["claude"], {
            "marketplace": "mp",
            "plugin": "plug",
        })

    def test_removing_one_bundle_keeps_shared_marketplace(self):
        self._set_runtimes("claude")
        self._install("ponytail")
        self._install("other")

        with patch("agal.hooks.get_all_hooks", return_value=self.bundles):
            self.assertTrue(uninstall_hook("ponytail", target_dir=self.project))

        data = self._settings()
        self.assertIn("mp", data["extraKnownMarketplaces"])
        self.assertEqual(data["enabledPlugins"], {"other-plugin@mp": True})

    def test_removing_last_bundle_deletes_agal_created_settings(self):
        self._set_runtimes("claude")
        self._install()
        settings_path = self.project / ".claude" / "settings.local.json"
        self.assertTrue(settings_path.is_file())

        self.assertTrue(uninstall_hook("ponytail", target_dir=self.project))

        self.assertFalse(settings_path.exists())
        self.assertNotIn("ponytail", load_local_state(self.project)["hooks"])

    def test_legacy_entry_uninstalls_by_unlinking(self):
        legacy_path = self.project / ".claude" / "hooks" / "x.sh"
        legacy_path.parent.mkdir(parents=True)
        legacy_path.write_text("#!/bin/sh\n", encoding="utf-8")
        save_local_state(self.project, {
            "runtimes": ["claude"],
            "hooks": {"x.sh": {"source": "old", "path": ".claude/hooks/x.sh"}},
        })

        self.assertTrue(uninstall_hook("x.sh", target_dir=self.project))
        self.assertFalse(legacy_path.exists())
        self.assertNotIn("x.sh", load_local_state(self.project).get("hooks", {}))

    def test_global_install_is_rejected_without_touching_home(self):
        with patch("pathlib.Path.home", return_value=self.home_dir):
            with self.assertRaises(ValueError) as caught:
                self._install(scope="global")

        self.assertIn("per project", str(caught.exception))
        self.assertEqual(list(self.home_dir.iterdir()), [])

    def test_opencode_stub_uses_absolute_entry_path(self):
        self._set_runtimes("opencode")
        result, _ = self._install()

        stub = self.project / ".opencode" / "plugins" / "agal-ponytail.js"
        text = stub.read_text(encoding="utf-8")
        entry = str(self.opencode_entry.resolve())
        self.assertEqual(
            text.splitlines()[0],
            "// Generated by agal from source ponytail. Do not edit.",
        )
        self.assertIn(f'export * from "{entry}"', text)
        self.assertIn(f'export {{ default }} from "{entry}"', text)
        self.assertEqual(result["adapters"]["opencode"], ".opencode/plugins/agal-ponytail.js")

    def test_opencode_does_not_clobber_foreign_stub(self):
        self._set_runtimes("opencode")
        stub = self.project / ".opencode" / "plugins" / "agal-ponytail.js"
        stub.parent.mkdir(parents=True)
        stub.write_text("// mine\n", encoding="utf-8")

        result, output = self._install()

        self.assertEqual(stub.read_text(encoding="utf-8"), "// mine\n")
        self.assertEqual(result["adapters"], {})
        self.assertIn("not written by agal", output)
        self.assertNotIn("ponytail", load_local_state(self.project).get("hooks", {}))

    def test_opencode_uninstall_prunes_empty_plugin_dir(self):
        self._set_runtimes("opencode")
        self._install()

        self.assertTrue(uninstall_hook("ponytail", target_dir=self.project))

        self.assertFalse((self.project / ".opencode" / "plugins").exists())
        self.assertFalse((self.project / ".opencode").exists())

    def test_agy_merges_next_to_user_hook(self):
        self._set_runtimes("agy")
        hooks_path = self.project / ".agents" / "hooks.json"
        hooks_path.parent.mkdir()
        hooks_path.write_text(
            json.dumps({"user-hook": {"enabled": True}}), encoding="utf-8"
        )

        self._install()

        data = json.loads(hooks_path.read_text(encoding="utf-8"))
        self.assertEqual(data["user-hook"], {"enabled": True})
        self.assertEqual(data["agal-ponytail-lint"], {"PreToolUse": []})
        state = load_local_state(self.project)
        self.assertEqual(state["hooks"]["ponytail"]["adapters"]["agy"], ["agal-ponytail-lint"])

    def test_agy_uninstall_removes_only_agal_keys(self):
        self._set_runtimes("agy")
        hooks_path = self.project / ".agents" / "hooks.json"
        hooks_path.parent.mkdir()
        hooks_path.write_text(
            json.dumps({"user-hook": {"enabled": True}}), encoding="utf-8"
        )
        self._install()

        self.assertTrue(uninstall_hook("ponytail", target_dir=self.project))

        data = json.loads(hooks_path.read_text(encoding="utf-8"))
        self.assertEqual(data, {"user-hook": {"enabled": True}})

    def test_agy_empty_file_is_deleted(self):
        self._set_runtimes("agy")
        hooks_path = self.project / ".agents" / "hooks.json"
        self._install()
        self.assertTrue(hooks_path.is_file())

        self.assertTrue(uninstall_hook("ponytail", target_dir=self.project))

        self.assertFalse(hooks_path.exists())

    def test_agy_does_not_clobber_unrecorded_key(self):
        self._set_runtimes("agy")
        hooks_path = self.project / ".agents" / "hooks.json"
        hooks_path.parent.mkdir()
        hooks_path.write_text(
            json.dumps({"agal-ponytail-lint": {"enabled": False}}), encoding="utf-8"
        )

        result, output = self._install()

        data = json.loads(hooks_path.read_text(encoding="utf-8"))
        self.assertEqual(data["agal-ponytail-lint"], {"enabled": False})
        self.assertIn("not written by agal", output)
        self.assertEqual(result["adapters"]["agy"], [])

    def test_sync_follows_runtime_switch(self):
        self._set_runtimes("claude", "opencode")
        self._install()
        stub = self.project / ".opencode" / "plugins" / "agal-ponytail.js"
        self.assertTrue(stub.is_file())

        state = load_local_state(self.project)
        state["runtimes"] = ["claude"]
        save_local_state(self.project, state)
        with patch("agal.hooks.get_all_hooks", return_value=self.bundles), \
             contextlib.redirect_stdout(io.StringIO()):
            sync_installed_hooks(self.project, {})
        self.assertFalse(stub.exists())
        self.assertIn("plug@mp", self._settings()["enabledPlugins"])

        state = load_local_state(self.project)
        state["runtimes"] = ["opencode"]
        save_local_state(self.project, state)
        with patch("agal.hooks.get_all_hooks", return_value=self.bundles), \
             contextlib.redirect_stdout(io.StringIO()):
            sync_installed_hooks(self.project, {})
        self.assertTrue(stub.is_file())


if __name__ == "__main__":
    unittest.main()
