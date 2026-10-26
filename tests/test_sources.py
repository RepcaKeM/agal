import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agal.sources import (
    derive_source_name,
    parse_skill_frontmatter,
    parse_mcp_manifest,
    index_source_dir,
    load_sources_registry,
    save_sources_registry,
)


class TestSources(unittest.TestCase):
    def test_derive_source_name(self):
        self.assertEqual(derive_source_name("https://github.com/obra/superpowers.git"), "superpowers")
        self.assertEqual(derive_source_name("git@github.com:foo/my-repo"), "my-repo")
        self.assertEqual(derive_source_name("https://github.com/org/repo/"), "repo")

    def test_parse_skill_frontmatter(self):
        with tempfile.TemporaryDirectory() as td:
            skill_dir = Path(td) / "my-skill"
            skill_dir.mkdir()
            skill_md = skill_dir / "SKILL.md"
            skill_md.write_text(
                "---\nname: custom-name\ndescription: Test skill description.\n---\n# Body\n",
                encoding="utf-8",
            )
            meta = parse_skill_frontmatter(skill_md)
            self.assertEqual(meta["name"], "custom-name")
            self.assertEqual(meta["description"], "Test skill description.")

    def test_parse_mcp_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            mcp_json = Path(td) / "mcp.json"
            mcp_json.write_text(
                json.dumps({
                    "mcpServers": {
                        "test-server": {
                            "command": "npx",
                            "args": ["-y", "@modelcontextprotocol/test"],
                            "env": {"DEBUG": "1"},
                            "description": "Test MCP server",
                        }
                    }
                }),
                encoding="utf-8",
            )
            servers = parse_mcp_manifest(mcp_json)
            self.assertIn("test-server", servers)
            self.assertEqual(servers["test-server"]["command"], "npx")
            self.assertEqual(servers["test-server"]["env"], {"DEBUG": "1"})

    def test_parse_mcp_manifest_http_server(self):
        with tempfile.TemporaryDirectory() as td:
            mcp_json = Path(td) / "mcp.json"
            mcp_json.write_text(
                json.dumps({
                    "mcpServers": {
                        "remote": {
                            "type": "http",
                            "url": "https://example.com/mcp",
                            "headers": {"Authorization": "Bearer ${TOKEN}"},
                            "description": "Remote MCP server",
                        }
                    }
                }),
                encoding="utf-8",
            )
            servers = parse_mcp_manifest(mcp_json)
            self.assertEqual(servers["remote"], {
                "type": "http",
                "url": "https://example.com/mcp",
                "headers": {"Authorization": "Bearer ${TOKEN}"},
                "description": "Remote MCP server",
            })

    def test_parse_mcp_manifest_http_server_map_yaml(self):
        with tempfile.TemporaryDirectory() as td:
            manifest = Path(td) / "agal-mcp.yaml"
            manifest.write_text(
                "itsaplan:\n"
                "  url: https://example.com/mcp\n"
                "  headers:\n"
                "    Authorization: Bearer ${ITSAPLAN_TOKEN}\n",
                encoding="utf-8",
            )
            servers = parse_mcp_manifest(manifest)
            self.assertEqual(servers["itsaplan"]["type"], "http")
            self.assertEqual(servers["itsaplan"]["url"], "https://example.com/mcp")
            self.assertEqual(
                servers["itsaplan"]["headers"],
                {"Authorization": "Bearer ${ITSAPLAN_TOKEN}"},
            )
            self.assertNotIn("command", servers["itsaplan"])

    def test_parse_mcp_manifest_registry_packages_with_args(self):
        with tempfile.TemporaryDirectory() as td:
            server_json = Path(td) / "server.json"
            server_json.write_text(
                json.dumps({
                    "$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
                    "name": "io.github.morluto/rea",
                    "packages": [
                        {
                            "registryType": "npm",
                            "identifier": "rea-agents",
                            "packageArguments": [
                                {
                                    "type": "positional",
                                    "value": "mcp",
                                }
                            ],
                        }
                    ],
                }),
                encoding="utf-8",
            )
            servers = parse_mcp_manifest(server_json)
            self.assertIn("rea", servers)
            self.assertEqual(servers["rea"]["command"], "npx")
            self.assertEqual(servers["rea"]["args"], ["-y", "rea-agents", "mcp"])


    def test_index_source_dir(self):
        with tempfile.TemporaryDirectory() as td:
            source_dir = Path(td) / "source"
            source_dir.mkdir()

            # Create a skill with a script and a reference
            skill_dir = source_dir / "skills" / "debugging"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: debugging\ndescription: Debugging skill\n---\n",
                encoding="utf-8",
            )
            (skill_dir / "helper.sh").write_text("#!/bin/bash\necho hi", encoding="utf-8")
            ref_dir = skill_dir / "references"
            ref_dir.mkdir()
            (ref_dir / "guide.md").write_text("Guide", encoding="utf-8")

            # Create an MCP manifest
            mcp_file = source_dir / "mcp.json"
            mcp_file.write_text(
                json.dumps({
                    "mcpServers": {
                        "db": {
                            "command": "python",
                            "args": ["-m", "mcp_db"],
                        }
                    }
                }),
                encoding="utf-8",
            )

            # Create a hook
            hooks_dir = source_dir / "hooks"
            hooks_dir.mkdir()
            (hooks_dir / "pre-tool.sh").write_text("#!/bin/bash\nexit 0", encoding="utf-8")

            indexed = index_source_dir(source_dir)
            self.assertIn("debugging", indexed["skills"])
            self.assertTrue(indexed["skills"]["debugging"]["has_scripts"])
            self.assertTrue(indexed["skills"]["debugging"]["has_references"])

            self.assertIn("db", indexed["mcp_servers"])
            self.assertEqual(indexed["mcp_servers"]["db"]["config"]["command"], "python")

            # A bare hooks/ directory is not an adapter any runtime can load.
            self.assertEqual(indexed["hooks"], [])

    def _write_marketplace(self, src, name="mp", plugin="plug"):
        plugin_dir = src / ".claude-plugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "marketplace.json").write_text(
            json.dumps({
                "name": name,
                "plugins": [{"name": plugin, "source": "./"}],
            }),
            encoding="utf-8",
        )

    def test_index_hook_bundle_with_all_adapters(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "fixture"
            src.mkdir()
            self._write_marketplace(src)
            (src / "hooks").mkdir()
            (src / "hooks" / "hook.sh").write_text("#!/bin/sh\n", encoding="utf-8")
            plugins = src / ".opencode" / "plugins"
            plugins.mkdir(parents=True)
            entry = plugins / "index.js"
            entry.write_text("export default {}\n", encoding="utf-8")
            agy_dir = src / ".antigravity-plugin"
            agy_dir.mkdir()
            (agy_dir / "hooks.json").write_text(
                json.dumps({"lint": {"enabled": True}}), encoding="utf-8"
            )

            hooks = index_source_dir(src)["hooks"]
            self.assertEqual(len(hooks), 1)
            self.assertEqual(hooks[0]["name"], "fixture")
            self.assertEqual(hooks[0]["path"], str(src.resolve()))
            self.assertEqual(hooks[0]["adapters"], {
                "claude": {"marketplace": "mp", "plugin": "plug"},
                "opencode": str(entry.resolve()),
                "agy": str((agy_dir / "hooks.json").resolve()),
            })

    def test_index_claude_only_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "claude-only"
            src.mkdir()
            self._write_marketplace(src)
            (src / "hooks").mkdir()

            hooks = index_source_dir(src)["hooks"]
            self.assertEqual(len(hooks), 1)
            self.assertEqual(hooks[0]["adapters"], {
                "claude": {"marketplace": "mp", "plugin": "plug"},
            })

    def test_pure_skill_plugin_is_not_a_hook_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "pure-skills"
            src.mkdir()
            self._write_marketplace(src)
            plugin_dir = src / ".claude-plugin"
            (plugin_dir / "plugin.json").write_text(
                json.dumps({"name": "plug"}), encoding="utf-8"
            )
            self._write_skill(src / "skills" / "one", "one")

            indexed = index_source_dir(src)
            self.assertIn("one", indexed["skills"])
            self.assertEqual(indexed["hooks"], [])

    def test_claude_hooks_json_is_not_an_agy_adapter(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "claude-hooks"
            src.mkdir()
            self._write_marketplace(src)
            hooks_dir = src / "hooks"
            hooks_dir.mkdir()
            (hooks_dir / "hooks.json").write_text(
                json.dumps({"hooks": {"SessionStart": []}}), encoding="utf-8"
            )

            hooks = index_source_dir(src)["hooks"]
            self.assertEqual(len(hooks), 1)
            self.assertIn("claude", hooks[0]["adapters"])
            self.assertNotIn("agy", hooks[0]["adapters"])

    def test_mjs_only_opencode_dir_is_not_an_adapter(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "mjs-only"
            src.mkdir()
            self._write_marketplace(src)
            (src / "hooks").mkdir()
            plugins = src / ".opencode" / "plugins"
            plugins.mkdir(parents=True)
            (plugins / "hook.mjs").write_text("export default {}\n", encoding="utf-8")

            hooks = index_source_dir(src)["hooks"]
            self.assertEqual(len(hooks), 1)
            self.assertNotIn("opencode", hooks[0]["adapters"])

    def test_detect_source_binaries_pyproject(self):
        from agal.sources import detect_source_binaries
        with tempfile.TemporaryDirectory() as td:
            src_dir = Path(td)
            (src_dir / "pyproject.toml").write_text(
                '[project.scripts]\nmy-cli = "my_pkg.__main__:main"\nother-cmd = "my_pkg.cli:run"\n',
                encoding="utf-8",
            )
            detected = detect_source_binaries(src_dir)
            self.assertIn("my-cli", detected)
            self.assertIn("other-cmd", detected)

    def test_detect_source_binaries_setup_py(self):
        from agal.sources import detect_source_binaries
        with tempfile.TemporaryDirectory() as td:
            src_dir = Path(td)
            (src_dir / "setup.py").write_text(
                'setup(name="pkg", entry_points={"console_scripts": ["setup-tool = pkg:main"]})\n',
                encoding="utf-8",
            )
            detected = detect_source_binaries(src_dir)
            self.assertIn("setup-tool", detected)


    def test_parse_mcp_manifest_registry_schema(self):
        with tempfile.TemporaryDirectory() as td:
            server_json = Path(td) / "server.json"
            server_json.write_text(
                json.dumps({
                    "$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
                    "name": "io.github.microsoft/playwright-mcp",
                    "description": "Playwright Tools for MCP",
                    "packages": [
                        {
                            "registryType": "npm",
                            "identifier": "@playwright/mcp",
                            "version": "0.0.81",
                            "transport": {"type": "stdio"}
                        }
                    ]
                }),
                encoding="utf-8",
            )
            servers = parse_mcp_manifest(server_json)
            self.assertIn("playwright-mcp", servers)
            self.assertEqual(servers["playwright-mcp"]["command"], "npx")
            self.assertEqual(servers["playwright-mcp"]["args"], ["-y", "@playwright/mcp"])
            self.assertEqual(servers["playwright-mcp"]["raw_name"], "io.github.microsoft/playwright-mcp")
            self.assertEqual(servers["playwright-mcp"]["package"], "@playwright/mcp")

    def test_index_source_dir_server_json(self):
        with tempfile.TemporaryDirectory() as td:
            source_dir = Path(td) / "playwright-mcp"
            source_dir.mkdir()
            (source_dir / "server.json").write_text(
                json.dumps({
                    "name": "io.github.microsoft/playwright-mcp",
                    "packages": [{"registryType": "npm", "identifier": "@playwright/mcp"}]
                }),
                encoding="utf-8",
            )
            indexed = index_source_dir(source_dir)
            self.assertIn("playwright-mcp", indexed["mcp_servers"])
            self.assertEqual(indexed["mcp_servers"]["playwright-mcp"]["config"]["command"], "npx")

    def test_get_all_skills_indexes_each_source_once(self):
        from unittest.mock import patch
        import agal.sources

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src_dir = root / "sources" / "s1"
            (src_dir / "skills" / "sk1").mkdir(parents=True)
            (src_dir / "skills" / "sk1" / "SKILL.md").write_text(
                "---\nname: sk1\ndescription: d\n---\n", encoding="utf-8"
            )
            cfg = {"sources_dir": str(root / "sources"), "skills_dir": str(root / "no-bundled")}
            registry = {"s1": {"path": str(src_dir)}}
            with (
                patch("agal.sources.load_sources_registry", return_value=registry),
                patch("agal.sources.index_source_dir", wraps=agal.sources.index_source_dir) as spy_index,
            ):
                skills = agal.sources.get_all_skills(cfg)
                self.assertIn("sk1", skills)
                self.assertEqual(spy_index.call_count, 1)

    def _write_skill(self, skill_dir, name):
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(f"---\nname: {name}\ndescription: d\n---\n", encoding="utf-8")

    def test_index_includes_agent_skill_dirs_but_skips_other_hidden_dirs(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td)
            for rel in (".agents/skills", ".claude/skills", ".codex/skills", ".cursor/skills"):
                self._write_skill(src / rel / rel.split("/")[0].strip("."), rel.split("/")[0].strip("."))
            self._write_skill(src / ".github" / "hidden", "hidden")
            self._write_skill(src / ".agents" / "notes" / "loose", "loose")
            (src / ".agents" / "skills" / "agents" / "mcp.json").write_text(
                json.dumps({"mcpServers": {"skill-server": {"command": "x"}}}), encoding="utf-8"
            )
            indexed = index_source_dir(src)
            self.assertEqual(sorted(indexed["skills"]), ["agents", "claude", "codex", "cursor"])
            self.assertIn("skill-server", indexed["mcp_servers"])

    def test_index_prefers_visible_copy_over_hidden_duplicate(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td)
            self._write_skill(src / ".claude" / "skills" / "dup", "dup")
            self._write_skill(src / "skills" / "dup", "dup")
            indexed = index_source_dir(src)
            self.assertEqual(indexed["skills"]["dup"]["path"], str((src / "skills" / "dup").resolve()))

    def test_get_all_skills_honours_source_exclude(self):
        import agal.sources

        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "rea"
            self._write_skill(src / ".agents" / "skills" / "reverse-engineer-anything", "reverse-engineer-anything")
            self._write_skill(src / ".agents" / "skills" / "rea-changelog-update", "rea-changelog-update")
            cfg = {"sources_dir": str(td), "skills_dir": str(Path(td) / "no-bundled")}
            registry = {"rea": {"path": str(src), "exclude": ["rea-*"]}}
            with patch("agal.sources.load_sources_registry", return_value=registry):
                self.assertEqual(sorted(agal.sources.get_all_skills(cfg)), ["reverse-engineer-anything"])
                self.assertIn("rea-changelog-update", agal.sources.explain_missing_skill("rea-changelog-update", cfg))
                self.assertIn("exclude", agal.sources.explain_missing_skill("rea-changelog-update", cfg))

    def test_explain_missing_skill_names_source_and_skipped_dir(self):
        import agal.sources

        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "s1"
            self._write_skill(src / ".openclaw" / "skills" / "claw", "claw")
            cfg = {"sources_dir": str(td)}
            with patch("agal.sources.load_sources_registry", return_value={"s1": {"path": str(src)}}):
                msg = agal.sources.explain_missing_skill("claw", cfg)
                self.assertIn("'s1'", msg)
                self.assertIn(".openclaw/skills/claw", msg)
                self.assertEqual(agal.sources.explain_missing_skill("nope", cfg), "")


if __name__ == "__main__":
    unittest.main()
