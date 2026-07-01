# --- CONNECTION : Gestion de la connexion SQLite et initialisation BD ---

import sqlite3
import os
import sys


def get_app_dir() -> str:
    """
    Retourne le dossier de stockage de la base de données.
    Sur Android avec Flet, on utilise le dossier interne de l'app
    qui est toujours accessible sans permissions spéciales.
    """
    # Sur Android via Flet/serious_python, DATA_DIR est défini
    data_dir = os.environ.get("FLET_APP_STORAGE_DATA")
    if data_dir:
        os.makedirs(data_dir, exist_ok=True)
        return data_dir

    # Fallback PC/Linux
    if sys.platform == "linux" and (
        os.path.isdir("/storage/emulated/0") or os.path.isdir("/sdcard")
    ):
        # Android sans variable d'env → dossier interne app
        base = "/data/user/0/com.flet.zelidepance_v2/files"
    else:
        documents = os.path.join(os.path.expanduser("~"), "Documents")
        if not os.path.isdir(documents):
            documents = os.path.expanduser("~")
        base = os.path.join(documents, "ZeliDepance")

    os.makedirs(base, exist_ok=True)
    return base


DB_NAME = os.path.join(get_app_dir(), "depenses_v2.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS utilisateur (
                id INTEGER PRIMARY KEY,
                identifiant TEXT NOT NULL,
                password TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS listes_depenses (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                nom           TEXT NOT NULL UNIQUE,
                date_creation TEXT,
                synced        INTEGER DEFAULT 0,
                supabase_id   INTEGER DEFAULT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS depenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                liste_id    INTEGER NOT NULL,
                description TEXT,
                montant     REAL,
                categorie   TEXT,
                date        TEXT,
                synced      INTEGER DEFAULT 0,
                supabase_id INTEGER DEFAULT NULL,
                FOREIGN KEY (liste_id) REFERENCES listes_depenses(id)
                ON DELETE CASCADE
            )
        """)

        conn.commit()

        cur.execute("SELECT COUNT(*) FROM utilisateur")
        if cur.fetchone()[0] == 0:
            cur.execute(
                "INSERT INTO utilisateur (identifiant, password) VALUES (?, ?)",
                ("Deg", "Deg"),
            )
            conn.commit()
