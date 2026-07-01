# --- PREFERENCES : Gestion des préférences utilisateur dans perso.db ---

import sqlite3
import os
from app.db.connection import get_app_dir

PERSO_DB = os.path.join(get_app_dir(), "perso.db")

DEFAULT_PRIMARY_COLOR = "#2E7D32"
DEFAULT_BG_COLOR = "#F4F7F9"
DEFAULT_BG_IMAGE = None


def get_perso_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(PERSO_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_preferences_db() -> None:
    """Initialise la base de données des préférences."""
    with get_perso_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()

        # Valeurs par défaut si absent
        defaults = {
            "primary_color": DEFAULT_PRIMARY_COLOR,
            "bg_color":      DEFAULT_BG_COLOR,
            "bg_image":      "",
        }
        for key, value in defaults.items():
            cur.execute(
                "INSERT OR IGNORE INTO preferences (key, value) VALUES (?, ?)",
                (key, value)
            )
        conn.commit()


def get_preference(key: str) -> str:
    """Récupère une préférence par sa clé."""
    with get_perso_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM preferences WHERE key=?", (key,))
        row = cur.fetchone()
        return row[0] if row else ""


def set_preference(key: str, value: str) -> None:
    """Enregistre une préférence."""
    with get_perso_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO preferences (key, value) VALUES (?, ?)",
            (key, value)
        )
        conn.commit()


def get_primary_color() -> str:
    return get_preference("primary_color") or DEFAULT_PRIMARY_COLOR


def get_bg_color() -> str:
    return get_preference("bg_color") or DEFAULT_BG_COLOR


def get_bg_image() -> str:
    return get_preference("bg_image") or ""


def set_primary_color(color: str) -> None:
    set_preference("primary_color", color)


def set_bg_color(color: str) -> None:
    set_preference("bg_color", color)


def set_bg_image(path: str) -> None:
    set_preference("bg_image", path)
