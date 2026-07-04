import os
from datetime import datetime

import flet as ft

import database as db
import Dialog as Diag

C_PRIMARY = "#2E7D32"
C_DARK = "#1B5E20"
C_BG = "#F4F7F9"
C_SURFACE = "#FFFFFF"
C_ERROR = "#C62828"
C_BLUE = "#1565C0"
C_PURPLE = "#6A1B9A"
C_TEXT = "#1A1A1A"
C_MUTED = "#616161"


def build_liste_view(page: ft.Page, session: dict, navigate) -> ft.View:
    """Depenses d'une liste : ajout, modification, suppression, PDF."""
    user = session["user"]
    uid = user["id"]
    liste = session.get("current_liste") or {}
    liste_id = liste.get("id")
    liste_nom = liste.get("nom", "")

    edit_id: dict = {"id": None}

    description_field = ft.TextField(
        label="Description",
        prefix_icon=ft.Icons.DESCRIPTION_OUTLINED,
        border_radius=12,
        focused_border_color=C_PRIMARY,
    )
    montant_field = ft.TextField(
        label="Montant",
        prefix_icon=ft.Icons.ATTACH_MONEY,
        keyboard_type=ft.KeyboardType.NUMBER,
        border_radius=12,
        focused_border_color=C_PRIMARY,
    )
    categorie_field = ft.TextField(
        label="Categorie",
        prefix_icon=ft.Icons.CATEGORY_OUTLINED,
        border_radius=12,
        focused_border_color=C_PRIMARY,
    )
    date_field = ft.TextField(
        label="Date (YYYY-MM-DD)",
        value=datetime.now().strftime("%Y-%m-%d"),
        prefix_icon=ft.Icons.CALENDAR_MONTH,
        border_radius=12,
        focused_border_color=C_PRIMARY,
    )
    submit_label = ft.Text("Ajouter", color=ft.Colors.WHITE, weight=ft.FontWeight.W_600)

    total_text = ft.Text("0.00", size=26, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
    count_text = ft.Text("0 depense(s)", size=13, color=ft.Colors.WHITE70)

    depenses_list = ft.ListView(spacing=8, expand=False, auto_scroll=False)

    # ── Helpers ───────────────────────────────────────────────────────────

    def clear_form():
        description_field.value = ""
        montant_field.value = ""
        categorie_field.value = ""
        date_field.value = datetime.now().strftime("%Y-%m-%d")
        edit_id["id"] = None
        submit_label.value = "Ajouter"

    def validate_form():
        if not all([description_field.value, montant_field.value,
                    categorie_field.value, date_field.value]):
            Diag.error_dialog(page, message="Veuillez remplir tous les champs.")
            return False, 0.0
        try:
            m = float(montant_field.value)
            if m < 0:
                Diag.error_dialog(page, message="Le montant doit etre positif.")
                return False, 0.0
        except ValueError:
            Diag.error_dialog(page, message="Le montant doit etre un nombre valide.")
            return False, 0.0
        try:
            datetime.strptime(date_field.value, "%Y-%m-%d")
        except ValueError:
            Diag.error_dialog(page, message="Format de date invalide. Utilisez YYYY-MM-DD.")
            return False, 0.0
        return True, float(montant_field.value)

    def _expense_card(dep_id, desc, montant, cat, date):
        return ft.Card(
            elevation=2,
            content=ft.Container(
                bgcolor=C_SURFACE,
                border_radius=12,
                padding=ft.padding.symmetric(horizontal=14, vertical=12),
                content=ft.Column(
                    spacing=6,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(desc, size=15, weight=ft.FontWeight.W_600,
                                        color=C_TEXT, expand=True),
                                ft.Container(
                                    bgcolor="#E8F5E9",
                                    border_radius=8,
                                    padding=ft.padding.symmetric(horizontal=10, vertical=4),
                                    content=ft.Text(f"{montant:.2f}", color=C_DARK,
                                                    weight=ft.FontWeight.BOLD, size=14),
                                ),
                            ],
                        ),
                        ft.Row(
                            spacing=16,
                            controls=[
                                ft.Row(spacing=4, controls=[
                                    ft.Icon(ft.Icons.LABEL_OUTLINE, size=14, color=C_MUTED),
                                    ft.Text(cat, size=13, color=C_MUTED),
                                ]),
                                ft.Row(spacing=4, controls=[
                                    ft.Icon(ft.Icons.CALENDAR_TODAY, size=14, color=C_MUTED),
                                    ft.Text(date, size=13, color=C_MUTED),
                                ]),
                            ],
                        ),
                        ft.Divider(height=1, color="#F5F5F5"),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.END,
                            spacing=4,
                            controls=[
                                ft.IconButton(
                                    icon=ft.Icons.EDIT_OUTLINED,
                                    icon_color=C_BLUE,
                                    icon_size=20,
                                    tooltip="Modifier",
                                    on_click=lambda e, d=(dep_id, desc, montant, cat, date): _load_edit(d),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    icon_color=C_ERROR,
                                    icon_size=20,
                                    tooltip="Supprimer",
                                    on_click=lambda e, did=dep_id: _confirm_delete(did),
                                ),
                            ],
                        ),
                    ],
                ),
            ),
        )

    def _populate_list():
        depenses = db.get_depenses(liste_id=liste_id)
        depenses_list.controls.clear()
        if not depenses:
            depenses_list.controls.append(
                ft.Container(
                    padding=32,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=12,
                        controls=[
                            ft.Icon(ft.Icons.RECEIPT_LONG, size=52, color="#BDBDBD"),
                            ft.Text("Aucune depense dans cette liste", italic=True, color="#9E9E9E", size=15),
                        ],
                    ),
                )
            )
        else:
            for dep_id, desc, montant, cat, date in depenses:
                depenses_list.controls.append(_expense_card(dep_id, desc, montant, cat, date))

    def _update_totals():
        depenses = db.get_depenses(liste_id=liste_id)
        total = sum(d[2] for d in depenses)
        total_text.value = f"{total:.2f}"
        count_text.value = f"{len(depenses)} depense(s)"

    def refresh():
        _update_totals()
        _populate_list()
        page.update()

    def _load_edit(data):
        dep_id, desc, montant, cat, date = data
        edit_id["id"] = dep_id
        description_field.value = desc
        montant_field.value = str(montant)
        categorie_field.value = cat
        date_field.value = date
        submit_label.value = "Enregistrer"
        page.update()

    def _confirm_delete(dep_id):
        def do_delete(e):
            Diag.close_dialog(page, dlg)
            db.delete_depense(dep_id)
            refresh()

        def cancel(e):
            Diag.close_dialog(page, dlg)

        dlg = Diag.ask_dialog(
            page,
            title="Confirmer",
            message="Voulez-vous supprimer cette depense ?",
            on_oui=do_delete,
            on_non=cancel,
        )

    def save_depense(e):
        valid, montant = validate_form()
        if not valid:
            return

        desc = description_field.value.strip()
        cat = categorie_field.value.strip()
        date = date_field.value.strip()

        if edit_id["id"] is None:
            db.add_depense(desc, montant, cat, date, uid, liste_id)
            msg = "Depense ajoutee avec succes."
        else:
            db.update_depense(edit_id["id"], desc, montant, cat, date)
            msg = "Depense modifiee avec succes."

        clear_form()
        refresh()

        def close(e):
            Diag.close_dialog(page, dlg)

        dlg = Diag.success_dialog(page, message=msg, on_ok=close)

    async def create_pdf(e):
        if page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS):
            storage = ft.StoragePaths()
            target_dir = await storage.get_downloads_directory()
            if not target_dir:
                target_dir = await storage.get_application_documents_directory()
        else:
            target_dir = os.getcwd()

        safe_nom = "".join(c if c.isalnum() else "_" for c in liste_nom) or "liste"
        pdf_path = os.path.join(target_dir, f"rapport_{user['username']}_{safe_nom}.pdf")
        db.generate_pdf(pdf_path, liste_id=liste_id, liste_nom=liste_nom)

        def close(e):
            Diag.close_dialog(page, dlg)

        dlg = Diag.success_dialog(page, message=f"PDF genere :\n{pdf_path}", on_ok=close)

    # ── Wallpaper ─────────────────────────────────────────────────────────

    wallpaper = db.get_wallpaper(uid)
    use_wallpaper = bool(wallpaper)

    # ── Etat initial (sans page.update) ───────────────────────────────────

    _update_totals()
    _populate_list()

    summary_card = ft.Card(
        elevation=4,
        content=ft.Container(
            border_radius=14,
            padding=ft.padding.symmetric(horizontal=20, vertical=18),
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=[C_PRIMARY, C_DARK],
            ),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Column(
                        spacing=4,
                        controls=[
                            ft.Text(f"Total — {liste_nom}", size=13, color=ft.Colors.WHITE70),
                            total_text,
                            count_text,
                        ],
                    ),
                    ft.Icon(ft.Icons.FOLDER_OPEN, size=52, color=ft.Colors.WHITE24),
                ],
            ),
        ),
    )

    form_card = ft.Card(
        elevation=2,
        content=ft.Container(
            bgcolor=C_SURFACE,
            border_radius=12,
            padding=16,
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE, color=C_PRIMARY, size=20),
                            ft.Text("Nouvelle depense", size=16, weight=ft.FontWeight.BOLD, color=C_TEXT),
                        ],
                    ),
                    ft.Row(spacing=10, controls=[
                        ft.Container(content=description_field, expand=True),
                        ft.Container(content=montant_field, expand=True),
                    ]),
                    ft.Row(spacing=10, controls=[
                        ft.Container(content=categorie_field, expand=True),
                        ft.Container(content=date_field, expand=True),
                    ]),
                    ft.Row([
                        ft.ElevatedButton(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.SAVE_OUTLINED, color=ft.Colors.WHITE),
                                    submit_label,
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                tight=True,
                            ),
                            on_click=save_depense,
                            expand=True,
                            style=ft.ButtonStyle(
                                bgcolor=C_PRIMARY,
                                color=ft.Colors.WHITE,
                                shape=ft.RoundedRectangleBorder(radius=10),
                                padding=ft.padding.symmetric(vertical=12),
                            ),
                        )
                    ]),
                ],
            ),
        ),
    )

    main_column = ft.Column(
        spacing=14,
        controls=[
            summary_card,
            form_card,
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text("Depenses de la liste", size=16, weight=ft.FontWeight.BOLD, color=C_TEXT),
                    ft.IconButton(
                        icon=ft.Icons.REFRESH,
                        icon_color=C_MUTED,
                        icon_size=20,
                        tooltip="Actualiser",
                        on_click=lambda e: refresh(),
                    ),
                ],
            ),
            depenses_list,
            ft.Row([
                ft.ElevatedButton(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.PICTURE_AS_PDF, color=ft.Colors.WHITE),
                            ft.Text("Telecharger PDF de la liste", color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        tight=True,
                    ),
                    on_click=create_pdf,
                    expand=True,
                    style=ft.ButtonStyle(
                        bgcolor=C_PURPLE,
                        color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.padding.symmetric(vertical=12),
                    ),
                )
            ]),
        ],
    )

    page_content = ft.Container(
        expand=True,
        bgcolor=C_BG,
        image=(
            ft.DecorationImage(src=wallpaper, fit=ft.BoxFit.COVER, opacity=0.18)
            if use_wallpaper else None
        ),
        padding=ft.padding.symmetric(horizontal=14, vertical=12),
        content=main_column,
    )

    return ft.View(
        route="/liste",
        bgcolor=C_BG,
        scroll=ft.ScrollMode.AUTO,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        appbar=ft.AppBar(
            title=ft.Text(liste_nom, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=16),
            bgcolor=C_PRIMARY,
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                icon_color=ft.Colors.WHITE,
                tooltip="Mes listes",
                on_click=lambda e: navigate("/expenses"),
            ),
            actions=[
                ft.IconButton(
                    icon=ft.Icons.PICTURE_AS_PDF,
                    icon_color=ft.Colors.WHITE,
                    tooltip="PDF de la liste",
                    on_click=create_pdf,
                ),
            ],
        ),
        controls=[page_content],
    )
