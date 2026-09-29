import os
import unittest
from unittest.mock import patch

from agal import ui


class TestUI(unittest.TestCase):
    def test_visible_len(self):
        colored = "\033[32mhello\033[0m world"
        self.assertEqual(ui.visible_len(colored), 11)
        self.assertEqual(ui.visible_len("plain text"), 10)

    def test_card_rendering(self):
        title = "Test Card"
        rows = [("Key1:", "Val1"), ("Key2:", "Val2")]
        rendered = ui.card(title, rows, min_width=40)
        self.assertIn("Test Card", rendered)
        self.assertIn("Key1:", rendered)
        self.assertIn("Val1", rendered)
        self.assertIn("╭", rendered)
        self.assertIn("╰", rendered)

    def test_notice_banner_rendering(self):
        notice = "Update available"
        rendered = ui.notice_banner(notice)
        self.assertIn("Update available", rendered)
        self.assertIn("╭─ Notice", rendered)
        self.assertIn("╰", rendered)

    def test_no_color_environment(self):
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            self.assertEqual(ui.cyan("text"), "text")
            self.assertEqual(ui.green("ok"), "ok")
            self.assertEqual(ui.ok_mark(), "✔")
            self.assertEqual(ui.fail_mark(), "✖")

    def test_color_supported_when_isatty(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch("sys.stdout.isatty", return_value=True):
            self.assertIn("\033[36m", ui.cyan("test"))
            self.assertIn("\033[32m", ui.green("test"))


if __name__ == "__main__":
    unittest.main()
