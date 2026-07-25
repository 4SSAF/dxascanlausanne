# 🖥️ App Mac — Générer un rapport DXA 2.0

Une petite « app » à double-cliquer. Elle demande un PDF Hologic et ouvre le
rapport 2.0 dans votre navigateur. **Rien à taper.**

---

## Installation (une seule fois)

1. Récupérez le dossier **`generator`** sur votre Mac (par ex. dans vos Documents).
2. Ouvrez le sous-dossier **`generator/mac`**.
3. **Clic droit** sur **`Générer un rapport DXA.command`** → **Ouvrir**.
4. macOS affiche un avertissement (« développeur non identifié ») → cliquez encore
   sur **Ouvrir**. *(C'est normal : le fichier vient de vous, pas de l'App Store.
   Ce clic droit → Ouvrir n'est nécessaire que la toute première fois.)*
5. Une fenêtre Terminal s'ouvre et installe automatiquement ce qu'il faut
   (~30 secondes, connexion internet requise). Laissez faire.

> Si un message dit que **Python 3** manque : ouvrez l'app **Terminal**, tapez
> `xcode-select --install`, validez, puis relancez le fichier. C'est un composant
> gratuit d'Apple.

---

## Utilisation (à chaque fois)

1. **Double-cliquez** `Générer un rapport DXA.command`.
2. Choisissez **un ou plusieurs PDF** Hologic dans la fenêtre.
3. Le(s) rapport(s) s'ouvrent **automatiquement dans votre navigateur**.
4. Dans le navigateur, **⌘P** pour imprimer ou **enregistrer en PDF**.

Le fichier HTML du rapport est enregistré **à côté du PDF d'origine**
(même dossier, nom `…rapport2.html`).

---

## En cas de souci

| Problème | Solution |
|---|---|
| « développeur non identifié » | Clic droit → **Ouvrir** (au lieu de double-clic) la 1ʳᵉ fois |
| « Python 3 n'est pas installé » | Terminal → `xcode-select --install` puis relancer |
| Échec d'installation | Vérifiez la connexion internet et relancez le fichier |
| Rien ne s'ouvre | Le rapport est enregistré à côté du PDF (`…rapport2.html`) — ouvrez-le à la main |

---

## Comment ça marche (pour info)

Le fichier `.command` crée, au premier lancement, un mini-environnement Python
isolé dans `generator/mac/.venv` et y installe **PyMuPDF** (lecture des PDF).
Ensuite il appelle le générateur (`generator/generate.py`). **Tout se passe sur
votre Mac** — aucune donnée patient n'est envoyée sur internet.
