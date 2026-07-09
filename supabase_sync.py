"""
supabase_sync.py — Synchronisation SQLite local <-> Supabase.

Colonnes synced/supabase_id (0=a envoyer, 1=a jour, 2=a supprimer), sync
lancee en arriere-plan au demarrage avec des SnackBars de statut.

Le projet Supabase est PARTAGE avec l'application Version-3, qui possede
deja les tables listes_depenses (id, nom, date_creation) et depenses
(id, liste_id, description, montant, categorie, date). Leur structure ne
doit jamais etre modifiee. Cette version multi-utilisateurs s'y adapte :

  - chaque liste distante encode son proprietaire dans son nom
    ("identifiant::nom" ou nom tel quel pour l'administrateur) ;
  - les depenses restent stockees dans la table depenses existante via
    liste_id, comme le fait Version-3 ;
  - les listes historiques de Version-3 (nom sans prefixe utilisateur)
    sont rattachees a l'administrateur (Deg) ;
  - la table users (comptes) est la seule table propre a cette version.

Contrairement a Version-3, l'URL et la cle du projet Supabase ne sont
JAMAIS ecrites dans le code source : l'administrateur les saisit depuis
le panneau Administration, elles sont stockees uniquement dans la base
SQLite locale (table app_config) et ne sont donc jamais poussees sur
GitHub.

Le client REST ci-dessous est reimplemente a la main avec uniquement la
bibliotheque standard (urllib), au lieu du SDK officiel supabase-py :
celui-ci depend de pydantic (extension native pydantic-core, en Rust) et
de yarl (extension C) via postgrest/storage3/realtime/supabase-auth. Ces
binaires n'existent pas pour Android/iOS, ce qui faisait planter l'app
juste apres l'ecran de demarrage (splash) une fois compilee avec
`flet build apk`. Ce client minimal parle directement l'API REST
PostgREST exposee par Supabase et fonctionne donc sur toutes les
plateformes.
"""

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

import database as db


# ── Client PostgREST minimal (stdlib pure, sans dependance native) ──────────

class _PostgrestResponse:
    def __init__(self, data):
        self.data = data


class _QueryBuilder:
    def __init__(self, base_url: str, api_key: str, table: str):
        self._base_url = base_url
        self._api_key = api_key
        self._table = table
        self._method = "GET"
        self._select = "*"
        self._filters = []
        self._payload = None
        self._limit = None

    def select(self, columns: str = "*"):
        self._method = "GET"
        self._select = columns
        return self

    def insert(self, payload):
        self._method = "POST"
        self._payload = payload
        return self

    def update(self, payload):
        self._method = "PATCH"
        self._payload = payload
        return self

    def delete(self):
        self._method = "DELETE"
        return self

    def eq(self, field: str, value):
        self._filters.append((field, value))
        return self

    def limit(self, n: int):
        self._limit = n
        return self

    def execute(self) -> _PostgrestResponse:
        params = []
        if self._method == "GET":
            params.append(("select", self._select))
        for field, value in self._filters:
            params.append((field, f"eq.{value}"))
        if self._limit is not None:
            params.append(("limit", str(self._limit)))

        url = f"{self._base_url}/rest/v1/{self._table}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        headers = {
            "apikey": self._api_key,
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        body = json.dumps(self._payload).encode("utf-8") if self._payload is not None else None

        req = urllib.request.Request(url, data=body, headers=headers, method=self._method)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "ignore")
            raise RuntimeError(f"{e.code} {e.reason} — {detail}") from None

        data = json.loads(raw) if raw else []
        return _PostgrestResponse(data)


class Client:
    def __init__(self, url: str, api_key: str):
        self._url = url.rstrip("/")
        self._api_key = api_key

    def table(self, name: str) -> _QueryBuilder:
        return _QueryBuilder(self._url, self._api_key, name)


def create_client(url: str, api_key: str) -> Client:
    return Client(url, api_key)


# ── Configuration ─────────────────────────────────────────────────────────

def get_config() -> tuple:
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT key, value FROM app_config WHERE key IN ('supabase_url', 'supabase_key')")
        rows = dict(cur.fetchall())
    return rows.get("supabase_url") or None, rows.get("supabase_key") or None


def set_config(url: str, api_key: str) -> None:
    url = (url or "").strip().rstrip("/")
    api_key = (api_key or "").strip()
    with db.get_connection() as conn:
        cur = conn.cursor()
        for key, value in (("supabase_url", url), ("supabase_key", api_key)):
            cur.execute(
                "INSERT INTO app_config (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = ?",
                (key, value, value),
            )
        conn.commit()


def is_configured() -> bool:
    url, key = get_config()
    return bool(url) and bool(key)


def get_supabase() -> Client:
    url, key = get_config()
    if not url or not key:
        raise RuntimeError("Supabase n'est pas configure.")
    return create_client(url, key)


def is_online() -> bool:
    """Verifie si le projet Supabase configure est joignable."""
    url, _ = get_config()
    if not url:
        return False
    import urllib.error
    import urllib.request
    try:
        urllib.request.urlopen(url, timeout=5)
        return True
    except urllib.error.HTTPError:
        # Le serveur a repondu (ex: 401/404 sans cle) -> il est bien joignable.
        return True
    except Exception:
        return False


def test_connection(url: str, api_key: str) -> tuple:
    try:
        client = create_client(url.strip().rstrip("/"), api_key.strip())
        client.table("users").select("id").limit(1).execute()
        client.table("listes_depenses").select("id").limit(1).execute()
        client.table("depenses").select("id").limit(1).execute()
        return True, "Connexion reussie."
    except Exception as e:
        return False, f"Impossible de joindre Supabase : {e}"


# ── Verification de disponibilite d'un identifiant ───────────────────────

def check_username_taken(username: str):
    """Retourne True/False si Supabase a pu repondre, None si injoignable."""
    if not is_online():
        return None
    try:
        supabase = get_supabase()
        res = supabase.table("users").select("username").eq("username", username).execute()
        return len(res.data) > 0
    except Exception:
        return None


# ── Sync utilisateurs ──────────────────────────────────────────────────────

def sync_users(supabase: Client) -> int:
    """Pousse les utilisateurs non encore synchronises. Retourne le nombre traite."""
    count = 0
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, nom, password_hash, salt, role, is_approved, "
            "section_pin_hash, section_pin_salt, created_at, supabase_id "
            "FROM users WHERE synced = 0"
        )
        rows = cur.fetchall()

    for (uid, username, nom, password_hash, salt, role, is_approved,
         section_pin_hash, section_pin_salt, created_at, supabase_id) in rows:
        payload = {
            "username": username, "nom": nom, "password_hash": password_hash,
            "salt": salt, "role": role, "is_approved": is_approved,
            "section_pin_hash": section_pin_hash, "section_pin_salt": section_pin_salt,
            "created_at": created_at,
        }
        try:
            if supabase_id is not None:
                supabase.table("users").update(payload).eq("id", supabase_id).execute()
                supa_id = supabase_id
            else:
                existing = supabase.table("users").select("id").eq("username", username).execute()
                if existing.data:
                    supa_id = existing.data[0]["id"]
                    supabase.table("users").update(payload).eq("id", supa_id).execute()
                else:
                    inserted = supabase.table("users").insert(payload).execute()
                    supa_id = inserted.data[0]["id"]

            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("UPDATE users SET synced=1, supabase_id=? WHERE id=?", (supa_id, uid))
                conn.commit()
            count += 1
            print(f"[SYNC] Utilisateur '{username}' synchronise (supabase_id={supa_id})")
        except Exception as e:
            print(f"[SYNC] Erreur utilisateur '{username}': {e}")

    return count


# ── Sync listes ──────────────────────────────────────────────────────────────
#
# Les listes locales sont stockees dans la table listes_depenses existante de
# Version-3 (id, nom UNIQUE, date_creation — structure intouchee). Le nom
# distant encode le proprietaire :
#   - listes de l'administrateur : nom tel quel (identiques a celles de
#     Version-3, qui reste l'app de l'administrateur) ;
#   - listes des autres utilisateurs : "identifiant::nom" pour garantir
#     l'unicite et retrouver le proprietaire a la restauration.

def _encode_liste_nom(nom: str, username: str, role: str) -> str:
    return nom if role == "admin" else f"{username}::{nom}"


def _decode_liste_nom(remote_nom: str, usernames: set) -> tuple:
    """Retourne (username_proprietaire | None, nom_affiche).
    None -> liste de l'administrateur (listes historiques Version-3 incluses)."""
    if "::" in remote_nom:
        prefix, rest = remote_nom.split("::", 1)
        if prefix in usernames:
            return prefix, rest
    return None, remote_nom


def sync_listes(supabase: Client) -> int:
    """Pousse les listes non encore synchronisees. Retourne le nombre traite."""
    count = 0
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT l.id, l.nom, l.date_creation, l.supabase_id,
                   u.username, u.role, u.supabase_id
            FROM listes l
            JOIN users u ON u.id = l.user_id
            WHERE l.synced = 0
        """)
        rows = cur.fetchall()

    for (liste_id, nom, date_creation, supa_id, username, role, supa_user_id) in rows:
        if supa_user_id is None:
            print(f"[SYNC] Liste '{nom}' ignoree — utilisateur pas encore sync")
            continue
        remote_nom = _encode_liste_nom(nom, username, role)
        try:
            if supa_id is None:
                existing = supabase.table("listes_depenses").select("id").eq("nom", remote_nom).execute()
                if existing.data:
                    supa_id = existing.data[0]["id"]
                else:
                    inserted = supabase.table("listes_depenses").insert({
                        "nom": remote_nom,
                        "date_creation": date_creation or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }).execute()
                    supa_id = inserted.data[0]["id"]

            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("UPDATE listes SET synced=1, supabase_id=? WHERE id=?", (supa_id, liste_id))
                conn.commit()
            count += 1
            print(f"[SYNC] Liste '{nom}' synchronisee (supabase_id={supa_id})")
        except Exception as e:
            print(f"[SYNC] Erreur liste '{nom}': {e}")

    return count


# ── Sync depenses ───────────────────────────────────────────────────────────

def sync_depenses(supabase: Client) -> int:
    """Pousse les depenses non encore synchronisees. Retourne le nombre traite."""
    count = 0
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT d.id, d.description, d.montant, d.categorie, d.date, d.supabase_id,
                   l.supabase_id
            FROM depenses d
            LEFT JOIN listes l ON l.id = d.liste_id
            WHERE d.synced = 0
        """)
        rows = cur.fetchall()

    for (dep_id, description, montant, categorie, date, supa_id, supa_liste_id) in rows:
        try:
            if supa_id is not None:
                # Mise a jour en place, sans toucher liste_id : une depense
                # reste dans sa liste d'origine (y compris les listes
                # historiques de Version-3).
                payload = {"description": description, "montant": montant,
                           "categorie": categorie, "date": date}
                supabase.table("depenses").update(payload).eq("id", supa_id).execute()
            else:
                if supa_liste_id is None:
                    print(f"[SYNC] Depense '{description}' ignoree — liste pas encore sync")
                    continue
                payload = {"liste_id": supa_liste_id, "description": description,
                           "montant": montant, "categorie": categorie, "date": date}
                inserted = supabase.table("depenses").insert(payload).execute()
                supa_id = inserted.data[0]["id"]

            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("UPDATE depenses SET synced=1, supabase_id=? WHERE id=?", (supa_id, dep_id))
                conn.commit()
            count += 1
            print(f"[SYNC] Depense '{description}' synchronisee (supabase_id={supa_id})")
        except Exception as e:
            print(f"[SYNC] Erreur depense '{description}': {e}")

    return count


# ── Sync suppressions ────────────────────────────────────────────────────────

def sync_deletions(supabase: Client) -> int:
    """Supprime sur Supabase les entrees marquees pour suppression (synced=2)."""
    count = 0
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, supabase_id FROM depenses WHERE synced = 2 AND supabase_id IS NOT NULL")
        depense_rows = cur.fetchall()
        cur.execute("SELECT id, nom, supabase_id FROM listes WHERE synced = 2 AND supabase_id IS NOT NULL")
        liste_rows = cur.fetchall()
        cur.execute("SELECT id, username, supabase_id FROM users WHERE synced = 2 AND supabase_id IS NOT NULL")
        user_rows = cur.fetchall()

    for local_id, supa_id in depense_rows:
        try:
            supabase.table("depenses").delete().eq("id", supa_id).execute()
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM depenses WHERE id=? AND synced=2", (local_id,))
                conn.commit()
            count += 1
            print(f"[SYNC] Depense supabase_id={supa_id} supprimee du cloud")
        except Exception as e:
            print(f"[SYNC] Erreur suppression depense {supa_id}: {e}")

    for local_id, nom, supa_id in liste_rows:
        try:
            supabase.table("depenses").delete().eq("liste_id", supa_id).execute()
            supabase.table("listes_depenses").delete().eq("id", supa_id).execute()
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM depenses WHERE liste_id=? AND synced=2", (local_id,))
                cur.execute("DELETE FROM listes WHERE id=? AND synced=2", (local_id,))
                conn.commit()
            count += 1
            print(f"[SYNC] Liste '{nom}' supprimee du cloud")
        except Exception as e:
            print(f"[SYNC] Erreur suppression liste '{nom}': {e}")

    for local_id, username, supa_id in user_rows:
        try:
            supabase.table("users").delete().eq("id", supa_id).execute()
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM depenses WHERE user_id=? AND synced=2", (local_id,))
                cur.execute("DELETE FROM listes WHERE user_id=? AND synced=2", (local_id,))
                cur.execute("DELETE FROM users WHERE id=? AND synced=2", (local_id,))
                conn.commit()
            count += 1
            print(f"[SYNC] Utilisateur '{username}' supprime du cloud")
        except Exception as e:
            print(f"[SYNC] Erreur suppression utilisateur '{username}': {e}")

    return count


# ── Restauration depuis Supabase (premier lancement / nouvel appareil) ──────

def restore_from_supabase(supabase: Client) -> dict:
    """Recupere toutes les donnees Supabase absentes localement et les importe."""
    result = {"users": 0, "listes": 0, "depenses": 0}
    with db.get_connection() as conn:
        cur = conn.cursor()
        local_id_by_username = {}

        users = supabase.table("users").select("*").execute().data
        for u in users:
            cur.execute("SELECT id, synced, supabase_id FROM users WHERE username=?", (u["username"],))
            existing = cur.fetchone()
            if existing:
                local_id, local_synced, local_supa_id = existing
                # N'ecrase l'etat local que s'il est propre (synced=1) ou jamais
                # lie au cloud (supabase_id NULL). Un compte avec des changements
                # locaux en attente (synced=0) ou marque pour suppression
                # (synced=2) garde son etat : sync_users/sync_deletions le
                # poussera juste apres.
                if local_supa_id is None or local_synced == 1:
                    cur.execute(
                        "UPDATE users SET nom=?, password_hash=?, salt=?, role=?, is_approved=?, "
                        "section_pin_hash=?, section_pin_salt=?, synced=1, supabase_id=? WHERE id=?",
                        (u.get("nom"), u["password_hash"], u["salt"], u.get("role", "user"),
                         u.get("is_approved", 0), u.get("section_pin_hash"), u.get("section_pin_salt"),
                         u["id"], local_id),
                    )
            else:
                cur.execute(
                    "INSERT INTO users (username, nom, password_hash, salt, role, is_approved, "
                    "section_pin_hash, section_pin_salt, created_at, synced, supabase_id) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)",
                    (u["username"], u.get("nom"), u["password_hash"], u["salt"], u.get("role", "user"),
                     u.get("is_approved", 0), u.get("section_pin_hash"), u.get("section_pin_salt"),
                     u.get("created_at"), u["id"]),
                )
                local_id = cur.lastrowid
                result["users"] += 1
                print(f"[RESTORE] Utilisateur '{u['username']}' restaure")
            conn.commit()
            local_id_by_username[u["username"]] = local_id

        # Les listes historiques de Version-3 (nom sans prefixe utilisateur)
        # sont rattachees a l'administrateur, chacune restant une liste
        # distincte (Tous les depenses pour UTBM, Amortissement des 6000, ...).
        cur.execute("SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1")
        row = cur.fetchone()
        admin_local_id = row[0] if row else None
        usernames = set(local_id_by_username.keys())

        listes = supabase.table("listes_depenses").select("*").execute().data
        local_liste_by_remote = {}
        owner_by_remote_liste = {}
        for liste in listes:
            owner_username, display_nom = _decode_liste_nom(liste.get("nom") or "", usernames)
            owner_id = local_id_by_username.get(owner_username, admin_local_id) if owner_username else admin_local_id
            if owner_id is None:
                continue
            owner_by_remote_liste[liste["id"]] = owner_id

            cur.execute("SELECT id FROM listes WHERE supabase_id=?", (liste["id"],))
            existing = cur.fetchone()
            if existing:
                local_liste_id = existing[0]
            else:
                # Une liste locale du meme nom en attente d'envoi ? On la lie
                # au lieu de creer un doublon.
                cur.execute(
                    "SELECT id FROM listes WHERE user_id=? AND nom=? AND supabase_id IS NULL AND synced != 2",
                    (owner_id, display_nom),
                )
                pending = cur.fetchone()
                if pending:
                    local_liste_id = pending[0]
                    cur.execute(
                        "UPDATE listes SET synced=1, supabase_id=? WHERE id=?",
                        (liste["id"], local_liste_id),
                    )
                else:
                    cur.execute(
                        "INSERT INTO listes (nom, user_id, date_creation, synced, supabase_id) "
                        "VALUES (?, ?, ?, 1, ?)",
                        (display_nom, owner_id, liste.get("date_creation"), liste["id"]),
                    )
                    local_liste_id = cur.lastrowid
                    result["listes"] += 1
                    print(f"[RESTORE] Liste '{display_nom}' restauree")
                conn.commit()
            local_liste_by_remote[liste["id"]] = local_liste_id

        depenses = supabase.table("depenses").select("*").execute().data
        for d in depenses:
            local_liste_id = local_liste_by_remote.get(d.get("liste_id"))
            owner_id = owner_by_remote_liste.get(d.get("liste_id"), admin_local_id)
            if owner_id is None:
                continue
            cur.execute("SELECT id, liste_id FROM depenses WHERE supabase_id=?", (d["id"],))
            existing = cur.fetchone()
            if existing:
                # Reparation : depense deja locale mais pas encore rattachee a
                # sa liste (donnees d'avant l'arrivee des listes).
                if existing[1] is None and local_liste_id is not None:
                    cur.execute(
                        "UPDATE depenses SET liste_id=?, user_id=? WHERE id=?",
                        (local_liste_id, owner_id, existing[0]),
                    )
                    conn.commit()
            else:
                cur.execute(
                    "INSERT INTO depenses (description, montant, categorie, date, user_id, liste_id, synced, supabase_id) "
                    "VALUES (?, ?, ?, ?, ?, ?, 1, ?)",
                    (d.get("description"), d.get("montant"), d.get("categorie"), d.get("date"),
                     owner_id, local_liste_id, d["id"]),
                )
                conn.commit()
                result["depenses"] += 1

    print(f"[RESTORE] {result['users']} compte(s), {result['listes']} liste(s) et "
          f"{result['depenses']} depense(s) restaures depuis Supabase")
    return result


def first_launch_restore() -> dict:
    """Si aucun compte local n'est encore lie au cloud, restaure depuis Supabase."""
    if not is_online():
        return {"users": 0, "depenses": 0}
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE supabase_id IS NOT NULL")
        already_linked = cur.fetchone()[0]
    if already_linked > 0:
        return {"users": 0, "depenses": 0}
    try:
        return restore_from_supabase(get_supabase())
    except Exception as e:
        print(f"[RESTORE] Erreur : {e}")
        return {"users": 0, "depenses": 0, "error": str(e)}


def try_restore() -> None:
    """Restauration silencieuse, meme si l'appareil est deja lie au cloud.
    Utilisee quand un identifiant inconnu localement tente de se connecter
    (compte cree sur un autre appareil)."""
    if not is_online():
        return
    try:
        restore_from_supabase(get_supabase())
    except Exception as e:
        print(f"[RESTORE] Erreur : {e}")


# ── Fonction principale : lance toute la sync ────────────────────────────────

def run_sync() -> dict:
    """Lance la synchronisation complete si internet est disponible."""
    if not is_online():
        print("[SYNC] Pas de connexion internet — mode local uniquement")
        return {"online": False, "synced": False}

    try:
        supabase = get_supabase()
        u = sync_users(supabase)
        listes = sync_listes(supabase)
        d = sync_depenses(supabase)
        deleted = sync_deletions(supabase)
        print("[SYNC] Synchronisation complete")
        return {"online": True, "synced": True, "users": u, "listes": listes,
                "depenses": d, "deleted": deleted}
    except Exception as e:
        print(f"[SYNC] Erreur sync : {e}")
        return {"online": True, "synced": False, "error": str(e)}


def full_sync() -> dict:
    """Synchronisation manuelle bidirectionnelle : rapatrie d'abord les
    donnees distantes absentes localement, puis pousse les changements
    locaux. Utilisee par le bouton "Synchroniser maintenant"."""
    if not is_online():
        return {"online": False, "synced": False}
    try:
        supabase = get_supabase()
        restored = restore_from_supabase(supabase)
        u = sync_users(supabase)
        listes = sync_listes(supabase)
        d = sync_depenses(supabase)
        deleted = sync_deletions(supabase)
        return {
            "online": True, "synced": True,
            "restored_users": restored["users"],
            "restored_listes": restored["listes"],
            "restored_depenses": restored["depenses"],
            "users": u, "listes": listes, "depenses": d, "deleted": deleted,
        }
    except Exception as e:
        print(f"[SYNC] Erreur sync : {e}")
        return {"online": True, "synced": False, "error": str(e)}


# ── Lancement en arriere-plan avec SnackBars (comme Version-3) ──────────────

def _snackbar(page, message: str, bgcolor: str, duration: int = 4000) -> None:
    import flet as ft
    snack = ft.SnackBar(
        content=ft.Text(message, color="#FFFFFF", weight=ft.FontWeight.W_600),
        bgcolor=bgcolor,
        duration=duration,
    )
    page.overlay.append(snack)
    snack.open = True
    page.update()


def run_in_background(page, on_done=None) -> None:
    """Lance la restauration/synchronisation dans un thread, avec notifications."""

    def _worker():
        try:
            if not is_configured():
                # Pas d'URL/cle enregistree — rien a synchroniser, mode local uniquement.
                if on_done:
                    on_done({"online": False, "synced": False})
                return

            if not is_online():
                _snackbar(page, "Vous n'etes pas connecte — mode hors-ligne", "#C62828")
                if on_done:
                    on_done({"online": False, "synced": False})
                return

            _snackbar(page, "Connexion detectee — synchronisation en cours...", "#F59E0B")
            first_launch_restore()
            result = run_sync()

            if result.get("synced"):
                _snackbar(page, "Synchronisation terminee avec succes !", "#2E7D32")
            else:
                error_msg = result.get("error", "Erreur inconnue")
                _snackbar(page, f"Synchronisation echouee : {error_msg}", "#D97706", 6000)

            if on_done:
                on_done(result)
        except Exception as e:
            _snackbar(page, f"Erreur de synchronisation : {e}", "#B71C1C", 8000)
            if on_done:
                on_done({"online": True, "synced": False, "error": str(e)})

    threading.Thread(target=_worker, daemon=True).start()
