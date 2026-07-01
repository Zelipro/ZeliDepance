"""
supabase_sync.py — Synchronisation optionnelle des comptes et depenses avec
un projet Supabase (Postgres + API REST).

N'utilise que la bibliotheque standard (urllib) : aucune dependance
supplementaire. Toutes les operations reseau sont best-effort — si Supabase
est injoignable, l'application continue de fonctionner normalement avec la
base SQLite locale.
"""

import json
import threading
import urllib.error
import urllib.parse
import urllib.request

import database as db

TIMEOUT = 6.0


class SupabaseError(Exception):
    pass


# ── Configuration (stockee localement dans app_config, jamais dans le code) ──

def get_config() -> tuple:
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT key, value FROM app_config WHERE key IN ('supabase_url', 'supabase_key')")
        rows = dict(cur.fetchall())
    return rows.get("supabase_url"), rows.get("supabase_key")


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


def get_last_sync() -> str:
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM app_config WHERE key = 'last_sync_at'")
        row = cur.fetchone()
    return row[0] if row else None


def _set_last_sync(value: str) -> None:
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO app_config (key, value) VALUES ('last_sync_at', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = ?",
            (value, value),
        )
        conn.commit()


# ── Client HTTP minimal (urllib) ─────────────────────────────────────────────

def _request(path: str, method: str = "GET", params: dict = None, body=None,
             extra_headers: dict = None):
    url, api_key = get_config()
    if not url or not api_key:
        raise SupabaseError("Supabase non configure.")

    full_url = f"{url}{path}"
    if params:
        full_url += "?" + urllib.parse.urlencode(params)

    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)

    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(full_url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else []
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")
        raise SupabaseError(f"{e.code} {detail}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise SupabaseError(str(e)) from e


def test_connection(url: str, api_key: str) -> tuple:
    """Teste une URL/cle sans passer par la config enregistree."""
    full_url = f"{url.rstrip('/')}/rest/v1/users?select=username&limit=1"
    headers = {"apikey": api_key, "Authorization": f"Bearer {api_key}"}
    req = urllib.request.Request(full_url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            resp.read()
        return True, "Connexion reussie."
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")
        return False, f"Erreur {e.code} : {detail[:200]}"
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return False, f"Impossible de joindre Supabase : {e}"


# ── Verification de disponibilite d'un identifiant ───────────────────────────

def check_username_taken(username: str):
    """Retourne True/False si Supabase a pu repondre, None si injoignable."""
    if not is_configured():
        return None
    try:
        rows = _request(
            "/rest/v1/users",
            params={"username": f"eq.{username}", "select": "username", "deleted": "eq.0"},
        )
        return len(rows) > 0
    except SupabaseError:
        return None


# ── Push (local -> cloud), best-effort, en arriere-plan ──────────────────────

def _push_user_row(row: dict) -> None:
    _request(
        "/rest/v1/users",
        method="POST",
        params={"on_conflict": "uuid"},
        body=row,
        extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
    )


def _push_depense_row(row: dict) -> None:
    _request(
        "/rest/v1/depenses",
        method="POST",
        params={"on_conflict": "uuid"},
        body=row,
        extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
    )


def _push_preferences_row(row: dict) -> None:
    _request(
        "/rest/v1/user_preferences",
        method="POST",
        params={"on_conflict": "user_uuid"},
        body=row,
        extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
    )


def _run_in_background(fn, *args) -> None:
    if not is_configured():
        return

    def _runner():
        try:
            fn(*args)
        except SupabaseError:
            pass

    threading.Thread(target=_runner, daemon=True).start()


def push_user(user_id: int) -> None:
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT uuid, username, nom, password_hash, salt, role, is_approved, "
            "section_pin_hash, section_pin_salt, created_at, updated_at, deleted "
            "FROM users WHERE id = ?",
            (user_id,),
        )
        row = cur.fetchone()
    if not row:
        return
    payload = {
        "uuid": row[0], "username": row[1], "nom": row[2], "password_hash": row[3],
        "salt": row[4], "role": row[5], "is_approved": row[6], "section_pin_hash": row[7],
        "section_pin_salt": row[8], "created_at": row[9], "updated_at": row[10], "deleted": row[11],
    }
    _run_in_background(_push_user_row, payload)


def push_depense(depense_id: int) -> None:
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT d.uuid, u.uuid, d.description, d.montant, d.categorie, d.date, "
            "d.updated_at, d.deleted "
            "FROM depenses d LEFT JOIN users u ON u.id = d.user_id WHERE d.id = ?",
            (depense_id,),
        )
        row = cur.fetchone()
    if not row or not row[1]:
        return
    payload = {
        "uuid": row[0], "user_uuid": row[1], "description": row[2], "montant": row[3],
        "categorie": row[4], "date": row[5], "updated_at": row[6], "deleted": row[7],
    }
    _run_in_background(_push_depense_row, payload)


def push_preferences(user_id: int) -> None:
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT u.uuid, p.wallpaper_path, p.updated_at "
            "FROM user_preferences p JOIN users u ON u.id = p.user_id WHERE p.user_id = ?",
            (user_id,),
        )
        row = cur.fetchone()
    if not row:
        return
    payload = {"user_uuid": row[0], "wallpaper_path": row[1], "updated_at": row[2]}
    _run_in_background(_push_preferences_row, payload)


# ── Pull (cloud -> local) ────────────────────────────────────────────────────

def pull_and_merge() -> dict:
    """Recupere toutes les donnees distantes et les fusionne dans la base locale.
    Retourne un resume {"users": n, "depenses": n, "error": str|None}."""
    result = {"users": 0, "depenses": 0, "error": None}
    try:
        remote_users = _request("/rest/v1/users", params={"select": "*"})
        remote_depenses = _request("/rest/v1/depenses", params={"select": "*"})
        remote_prefs = _request("/rest/v1/user_preferences", params={"select": "*"})
    except SupabaseError as e:
        result["error"] = str(e)
        return result

    with db.get_connection() as conn:
        cur = conn.cursor()

        uuid_to_local_id = {}

        for r in remote_users:
            cur.execute("SELECT id, updated_at FROM users WHERE username = ?", (r["username"],))
            existing = cur.fetchone()
            if existing:
                local_id, local_updated = existing
                if not local_updated or (r.get("updated_at") or "") >= local_updated:
                    cur.execute(
                        "UPDATE users SET uuid=?, nom=?, password_hash=?, salt=?, role=?, "
                        "is_approved=?, section_pin_hash=?, section_pin_salt=?, updated_at=?, deleted=? "
                        "WHERE id=?",
                        (r.get("uuid"), r.get("nom"), r.get("password_hash"), r.get("salt"),
                         r.get("role"), r.get("is_approved"), r.get("section_pin_hash"),
                         r.get("section_pin_salt"), r.get("updated_at"), r.get("deleted", 0),
                         local_id),
                    )
                uuid_to_local_id[r.get("uuid")] = local_id
            else:
                cur.execute(
                    "INSERT INTO users (uuid, username, nom, password_hash, salt, role, "
                    "is_approved, section_pin_hash, section_pin_salt, created_at, updated_at, deleted) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (r.get("uuid"), r["username"], r.get("nom"), r.get("password_hash"),
                     r.get("salt"), r.get("role", "user"), r.get("is_approved", 0),
                     r.get("section_pin_hash"), r.get("section_pin_salt"), r.get("created_at"),
                     r.get("updated_at"), r.get("deleted", 0)),
                )
                uuid_to_local_id[r.get("uuid")] = cur.lastrowid
                result["users"] += 1

        for r in remote_depenses:
            owner_id = uuid_to_local_id.get(r.get("user_uuid"))
            if owner_id is None:
                continue
            cur.execute("SELECT id, updated_at FROM depenses WHERE uuid = ?", (r.get("uuid"),))
            existing = cur.fetchone()
            if existing:
                local_id, local_updated = existing
                if not local_updated or (r.get("updated_at") or "") >= local_updated:
                    cur.execute(
                        "UPDATE depenses SET description=?, montant=?, categorie=?, date=?, "
                        "updated_at=?, deleted=?, user_id=? WHERE id=?",
                        (r.get("description"), r.get("montant"), r.get("categorie"), r.get("date"),
                         r.get("updated_at"), r.get("deleted", 0), owner_id, local_id),
                    )
            else:
                cur.execute(
                    "INSERT INTO depenses (uuid, description, montant, categorie, date, "
                    "user_id, updated_at, deleted) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (r.get("uuid"), r.get("description"), r.get("montant"), r.get("categorie"),
                     r.get("date"), owner_id, r.get("updated_at"), r.get("deleted", 0)),
                )
                result["depenses"] += 1

        for r in remote_prefs:
            owner_id = uuid_to_local_id.get(r.get("user_uuid"))
            if owner_id is None:
                continue
            cur.execute(
                "INSERT INTO user_preferences (user_id, wallpaper_path, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET wallpaper_path = excluded.wallpaper_path, "
                "updated_at = excluded.updated_at "
                "WHERE excluded.updated_at >= COALESCE(user_preferences.updated_at, '')",
                (owner_id, r.get("wallpaper_path"), r.get("updated_at")),
            )

        conn.commit()

    import datetime
    _set_last_sync(datetime.datetime.now().isoformat(timespec="seconds"))
    return result


def push_all() -> dict:
    """Pousse l'intergralite des donnees locales vers Supabase (synchrone)."""
    result = {"users": 0, "depenses": 0, "error": None}
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()
            user_ids = [r[0] for r in cur.execute("SELECT id FROM users").fetchall()]
            depense_ids = [r[0] for r in cur.execute("SELECT id FROM depenses").fetchall()]

        for uid in user_ids:
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT uuid, username, nom, password_hash, salt, role, is_approved, "
                    "section_pin_hash, section_pin_salt, created_at, updated_at, deleted "
                    "FROM users WHERE id = ?",
                    (uid,),
                )
                row = cur.fetchone()
            payload = {
                "uuid": row[0], "username": row[1], "nom": row[2], "password_hash": row[3],
                "salt": row[4], "role": row[5], "is_approved": row[6], "section_pin_hash": row[7],
                "section_pin_salt": row[8], "created_at": row[9], "updated_at": row[10], "deleted": row[11],
            }
            _push_user_row(payload)
            result["users"] += 1

        for did in depense_ids:
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT d.uuid, u.uuid, d.description, d.montant, d.categorie, d.date, "
                    "d.updated_at, d.deleted "
                    "FROM depenses d LEFT JOIN users u ON u.id = d.user_id WHERE d.id = ?",
                    (did,),
                )
                row = cur.fetchone()
            if not row or not row[1]:
                continue
            payload = {
                "uuid": row[0], "user_uuid": row[1], "description": row[2], "montant": row[3],
                "categorie": row[4], "date": row[5], "updated_at": row[6], "deleted": row[7],
            }
            _push_depense_row(payload)
            result["depenses"] += 1
    except SupabaseError as e:
        result["error"] = str(e)
    return result


def sync_now() -> dict:
    """Synchronisation complete : pousse les changements locaux puis rapatrie
    les changements distants. Retourne un resume a afficher a l'utilisateur."""
    if not is_configured():
        return {"error": "Supabase n'est pas configure."}
    push_result = push_all()
    if push_result.get("error"):
        return push_result
    pull_result = pull_and_merge()
    if pull_result.get("error"):
        return pull_result
    return {
        "sent_users": push_result["users"],
        "sent_depenses": push_result["depenses"],
        "new_users": pull_result["users"],
        "new_depenses": pull_result["depenses"],
        "error": None,
    }
