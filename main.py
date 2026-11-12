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
from pz_backup import (create_verified_backup, inspect_backup, stage_restore, prune_backups, due_daily)
from pz_native import ProfileStore, NativeProcess, native_log_tail, steamcmd_arguments, native_launcher_path, validate_profile, DEFAULT_PROFILE
from pz_features import (AuditStore, player_command, parse_ini, parse_mod_pairs,
                         replace_ini_keys, discord_webhook, safe_extract_plan)

ROOT = Path(os.getenv("APPDATA") or Path.home()) / "PanelGUI_ProjectZomboid_Pro"
ROOT.mkdir(parents=True, exist_ok=True)
CONFIG = ROOT / "config.json"
DEFAULT = dict(DEFAULT_PROFILE, backup_hour=3, backup_enabled=False, backup_last="", backup_keep=7,
               webhook="", container="pz-game-server", host="127.0.0.1", port=27015,
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
        self.audit = AuditStore(ROOT / "audit.sqlite3")
        self.profiles = ProfileStore(ROOT / "profiles")
        self.native_process = NativeProcess()
        self.native_log_path = ROOT / "native_server.log"
        self.title("PanelGUI Project Zomboid PRO | Desktop v1.3")
        self.geometry("1120x740")
        self.minsize(850, 580)
        self.configure(bg=BG)
        self.events = queue.Queue()
        self.active = None
        self.backup_busy = False
        self.status_busy = False
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
        self.build_players()
        self.build_mods()
        self.build_activity()
        self.build_logs()
        self.build_native()
        self.build_settings()
        self.build_profiles()
        self.output = tk.Text(self, height=7, bg="#0c1220", fg="#cddced", insertbackground="white",
                              relief="flat", wrap="word", font=("Consolas", 10))
        self.output.pack(fill="x", padx=18, pady=(0, 14))
        self.log("Listo. Configura Docker, RCON y rutas desde Ajustes.")
        self.after(100, self.consume)
        self.after(800, self.refresh_status)
        self.after(60_000, self.periodic)
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
                    self.audit.record("error", label, False)
                    if label == "Estado":
                        self.state_var.set("Docker: error")
                        self.status_busy = False
                    if label.startswith("Backup"):
                        self.backup_busy = False
                else:
                    self.log(label + ": " + str(result)[:1800])
                    if not label.startswith(("Estado", "Logs")):
                        self.audit.record("accion", label, True)
                    if label == "Estado":
                        self.status_busy = False
                    if label.startswith("Backup"):
                        self.backup_busy = False
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
        self.button(actions, "CPU / RAM", self.view_stats)
        self.button(actions, "Iniciar Windows nativo", self.native_start)
        self.status_text = tk.Text(page, bg=SURFACE, fg=FG, relief="flat", height=15,
                                   font=("Consolas", 11))
        self.status_text.pack(fill="both", expand=True, padx=12, pady=15)
    def refresh_status(self):
        if self.config_data.get("mode") == "native":
            value = self.native_process.status()
            self.state_var.set("Nativo: " + value)
            self.status_text.delete("1.0", "end")
            self.status_text.insert("1.0", value + "\nUsa Windows Nativo para administrar este proceso.")
            return
        if self.status_busy:
            return
        self.status_busy = True
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
        if self.config_data.get("mode") == "native":
            messagebox.showinfo("Modo nativo", "Controles Docker no aplicables en modo nativo")
            return
        if action in ("stop", "restart") and not messagebox.askyesno(
                "Confirmar", "¿Ejecutar " + action + " en el contenedor?"):
            return
        name = self.config_data["container"]
        self.submit("Docker " + action, lambda: docker(action, name, timeout=120),
                    lambda _: self.refresh_status())
    def view_logs(self):
        self.tabs.select(self.logs_page)
        self.refresh_logs()
    def view_stats(self):
        if self.config_data.get("mode") == "native":
            self.log("Métricas Docker no disponibles en modo nativo")
            return
        name = self.config_data["container"]
        self.submit("Recursos", lambda: docker("stats", "--no-stream",
                  "--format", "CPU={{.CPUPerc}} RAM={{.MemUsage}} NET={{.NetIO}}", name))
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
    def build_logs(self):
        page = self.tab("Logs")
        self.logs_page = page
        header = ttk.Frame(page)
        header.pack(fill="x", padx=12, pady=10)
        ttk.Label(header, text="Filtro").pack(side="left", padx=5)
        self.log_filter = tk.StringVar()
        ttk.Entry(header, textvariable=self.log_filter, width=32).pack(side="left", padx=5)
        self.button(header, "Recargar logs", self.refresh_logs)
        self.button(header, "Aplicar filtro", self.filter_logs)
        self.button(header, "Exportar visible", self.export_logs)
        self.logs_widget = tk.Text(page, bg=SURFACE, fg=FG, font=("Consolas", 10),
                                   wrap="none", relief="flat")
        self.logs_widget.pack(fill="both", expand=True, padx=12, pady=10)
        self.raw_logs = ""
    def refresh_logs(self):
        if self.config_data.get("mode") == "native":
            self.submit("Logs nativos", lambda: native_log_tail(self.native_log_path), self.on_logs)
            return
        name = self.config_data["container"]
        self.submit("Logs Docker", lambda: docker("logs", "--tail", "500", "--timestamps", name),
                    self.on_logs)
    def on_logs(self, content):
        self.raw_logs = content
        self.filter_logs()
    def filter_logs(self):
        needle = self.log_filter.get().casefold()
        rows = [line for line in self.raw_logs.splitlines() if needle in line.casefold()]
        self.logs_widget.delete("1.0", "end")
        self.logs_widget.insert("1.0", "\n".join(rows))
    def export_logs(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("TXT","*.txt")])
        if path:
            Path(path).write_text(self.logs_widget.get("1.0", "end-1c"), encoding="utf-8")
            self.log("Logs visibles exportados")
    def periodic(self):
        """Auto-refresh every minute; daily backup only with Docker container stopped."""
        if self.winfo_exists():
            self.native_process.close_log_if_stopped()
            self.refresh_status()
            c = self.config_data
            if c.get("backup_enabled") and not self.backup_busy:
                try:
                    if due_daily(datetime.now(), c.get("backup_last", ""), int(c["backup_hour"])):
                        self.scheduled_backup()
                except (ValueError, TypeError) as exc:
                    self.log("Programador: " + str(exc))
            self.after(60_000, self.periodic)
    def scheduled_backup(self):
        self.backup_busy = True
        c = self.config_data.copy()
        def job():
            if c.get("mode") != "docker":
                raise RuntimeError("Backup automático nativo no soportado. Usa backup manual con el servidor detenido.")
            state = json.loads(docker("inspect", "-f", "{{json .State}}", c["container"]))
            if state.get("Running"):
                raise RuntimeError("Backup programado omitido: detén el contenedor para un respaldo consistente")
            archive = create_verified_backup(c["data_dir"], c["backup_dir"])
            prune_backups(c["backup_dir"], int(c.get("backup_keep", 7)))
            return str(archive)
        def success(result):
            self.config_data["backup_last"] = datetime.now().date().isoformat()
            self.persist_settings()
        self.submit("Backup programado", job, success)
    def persist_settings(self):
        CONFIG.write_text(json.dumps(self.config_data, ensure_ascii=False, indent=2), encoding="utf-8")
    def build_backup(self):
        page = self.tab("Backups")
        ttk.Label(page, text="Respaldos manuales", font=("Segoe UI", 16, "bold")).pack(
            anchor="w", padx=12, pady=15)
        actions = ttk.Frame(page)
        actions.pack(anchor="w", padx=12)
        self.button(actions, "Crear backup ZIP", self.create_backup)
        self.button(actions, "Abrir carpeta de backups", self.open_backups)
        self.button(actions, "Verificar backup ZIP", self.verify_backup)
        self.button(actions, "Preparar restauración segura", self.restore_backup)
        self.button(actions, "Limpiar backups antiguos", self.cleanup_backups)
        ttk.Label(page, text="Para garantizar consistencia, detén el servidor antes de respaldar.\n"
                            "Restaurar prepara los archivos en una carpeta nueva, NUNCA sobrescribe el mundo activo.").pack(
            anchor="w", padx=12, pady=12)
    def create_backup(self):
        if not messagebox.askyesno("Copia de seguridad", "¿Confirmas que el servidor está detenido y deseas respaldarlo?"):
            return
        if self.backup_busy:
            self.log("Ya hay un backup en curso")
            return
        self.backup_busy = True
        c = self.config_data.copy()
        self.submit("Backup manual", lambda: str(create_verified_backup(c["data_dir"], c["backup_dir"])))
    def verify_backup(self):
        archive = filedialog.askopenfilename(filetypes=[("Backups ZIP", "*.zip")])
        if not archive:
            return
        try:
            self.submit("Verificar ZIP", lambda: inspect_backup(archive))
        except Exception as exc:
            messagebox.showerror("Verificar backup", str(exc))
    def restore_backup(self):
        archive = filedialog.askopenfilename(filetypes=[("Backups ZIP", "*.zip")])
        if not archive:
            return
        dest = filedialog.askdirectory(title="Selecciona carpeta PADRE para preparar restauración")
        if not dest:
            return
        folder = (Path(dest) / ("restore_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))).resolve()
        live = self.config_data.get("data_dir", "")
        if live:
            root = Path(live).expanduser().resolve()
            if root == folder or root in folder.parents or folder in root.parents:
                messagebox.showerror("Restauración", "El destino debe estar fuera de la carpeta del mundo activo")
                return
        if not messagebox.askyesno("Restauración protegida",
                f"Extraer backup validado en carpeta NUEVA:\n{folder}\n"
                "El mundo activo no será modificado. ¿Continuar?"):
            return
        self.submit("Restauración preparada", lambda: stage_restore(archive, folder))
    def cleanup_backups(self):
        if not messagebox.askyesno("Retención", "¿Eliminar copias antiguas verificadas, "
                                   "conservando el número configurado?"):
            return
        c = self.config_data.copy()
        self.submit("Retención backups", lambda: prune_backups(c["backup_dir"],
                                                              int(c.get("backup_keep", 7))))
    def open_backups(self):
        target = Path(self.config_data["backup_dir"]).expanduser()
        target.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(target)
        else:
            messagebox.showinfo("Carpeta", str(target))
    def build_players(self):
        page = self.tab("Jugadores")
        ttk.Label(page, text="Moderación vía RCON", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=12, pady=14)
        self.player_name = tk.StringVar()
        self.player_role = tk.StringVar(value="moderator")
        self.player_item = tk.StringVar(value="Base.Axe")
        row = ttk.Frame(page)
        row.pack(fill="x", padx=12, pady=5)
        ttk.Label(row, text="Usuario").pack(side="left", padx=5)
        ttk.Entry(row, textvariable=self.player_name, width=28).pack(side="left", padx=5)
        ttk.Label(row, text="Rol").pack(side="left", padx=5)
        ttk.Combobox(row, textvariable=self.player_role, values=[
            "admin", "moderator", "overseer", "gm", "observer", "none"
        ], state="readonly", width=13).pack(side="left", padx=5)
        row2 = ttk.Frame(page)
        row2.pack(fill="x", padx=12)
        self.button(row2, "Lista de jugadores", lambda: self.run_rcon_command("players"))
        self.button(row2, "Expulsar", lambda: self.player_action("kickuser"))
        self.button(row2, "Banear", lambda: self.player_action("banuser"))
        self.button(row2, "Desbanear", lambda: self.player_action("unbanuser"))
        self.button(row2, "Aplicar nivel", lambda: self.player_action("setaccesslevel", self.player_role.get()))
        row3 = ttk.Frame(page)
        row3.pack(fill="x", padx=12)
        ttk.Label(row3, text="ID del ítem").pack(side="left", padx=5)
        ttk.Entry(row3, textvariable=self.player_item, width=25).pack(side="left", padx=5)
        self.button(row3, "Entregar ítem", lambda: self.player_action("additem", self.player_item.get()))
        ttk.Label(page, text="Los comandos disponibles y los roles pueden variar según la versión del servidor.").pack(
            anchor="w", padx=12, pady=10)
    def player_action(self, action, value=""):
        try:
            command = player_command(action, self.player_name.get(), value)
        except ValueError as exc:
            messagebox.showerror("Validación", str(exc))
            return
        if action in ("banuser", "kickuser", "setaccesslevel", "additem") and not messagebox.askyesno(
                "Confirmación", "Ejecutar: " + command + " ?"):
            return
        self.run_rcon_command(command)
    def build_mods(self):
        page = self.tab("Workshop Mods")
        ttk.Label(page, text="Mods por parejas Workshop ID + Mod ID", font=("Segoe UI", 16, "bold")).pack(
            anchor="w", padx=12, pady=12)
        self.workshop_ids = tk.StringVar()
        self.mod_ids = tk.StringVar()
        for title, var in (("WorkshopItems (separados por ;)", self.workshop_ids),
                           ("Mods (separados por ;)", self.mod_ids)):
            ttk.Label(page, text=title).pack(anchor="w", padx=12, pady=(8, 2))
            ttk.Entry(page, textvariable=var).pack(fill="x", padx=12)
        row = ttk.Frame(page)
        row.pack(anchor="w", padx=12, pady=8)
        self.button(row, "Leer del server.ini", self.load_mods)
        self.button(row, "Validar parejas", self.validate_mods)
        self.button(row, "Guardar mods (con respaldo)", self.save_mods)
        ttk.Label(page, text="El ID numérico de Workshop NO siempre coincide con el Mod ID interno.\n"
                            "Se necesita reiniciar el servidor para aplicar los cambios.").pack(
            anchor="w", padx=12, pady=10)
    def load_mods(self):
        try:
            data = parse_ini(self.ini_path().read_text(encoding="utf-8-sig"))
            self.workshop_ids.set(data.get("WorkshopItems", ""))
            self.mod_ids.set(data.get("Mods", ""))
            self.log("IDs de mods cargados")
        except Exception as exc:
            messagebox.showerror("Mods", str(exc))
    def validate_mods(self):
        try:
            pairs = parse_mod_pairs(self.workshop_ids.get(), self.mod_ids.get())
            self.log("Mods validados: " + str(len(pairs)) + " parejas")
        except Exception as exc:
            messagebox.showerror("Mods", str(exc))
    def save_mods(self):
        try:
            pairs = parse_mod_pairs(self.workshop_ids.get(), self.mod_ids.get())
            if not messagebox.askyesno("Guardar mods", f"Guardar {len(pairs)} mods. Se creará respaldo del INI. ¿Continuar?"):
                return
            path = self.ini_path()
            original = path.read_text(encoding="utf-8-sig")
            updated = replace_ini_keys(original, {
                "WorkshopItems": ";".join(x[0] for x in pairs),
                "Mods": ";".join(x[1] for x in pairs)})
            bak = path.with_suffix(path.suffix + "." + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".bak")
            bak.write_text(original, encoding="utf-8")
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(updated, encoding="utf-8")
            os.replace(tmp, path)
            self.log("Mods guardados en INI. Reiniciar servidor. Respaldo: " + str(bak))
            self.audit.record("mods", str(len(pairs)) + " pares", True)
        except Exception as exc:
            messagebox.showerror("Guardar mods", str(exc))
    def build_activity(self):
        page = self.tab("Auditoría / Discord")
        ttk.Label(page, text="Auditoría local de acciones", font=("Segoe UI", 16, "bold")).pack(
            anchor="w", padx=12, pady=12)
        row = ttk.Frame(page)
        row.pack(anchor="w", padx=12)
        self.button(row, "Recargar historial", self.show_audit)
        self.button(row, "Enviar webhook de prueba", self.test_discord)
        self.audit_box = tk.Text(page, bg=SURFACE, fg=FG, relief="flat",
                                 font=("Consolas", 10))
        self.audit_box.pack(fill="both", expand=True, padx=12, pady=10)
        self.show_audit()
    def show_audit(self):
        self.audit_box.delete("1.0", "end")
        for stamp, kind, detail, success in self.audit.recent(100):
            self.audit_box.insert("end", f"{stamp} [{kind}] {detail} {'OK' if success else 'ERROR'}\n")
    def test_discord(self):
        endpoint = self.config_data.get("webhook", "").strip()
        if not endpoint:
            messagebox.showwarning("Discord", "Configura webhook en Ajustes")
            return
        self.submit("Test Discord", lambda: discord_webhook(
            endpoint, "Project Zomboid Manager PRO", "Prueba desde el panel de escritorio"))
    def build_native(self):
        page = self.tab("Windows Nativo")
        ttk.Label(page, text="Servidor dedicado Windows sin Docker",
                  font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=12, pady=14)
        bar = ttk.Frame(page)
        bar.pack(anchor="w", padx=12)
        self.button(bar, "Comprobar ruta", self.native_check)
        self.button(bar, "Iniciar servidor", self.native_start)
        self.button(bar, "Ver log", self.native_show_log)
        self.button(bar, "Instalar / actualizar", self.steamcmd_install)
        self.button(bar, "Validar SteamCMD", lambda: self.steamcmd_install(validate=True))
        ttk.Label(page, text="Selecciona modo native en Ajustes y configura el directorio de instalación.\n"
                  "Solo se supervisan procesos lanzados durante esta sesión.\n"
                  "Para detenerlo, utiliza los mecanismos oficiales del servidor; no se fuerza su cierre.\n"
                  "La instalación utiliza SteamCMD local ya instalado por el usuario.").pack(
                      anchor="w", padx=12, pady=14)
        self.native_status = tk.StringVar(value="Sin iniciar")
        ttk.Label(page, textvariable=self.native_status).pack(anchor="w", padx=12, pady=6)

    def native_check(self):
        try:
            script = native_launcher_path(self.config_data)
            self.native_status.set("Encontrado: " + str(script))
        except Exception as exc:
            messagebox.showerror("Comprobar instalación", str(exc))

    def native_start(self):
        if self.config_data.get("mode") != "native":
            messagebox.showwarning("Modo", "Selecciona native en Ajustes.")
            return
        if not messagebox.askyesno("Iniciar servidor", "¿Iniciar el servidor Windows de este perfil?"):
            return
        try:
            pid = self.native_process.start(self.config_data, self.native_log_path)
            self.native_status.set("Proceso lanzado con PID " + str(pid))
            self.audit.record("native_start", "PID " + str(pid))
            self.refresh_status()
        except Exception as exc:
            messagebox.showerror("Iniciar servidor", str(exc))

    def native_show_log(self):
        self.tabs.select(self.logs_page)
        self.refresh_logs()

    def steamcmd_install(self, validate=False):
        if self.config_data.get("mode") != "native":
            messagebox.showwarning("SteamCMD", "Selecciona native en Ajustes")
            return
        try:
            args = steamcmd_arguments(self.config_data, validate=validate)
        except Exception as exc:
            messagebox.showerror("SteamCMD", str(exc))
            return
        if self.native_process.running():
            messagebox.showerror("SteamCMD", "Detén el servidor antes de actualizar.")
            return
        action = "validar" if validate else "instalar/actualizar"
        if not messagebox.askyesno("Confirmar SteamCMD",
                f"¿{action} el servidor en {self.config_data['native_dir']}? "
                "SteamCMD descargará archivos y puede modificar la instalación."):
            return
        def job():
            proc = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True,
                                  text=True, errors="replace", timeout=3600)
            if proc.returncode:
                raise RuntimeError(f"SteamCMD falló ({proc.returncode}): " +
                                   (proc.stderr or proc.stdout)[-1500:])
            return "SteamCMD finalizó. Verifica los archivos instalados."
        self.submit("SteamCMD", job)

    def build_profiles(self):
        page = self.tab("Perfiles")
        ttk.Label(page, text="Perfiles de servidores", font=("Segoe UI", 16, "bold")).pack(
            anchor="w", padx=12, pady=14)
        row = ttk.Frame(page)
        row.pack(fill="x", padx=12)
        self.profile_name = tk.StringVar(value="Principal")
        self.profile_combo = ttk.Combobox(row, textvariable=self.profile_name, width=28)
        self.profile_combo.pack(side="left", padx=5)
        self.button(row, "Guardar perfil", self.save_profile)
        self.button(row, "Cargar perfil", self.load_profile)
        self.button(row, "Actualizar", self.refresh_profiles)
        ttk.Label(page, text="Los perfiles NO guardan contraseñas ni webhooks.\n"
                  "Al cargar otro perfil se limpian las credenciales activas.\n"
                  "Guarda los Ajustes primero y revisa las rutas antes de iniciar.").pack(
                      anchor="w", padx=12, pady=15)
        self.refresh_profiles()

    def refresh_profiles(self):
        self.profile_combo.configure(values=self.profiles.names())

    def save_profile(self):
        try:
            values = self.read_settings()
            path = self.profiles.save(self.profile_name.get(), values)
            self.log("Perfil guardado: " + str(path))
            self.refresh_profiles()
        except Exception as exc:
            messagebox.showerror("Perfil", str(exc))

    def load_profile(self):
        if self.native_process.running():
            messagebox.showerror("Perfil", "No cambies de perfil con un proceso nativo activo.")
            return
        try:
            values = self.profiles.load(self.profile_name.get())
            values["password"] = ""
            values["webhook"] = ""
            self.config_data = {**DEFAULT, **values}
            self.persist_settings()
            for key, var in self.fields.items():
                var.set(str(self.config_data.get(key, "")))
            self.log("Perfil cargado. Reintroduce credenciales RCON/Discord.")
            self.refresh_status()
        except Exception as exc:
            messagebox.showerror("Perfil", str(exc))

    def build_settings(self):
        page = self.tab("Ajustes")
        self.fields = {}
        labels = dict(mode="Modo (docker / native)", native_dir="Carpeta servidor Windows",
                      native_launcher="Lanzador (StartServer64.bat)", steamcmd_exe="Ruta steamcmd.exe",
                      steam_app_id="Steam App ID servidor", backup_enabled="Backup diario (true / false)", backup_hour="Hora backup diario (0-23)",
                      backup_keep="Cantidad de copias a conservar", webhook="Discord webhook HTTPS", container="Nombre contenedor Docker", host="RCON host",
                      port="RCON puerto", password="RCON contraseña",
                      data_dir="Carpeta local de datos Project Zomboid",
                      ini_file="Ruta de server.ini", backup_dir="Carpeta de backups")
        for key, label in labels.items():
            line = ttk.Frame(page)
            line.pack(fill="x", padx=12, pady=6)
            ttk.Label(line, text=label, width=38).pack(side="left")
            var = tk.StringVar(value=str(self.config_data.get(key, "")))
            ttk.Entry(line, textvariable=var, show="*" if key in ("password", "webhook") else "").pack(
                side="left", fill="x", expand=True)
            self.fields[key] = var
        ttk.Button(page, text="Guardar ajustes", command=self.save_settings).pack(anchor="w", padx=12, pady=16)
        ttk.Label(page, text="Las credenciales se guardan localmente SIN cifrado. No compartas config.json.").pack(
            anchor="w", padx=12, pady=5)
    def read_settings(self):
        values = {k: v.get().strip() for k, v in self.fields.items()}
        values["backup_last"] = self.config_data.get("backup_last", "")
        values["backup_enabled"] = str(values["backup_enabled"]).lower() in ("true", "1", "yes", "si")
        return validate_profile(values)
    def save_settings(self):
        try:
            values = self.read_settings()
            self.config_data = values
            self.persist_settings()
            self.log("Configuración guardada en " + str(CONFIG))
            self.audit.record("configuracion", "ajustes guardados", True)
        except Exception as exc:
            messagebox.showerror("Ajustes", str(exc))

if __name__ == "__main__":
    Application().mainloop()
