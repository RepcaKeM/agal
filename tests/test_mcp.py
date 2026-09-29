import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agal.mcp import (
    install_mcp,
    uninstall_mcp,
    list_installed_mcp,
    LOCAL_MCP_FILE,
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
