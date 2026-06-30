import flet as ft
import database as db

C_PRIMARY = "#2E7D32"
C_BG = "#F4F7F9"
C_ERROR = "#C62828"


def build_register_view(page: ft.Page, session: dict, navigate) -> ft.View:
    username_field = ft.TextField(
        label="Nom d'utilisateur",
        prefix_icon=ft.Icons.PERSON_OUTLINE,
        border_radius=12,
        focused_border_color=C_PRIMARY,
    )
    nom_field = ft.TextField(
        label="Nom complet",
        prefix_icon=ft.Icons.BADGE_OUTLINED,
        border_radius=12,
        focused_border_color=C_PRIMARY,
    )
    password_field = ft.TextField(
        label="Mot de passe (min. 6 caracteres)",
        prefix_icon=ft.Icons.LOCK_OUTLINE,
        password=True,
        can_reveal_password=True,
        border_radius=12,
        focused_border_color=C_PRIMARY,
    )
    confirm_field = ft.TextField(
        label="Confirmer le mot de passe",
        prefix_icon=ft.Icons.LOCK_RESET,
        password=True,
        can_reveal_password=True,
        border_radius=12,
        focused_border_color=C_PRIMARY,
    )
    error_text = ft.Text("", color=C_ERROR, size=13, visible=False)

    def register(e):
        error_text.visible = False
        if not all([username_field.value, nom_field.value, password_field.value, confirm_field.value]):
            error_text.value = "Veuillez remplir tous les champs."
            error_text.visible = True
            page.update()
            return
        if len(password_field.value) < 6:
            error_text.value = "Le mot de passe doit contenir au moins 6 caracteres."
            error_text.visible = True
            page.update()
            return
        if password_field.value != confirm_field.value:
            error_text.value = "Les mots de passe ne correspondent pas."
            error_text.visible = True
            page.update()
            return

        success, msg = db.create_user(
            username_field.value.strip(),
            nom_field.value.strip(),
            password_field.value,
        )

        if success:
            dlg = ft.AlertDialog(
                title=ft.Row(controls=[
                    ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=C_PRIMARY),
                    ft.Text("Compte cree", color=C_PRIMARY, weight=ft.FontWeight.W_600),
                ]),
                content=ft.Text(msg, size=14),
                actions=[
                    ft.ElevatedButton(
                        "OK",
                        bgcolor=C_PRIMARY,
                        color=ft.Colors.WHITE,
                        on_click=lambda e: (
                            setattr(dlg, "open", False),
                            page.update(),
                            navigate("/login"),
                        ),
                    )
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            if dlg not in page.overlay:
                page.overlay.append(dlg)
            dlg.open = True
            page.update()
        else:
            error_text.value = msg
            error_text.visible = True
            page.update()

    confirm_field.on_submit = register

    return ft.View(
        route="/register",
        bgcolor=C_BG,
        scroll=ft.ScrollMode.AUTO,
        appbar=ft.AppBar(
            title=ft.Text("Creer un compte", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            bgcolor=C_PRIMARY,
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                icon_color=ft.Colors.WHITE,
                on_click=lambda e: navigate("/login"),
            ),
        ),
        controls=[
            ft.Container(
                padding=ft.padding.symmetric(horizontal=24, vertical=24),
                content=ft.Column(
                    spacing=16,
                    controls=[
                        ft.Text("Informations du compte", size=15, color="#616161", weight=ft.FontWeight.W_500),
                        username_field,
                        nom_field,
                        ft.Divider(color="#E0E0E0"),
                        ft.Text("Securite", size=15, color="#616161", weight=ft.FontWeight.W_500),
                        password_field,
                        confirm_field,
                        error_text,
                        ft.Container(height=4),
                        ft.Row([
                            ft.ElevatedButton(
                                "Creer mon compte",
                                icon=ft.Icons.PERSON_ADD,
                                on_click=register,
                                expand=True,
                                style=ft.ButtonStyle(
                                    bgcolor=C_PRIMARY,
                                    color=ft.Colors.WHITE,
                                    shape=ft.RoundedRectangleBorder(radius=12),
                                    padding=ft.padding.symmetric(vertical=14),
                                ),
                            )
                        ]),
                        ft.Container(
                            padding=12,
                            border_radius=10,
                            bgcolor="#FFF3E0",
                            border=ft.border.all(1, "#FFB74D"),
                            content=ft.Row(
                                spacing=8,
                                controls=[
                                    ft.Icon(ft.Icons.INFO_OUTLINE, color="#F57C00", size=18),
                                    ft.Text(
                                        "Votre compte sera active apres validation par l'administrateur.",
                                        size=12,
                                        color="#E65100",
                                        expand=True,
                                    ),
                                ],
                            ),
                        ),
                    ],
                ),
            )
        ],
    )
