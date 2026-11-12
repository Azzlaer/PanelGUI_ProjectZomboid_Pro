import json
import tempfile
import unittest
from pathlib import Path
from pz_native import ProfileStore, validate_profile, native_launcher_path, steamcmd_arguments, NativeProcess, native_log_tail


class NativeTests(unittest.TestCase):
    def test_profile_round_trip(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ProfileStore(temp)
            store.save("Principal", {"mode": "native", "container": "pz-one",
                                     "password": "secret", "webhook": "https://example.invalid"})
            loaded = store.load("Principal")
            self.assertEqual(loaded["mode"], "native")
            self.assertEqual(loaded["container"], "pz-one")
            self.assertNotIn("password", json.loads((Path(temp) / "Principal.json").read_text()))
            self.assertNotIn("webhook", json.loads((Path(temp) / "Principal.json").read_text()))
            self.assertEqual(store.names(), ["Principal"])
    def test_profile_rejects_path(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ProfileStore(temp)
            for name in ("../secret", "a/b", "foo\\bar", ""):
                with self.assertRaises(ValueError):
                    store.save(name, {})
    def test_native_launcher_whitelist(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = root / "StartServer64.bat"
            script.write_text("@echo off")
            self.assertEqual(native_launcher_path({"native_dir": str(root)}).resolve(), script.resolve())
            with self.assertRaises(ValueError):
                validate_profile({"native_launcher": "dangerous.bat"})
    def test_steamcmd_args(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            exe = root / "steamcmd.exe"
            exe.touch()
            args = steamcmd_arguments({"native_dir": str(root / "server"),
                                       "steamcmd_exe": str(exe)}, validate=True)
            self.assertEqual(args[-3:], ["380870", "validate", "+quit"])
            self.assertNotIn("shell", args)
    def test_log_tail(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "server.log"
            p.write_text("one\ntwo\nthree\n")
            self.assertEqual(native_log_tail(p, 2), "two\nthree")
    def test_embedded_console_api(self):
        import inspect
        self.assertTrue(callable(NativeProcess.send))
        source = inspect.getsource(NativeProcess.start)
        self.assertIn("CREATE_NO_WINDOW", source)
        self.assertIn("stdout=subprocess.PIPE", source)
        self.assertIn("stdin=subprocess.PIPE", source)
        self.assertNotIn("CREATE_NEW_CONSOLE", source)

    def test_not_running_by_default(self):
        self.assertFalse(NativeProcess().running())

if __name__ == "__main__":
    unittest.main()
