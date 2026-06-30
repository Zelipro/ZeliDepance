import flet as ft

import database as db
from views.login_view import build_login_view
from views.register_view import build_register_view
from views.expenses_view import build_expenses_view
from views.admin_view import build_admin_view
from views.settings_view import build_settings_view


def main(page: ft.Page) -> None:
    db.init_db()

    page.title = "ZeliDepense"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.bgcolor = "#F4F7F9"

    session: dict = {"user": None, "section_unlocked": False}

    def navigate(route: str) -> None:
        page.go(route)

    def route_change(e: ft.RouteChangeEvent) -> None:
        page.views.clear()
        route = page.route

        if not session["user"] or route in ("/", "/login"):
            page.views.append(build_login_view(page, session, navigate))
        elif route == "/register":
            page.views.append(build_register_view(page, session, navigate))
        elif route == "/expenses":
            page.views.append(build_expenses_view(page, session, navigate))
        elif route == "/admin":
            if session["user"]["role"] == "admin":
                page.views.append(build_admin_view(page, session, navigate))
            else:
                page.views.append(build_expenses_view(page, session, navigate))
        elif route == "/settings":
            page.views.append(build_settings_view(page, session, navigate))
        else:
            page.views.append(build_login_view(page, session, navigate))

        page.update()

    def view_pop(e: ft.ViewPopEvent) -> None:
        if len(page.views) > 1:
            page.views.pop()
            page.go(page.views[-1].route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go("/login")


if __name__ == "__main__":
    ft.run(main)
