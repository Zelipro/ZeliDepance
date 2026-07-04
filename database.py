import hashlib
import secrets
import sqlite3

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

        # Listes de depenses (meme principe que Version-3), rattachees a un
        # utilisateur. synced/supabase_id : meme convention que depenses.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS listes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                user_id INTEGER REFERENCES users(id),
                date_creation TEXT,
                synced INTEGER DEFAULT 0,
                supabase_id INTEGER DEFAULT NULL
            )
        """)

        conn.commit()

        # Migration: ajouter user_id a depenses si absent
        cur.execute("PRAGMA table_info(depenses)")
        cols = [r[1] for r in cur.fetchall()]
        if "user_id" not in cols:
            cur.execute("ALTER TABLE depenses ADD COLUMN user_id INTEGER REFERENCES users(id)")
            conn.commit()

        # Migration: colonnes de synchronisation Supabase (meme principe que Version-3)
        # synced : 0 = a envoyer, 1 = a jour, 2 = a supprimer sur le cloud
        if "synced" not in cols:
            cur.execute("ALTER TABLE depenses ADD COLUMN synced INTEGER DEFAULT 0")
        if "supabase_id" not in cols:
            cur.execute("ALTER TABLE depenses ADD COLUMN supabase_id INTEGER DEFAULT NULL")
        if "liste_id" not in cols:
            cur.execute("ALTER TABLE depenses ADD COLUMN liste_id INTEGER REFERENCES listes(id)")
        conn.commit()

        cur.execute("PRAGMA table_info(users)")
        user_cols = [r[1] for r in cur.fetchall()]
        if "synced" not in user_cols:
            cur.execute("ALTER TABLE users ADD COLUMN synced INTEGER DEFAULT 0")
        if "supabase_id" not in user_cols:
            cur.execute("ALTER TABLE users ADD COLUMN supabase_id INTEGER DEFAULT NULL")
        conn.commit()

        # Creer le compte admin si inexistant
        cur.execute("SELECT id, password_hash, salt FROM users WHERE username = 'Deg'")
        admin = cur.fetchone()
        if not admin:
            h, s = _hash("Deg")
            cur.execute(
                "INSERT INTO users (username, nom, password_hash, salt, role, is_approved) VALUES (?, ?, ?, ?, ?, ?)",
                ("Deg", "Deg", h, s, "admin", 1),
            )
            admin_id = cur.lastrowid
            cur.execute("UPDATE depenses SET user_id = ? WHERE user_id IS NULL", (admin_id,))
        else:
            admin_id, admin_hash, admin_salt = admin
            # Migre les comptes crees avec l'ancien mot de passe par defaut
            if _verify("Deg@2024", admin_hash, admin_salt):
                h, s = _hash("Deg")
                cur.execute("UPDATE users SET password_hash = ?, salt = ? WHERE id = ?", (h, s, admin_id))
            cur.execute("UPDATE depenses SET user_id = ? WHERE user_id IS NULL", (admin_id,))

        conn.commit()

        # Migration: les depenses purement locales (jamais synchronisees) sans
        # liste sont rangees dans une liste par defaut de leur proprietaire.
        # Celles deja liees au cloud (supabase_id) seront rattachees a leur
        # vraie liste lors de la prochaine restauration.
        cur.execute(
            "SELECT DISTINCT user_id FROM depenses "
            "WHERE liste_id IS NULL AND supabase_id IS NULL AND user_id IS NOT NULL"
        )
        for (owner_id,) in cur.fetchall():
            cur.execute(
                "SELECT id FROM listes WHERE user_id = ? AND nom = ? AND synced != 2",
                (owner_id, "Mes depenses"),
            )
            row = cur.fetchone()
            if row:
                default_liste_id = row[0]
            else:
                cur.execute(
                    "INSERT INTO listes (nom, user_id, date_creation, synced) VALUES (?, ?, datetime('now'), 0)",
                    ("Mes depenses", owner_id),
                )
                default_liste_id = cur.lastrowid
            cur.execute(
                "UPDATE depenses SET liste_id = ? WHERE user_id = ? AND liste_id IS NULL AND supabase_id IS NULL",
                (default_liste_id, owner_id),
            )

        conn.commit()


# ── Gestion des utilisateurs ───────────────────────────────────────────────

def create_user(username: str, nom: str, password: str) -> tuple:
    import supabase_sync

    if supabase_sync.check_username_taken(username):
        return False, "Ce nom d'utilisateur est deja pris (compte existant en ligne)."

    h, s = _hash(password)
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO users (username, nom, password_hash, salt) VALUES (?, ?, ?, ?)",
                (username, nom, h, s),
            )
            conn.commit()
        return True, "Compte cree. En attente d'approbation par l'administrateur."
    except sqlite3.IntegrityError:
        return False, "Ce nom d'utilisateur est deja pris."


def authenticate(username: str, password: str) -> dict:
    def _lookup():
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, username, nom, password_hash, salt, role, is_approved FROM users "
                "WHERE username = ? AND synced != 2",
                (username,),
            )
            return cur.fetchone()

    def _check(row):
        if not row:
            return None
        uid, uname, nom, h, s, role, approved = row
        if _verify(password, h, s):
            return {"id": uid, "username": uname, "nom": nom, "role": role, "is_approved": approved}
        return None

    user = _check(_lookup())
    if user is None:
        # Compte inconnu localement ou mot de passe refuse : le compte a pu
        # etre cree ou modifie sur un autre appareil — on rapatrie le cloud
        # puis on reessaie une fois.
        import supabase_sync
        supabase_sync.try_restore()
        user = _check(_lookup())
    return user


def get_all_users() -> list:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, nom, role, is_approved, created_at FROM users "
            "WHERE synced != 2 "
            "ORDER BY is_approved ASC, created_at DESC"
        )
        return [
            {"id": r[0], "username": r[1], "nom": r[2], "role": r[3],
             "is_approved": r[4], "created_at": r[5]}
            for r in cur.fetchall()
        ]


def approve_user(user_id: int, approved: bool) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET is_approved = ?, synced = 0 WHERE id = ?",
            (1 if approved else 0, user_id),
        )
        conn.commit()


def delete_user(user_id: int) -> None:
    """
    Supprime un utilisateur, ses listes et ses depenses :
    - Si jamais synchronise (supabase_id NULL) -> suppression directe
    - Sinon -> marque synced=2 (sera supprime sur Supabase a la prochaine sync)
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT supabase_id FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        if row and row[0] is not None:
            cur.execute("UPDATE users SET synced = 2 WHERE id = ?", (user_id,))
            cur.execute(
                "UPDATE depenses SET synced = 2 WHERE user_id = ? AND supabase_id IS NOT NULL",
                (user_id,),
            )
            cur.execute(
                "DELETE FROM depenses WHERE user_id = ? AND supabase_id IS NULL",
                (user_id,),
            )
            cur.execute(
                "UPDATE listes SET synced = 2 WHERE user_id = ? AND supabase_id IS NOT NULL",
                (user_id,),
            )
            cur.execute(
                "DELETE FROM listes WHERE user_id = ? AND supabase_id IS NULL",
                (user_id,),
            )
        else:
            cur.execute("DELETE FROM depenses WHERE user_id = ?", (user_id,))
            cur.execute("DELETE FROM listes WHERE user_id = ?", (user_id,))
            cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
        cur.execute("DELETE FROM user_preferences WHERE user_id = ?", (user_id,))
        conn.commit()


def change_password(user_id: int, old_password: str, new_password: str) -> tuple:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT password_hash, salt FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
    if not row or not _verify(old_password, row[0], row[1]):
        return False, "Mot de passe actuel incorrect."
    h, s = _hash(new_password)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET password_hash = ?, salt = ?, synced = 0 WHERE id = ?", (h, s, user_id))
        conn.commit()
    return True, "Mot de passe modifie avec succes."


def set_section_pin(user_id: int, pin: str) -> None:
    h, s = _hash(pin)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET section_pin_hash = ?, section_pin_salt = ?, synced = 0 WHERE id = ?",
            (h, s, user_id),
        )
        conn.commit()


def remove_section_pin(user_id: int) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET section_pin_hash = NULL, section_pin_salt = NULL, synced = 0 WHERE id = ?",
            (user_id,),
        )
        conn.commit()


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
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO user_preferences (user_id, wallpaper_path) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET wallpaper_path = ?",
            (user_id, path, path),
        )
        conn.commit()


# ── Listes de depenses ───────────────────────────────────────────────────────

def create_liste(nom: str, user_id: int) -> tuple:
    nom = (nom or "").strip()
    if not nom:
        return False, "Le nom de la liste ne peut pas etre vide."
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM listes WHERE user_id = ? AND nom = ? AND synced != 2",
            (user_id, nom),
        )
        if cur.fetchone():
            return False, "Vous avez deja une liste portant ce nom."
        cur.execute(
            "INSERT INTO listes (nom, user_id, date_creation, synced) VALUES (?, ?, datetime('now'), 0)",
            (nom, user_id),
        )
        conn.commit()
    return True, "Liste creee."


def get_listes(user_id: int) -> list:
    """Retourne les listes actives d'un utilisateur :
    [{id, nom, count, total}]"""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT l.id, l.nom,
                   COUNT(CASE WHEN d.synced != 2 THEN d.id END),
                   COALESCE(SUM(CASE WHEN d.synced != 2 THEN d.montant END), 0)
            FROM listes l
            LEFT JOIN depenses d ON d.liste_id = l.id
            WHERE l.user_id = ? AND l.synced != 2
            GROUP BY l.id, l.nom
            ORDER BY l.id DESC
            """,
            (user_id,),
        )
        return [
            {"id": r[0], "nom": r[1], "count": r[2], "total": float(r[3])}
            for r in cur.fetchall()
        ]


def get_liste_nom(liste_id: int) -> str:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT nom FROM listes WHERE id = ?", (liste_id,))
        row = cur.fetchone()
    return row[0] if row else ""


def delete_liste(liste_id: int) -> None:
    """
    Supprime une liste et ses depenses :
    - jamais synchronisee -> suppression directe
    - sinon -> marquee synced=2 (supprimee sur Supabase a la prochaine sync)
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT supabase_id FROM listes WHERE id = ?", (liste_id,))
        row = cur.fetchone()
        if row and row[0] is not None:
            cur.execute("UPDATE listes SET synced = 2 WHERE id = ?", (liste_id,))
            cur.execute(
                "UPDATE depenses SET synced = 2 WHERE liste_id = ? AND supabase_id IS NOT NULL",
                (liste_id,),
            )
            cur.execute(
                "DELETE FROM depenses WHERE liste_id = ? AND supabase_id IS NULL",
                (liste_id,),
            )
        else:
            cur.execute("DELETE FROM depenses WHERE liste_id = ?", (liste_id,))
            cur.execute("DELETE FROM listes WHERE id = ?", (liste_id,))
        conn.commit()


# ── Operations sur les depenses ──────────────────────────────────────────────

def add_depense(description: str, montant: float, categorie: str, date: str,
                user_id: int = None, liste_id: int = None) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO depenses (description, montant, categorie, date, user_id, liste_id, synced) "
            "VALUES (?, ?, ?, ?, ?, ?, 0)",
            (description, montant, categorie, date, user_id, liste_id),
        )
        conn.commit()


def get_depenses(user_id: int = None, liste_id: int = None) -> list:
    with get_connection() as conn:
        cur = conn.cursor()
        if liste_id is not None:
            rows = cur.execute(
                "SELECT id, description, montant, categorie, date FROM depenses "
                "WHERE liste_id = ? AND synced != 2 ORDER BY id DESC",
                (liste_id,),
            ).fetchall()
        elif user_id is not None:
            rows = cur.execute(
                "SELECT id, description, montant, categorie, date FROM depenses "
                "WHERE user_id = ? AND synced != 2 ORDER BY id DESC",
                (user_id,),
            ).fetchall()
        else:
            rows = cur.execute(
                "SELECT id, description, montant, categorie, date FROM depenses "
                "WHERE synced != 2 ORDER BY id DESC"
            ).fetchall()
    return rows


def update_depense(depense_id: int, description: str, montant: float, categorie: str, date: str) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE depenses SET description = ?, montant = ?, categorie = ?, date = ?, synced = 0 WHERE id = ?",
            (description, montant, categorie, date, depense_id),
        )
        conn.commit()


def delete_depense(depense_id: int) -> None:
    """
    Supprime une depense :
    - Si jamais synchronisee -> suppression directe
    - Sinon -> marquee synced=2 (sera supprimee sur Supabase a la sync)
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT supabase_id FROM depenses WHERE id = ?", (depense_id,))
        row = cur.fetchone()
        if row and row[0] is not None:
            cur.execute("UPDATE depenses SET synced = 2 WHERE id = ?", (depense_id,))
        else:
            cur.execute("DELETE FROM depenses WHERE id = ?", (depense_id,))
        conn.commit()


def calcul_total(user_id: int = None) -> float:
    with get_connection() as conn:
        cur = conn.cursor()
        if user_id is not None:
            cur.execute(
                "SELECT COALESCE(SUM(montant), 0) FROM depenses WHERE user_id = ? AND synced != 2",
                (user_id,),
            )
        else:
            cur.execute("SELECT COALESCE(SUM(montant), 0) FROM depenses WHERE synced != 2")
        result = cur.fetchone()
    return float(result[0]) if result else 0.0


def get_depenses_count(user_id: int = None) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        if user_id is not None:
            cur.execute(
                "SELECT COUNT(*) FROM depenses WHERE user_id = ? AND synced != 2",
                (user_id,),
            )
        else:
            cur.execute("SELECT COUNT(*) FROM depenses WHERE synced != 2")
        result = cur.fetchone()
    return result[0] if result else 0


def generate_pdf(file_path: str, user_id: int = None, user_nom: str = "",
                 liste_id: int = None, liste_nom: str = "") -> None:
    if liste_id is not None:
        depenses = get_depenses(liste_id=liste_id)
        total = sum(d[2] for d in depenses)
    else:
        depenses = get_depenses(user_id)
        total = calcul_total(user_id)

    doc = SimpleDocTemplate(file_path, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    titre = "Rapport des depenses"
    if liste_nom:
        titre += f" — {liste_nom}"
    elif user_nom:
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
