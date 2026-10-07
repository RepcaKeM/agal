import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "Skills" / "sales-writing" / "scripts" / "check_copy.py"
_spec = importlib.util.spec_from_file_location("check_copy", SCRIPT)
check_copy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_copy)
check = check_copy.check
load_list = check_copy.load_list


class TestCheck(unittest.TestCase):
    def test_ok_text(self):
        self.assertEqual(check("We can fix it. Want a plan?", 150, ["expert"], ["Acme"], True), [])

    def test_too_long(self):
        self.assertEqual(check("word " * 151, 150, [], [], False), ["too long: 151 words (max 150)"])

    def test_banned_word_case_insensitive(self):
        self.assertIn("banned word: passionate", check("I am Passionate about it.", 150, ["passionate"], [], False))

    def test_banned_word_whole_word_only(self):
        self.assertEqual(check("Deep expertise in n8n.", 150, ["expert"], [], False), [])

    def test_banned_phrase(self):
        self.assertIn("banned word: look forward", check("I look forward to it.", 150, ["look forward"], [], False))

    def test_name_case_insensitive(self):
        self.assertIn("banned name: Globex", check("Built for globex.", 150, [], ["Globex"], False))

    def test_name_with_possessive(self):
        self.assertIn("banned name: Initech", check("Initech's CRM was slow.", 150, [], ["Initech"], False))

    def test_multiword_name(self):
        self.assertIn("banned name: Acme Corp", check("At acme corp I built MCP.", 150, [], ["Acme Corp"], False))

    def test_requires_question(self):
        self.assertEqual(check("Let me know.", 150, [], [], True), ["must end with a question"])

    def test_question_with_trailing_whitespace(self):
        self.assertEqual(check("Which CRM do you use?  \n", 150, [], [], True), [])

    def test_required_text_present(self):
        self.assertEqual(check("Cases: Example.com. Want more?", 150, [], [], True, ["example.com"]), [])

    def test_required_text_not_counted(self):
        line = "Portfolio: example.com - more proofs and examples of my work."
        self.assertEqual(check("word " * 150 + line + " Ok?", 151, [], [], True, [line]), [])

    def test_required_text_missing(self):
        self.assertEqual(check("No link here?", 150, [], [], True, ["example.com"]), ["missing required text: example.com"])


class TestLoadList(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.dir = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def test_names_file_blank_and_comments(self):
        path = self.dir / "names.txt"
        path.write_text("# clients\n\nAcme\n  \nGlobex\n", encoding="utf-8")
        self.assertEqual(load_list(path), ["Acme", "Globex"])

    def test_md_list_parsing(self):
        path = self.dir / "banned.md"
        path.write_text("# Banned\n\nIntro line\n- passionate\n- look forward\n", encoding="utf-8")
        self.assertEqual(load_list(path), ["passionate", "look forward"])


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.dir = Path(self.td.name)
        self.ok_file = self.dir / "ok.txt"
        self.ok_file.write_text("We can fix it. Want a plan?", encoding="utf-8")
        self.long_file = self.dir / "long.txt"
        self.long_file.write_text("one two three four five six seven", encoding="utf-8")

    def tearDown(self):
        self.td.cleanup()

    def run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = check_copy.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_cli_ok_and_fail_exit_codes(self):
        code, out, _ = self.run_main([str(self.ok_file), "--max-words", "150"])
        self.assertEqual((code, out.strip()), (0, "OK"))
        code, out, _ = self.run_main([str(self.long_file), "--max-words", "5"])
        self.assertEqual(code, 1)
        self.assertIn("too long: 7 words (max 5)", out)

    def test_cli_require_text(self):
        code, out, _ = self.run_main([str(self.ok_file), "--max-words", "150", "--require-text", "example.com"])
        self.assertEqual((code, out.strip()), (1, "missing required text: example.com"))

    def test_missing_names_file_errors_clearly(self):
        code, _, err = self.run_main([str(self.ok_file), "--max-words", "150", "--banned-names", "/nonexistent"])
        self.assertEqual(code, 2)
        self.assertIn("/nonexistent", err)


if __name__ == "__main__":
    unittest.main()
