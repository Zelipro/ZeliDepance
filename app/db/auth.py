# --- AUTH : Authentification utilisateur ---

from app.db.connection import get_connection


def check_login(identifiant: str, password: str) -> bool:
    """Vérifie les credentials utilisateur."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM utilisateur WHERE identifiant = ? AND password = ?",
            (identifiant, password),
        )
        return cur.fetchone() is not None
