import tempfile
import unittest
from pathlib import Path
from pz_paths import candidate_data_directories, server_ini_files


class PathDiscoveryTests(unittest.TestCase):
    def test_detect_data_and_ini(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "Zomboid" / "Server"
            target.mkdir(parents=True)
            (target / "servertest.ini").write_text("PVP=false")
            self.assertEqual(candidate_data_directories(root, {}), [root / "Zomboid"])
            self.assertEqual([p.name for p in server_ini_files(root / "Zomboid")],
                             ["servertest.ini"])

    def test_does_not_confuse_install_dir_with_data_dir(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "Zomboid").mkdir()
            self.assertEqual(candidate_data_directories(root, {}), [])

if __name__ == "__main__":
    unittest.main()
