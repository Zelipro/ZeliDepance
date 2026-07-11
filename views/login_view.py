import flet as ft
import database as db

C_PRIMARY = "#2E7D32"
C_DARK = "#1B5E20"
C_BG = "#F4F7F9"
C_ERROR = "#C62828"


def build_login_view(page: ft.Page, session: dict, navigate) -> ft.View:
    username_field = ft.TextField(
        label="Nom d'utilisateur",
        prefix_icon=ft.Icons.PERSON_OUTLINE,
        border_radius=12,
        focused_border_color=C_PRIMARY,
    )
    password_field = ft.TextField(
        label="Mot de passe",
        prefix_icon=ft.Icons.LOCK_OUTLINE,
        password=True,
        can_reveal_password=True,
        border_radius=12,
        focused_border_color=C_PRIMARY,
    )
    error_text = ft.Text("", color=C_ERROR, size=13, visible=False)

    def login(e):
        error_text.visible = False
        if not username_field.value or not password_field.value:
            error_text.value = "Veuillez remplir tous les champs."
            error_text.visible = True
            page.update()
            return

        user = db.authenticate(username_field.value.strip(), password_field.value)
        if not user:
            error_text.value = "Identifiant ou mot de passe incorrect."
            error_text.visible = True
            page.update()
            return

        if not user["is_approved"] and user["role"] != "admin":
            error_text.value = "Votre compte est en attente d'approbation par l'administrateur."
            error_text.visible = True
            page.update()
            return

        session["user"] = user
        session["section_unlocked"] = not db.has_section_pin(user["id"])
        navigate("/admin" if user["role"] == "admin" else "/expenses")

    password_field.on_submit = login

    return ft.View(
        route="/login",
        bgcolor=C_BG,
        padding=0,
        scroll=ft.ScrollMode.AUTO,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            ft.Column(
                spacing=0,
                expand=True,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    # Header degrade vert
                    ft.Container(
                        padding=ft.Padding.symmetric(vertical=48, horizontal=24),
                        gradient=ft.LinearGradient(
                            begin=ft.Alignment.TOP_CENTER,
                            end=ft.Alignment.BOTTOM_CENTER,
                            colors=[C_DARK, C_PRIMARY],
                        ),
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=10,
                            controls=[
                                ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET, color=ft.Colors.WHITE, size=64),
                                ft.Text(
                                    "ZeliDepense",
                                    size=30,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.WHITE,
                                ),
                                ft.Text(
                                    "Gestion des depenses",
                                    size=14,
                                    color=ft.Colors.WHITE70,
                                ),
                            ],
                        ),
                    ),
                    # Formulaire de connexion
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=24, vertical=32),
                        content=ft.Column(
                            spacing=16,
                            controls=[
                                ft.Text(
                                    "Connexion",
                                    size=22,
                                    weight=ft.FontWeight.BOLD,
                                    color="#1A1A1A",
                                ),
                                username_field,
                                password_field,
                                error_text,
                                ft.Container(height=4),
                                ft.Row([
                                    ft.ElevatedButton(
                                        "Se connecter",
                                        icon=ft.Icons.LOGIN,
                                        on_click=login,
                                        expand=True,
                                        style=ft.ButtonStyle(
                                            bgcolor=C_PRIMARY,
                                            color=ft.Colors.WHITE,
                                            shape=ft.RoundedRectangleBorder(radius=12),
                                            padding=ft.Padding.symmetric(vertical=14),
                                        ),
                                    )
                                ]),
                                ft.Divider(color="#E0E0E0"),
                                ft.Row(
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    controls=[
                                        ft.Text("Pas encore de compte ?", color="#616161", size=13),
                                        ft.TextButton(
                                            "S'inscrire",
                                            on_click=lambda e: navigate("/register"),
                                            style=ft.ButtonStyle(color=C_PRIMARY),
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ),
                ],
            )
        ],
    )
