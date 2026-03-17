import os
import sqlite3
from datetime import datetime
import Dialog as Diag

import flet as ft
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

DB_NAME = "depenses.db"


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_NAME)


def init_db() -> None:
    with get_connection() as conn:
        con = conn.cursor()
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS depenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT,
                montant REAL,
                categorie TEXT,
                date TEXT
            )
            """
        )
        conn.commit()


def add_depense(description: str, montant: float, categorie: str, date: str) -> None:
    with get_connection() as conn:
        con = conn.cursor()
        con.execute(
            "INSERT INTO depenses(description, montant, categorie, date) VALUES (?, ?, ?, ?)",
            (description, montant, categorie, date),
        )
        conn.commit()


def get_depenses() -> list[tuple[int, str, float, str, str]]:
    with get_connection() as conn:
        con = conn.cursor()
        cursor = con.execute(
            "SELECT id, description, montant, categorie, date FROM depenses ORDER BY id DESC"
        )
        return cursor.fetchall()


def update_depense(
    depense_id: int, description: str, montant: float, categorie: str, date: str
) -> None:
    with get_connection() as conn:
        con = conn.cursor()
        con.execute(
            """
            UPDATE depenses
            SET description = ?, montant = ?, categorie = ?, date = ?
            WHERE id = ?
            """,
            (description, montant, categorie, date, depense_id),
        )
        conn.commit()


def delete_depense(depense_id: int) -> None:
    with get_connection() as conn:
        con = conn.cursor()
        con.execute("DELETE FROM depenses WHERE id = ?", (depense_id,))
        conn.commit()


def calcul_total() -> float:
    with get_connection() as conn:
        con = conn.cursor()
        con.execute("SELECT COALESCE(SUM(montant), 0) FROM depenses")
        result = con.fetchone()
        return float(result[0]) if result else 0.0


def generate_pdf(file_path: str) -> None:
    depenses = get_depenses()
    total = calcul_total()

    doc = SimpleDocTemplate(file_path, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Rapport des depenses", styles["Title"]))
    elements.append(Spacer(1, 12))

    table_data = [["Description", "Montant", "Categorie", "Date"]]
    for _, description, montant, categorie, date in depenses:
        table_data.append([description, f"{montant:.2f}", categorie, date])

    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E7D32")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
            ]
        )
    )

    elements.append(table)
    elements.append(Spacer(1, 14))
    elements.append(Paragraph(f"Total des depenses : {total:.2f}", styles["Heading3"]))

    doc.build(elements)


def main(page: ft.Page) -> None:
    init_db()

    page.title = "Gestion des Depenses"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 12
    page.bgcolor = "#F4F7F9"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.AUTO

    page.appbar = ft.AppBar(
        title=ft.Text("Gestion des Depenses", weight=ft.FontWeight.BOLD),
        center_title=True,
        bgcolor="#2E7D32",
        color=ft.Colors.WHITE,
    )

    edit_id: dict[str, int | None] = {"id": None}

    description_field = ft.TextField(
        label="Description",
        prefix_icon=ft.Icons.DESCRIPTION_OUTLINED,
        border_radius=10,
    )
    montant_field = ft.TextField(
        label="Montant",
        prefix_icon=ft.Icons.ATTACH_MONEY,
        keyboard_type=ft.KeyboardType.NUMBER,
        border_radius=10,
    )
    categorie_field = ft.TextField(
        label="Categorie",
        prefix_icon=ft.Icons.CATEGORY_OUTLINED,
        border_radius=10,
    )
    date_field = ft.TextField(
        label="Date (YYYY-MM-DD)",
        value=datetime.now().strftime("%Y-%m-%d"),
        prefix_icon=ft.Icons.CALENDAR_MONTH,
        border_radius=10,
    )

    total_text = ft.Text(
        value="Total des depenses : 0.00",
        size=18,
        weight=ft.FontWeight.BOLD,
        color="#1B5E20",
    )

    depenses_list = ft.ListView(spacing=10, expand=False, auto_scroll=False)
    list_container = ft.Container(
        visible=False,
        content=depenses_list,
        padding=ft.padding.only(bottom=10),
    )


    def clear_form() -> None:
        description_field.value = ""
        montant_field.value = ""
        categorie_field.value = ""
        date_field.value = datetime.now().strftime("%Y-%m-%d")
        edit_id["id"] = None
        submit_button_label.value = "Ajouter"

    def validate_form() -> tuple[bool, float]:
        if not description_field.value or not montant_field.value or not categorie_field.value or not date_field.value:
            Diag.error_dialog(
                page = page , 
                message="Veuillez remplir tous les champs.",
            )
            return False, 0.0

        try:
            montant = float(montant_field.value)
            if montant < 0:
                Diag.error_dialog(
                page = page , 
                message="Le montant doit etre positif.",
            )
                return False, 0.0
        except ValueError:
            Diag.error_dialog(
                page = page , 
                message="Le montant doit etre un nombre valide.",
            )
            return False, 0.0

        try:
            datetime.strptime(date_field.value, "%Y-%m-%d")
        except ValueError:
            Diag.error_dialog(
                page = page , 
                message="Format de date invalide. Utilisez YYYY-MM-DD.",
            )
            return False, 0.0

        return True, montant

    def refresh_depenses(_=None) -> None:
        depenses = get_depenses()
        depenses_list.controls.clear()
        list_container.visible = True

        if not depenses:
            depenses_list.controls.append(
                ft.Container(
                    content=ft.Text("Aucune depense enregistree.", italic=True),
                    padding=10,
                )
            )
        else:
            for depense_id, description, montant, categorie, date in depenses:
                depenses_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            bgcolor="#FFFFFF",
                            padding=10,
                            content=ft.Column(
                                spacing=8,
                                controls=[
                                    ft.Row(
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                        controls=[
                                            ft.Text(
                                                description,
                                                size=16,
                                                weight=ft.FontWeight.W_600,
                                            ),
                                            ft.Text(
                                                f"{montant:.2f}",
                                                color="#0D47A1",
                                                weight=ft.FontWeight.BOLD,
                                            ),
                                        ],
                                    ),
                                    ft.Row(
                                        controls=[
                                            ft.Icon(ft.Icons.CATEGORY, size=16, color="#616161"),
                                            ft.Text(categorie),
                                        ]
                                    ),
                                    ft.Row(
                                        controls=[
                                            ft.Icon(ft.Icons.DATE_RANGE, size=16, color="#616161"),
                                            ft.Text(date),
                                        ]
                                    ),
                                    ft.Row(
                                        alignment=ft.MainAxisAlignment.END,
                                        controls=[
                                            ft.IconButton(
                                                icon=ft.Icons.EDIT,
                                                on_click=lambda e, d=(
                                                    depense_id,
                                                    description,
                                                    montant,
                                                    categorie,
                                                    date,
                                                ): load_for_edit(d),
                                            ),
                                            ft.IconButton(
                                                icon=ft.Icons.DELETE,
                                                style=ft.ButtonStyle(
                                                    color="#C62828",
                                                ),
                                                on_click=lambda e, d_id=depense_id: remove_depense(d_id),
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ),
                    )
                )

        total_text.value = f"Total des depenses : {calcul_total():.2f}"
        page.update()

    def load_for_edit(depense_data: tuple[int, str, float, str, str]) -> None:
        depense_id, description, montant, categorie, date = depense_data
        edit_id["id"] = depense_id
        description_field.value = description
        montant_field.value = str(montant)
        categorie_field.value = categorie
        date_field.value = date
        submit_button_label.value = "Enregistrer"
        page.update()

    def remove_depense(depense_id: int) :
        def sup(e) :
            Diag.close_dialog(page , diag)
            
        delete_depense(depense_id)
        diag = Diag.success_dialog(
            page=page , 
            message= "Depense supprimee.",
            on_ok= sup
        )
        
        refresh_depenses()

    def save_depense(_):
        def sup(e):
            Diag.close_dialog(page , diag)
        
        def sup2(e):
            Diag.close_dialog(page , diag2)
            
        valid, montant = validate_form()
        if not valid:
            return

        description = description_field.value.strip()
        categorie = categorie_field.value.strip()
        date_value = date_field.value.strip()

        if edit_id["id"] is None:
            add_depense(description, montant, categorie, date_value)
            diag = Diag.success_dialog(
            page=page , 
            message= "Ajout effectue.",
            on_ok= sup
            )

        else:
            update_depense(edit_id["id"], description, montant, categorie, date_value)
            diag2=Diag.success_dialog(
            page=page ,
            message="Depense modifiee.",
            on_ok=sup2
            )

        clear_form()
        refresh_depenses()

    def create_pdf(_):
        def sup2(e):
            Diag.close_dialog(page , diag2)
        pdf_path = os.path.join(os.getcwd(), "rapport_depenses.pdf")
        generate_pdf(pdf_path)
        diag2 = Diag.success_dialog(
            page=page , 
            message= f"PDF genere: {pdf_path}",
            on_ok= sup2
        )


    submit_button_label = ft.Text("Ajouter", color="#FFFFFF", weight=ft.FontWeight.W_600)

    submit_button = ft.TextButton(
        content=ft.Row(
            controls=[ft.Icon(ft.Icons.ADD, color="#FFFFFF"), submit_button_label],
            alignment=ft.MainAxisAlignment.CENTER,
            tight=True,
        ),
        style=ft.ButtonStyle(
            bgcolor="#2E7D32",
            color="#FFFFFF",
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=12,
        ),
        on_click=save_depense,
    )

    liste_button = ft.TextButton(
        content=ft.Row(
            controls=[ft.Icon(ft.Icons.LIST, color="#FFFFFF"), ft.Text("Liste", color="#FFFFFF")],
            alignment=ft.MainAxisAlignment.CENTER,
            tight=True,
        ),
        style=ft.ButtonStyle(
            bgcolor="#1565C0",
            color="#FFFFFF",
            shape=ft.RoundedRectangleBorder(radius=10),
        ),
        on_click=refresh_depenses,
    )

    pdf_button = ft.TextButton(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.PICTURE_AS_PDF, color="#FFFFFF"),
                ft.Text("Telecharger PDF", color="#FFFFFF"),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            tight=True,
        ),
        style=ft.ButtonStyle(
            bgcolor="#6A1B9A",
            color="#FFFFFF",
            shape=ft.RoundedRectangleBorder(radius=10),
        ),
        on_click=create_pdf,
    )

    form_card = ft.Card(
        content=ft.Container(
            bgcolor="#FFFFFF",
            width=420,
            padding=14,
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Text("Nouvelle depense", size=18, weight=ft.FontWeight.BOLD),
                    description_field,
                    montant_field,
                    categorie_field,
                    date_field,
                    submit_button,
                ],
            ),
        ),
    )

    page.add(
        ft.Column(
            width=460,
            spacing=14,
            controls=[
                form_card,
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[liste_button, pdf_button],
                ),
                total_text,
                list_container,
            ],
        )
    )


if __name__ == "__main__":
    ft.run(main)

