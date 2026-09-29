import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from agal.cli import main
from agal.config import LOCAL_STATE_FILE


class TestCLIIntegration(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.home_dir = Path(self.td.name) / "home"
        self.home_dir.mkdir()
        self.proj_dir = Path(self.td.name) / "project"
        self.proj_dir.mkdir()

        self.env = {
            "AGAL_HOME": str(self.home_dir),
            "HOME": str(self.home_dir),
        }

        # Create a mock source git repository
        self.repo_dir = Path(self.td.name) / "test-repo"
        self.repo_dir.mkdir()
        subprocess.run(["git", "init", "-b", "main"], cwd=self.repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.repo_dir, capture_output=True, check=True)

        # Add a skill
        skill_dir = self.repo_dir / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: Use when testing the system.\n---\n# Test skill body\n",
            encoding="utf-8",
        )
        (skill_dir / "run.sh").write_text("#!/bin/bash\necho ok", encoding="utf-8")

        # Add an MCP server
        (self.repo_dir / "mcp.json").write_text(
            json.dumps({
                "mcpServers": {
                    "test-server": {
                        "command": "python",
                        "args": ["-m", "server"],
                        "description": "A test MCP server",
                    }
                }
            }),
            encoding="utf-8",
        )

        subprocess.run(["git", "add", "."], cwd=self.repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=self.repo_dir, capture_output=True, check=True)

    def tearDown(self):
        self.td.cleanup()

    def test_cli_full_lifecycle(self):
        with patch.dict("os.environ", self.env):
            # 1. Add source
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture):
                main(["source", "add", str(self.repo_dir), "--name", "my-source"])
            out = stdout_capture.getvalue()
            self.assertIn("Successfully added source 'my-source'", out)
            self.assertIn("Skills:  1 discovered", out)
            self.assertIn("MCP:     1 discovered", out)

            # 2. List skills & MCP
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture):
                main(["list", "all"])
            out = stdout_capture.getvalue()
            self.assertIn("test-skill", out)
            self.assertIn("test-server", out)

            # 3. Add skill locally in project dir
            with patch("pathlib.Path.cwd", return_value=self.proj_dir):
                stdout_capture = io.StringIO()
                with patch("sys.stdout", stdout_capture):
                    main(["add", "skill", "test-skill"])
                self.assertIn("Installed skill 'test-skill'", stdout_capture.getvalue())

                # Check files exist
                self.assertTrue((self.proj_dir / ".agents" / "skills" / "test-skill" / "run.sh").is_file())
                self.assertTrue((self.proj_dir / ".claude" / "skills" / "test-skill" / "run.sh").is_file())

                # 4. Add MCP locally
                stdout_capture = io.StringIO()
                with patch("sys.stdout", stdout_capture):
                    main(["add", "mcp", "test-server"])
                self.assertIn("Installed MCP server 'test-server'", stdout_capture.getvalue())

                mcp_file = self.proj_dir / ".mcp.json"
                self.assertTrue(mcp_file.is_file())
                with open(mcp_file, "r") as f:
                    data = json.load(f)
                self.assertIn("test-server", data["mcpServers"])

                # 5. Check status
                stdout_capture = io.StringIO()
                with patch("sys.stdout", stdout_capture):
                    main(["status"])
                out = stdout_capture.getvalue()
                self.assertIn("test-skill", out)
                self.assertIn("test-server", out)

                # 6. Remove skill & MCP
                stdout_capture = io.StringIO()
                with patch("sys.stdout", stdout_capture):
                    main(["remove", "skill", "test-skill"])
                    main(["remove", "mcp", "test-server"])
                self.assertFalse((self.proj_dir / ".agents" / "skills" / "test-skill").exists())

                # Check .mcp.json either doesn't exist (cleaned up) or doesn't have test-server
                if mcp_file.is_file():
                    with open(mcp_file, "r") as f:
                        data = json.load(f)
                    self.assertNotIn("test-server", data.get("mcpServers", {}))

    def test_source_tool_prompt_and_install_tools(self):
        # Create a repo with a pyproject.toml containing a script
        tool_repo = Path(self.td.name) / "tool-repo"
        tool_repo.mkdir()
        subprocess.run(["git", "init", "-b", "main"], cwd=tool_repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tool_repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tool_repo, capture_output=True, check=True)
        (tool_repo / "pyproject.toml").write_text(
            '[project]\nname = "mytool"\nversion = "0.1.0"\n[project.scripts]\nmytool = "mytool:main"\n',
            encoding="utf-8",
        )
        (tool_repo / "SKILL.md").write_text("---\nname: mytool\ndescription: Tool skill\n---\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=tool_repo, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "Init"], cwd=tool_repo, capture_output=True, check=True)

        with patch.dict("os.environ", self.env):
            # Test 1: User says 'n' at prompt -> tool skipped
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture), patch("sys.stdin.isatty", return_value=True), patch("builtins.input", return_value="n"):
                main(["source", "add", str(tool_repo), "--name", "prompt-repo"])
            out = stdout_capture.getvalue()
            self.assertIn("Detected executable CLI tool(s): 'mytool'", out)
            self.assertIn("Skipped tool installation", out)

            # Test 2: agal source install-tools prompt-repo
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture), patch("agal.sources.install_source_binaries", return_value=["mytool"]):
                main(["source", "install-tools", "prompt-repo"])
            out = stdout_capture.getvalue()
            self.assertIn("Detected CLI tool(s) in 'prompt-repo': 'mytool'", out)
            self.assertIn("Successfully installed and symlinked", out)

            # Test 3: source add with --yes
            tool_repo2 = Path(self.td.name) / "tool-repo2"
            tool_repo2.mkdir()
            subprocess.run(["git", "init", "-b", "main"], cwd=tool_repo2, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tool_repo2, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tool_repo2, capture_output=True, check=True)
            (tool_repo2 / "pyproject.toml").write_text(
                '[project]\nname = "mytool2"\nversion = "0.1.0"\n[project.scripts]\nmytool2 = "mytool2:main"\n',
                encoding="utf-8",
            )
            subprocess.run(["git", "add", "."], cwd=tool_repo2, capture_output=True, check=True)
            subprocess.run(["git", "commit", "-m", "Init"], cwd=tool_repo2, capture_output=True, check=True)

            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture), patch("agal.sources.install_source_binaries", return_value=["mytool2"]):
                main(["source", "add", str(tool_repo2), "--name", "auto-repo", "--yes"])
            out = stdout_capture.getvalue()
            self.assertIn("Installing into isolated environment (~/.agal/venv) (--yes flag)", out)

            # Test 4: source add when already exists (user says 'N' to overwrite)
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture), patch("sys.stdin.isatty", return_value=True), patch("builtins.input", return_value="n"):
                main(["source", "add", str(tool_repo2), "--name", "auto-repo"])
            out = stdout_capture.getvalue()
            self.assertIn("Source 'auto-repo' already exists", out)
            self.assertIn("Aborted", out)

            # Test 5: source add with --force on existing source
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture), patch("agal.sources.install_source_binaries", return_value=["mytool2"]):
                main(["source", "add", str(tool_repo2), "--name", "auto-repo", "--force", "--yes"])
            out = stdout_capture.getvalue()
            self.assertIn("Successfully added source 'auto-repo'", out)

    def test_cmd_preset_delete(self):
        with patch.dict("os.environ", self.env):
            presets_dir = self.home_dir / "presets"
            presets_dir.mkdir(parents=True, exist_ok=True)
            test_preset = presets_dir / "my-preset.yaml"
            test_preset.write_text("name: my-preset\nskills: []\n", encoding="utf-8")

            # 1. Abort deletion when user says 'n'
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture), patch("builtins.input", return_value="n"):
                main(["preset", "delete", "my-preset"])
            out = stdout_capture.getvalue()
            self.assertIn("Cancelled", out)
            self.assertTrue(test_preset.is_file())

            # 2. Confirm deletion when user says 'y'
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture), patch("builtins.input", return_value="y"):
                main(["preset", "delete", "my-preset"])
            out = stdout_capture.getvalue()
            self.assertIn("Deleted preset 'my-preset'", out)
            self.assertFalse(test_preset.is_file())

            # 3. Non-existent preset
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture):
                main(["preset", "delete", "non-existent"])
            out = stdout_capture.getvalue()
            self.assertIn("Preset 'non-existent' not found", out)

    def test_cmd_preset_edit(self):
        with patch.dict("os.environ", self.env):
            presets_dir = self.home_dir / "presets"
            presets_dir.mkdir(parents=True, exist_ok=True)
            test_preset = presets_dir / "my-preset.yaml"
            test_preset.write_text("name: my-preset\nskills: [brainstorming]\nmcp: []\n", encoding="utf-8")

            # 1. Edit via subcommand
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture), patch("subprocess.run"):
                main(["preset", "edit", "my-preset"])
            out = stdout_capture.getvalue()
            self.assertIn("Preset 'my-preset' saved", out)

            # 2. Edit via top-level -e flag
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture), patch("subprocess.run"):
                main(["-e", "my-preset"])
            out = stdout_capture.getvalue()
            self.assertIn("Preset 'my-preset' saved", out)

            # 3. Non-existent preset
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture):
                main(["preset", "edit", "non-existent"])
            out = stdout_capture.getvalue()
            self.assertIn("Preset 'non-existent' not found", out)

    def test_cmd_list_sources(self):
        with patch.dict("os.environ", self.env):
            # Add source first
            main(["source", "add", str(self.repo_dir), "--name", "src-list-test"])

            # Test list sources explicitly
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture):
                main(["list", "sources"])
            out = stdout_capture.getvalue()
            self.assertIn("Registered Git Sources", out)
            self.assertIn("src-list-test", out)

    def test_cmd_error_handling_graceful(self):
        with patch.dict("os.environ", self.env):
            # Non-existent skill
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture):
                main(["add", "skill", "does-not-exist"])
            out = stdout_capture.getvalue()
            self.assertIn("❌ Skill 'does-not-exist' not found in any registered source", out)

            # Non-existent preset in prepare
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture):
                main(["prepare", "does-not-exist"])
            out = stdout_capture.getvalue()
            self.assertIn("❌ Preset 'does-not-exist' not found", out)


if __name__ == "__main__":
    unittest.main()
