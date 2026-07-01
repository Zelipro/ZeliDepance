# --- LISTES : Gestion des listes de dépenses ---

from datetime import datetime
from app.db.connection import get_connection


def create_liste(nom: str) -> None:
    """Crée une nouvelle liste — synced=0 par défaut (sera sync plus tard)."""
    date_creation = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO listes_depenses (nom, date_creation, synced) VALUES (?, ?, 0)",
            (nom, date_creation),
        )
        conn.commit()


def get_all_listes() -> list[tuple]:
    """Récupère toutes les listes actives (synced != 2)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, nom, date_creation FROM listes_depenses WHERE synced != 2 ORDER BY id DESC"
        )
        return cur.fetchall()


def delete_liste(liste_id: int) -> None:
    """
    Supprime une liste :
    - Si jamais synchronisée (supabase_id NULL) → suppression directe
    - Sinon → marquée synced=2 (sera supprimée sur Supabase à la prochaine sync)
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT supabase_id FROM listes_depenses WHERE id=?", (liste_id,))
        row = cur.fetchone()
        if row and row[0] is not None:
            # Marquer pour suppression cloud
            cur.execute(
                "UPDATE listes_depenses SET synced=2 WHERE id=?", (liste_id,)
            )
        else:
            # Jamais sync → suppression directe
            cur.execute("DELETE FROM listes_depenses WHERE id=?", (liste_id,))
        conn.commit()


def get_liste_name(liste_id: int) -> str:
    """Récupère le nom d'une liste par son ID."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT nom FROM listes_depenses WHERE id=?", (liste_id,))
        result = cur.fetchone()
        return result[0] if result else ""
