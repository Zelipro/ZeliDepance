# --- LISTE CARD : Card affichant une liste de dépenses ---

import flet as ft
from app.db.depenses import calcul_total_liste, count_depenses_by_liste


def build_liste_card(
    liste_id: int, nom: str, on_open, on_delete
) -> ft.Card:
    """Construit une Card pour une liste de dépenses."""
    total = calcul_total_liste(liste_id)
    count = count_depenses_by_liste(liste_id)

    return ft.Card(
        elevation=2,
        content=ft.Container(
            bgcolor="#FFFFFF",
            padding=14,
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(nom, size=18, weight=ft.FontWeight.BOLD),
                            ft.Text(f"{total:.2f}", size=16, color="#1B5E20"),
                        ],
                    ),
                    ft.Text(f"{count} dépense(s)", size=12, color="#616161"),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.TextButton(
                                "Ouvrir",
                                style=ft.ButtonStyle(
                                    bgcolor="#2E7D32", color="#FFFFFF"
                                ),
                                on_click=lambda e: on_open(liste_id, nom),
                            ),
                            ft.IconButton(
                                ft.Icons.DELETE,
                                icon_color="#C62828",
                                on_click=lambda e: on_delete(liste_id, nom),
                            ),
                        ],
                    ),
                ],
            ),
        ),
    )
