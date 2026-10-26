import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from agal.cli import _reconcile_managed, main
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
            # Non-existent skill exits non-zero after reporting the error
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture):
                with self.assertRaises(SystemExit) as caught:
                    main(["add", "skill", "does-not-exist"])
            self.assertEqual(caught.exception.code, 1)
            out = stdout_capture.getvalue()
            self.assertIn("❌ Skill 'does-not-exist' not found in any registered source", out)

            # Non-existent preset in prepare
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture):
                main(["prepare", "does-not-exist"])
            out = stdout_capture.getvalue()
            self.assertIn("❌ Preset 'does-not-exist' not found", out)

    def test_add_global_hook_is_rejected(self):
        with patch.dict("os.environ", self.env):
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture):
                with self.assertRaises(SystemExit) as caught:
                    main(["add", "hook", "anything", "--global"])
            self.assertEqual(caught.exception.code, 1)
            self.assertIn(
                "Global hook installation is not supported; install hooks per project.",
                stdout_capture.getvalue(),
            )

    def test_list_hooks_shows_adapters(self):
        bundles = {
            "ponytail": {
                "source": "ponytail",
                "adapters": {"claude": {"marketplace": "ponytail", "plugin": "ponytail"}},
            }
        }
        with patch.dict("os.environ", self.env), \
             patch("agal.cli.get_all_hooks", return_value=bundles):
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture):
                main(["list", "hooks"])
        out = stdout_capture.getvalue()
        self.assertIn("ponytail", out)
        self.assertIn("[claude]", out)

    def test_reconcile_managed_replaces_selection(self):
        installed, removed = [], []
        with patch("agal.cli._select_items_cli", return_value=["new"]), \
             patch("builtins.input", return_value="y"):
            _reconcile_managed(
                "Pick",
                {"old": "old", "new": "new"},
                {"old"},
                installed.append,
                removed.append,
            )
        self.assertEqual(installed, ["new"])
        self.assertEqual(removed, ["old"])

    def test_reconcile_managed_enter_keeps_current(self):
        installed, removed = [], []
        with patch("agal.cli._select_items_cli", return_value=[]):
            _reconcile_managed(
                "Pick",
                {"old": "old", "new": "new"},
                {"old"},
                installed.append,
                removed.append,
            )
        self.assertEqual(installed, [])
        self.assertEqual(removed, [])

    def test_reconcile_managed_no_confirmation_keeps_unselected(self):
        installed, removed = [], []
        with patch("agal.cli._select_items_cli", return_value=["new"]), \
             patch("builtins.input", return_value="n"):
            _reconcile_managed(
                "Pick",
                {"old": "old", "new": "new"},
                {"old"},
                installed.append,
                removed.append,
            )
        self.assertEqual(installed, ["new"])
        self.assertEqual(removed, [])

    def test_reconcile_managed_aborts_removal_when_install_fails(self):
        removed = []

        def install(name):
            raise ValueError("boom")

        with patch("agal.cli._select_items_cli", return_value=["new"]), \
             patch("builtins.input", return_value="y"):
            _reconcile_managed(
                "Pick",
                {"old": "old", "new": "new"},
                {"old"},
                install,
                removed.append,
            )
        self.assertEqual(removed, [])

    def test_bare_skill_prints_help_when_not_a_tty(self):
        with patch.dict("os.environ", self.env), patch("sys.stdin.isatty", return_value=False):
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture):
                main(["skill"])
            self.assertIn("usage: agal skill", stdout_capture.getvalue())

    def test_preset_named_skill_does_not_shadow_skill_command(self):
        with (
            patch.dict("os.environ", self.env),
            patch("sys.stdin.isatty", return_value=False),
            patch("pathlib.Path.cwd", return_value=self.proj_dir),
        ):
            presets_dir = self.home_dir / "presets"
            presets_dir.mkdir(parents=True, exist_ok=True)
            (presets_dir / "skill.yaml").write_text("name: skill\nskills: []\n", encoding="utf-8")
            stdout_capture = io.StringIO()
            with patch("sys.stdout", stdout_capture):
                main(["skill"])
            self.assertIn("usage: agal skill", stdout_capture.getvalue())
            self.assertFalse((self.proj_dir / LOCAL_STATE_FILE).exists())

    def test_skill_wizard_copies_selected_skills_for_active_runtime_and_keeps_preset_and_subagents(self):
        with patch.dict("os.environ", self.env):
            main(["source", "add", str(self.repo_dir), "--name", "my-source"])
            presets_dir = self.home_dir / "presets"
            presets_dir.mkdir(parents=True, exist_ok=True)
            (presets_dir / "base.yaml").write_text("name: base\nskills: []\nmcp: [test-server]\n", encoding="utf-8")
            sub_dir = self.home_dir / "subagents" / "helper"
            sub_dir.mkdir(parents=True, exist_ok=True)
            (sub_dir / "AGENT.md").write_text(
                "---\nname: helper\ndescription: Use when helping.\n---\nBody\n",
                encoding="utf-8",
            )

            with patch("pathlib.Path.cwd", return_value=self.proj_dir):
                main(["runtime", "set", "cursor"])
                main(["prepare", "base"])
                main(["subagent", "add", "helper"])

                stdout_capture = io.StringIO()
                with (
                    patch("sys.stdout", stdout_capture),
                    patch("sys.stdin.isatty", return_value=True),
                    patch("agal.cli._select_items_cli", side_effect=[["skills"], ["test-skill"]]),
                    patch("builtins.input", return_value=""),
                ):
                    main(["skill"])

                self.assertIn("Installed skill 'test-skill'", stdout_capture.getvalue())
                self.assertTrue((self.proj_dir / ".agents" / "skills" / "test-skill" / "SKILL.md").is_file())
                self.assertFalse((self.proj_dir / ".claude" / "skills" / "test-skill").exists())
                state = json.loads((self.proj_dir / LOCAL_STATE_FILE).read_text(encoding="utf-8"))
                self.assertEqual(state.get("preset"), "base")
                self.assertIn("helper", state.get("subagents", {}))

    def test_skill_wizard_preset_branch_replaces_active_preset(self):
        with patch.dict("os.environ", self.env):
            main(["source", "add", str(self.repo_dir), "--name", "my-source"])
            presets_dir = self.home_dir / "presets"
            presets_dir.mkdir(parents=True, exist_ok=True)
            (presets_dir / "p1.yaml").write_text("name: p1\nskills: [test-skill]\n", encoding="utf-8")
            (presets_dir / "p2.yaml").write_text("name: p2\nskills: []\nmcp: [test-server]\n", encoding="utf-8")

            with patch("pathlib.Path.cwd", return_value=self.proj_dir):
                main(["prepare", "p1"])
                self.assertTrue((self.proj_dir / ".agents" / "skills" / "test-skill").is_dir())

                with (
                    patch("sys.stdout", io.StringIO()),
                    patch("sys.stdin.isatty", return_value=True),
                    patch("agal.cli._select_items_cli", side_effect=[["preset"], ["p2"]]),
                ):
                    main(["skill"])

                state = json.loads((self.proj_dir / LOCAL_STATE_FILE).read_text(encoding="utf-8"))
                self.assertEqual(state.get("preset"), "p2")
                self.assertFalse((self.proj_dir / ".agents" / "skills" / "test-skill").exists())
                self.assertIn("test-server", state.get("mcp", {}))

    def test_skill_wizard_promotes_preset_skill_to_manual(self):
        with patch.dict("os.environ", self.env):
            main(["source", "add", str(self.repo_dir), "--name", "my-source"])
            presets_dir = self.home_dir / "presets"
            presets_dir.mkdir(parents=True, exist_ok=True)
            (presets_dir / "p1.yaml").write_text("name: p1\nskills: [test-skill]\n", encoding="utf-8")
            (presets_dir / "p2.yaml").write_text("name: p2\nskills: []\n", encoding="utf-8")

            with patch("pathlib.Path.cwd", return_value=self.proj_dir):
                main(["prepare", "p1"])
                state = json.loads((self.proj_dir / LOCAL_STATE_FILE).read_text(encoding="utf-8"))
                self.assertIn("test-skill", state["preset_owned"]["skills"])

                with (
                    patch("sys.stdout", io.StringIO()),
                    patch("sys.stdin.isatty", return_value=True),
                    patch("agal.cli._select_items_cli", side_effect=[["skills"], ["test-skill"]]),
                    patch("builtins.input", return_value=""),
                ):
                    main(["skill"])

                state = json.loads((self.proj_dir / LOCAL_STATE_FILE).read_text(encoding="utf-8"))
                self.assertNotIn("test-skill", state.get("preset_owned", {}).get("skills", []))
                main(["prepare", "p2"])
                state = json.loads((self.proj_dir / LOCAL_STATE_FILE).read_text(encoding="utf-8"))
                self.assertEqual(state.get("preset"), "p2")
                self.assertIn("test-skill", state.get("skills", {}))
                self.assertTrue((self.proj_dir / ".agents" / "skills" / "test-skill").is_dir())

    def test_skill_wizard_empty_selections_do_nothing(self):
        with patch.dict("os.environ", self.env):
            main(["source", "add", str(self.repo_dir), "--name", "my-source"])
            presets_dir = self.home_dir / "presets"
            presets_dir.mkdir(parents=True, exist_ok=True)
            (presets_dir / "p1.yaml").write_text("name: p1\nskills: [test-skill]\n", encoding="utf-8")

            with patch("pathlib.Path.cwd", return_value=self.proj_dir):
                main(["prepare", "p1"])
                before = json.loads((self.proj_dir / LOCAL_STATE_FILE).read_text(encoding="utf-8"))

                with (
                    patch("sys.stdout", io.StringIO()),
                    patch("sys.stdin.isatty", return_value=True),
                    patch("agal.cli._select_items_cli", return_value=[]),
                ):
                    main(["skill"])
                self.assertEqual(
                    json.loads((self.proj_dir / LOCAL_STATE_FILE).read_text(encoding="utf-8")),
                    before,
                )

                with (
                    patch("sys.stdout", io.StringIO()),
                    patch("sys.stdin.isatty", return_value=True),
                    patch("agal.cli._select_items_cli", side_effect=[["skills"], []]),
                    patch("builtins.input", return_value=""),
                ):
                    main(["skill"])
                self.assertEqual(
                    json.loads((self.proj_dir / LOCAL_STATE_FILE).read_text(encoding="utf-8")),
                    before,
                )

    def test_add_skill_without_name_opens_picker_in_tty_and_help_in_non_tty(self):
        with patch.dict("os.environ", self.env):
            main(["source", "add", str(self.repo_dir), "--name", "my-source"])
            with patch("pathlib.Path.cwd", return_value=self.proj_dir):
                buf = io.StringIO()
                with patch("sys.stdout", buf), patch("sys.stdin.isatty", return_value=False):
                    main(["add", "skill"])
                self.assertIn("usage: agal add", buf.getvalue())
                self.assertFalse((self.proj_dir / ".agents" / "skills" / "test-skill").exists())

                with (
                    patch("sys.stdout", io.StringIO()),
                    patch("sys.stdin.isatty", return_value=True),
                    patch("agal.cli._select_items_cli", return_value=["test-skill"]),
                    patch("builtins.input", return_value=""),
                ):
                    main(["add", "skill"])
                self.assertTrue((self.proj_dir / ".agents" / "skills" / "test-skill").is_dir())

    def test_interactive_launcher_routes_to_skill_wizard_and_preset_replace(self):
        with patch.dict("os.environ", self.env):
            main(["source", "add", str(self.repo_dir), "--name", "my-source"])
            presets_dir = self.home_dir / "presets"
            presets_dir.mkdir(parents=True, exist_ok=True)
            (presets_dir / "p1.yaml").write_text("name: p1\nskills: [test-skill]\n", encoding="utf-8")
            (presets_dir / "p2.yaml").write_text("name: p2\nskills: []\n", encoding="utf-8")

            with patch("pathlib.Path.cwd", return_value=self.proj_dir):
                with (
                    patch("sys.stdout", io.StringIO()),
                    patch("sys.stdin.isatty", return_value=True),
                    patch("builtins.input", side_effect=["11", ""]),
                    patch("agal.cli._select_items_cli", side_effect=[["skills"], ["test-skill"]]),
                ):
                    main([])
                self.assertTrue((self.proj_dir / ".agents" / "skills" / "test-skill").is_dir())

                with (
                    patch("sys.stdout", io.StringIO()),
                    patch("sys.stdin.isatty", return_value=True),
                    patch("builtins.input", return_value="2"),
                    patch("agal.cli._select_items_cli", return_value=["p2"]),
                ):
                    main([])
                state = json.loads((self.proj_dir / LOCAL_STATE_FILE).read_text(encoding="utf-8"))
                self.assertEqual(state.get("preset"), "p2")
                self.assertTrue((self.proj_dir / ".agents" / "skills" / "test-skill").is_dir())

    def test_check_and_refresh_handle_dead_links_and_update_warns_about_orphans(self):
        def run(*argv):
            out = io.StringIO()
            with patch("sys.stdout", out):
                main(list(argv))
            return out.getvalue()

        with patch.dict("os.environ", self.env), patch("pathlib.Path.cwd", return_value=self.proj_dir):
            run("source", "add", str(self.repo_dir), "--name", "my-source")
            run("add", "skill", "test-skill")
            dead = self.proj_dir / ".claude" / "skills" / "old-skill"
            dead.symlink_to(Path(self.td.name) / "gone" / "old-skill")

            out = run("check")
            self.assertIn("Dead skill links (1)", out)
            self.assertIn(str(dead), out)

            out = run("refresh")
            self.assertIn(f"Removed dead link {dead}", out)
            self.assertFalse(dead.is_symlink())

            subprocess.run(["git", "rm", "-rq", "test-skill"], cwd=self.repo_dir, check=True)
            subprocess.run(["git", "commit", "-qm", "drop skill"], cwd=self.repo_dir, check=True)
            out = run("update")
            self.assertIn("Installed skill 'test-skill' is no longer in any source", out)


if __name__ == "__main__":
    unittest.main()
