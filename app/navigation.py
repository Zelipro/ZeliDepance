# --- NAVIGATION : Gestion de la navigation et les vues ---

import flet as ft


def navigate(page: ft.Page, view_name: str, **kwargs) -> None:
    """Navigue vers une vue spécifique et met à jour la page."""
    # Imports à l'intérieur pour éviter les dépendances circulaires
    from app.views.lock_view import build_lock_view
    from app.views.home_view import build_home_view
    from app.views.liste_view import build_liste_view
    
    page.controls.clear()
    
    if view_name == "lock":
        page.add(build_lock_view(page))
    elif view_name == "accueil":
        page.add(build_home_view(page))
    elif view_name == "liste":
        liste_id = kwargs.get("liste_id")
        liste_nom = kwargs.get("liste_nom")
        page.add(build_liste_view(page, liste_id, liste_nom))
    
    page.update()
