#!/bin/bash
# =====================================================================
#  Installe l'application "Rapport DXA 2.0" sur le BUREAU (une fois).
#  Double-cliquez ce fichier. Ensuite, utilisez l'icône sur le Bureau.
# =====================================================================

DIR="$(cd "$(dirname "$0")" && pwd)"
GEN_DIR="$(dirname "$DIR")"                 # dossier generator/
APPNAME="Rapport DXA 2.0"
APP="$HOME/Desktop/$APPNAME.app"

alertbox(){ osascript -e "display dialog \"$1\" with title \"Rapport DXA 2.0\" buttons {\"OK\"} default button 1" >/dev/null 2>&1 || true; }

echo "──────────────────────────────────────────"
echo "  Installation de « $APPNAME » sur le Bureau"
echo "──────────────────────────────────────────"

if ! command -v python3 >/dev/null 2>&1; then
  alertbox "Python 3 est requis. Ouvrez le Terminal, tapez  xcode-select --install  puis relancez ce fichier."
  echo "Python 3 manquant."; exit 1
fi

# 1) Structure du bundle .app
echo "Création de l'application…"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources/engine"
cp "$DIR/app_template/Info.plist"  "$APP/Contents/Info.plist"
cp "$DIR/app_template/launcher.sh" "$APP/Contents/MacOS/rapport-dxa"
chmod +x "$APP/Contents/MacOS/rapport-dxa"
[ -f "$DIR/AppIcon.icns" ] && cp "$DIR/AppIcon.icns" "$APP/Contents/Resources/AppIcon.icns"

# 2) Moteur (copié DANS l'app -> autonome, même si on déplace le dossier)
cp -R "$GEN_DIR/dxa2" "$APP/Contents/Resources/engine/dxa2"
cp "$GEN_DIR/generate.py" "$GEN_DIR/requirements.txt" "$APP/Contents/Resources/engine/"
find "$APP/Contents/Resources/engine" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null

# 3) Environnement Python + PyMuPDF (dans l'app)
echo "Installation des dépendances (~30 s)…"
python3 -m venv "$APP/Contents/Resources/.venv"
"$APP/Contents/Resources/.venv/bin/pip" install -q --upgrade pip
if ! "$APP/Contents/Resources/.venv/bin/pip" install -q -r "$APP/Contents/Resources/engine/requirements.txt"; then
  alertbox "Échec de l'installation de PyMuPDF. Vérifiez votre connexion internet et relancez."
  exit 1
fi

# 4) Lever la quarantaine + rafraîchir l'icône
xattr -dr com.apple.quarantine "$APP" 2>/dev/null
touch "$APP"

echo "Terminé ✅"
alertbox "✅ L'application « $APPNAME » est maintenant sur votre Bureau.\n\nDouble-cliquez son icône pour générer un rapport à partir d'un PDF Hologic."
open -R "$APP" 2>/dev/null || true
