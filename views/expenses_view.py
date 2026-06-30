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


def build_expenses_view(page: ft.Page, session: dict, navigate) -> ft.View:
    user = session["user"]
    uid = user["id"]

    edit_id: dict = {"id": None}

    # ── Champs du formulaire ──────────────────────────────────────────────
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
    list_area = ft.Container()

    # ── Helpers ────────────────────────────────────────────────────────────

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

    def _populate_list(depenses):
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
                            ft.Text("Aucune depense enregistree", italic=True, color="#9E9E9E", size=15),
                        ],
                    ),
                )
            )
        else:
            for dep_id, desc, montant, cat, date in depenses:
                depenses_list.controls.append(_expense_card(dep_id, desc, montant, cat, date))

    def _update_totals():
        total_text.value = f"{db.calcul_total(uid):.2f}"
        count_text.value = f"{db.get_depenses_count(uid)} depense(s)"

    def _render_list_area():
        has_pin = db.has_section_pin(uid)
        unlocked = session.get("section_unlocked", True)

        if has_pin and not unlocked:
            list_area.content = ft.Container(
                padding=32,
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=16,
                    controls=[
                        ft.Icon(ft.Icons.LOCK, size=64, color="#BDBDBD"),
                        ft.Text("Section verrouillee", size=16, color="#9E9E9E"),
                        ft.Text(
                            "Entrez votre code PIN pour acceder a vos depenses.",
                            size=13, color="#BDBDBD", text_align=ft.TextAlign.CENTER,
                        ),
                        ft.ElevatedButton(
                            "Deverrouiller",
                            icon=ft.Icons.LOCK_OPEN,
                            on_click=lambda e: _show_unlock_dialog(),
                            style=ft.ButtonStyle(
                                bgcolor=C_PRIMARY, color=ft.Colors.WHITE,
                                shape=ft.RoundedRectangleBorder(radius=10),
                            ),
                        ),
                    ],
                ),
            )
        else:
            _populate_list(db.get_depenses(uid))
            list_area.content = depenses_list

    def refresh():
        _update_totals()
        _render_list_area()
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
            db.add_depense(desc, montant, cat, date, uid)
            msg = "Depense ajoutee avec succes."
        else:
            db.update_depense(edit_id["id"], desc, montant, cat, date)
            msg = "Depense modifiee avec succes."

        clear_form()
        refresh()

        def close(e):
            Diag.close_dialog(page, dlg)

        dlg = Diag.success_dialog(page, message=msg, on_ok=close)

    def create_pdf(e):
        pdf_path = os.path.join(os.getcwd(), f"rapport_{user['username']}.pdf")
        db.generate_pdf(pdf_path, uid, user["nom"])

        def close(e):
            Diag.close_dialog(page, dlg)

        dlg = Diag.success_dialog(page, message=f"PDF genere :\n{pdf_path}", on_ok=close)

    def _show_unlock_dialog():
        pin_field = ft.TextField(
            label="Code PIN de section",
            password=True,
            can_reveal_password=True,
            border_radius=10,
            autofocus=True,
        )
        pin_error = ft.Text("", color=C_ERROR, size=12)

        def try_unlock(e):
            if db.verify_section_pin(uid, pin_field.value):
                session["section_unlocked"] = True
                Diag.close_dialog(page, dlg)
                refresh()
            else:
                pin_error.value = "Code incorrect."
                page.update()

        pin_field.on_submit = try_unlock

        dlg = Diag.custom_dialog(
            page,
            title="Section verrouillee",
            content_widget=ft.Column(
                tight=True,
                spacing=10,
                controls=[
                    ft.Row(controls=[
                        ft.Icon(ft.Icons.LOCK, color=C_DARK),
                        ft.Text("Entrez votre code PIN", expand=True),
                    ]),
                    pin_field,
                    pin_error,
                ],
            ),
            actions=[
                ft.ElevatedButton(
                    "Deverrouiller",
                    bgcolor=C_PRIMARY,
                    color=ft.Colors.WHITE,
                    on_click=try_unlock,
                ),
                ft.TextButton("Annuler", on_click=lambda e: Diag.close_dialog(page, dlg)),
            ],
        )

    def toggle_lock(e):
        if session.get("section_unlocked", True):
            session["section_unlocked"] = False
            refresh()
        else:
            _show_unlock_dialog()

    # ── Wallpaper ─────────────────────────────────────────────────────

    wallpaper = db.get_wallpaper(uid)
    use_wallpaper = wallpaper and os.path.exists(wallpaper)

    # ── Actions AppBar ────────────────────────────────────────────────

    appbar_actions = [
        ft.IconButton(
            icon=ft.Icons.PICTURE_AS_PDF,
            icon_color=ft.Colors.WHITE,
            tooltip="Telecharger PDF",
            on_click=create_pdf,
        ),
        ft.IconButton(
            icon=ft.Icons.SETTINGS,
            icon_color=ft.Colors.WHITE,
            tooltip="Parametres",
            on_click=lambda e: navigate("/settings"),
        ),
    ]
    if user["role"] == "admin":
        appbar_actions.insert(0, ft.IconButton(
            icon=ft.Icons.ADMIN_PANEL_SETTINGS,
            icon_color=ft.Colors.WHITE,
            tooltip="Administration",
            on_click=lambda e: navigate("/admin"),
        ))

    # ── Section verrou (visible seulement si PIN configure) ─────────────────

    has_pin = db.has_section_pin(uid)
    lock_section_header = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            ft.Text("Mes depenses", size=16, weight=ft.FontWeight.BOLD, color=C_TEXT),
            ft.Row(
                spacing=4,
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.LOCK_OPEN if session.get("section_unlocked", True) else ft.Icons.LOCK,
                        icon_color=C_PRIMARY if session.get("section_unlocked", True) else "#F57C00",
                        icon_size=20,
                        tooltip="Verrouiller / Deverrouiller",
                        visible=has_pin,
                        on_click=toggle_lock,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.REFRESH,
                        icon_color=C_MUTED,
                        icon_size=20,
                        tooltip="Actualiser",
                        on_click=lambda e: refresh(),
                    ),
                ],
            ),
        ],
    )

    # ── Construire l'etat initial (sans page.update) ────────────────────────

    _update_totals()
    _render_list_area()

    # ── Cartes principales ──────────────────────────────────────────────

    summary_card = ft.Card(
        elevation=4,
        content=ft.Container(
            border_radius=14,
            padding=ft.padding.symmetric(horizontal=20, vertical=18),
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=[C_PRIMARY, C_DARK],
            ),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Column(
                        spacing=4,
                        controls=[
                            ft.Text("Total des depenses", size=13, color=ft.Colors.WHITE70),
                            total_text,
                            count_text,
                        ],
                    ),
                    ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET, size=52, color=ft.Colors.WHITE24),
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
            ft.Container(
                content=ft.Column(
                    spacing=10,
                    controls=[lock_section_header, list_area],
                ),
            ),
            ft.Row([
                ft.ElevatedButton(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.PICTURE_AS_PDF, color=ft.Colors.WHITE),
                            ft.Text("Telecharger PDF", color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
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

    if use_wallpaper:
        page_content = ft.Stack(
            expand=True,
            controls=[
                ft.Container(
                    expand=True,
                    image=ft.DecorationImage(src=wallpaper, fit=ft.ImageFit.COVER, opacity=0.18),
                    bgcolor=C_BG,
                ),
                ft.Container(
                    expand=True,
                    padding=ft.padding.symmetric(horizontal=14, vertical=12),
                    content=main_column,
                ),
            ],
        )
    else:
        page_content = ft.Container(
            expand=True,
            bgcolor=C_BG,
            padding=ft.padding.symmetric(horizontal=14, vertical=12),
            content=main_column,
        )

    return ft.View(
        route="/expenses",
        bgcolor=C_BG,
        scroll=ft.ScrollMode.AUTO,
        appbar=ft.AppBar(
            title=ft.Text(
                f"ZeliDepense  —  {user['nom']}",
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.WHITE,
                size=16,
            ),
            bgcolor=C_PRIMARY,
            actions=appbar_actions,
        ),
        controls=[page_content],
    )
