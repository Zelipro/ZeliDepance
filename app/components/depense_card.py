# --- DEPENSE CARD : Card affichant une dépense ---

import flet as ft


def build_depense_card(
    depense_id: int, description: str, montant: float, categorie: str, date: str,
    on_edit, on_delete
) -> ft.Card:
    """Construit une Card pour une dépense."""
    return ft.Card(
        elevation=2,
        content=ft.Container(
            bgcolor="#FFFFFF",
            padding=10,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(
                                description,
                                size=16,
                                weight=ft.FontWeight.W_600,
                            ),
                            ft.Text(
                                f"{montant:.2f}",
                                color="#1B5E20",
                                weight=ft.FontWeight.BOLD,
                            ),
                        ],
                    ),
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.CATEGORY, size=16, color="#616161"),
                            ft.Text(categorie),
                        ]
                    ),
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.DATE_RANGE, size=16, color="#616161"),
                            ft.Text(date),
                        ]
                    ),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            ft.IconButton(
                                ft.Icons.EDIT,
                                on_click=lambda e: on_edit(
                                    depense_id, description, montant, categorie, date
                                ),
                            ),
                            ft.IconButton(
                                ft.Icons.DELETE,
                                icon_color="#C62828",
                                on_click=lambda e: on_delete(depense_id),
                            ),
                        ],
                    ),
                ],
            ),
        ),
    )
