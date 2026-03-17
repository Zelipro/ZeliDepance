#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
#  BUILD_APK.sh — Script universel de build APK avec Storage Permissions
#  Par Zeli — Applications De Zeli
#
#  ✅ Compatible avec toutes vos applications Flet
#  📋 Usage : bash BUILD_APK.sh
#  📂 À placer à la racine de votre projet (à côté de main.py)
# ═══════════════════════════════════════════════════════════════════════════

set -e

# ── Nom de l'application (détecté automatiquement depuis le dossier) ────────
APP_NAME=$(basename "$PWD")

# ── Bannière ────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║            ███████╗███████╗██╗     ██╗                      ║"
echo "║            ╚══███╔╝██╔════╝██║     ██║                      ║"
echo "║              ███╔╝ █████╗  ██║     ██║                      ║"
echo "║             ███╔╝  ██╔══╝  ██║     ██║                      ║"
echo "║            ███████╗███████╗███████╗██║                      ║"
echo "║            ╚══════╝╚══════╝╚══════╝╚═╝                      ║"
echo "║                                                              ║"
echo "║          ✦  Applications De Zeli  ✦                         ║"
echo "║                                                              ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║   🔨  Build APK  →  $APP_NAME"
echo "║   🔐  Mode      →  Storage Permissions activées             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── Vérification de flet ─────────────────────────────────────────────────────
if ! command -v flet &> /dev/null; then
    # Essai avec ~/.local/bin
    if [ -f "$HOME/.local/bin/flet" ]; then
        export PATH="$HOME/.local/bin:$PATH"
        echo "✅ flet trouvé dans ~/.local/bin — PATH mis à jour."
    else
        echo "❌ flet introuvable !"
        echo ""
        echo "   Installez flet avec :  pip install flet"
        echo "   Puis relancez :        bash BUILD_APK.sh"
        exit 1
    fi
fi

echo "✅ flet détecté : $(flet --version 2>/dev/null || echo 'version inconnue')"
echo ""

# ── Vérification du android_patch ────────────────────────────────────────────
if [ ! -f "android_patch/AndroidManifest.xml" ]; then
    echo "⚠️  Dossier android_patch/AndroidManifest.xml introuvable."
    echo "   Les permissions de stockage ne seront PAS injectées."
    SKIP_PATCH=true
else
    SKIP_PATCH=false
fi

# ── ÉTAPE 1 : Build initial ───────────────────────────────────────────────────
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│  ÉTAPE 1/3 — Premier build APK                              │"
echo "└─────────────────────────────────────────────────────────────┘"

flet build apk 2>&1 || {
    echo ""
    echo "❌ Erreur lors du premier build."
    echo "   Vérifiez que Flutter SDK est installé : flutter doctor"
    exit 1
}

echo ""
echo "✅ Premier build terminé."
echo ""

# ── ÉTAPE 2 : Injection du AndroidManifest.xml ────────────────────────────────
if [ "$SKIP_PATCH" = false ]; then
    echo "┌─────────────────────────────────────────────────────────────┐"
    echo "│  ÉTAPE 2/3 — Injection des permissions de stockage          │"
    echo "└─────────────────────────────────────────────────────────────┘"

    # Chercher automatiquement le bon AndroidManifest
    MANIFEST_PATH="build/flutter/android/app/src/main/AndroidManifest.xml"

    if [ ! -f "$MANIFEST_PATH" ]; then
        echo "   Chemin standard introuvable, recherche automatique..."
        MANIFEST_PATH=$(find build/ -path "*/app/src/main/AndroidManifest.xml" 2>/dev/null | head -1)
    fi

    if [ -z "$MANIFEST_PATH" ] || [ ! -f "$MANIFEST_PATH" ]; then
        echo "❌ AndroidManifest.xml introuvable dans build/"
        echo "   Fichiers trouvés :"
        find build/ -name "AndroidManifest.xml" 2>/dev/null | head -10
        exit 1
    fi

    echo "   📄 Manifest trouvé : $MANIFEST_PATH"

    # Sauvegarde
    cp "$MANIFEST_PATH" "${MANIFEST_PATH}.backup"
    echo "   💾 Backup créé."

    # Injection
    cp android_patch/AndroidManifest.xml "$MANIFEST_PATH"
    echo ""
    echo "✅ Permissions de stockage injectées avec succès."
    echo ""
else
    echo "⏭️  ÉTAPE 2/3 — Injection ignorée (android_patch absent)."
    echo ""
fi

# ── ÉTAPE 3 : Rebuild final ───────────────────────────────────────────────────
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│  ÉTAPE 3/3 — Rebuild final                                  │"
echo "└─────────────────────────────────────────────────────────────┘"

flet build apk 2>&1 || {
    echo ""
    echo "❌ Erreur lors du rebuild final."
    exit 1
}

echo ""
echo "✅ Rebuild final terminé !"
echo ""

# ── Résultat final ────────────────────────────────────────────────────────────
APK_FILE=$(find build/ -name "*.apk" 2>/dev/null | grep -v "unsigned" | head -1)
if [ -z "$APK_FILE" ]; then
    APK_FILE=$(find build/ -name "*.apk" 2>/dev/null | head -1)
fi

if [ -n "$APK_FILE" ]; then
    APK_SIZE=$(du -sh "$APK_FILE" 2>/dev/null | cut -f1)
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                                                              ║"
    echo "║   🎉  APK généré avec succès !                              ║"
    echo "║                                                              ║"
    echo "║   📦  Fichier  : $APK_FILE"
    echo "║   📏  Taille   : $APK_SIZE"
    echo "║   🔐  Storage  : Permissions incluses ✅                    ║"
    echo "║                                                              ║"
    echo "╠══════════════════════════════════════════════════════════════╣"
    echo "║                                                              ║"
    echo "║   📱  INSTRUCTIONS D'INSTALLATION :                         ║"
    echo "║                                                              ║"
    echo "║   1. Copiez l'APK sur votre téléphone                       ║"
    echo "║   2. Installez l'APK (autoriser sources inconnues)          ║"
    echo "║   3. NE PAS lancer tout de suite                            ║"
    echo "║   4. Paramètres → Applications → $APP_NAME"
    echo "║   5. Permissions → Stockage → Autoriser                     ║"
    echo "║   6. Android 11+ : aussi Accès à tous les fichiers          ║"
    echo "║   7. Lancez l'application ✅                                 ║"
    echo "║                                                              ║"
    echo "║             ✦  Applications De Zeli  ✦                      ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
else
    echo "⚠️  APK introuvable. Vérifiez le dossier build/"
fi
