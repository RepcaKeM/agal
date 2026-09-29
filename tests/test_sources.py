import json
from pathlib import Path
import tempfile
import unittest

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

            self.assertEqual(len(indexed["hooks"]), 1)
            self.assertEqual(indexed["hooks"][0]["name"], "pre-tool.sh")

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


if __name__ == "__main__":
    unittest.main()
