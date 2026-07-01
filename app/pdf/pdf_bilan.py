# --- PDF BILAN : Génération PDF/HTML bilan annuel ---

import os
import importlib
from html import escape

from app.db.depenses import get_depenses_by_annee, calcul_total_annee
from app.db.listes import get_liste_name
from app.pdf import has_reportlab, get_pdf_dir


def _build_html_bilan(annee: int, depenses: list[tuple], total_annee: float) -> str:
    rows = []
    for _, liste_id, description, montant, categorie, date in depenses:
        liste_nom = get_liste_name(liste_id)
        rows.append(
            "<tr>"
            f"<td>{escape(str(liste_nom))}</td>"
            f"<td>{escape(str(description))}</td>"
            f"<td>{float(montant):.2f}</td>"
            f"<td>{escape(str(categorie))}</td>"
            f"<td>{escape(str(date))}</td>"
            "</tr>"
        )

    rows_html = "\n".join(rows) if rows else "<tr><td colspan='5'>Aucune depense</td></tr>"
    return f"""<!DOCTYPE html>
<html lang='fr'>
<head>
  <meta charset='UTF-8'>
  <title>Bilan depenses {annee}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 28px; color: #1F2937; }}
    h1 {{ color: #2E7D32; margin-bottom: 8px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 14px; }}
    th {{ background: #2E7D32; color: white; text-align: left; padding: 10px; }}
    td {{ border-bottom: 1px solid #E5E7EB; padding: 9px 10px; }}
    .total {{ margin-top: 16px; font-weight: bold; color: #1B5E20; }}
  </style>
</head>
<body>
  <h1>Bilan des depenses - Annee {annee}</h1>
  <table>
    <thead><tr><th>Liste</th><th>Description</th><th>Montant</th><th>Categorie</th><th>Date</th></tr></thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
  <p class='total'>Total annuel : {total_annee:.2f}</p>
</body>
</html>
"""


def generate_pdf_bilan_annee(annee: int, file_path: str = None) -> str:
    """
    Génère un bilan PDF (ou HTML fallback) pour une année.
    Si file_path n'est pas fourni, sauvegarde automatiquement dans
    le dossier Download/Documents selon la plateforme.
    """
    depenses = get_depenses_by_annee(annee)
    total_annee = calcul_total_annee(annee)

    # ── Chemin de sortie automatique ──────────────────────────────────────
    if file_path is None:
        ext = ".pdf" if has_reportlab() else ".html"
        file_path = os.path.join(get_pdf_dir(), f"bilan_depenses_{annee}{ext}")

    if has_reportlab():
        colors = importlib.import_module("reportlab.lib.colors")
        A4 = importlib.import_module("reportlab.lib.pagesizes").A4
        getSampleStyleSheet = importlib.import_module("reportlab.lib.styles").getSampleStyleSheet
        platypus = importlib.import_module("reportlab.platypus")
        Paragraph = platypus.Paragraph
        SimpleDocTemplate = platypus.SimpleDocTemplate
        Spacer = platypus.Spacer
        Table = platypus.Table
        TableStyle = platypus.TableStyle

        doc = SimpleDocTemplate(file_path, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph(f"Bilan des depenses - Annee {annee}", styles["Title"]))
        elements.append(Spacer(1, 12))

        table_data = [["Liste", "Description", "Montant", "Categorie", "Date"]]
        for _, liste_id, description, montant, categorie, date in depenses:
            liste_nom = get_liste_name(liste_id)
            table_data.append([liste_nom, description, f"{montant:.2f}", categorie, date])

        table = Table(table_data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E7D32")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (2, 1), (2, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    ("TOPPADDING", (0, 0), (-1, 0), 8),
                ]
            )
        )

        elements.append(table)
        elements.append(Spacer(1, 14))
        elements.append(Paragraph(f"Total annuel : {total_annee:.2f}", styles["Heading3"]))

        doc.build(elements)
        return file_path

    # ── Fallback HTML ─────────────────────────────────────────────────────
    html_path = os.path.splitext(file_path)[0] + ".html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(_build_html_bilan(annee, depenses, total_annee))
    return html_path
