"""Configuration and record management for the MelodyMine WebUI server.

Handles persistent config (~/.melodymine/config.json) and download
record tracking (~/Downloads/MelodyMine/.hidden_records.json).
"""

import json
import os
import threading
from pathlib import Path

# ── Constants ──────────────────────────────────────────────────────────

DOWNLOADS_DIR = Path.home() / "Downloads" / "MelodyMine"
RECORDS_FILE = DOWNLOADS_DIR / ".hidden_records.json"
CONFIG_FILE = Path.home() / ".melodymine" / "config.json"

DEFAULT_CONFIG: dict[str, str] = {
    "soulseek_username": "",
    "soulseek_password": "",
    "output_dir": "",
    "proxy": "",
}

# ── Locks ──────────────────────────────────────────────────────────────

_config_lock = threading.Lock()
_record_lock = threading.Lock()


# ── Config I/O ─────────────────────────────────────────────────────────

def _load_config() -> dict:
    """Load persistent config from ~/.melodymine/config.json."""
    if not CONFIG_FILE.exists():
        return dict(DEFAULT_CONFIG)
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        cfg = dict(DEFAULT_CONFIG)
        cfg.update({k: v for k, v in data.items() if k in DEFAULT_CONFIG})
        return cfg
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_CONFIG)


def _save_config(updates: dict) -> dict:
    """Merge *updates* into config and persist to disk. Returns new config."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    cfg = _load_config()
    cfg.update({k: v for k, v in updates.items() if k in DEFAULT_CONFIG})
    CONFIG_FILE.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return cfg


def get_soulseek_creds() -> tuple[str | None, str | None]:
    """Return (username, password) from stored config or env vars."""
    cfg = _load_config()
    user = cfg.get("soulseek_username") or os.getenv("SLSK_USERNAME") or None
    pwd = cfg.get("soulseek_password") or os.getenv("SLSK_PASSWORD") or None
    return user, pwd


# ── Records I/O ────────────────────────────────────────────────────────

def _load_hidden_set() -> set[str]:
    """Load the set of filenames hidden (removed) from the download list."""
    if not RECORDS_FILE.exists():
        return set()
    try:
        data = json.loads(RECORDS_FILE.read_text(encoding="utf-8"))
        return set(data.get("hidden", []))
    except (json.JSONDecodeError, OSError):
        return set()


def _save_hidden_set(hidden: set[str]) -> None:
    """Persist the hidden-filename set to disk."""
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    RECORDS_FILE.write_text(
        json.dumps({"hidden": sorted(hidden)}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
