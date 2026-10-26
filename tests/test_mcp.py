import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from agal.config import mcp_files_for_runtimes
from agal.mcp import (
    _agy_entry,
    _opencode_entry,
    _sh_wrap,
    install_mcp,
    sync_installed_mcp,
    uninstall_mcp,
    list_installed_mcp,
    LOCAL_MCP_FILE,
)
from agal.skills import load_local_state, save_local_state


class TestMCPProjectTargets(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.target_dir = Path(self.td.name) / "project"
        self.target_dir.mkdir()
        self.base_servers = {
            "test-github": {
                "name": "test-github",
                "source": "mcp-source",
                "config": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                },
            }
        }

    def tearDown(self):
        self.td.cleanup()

    def _set_runtimes(self, *names):
        save_local_state(self.target_dir, {"runtimes": list(names)})

    def _read(self, rel):
        with open(self.target_dir / rel, "r", encoding="utf-8") as f:
            return json.load(f)

    def _install(self, name="test-github", servers=None):
        with patch(
            "agal.mcp.get_all_mcp_servers",
            return_value=servers or self.base_servers,
        ):
            return install_mcp(name, target_dir=self.target_dir, scope="local")

    def test_opencode_only_writes_only_opencode_json(self):
        self._set_runtimes("opencode")
        self._install()

        self.assertFalse((self.target_dir / LOCAL_MCP_FILE).exists())
        data = self._read("opencode.json")
        self.assertEqual(data["$schema"], "https://opencode.ai/config.json")
        self.assertEqual(data["mcp"]["test-github"], {
            "type": "local",
            "command": ["npx", "-y", "@modelcontextprotocol/server-github"],
        })

    def test_three_runtimes_write_three_shapes(self):
        self._set_runtimes("claude", "opencode", "agy")
        self._install()

        claude = self._read(".mcp.json")
        opencode = self._read("opencode.json")
        agy = self._read(".agents/mcp_config.json")

        self.assertEqual(
            claude["mcpServers"]["test-github"]["args"],
            ["-y", "@modelcontextprotocol/server-github"],
        )
        self.assertEqual(
            opencode["mcp"]["test-github"]["command"],
            ["npx", "-y", "@modelcontextprotocol/server-github"],
        )
        self.assertEqual(agy["mcpServers"]["test-github"], {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {},
        })

    def test_existing_opencode_config_is_kept(self):
        self._set_runtimes("opencode")
        original = {
            "theme": "dark",
            "mcp": {"servers": {"own": {"type": "remote", "url": "https://own"}}},
        }
        (self.target_dir / "opencode.json").write_text(
            json.dumps(original), encoding="utf-8"
        )

        self._install()
        data = self._read("opencode.json")
        self.assertEqual(data["theme"], "dark")
        self.assertIn("own", data["mcp"]["servers"])
        self.assertIn("test-github", data["mcp"])

        self.assertTrue(uninstall_mcp("test-github", target_dir=self.target_dir))
        data = self._read("opencode.json")
        self.assertEqual(data["theme"], "dark")
        self.assertIn("own", data["mcp"]["servers"])
        self.assertNotIn("test-github", data["mcp"])

    def test_agal_created_file_is_deleted_after_last_server(self):
        self._set_runtimes("opencode")
        self._install()
        self.assertTrue((self.target_dir / "opencode.json").is_file())
        self.assertTrue(uninstall_mcp("test-github", target_dir=self.target_dir))
        self.assertFalse((self.target_dir / "opencode.json").exists())

    def test_existing_opencode_jsonc_is_untouched(self):
        self._set_runtimes("opencode")
        jsonc = self.target_dir / "opencode.jsonc"
        content = '{\n  // keep me\n  "theme": "dark"\n}\n'
        jsonc.write_text(content, encoding="utf-8")

        self._install()

        self.assertEqual(jsonc.read_text(encoding="utf-8"), content)
        self.assertTrue((self.target_dir / "opencode.json").is_file())

    def test_invalid_json_is_left_alone_but_state_records_server(self):
        self._set_runtimes("opencode", "agy")
        opencode = self.target_dir / "opencode.json"
        opencode.write_text('{not json', encoding="utf-8")
        agy = self.target_dir / ".agents" / "mcp_config.json"
        agy.parent.mkdir()
        agy.write_text("[]", encoding="utf-8")

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self._install()

        self.assertEqual(opencode.read_text(encoding="utf-8"), "{not json")
        self.assertEqual(agy.read_text(encoding="utf-8"), "[]")
        self.assertEqual(out.getvalue().count("cannot read"), 2)
        self.assertIn("test-github", load_local_state(self.target_dir)["mcp"])

    def test_runtime_switch_removes_old_targets_and_writes_claude(self):
        self._set_runtimes("opencode", "agy")
        self._install()
        state = load_local_state(self.target_dir)
        state["runtimes"] = ["claude"]
        save_local_state(self.target_dir, state)

        sync_installed_mcp(self.target_dir)

        self.assertFalse((self.target_dir / "opencode.json").exists())
        self.assertFalse((self.target_dir / ".agents" / "mcp_config.json").exists())
        self.assertIn("test-github", self._read(".mcp.json")["mcpServers"])

    def test_agy_skips_remote_server_with_header_reference(self):
        self._set_runtimes("claude", "agy")
        servers = {
            "itsaplan": {
                "name": "itsaplan",
                "source": "mcp-source",
                "config": {
                    "type": "http",
                    "url": "https://itsaplan.example.com/mcp",
                    "headers": {"Authorization": "Bearer ${ITSAPLAN_TOKEN}"},
                },
            }
        }
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self._install("itsaplan", servers)

        self.assertIn("does not expand", out.getvalue())
        agy_path = self.target_dir / ".agents" / "mcp_config.json"
        if agy_path.is_file():
            self.assertNotIn("itsaplan", self._read(".agents/mcp_config.json")["mcpServers"])
        self.assertIn("itsaplan", self._read(".mcp.json")["mcpServers"])
        self.assertIn("itsaplan", load_local_state(self.target_dir)["mcp"])

    def test_global_install_touches_only_claude_config(self):
        global_file = Path(self.td.name) / "claude.json"
        with (
            patch("agal.mcp.get_all_mcp_servers", return_value=self.base_servers),
            patch("agal.mcp.CLAUDE_GLOBAL_CONFIG", global_file),
            patch("agal.mcp.load_global_state", return_value={}),
            patch("agal.mcp.save_global_state"),
        ):
            install_mcp("test-github", scope="global")

        self.assertTrue(global_file.is_file())
        self.assertEqual(
            json.loads(global_file.read_text(encoding="utf-8"))["mcpServers"]["test-github"],
            self.base_servers["test-github"]["config"],
        )
        self.assertFalse((self.target_dir / "opencode.json").exists())
        self.assertFalse((self.target_dir / ".agents").exists())


class TestShWrap(unittest.TestCase):
    def _run(self, command, args, env, base_env):
        shell, sh_args, literal_env = _sh_wrap(command, args, env)
        result = subprocess.run(
            [shell, *sh_args],
            env={**base_env, **literal_env},
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def _base_env(self):
        env = dict(os.environ)
        env.pop("AGAL_TEST_UNSET", None)
        env["AGAL_TEST_SET"] = "set-value"
        env["HOME"] = "/home/probe"
        return env

    def test_expands_home_default_and_set_value(self):
        out = self._run(
            "printf",
            ["%s\n", "${HOME}", "${AGAL_TEST_UNSET:-dflt}", "${AGAL_TEST_SET:-dflt}"],
            {},
            self._base_env(),
        )
        self.assertEqual(out.splitlines(), ["/home/probe", "dflt", "set-value"])

    def test_literal_dollar_quote_backslash_and_backtick_survive(self):
        literal = ["$", '"', "\\", "`", "$HOME", "a$b", "$(echo pwned)"]
        out = self._run("printf", ["%s\n", *literal], {}, self._base_env())
        self.assertEqual(out.splitlines(), literal)

    def test_default_with_spaces_and_quotes(self):
        out = self._run(
            "printf",
            ["%s\n", '${AGAL_TEST_UNSET:-hello "world"}'],
            {},
            self._base_env(),
        )
        self.assertEqual(out, 'hello "world"\n')

    def test_env_reference_reaches_server_and_literal_env_is_returned(self):
        shell, sh_args, literal_env = _sh_wrap(
            "printenv", ["P"], {"P": "${HOME}", "L": "literal"}
        )
        self.assertEqual(literal_env, {"L": "literal"})
        result = subprocess.run(
            [shell, *sh_args],
            env={**self._base_env(), **literal_env},
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.stdout.strip(), "/home/probe")


class TestOpenCodeEntry(unittest.TestCase):
    def test_stdio_without_references(self):
        entry, warnings = _opencode_entry(
            {"command": "npx", "args": ["-y", "pkg"], "env": {"DEBUG": "1"}}
        )
        self.assertEqual(entry, {
            "type": "local",
            "command": ["npx", "-y", "pkg"],
            "environment": {"DEBUG": "1"},
        })
        self.assertEqual(warnings, [])

    def test_stdio_with_references_is_wrapped(self):
        entry, warnings = _opencode_entry({
            "command": "npx",
            "args": ["-y", "pkg", "--url", "${API_URL:-http://localhost}"],
            "env": {"P": "${HOME}"},
        })
        self.assertEqual(entry["type"], "local")
        self.assertEqual(entry["command"][:2], ["sh", "-c"])
        self.assertIn(
            'exec "npx" "-y" "pkg" "--url" "${API_URL:-http://localhost}"',
            entry["command"][2],
        )
        self.assertNotIn("environment", entry)
        self.assertEqual(warnings, [])

    def test_http_without_references(self):
        entry, warnings = _opencode_entry({
            "type": "http",
            "url": "https://mcp.example.com/",
            "headers": {"Authorization": "Bearer abc"},
        })
        self.assertEqual(entry, {
            "type": "remote",
            "url": "https://mcp.example.com/",
            "headers": {"Authorization": "Bearer abc"},
        })
        self.assertEqual(warnings, [])

    def test_http_header_reference_is_converted(self):
        entry, warnings = _opencode_entry({
            "type": "http",
            "url": "https://itsaplan.example.com/mcp",
            "headers": {"Authorization": "Bearer ${ITSAPLAN_TOKEN}"},
        })
        self.assertEqual(entry["headers"], {"Authorization": "Bearer {env:ITSAPLAN_TOKEN}"})
        self.assertEqual(warnings, [])

    def test_http_default_reference_drops_default_with_warning(self):
        entry, warnings = _opencode_entry({
            "type": "http",
            "url": "https://example.com/mcp/${TENANT:-public}",
        })
        self.assertEqual(entry["url"], "https://example.com/mcp/{env:TENANT}")
        self.assertTrue(any("default" in warning for warning in warnings))

    def test_sse_and_unknown_key(self):
        entry, warnings = _opencode_entry({
            "type": "sse",
            "url": "https://example.com/sse",
            "timeout": 30,
        })
        self.assertEqual(entry["type"], "remote")
        self.assertTrue(any("timeout" in warning for warning in warnings))

    def test_zoho_imap_shape(self):
        entry, warnings = _opencode_entry({
            "command": "npx",
            "args": ["-y", "zoho-imap-mcp"],
            "env": {"EMAIL": "${ZOHO_EMAIL:-me@example.com}"},
        })
        self.assertEqual(entry["command"][:2], ["sh", "-c"])
        self.assertIn('EMAIL="${ZOHO_EMAIL:-me@example.com}"', entry["command"][2])
        self.assertEqual(warnings, [])

    def test_apify_shape(self):
        entry, warnings = _opencode_entry({
            "type": "http",
            "url": "https://mcp.apify.com/",
            "headers": {"Authorization": "Bearer apify-token"},
        })
        self.assertEqual(entry, {
            "type": "remote",
            "url": "https://mcp.apify.com/",
            "headers": {"Authorization": "Bearer apify-token"},
        })
        self.assertEqual(warnings, [])


class TestAgyEntry(unittest.TestCase):
    def test_stdio_without_references_keeps_cwd(self):
        entry, warnings = _agy_entry({
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "pkg"],
            "env": {"DEBUG": "1"},
            "cwd": "/tmp/work",
        })
        self.assertEqual(entry, {
            "command": "npx",
            "args": ["-y", "pkg"],
            "env": {"DEBUG": "1"},
            "cwd": "/tmp/work",
        })
        self.assertEqual(warnings, [])

    def test_stdio_with_references_is_wrapped(self):
        entry, warnings = _agy_entry({
            "command": "npx",
            "args": ["-y", "zoho-imap-mcp"],
            "env": {"EMAIL": "${ZOHO_EMAIL:-me@example.com}"},
        })
        self.assertEqual(entry["command"], "sh")
        self.assertEqual(entry["args"][0], "-c")
        self.assertIn('EMAIL="${ZOHO_EMAIL:-me@example.com}"', entry["args"][1])
        self.assertIn('exec "npx" "-y" "zoho-imap-mcp"', entry["args"][1])
        self.assertEqual(entry["env"], {})
        self.assertEqual(warnings, [])

    def test_http_without_references(self):
        entry, warnings = _agy_entry({
            "type": "http",
            "url": "https://mcp.apify.com/",
            "headers": {"Authorization": "Bearer apify-token"},
        })
        self.assertEqual(entry, {
            "serverUrl": "https://mcp.apify.com/",
            "headers": {"Authorization": "Bearer apify-token"},
        })
        self.assertEqual(warnings, [])

    def test_http_header_reference_is_skipped(self):
        entry, warnings = _agy_entry({
            "type": "http",
            "url": "https://itsaplan.example.com/mcp",
            "headers": {"Authorization": "Bearer ${ITSAPLAN_TOKEN}"},
        })
        self.assertIsNone(entry)
        self.assertTrue(any("does not expand" in warning for warning in warnings))

    def test_http_default_reference_is_skipped(self):
        entry, warnings = _agy_entry({
            "type": "http",
            "url": "https://example.com/mcp/${TENANT:-public}",
        })
        self.assertIsNone(entry)
        self.assertTrue(any("does not expand" in warning for warning in warnings))

    def test_sse_warns(self):
        entry, warnings = _agy_entry({
            "type": "sse",
            "url": "https://example.com/sse",
        })
        self.assertEqual(entry, {"serverUrl": "https://example.com/sse"})
        self.assertTrue(any("Streamable HTTP" in warning for warning in warnings))

    def test_unknown_key_is_dropped(self):
        entry, warnings = _agy_entry({
            "command": "npx",
            "args": ["-y", "pkg"],
            "timeout": 30,
        })
        self.assertNotIn("timeout", entry)
        self.assertTrue(any("timeout" in warning for warning in warnings))


class TestMCPFiles(unittest.TestCase):
    def test_files_for_runtimes(self):
        self.assertEqual(mcp_files_for_runtimes(None), [".mcp.json"])
        self.assertEqual(mcp_files_for_runtimes(["opencode"]), ["opencode.json"])
        self.assertEqual(mcp_files_for_runtimes(["agy"]), [".agents/mcp_config.json"])
        self.assertEqual(
            mcp_files_for_runtimes(["claude", "opencode", "agy"]),
            [".mcp.json", "opencode.json", ".agents/mcp_config.json"],
        )


class TestMCP(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.target_dir = Path(self.td.name) / "project"
        self.target_dir.mkdir()

        self.mock_servers = {
            "test-postgres": {
                "name": "test-postgres",
                "source": "mcp-source",
                "config": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-postgres", "db_url"],
                    "env": {},
                },
                "description": "Postgres MCP server",
            },
            "test-github": {
                "name": "test-github",
                "source": "mcp-source",
                "config": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                },
            }
        }

    def tearDown(self):
        self.td.cleanup()

    @patch("agal.mcp.get_all_mcp_servers")
    def test_install_and_merge_mcp_local(self, mock_get_servers):
        mock_get_servers.return_value = self.mock_servers

        # Install first server
        install_mcp("test-postgres", target_dir=self.target_dir, scope="local")
        mcp_path = self.target_dir / LOCAL_MCP_FILE
        self.assertTrue(mcp_path.is_file())

        with open(mcp_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("test-postgres", data["mcpServers"])
        self.assertEqual(data["mcpServers"]["test-postgres"]["command"], "npx")

        # Install second server without clobbering first
        install_mcp("test-github", target_dir=self.target_dir, scope="local")
        with open(mcp_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("test-postgres", data["mcpServers"])
        self.assertIn("test-github", data["mcpServers"])

    @patch("agal.mcp.get_all_mcp_servers")
    def test_uninstall_mcp_local(self, mock_get_servers):
        mock_get_servers.return_value = self.mock_servers

        install_mcp("test-postgres", target_dir=self.target_dir, scope="local")
        install_mcp("test-github", target_dir=self.target_dir, scope="local")

        uninstall_mcp("test-postgres", target_dir=self.target_dir, scope="local")

        mcp_path = self.target_dir / LOCAL_MCP_FILE
        with open(mcp_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertNotIn("test-postgres", data["mcpServers"])
        self.assertIn("test-github", data["mcpServers"])

        installed = list_installed_mcp(self.target_dir, scope="local")
        self.assertNotIn("test-postgres", installed)
        self.assertIn("test-github", installed)

    @patch("agal.mcp.get_all_mcp_servers")
    def test_install_http_mcp_local(self, mock_get_servers):
        mock_get_servers.return_value = {
            "itsaplan": {
                "name": "itsaplan",
                "source": "mcp-source",
                "config": {
                    "type": "http",
                    "url": "https://example.com/mcp",
                    "headers": {"Authorization": "Bearer ${ITSAPLAN_TOKEN}"},
                    "description": "itsaplan",
                },
            }
        }

        install_mcp("itsaplan", target_dir=self.target_dir, scope="local")

        with open(self.target_dir / LOCAL_MCP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["mcpServers"]["itsaplan"], {
            "type": "http",
            "url": "https://example.com/mcp",
            "headers": {"Authorization": "Bearer ${ITSAPLAN_TOKEN}"},
        })

    @patch("agal.mcp.get_all_mcp_servers")
    def test_install_and_uninstall_mcp_alias(self, mock_get_servers):
        mock_get_servers.return_value = {
            "playwright-mcp": {
                "name": "playwright-mcp",
                "source": "playwright-mcp",
                "raw_name": "io.github.microsoft/playwright-mcp",
                "package": "@playwright/mcp",
                "config": {
                    "command": "npx",
                    "args": ["-y", "@playwright/mcp"],
                    "raw_name": "io.github.microsoft/playwright-mcp",
                    "package": "@playwright/mcp",
                },
                "description": "Playwright Tools for MCP",
            }
        }

        # Install using alias 'playwright' (suffix -mcp stripped)
        install_mcp("playwright", target_dir=self.target_dir, scope="local")
        mcp_path = self.target_dir / LOCAL_MCP_FILE
        with open(mcp_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("playwright-mcp", data["mcpServers"])
        self.assertNotIn("raw_name", data["mcpServers"]["playwright-mcp"])
        self.assertNotIn("package", data["mcpServers"]["playwright-mcp"])

        # Uninstall using alias 'playwright'
        self.assertTrue(uninstall_mcp("playwright", target_dir=self.target_dir, scope="local"))
        self.assertFalse(mcp_path.exists())


if __name__ == "__main__":
    unittest.main()
