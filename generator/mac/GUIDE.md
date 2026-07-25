# 🖥️ App Mac — Générer un rapport DXA 2.0

Une app à double-cliquer : elle demande un PDF Hologic et ouvre le rapport 2.0
dans votre navigateur. **Rien à taper.**

Deux façons de faire — la **A est recommandée** (vraie icône d'app sur le Bureau).

---

## ⭐ A. Installer la vraie app sur le Bureau (recommandé)

1. Ouvrez le dossier **`generator/mac`**.
2. **Clic droit** sur **`Installer l'app sur le Bureau.command`** → **Ouvrir** →
   **Ouvrir** (l'avertissement macOS est normal, seulement la 1ʳᵉ fois).
3. Patientez ~30 s : une **icône « Rapport DXA 2.0 »** apparaît sur votre **Bureau**.
4. Ensuite, **double-cliquez cette icône** quand vous voulez un rapport →
   choisissez un PDF → le rapport s'ouvre dans le navigateur.

En haut du rapport, un **panneau coach** (masqué dans le PDF) permet de
**cocher/décocher les sections** et de choisir **objectif / activité / nombre de
repas** (calcul des calories et macros en direct). Cliquez **« 🖨 Exporter en
PDF »** → **« Enregistrer au format PDF »** : le PDF ne contient que ce qui est
affiché.

L'app du Bureau est **autonome** : le moteur est copié à l'intérieur, vous pouvez
la garder même si vous déplacez le dossier. Pour la mettre à jour plus tard,
relancez simplement l'installateur.

---

## B. Version simple sans installation (alternative)

Lance le même outil sans créer d'icône sur le Bureau.

### Installation (une seule fois)

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
