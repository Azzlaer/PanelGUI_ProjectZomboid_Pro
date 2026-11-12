"""Windows native server support and per-server profiles (Python stdlib only).

Native process ownership deliberately limited to processes started by this GUI.
No shell=True. No automatic shutdown/kill of unrelated processes.
"""
from __future__ import annotations
import json
import os
import re
import subprocess
import threading
from pathlib import Path

PROFILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_. -]{0,39}$")
DEFAULT_PROFILE = {
    "mode": "native", "container": "pz-game-server", "host": "127.0.0.1",
    "port": 27015, "data_dir": "", "ini_file": "", "backup_dir": "",
    "webhook": "", "backup_enabled": False, "backup_hour": 3,
    "backup_keep": 7, "backup_last": "",
    "native_dir": "", "native_launcher": "StartServer64.bat",
    "steamcmd_exe": "", "steam_app_id": "380870",
}


def validate_profile(config: dict) -> dict:
    """Return normalized profile, rejecting invalid execution arguments."""
    if not isinstance(config, dict):
        raise ValueError("El perfil debe ser un objeto")
    p = {**DEFAULT_PROFILE, **config}
    # Project Zomboid Manager now targets local Windows server execution only.
    p["mode"] = "native"
    try:
        p["port"] = int(p["port"])
        p["backup_hour"] = int(p["backup_hour"])
        p["backup_keep"] = int(p["backup_keep"])
    except (ValueError, TypeError) as exc:
        raise ValueError("Puertos y horarios deben ser enteros") from exc
    if not 1 <= p["port"] <= 65535:
        raise ValueError("Puerto RCON inválido")
    if not 0 <= p["backup_hour"] <= 23 or not 1 <= p["backup_keep"] <= 365:
        raise ValueError("Hora/retención inválida")
    p["backup_enabled"] = bool(p["backup_enabled"])
    for key in ("native_dir", "native_launcher", "steamcmd_exe", "steam_app_id"):
        if not isinstance(p[key], str):
            raise ValueError(key + " debe ser texto")
    if p["native_launcher"] not in ("StartServer64.bat", "StartServer64_nosteam.bat",
                                     "StartServer32.bat"):
        raise ValueError("Lanzador de servidor no reconocido")
    if not re.fullmatch(r"[1-9][0-9]{3,9}", p["steam_app_id"]):
        raise ValueError("App ID SteamCMD inválido")
    return p


class ProfileStore:
    """One JSON file per installation; legacy configuration can be imported in GUI."""
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, name):
        if not isinstance(name, str) or not PROFILE_RE.fullmatch(name):
            raise ValueError("Nombre de perfil inválido")
        return self.directory / (name + ".json")

    def names(self):
        return sorted(p.stem for p in self.directory.glob("*.json") if PROFILE_RE.fullmatch(p.stem))

    def load(self, name):
        path = self._path(name)
        return validate_profile(json.loads(path.read_text(encoding="utf-8")))

    def save(self, name, config):
        path = self._path(name)
        profile = validate_profile(config)
        # Avoid embedding secrets in profile files. Legacy secrets migrate via separate store later.
        clean = {key: value for key, value in profile.items() if key not in ("password", "webhook")}
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, path)
        return path


def native_launcher_path(config):
    c = validate_profile(config)
    root = Path(c["native_dir"]).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("Carpeta del servidor Windows no encontrada")
    launcher = root / c["native_launcher"]
    if not launcher.is_file() or launcher.is_symlink():
        raise ValueError("Archivo StartServer no encontrado")
    return launcher


def steamcmd_arguments(config, *, validate=False):
    """Build dedicated server installation command for SteamCMD.

    Caller must show explicit confirmation before running this command.
    """
    c = validate_profile(config)
    if not c["steamcmd_exe"]:
        raise ValueError("Indica la ruta de steamcmd.exe")
    exe = Path(c["steamcmd_exe"]).expanduser().resolve()
    directory = Path(c["native_dir"]).expanduser().resolve()
    if not directory.is_absolute() or not c["native_dir"].strip():
        raise ValueError("Indica un directorio de instalación")
    if not exe.is_file() or exe.name.lower() != "steamcmd.exe":
        raise ValueError("No se encontró steamcmd.exe")
    args = [str(exe), "+force_install_dir", str(directory), "+login", "anonymous",
            "+app_update", c["steam_app_id"]]
    if validate:
        args.append("validate")
    args.append("+quit")
    return args


class NativeProcess:
    """Managed interactive Windows console owned by this GUI session."""
    def __init__(self):
        self.process = None
        self.log = None
        self.directory = None
        self.lock = threading.Lock()

    def running(self):
        with self.lock:
            return self.process is not None and self.process.poll() is None

    def start(self, config, log_path=None):
        """Run the official .bat in a VISIBLE, interactive Windows console.

        A first-run admin-password prompt must be visible to the operator.
        This tracks the launched batch command process, not unrelated services.
        """
        if os.name != "nt":
            raise RuntimeError("El servidor nativo solo se puede iniciar en Windows")
        script = native_launcher_path(config)
        root = script.parent
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                raise RuntimeError("Ya existe una consola de servidor iniciada desde el panel")
            if self.log:
                self.log.close()
                self.log = None
            # cmd /d disables AutoRun; /c call executes only the trusted,
            # allowlisted batch filename from the configured server directory.
            self.process = subprocess.Popen(
                ["cmd.exe", "/d", "/c", "call", script.name],
                cwd=str(root), creationflags=subprocess.CREATE_NEW_CONSOLE)
            self.directory = root
            return self.process.pid

    def status(self):
        with self.lock:
            if self.process is None:
                return "No iniciado por este panel"
            rc = self.process.poll()
            return f"Consola activa · PID {self.process.pid}" if rc is None else f"Consola finalizada (código {rc})"

    def close_log_if_stopped(self):
        with self.lock:
            if self.process is not None and self.process.poll() is not None and self.log:
                self.log.close()
                self.log = None


def native_log_tail(path, limit=500):
    path = Path(path)
    if not path.is_file():
        return "Todavía no existe un log nativo."
    # Bound memory usage; read last 256 KiB only.
    with path.open("rb") as file:
        file.seek(0, 2)
        size = file.tell()
        file.seek(max(0, size - 262_144))
        data = file.read()
    return "\n".join(data.decode("utf-8", "replace").splitlines()[-limit:])
