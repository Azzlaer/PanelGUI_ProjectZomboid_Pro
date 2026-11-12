"""PanelGUI Project Zomboid PRO - Windows desktop manager. Python 3.10+."""
import json
import os
import queue
import shutil
import socket
import struct
import subprocess
import threading
import tkinter as tk
import zipfile
from datetime import datetime
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

ROOT = Path(os.getenv("APPDATA") or Path.home()) / "PanelGUI_ProjectZomboid_Pro"
ROOT.mkdir(parents=True, exist_ok=True)
CONFIG = ROOT / "config.json"
DEFAULT = dict(container="pz-game-server", host="127.0.0.1", port=27015,
               password="", data_dir="", ini_file="", backup_dir=str(ROOT / "backups"))
BG, SURFACE, FG, ACCENT = "#101827", "#1a283a", "#e8f0f8", "#4daee8"

def load_config():
    try:
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
        return {**DEFAULT, **{k: v for k, v in data.items() if k in DEFAULT}}
    except (OSError, ValueError):
        return DEFAULT.copy()

def docker(*args, timeout=30):
    if not shutil.which("docker"):
        raise RuntimeError("Docker no está instalado o no está en PATH.")
    proc = subprocess.run(["docker", *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)
    if proc.returncode:
        raise RuntimeError((proc.stderr or proc.stdout).strip()[:1000])
    return proc.stdout.strip()

def recv_exact(sock, n):
    buf = bytearray()
    while len(buf) < n:
        part = sock.recv(n - len(buf))
        if not part:
            raise ConnectionError("RCON desconectado")
        buf.extend(part)
    return bytes(buf)

def rcon(host, port, password, cmd):
    """Source RCON over TCP. Never expose RCON directly to the public Internet."""
    def pack(req_id, kind, value):
        raw = value.encode("utf-8")
        return struct.pack("<iii", len(raw)+10, req_id, kind) + raw + b"\0\0"
    def read(sock):
        n = struct.unpack("<i", recv_exact(sock, 4))[0]
        if n < 10 or n > 4 * 1024 * 1024:
            raise RuntimeError("Tamaño de paquete RCON inválido")
        raw = recv_exact(sock, n)
        rid, typ = struct.unpack("<ii", raw[:8])
        return rid, typ, raw[8:-2].decode("utf-8", "replace")
    with socket.create_connection((host, int(port)), timeout=6) as s:
        s.settimeout(5)
        s.sendall(pack(10, 3, password))
        for _ in range(3):
            rid, typ, value = read(s)
            if rid == -1:
                raise PermissionError("Contraseña RCON incorrecta")
            if rid == 10 and typ == 2:
                break
        else:
            raise RuntimeError("El servidor no confirmó la autenticación RCON")
        s.sendall(pack(11, 2, cmd) + pack(12, 0, ""))
        parts = []
        for _ in range(40):
            rid, typ, value = read(s)
            if rid == 12:
                break
            if rid == 11:
                parts.append(value)
        return "".join(parts) or "(Sin respuesta)"

def backup_directory(source, dest):
    root = Path(source).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("Configura una carpeta de datos válida")
    target = Path(dest).expanduser().resolve()
    if root == target or root in target.parents:
        raise ValueError("Los backups deben estar fuera del directorio de datos")
    target.mkdir(parents=True, exist_ok=True)
    filename = target / ("zomboid_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".zip")
    with zipfile.ZipFile(filename, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for file in root.rglob("*"):
            if file.is_file() and not file.is_symlink():
                z.write(file, file.relative_to(root))
    return filename

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.config_data = load_config()
        self.title("PanelGUI Project Zomboid PRO | Desktop v1.0")
        self.geometry("1120x740")
        self.minsize(850, 580)
        self.configure(bg=BG)
        self.events = queue.Queue()
        self.active = None
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure(".", background=BG, foreground=FG, font=("Segoe UI", 10))
        self.style.configure("TFrame", background=BG)
        self.style.configure("TLabel", background=BG, foreground=FG)
        self.style.configure("TButton", background=SURFACE, foreground=FG, padding=9)
        self.style.map("TButton", background=[("active", "#2d4560")])
        self.style.configure("TEntry", fieldbackground=SURFACE, foreground=FG)
        self.style.configure("TNotebook", background=BG)
        self.style.configure("TNotebook.Tab", background=SURFACE, foreground=FG, padding=(15,10))
        self.style.map("TNotebook.Tab", background=[("selected", "#285779")])
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=18, pady=(18, 8))
        tk.Label(header, text="PROJECT ZOMBOID  /  MANAGER PRO", font=("Segoe UI", 19, "bold"),
                 fg=ACCENT, bg=BG).pack(side="left")
        self.state_var = tk.StringVar(value="Sin comprobar")
        tk.Label(header, textvariable=self.state_var, fg="#7ed4ad", bg=BG).pack(side="right")
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=18, pady=10)
        self.build_dashboard()
        self.build_rcon()
        self.build_editor()
        self.build_backup()
        self.build_settings()
        self.output = tk.Text(self, height=7, bg="#0c1220", fg="#cddced", insertbackground="white",
                              relief="flat", wrap="word", font=("Consolas", 10))
        self.output.pack(fill="x", padx=18, pady=(0, 14))
        self.log("Listo. Configura Docker, RCON y rutas desde Ajustes.")
        self.after(100, self.consume)
        self.after(800, self.refresh_status)
    def log(self, value):
        self.output.insert("end", datetime.now().strftime("[%H:%M:%S] ") + str(value) + "\n")
        self.output.see("end")
    def submit(self, label, fn, callback=None):
        def worker():
            try:
                result = fn()
                self.events.put(("ok", label, result, callback))
            except Exception as exc:
                self.events.put(("error", label, str(exc), None))
        threading.Thread(target=worker, daemon=True).start()
    def consume(self):
        try:
            while True:
                kind, label, result, callback = self.events.get_nowait()
                if kind == "error":
                    self.log("ERROR " + label + ": " + result)
                else:
                    self.log(label + ": " + str(result)[:1800])
                    if callback:
                        callback(result)
        except queue.Empty:
            pass
        self.after(100, self.consume)
    def button(self, parent, title, func):
        ttk.Button(parent, text=title, command=func).pack(side="left", padx=5, pady=8)
    def tab(self, title):
        parent = ttk.Frame(self.tabs)
        self.tabs.add(parent, text=title)
        return parent
    def build_dashboard(self):
        page = self.tab("Dashboard")
        ttk.Label(page, text="Control de servidor Docker", font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=12, pady=16)
        actions = ttk.Frame(page)
        actions.pack(anchor="w", padx=12)
        self.button(actions, "Actualizar estado", self.refresh_status)
        self.button(actions, "Iniciar", lambda: self.container_action("start"))
        self.button(actions, "Detener", lambda: self.container_action("stop"))
        self.button(actions, "Reiniciar", lambda: self.container_action("restart"))
        self.button(actions, "Guardar mundo (RCON)", lambda: self.run_rcon_command("save"))
        self.button(actions, "Ver logs", self.view_logs)
        self.status_text = tk.Text(page, bg=SURFACE, fg=FG, relief="flat", height=15,
                                   font=("Consolas", 11))
        self.status_text.pack(fill="both", expand=True, padx=12, pady=15)
    def refresh_status(self):
        name = self.config_data["container"]
        self.submit("Estado", lambda: docker("inspect", "-f", "{{json .State}}", name),
                    self.show_status)
    def show_status(self, raw):
        obj = json.loads(raw)
        state = obj.get("Status", "?")
        self.state_var.set("Docker: " + state)
        self.status_text.delete("1.0", "end")
        self.status_text.insert("end", json.dumps(obj, indent=2, ensure_ascii=False))
    def container_action(self, action):
        if action in ("stop", "restart") and not messagebox.askyesno(
                "Confirmar", "¿Ejecutar " + action + " en el contenedor?"):
            return
        name = self.config_data["container"]
        self.submit("Docker " + action, lambda: docker(action, name, timeout=120),
                    lambda _: self.refresh_status())
    def view_logs(self):
        name = self.config_data["container"]
        self.submit("Logs Docker", lambda: docker("logs", "--tail", "120", name))
    def build_rcon(self):
        page = self.tab("Consola RCON")
        ttk.Label(page, text="Comandos administrativos del servidor", font=("Segoe UI", 16, "bold")).pack(
            anchor="w", padx=12, pady=15)
        self.command = tk.StringVar(value="players")
        entry = ttk.Entry(page, textvariable=self.command)
        entry.pack(fill="x", padx=12)
        entry.bind("<Return>", lambda e: self.run_rcon_command())
        actions = ttk.Frame(page)
        actions.pack(anchor="w", padx=12)
        self.button(actions, "Enviar comando", self.run_rcon_command)
        self.button(actions, "Jugadores", lambda: self.run_rcon_command("players"))
        self.button(actions, "Guardar", lambda: self.run_rcon_command("save"))
        self.button(actions, "Ayuda", lambda: self.run_rcon_command("help"))
        ttk.Label(page, text="RCON debe ser accesible desde tu PC. No publiques su puerto en Internet.").pack(
            anchor="w", padx=12, pady=8)
    def run_rcon_command(self, command=None):
        cmd = command or self.command.get().strip()
        if not cmd:
            return
        c = self.config_data
        self.submit("RCON > " + cmd, lambda: rcon(c["host"], c["port"], c["password"], cmd))
    def build_editor(self):
        page = self.tab("Configuración y Mods")
        row = ttk.Frame(page)
        row.pack(fill="x", padx=12, pady=10)
        self.button(row, "Abrir server.ini", self.open_ini)
        self.button(row, "Guardar cambios", self.save_ini)
        ttk.Label(page, text="Editor de texto: WorkshopItems y Mods pueden modificarse en el mismo INI.").pack(
            anchor="w", padx=12, pady=4)
        self.editor = tk.Text(page, bg=SURFACE, fg=FG, insertbackground=FG, undo=True,
                              font=("Consolas", 10), relief="flat")
        self.editor.pack(fill="both", expand=True, padx=12, pady=10)
    def ini_path(self):
        path = Path(self.config_data["ini_file"]).expanduser()
        if not path.is_file():
            raise ValueError("Selecciona un server.ini válido en Ajustes")
        return path
    def open_ini(self):
        try:
            path = self.ini_path()
            content = path.read_text(encoding="utf-8-sig")
            self.editor.delete("1.0", "end")
            self.editor.insert("1.0", content)
            self.log("Cargado " + str(path))
        except Exception as exc:
            messagebox.showerror("INI", str(exc))
    def save_ini(self):
        try:
            path = self.ini_path()
            if not messagebox.askyesno("Guardar", "Se hará copia .bak antes de sobrescribir server.ini. ¿Continuar?"):
                return
            original = path.read_bytes()
            bak = path.with_suffix(path.suffix + "." + datetime.now().strftime("%Y%m%d_%H%M%S") + ".bak")
            bak.write_bytes(original)
            temporary = path.with_suffix(path.suffix + ".tmp")
            temporary.write_text(self.editor.get("1.0", "end-1c"), encoding="utf-8")
            os.replace(temporary, path)
            self.log("INI guardado. Reinicia el servidor para aplicar cambios. Respaldo: " + str(bak))
        except Exception as exc:
            messagebox.showerror("Guardar INI", str(exc))
    def build_backup(self):
        page = self.tab("Backups")
        ttk.Label(page, text="Respaldos manuales", font=("Segoe UI", 16, "bold")).pack(
            anchor="w", padx=12, pady=15)
        actions = ttk.Frame(page)
        actions.pack(anchor="w", padx=12)
        self.button(actions, "Crear backup ZIP", self.create_backup)
        self.button(actions, "Abrir carpeta de backups", self.open_backups)
        ttk.Label(page, text="Para garantizar consistencia, detén el servidor antes de respaldar.\n"
                            "Esta versión no restaura automáticamente ni elimina archivos del mundo.").pack(
            anchor="w", padx=12, pady=12)
    def create_backup(self):
        if not messagebox.askyesno("Copia de seguridad", "¿Confirmas que el servidor está detenido y deseas respaldarlo?"):
            return
        c = self.config_data
        self.submit("Backup", lambda: backup_directory(c["data_dir"], c["backup_dir"]))
    def open_backups(self):
        target = Path(self.config_data["backup_dir"]).expanduser()
        target.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(target)
        else:
            messagebox.showinfo("Carpeta", str(target))
    def build_settings(self):
        page = self.tab("Ajustes")
        self.fields = {}
        labels = dict(container="Nombre contenedor Docker", host="RCON host",
                      port="RCON puerto", password="RCON contraseña",
                      data_dir="Carpeta local de datos Project Zomboid",
                      ini_file="Ruta de server.ini", backup_dir="Carpeta de backups")
        for key, label in labels.items():
            line = ttk.Frame(page)
            line.pack(fill="x", padx=12, pady=6)
            ttk.Label(line, text=label, width=38).pack(side="left")
            var = tk.StringVar(value=str(self.config_data.get(key, "")))
            ttk.Entry(line, textvariable=var, show="*" if key == "password" else "").pack(
                side="left", fill="x", expand=True)
            self.fields[key] = var
        ttk.Button(page, text="Guardar ajustes", command=self.save_settings).pack(anchor="w", padx=12, pady=16)
        ttk.Label(page, text="Las credenciales se guardan localmente SIN cifrado. No compartas config.json.").pack(
            anchor="w", padx=12, pady=5)
    def save_settings(self):
        try:
            values = {k: v.get().strip() for k, v in self.fields.items()}
            values["port"] = int(values["port"])
            if not 1 <= values["port"] <= 65535:
                raise ValueError("Puerto fuera de rango")
            if not values["container"]:
                raise ValueError("Indica el nombre del contenedor")
            CONFIG.write_text(json.dumps(values, indent=2, ensure_ascii=False), encoding="utf-8")
            self.config_data = values
            self.log("Configuración guardada en " + str(CONFIG))
        except Exception as exc:
            messagebox.showerror("Ajustes", str(exc))

if __name__ == "__main__":
    Application().mainloop()
