# --- FORM DEPENSE : Formulaire d'ajout/édition de dépense ---

import flet as ft
from datetime import datetime


def build_form_depense(page: ft.Page) -> tuple:
    """
    Construit le formulaire d'ajout/édition de dépense.
    Retourne (form_container, fields_dict, clear_func, get_values_func).
    """
    description_field = ft.TextField(
        label="Description",
        prefix_icon=ft.Icons.DESCRIPTION_OUTLINED,
        border_radius=10,
    )
    montant_field = ft.TextField(
        label="Montant",
        prefix_icon=ft.Icons.ATTACH_MONEY,
        keyboard_type=ft.KeyboardType.NUMBER,
        border_radius=10,
    )
    categorie_field = ft.TextField(
        label="Catégorie",
        prefix_icon=ft.Icons.CATEGORY_OUTLINED,
        border_radius=10,
    )
    date_field = ft.TextField(
        label="Date (YYYY-MM-DD)",
        value=datetime.now().strftime("%Y-%m-%d"),
        prefix_icon=ft.Icons.CALENDAR_MONTH,
        border_radius=10,
    )

    submit_button_label = ft.Text(
        "Ajouter", color="#FFFFFF", weight=ft.FontWeight.W_600
    )
    
    cancel_button = ft.TextButton(
        "Annuler",
        visible=False,
        style=ft.ButtonStyle(color="#616161"),
    )

    def clear_form():
        description_field.value = ""
        montant_field.value = ""
        categorie_field.value = ""
        date_field.value = datetime.now().strftime("%Y-%m-%d")
        submit_button_label.value = "Ajouter"
        cancel_button.visible = False
        page.update()

    def get_values():
        return (
            description_field.value.strip(),
            montant_field.value.strip(),
            categorie_field.value.strip(),
            date_field.value.strip(),
        )

    def set_edit_mode(description, montant, categorie, date):
        description_field.value = description
        montant_field.value = str(montant)
        categorie_field.value = categorie
        date_field.value = date
        submit_button_label.value = "Enregistrer"
        cancel_button.visible = True
        page.update()

    submit_button = ft.TextButton(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.ADD, color="#FFFFFF"),
                submit_button_label,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            tight=True,
        ),
        style=ft.ButtonStyle(
            bgcolor="#2E7D32",
            color="#FFFFFF",
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=12,
        ),
    )

    form_container = ft.Card(
        elevation=2,
        content=ft.Container(
            bgcolor="#FFFFFF",
            width=420,
            padding=14,
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Text("Nouvelle dépense", size=18, weight=ft.FontWeight.BOLD),
                    description_field,
                    montant_field,
                    categorie_field,
                    date_field,
                    ft.Row(
                        spacing=10,
                        controls=[submit_button, cancel_button],
                    ),
                ],
            ),
        ),
    )

    return (
        form_container,
        {
            "description": description_field,
            "montant": montant_field,
            "categorie": categorie_field,
            "date": date_field,
            "submit_label": submit_button_label,
            "cancel_button": cancel_button,
            "submit_button": submit_button,
        },
        clear_form,
        get_values,
        set_edit_mode,
    )
