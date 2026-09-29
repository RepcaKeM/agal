import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agal.updater import (
    format_update_notice,
    load_update_cache,
    save_update_cache,
)


class TestUpdater(unittest.TestCase):
    def test_format_update_notice_single(self):
        updates = {"superpowers": {"local": "1111111", "remote": "2222222", "url": "https://..."}}
        notice = format_update_notice(updates)
        self.assertIsNotNone(notice)
        self.assertIn("superpowers", notice)
        self.assertIn("1111111 → 2222222", notice)
        self.assertIn("agal update superpowers", notice)

    def test_format_update_notice_multiple(self):
        updates = {
            "source-a": {"local": "1111111", "remote": "2222222", "url": "https://..."},
            "source-b": {"local": "3333333", "remote": "4444444", "url": "https://..."},
        }
        notice = format_update_notice(updates)
        self.assertIsNotNone(notice)
        self.assertIn("'source-a'", notice)
        self.assertIn("'source-b'", notice)

    def test_format_update_notice_empty(self):
        self.assertIsNone(format_update_notice({}))


if __name__ == "__main__":
    unittest.main()
