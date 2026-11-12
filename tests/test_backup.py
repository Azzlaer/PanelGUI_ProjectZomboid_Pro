import tempfile
import unittest
import zipfile
from datetime import datetime
from pathlib import Path
from pz_backup import (create_verified_backup, inspect_backup, stage_restore,
                       prune_backups, due_daily)


class BackupTests(unittest.TestCase):
    def test_verified_backup_and_safe_stage(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            src = base / "world"
            (src / "Saves").mkdir(parents=True)
            (src / "Saves" / "map.bin").write_bytes(b"hello zomboid")
            archive = create_verified_backup(src, base / "archives")
            result = inspect_backup(archive)
            self.assertTrue(result["hash_verified"])
            staged = base / "restored"
            stage_restore(archive, staged)
            self.assertEqual((staged / "Saves" / "map.bin").read_bytes(), b"hello zomboid")
            with self.assertRaises(FileExistsError):
                stage_restore(archive, staged)

    def test_zip_traversal_prevented(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            archive = base / "evil.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("../outside.txt", "no")
            with self.assertRaises(ValueError):
                inspect_backup(archive)

    def test_corrupt_hash_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            src = base / "world"
            src.mkdir()
            (src / "file").write_text("original")
            archive = create_verified_backup(src, base / "archive")
            with zipfile.ZipFile(archive, "a") as zf:
                zf.writestr("intruder.txt", "modified")
            with self.assertRaises(ValueError):
                inspect_backup(archive)

    def test_retention(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            src = base / "world"
            src.mkdir()
            (src / "file").write_text("hello")
            folder = base / "archives"
            for _ in range(3):
                create_verified_backup(src, folder)
            self.assertEqual(prune_backups(folder, 1), 2)
            self.assertEqual(len(list(folder.glob("*.zip"))), 1)

    def test_daily(self):
        now = datetime(2026, 11, 11, 22, 0)
        self.assertTrue(due_daily(now, "2026-11-10", 21))
        self.assertFalse(due_daily(now, "2026-11-11", 21))
        self.assertFalse(due_daily(now, "2026-11-10", 23))


if __name__ == "__main__":
    unittest.main()
