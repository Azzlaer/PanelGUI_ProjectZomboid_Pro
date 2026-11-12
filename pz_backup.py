"""Verified backups, safe staging, rotation and lightweight scheduling helpers.

Only local paths. Restore ALWAYS stages to a NEW empty directory, never the live world.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath


MAX_FILES = 100_000
MAX_UNCOMPRESSED = 64 * 1024**3  # 64 GiB safety cap
MAX_RATIO = 10_000
MANIFEST = "_panelgui_backup_manifest.json"


def _validate_entry(info: zipfile.ZipInfo) -> Path:
    name = info.filename
    if not name or "\\" in name or name.startswith("/") or "\0" in name or ":" in name:
        raise ValueError("Nombre de archivo ZIP peligroso")
    parts = PurePosixPath(name).parts
    if not parts or "." in parts or ".." in parts:
        raise ValueError("ZIP con traversal de rutas")
    if info.flag_bits & 1:
        raise ValueError("Backups cifrados no soportados")
    mode = info.external_attr >> 16
    if mode & 0o170000 == 0o120000:
        raise ValueError("ZIP con enlace simbólico")
    if info.file_size > MAX_UNCOMPRESSED:
        raise ValueError("Entrada demasiado grande")
    if info.file_size and info.file_size > max(1, info.compress_size) * MAX_RATIO:
        raise ValueError("Relación de compresión sospechosa")
    return Path(*parts)


def inspect_backup(archive: str | Path, verify_crc: bool = True) -> dict:
    """Inspect the ZIP, verify CRC, and optionally verify our own SHA256 manifest."""
    archive = Path(archive)
    with zipfile.ZipFile(archive) as zf:
        info = zf.infolist()
        if len(info) > MAX_FILES:
            raise ValueError("Demasiados archivos en backup")
        total = 0
        seen = set()
        manifest = None
        for entry in info:
            rel = _validate_entry(entry)
            key = rel.as_posix().casefold()
            if key in seen:
                raise ValueError("Rutas duplicadas en el backup")
            seen.add(key)
            total += entry.file_size
            if total > MAX_UNCOMPRESSED:
                raise ValueError("Backup excede límite de 64 GiB")
        if MANIFEST in zf.namelist():
            manifest = json.loads(zf.read(MANIFEST))
            if manifest.get("format") != "panelgui-v2":
                raise ValueError("Manifest no compatible")
        elif verify_crc:
            # Older ZIP: CRC validation only, without SHA256.
            pass
        if verify_crc:
            if zf.testzip() is not None:
                raise ValueError("CRC incorrecto en backup")
            if manifest is not None:
                expected = manifest.get("sha256", {})
                if not isinstance(expected, dict):
                    raise ValueError("Manifest inválido")
                content_names = {x.filename for x in info if not x.is_dir()} - {MANIFEST}
                if set(expected) != content_names:
                    raise ValueError("Archivos faltantes o adicionales en el manifest")
                for name, digest in expected.items():
                    if not isinstance(digest, str) or len(digest) != 64:
                        raise ValueError("Hash inválido en manifest")
                    h = hashlib.sha256()
                    with zf.open(name) as stream:
                        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                            h.update(chunk)
                    if h.hexdigest() != digest:
                        raise ValueError("Hash SHA256 incorrecto: " + name)
        return {"files": sum(not x.is_dir() for x in info),
                "uncompressed_bytes": total, "hash_verified": bool(manifest and verify_crc)}


def create_verified_backup(source: str | Path, directory: str | Path) -> Path:
    """Create backup in a temporary file and rename only after integrity verification."""
    root = Path(source).expanduser().resolve()
    dest = Path(directory).expanduser().resolve()
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Carpeta de datos inexistente o inválida")
    if root == dest or root in dest.parents:
        raise ValueError("El directorio de backups debe estar fuera del directorio de datos")
    dest.mkdir(parents=True, exist_ok=True)
    output = dest / ("zomboid_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".zip")
    fd, temporary = tempfile.mkstemp(prefix=".pz-backup-", suffix=".tmp", dir=dest)
    os.close(fd)
    count = 0
    try:
        hashes = {}
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for file in sorted(root.rglob("*")):
                if file.is_symlink() or not file.is_file():
                    continue
                rel = file.relative_to(root).as_posix()
                if rel == MANIFEST:
                    raise ValueError("Ruta reservada para manifest de backup")
                # Prevent accidental backup of very large/unsafe files.
                if file.stat().st_size > MAX_UNCOMPRESSED:
                    raise ValueError("Archivo demasiado grande: " + rel)
                h = hashlib.sha256()
                with file.open("rb") as source_file, zf.open(rel, "w", force_zip64=True) as target:
                    for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
                        target.write(chunk)
                        h.update(chunk)
                hashes[rel] = h.hexdigest()
                count += 1
                if count > MAX_FILES:
                    raise ValueError("Se excedió el límite de archivos")
            manifest = {"format": "panelgui-v2", "created_at": datetime.now().isoformat(),
                        "sha256": hashes}
            zf.writestr(MANIFEST, json.dumps(manifest, ensure_ascii=False))
        inspect_backup(temporary)
        os.replace(temporary, output)
        return output
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def stage_restore(archive: str | Path, target: str | Path) -> dict:
    """Extract validated ZIP into a new empty directory outside the running server.

    Does NOT remove, overwrite or merge an existing world. No symlinks allowed.
    """
    directory = Path(target).expanduser().resolve()
    if directory.exists():
        raise FileExistsError("El destino ya existe. Selecciona una carpeta nueva.")
    info = inspect_backup(archive)
    directory.mkdir(parents=True)
    try:
        with zipfile.ZipFile(archive) as zf:
            for entry in zf.infolist():
                if entry.filename == MANIFEST:
                    continue
                rel = _validate_entry(entry)
                path = directory.joinpath(rel)
                if entry.is_dir():
                    path.mkdir(parents=True, exist_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(entry) as source, path.open("xb") as dest:
                        shutil.copyfileobj(source, dest, length=1024 * 1024)
        return info
    except Exception:
        shutil.rmtree(directory)
        raise


def prune_backups(directory: str | Path, keep: int = 7) -> int:
    """Remove only verified backup ZIPs generated by this application."""
    keep = int(keep)
    if not 1 <= keep <= 365:
        raise ValueError("Retención entre 1 y 365")
    folder = Path(directory).expanduser().resolve()
    if not folder.is_dir():
        return 0
    files = sorted(folder.glob("zomboid_*.zip"), key=lambda p: (p.stat().st_mtime_ns, p.name),
                   reverse=True)
    count = 0
    for file in files[keep:]:
        if file.is_file() and not file.is_symlink():
            # Only clean our own verified v2 backups, never arbitrary files.
            try:
                with zipfile.ZipFile(file) as zf:
                    manifest = json.loads(zf.read(MANIFEST))
                if manifest.get("format") != "panelgui-v2":
                    continue
            except (OSError, ValueError, KeyError, zipfile.BadZipFile):
                continue
            file.unlink()
            count += 1
    return count


def due_daily(now: datetime, last_date: str, hour: int) -> bool:
    """Pure scheduling predicate; app must be running and server stopped."""
    if not 0 <= int(hour) <= 23:
        raise ValueError("Hora fuera de rango")
    return now.hour >= int(hour) and now.date().isoformat() != last_date
