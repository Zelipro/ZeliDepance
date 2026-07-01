# --- HOME VIEW : Page accueil (liste des listes + bilan) ---

import flet as ft
import Dialog as Diag

from app.db.listes import create_liste, delete_liste, get_all_listes
from app.db.preferences import get_primary_color, get_bg_color, get_bg_image, init_preferences_db
from app.components.liste_card import build_liste_card
from app.components.bilan_widget import build_bilan_widget
from app.components.settings_menu import open_settings
from app.navigation import navigate
from app.pdf.pdf_bilan import generate_pdf_bilan_annee


def _is_dark(color: str) -> bool:
    dark_colors = {"#121212", "#0D1B2A", "#1B2E1F", "#1B5E20", "#0D47A1",
                   "#B71C1C", "#4A148C", "#006064", "#2E7D32", "#1565C0",
                   "#C62828", "#6A1B9A", "#00838F", "#F9A825"}
    return color.lower() in {c.lower() for c in dark_colors}


def build_home_view(page: ft.Page) -> ft.Column:
    """Construit la page accueil."""

    init_preferences_db()
    primary_color = get_primary_color()
    bg_color      = get_bg_color()
    bg_image      = get_bg_image()

    text_color = "#FFFFFF" if _is_dark(bg_color) else "#212121"

    page.title      = "Gestion des Dépenses - Accueil"
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
        navigate(page, "accueil")

    page.appbar = ft.AppBar(
        title=ft.Text("Mes Dépenses", weight=ft.FontWeight.BOLD, color="#FFFFFF"),
        center_title=True,
        bgcolor=primary_color,
        color=ft.Colors.WHITE,
        actions=[
            ft.IconButton(
                ft.Icons.SETTINGS,
                icon_color=ft.Colors.WHITE,
                tooltip="Paramètres",
                on_click=lambda e: open_settings(page, apply_preferences),
            ),
            ft.IconButton(
                ft.Icons.LOGOUT,
                icon_color=ft.Colors.WHITE,
                on_click=lambda e: navigate(page, "lock"),
            ),
        ],
    )

    listes_list = ft.ListView(spacing=10, expand=False)
    listes_container = ft.Container(
        visible=False,
        content=listes_list,
        padding=ft.Padding(0, 0, 0, 10),
    )

    bilan_card, annee_field, resultat_container, bilan_pdf_button = build_bilan_widget(page)

    def handle_open_liste(liste_id: int, nom: str):
        navigate(page, "liste", liste_id=liste_id, liste_nom=nom)

    def handle_delete_liste(liste_id: int, nom: str):
        def on_yes(_=None):
            try:
                delete_liste(int(liste_id))
                Diag.close_dialog(page, confirm_dlg)
                refresh_listes()
                Diag.success_dialog(page, "Succès", f"Liste '{nom}' supprimée.")
            except Exception as ex:
                Diag.close_dialog(page, confirm_dlg)
                Diag.error_dialog(page, "Erreur", f"Suppression impossible: {str(ex)}")

        def on_no(_=None):
            Diag.close_dialog(page, confirm_dlg)

        confirm_dlg = Diag.ask_dialog(
            page,
            title="Confirmation",
            message=f"Supprimer la liste '{nom}' et toutes ses dépenses ?",
            on_oui=on_yes,
            on_non=on_no,
        )

    def refresh_listes(_=None):
        listes_list.controls.clear()
        listes = get_all_listes()
        if not listes:
            listes_list.controls.append(
                ft.Container(
                    content=ft.Text("Aucune liste créée.", italic=True, color=text_color),
                    padding=10,
                )
            )
            listes_container.visible = False
        else:
            listes_container.visible = True
            for liste_id, nom, _ in listes:
                listes_list.controls.append(
                    build_liste_card(liste_id, nom, handle_open_liste, handle_delete_liste)
                )
        page.update()

    nom_liste_field = ft.TextField(
        label="Nom de la liste",
        hint_text="Ex: Mes Tranches",
        border_radius=10,
        focused_border_color=primary_color,
        cursor_color=primary_color,
    )

    def handle_create_liste(_):
        nom = nom_liste_field.value.strip()
        if not nom:
            Diag.error_dialog(page, "Veuillez entrer un nom pour la liste.")
            return
        try:
            create_liste(nom)
            nom_liste_field.value = ""
            Diag.success_dialog(page, "Liste créée !", on_ok=lambda x: refresh_listes())
        except Exception:
            Diag.error_dialog(page, "Une liste avec ce nom existe déjà.")

    create_liste_card = ft.Card(
        elevation=2,
        content=ft.Container(
            bgcolor="#FFFFFF",
            padding=14,
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Text("Nouvelle liste de dépenses", size=18, weight=ft.FontWeight.BOLD),
                    nom_liste_field,
                    ft.TextButton(
                        "Créer la liste",
                        style=ft.ButtonStyle(bgcolor=primary_color, color="#FFFFFF"),
                        on_click=handle_create_liste,
                    ),
                ],
            ),
        ),
    )

    def handle_create_pdf_bilan(e):
        try:
            annee = int(annee_field.value)
            output_path = generate_pdf_bilan_annee(annee)
            Diag.success_dialog(page, "Rapport généré !", f"Fichier : {output_path}")
        except ValueError:
            Diag.error_dialog(page, "Année invalide.")
        except Exception as ex:
            Diag.error_dialog(page, "Erreur", str(ex))

    bilan_pdf_button.on_click = handle_create_pdf_bilan

    main_column = ft.Column(
        spacing=12,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            create_liste_card,
            bilan_card,
            ft.Text("Mes listes de dépenses", size=18, weight=ft.FontWeight.BOLD, color=text_color),
            listes_container,
        ],
    )

    refresh_listes()
    return main_column
