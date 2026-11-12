"""Independent desktop features for PanelGUI Project Zomboid PRO."""
from __future__ import annotations
import json
import re
import sqlite3
from contextlib import closing
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PLAYER_RE = re.compile(r"^[A-Za-z0-9_.-]{1,32}$")
WORKSHOP_RE = re.compile(r"^[1-9][0-9]{4,19}$")
MOD_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
ROLES = {"admin", "moderator", "overseer", "gm", "observer", "none"}

def valid_player(name: str) -> str:
    name = name.strip()
    if not PLAYER_RE.fullmatch(name):
        raise ValueError("Jugador inválido: usa letras, números, _, . o - (máximo 32)")
    return name

def player_command(action: str, player: str, value: str = "") -> str:
    """Construct known PZ console commands; no arbitrary text injection in names."""
    name = valid_player(player)
    quoted = '"' + name + '"'
    if action in ("kickuser", "banuser", "unbanuser"):
        return f"{action} {quoted}"
    if action == "setaccesslevel":
        role = value.strip().lower()
        if role not in ROLES:
            raise ValueError("Nivel de acceso no permitido")
        return f"setaccesslevel {quoted} {role}"
    if action == "additem":
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*\.[A-Za-z][A-Za-z0-9_]*", value):
            raise ValueError("Formato de ítem esperado: Base.Axe")
        return f"additem {quoted} {value}"
    raise ValueError("Comando no permitido")

def parse_ini(text: str) -> dict[str, str]:
    data = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ";")) or "=" not in line:
            continue
        key, val = line.split("=", 1)
        data[key.strip()] = val.strip()
    return data

def replace_ini_keys(text: str, changes: dict[str, str]) -> str:
    """Preserve other lines and comments; append missing keys, reject duplicate keys."""
    if not changes:
        return text
    seen = set()
    out = []
    for line in text.splitlines(keepends=True):
        key = line.split("=", 1)[0].strip() if "=" in line else None
        if key in changes and not line.lstrip().startswith(("#", ";")):
            if key in seen:
                raise ValueError(f"Clave duplicada en server.ini: {key}")
            seen.add(key)
            ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
            out.append(key + "=" + changes[key] + ending)
        else:
            out.append(line)
    ending = "\r\n" if "\r\n" in text else "\n"
    for key, value in changes.items():
        if key not in seen:
            if out and not out[-1].endswith(("\n", "\r")):
                out.append(ending)
            out.append(key + "=" + value + ending)
    return "".join(out)

def parse_mod_pairs(workshop_text: str, mod_text: str) -> list[tuple[str, str]]:
    ws = [x.strip() for x in workshop_text.split(";") if x.strip()]
    mods = [x.strip() for x in mod_text.split(";") if x.strip()]
    if len(ws) != len(mods):
        raise ValueError("La cantidad de WorkshopItems y Mods debe coincidir")
    if len(set(ws)) != len(ws) or len(set(mods)) != len(mods):
        raise ValueError("Hay IDs duplicados")
    for wid, mid in zip(ws, mods):
        if not WORKSHOP_RE.fullmatch(wid) or not MOD_RE.fullmatch(mid):
            raise ValueError("ID Workshop o Mod inválido")
    return list(zip(ws, mods))

def safe_extract_plan(archive: Path, destination: Path):
    """Validate ZIP filenames BEFORE any future restore support is added."""
    import zipfile
    root = destination.resolve()
    with zipfile.ZipFile(archive) as z:
        files = z.infolist()
        if len(files) > 100_000:
            raise ValueError("Demasiados archivos")
        for item in files:
            name = item.filename.replace("\\", "/")
            parts = Path(name).parts
            if name.startswith("/") or ":" in name or ".." in parts:
                raise ValueError("ZIP contiene rutas inseguras")
            target = (root / name).resolve()
            if target != root and root not in target.parents:
                raise ValueError("ZIP sale del directorio de destino")
            # Unix symlinks are not allowed
            if (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("No se permiten enlaces simbólicos")
    return len(files)

class AuditStore:
    def __init__(self, filename):
        self.filename = str(filename)
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.filename, timeout=10)) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS audit (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              timestamp TEXT NOT NULL,
              kind TEXT NOT NULL,
              detail TEXT NOT NULL,
              success INTEGER NOT NULL
            )""")
            db.commit()

    def record(self, kind: str, detail: str, success=True):
        with closing(sqlite3.connect(self.filename, timeout=10)) as db:
            db.execute("INSERT INTO audit(timestamp,kind,detail,success) VALUES(?,?,?,?)",
                (datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 str(kind)[:80], str(detail)[:500], int(bool(success))))
            db.commit()

    def recent(self, limit=100):
        with closing(sqlite3.connect(self.filename, timeout=10)) as db:
            return db.execute(
                "SELECT timestamp,kind,detail,success FROM audit ORDER BY id DESC LIMIT ?",
                (max(1, min(int(limit), 1000)),)).fetchall()

def discord_webhook(url: str, title: str, message: str):
    """Webhook with no redirects; require Discord's official webhook hostname."""
    from urllib.parse import urlsplit
    from urllib.error import HTTPError
    endpoint = urlsplit(url.strip())
    if endpoint.scheme != "https" or endpoint.hostname not in ("discord.com", "discordapp.com"):
        raise ValueError("Se requiere URL HTTPS del webhook oficial Discord")
    if not endpoint.path.startswith("/api/webhooks/") or endpoint.username or endpoint.password:
        raise ValueError("Ruta de webhook inválida")
    payload = {"username": "Zomboid Manager PRO",
               "embeds": [{"title": str(title)[:200], "description": str(message)[:2000],
                           "color": 3394815}]}
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "PanelGUI-Zomboid/1.1"},
        method="POST")
    # urllib normally follows redirects. Restrict them to avoid leaking webhook URLs.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=8) as response:
            if response.status not in (200, 204):
                raise RuntimeError("Discord HTTP " + str(response.status))
    except HTTPError as exc:
        raise RuntimeError("Discord rechazó el envío (HTTP " + str(exc.code) + ")") from None
    return "Discord: enviado"
