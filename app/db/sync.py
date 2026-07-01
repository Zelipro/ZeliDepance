# --- SYNC : Synchronisation SQLite local ↔ Supabase ---

import sqlite3
from supabase import create_client, Client
from app.db.connection import get_connection, DB_NAME

# ══════════════════════════════════════════════════════════════════════════
#  CONFIGURATION SUPABASE
# ══════════════════════════════════════════════════════════════════════════

SUPABASE_URL = "https://vzfqpyyukufdqvlvkaft.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6ZnFweXl1a3VmZHF2bHZrYWZ0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg1NTQ4MjgsImV4cCI6MjA5NDEzMDgyOH0.r1T601zTbt0TWPRy_wHEmOR5mJ4Wf2BKFU8ib8uGnY8"


def get_supabase() -> Client:
    """Retourne un client Supabase."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def is_online() -> bool:
    """Vérifie si internet est disponible."""
    try:
        import urllib.request
        urllib.request.urlopen("https://www.google.com", timeout=5)
        return True
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════
#  MIGRATION DB LOCALE — Ajoute les colonnes synced/supabase_id si absentes
# ══════════════════════════════════════════════════════════════════════════

def migrate_local_db() -> None:
    """Ajoute les colonnes synced et supabase_id si elles n'existent pas."""
    with get_connection() as conn:
        cur = conn.cursor()

        # listes_depenses
        cur.execute("PRAGMA table_info(listes_depenses)")
        cols = [row[1] for row in cur.fetchall()]
        if "synced" not in cols:
            cur.execute("ALTER TABLE listes_depenses ADD COLUMN synced INTEGER DEFAULT 0")
        if "supabase_id" not in cols:
            cur.execute("ALTER TABLE listes_depenses ADD COLUMN supabase_id INTEGER DEFAULT NULL")

        # depenses
        cur.execute("PRAGMA table_info(depenses)")
        cols = [row[1] for row in cur.fetchall()]
        if "synced" not in cols:
            cur.execute("ALTER TABLE depenses ADD COLUMN synced INTEGER DEFAULT 0")
        if "supabase_id" not in cols:
            cur.execute("ALTER TABLE depenses ADD COLUMN supabase_id INTEGER DEFAULT NULL")

        conn.commit()
        print("[SYNC] Migration locale OK.")


# ══════════════════════════════════════════════════════════════════════════
#  SYNC LISTES
# ══════════════════════════════════════════════════════════════════════════

def sync_listes(supabase: Client) -> None:
    """Synchronise les listes non encore envoyées vers Supabase."""
    with get_connection() as conn:
        cur = conn.cursor()

        # Récupère les listes pas encore synchronisées
        cur.execute(
            "SELECT id, nom, date_creation FROM listes_depenses WHERE synced = 0"
        )
        listes = cur.fetchall()

        for liste_id, nom, date_creation in listes:
            try:
                # Vérifie si elle existe déjà sur Supabase
                res = supabase.table("listes_depenses").select("id").eq("nom", nom).execute()

                if res.data:
                    # Existe déjà → on note juste le supabase_id
                    supa_id = res.data[0]["id"]
                else:
                    # N'existe pas → on l'insère
                    insert = supabase.table("listes_depenses").insert({
                        "nom": nom,
                        "date_creation": date_creation,
                    }).execute()
                    supa_id = insert.data[0]["id"]

                # Mise à jour locale : synced=1, supabase_id=supa_id
                cur.execute(
                    "UPDATE listes_depenses SET synced=1, supabase_id=? WHERE id=?",
                    (supa_id, liste_id)
                )
                conn.commit()
                print(f"[SYNC] Liste '{nom}' synchronisée (supabase_id={supa_id})")

            except Exception as e:
                print(f"[SYNC] Erreur liste '{nom}': {e}")


# ══════════════════════════════════════════════════════════════════════════
#  SYNC DÉPENSES
# ══════════════════════════════════════════════════════════════════════════

def sync_depenses(supabase: Client) -> None:
    """Synchronise les dépenses non encore envoyées vers Supabase."""
    with get_connection() as conn:
        cur = conn.cursor()

        # Récupère les dépenses pas encore synchronisées
        cur.execute("""
            SELECT d.id, d.liste_id, d.description, d.montant, d.categorie, d.date,
                   l.supabase_id
            FROM depenses d
            JOIN listes_depenses l ON l.id = d.liste_id
            WHERE d.synced = 0
        """)
        depenses = cur.fetchall()

        for dep_id, liste_id, description, montant, categorie, date, supa_liste_id in depenses:
            if supa_liste_id is None:
                print(f"[SYNC] Dépense '{description}' ignorée — liste pas encore sync")
                continue
            try:
                insert = supabase.table("depenses").insert({
                    "liste_id":    supa_liste_id,
                    "description": description,
                    "montant":     montant,
                    "categorie":   categorie,
                    "date":        date,
                }).execute()
                supa_id = insert.data[0]["id"]

                cur.execute(
                    "UPDATE depenses SET synced=1, supabase_id=? WHERE id=?",
                    (supa_id, dep_id)
                )
                conn.commit()
                print(f"[SYNC] Dépense '{description}' synchronisée (supabase_id={supa_id})")

            except Exception as e:
                print(f"[SYNC] Erreur dépense '{description}': {e}")


# ══════════════════════════════════════════════════════════════════════════
#  SYNC SUPPRESSIONS
# ══════════════════════════════════════════════════════════════════════════

def sync_deletions(supabase: Client) -> None:
    """Supprime sur Supabase les entrées marquées pour suppression."""
    with get_connection() as conn:
        cur = conn.cursor()

        # Listes marquées à supprimer
        cur.execute("SELECT supabase_id FROM listes_depenses WHERE synced = 2 AND supabase_id IS NOT NULL")
        for (supa_id,) in cur.fetchall():
            try:
                supabase.table("listes_depenses").delete().eq("id", supa_id).execute()
                cur.execute("DELETE FROM listes_depenses WHERE supabase_id=? AND synced=2", (supa_id,))
                conn.commit()
                print(f"[SYNC] Liste supabase_id={supa_id} supprimée du cloud")
            except Exception as e:
                print(f"[SYNC] Erreur suppression liste {supa_id}: {e}")

        # Dépenses marquées à supprimer
        cur.execute("SELECT supabase_id FROM depenses WHERE synced = 2 AND supabase_id IS NOT NULL")
        for (supa_id,) in cur.fetchall():
            try:
                supabase.table("depenses").delete().eq("id", supa_id).execute()
                cur.execute("DELETE FROM depenses WHERE supabase_id=? AND synced=2", (supa_id,))
                conn.commit()
                print(f"[SYNC] Dépense supabase_id={supa_id} supprimée du cloud")
            except Exception as e:
                print(f"[SYNC] Erreur suppression dépense {supa_id}: {e}")


# ══════════════════════════════════════════════════════════════════════════
#  RESTAURATION DEPUIS SUPABASE (premier lancement / réinstallation)
# ══════════════════════════════════════════════════════════════════════════

def restore_from_supabase(supabase: Client) -> int:
    """
    Récupère toutes les données Supabase et les importe en local.
    Retourne le nombre de dépenses restaurées.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        total = 0

        try:
            # ── Listes ────────────────────────────────────────────────────
            listes = supabase.table("listes_depenses").select("*").execute().data
            for l in listes:
                cur.execute("SELECT id FROM listes_depenses WHERE supabase_id=?", (l["id"],))
                if not cur.fetchone():
                    cur.execute(
                        "INSERT INTO listes_depenses(nom, date_creation, synced, supabase_id) VALUES(?,?,1,?)",
                        (l["nom"], l.get("date_creation", ""), l["id"])
                    )
                    conn.commit()
                    print(f"[RESTORE] Liste '{l['nom']}' restaurée")

            # ── Dépenses ──────────────────────────────────────────────────
            depenses = supabase.table("depenses").select("*").execute().data
            for d in depenses:
                cur.execute("SELECT id FROM depenses WHERE supabase_id=?", (d["id"],))
                if not cur.fetchone():
                    # Trouver le liste_id local depuis supabase_id
                    cur.execute(
                        "SELECT id FROM listes_depenses WHERE supabase_id=?",
                        (d["liste_id"],)
                    )
                    row = cur.fetchone()
                    if row:
                        local_liste_id = row[0]
                        cur.execute(
                            """INSERT INTO depenses
                               (liste_id, description, montant, categorie, date, synced, supabase_id)
                               VALUES(?,?,?,?,?,1,?)""",
                            (local_liste_id, d["description"], d["montant"],
                             d["categorie"], d["date"], d["id"])
                        )
                        conn.commit()
                        total += 1

            print(f"[RESTORE] {total} dépenses restaurées depuis Supabase")

        except Exception as e:
            print(f"[RESTORE] Erreur : {e}")

        return total


# ══════════════════════════════════════════════════════════════════════════
#  FONCTION PRINCIPALE : Lance toute la sync
# ══════════════════════════════════════════════════════════════════════════

def run_sync() -> dict:
    """
    Lance la synchronisation complète si internet est disponible.
    Retourne un dict avec le statut.
    """
    if not is_online():
        print("[SYNC] Pas de connexion internet — mode local uniquement")
        return {"online": False, "synced": False}

    try:
        supabase = get_supabase()
        sync_listes(supabase)
        sync_depenses(supabase)
        sync_deletions(supabase)
        print("[SYNC] Synchronisation complète ✅")
        return {"online": True, "synced": True}
    except Exception as e:
        print(f"[SYNC] Erreur sync : {e}")
        return {"online": True, "synced": False, "error": str(e)}
