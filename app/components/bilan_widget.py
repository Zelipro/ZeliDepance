# --- BILAN WIDGET : Widget affichant le bilan annuel ---

import flet as ft
from datetime import datetime
from app.db.depenses import get_depenses_by_annee, calcul_total_annee
from app.db.listes import get_all_listes, get_liste_name


def build_bilan_widget(page: ft.Page) -> ft.Card:
    """Construit le widget bilan annuel."""
    current_year = datetime.now().year

    annee_field = ft.TextField(
        label="Année",
        value=str(current_year),
        keyboard_type=ft.KeyboardType.NUMBER,
        prefix_icon=ft.Icons.CALENDAR_MONTH,
        border_radius=10,
    )

    resultat_container = ft.Container(visible=False)

    def charger_bilan(_=None):
        try:
            annee = int(annee_field.value)
        except ValueError:
            resultat_container.visible = False
            page.update()
            return

        depenses = get_depenses_by_annee(annee)
        total = calcul_total_annee(annee)
        count = len(depenses)

        # Calcul par liste
        listes_dict = {}
        for _, liste_id, _, montant, _, _ in depenses:
            if liste_id not in listes_dict:
                listes_dict[liste_id] = {"count": 0, "total": 0.0}
            listes_dict[liste_id]["count"] += 1
            listes_dict[liste_id]["total"] += montant

        # Tableau récapitulatif
        table_data = [["Liste", "Dépenses", "Sous-total"]]
        for liste_id, data in listes_dict.items():
            nom = get_liste_name(liste_id)
            table_data.append(
                [nom, str(data["count"]), f"{data['total']:.2f}"]
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Liste")),
                ft.DataColumn(ft.Text("Dépenses"), numeric=True),
                ft.DataColumn(ft.Text("Sous-total"), numeric=True),
            ],
            rows=[
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(row[0])),
                        ft.DataCell(ft.Text(row[1])),
                        ft.DataCell(ft.Text(row[2])),
                    ]
                )
                for row in table_data[1:]
            ],
        )

        resultat_container.content = ft.Column(
            spacing=10,
            controls=[
                ft.Text(f"Total annuel : {total:.2f}", size=16, weight=ft.FontWeight.BOLD),
                ft.Text(f"Nombre de dépenses : {count}", size=14),
                ft.Divider(),
                ft.Text("Récapitulatif par liste", size=14, weight=ft.FontWeight.BOLD),
                table,
            ],
        )
        resultat_container.visible = True
        page.update()

    pdf_button = ft.TextButton(
        content=ft.Row(
            controls=[
                ft.Icon(
                    ft.Icons.PICTURE_AS_PDF,
                    color="#FFFFFF",
                ),
                ft.Text("PDF", color="#FFFFFF"),
            ],
            tight=True,
        ),
        style=ft.ButtonStyle(
            bgcolor="#2E7D32", color="#FFFFFF"
        ),
    )

    bilan_card = ft.Card(
        elevation=2,
        content=ft.Container(
            bgcolor="#FFFFFF",
            padding=14,
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Text("Bilan de l'année", size=18, weight=ft.FontWeight.BOLD),
                    annee_field,
                    ft.Row(
                        spacing=10,
                        controls=[
                            ft.TextButton(
                                "Voir le bilan",
                                style=ft.ButtonStyle(
                                    bgcolor="#2E7D32", color="#FFFFFF"
                                ),
                                on_click=charger_bilan,
                            ),
                            pdf_button,
                        ],
                    ),
                    resultat_container,
                ],
            ),
        ),
    )

    return bilan_card, annee_field, resultat_container, pdf_button
