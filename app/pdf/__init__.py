# --- INIT PDF : Package pour la génération PDF ---

import os
import sys


def is_android() -> bool:
    """Détecte si l'application tourne sur Android."""
    if sys.platform != "linux":
        return False
    return os.path.isdir("/storage/emulated/0") or os.path.isdir("/sdcard")


def has_reportlab() -> bool:
    """Retourne True si ReportLab est disponible."""
    try:
        import reportlab  # noqa: F401
        return True
    except Exception:
        return False


def get_pdf_dir() -> str:
    """
    Retourne le dossier où sauvegarder les PDF.
    - Android  → /storage/emulated/0/Download/ZeliDepance
    - PC/Linux → ~/Documents/ZeliDepance  (ou ~ si pas de Documents)
    """
    if is_android():
        # Dossier Téléchargements Android, visible depuis le gestionnaire de fichiers
        base = "/storage/emulated/0/Download/ZeliDepance"
    else:
        documents = os.path.join(os.path.expanduser("~"), "Documents")
        if not os.path.isdir(documents):
            documents = os.path.expanduser("~")
        base = os.path.join(documents, "ZeliDepance")

    os.makedirs(base, exist_ok=True)
    return base


def check_pdf_backend_on_startup() -> dict:
    """
    Vérifie le moteur PDF disponible au démarrage.
    Sur Android, si ReportLab est absent, l'app utilisera HTML/CSS sans erreur bloquante.
    """
    android = is_android()
    reportlab_ok = has_reportlab()
    backend = "reportlab" if reportlab_ok else "html"

    if android and not reportlab_ok:
        print("[PDF] ReportLab absent sur Android: fallback HTML/CSS activé.")

    print(f"[PDF] Dossier de sortie : {get_pdf_dir()}")

    return {
        "android": android,
        "reportlab": reportlab_ok,
        "backend": backend,
    }
