import tempfile
from pathlib import Path
import unittest

from agal.config import AGAL_CONTEXT_MARKER, CONTEXT_FILENAMES
from agal.context import (
    extract_triggers,
    build_routing_block,
    place_context_file,
    remove_context_file,
)


class TestContext(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.target_dir = Path(self.td.name) / "project"
        self.target_dir.mkdir()
        self.guidelines_dir = Path(self.td.name) / "guidelines"
        self.guidelines_dir.mkdir()
        self.guideline_src = self.guidelines_dir / "AGENTS.md"
        self.guideline_src.write_text("# Project Coding Guidelines\nFollow clean code.\n", encoding="utf-8")

    def tearDown(self):
        self.td.cleanup()

    def test_extract_triggers(self):
        text_with_trigger = (
            "---\n"
            "name: debugger\n"
            "description: Use when debugging failing unit tests, tracing memory leaks, or analyzing crashes.\n"
            "---\n"
            "# Debugger\n"
        )
        triggers = extract_triggers(text_with_trigger)
        self.assertIn("debugging failing unit tests", triggers)
        self.assertIn("tracing memory leaks", triggers)

        text_without_frontmatter = "# No frontmatter"
        self.assertEqual(extract_triggers(text_without_frontmatter), "")

        text_no_use_when = "---\nname: simple\ndescription: A simple skill.\n---\n"
        self.assertEqual(extract_triggers(text_no_use_when), "")

    def test_build_routing_block(self):
        skill_dir = Path(self.td.name) / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: my-skill\ndescription: Use when writing new unit tests.\n---\n",
            encoding="utf-8",
        )
        block, count = build_routing_block(["my-skill"], {"my-skill": skill_dir})
        self.assertEqual(count, 1)
        self.assertIn("Skill routing (this project)", block)
        self.assertIn("writing new unit tests,my-skill", block)

        empty_block, empty_count = build_routing_block(["missing"], {})
        self.assertEqual(empty_count, 0)
        self.assertEqual(empty_block, "")

    def test_place_and_remove_context_file(self):
        # 1. Place files cleanly
        created = place_context_file(self.target_dir, self.guideline_src)
        self.assertEqual(sorted(created), sorted(CONTEXT_FILENAMES))

        for fname in CONTEXT_FILENAMES:
            p = self.target_dir / fname
            self.assertTrue(p.exists())

        marker = self.target_dir / AGAL_CONTEXT_MARKER
        self.assertTrue(marker.exists())

        # 2. Re-placing overwrites tracked files and returns created
        created2 = place_context_file(self.target_dir, self.guideline_src, copy=True, routing_block="\nrouting")
        self.assertEqual(sorted(created2), sorted(CONTEXT_FILENAMES))
        self.assertIn("routing", (self.target_dir / "AGENTS.md").read_text(encoding="utf-8"))

        # 3. Remove files created by agal
        removed = remove_context_file(self.target_dir)
        self.assertEqual(sorted(removed), sorted(CONTEXT_FILENAMES))
        for fname in CONTEXT_FILENAMES:
            self.assertFalse((self.target_dir / fname).exists())
        self.assertFalse(marker.exists())

    def test_preexisting_file_is_skipped_and_protected(self):
        # User manually created KIMI.md before agal
        custom_kimi = self.target_dir / "KIMI.md"
        custom_kimi.write_text("# My Custom KIMI config\nDo not touch.\n", encoding="utf-8")

        created = place_context_file(self.target_dir, self.guideline_src)
        self.assertNotIn("KIMI.md", created)
        self.assertEqual(sorted(created), sorted(["AGENTS.md", "CLAUDE.md", "GEMINI.md"]))
        self.assertEqual(custom_kimi.read_text(encoding="utf-8"), "# My Custom KIMI config\nDo not touch.\n")

        # Uninstall should not touch KIMI.md
        removed = remove_context_file(self.target_dir)
        self.assertNotIn("KIMI.md", removed)
        self.assertTrue(custom_kimi.exists())


if __name__ == "__main__":
    unittest.main()
