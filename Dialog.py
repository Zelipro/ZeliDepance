"""
Dialog.py — Utilitaires de dialogues pour ZeliCot.

Fonctions disponibles :
    error_dialog(page, title, message)
    success_dialog(page, title, message, on_ok)
    ask_dialog(page, title, message, on_oui, on_non)  → retourne le dialog
    custom_dialog(page, title, content_widget, actions) → retourne le dialog
    close_dialog(page, dialog)
"""

import flet as ft

global Colors_col
Colors_col = ft.Colors.BLACK
# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------

def _show(page: ft.Page, dialog: ft.AlertDialog) -> ft.AlertDialog:
    """Ajoute le dialog à l'overlay s'il n'y est pas déjà, puis l'ouvre."""
    if dialog not in page.overlay:
        page.overlay.append(dialog)
    dialog.open = True
    page.update()
    return dialog


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def close_dialog(page: ft.Page, dialog: ft.AlertDialog):
    """Ferme un dialog spécifique."""
    if dialog is not None:
        dialog.open = False
        page.update()


def error_dialog(page: ft.Page, title: str = "Erreur", message: str = ""):
    """Affiche un dialog d'erreur (rouge) avec un bouton OK."""
    def _close(e):
        dlg.open = False
        page.update()

    dlg = ft.AlertDialog(
        title=ft.Row(
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.ERROR_OUTLINE, color="#DC2626", size=22),
                ft.Text(title, color="#DC2626", weight=ft.FontWeight.W_600, size=16),
            ],
        ),
        content=ft.Text(message, color=Colors_col, size=14),
        actions=[
            ft.ElevatedButton(
                "OK",
                bgcolor="#DC2626",
                color=ft.Colors.WHITE,
                on_click=_close,
            )
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    _show(page, dlg)


def success_dialog(
    page: ft.Page,
    title: str = "Succès",
    message: str = "",
    on_ok=None,
):
    """
    Affiche un dialog de succès (vert) avec un bouton OK.
    Si on_ok est fourni, il est appelé après la fermeture du dialog.
    """
    def _close(e):
        dlg.open = False
        page.update()
        if callable(on_ok):
            on_ok(e)

    dlg = ft.AlertDialog(
        title=ft.Row(
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color="#2D7D4D", size=22),
                ft.Text(title, color="#2D7D4D", weight=ft.FontWeight.W_600, size=16),
            ],
        ),
        content=ft.Text(message, color=Colors_col, size=14),
        actions=[
            ft.ElevatedButton(
                "OK",
                bgcolor="#2D7D4D",
                color=ft.Colors.WHITE,
                on_click=_close,
            )
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    _show(page, dlg)


def ask_dialog(
    page: ft.Page,
    title: str = "Confirmation",
    message: str = "",
    on_oui=None,
    on_non=None,
) -> ft.AlertDialog:
    """
    Affiche un dialog de confirmation Oui / Non.
    Retourne la référence du dialog (utile pour on_non = lambda e: setattr(diag, 'open', False)).
    """
    dlg = ft.AlertDialog(
        title=ft.Row(
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.HELP_OUTLINE, color="#F59E0B", size=22),
                ft.Text(title, color="#F59E0B", weight=ft.FontWeight.W_600, size=16),
            ],
        ),
        content=ft.Text(message, color=Colors_col, size=14),
        actions=[
            ft.ElevatedButton(
                "Oui",
                bgcolor="#2D7D4D",
                color=ft.Colors.WHITE,
                on_click=on_oui,
            ),
            ft.ElevatedButton(
                "Non",
                bgcolor="#EF4444",
                color=ft.Colors.WHITE,
                on_click=on_non,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    _show(page, dlg)
    return dlg


def custom_dialog(
    page: ft.Page,
    title: str = "",
    content_widget=None,
    actions=None,
) -> ft.AlertDialog:
    """
    Affiche un dialog entièrement personnalisé.
    Retourne la référence du dialog (utile pour modifier dlg.open depuis les callbacks).

    Note : dialog.content == content_widget, ce qui permet dans les callbacks de faire :
        diag.content.value  (si content_widget est un TextField)
    """
    if actions is None:
        actions = []

    dlg = ft.AlertDialog(
        title=ft.Text(title, color=Colors_col, weight=ft.FontWeight.W_600, size=16) if title else None,
        content=content_widget,
        actions=actions,
        actions_alignment=ft.MainAxisAlignment.END,
    )
    _show(page, dlg)
    return dlg
