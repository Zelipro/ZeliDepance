import os

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
    """Page d'accueil de l'utilisateur : ses listes de depenses."""
    user = session["user"]
    uid = user["id"]

    total_text = ft.Text("0.00", size=26, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
    count_text = ft.Text("", size=13, color=ft.Colors.WHITE70)

    nouvelle_liste_field = ft.TextField(
        label="Nom de la nouvelle liste",
        prefix_icon=ft.Icons.PLAYLIST_ADD,
        border_radius=12,
        focused_border_color=C_PRIMARY,
        expand=True,
    )

    listes_column = ft.Column(spacing=10)
    list_area = ft.Container()

    # ── Construction des cartes de listes ────────────────────────────────

    def _liste_card(liste: dict) -> ft.Card:
        return ft.Card(
            elevation=2,
            content=ft.Container(
                bgcolor=C_SURFACE,
                border_radius=12,
                padding=ft.Padding.symmetric(horizontal=14, vertical=12),
                on_click=lambda e, l=liste: _open_liste(l),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(
                            spacing=12,
                            expand=True,
                            controls=[
                                ft.Container(
                                    width=42, height=42, border_radius=10,
                                    bgcolor="#E8F5E9",
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.Icon(ft.Icons.FOLDER_OUTLINED, color=C_PRIMARY, size=22),
                                ),
                                ft.Column(
                                    spacing=2,
                                    expand=True,
                                    controls=[
                                        ft.Text(liste["nom"], size=15, weight=ft.FontWeight.W_600, color=C_TEXT),
                                        ft.Text(
                                            f"{liste['count']} depense(s) — Total : {liste['total']:.2f}",
                                            size=12, color=C_MUTED,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        ft.Row(
                            spacing=0,
                            controls=[
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    icon_color=C_ERROR,
                                    icon_size=20,
                                    tooltip="Supprimer la liste",
                                    on_click=lambda e, l=liste: _confirm_delete_liste(l),
                                ),
                                ft.Icon(ft.Icons.CHEVRON_RIGHT, color=C_MUTED),
                            ],
                        ),
                    ],
                ),
            ),
        )

    def _populate_listes():
        listes = db.get_listes(uid)
        listes_column.controls.clear()
        if not listes:
            listes_column.controls.append(
                ft.Container(
                    padding=32,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=12,
                        controls=[
                            ft.Icon(ft.Icons.FOLDER_OFF_OUTLINED, size=52, color="#BDBDBD"),
                            ft.Text("Aucune liste pour le moment", italic=True, color="#9E9E9E", size=15),
                            ft.Text("Creez votre premiere liste ci-dessus.", size=12, color="#BDBDBD"),
                        ],
                    ),
                )
            )
        else:
            for liste in listes:
                listes_column.controls.append(_liste_card(liste))

    def _update_totals():
        listes = db.get_listes(uid)
        total_text.value = f"{db.calcul_total(uid):.2f}"
        count_text.value = f"{db.get_depenses_count(uid)} depense(s) dans {len(listes)} liste(s)"

    def _render_list_area():
        has_pin = db.has_section_pin(uid)
        unlocked = session.get("section_unlocked", True)

        lock_toggle_btn.icon = ft.Icons.LOCK_OPEN if unlocked else ft.Icons.LOCK
        lock_toggle_btn.icon_color = C_PRIMARY if unlocked else "#F57C00"
        lock_toggle_btn.visible = has_pin

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
                            "Entrez votre code PIN pour acceder a vos listes.",
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
            _populate_listes()
            list_area.content = listes_column

    def refresh():
        _update_totals()
        _render_list_area()
        page.update()

    # ── Actions ───────────────────────────────────────────────────────────

    def creer_liste(e):
        ok, msg = db.create_liste(nouvelle_liste_field.value, uid)
        if not ok:
            Diag.error_dialog(page, message=msg)
            return
        nouvelle_liste_field.value = ""
        refresh()

    nouvelle_liste_field.on_submit = creer_liste

    def _open_liste(liste: dict):
        session["current_liste"] = {"id": liste["id"], "nom": liste["nom"]}
        navigate("/liste")

    def _confirm_delete_liste(liste: dict):
        def do_delete(e):
            Diag.close_dialog(page, dlg)
            db.delete_liste(liste["id"])
            refresh()

        def cancel(e):
            Diag.close_dialog(page, dlg)

        dlg = Diag.ask_dialog(
            page,
            title="Confirmation",
            message=f"Supprimer la liste « {liste['nom']} » et toutes ses depenses ?",
            on_oui=do_delete,
            on_non=cancel,
        )

    async def create_pdf(e):
        if page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS):
            storage = ft.StoragePaths()
            target_dir = await storage.get_downloads_directory()
            if not target_dir:
                target_dir = await storage.get_application_documents_directory()
        else:
            target_dir = os.getcwd()

        pdf_path = os.path.join(target_dir, f"rapport_{user['username']}.pdf")
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

    # ── Wallpaper ─────────────────────────────────────────────────────────

    wallpaper = db.get_wallpaper(uid)
    use_wallpaper = bool(wallpaper)

    # ── Actions AppBar ────────────────────────────────────────────────────

    appbar_actions = [
        ft.IconButton(
            icon=ft.Icons.PICTURE_AS_PDF,
            icon_color=ft.Colors.WHITE,
            tooltip="Telecharger PDF (toutes mes depenses)",
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

    # ── En-tete de section avec verrou ────────────────────────────────────

    has_pin = db.has_section_pin(uid)
    lock_toggle_btn = ft.IconButton(
        icon=ft.Icons.LOCK_OPEN if session.get("section_unlocked", True) else ft.Icons.LOCK,
        icon_color=C_PRIMARY if session.get("section_unlocked", True) else "#F57C00",
        icon_size=20,
        tooltip="Verrouiller / Deverrouiller",
        visible=has_pin,
        on_click=toggle_lock,
    )
    section_header = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            ft.Text("Mes listes", size=16, weight=ft.FontWeight.BOLD, color=C_TEXT),
            ft.Row(
                spacing=4,
                controls=[
                    lock_toggle_btn,
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

    # ── Etat initial (sans page.update) ───────────────────────────────────

    _update_totals()
    _render_list_area()

    summary_card = ft.Card(
        elevation=4,
        content=ft.Container(
            border_radius=14,
            padding=ft.Padding.symmetric(horizontal=20, vertical=18),
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
                            ft.Icon(ft.Icons.CREATE_NEW_FOLDER_OUTLINED, color=C_PRIMARY, size=20),
                            ft.Text("Nouvelle liste", size=16, weight=ft.FontWeight.BOLD, color=C_TEXT),
                        ],
                    ),
                    ft.Row(
                        spacing=10,
                        controls=[
                            nouvelle_liste_field,
                            ft.ElevatedButton(
                                "Creer",
                                icon=ft.Icons.ADD,
                                on_click=creer_liste,
                                style=ft.ButtonStyle(
                                    bgcolor=C_PRIMARY,
                                    color=ft.Colors.WHITE,
                                    shape=ft.RoundedRectangleBorder(radius=10),
                                    padding=ft.Padding.symmetric(horizontal=18, vertical=14),
                                ),
                            ),
                        ],
                    ),
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
                    controls=[section_header, list_area],
                ),
            ),
        ],
    )

    page_content = ft.Container(
        expand=True,
        bgcolor=C_BG,
        image=(
            ft.DecorationImage(src=wallpaper, fit=ft.BoxFit.COVER, opacity=0.18)
            if use_wallpaper else None
        ),
        padding=ft.Padding.symmetric(horizontal=14, vertical=12),
        content=main_column,
    )

    return ft.View(
        route="/expenses",
        bgcolor=C_BG,
        scroll=ft.ScrollMode.AUTO,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
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
