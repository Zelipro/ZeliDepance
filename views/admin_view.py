import flet as ft
import database as db
import Dialog as Diag

C_PRIMARY = "#2E7D32"
C_DARK = "#1B5E20"
C_BG = "#F4F7F9"
C_SURFACE = "#FFFFFF"
C_ERROR = "#C62828"
C_ADMIN = "#6A1B9A"
C_WARNING = "#F57C00"
C_TEXT = "#1A1A1A"
C_MUTED = "#616161"


def build_admin_view(page: ft.Page, session: dict, navigate) -> ft.View:
    user = session["user"]

    users_list = ft.Column(spacing=10)
    stats_row = ft.Row(spacing=10)

    def _stat_card(label, value, icon, color):
        return ft.Card(
            elevation=2,
            expand=True,
            content=ft.Container(
                bgcolor=C_SURFACE,
                border_radius=12,
                padding=14,
                content=ft.Column(
                    spacing=6,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(icon, color=color, size=28),
                        ft.Text(str(value), size=22, weight=ft.FontWeight.BOLD, color=color),
                        ft.Text(label, size=12, color=C_MUTED, text_align=ft.TextAlign.CENTER),
                    ],
                ),
            ),
        )

    def _user_card(u: dict) -> ft.Card:
        is_admin_account = u["username"] == "Deg"
        approved = u["is_approved"] == 1
        role_color = C_ADMIN if u["role"] == "admin" else C_PRIMARY
        status_color = C_PRIMARY if approved else C_WARNING

        actions = []
        if not is_admin_account:
            if not approved:
                actions.append(
                    ft.ElevatedButton(
                        "Approuver",
                        icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                        style=ft.ButtonStyle(
                            bgcolor=C_PRIMARY, color=ft.Colors.WHITE,
                            shape=ft.RoundedRectangleBorder(radius=8),
                            padding=ft.padding.symmetric(horizontal=12, vertical=8),
                        ),
                        on_click=lambda e, uid=u["id"]: _approve(uid, True),
                    )
                )
            else:
                actions.append(
                    ft.OutlinedButton(
                        "Suspendre",
                        icon=ft.Icons.BLOCK,
                        style=ft.ButtonStyle(
                            color=C_WARNING,
                            side=ft.BorderSide(1, C_WARNING),
                            shape=ft.RoundedRectangleBorder(radius=8),
                            padding=ft.padding.symmetric(horizontal=12, vertical=8),
                        ),
                        on_click=lambda e, uid=u["id"]: _approve(uid, False),
                    )
                )
            actions.append(
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_color=C_ERROR,
                    tooltip="Supprimer l'utilisateur",
                    on_click=lambda e, uid=u["id"], uname=u["username"]: _confirm_delete(uid, uname),
                )
            )

        dep_count = db.get_depenses_count(u["id"])
        dep_total = db.calcul_total(u["id"])

        return ft.Card(
            elevation=2,
            content=ft.Container(
                bgcolor=C_SURFACE,
                border_radius=12,
                padding=14,
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Row(
                                    spacing=10,
                                    controls=[
                                        ft.CircleAvatar(
                                            content=ft.Text(
                                                u["nom"][0].upper() if u["nom"] else "?",
                                                weight=ft.FontWeight.BOLD,
                                                color=ft.Colors.WHITE,
                                            ),
                                            bgcolor=role_color,
                                            radius=20,
                                        ),
                                        ft.Column(
                                            spacing=2,
                                            controls=[
                                                ft.Text(u["nom"], size=15, weight=ft.FontWeight.W_600, color=C_TEXT),
                                                ft.Text(f"@{u['username']}", size=12, color=C_MUTED),
                                            ],
                                        ),
                                    ],
                                ),
                                ft.Column(
                                    spacing=4,
                                    horizontal_alignment=ft.CrossAxisAlignment.END,
                                    controls=[
                                        ft.Container(
                                            padding=ft.padding.symmetric(horizontal=8, vertical=3),
                                            border_radius=20,
                                            bgcolor="#EDE7F6" if u["role"] == "admin" else "#E8F5E9",
                                            content=ft.Text(
                                                u["role"].upper(),
                                                size=11,
                                                color=role_color,
                                                weight=ft.FontWeight.W_600,
                                            ),
                                        ),
                                        ft.Container(
                                            padding=ft.padding.symmetric(horizontal=8, vertical=3),
                                            border_radius=20,
                                            bgcolor="#FFF3E0" if not approved else "#E8F5E9",
                                            content=ft.Text(
                                                "En attente" if not approved else "Actif",
                                                size=11,
                                                color=status_color,
                                                weight=ft.FontWeight.W_500,
                                            ),
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        ft.Divider(height=1, color="#F5F5F5"),
                        ft.Row(
                            spacing=16,
                            controls=[
                                ft.Row(spacing=4, controls=[
                                    ft.Icon(ft.Icons.RECEIPT, size=14, color=C_MUTED),
                                    ft.Text(f"{dep_count} depenses", size=12, color=C_MUTED),
                                ]),
                                ft.Row(spacing=4, controls=[
                                    ft.Icon(ft.Icons.ATTACH_MONEY, size=14, color=C_MUTED),
                                    ft.Text(f"Total : {dep_total:.2f}", size=12, color=C_MUTED),
                                ]),
                            ],
                        ),
                        ft.Text(
                            f"Inscrit le : {u['created_at'][:10] if u['created_at'] else '—'}",
                            size=11, color=C_MUTED, italic=True,
                        ),
                        ft.Row(actions, spacing=8) if actions else ft.Container(),
                    ],
                ),
            ),
        )

    def _approve(uid, approved):
        db.approve_user(uid, approved)
        msg = "Utilisateur approuve." if approved else "Utilisateur suspendu."

        def close(e):
            Diag.close_dialog(page, dlg)

        dlg = Diag.success_dialog(page, message=msg, on_ok=close)
        refresh()

    def _confirm_delete(uid, uname):
        def do_delete(e):
            Diag.close_dialog(page, dlg)
            db.delete_user(uid)
            refresh()

        def cancel(e):
            Diag.close_dialog(page, dlg)

        dlg = Diag.ask_dialog(
            page,
            title="Confirmation",
            message=f"Supprimer l'utilisateur @{uname} et toutes ses depenses ?",
            on_oui=do_delete,
            on_non=cancel,
        )

    def refresh():
        all_users = db.get_all_users()
        total_users = len(all_users)
        pending = sum(1 for u in all_users if not u["is_approved"])
        total_depenses = db.get_depenses_count()

        stats_row.controls = [
            _stat_card("Utilisateurs", total_users, ft.Icons.GROUP, C_PRIMARY),
            _stat_card("En attente", pending, ft.Icons.PENDING, C_WARNING),
            _stat_card("Depenses", total_depenses, ft.Icons.RECEIPT_LONG, C_ADMIN),
        ]

        users_list.controls.clear()
        if not all_users:
            users_list.controls.append(
                ft.Container(
                    padding=20,
                    content=ft.Text("Aucun utilisateur.", italic=True, color=C_MUTED),
                )
            )
        else:
            for u in all_users:
                users_list.controls.append(_user_card(u))

        page.update()

    # Initialisation
    all_users_init = db.get_all_users()
    total_users_init = len(all_users_init)
    pending_init = sum(1 for u in all_users_init if not u["is_approved"])
    total_dep_init = db.get_depenses_count()

    stats_row.controls = [
        _stat_card("Utilisateurs", total_users_init, ft.Icons.GROUP, C_PRIMARY),
        _stat_card("En attente", pending_init, ft.Icons.PENDING, C_WARNING),
        _stat_card("Depenses total", total_dep_init, ft.Icons.RECEIPT_LONG, C_ADMIN),
    ]

    for u in all_users_init:
        users_list.controls.append(_user_card(u))

    return ft.View(
        route="/admin",
        bgcolor=C_BG,
        scroll=ft.ScrollMode.AUTO,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        appbar=ft.AppBar(
            title=ft.Text("Administration", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            bgcolor=C_ADMIN,
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                icon_color=ft.Colors.WHITE,
                on_click=lambda e: navigate("/expenses"),
                tooltip="Mes depenses",
            ),
            actions=[
                ft.IconButton(
                    icon=ft.Icons.REFRESH,
                    icon_color=ft.Colors.WHITE,
                    tooltip="Actualiser",
                    on_click=lambda e: refresh(),
                ),
                ft.IconButton(
                    icon=ft.Icons.SETTINGS,
                    icon_color=ft.Colors.WHITE,
                    tooltip="Parametres",
                    on_click=lambda e: navigate("/settings"),
                ),
            ],
        ),
        controls=[
            ft.Container(
                padding=ft.padding.symmetric(horizontal=14, vertical=14),
                content=ft.Column(
                    spacing=16,
                    controls=[
                        ft.Text("Vue d'ensemble", size=18, weight=ft.FontWeight.BOLD, color=C_TEXT),
                        stats_row,
                        ft.Divider(color="#E0E0E0"),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text("Utilisateurs", size=16, weight=ft.FontWeight.BOLD, color=C_TEXT),
                                ft.IconButton(
                                    icon=ft.Icons.REFRESH,
                                    icon_color=C_MUTED,
                                    icon_size=20,
                                    on_click=lambda e: refresh(),
                                ),
                            ],
                        ),
                        users_list,
                    ],
                ),
            )
        ],
    )
