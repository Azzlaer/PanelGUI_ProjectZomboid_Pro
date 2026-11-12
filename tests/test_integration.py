"""Integration checks that all GUI modules can be imported together."""
import unittest
import main
import pz_native
import pz_backup
import pz_features


class MergeIntegrationTests(unittest.TestCase):
    def test_modules_are_wired(self):
        self.assertTrue(callable(main.Application))
        self.assertTrue(callable(pz_backup.create_verified_backup))
        self.assertTrue(callable(pz_features.player_command))
        self.assertTrue(callable(pz_native.NativeProcess))
    def test_native_defaults_are_merged(self):
        self.assertEqual(main.DEFAULT["mode"], "docker")
        self.assertEqual(main.DEFAULT["steam_app_id"], "380870")
        self.assertEqual(main.DEFAULT["native_launcher"], "StartServer64.bat")
    def test_app_can_validate_both_modes(self):
        for mode in ("docker", "native"):
            profile = pz_native.validate_profile({**main.DEFAULT, "mode": mode})
            self.assertEqual(profile["mode"], mode)

if __name__ == "__main__":
    unittest.main()
