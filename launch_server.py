"""Simple emergency launcher for the Project Zomboid dedicated server on Windows."""
from __future__ import annotations

import json
import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from pz_native import NativeProcess, native_launcher_path, DEFAULT_PROFILE

ROOT = Path(os.getenv("APPDATA") or Path.home()) / "PanelGUI_ProjectZomboid_Pro"
CONFIG = ROOT / "config.json"


def load_settings():
    try:
        raw = json.loads(CONFIG.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return dict(DEFAULT_PROFILE)
        return {**DEFAULT_PROFILE, **raw, "mode": "native"}
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_PROFILE)


def choose_and_launch():
    if os.name != "nt":
        print("Este iniciador requiere Windows.", file=sys.stderr)
        return 1
    root = tk.Tk()
    root.withdraw()
    try:
        cfg = load_settings()
        try:
            script = native_launcher_path(cfg)
        except (ValueError, OSError):
            selected = filedialog.askdirectory(
                title="Carpeta de instalación de Project Zomboid (contiene StartServer64.bat)")
            if not selected:
                return 1
            cfg["native_dir"] = selected
            try:
                script = native_launcher_path(cfg)
            except (ValueError, OSError) as exc:
                messagebox.showerror("Instalación inválida", str(exc))
                return 1
        if not messagebox.askyesno("Arrancar Project Zomboid",
                "Abrir consola del servidor desde:\n" + str(script.parent) + "\n\n¿Continuar?"):
            return 1
        ROOT.mkdir(parents=True, exist_ok=True)
        CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        pid = NativeProcess().start(cfg)
        messagebox.showinfo("Consola iniciada",
                            f"Se abrió la consola del servidor (PID {pid}).\n"
                            "Revisa esa ventana para completar el primer inicio.")
        return 0
    except Exception as exc:
        messagebox.showerror("No se pudo iniciar", str(exc))
        return 1
    finally:
        root.destroy()


if __name__ == "__main__":
    raise SystemExit(choose_and_launch())
