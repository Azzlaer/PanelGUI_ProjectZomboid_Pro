"""Safe local directory discovery for Project Zomboid on Windows and Linux."""
from __future__ import annotations
import os
from pathlib import Path


def candidate_data_directories(home=None, environ=None):
    """Look only at conventional paths; never crawl user drives or network shares."""
    env = dict(os.environ) if environ is None else environ
    user = Path(home).expanduser() if home is not None else Path.home()
    candidates = [
        user / "Zomboid",
        user / "Documents" / "Zomboid",
    ]
    if env.get("USERPROFILE"):
        candidates.append(Path(env["USERPROFILE"]) / "Zomboid")
    if env.get("ZOMBOID_DATA_DIR"):
        candidates.insert(0, Path(env["ZOMBOID_DATA_DIR"]))
    seen = set()
    results = []
    for path in candidates:
        normalized = path.expanduser().resolve()
        key = str(normalized).casefold()
        if key in seen:
            continue
        seen.add(key)
        if normalized.is_dir() and (normalized / "Server").is_dir():
            results.append(normalized)
    return results


def server_ini_files(data_dir):
    """Return .ini files only from the expected Server subfolder."""
    root = Path(data_dir).expanduser().resolve()
    target = root / "Server"
    if not target.is_dir():
        return []
    return sorted((p for p in target.glob("*.ini") if p.is_file() and not p.is_symlink()),
                  key=lambda p: p.name.casefold())
