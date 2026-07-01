import datetime
import hashlib
import os
import secrets
import sqlite3
import uuid as uuidlib

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

DB_NAME = "depenses.db"


def set_db_path(path: str) -> None:
    global DB_NAME
    DB_NAME = path


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_NAME)


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _new_uuid() -> str:
    return str(uuidlib.uuid4())


def _hash(password: str, salt: str = None) -> tuple:
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return h, salt


def _verify(password: str, stored_hash: str, salt: str) -> bool:
    h, _ = _hash(password, salt)
    return h == stored_hash


def init_db() -> None:
    with get_connection() as conn:
        cur = conn.cursor()

        # Table originale preservee exactement
        cur.execute("""
            CREATE TABLE IF NOT EXISTS depenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT,
                montant REAL,
                categorie TEXT,
                date TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                nom TEXT,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                is_approved INTEGER DEFAULT 0,
                section_pin_hash TEXT,
                section_pin_salt TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INTEGER PRIMARY KEY,
                wallpaper_path TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS app_config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        conn.commit()

        # Migration: ajouter user_id a depenses si absent
        cur.execute("PRAGMA table_info(depenses)")
        cols = [r[1] for r in cur.fetchall()]
        if "user_id" not in cols:
            cur.execute("ALTER TABLE depenses ADD COLUMN user_id INTEGER REFERENCES users(id)")
            conn.commit()

        # Migration: colonnes de synchronisation Supabase
        for col_sql in ("uuid TEXT", "updated_at TEXT", "deleted INTEGER DEFAULT 0"):
            col_name = col_sql.split()[0]
            if col_name not in cols:
                cur.execute(f"ALTER TABLE depenses ADD COLUMN {col_sql}")
        conn.commit()

        cur.execute("PRAGMA table_info(users)")
        user_cols = [r[1] for r in cur.fetchall()]
        for col_sql in ("uuid TEXT", "updated_at TEXT", "deleted INTEGER DEFAULT 0"):
            col_name = col_sql.split()[0]
            if col_name not in user_cols:
                cur.execute(f"ALTER TABLE users ADD COLUMN {col_sql}")
        conn.commit()

        cur.execute("PRAGMA table_info(user_preferences)")
        pref_cols = [r[1] for r in cur.fetchall()]
        if "updated_at" not in pref_cols:
            cur.execute("ALTER TABLE user_preferences ADD COLUMN updated_at TEXT")
            conn.commit()

        # Backfill des uuid manquants (comptes/depenses crees avant la sync)
        now = _now()
        cur.execute("SELECT id FROM users WHERE uuid IS NULL")
        for (uid,) in cur.fetchall():
            cur.execute("UPDATE users SET uuid = ?, updated_at = ? WHERE id = ?", (_new_uuid(), now, uid))
        cur.execute("SELECT id FROM depenses WHERE uuid IS NULL")
        for (did,) in cur.fetchall():
            cur.execute("UPDATE depenses SET uuid = ?, updated_at = ? WHERE id = ?", (_new_uuid(), now, did))
        conn.commit()

        # Creer le compte admin si inexistant
        cur.execute("SELECT id, password_hash, salt FROM users WHERE username = 'Deg'")
        admin = cur.fetchone()
        if not admin:
            h, s = _hash("Deg")
            cur.execute(
                "INSERT INTO users (uuid, username, nom, password_hash, salt, role, is_approved, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (_new_uuid(), "Deg", "Deg", h, s, "admin", 1, now),
            )
            admin_id = cur.lastrowid
            cur.execute("UPDATE depenses SET user_id = ? WHERE user_id IS NULL", (admin_id,))
        else:
            admin_id, admin_hash, admin_salt = admin
            # Migre les comptes crees avec l'ancien mot de passe par defaut
            if _verify("Deg@2024", admin_hash, admin_salt):
                h, s = _hash("Deg")
                cur.execute("UPDATE users SET password_hash = ?, salt = ?, updated_at = ? WHERE id = ?", (h, s, now, admin_id))
            cur.execute("UPDATE depenses SET user_id = ? WHERE user_id IS NULL", (admin_id,))

        conn.commit()


# ── Gestion des utilisateurs ───────────────────────────────────────────────

def create_user(username: str, nom: str, password: str) -> tuple:
    import supabase_sync

    if supabase_sync.check_username_taken(username):
        return False, "Ce nom d'utilisateur est deja pris (compte existant en ligne)."

    h, s = _hash(password)
    now = _now()
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO users (uuid, username, nom, password_hash, salt, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (_new_uuid(), username, nom, h, s, now),
            )
            conn.commit()
            new_id = cur.lastrowid
        supabase_sync.push_user(new_id)
        return True, "Compte cree. En attente d'approbation par l'administrateur."
    except sqlite3.IntegrityError:
        return False, "Ce nom d'utilisateur est deja pris."


def authenticate(username: str, password: str) -> dict:
    def _lookup():
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, username, nom, password_hash, salt, role, is_approved FROM users "
                "WHERE username = ? AND (deleted IS NULL OR deleted = 0)",
                (username,),
            )
            return cur.fetchone()

    row = _lookup()
    if not row:
        import supabase_sync
        if supabase_sync.is_configured():
            supabase_sync.pull_and_merge()
            row = _lookup()

    if not row:
        return None
    uid, uname, nom, h, s, role, approved = row
    if _verify(password, h, s):
        return {"id": uid, "username": uname, "nom": nom, "role": role, "is_approved": approved}
    return None


def get_all_users() -> list:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, nom, role, is_approved, created_at FROM users "
            "WHERE deleted IS NULL OR deleted = 0 "
            "ORDER BY is_approved ASC, created_at DESC"
        )
        return [
            {"id": r[0], "username": r[1], "nom": r[2], "role": r[3],
             "is_approved": r[4], "created_at": r[5]}
            for r in cur.fetchall()
        ]


def approve_user(user_id: int, approved: bool) -> None:
    now = _now()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET is_approved = ?, updated_at = ? WHERE id = ?", (1 if approved else 0, now, user_id))
        conn.commit()
    import supabase_sync
    supabase_sync.push_user(user_id)


def delete_user(user_id: int) -> None:
    now = _now()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE user_preferences SET updated_at = ? WHERE user_id = ?", (now, user_id))
        cur.execute("UPDATE depenses SET deleted = 1, updated_at = ? WHERE user_id = ?", (now, user_id))
        cur.execute("UPDATE users SET deleted = 1, updated_at = ? WHERE id = ?", (now, user_id))
        conn.commit()
    import supabase_sync
    supabase_sync.push_user(user_id)


def change_password(user_id: int, old_password: str, new_password: str) -> tuple:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT password_hash, salt FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
    if not row or not _verify(old_password, row[0], row[1]):
        return False, "Mot de passe actuel incorrect."
    h, s = _hash(new_password)
    now = _now()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET password_hash = ?, salt = ?, updated_at = ? WHERE id = ?", (h, s, now, user_id))
        conn.commit()
    import supabase_sync
    supabase_sync.push_user(user_id)
    return True, "Mot de passe modifie avec succes."


def set_section_pin(user_id: int, pin: str) -> None:
    h, s = _hash(pin)
    now = _now()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET section_pin_hash = ?, section_pin_salt = ?, updated_at = ? WHERE id = ?",
            (h, s, now, user_id),
        )
        conn.commit()
    import supabase_sync
    supabase_sync.push_user(user_id)


def remove_section_pin(user_id: int) -> None:
    now = _now()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET section_pin_hash = NULL, section_pin_salt = NULL, updated_at = ? WHERE id = ?",
            (now, user_id),
        )
        conn.commit()
    import supabase_sync
    supabase_sync.push_user(user_id)


def verify_section_pin(user_id: int, pin: str) -> bool:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT section_pin_hash, section_pin_salt FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
    if not row or not row[0]:
        return False
    return _verify(pin, row[0], row[1])


def has_section_pin(user_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT section_pin_hash FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
    return row is not None and row[0] is not None


def get_wallpaper(user_id: int) -> str:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT wallpaper_path FROM user_preferences WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
    return row[0] if row else None


def set_wallpaper(user_id: int, path: str) -> None:
    now = _now()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO user_preferences (user_id, wallpaper_path, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET wallpaper_path = ?, updated_at = ?",
            (user_id, path, now, path, now),
        )
        conn.commit()
    import supabase_sync
    supabase_sync.push_preferences(user_id)


# ── Operations sur les depenses ──────────────────────────────────────────────

def add_depense(description: str, montant: float, categorie: str, date: str, user_id: int = None) -> None:
    now = _now()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO depenses (uuid, description, montant, categorie, date, user_id, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (_new_uuid(), description, montant, categorie, date, user_id, now),
        )
        conn.commit()
        new_id = cur.lastrowid
    import supabase_sync
    supabase_sync.push_depense(new_id)


def get_depenses(user_id: int = None) -> list:
    with get_connection() as conn:
        cur = conn.cursor()
        if user_id is not None:
            rows = cur.execute(
                "SELECT id, description, montant, categorie, date FROM depenses "
                "WHERE user_id = ? AND (deleted IS NULL OR deleted = 0) ORDER BY id DESC",
                (user_id,),
            ).fetchall()
        else:
            rows = cur.execute(
                "SELECT id, description, montant, categorie, date FROM depenses "
                "WHERE deleted IS NULL OR deleted = 0 ORDER BY id DESC"
            ).fetchall()
    return rows


def update_depense(depense_id: int, description: str, montant: float, categorie: str, date: str) -> None:
    now = _now()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE depenses SET description = ?, montant = ?, categorie = ?, date = ?, updated_at = ? WHERE id = ?",
            (description, montant, categorie, date, now, depense_id),
        )
        conn.commit()
    import supabase_sync
    supabase_sync.push_depense(depense_id)


def delete_depense(depense_id: int) -> None:
    now = _now()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE depenses SET deleted = 1, updated_at = ? WHERE id = ?", (now, depense_id))
        conn.commit()
    import supabase_sync
    supabase_sync.push_depense(depense_id)


def calcul_total(user_id: int = None) -> float:
    with get_connection() as conn:
        cur = conn.cursor()
        if user_id is not None:
            cur.execute(
                "SELECT COALESCE(SUM(montant), 0) FROM depenses "
                "WHERE user_id = ? AND (deleted IS NULL OR deleted = 0)",
                (user_id,),
            )
        else:
            cur.execute("SELECT COALESCE(SUM(montant), 0) FROM depenses WHERE deleted IS NULL OR deleted = 0")
        result = cur.fetchone()
    return float(result[0]) if result else 0.0


def get_depenses_count(user_id: int = None) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        if user_id is not None:
            cur.execute(
                "SELECT COUNT(*) FROM depenses WHERE user_id = ? AND (deleted IS NULL OR deleted = 0)",
                (user_id,),
            )
        else:
            cur.execute("SELECT COUNT(*) FROM depenses WHERE deleted IS NULL OR deleted = 0")
        result = cur.fetchone()
    return result[0] if result else 0


def generate_pdf(file_path: str, user_id: int = None, user_nom: str = "") -> None:
    depenses = get_depenses(user_id)
    total = calcul_total(user_id)

    doc = SimpleDocTemplate(file_path, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    titre = "Rapport des depenses"
    if user_nom:
        titre += f" — {user_nom}"
    elements.append(Paragraph(titre, styles["Title"]))
    elements.append(Spacer(1, 12))

    table_data = [["Description", "Montant", "Categorie", "Date"]]
    for _, description, montant, categorie, date in depenses:
        table_data.append([description, f"{montant:.2f}", categorie, date])

    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E7D32")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 14))
    elements.append(Paragraph(f"Total : {total:.2f}", styles["Heading3"]))
    doc.build(elements)
