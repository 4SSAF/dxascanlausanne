#!/bin/bash
# Exécutable de l'app "Rapport DXA 2.0.app" (Contents/MacOS/rapport-dxa).
# Lancé par macOS au double-clic. Interface via dialogues natifs (osascript).

RES="$(cd "$(dirname "$0")/../Resources" && pwd)"
PY="$RES/.venv/bin/python"

notify()  { osascript -e "display notification \"$1\" with title \"Rapport DXA 2.0\"" >/dev/null 2>&1 || true; }
alertbox(){ osascript -e "display dialog \"$1\" with title \"Rapport DXA 2.0\" buttons {\"OK\"} default button 1" >/dev/null 2>&1 || true; }

# Auto-réparation : recrée l'environnement si absent
if [ ! -x "$PY" ]; then
  if ! command -v python3 >/dev/null 2>&1; then
    alertbox "Python 3 est requis. Ouvrez le Terminal, tapez  xcode-select --install  puis réessayez."
    exit 1
  fi
  notify "Première installation en cours…"
  python3 -m venv "$RES/.venv" \
    && "$RES/.venv/bin/pip" install -q --upgrade pip \
    && "$RES/.venv/bin/pip" install -q -r "$RES/engine/requirements.txt" \
    || { alertbox "Échec de l'installation (PyMuPDF). Vérifiez votre connexion internet."; exit 1; }
  PY="$RES/.venv/bin/python"
fi

# Choix de la langue / Report language
LANG_CHOICE=$(osascript <<'APPLESCRIPT' 2>/dev/null
try
  set c to choose from list {"Français", "English"} with prompt "Langue du rapport / Report language :" default items {"Français"} without multiple selections allowed
  if c is false then return ""
  return item 1 of c
on error
  return ""
end try
APPLESCRIPT
)
[ -z "$LANG_CHOICE" ] && exit 0
if [ "$LANG_CHOICE" = "English" ]; then LANG_CODE="en"; else LANG_CODE="fr"; fi

# Sélection des PDF (fenêtre native)
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
[ -z "$FILES" ] && exit 0

COUNT=0
while IFS= read -r pdf; do
  [ -z "$pdf" ] && continue
  out="${pdf%.*}.rapport2.${LANG_CODE}.html"
  if "$PY" "$RES/engine/generate.py" "$pdf" -o "$out" --lang "$LANG_CODE"; then
    [ -f "$out" ] && open "$out"
    COUNT=$((COUNT + 1))
  else
    alertbox "Erreur lors du traitement de : $(basename "$pdf")"
  fi
done <<< "$FILES"

notify "$COUNT rapport(s) généré(s) ✅"
