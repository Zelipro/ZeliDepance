# --- LISTE VIEW : Page détail d'une liste de dépenses ---

import flet as ft
import Dialog as Diag
from datetime import datetime

from app.db.depenses import (
    add_depense, delete_depense, update_depense,
    get_depenses_by_liste, calcul_total_liste,
)
from app.db.preferences import get_primary_color, get_bg_color, get_bg_image, init_preferences_db
from app.components.depense_card import build_depense_card
from app.components.form_depense import build_form_depense
from app.components.settings_menu import open_settings
from app.navigation import navigate
from app.pdf.pdf_liste import generate_pdf_liste
from app import state


def _is_dark(color: str) -> bool:
    dark_colors = {"#121212", "#0D1B2A", "#1B2E1F", "#1B5E20", "#0D47A1",
                   "#B71C1C", "#4A148C", "#006064", "#2E7D32", "#1565C0",
                   "#C62828", "#6A1B9A", "#00838F", "#F9A825"}
    return color.lower() in {c.lower() for c in dark_colors}


def build_liste_view(page: ft.Page, liste_id: int, liste_nom: str) -> ft.Column:
    """Construit la page détail d'une liste de dépenses."""

    init_preferences_db()
    primary_color = get_primary_color()
    bg_color      = get_bg_color()
    bg_image      = get_bg_image()

    text_color = "#FFFFFF" if _is_dark(bg_color) else "#212121"

    page.title      = f"Gestion des Dépenses - {liste_nom}"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding    = 12
    page.bgcolor    = bg_color
    page.scroll     = ft.ScrollMode.AUTO

    if bg_image:
        page.decoration = ft.BoxDecoration(
            image=ft.DecorationImage(src=bg_image, fit=ft.BoxFit.COVER)
        )
    else:
        page.decoration = None

    def apply_preferences(new_primary, new_bg, new_image):
        navigate(page, "liste", liste_id=liste_id, liste_nom=liste_nom)

    page.appbar = ft.AppBar(
        title=ft.Text(liste_nom, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
        center_title=True,
        bgcolor=primary_color,
        color=ft.Colors.WHITE,
        leading=ft.IconButton(
            ft.Icons.ARROW_BACK,
            icon_color=ft.Colors.WHITE,
            on_click=lambda e: navigate(page, "accueil"),
        ),
        actions=[
            ft.IconButton(
                ft.Icons.PICTURE_AS_PDF,
                icon_color="#FFFFFF",
                on_click=lambda e: handle_create_pdf(),
            ),
            ft.IconButton(
                ft.Icons.SETTINGS,
                icon_color=ft.Colors.WHITE,
                tooltip="Paramètres",
                on_click=lambda e: open_settings(page, apply_preferences),
            ),
        ],
    )

    def handle_create_pdf():
        try:
            output_path = generate_pdf_liste(liste_id)
            Diag.success_dialog(page, "Rapport généré !", f"Fichier : {output_path}")
        except Exception as ex:
            Diag.error_dialog(page, "Erreur", str(ex))

    depenses_list = ft.ListView(spacing=10, expand=False)
    list_container = ft.Container(
        visible=False,
        content=depenses_list,
        padding=ft.Padding(0, 0, 0, 10),
    )

    total_text = ft.Text(
        value="Total : 0.00",
        size=18,
        weight=ft.FontWeight.BOLD,
        color=primary_color if not _is_dark(bg_color) else "#FFFFFF",
    )

    (form_container, fields_dict, clear_form, get_values, set_edit_mode) = build_form_depense(page)

    state.edit_id["id"] = None

    def validate_form():
        desc, montant_str, cat, date_val = get_values()
        if not desc or not montant_str or not cat or not date_val:
            Diag.error_dialog(page, "Veuillez remplir tous les champs.")
            return False, 0.0
        try:
            montant = float(montant_str)
            if montant < 0:
                Diag.error_dialog(page, "Le montant doit être positif.")
                return False, 0.0
        except ValueError:
            Diag.error_dialog(page, "Le montant doit être un nombre valide.")
            return False, 0.0
        try:
            datetime.strptime(date_val, "%Y-%m-%d")
        except ValueError:
            Diag.error_dialog(page, "Format de date invalide. Utilisez YYYY-MM-DD.")
            return False, 0.0
        return True, montant

    def refresh_depenses(_=None):
        depenses_list.controls.clear()
        depenses = get_depenses_by_liste(liste_id)
        if not depenses:
            depenses_list.controls.append(
                ft.Container(
                    content=ft.Text("Aucune dépense enregistrée.", italic=True, color=text_color),
                    padding=10,
                )
            )
            list_container.visible = False
        else:
            list_container.visible = True
            for depense_id, description, montant, categorie, date in depenses:
                depenses_list.controls.append(
                    build_depense_card(
                        depense_id, description, montant, categorie, date,
                        handle_edit_depense, handle_delete_depense,
                    )
                )
        total_text.value = f"Total : {calcul_total_liste(liste_id):.2f}"
        page.update()

    def handle_edit_depense(depense_id, description, montant, categorie, date):
        state.edit_id["id"] = depense_id
        set_edit_mode(description, montant, categorie, date)

        def on_cancel(_=None):
            state.edit_id["id"] = None
            clear_form()

        fields_dict["cancel_button"].on_click = on_cancel

    def handle_delete_depense(depense_id):
        def on_yes(_=None):
            try:
                delete_depense(int(depense_id))
                Diag.close_dialog(page, confirm_dlg)
                Diag.success_dialog(page, "Dépense supprimée.")
                refresh_depenses()
            except Exception as ex:
                Diag.close_dialog(page, confirm_dlg)
                Diag.error_dialog(page, f"Suppression impossible: {str(ex)}")

        def on_no(_=None):
            Diag.close_dialog(page, confirm_dlg)

        confirm_dlg = Diag.ask_dialog(
            page,
            title="Confirmation",
            message="Supprimer cette dépense ?",
            on_oui=on_yes,
            on_non=on_no,
        )

    def handle_save_depense(_):
        valid, montant = validate_form()
        if not valid:
            return
        desc, _, cat, date_val = get_values()

        def on_ok(_=None):
            Diag.close_dialog(page, dlg)

        if state.edit_id["id"] is None:
            add_depense(liste_id, desc, montant, cat, date_val)
            dlg = Diag.success_dialog(page, "Ajout effectué.", on_ok=on_ok)
        else:
            update_depense(state.edit_id["id"], desc, montant, cat, date_val)
            dlg = Diag.success_dialog(page, "Dépense modifiée.", on_ok=on_ok)
            state.edit_id["id"] = None

        clear_form()
        refresh_depenses()

    fields_dict["submit_button"].on_click = handle_save_depense

    main_column = ft.Column(
        spacing=12,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[form_container, total_text, list_container],
    )

    refresh_depenses()
    return main_column
