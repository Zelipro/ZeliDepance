# --- MAIN : Point d'entrée de l'application ---

import threading
import traceback
import flet as ft

from app.db.connection import init_db
from app.db.sync import migrate_local_db, run_sync, is_online, get_supabase, restore_from_supabase
from app.navigation import navigate
from app.pdf import check_pdf_backend_on_startup


def show_snackbar(page: ft.Page, message: str, bgcolor: str, duration: int = 4000) -> None:
    """Affiche un SnackBar."""
    snack = ft.SnackBar(
        content=ft.Text(message, color="#FFFFFF", weight=ft.FontWeight.W_600),
        bgcolor=bgcolor,
        duration=duration,
    )
    page.overlay.append(snack)
    snack.open = True
    page.update()


def show_error_screen(page: ft.Page, error_text: str) -> None:
    """
    Affiche un écran d'erreur visible avec le message complet.
    Compatible avec toutes les versions de Flet.
    """
    page.controls.clear()
    page.bgcolor = "#1a1a1a"
    page.appbar = None
    page.scroll = ft.ScrollMode.AUTO

    page.add(
        ft.Container(
            expand=True,
            padding=20,
            content=ft.Column(
                scroll=ft.ScrollMode.AUTO,
                spacing=16,
                controls=[
                    ft.Container(height=40),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(ft.Icons.ERROR, color="#FF5252", size=48),
                        ],
                    ),
                    ft.Text(
                        "⚠️ ERREUR AU DÉMARRAGE",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color="#FF5252",
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "Une erreur s'est produite. Voici les détails :",
                        size=13,
                        color="#CCCCCC",
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(
                        bgcolor="#2a2a2a",
                        border_radius=10,
                        padding=16,
                        content=ft.Text(
                            error_text,
                            size=12,
                            color="#FF8A80",
                            selectable=True,
                        ),
                    ),
                    ft.Text(
                        "📋 Copiez ce message et envoyez-le au développeur.",
                        size=12,
                        color="#9E9E9E",
                        italic=True,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.ElevatedButton(
                        "🔄 Réessayer",
                        bgcolor="#FF5252",
                        color="#FFFFFF",
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=10)
                        ),
                        on_click=lambda e: navigate(page, "lock"),
                    ),
                ],
            ),
        )
    )
    page.update()


def main(page: ft.Page) -> None:
    """Point d'entrée de l'application."""

    try:
        # ── 1. Init DB locale ─────────────────────────────────────────────
        init_db()

        # ── 2. Migration ──────────────────────────────────────────────────
        migrate_local_db()

        # ── 3. Vérif PDF ──────────────────────────────────────────────────
        check_pdf_backend_on_startup()

        # ── 4. Lancer l'app immédiatement ─────────────────────────────────
        navigate(page, "lock")

    except Exception as e:
        error_text = traceback.format_exc()
        print(f"[MAIN] CRASH au démarrage :\n{error_text}")
        show_error_screen(page, error_text)
        return

    # ── 5. Restauration premier lancement ─────────────────────────────────
    def first_launch_restore():
        try:
            from app.db.listes import get_all_listes
            listes = get_all_listes()
            if not listes and is_online():
                print("[MAIN] Première installation — restauration Supabase...")
                supabase = get_supabase()
                restored = restore_from_supabase(supabase)
                print(f"[MAIN] {restored} dépenses restaurées ✅")
        except Exception as e:
            error_text = traceback.format_exc()
            print(f"[MAIN] Erreur restauration :\n{error_text}")
            show_snackbar(page, f"⚠️ Restauration échouée : {str(e)}", "#D97706", 6000)

    # ── 6. Sync en arrière-plan avec SnackBars ────────────────────────────
    def background_sync():
        try:
            if is_online():
                show_snackbar(
                    page,
                    "🔄 Connexion détectée — synchronisation en cours...",
                    "#F59E0B",
                )
                first_launch_restore()
                result = run_sync()

                if result["synced"]:
                    show_snackbar(page, "✅ Synchronisation terminée avec succès !", "#2E7D32")
                    print("[MAIN] Sync cloud OK ✅")
                else:
                    error_msg = result.get("error", "Erreur inconnue")
                    show_snackbar(page, f"⚠️ Sync échouée : {error_msg}", "#D97706", 6000)
                    print(f"[MAIN] Sync échouée : {error_msg}")
            else:
                show_snackbar(page, "📴 Vous n'êtes pas connecté — Mode hors-ligne", "#C62828")
                print("[MAIN] Mode hors-ligne 📴")

        except ImportError as e:
            error_text = traceback.format_exc()
            print(f"[MAIN] Module manquant :\n{error_text}")
            show_snackbar(
                page,
                f"❌ Module manquant : {str(e)}",
                "#B71C1C",
                8000,
            )
        except Exception as e:
            error_text = traceback.format_exc()
            print(f"[MAIN] Erreur sync :\n{error_text}")
            show_snackbar(page, f"❌ Erreur sync : {str(e)}", "#B71C1C", 8000)

    threading.Thread(target=background_sync, daemon=True).start()


if __name__ == "__main__":
    ft.run(main)
