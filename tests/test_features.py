import tempfile
import unittest
from pathlib import Path
from pz_features import (parse_ini, replace_ini_keys, parse_mod_pairs,
                         player_command, AuditStore, safe_extract_plan)
import zipfile

class FeatureTests(unittest.TestCase):
    def test_ini_preserves_comments(self):
        src = "# hello\nMods=old\nOther=x\n"
        self.assertEqual(replace_ini_keys(src, {"Mods":"new"}), "# hello\nMods=new\nOther=x\n")
        self.assertEqual(parse_ini(src)["Other"], "x")
    def test_mod_pairs(self):
        self.assertEqual(parse_mod_pairs("12345", "My.Mod"), [("12345","My.Mod")])
        with self.assertRaises(ValueError):
            parse_mod_pairs("12345;67890", "OnlyOne")
    def test_players(self):
        self.assertEqual(player_command("kickuser", "Alice"), 'kickuser "Alice"')
        with self.assertRaises(ValueError):
            player_command("banuser", 'a" bad')
    def test_audit(self):
        with tempfile.TemporaryDirectory() as td:
            store = AuditStore(Path(td)/"audit.sqlite3")
            store.record("test", "hello")
            self.assertEqual(store.recent(1)[0][2], "hello")
    def test_zip_traversal(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/"bad.zip"
            with zipfile.ZipFile(p,"w") as z:
                z.writestr("../outside.txt", "danger")
            with self.assertRaises(ValueError):
                safe_extract_plan(p, Path(td)/"dest")

if __name__ == "__main__":
    unittest.main()
