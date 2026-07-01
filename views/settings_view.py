import base64

import flet as ft

import database as db
import Dialog as Diag

C_PRIMARY = "#2E7D32"
C_DARK = "#1B5E20"
C_BG = "#F4F7F9"
C_SURFACE = "#FFFFFF"
C_ERROR = "#C62828"
C_TEXT = "#1A1A1A"
C_MUTED = "#616161"


def _section(title: str, icon, controls: list) -> ft.Container:
    return ft.Container(
        bgcolor=C_SURFACE,
        border_radius=14,
        padding=16,
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Row(
                    spacing=8,
                    controls=[
                        ft.Icon(icon, color=C_PRIMARY, size=20),
                        ft.Text(title, size=15, weight=ft.FontWeight.BOLD, color=C_TEXT),
                    ],
                ),
                ft.Divider(height=1, color="#F0F0F0"),
                *controls,
            ],
        ),
    )


def build_settings_view(page: ft.Page, session: dict, navigate) -> ft.View:
    user = session["user"]
    uid = user["id"]

    # ── Changer le mot de passe ──────────────────────────────────────────────

    old_pass = ft.TextField(label="Mot de passe actuel", password=True, can_reveal_password=True, border_radius=10, focused_border_color=C_PRIMARY)
    new_pass = ft.TextField(label="Nouveau mot de passe", password=True, can_reveal_password=True, border_radius=10, focused_border_color=C_PRIMARY)
    confirm_pass = ft.TextField(label="Confirmer le nouveau mot de passe", password=True, can_reveal_password=True, border_radius=10, focused_border_color=C_PRIMARY)
    pass_error = ft.Text("", color=C_ERROR, size=12, visible=False)

    def change_password(e):
        pass_error.visible = False
        if not all([old_pass.value, new_pass.value, confirm_pass.value]):
            pass_error.value = "Remplissez tous les champs."
            pass_error.visible = True
            page.update()
            return
        if len(new_pass.value) < 6:
            pass_error.value = "Le nouveau mot de passe doit contenir au moins 6 caracteres."
            pass_error.visible = True
            page.update()
            return
        if new_pass.value != confirm_pass.value:
            pass_error.value = "Les mots de passe ne correspondent pas."
            pass_error.visible = True
            page.update()
            return

        success, msg = db.change_password(uid, old_pass.value, new_pass.value)
        if success:
            old_pass.value = new_pass.value = confirm_pass.value = ""
            def close(e):
                Diag.close_dialog(page, dlg)
            dlg = Diag.success_dialog(page, message=msg, on_ok=close)
        else:
            pass_error.value = msg
            pass_error.visible = True
        page.update()

    password_section = _section(
        "Mot de passe",
        ft.Icons.LOCK_OUTLINE,
        [old_pass, new_pass, confirm_pass, pass_error,
         ft.Row([
             ft.ElevatedButton(
                 "Modifier le mot de passe",
                 icon=ft.Icons.SAVE,
                 on_click=change_password,
                 expand=True,
                 style=ft.ButtonStyle(
                     bgcolor=C_PRIMARY, color=ft.Colors.WHITE,
                     shape=ft.RoundedRectangleBorder(radius=10),
                     padding=ft.padding.symmetric(vertical=10),
                 ),
             )
         ])],
    )

    # ── Code PIN de section ──────────────────────────────────────────────

    pin_field = ft.TextField(
        label="Nouveau code PIN (min. 4 caracteres)",
        password=True,
        can_reveal_password=True,
        border_radius=10,
        focused_border_color=C_PRIMARY,
    )
    pin_error = ft.Text("", color=C_ERROR, size=12, visible=False)
    has_pin = db.has_section_pin(uid)
    pin_status = ft.Container(
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
        border_radius=20,
        bgcolor="#E8F5E9" if has_pin else "#FFF3E0",
        content=ft.Row(
            spacing=6,
            tight=True,
            controls=[
                ft.Icon(
                    ft.Icons.LOCK if has_pin else ft.Icons.LOCK_OPEN,
                    color=C_PRIMARY if has_pin else "#F57C00",
                    size=14,
                ),
                ft.Text(
                    "PIN configure" if has_pin else "Aucun PIN configure",
                    size=12,
                    color=C_PRIMARY if has_pin else "#F57C00",
                ),
            ],
        ),
    )

    def set_pin(e):
        pin_error.visible = False
        if not pin_field.value or len(pin_field.value) < 4:
            pin_error.value = "Le code PIN doit contenir au moins 4 caracteres."
            pin_error.visible = True
            page.update()
            return
        db.set_section_pin(uid, pin_field.value)
        pin_field.value = ""
        session["section_unlocked"] = False
        def close(e):
            Diag.close_dialog(page, dlg)
        dlg = Diag.success_dialog(page, message="Code PIN de section configure.", on_ok=close)
        navigate("/settings")

    def remove_pin(e):
        def do_remove(e):
            Diag.close_dialog(page, dlg)
            db.remove_section_pin(uid)
            session["section_unlocked"] = True
            def close(e2):
                Diag.close_dialog(page, dlg2)
            dlg2 = Diag.success_dialog(page, message="Code PIN supprime.", on_ok=close)
            navigate("/settings")

        def cancel(e):
            Diag.close_dialog(page, dlg)

        dlg = Diag.ask_dialog(
            page,
            title="Confirmation",
            message="Supprimer le code PIN de section ?",
            on_oui=do_remove,
            on_non=cancel,
        )

    pin_section = _section(
        "Securite — Section privee",
        ft.Icons.SHIELD_OUTLINED,
        [
            ft.Row(controls=[pin_status]),
            ft.Text(
                "Proteges vos depenses avec un code PIN. Vous devrez le saisir pour acceder a la liste.",
                size=12, color=C_MUTED,
            ),
            pin_field,
            pin_error,
            ft.Row(
                spacing=10,
                controls=[
                    ft.ElevatedButton(
                        "Definir le PIN",
                        icon=ft.Icons.LOCK,
                        on_click=set_pin,
                        expand=True,
                        style=ft.ButtonStyle(
                            bgcolor=C_PRIMARY, color=ft.Colors.WHITE,
                            shape=ft.RoundedRectangleBorder(radius=10),
                            padding=ft.padding.symmetric(vertical=10),
                        ),
                    ),
                    ft.OutlinedButton(
                        "Supprimer",
                        icon=ft.Icons.LOCK_OPEN,
                        on_click=remove_pin,
                        visible=has_pin,
                        style=ft.ButtonStyle(
                            color=C_ERROR,
                            side=ft.BorderSide(1, C_ERROR),
                            shape=ft.RoundedRectangleBorder(radius=10),
                            padding=ft.padding.symmetric(vertical=10),
                        ),
                    ),
                ],
            ),
        ],
    )

    # ── Fond d'ecran ─────────────────────────────────────────────────────

    current_wallpaper = db.get_wallpaper(uid)
    wallpaper_preview = ft.Container(
        border_radius=10,
        height=120,
        bgcolor="#E0E0E0",
        content=ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.IMAGE_NOT_SUPPORTED, color="#9E9E9E", size=36),
                ft.Text("Aucun fond d'ecran", size=12, color="#9E9E9E"),
            ],
        ),
    )

    if current_wallpaper:
        wallpaper_preview.content = ft.Image(
            src=current_wallpaper,
            fit=ft.BoxFit.COVER,
            border_radius=ft.BorderRadius(10, 10, 10, 10),
        )
        wallpaper_preview.bgcolor = None

    async def choose_wallpaper(e):
        files = await file_picker.pick_files(
            dialog_title="Choisir un fond d'ecran",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["png", "jpg", "jpeg", "webp"],
            with_data=True,
        )
        if files and files[0].bytes:
            b64_data = base64.b64encode(files[0].bytes).decode("ascii")
            db.set_wallpaper(uid, b64_data)
            def close(ev):
                Diag.close_dialog(page, dlg)
            dlg = Diag.success_dialog(page, message="Fond d'ecran mis a jour.", on_ok=close)
            navigate("/settings")

    def remove_wallpaper(e):
        db.set_wallpaper(uid, None)
        def close(ev):
            Diag.close_dialog(page, dlg)
        dlg = Diag.success_dialog(page, message="Fond d'ecran supprime.", on_ok=close)
        navigate("/settings")

    file_picker = ft.FilePicker()

    wallpaper_section = _section(
        "Fond d'ecran",
        ft.Icons.WALLPAPER,
        [
            wallpaper_preview,
            ft.Row(
                spacing=10,
                controls=[
                    ft.ElevatedButton(
                        "Choisir une image",
                        icon=ft.Icons.IMAGE,
                        on_click=choose_wallpaper,
                        expand=True,
                        style=ft.ButtonStyle(
                            bgcolor=C_PRIMARY, color=ft.Colors.WHITE,
                            shape=ft.RoundedRectangleBorder(radius=10),
                            padding=ft.padding.symmetric(vertical=10),
                        ),
                    ),
                    ft.OutlinedButton(
                        "Supprimer",
                        icon=ft.Icons.DELETE_OUTLINE,
                        on_click=remove_wallpaper,
                        visible=bool(current_wallpaper),
                        style=ft.ButtonStyle(
                            color=C_ERROR,
                            side=ft.BorderSide(1, C_ERROR),
                            shape=ft.RoundedRectangleBorder(radius=10),
                            padding=ft.padding.symmetric(vertical=10),
                        ),
                    ),
                ],
            ),
        ],
    )

    # ── Compte ────────────────────────────────────────────────────────────

    def logout(e):
        def do_logout(e2):
            Diag.close_dialog(page, dlg)
            session["user"] = None
            session["section_unlocked"] = False
            navigate("/login")

        def cancel(e2):
            Diag.close_dialog(page, dlg)

        dlg = Diag.ask_dialog(
            page,
            title="Deconnexion",
            message="Voulez-vous vous deconnecter ?",
            on_oui=do_logout,
            on_non=cancel,
        )

    account_section = _section(
        "Mon compte",
        ft.Icons.ACCOUNT_CIRCLE_OUTLINED,
        [
            ft.Row(
                spacing=12,
                controls=[
                    ft.CircleAvatar(
                        content=ft.Text(
                            user["nom"][0].upper() if user["nom"] else "?",
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.WHITE,
                            size=20,
                        ),
                        bgcolor=C_PRIMARY,
                        radius=24,
                    ),
                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text(user["nom"], size=16, weight=ft.FontWeight.W_600, color=C_TEXT),
                            ft.Text(f"@{user['username']}", size=13, color=C_MUTED),
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                                border_radius=20,
                                bgcolor="#E8F5E9" if user["role"] == "admin" else "#EDE7F6",
                                content=ft.Text(
                                    user["role"].upper(), size=11,
                                    color=C_PRIMARY if user["role"] == "admin" else "#6A1B9A",
                                    weight=ft.FontWeight.W_600,
                                ),
                            ),
                        ],
                    ),
                ],
            ),
            ft.Row([
                ft.ElevatedButton(
                    "Se deconnecter",
                    icon=ft.Icons.LOGOUT,
                    on_click=logout,
                    expand=True,
                    style=ft.ButtonStyle(
                        bgcolor=C_ERROR, color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.padding.symmetric(vertical=10),
                    ),
                )
            ]),
        ],
    )

    back_route = "/admin" if user["role"] == "admin" else "/expenses"

    return ft.View(
        route="/settings",
        bgcolor=C_BG,
        scroll=ft.ScrollMode.AUTO,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        appbar=ft.AppBar(
            title=ft.Text("Parametres", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            bgcolor=C_PRIMARY,
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                icon_color=ft.Colors.WHITE,
                on_click=lambda e: navigate(back_route),
            ),
        ),
        controls=[
            ft.Container(
                padding=ft.padding.symmetric(horizontal=14, vertical=14),
                content=ft.Column(
                    spacing=14,
                    controls=[
                        account_section,
                        password_section,
                        pin_section,
                        wallpaper_section,
                    ],
                ),
            )
        ],
    )
