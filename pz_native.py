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
import codecs
import locale
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
    """Local Project Zomboid process with redirected stdin/stdout/stderr.

    No Windows console window is created. The app owns the process during the
    current GUI session. Thread callbacks must NOT directly manipulate Tk.
    """
    def __init__(self):
        self.process = None
        self.directory = None
        self.reader = None
        self.output_file = None
        self.lock = threading.RLock()

    def running(self):
        with self.lock:
            return self.process is not None and self.process.poll() is None

    @staticmethod
    def launch_arguments(script):
        """Use a trusted launcher filename from the allowlist and no shell=True."""
        return ["cmd.exe", "/d", "/c", "call", script.name]

    def start(self, config, log_path=None, on_output=None, on_exit=None):
        """Start server silently with bidirectional pipes and asynchronous output."""
        if os.name != "nt":
            raise RuntimeError("El controlador nativo solo puede usarse en Windows")
        script = native_launcher_path(config)
        root = script.parent
        with self.lock:
            if self.running():
                raise RuntimeError("Ya existe un servidor iniciado desde este panel")
            if self.output_file is not None:
                self.output_file.close()
                self.output_file = None
            log_file = Path(log_path) if log_path else None
            if log_file:
                log_file.parent.mkdir(parents=True, exist_ok=True)
                self.output_file = log_file.open("ab", buffering=0)
            try:
                # cmd.exe executes the allowlisted .bat from its own working dir.
                # CREATE_NO_WINDOW prevents creation of a separate CMD window.
                self.process = subprocess.Popen(
                    self.launch_arguments(script),
                    cwd=str(root),
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=0,
                    creationflags=subprocess.CREATE_NO_WINDOW)
            except Exception:
                if self.output_file:
                    self.output_file.close()
                    self.output_file = None
                raise
            self.directory = root
            process = self.process
            self.reader = threading.Thread(
                target=self._consume_output,
                args=(process, on_output, on_exit),
                name="pz-native-console-reader", daemon=True)
            self.reader.start()
            return process.pid

    def _consume_output(self, process, on_output, on_exit):
        """Drain stdout continuously even if the user is on another tab."""
        encoding = locale.getpreferredencoding(False) or "utf-8"
        decoder = codecs.getincrementaldecoder(encoding)(errors="replace")
        try:
            if process.stdout is not None:
                while True:
                    # Buffered streams may use read1; raw pipes use read.
                    data = process.stdout.read(4096)
                    if not data:
                        break
                    with self.lock:
                        writer = self.output_file if self.process is process else None
                        if writer:
                            writer.write(data)
                    text = decoder.decode(data)
                    if text and on_output:
                        on_output(text)
                tail = decoder.decode(b"", final=True)
                if tail and on_output:
                    on_output(tail)
            code = process.wait()
            if on_exit:
                on_exit(code)
        except (OSError, ValueError) as exc:
            if on_output:
                on_output("\n[Error leyendo la salida del servidor: " + str(exc) + "]\n")
        finally:
            if process.stdout is not None:
                process.stdout.close()
            with self.lock:
                if self.process is process and self.output_file:
                    self.output_file.close()
                    self.output_file = None

    def send(self, command):
        """Write one line to server stdin. Never log the user's input here."""
        if not isinstance(command, str) or not command.strip():
            raise ValueError("Escribe un comando o respuesta")
        if "\r" in command or "\n" in command or "\0" in command:
            raise ValueError("Se permite una sola línea")
        with self.lock:
            if not self.running() or self.process.stdin is None:
                raise RuntimeError("El servidor no está en ejecución")
            encoding = locale.getpreferredencoding(False) or "utf-8"
            self.process.stdin.write((command + "\r\n").encode(encoding, errors="replace"))
            self.process.stdin.flush()

    def status(self):
        with self.lock:
            if self.process is None:
                return "No iniciado por este panel"
            code = self.process.poll()
            return (f"Ejecutando PID {self.process.pid}" if code is None
                    else f"Finalizado (código {code})")

    def close_log_if_stopped(self):
        with self.lock:
            if self.process is not None and self.process.poll() is not None and self.output_file:
                self.output_file.close()
                self.output_file = None


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
