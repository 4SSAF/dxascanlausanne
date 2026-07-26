#!/bin/bash
# =====================================================================
#  Rapport DXA 2.0
#  Double-cliquez ce fichier : choisissez un PDF Hologic, le rapport
#  s'ouvre tout seul dans votre navigateur. S'installe seul au 1er lancement.
# =====================================================================

DIR="$(cd "$(dirname "$0")" && pwd)"
GEN_DIR="$(dirname "$DIR")"          # dossier generator/
cd "$DIR"

notify()  { osascript -e "display notification \"$1\" with title \"Rapport DXA 2.0\"" >/dev/null 2>&1 || true; }
alertbox(){ osascript -e "display dialog \"$1\" with title \"Rapport DXA 2.0\" buttons {\"OK\"} default button 1" >/dev/null 2>&1 || true; }

echo "──────────────────────────────────────────"
echo "  Rapport DXA 2.0"
echo "──────────────────────────────────────────"

# 1) Python 3 présent ?
if ! command -v python3 >/dev/null 2>&1; then
  alertbox "Python 3 n'est pas installé sur ce Mac. Ouvrez l'app Terminal, tapez :  xcode-select --install  puis relancez ce fichier."
  echo "Python 3 manquant."; exit 1
fi

# 2) Installation (première fois seulement) : environnement + PyMuPDF
if [ ! -x "$DIR/.venv/bin/python" ]; then
  echo "Première utilisation : installation en cours (~30 s)…"
  notify "Première installation en cours…"
  python3 -m venv "$DIR/.venv" || { alertbox "Impossible de créer l'environnement Python."; exit 1; }
  "$DIR/.venv/bin/pip" install --quiet --upgrade pip
  if ! "$DIR/.venv/bin/pip" install --quiet -r "$GEN_DIR/requirements.txt"; then
    alertbox "Échec de l'installation (PyMuPDF). Vérifiez votre connexion internet et relancez."
    exit 1
  fi
  echo "Installation terminée ✅"
fi
PY="$DIR/.venv/bin/python"

# 3) Choisir un ou plusieurs PDF (fenêtre native macOS)
FILES=$(osascript <<'APPLESCRIPT' 2>/dev/null
try
  set theFiles to choose file with prompt "Choisissez un ou plusieurs rapports DXA (PDF) :" with multiple selections allowed
on error
  return ""
end try
set out to ""
repeat with f in theFiles
  set out to out & POSIX path of f & linefeed
end repeat
return out
APPLESCRIPT
)

if [ -z "$FILES" ]; then echo "Annulé."; exit 0; fi

# 4) Générer chaque rapport et l'ouvrir
COUNT=0
while IFS= read -r pdf; do
  [ -z "$pdf" ] && continue
  echo "→ $pdf"
  out="${pdf%.*}.rapport2.html"
  if "$PY" "$GEN_DIR/generate.py" "$pdf" -o "$out"; then
    [ -f "$out" ] && open "$out"
    COUNT=$((COUNT + 1))
  else
    alertbox "Erreur lors du traitement de : $(basename "$pdf")"
  fi
done <<< "$FILES"

notify "$COUNT rapport(s) généré(s) ✅"
echo "Terminé : $COUNT rapport(s). Le rapport s'ouvre dans votre navigateur."
echo "(Astuce : dans le navigateur, ⌘P pour imprimer ou enregistrer en PDF.)"
sleep 1
