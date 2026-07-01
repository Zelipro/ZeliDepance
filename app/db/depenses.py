# --- DEPENSES : Gestion des dépenses ---

from app.db.connection import get_connection


def add_depense(liste_id: int, description: str, montant: float, categorie: str, date: str) -> None:
    """Ajoute une dépense — synced=0 (sera sync plus tard)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO depenses (liste_id, description, montant, categorie, date, synced)
               VALUES (?, ?, ?, ?, ?, 0)""",
            (liste_id, description, montant, categorie, date),
        )
        conn.commit()


def get_depenses_by_liste(liste_id: int) -> list[tuple]:
    """Récupère toutes les dépenses actives d'une liste (synced != 2)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, description, montant, categorie, date FROM depenses
               WHERE liste_id=? AND synced != 2 ORDER BY id DESC""",
            (liste_id,),
        )
        return cur.fetchall()


def get_depenses_by_annee(annee: int) -> list[tuple]:
    """Récupère toutes les dépenses actives d'une année."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, liste_id, description, montant, categorie, date FROM depenses
               WHERE SUBSTR(date, 1, 4)=? AND synced != 2 ORDER BY date DESC""",
            (str(annee),),
        )
        return cur.fetchall()


def update_depense(depense_id: int, description: str, montant: float, categorie: str, date: str) -> None:
    """
    Met à jour une dépense et la marque synced=0 pour resynchronisation.
    Sur Supabase, la mise à jour sera gérée via update_depense_supabase.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """UPDATE depenses SET description=?, montant=?, categorie=?, date=?, synced=0
               WHERE id=?""",
            (description, montant, categorie, date, depense_id),
        )
        conn.commit()


def delete_depense(depense_id: int) -> None:
    """
    Supprime une dépense :
    - Si jamais synchronisée → suppression directe
    - Sinon → marquée synced=2 (sera supprimée sur Supabase à la sync)
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT supabase_id FROM depenses WHERE id=?", (depense_id,))
        row = cur.fetchone()
        if row and row[0] is not None:
            cur.execute("UPDATE depenses SET synced=2 WHERE id=?", (depense_id,))
        else:
            cur.execute("DELETE FROM depenses WHERE id=?", (depense_id,))
        conn.commit()


def calcul_total_liste(liste_id: int) -> float:
    """Calcule le total des dépenses actives d'une liste."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT COALESCE(SUM(montant), 0) FROM depenses WHERE liste_id=? AND synced != 2",
            (liste_id,),
        )
        result = cur.fetchone()
        return float(result[0]) if result else 0.0


def calcul_total_annee(annee: int) -> float:
    """Calcule le total des dépenses actives d'une année."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT COALESCE(SUM(montant), 0) FROM depenses
               WHERE SUBSTR(date, 1, 4)=? AND synced != 2""",
            (str(annee),),
        )
        result = cur.fetchone()
        return float(result[0]) if result else 0.0


def count_depenses_by_liste(liste_id: int) -> int:
    """Compte les dépenses actives d'une liste."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM depenses WHERE liste_id=? AND synced != 2",
            (liste_id,)
        )
        result = cur.fetchone()
        return result[0] if result else 0
