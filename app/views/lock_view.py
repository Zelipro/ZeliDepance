# --- LOCK VIEW : Page de verrouillage / connexion ---
import flet as ft
import Dialog as Diag
from app.db.auth import check_login
from app.db.preferences import get_primary_color, init_preferences_db
from app.navigation import navigate


def diag(pg, msg=None):
    def close(e):
        Diag.close_dialog(pg, digg)
    digg = Diag.custom_dialog(
        page=pg,
        title="Information",
        content_widget=ft.Column(
            [
                ft.Row([
                    ft.Text("Author Name:", color="red", weight=ft.FontWeight.BOLD),
                    ft.Text("Elisée ATIKPO", color="blue", weight=ft.FontWeight.BOLD),
                ]),
                ft.Row([
                    ft.Text("Contact:", color="red", weight=ft.FontWeight.BOLD),
                    ft.Text("+228 96 44 40 55", color="blue", weight=ft.FontWeight.BOLD),
                ]),
                ft.Row([
                    ft.Text("Year:", color="red", weight=ft.FontWeight.BOLD),
                    ft.Text("2026", color="blue", weight=ft.FontWeight.BOLD),
                ]),
            ],
            height=100,
            width=400,
        ),
        actions=[ft.TextButton("Fermer", on_click=close)],
    )


def build_lock_view(page: ft.Page) -> ft.Column:
    init_preferences_db()
    primary_color = get_primary_color()

    page.appbar     = None
    page.title      = "Gestion des Dépenses"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor    = primary_color
    page.padding    = 0

    identifiant_field = ft.TextField(
        label="Username",
        label_style=ft.TextStyle(color="#9E9E9E", size=13),
        prefix_icon=ft.Icons.PERSON_OUTLINE,
        border=ft.InputBorder.UNDERLINE,
        border_color="#E0E0E0",
        focused_border_color=primary_color,
        color="#212121",
        cursor_color=primary_color,
        bgcolor=ft.Colors.TRANSPARENT,
        width=280,
    )

    password_field = ft.TextField(
        label="Password",
        label_style=ft.TextStyle(color="#9E9E9E", size=13),
        prefix_icon=ft.Icons.LOCK_OUTLINE,
        password=True,
        can_reveal_password=True,
        border=ft.InputBorder.UNDERLINE,
        border_color="#E0E0E0",
        focused_border_color=primary_color,
        color="#212121",
        cursor_color=primary_color,
        bgcolor=ft.Colors.TRANSPARENT,
        width=280,
    )

    def handle_login(e):
        if not identifiant_field.value or not password_field.value:
            Diag.error_dialog(page, "Veuillez remplir tous les champs.")
            return
        if check_login(identifiant_field.value, password_field.value):
            snack = ft.SnackBar(ft.Text("Bienvenue Zeli 👋"), bgcolor=primary_color)
            page.overlay.append(snack)
            snack.open = True
            page.update()
            navigate(page, "accueil")
        else:
            Diag.error_dialog(page, "Identifiant ou mot de passe incorrect.")

    password_field.on_submit = handle_login

    login_button = ft.Container(
        width=280,
        height=48,
        border_radius=24,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1, 0),
            end=ft.Alignment(1, 0),
            colors=[primary_color, primary_color],
        ),
        content=ft.TextButton(
            "LOGIN",
            style=ft.ButtonStyle(
                color="#FFFFFF",
                overlay_color=ft.Colors.with_opacity(0.1, "#FFFFFF"),
                padding=ft.Padding(0, 12, 0, 12),
            ),
            on_click=handle_login,
            expand=True,
        ),
    )

    forgot_row = ft.TextButton(
        "Information",
        icon=ft.Icon(ft.Icons.INFO_OUTLINE, color="#9E9E9E"),
        style=ft.ButtonStyle(
            color="#9E9E9E",
            overlay_color=ft.Colors.with_opacity(0.1, "#9E9E9E"),
            padding=ft.Padding(8, 4, 8, 4),
        ),
        on_click=lambda e: diag(page),
    )

    # Avatar avec bordure blanche — on utilise un Container imbriqué au lieu de border
    avatar_circle = ft.Container(
        width=72,
        height=72,
        border_radius=36,
        bgcolor="#FFFFFF",
        content=ft.Container(
            width=64,
            height=64,
            border_radius=32,
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=[primary_color, primary_color],
            ),
            content=ft.Icon(ft.Icons.PERSON, color="#FFFFFF", size=36),
            alignment=ft.Alignment(0, 0),
        ),
        alignment=ft.Alignment(0, 0),
    )

    login_card = ft.Container(
        width=340,
        border_radius=ft.BorderRadius(
            top_left=30, top_right=30, bottom_left=16, bottom_right=16
        ),
        bgcolor="#FFFFFF",
        padding=ft.Padding(30, 50, 30, 30),
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=24,
            controls=[
                ft.Text("LOGIN", size=20, weight=ft.FontWeight.BOLD, color="#212121"),
                identifiant_field,
                password_field,
                ft.Container(height=4),
                login_button,
                forgot_row,
            ],
        ),
    )

    card_with_avatar = ft.Stack(
        width=340,
        controls=[
            ft.Container(
                margin=ft.Margin(0, 36, 0, 0),
                content=ft.Column([login_card, ft.Container(height=20)]),
            ),
            ft.Container(
                width=340,
                alignment=ft.Alignment(0, -1),
                content=avatar_circle,
            ),
        ],
    )

    return ft.Column(
        expand=True,
        spacing=0,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.END,
        controls=[
            ft.Row(
                expand=True,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text(
                                "Gestion des Dépenses",
                                size=22,
                                weight=ft.FontWeight.BOLD,
                                color="#FFFFFF",
                            ),
                            ft.Text(
                                "Connectez-vous pour continuer",
                                size=13,
                                color=ft.Colors.with_opacity(0.75, "#FFFFFF"),
                            ),
                        ],
                    ),
                ],
            ),
            card_with_avatar,
        ],
    )
