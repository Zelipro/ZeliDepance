# --- SETTINGS MENU : Menu paramètres (couleur, fond, sync) ---

import flet as ft
from app.db.preferences import (
    get_primary_color, get_bg_color, get_bg_image,
    set_primary_color, set_bg_color, set_bg_image,
)

# ── Couleurs disponibles ──────────────────────────────────────────────────
PRIMARY_COLORS = [
    {"label": "Vert",   "value": "#2E7D32"},
    {"label": "Bleu",   "value": "#1565C0"},
    {"label": "Rouge",  "value": "#C62828"},
    {"label": "Jaune",  "value": "#F9A825"},
    {"label": "Violet", "value": "#6A1B9A"},
    {"label": "Cyan",   "value": "#00838F"},
]

BG_COLORS = [
    {"label": "Gris clair", "value": "#F4F7F9"},
    {"label": "Blanc",      "value": "#FFFFFF"},
    {"label": "Noir",       "value": "#121212"},
    {"label": "Bleu nuit",  "value": "#0D1B2A"},
    {"label": "Beige",      "value": "#FDF6EC"},
    {"label": "Vert sombre","value": "#1B2E1F"},
]


def _color_chip(color: str, label: str, selected: dict, key: str, on_select, page: ft.Page) -> ft.Container:
    """Crée un chip de couleur cliquable."""
    is_selected = selected[key] == color

    def handle_click(_):
        selected[key] = color
        on_select()

    return ft.Container(
        width=70,
        height=70,
        border_radius=10,
        bgcolor=color,
        border=ft.Border(left=ft.BorderSide(4 if is_selected else 1,"#FFFFFF" if is_selected else "#E0E0E0"),right=ft.BorderSide(4 if is_selected else 1,"#FFFFFF" if is_selected else "#E0E0E0"),top=ft.BorderSide(4 if is_selected else 1,"#FFFFFF" if is_selected else "#E0E0E0"),bottom=ft.BorderSide(4 if is_selected else 1,"#FFFFFF" if is_selected else "#E0E0E0")),
        shadow=ft.BoxShadow(
            blur_radius=8 if is_selected else 2,
            color="#00000055" if is_selected else "#00000022",
        ),
        content=ft.Column(
            alignment=ft.MainAxisAlignment.END,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    bgcolor="#00000066",
                    border_radius=ft.BorderRadius(top_left=0, top_right=0, bottom_left=8, bottom_right=8),
                    padding=ft.Padding(0, 2, 0, 4),
                    content=ft.Text(label, size=10, color="#FFFFFF", text_align=ft.TextAlign.CENTER),
                    width=70,
                ),
            ],
        ),
        on_click=handle_click,
    )


def open_settings(page: ft.Page, on_apply) -> None:
    """Ouvre le panneau de paramètres dans un BottomSheet."""

    current_primary = get_primary_color()
    current_bg      = get_bg_color()
    current_image   = get_bg_image()

    selected = {
        "primary": current_primary,
        "bg":      current_bg,
    }
    selected_image = {"value": current_image}

    primary_container = ft.Ref[ft.Container]()
    bg_container_ref  = ft.Ref[ft.Container]()

    primary_cont = ft.Container()
    bg_cont      = ft.Container()

    def build_primary_chips():
        return ft.Row(
            wrap=True,
            spacing=10,
            run_spacing=10,
            controls=[
                _color_chip(c["value"], c["label"], selected, "primary", rebuild_chips, page)
                for c in PRIMARY_COLORS
            ],
        )

    def build_bg_chips():
        return ft.Row(
            wrap=True,
            spacing=10,
            run_spacing=10,
            controls=[
                _color_chip(c["value"], c["label"], selected, "bg", rebuild_chips, page)
                for c in BG_COLORS
            ],
        )

    def rebuild_chips():
        primary_cont.content = build_primary_chips()
        bg_cont.content      = build_bg_chips()
        page.update()

    primary_cont.content = build_primary_chips()
    bg_cont.content      = build_bg_chips()

    # ── Image de fond ─────────────────────────────────────────────────────
    image_path_field = ft.TextField(
        label="Chemin de l'image de fond (optionnel)",
        hint_text="Ex: /storage/emulated/0/Pictures/fond.jpg",
        value=current_image,
        prefix_icon=ft.Icons.IMAGE_OUTLINED,
        border_radius=10,
        expand=True,
        on_change=lambda e: selected_image.update({"value": e.control.value.strip()}),
    )

    def clear_image(_):
        image_path_field.value = ""
        selected_image["value"] = ""
        page.update()

    image_section = ft.Column(
        spacing=8,
        controls=[
            ft.Row(controls=[
                ft.Icon(ft.Icons.WALLPAPER, color="#616161"),
                ft.Text("Image de fond", size=15, weight=ft.FontWeight.W_600),
            ]),
            ft.Row(controls=[
                image_path_field,
                ft.IconButton(ft.Icons.CLEAR, icon_color="#C62828", on_click=clear_image),
            ]),
            ft.Text("💡 Entrez le chemin complet vers votre image", size=11, color="#9E9E9E", italic=True),
        ],
    )

    # ── Sync ──────────────────────────────────────────────────────────────
    sync_status = ft.Text("", size=13)

    def handle_sync(_):
        from app.db.sync import is_online, run_sync
        sync_status.value = "⏳ Synchronisation en cours..."
        sync_status.color = "#F59E0B"
        page.update()
        result = run_sync()
        if not result["online"]:
            sync_status.value = "📴 Pas de connexion internet"
            sync_status.color  = "#C62828"
        elif result["synced"]:
            sync_status.value = "✅ Synchronisation réussie !"
            sync_status.color  = "#2E7D32"
        else:
            sync_status.value = f"⚠️ Erreur : {result.get('error', 'Inconnue')}"
            sync_status.color  = "#D97706"
        page.update()

    sync_section = ft.Column(
        spacing=8,
        controls=[
            ft.Row(controls=[
                ft.Icon(ft.Icons.SYNC, color="#616161"),
                ft.Text("Synchronisation", size=15, weight=ft.FontWeight.W_600),
            ]),
            ft.ElevatedButton(
                "🔄 Synchroniser maintenant",
                bgcolor="#1565C0",
                color="#FFFFFF",
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                on_click=handle_sync,
            ),
            sync_status,
        ],
    )

    # ── Appliquer / Annuler ───────────────────────────────────────────────
    def handle_apply(_):
        set_primary_color(selected["primary"])
        set_bg_color(selected["bg"])
        set_bg_image(selected_image["value"])
        bottom_sheet.open = False
        page.update()
        on_apply(selected["primary"], selected["bg"], selected_image["value"])

    def handle_cancel(_):
        bottom_sheet.open = False
        page.update()

    # ── BottomSheet ───────────────────────────────────────────────────────
    bottom_sheet = ft.BottomSheet(
        content=ft.Container(
            padding=20,
            content=ft.Column(
                scroll=ft.ScrollMode.AUTO,
                height=600,
                spacing=20,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("⚙️ Paramètres", size=20, weight=ft.FontWeight.BOLD),
                            ft.IconButton(ft.Icons.CLOSE, on_click=handle_cancel),
                        ],
                    ),
                    ft.Divider(),
                    sync_section,
                    ft.Divider(),
                    ft.Column(spacing=10, controls=[
                        ft.Row(controls=[
                            ft.Icon(ft.Icons.PALETTE, color="#616161"),
                            ft.Text("Couleur principale", size=15, weight=ft.FontWeight.W_600),
                        ]),
                        primary_cont,
                    ]),
                    ft.Divider(),
                    ft.Column(spacing=10, controls=[
                        ft.Row(controls=[
                            ft.Icon(ft.Icons.FORMAT_COLOR_FILL, color="#616161"),
                            ft.Text("Couleur de fond", size=15, weight=ft.FontWeight.W_600),
                        ]),
                        bg_cont,
                    ]),
                    ft.Divider(),
                    image_section,
                    ft.Divider(),
                    ft.Row(
                        spacing=10,
                        controls=[
                            ft.ElevatedButton(
                                "✅ Appliquer",
                                bgcolor="#2E7D32",
                                color="#FFFFFF",
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                                on_click=handle_apply,
                                expand=True,
                            ),
                            ft.OutlinedButton(
                                "Annuler",
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                                on_click=handle_cancel,
                                expand=True,
                            ),
                        ],
                    ),
                    ft.Container(height=20),
                ],
            ),
        ),
        open=True,
    )

    page.overlay.append(bottom_sheet)
    page.update()
