"""Enterprise navigation invariants; no graphical display required."""
import unittest
from ui_enterprise import SECTIONS, all_tabs, section_for_tab, DARK, LIGHT
import main


class EnterpriseNavigationTests(unittest.TestCase):
    def test_every_existing_tab_is_reachable(self):
        expected = {
            "Dashboard", "Consola RCON", "Configuración y Mods",
            "Backups", "Jugadores", "Workshop Mods", "Auditoría / Discord",
            "Logs", "Windows Nativo", "Ajustes", "Perfiles",
        }
        self.assertEqual(set(all_tabs()), expected)
        self.assertEqual(len(all_tabs()), len(set(all_tabs())))

    def test_group_mapping(self):
        self.assertEqual(section_for_tab("Windows Nativo"), "Servidor")
        self.assertEqual(section_for_tab("Consola RCON"), "Servidor")
        self.assertEqual(section_for_tab("Ajustes"), "Configuración")
        self.assertEqual(section_for_tab("Workshop Mods"), "Workshop")
        self.assertIsNone(section_for_tab("no-existe"))

    def test_palette_contract(self):
        required = {"root", "sidebar", "surface", "surface_alt", "text",
                    "muted", "accent", "active", "border", "success"}
        self.assertEqual(set(DARK), required)
        self.assertEqual(set(LIGHT), required)

    def test_main_still_exports_application(self):
        self.assertTrue(callable(main.Application))
        self.assertTrue(callable(main.Application.apply_theme))


if __name__ == "__main__":
    unittest.main()
