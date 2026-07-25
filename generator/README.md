# Générateur de Rapport DXA 2.0 — Motion LAB

Transforme un **export PDF Hologic APEX** (scanner Horizon Wi) en un **Rapport 2.0**
HTML : âge biologique, comparaisons aux populations de référence, jauges lisibles,
suivi longitudinal et plan d'action — le tout auto-rempli depuis le PDF.

> Preuve de concept validée sur deux profils réels opposés (homme multi-examens /
> femme premier examen). Le HTML produit est autonome (CSS + images embarqués),
> s'affiche en thème clair/sombre et s'imprime.

## Installation

```bash
cd generator
pip install -r requirements.txt        # PyMuPDF
```

## Usage

```bash
# un rapport -> entree.rapport2.html (à côté du PDF)
python generate.py chemin/vers/DXA_client.pdf

# sortie explicite
python generate.py DXA_client.pdf -o rapport.html

# voir les données extraites (débogage / vérification)
python generate.py DXA_client.pdf --json

# traitement par lot
python generate.py dossier/*.pdf
```

## Ce que le générateur fait tout seul

- **Extraction** du PDF (démographie, DMO/T/Z, composition, TAV, ALMI, régional,
  historique multi-examens) — gère les deux mises en page (mono- et multi-examens).
- **Instantané le plus récent** : pour chaque mesure, prend la valeur de l'examen
  le plus récent qui la porte (les indices peuvent dater d'une page différente).
- **Âge biologique** : composite pondéré de trois sous-âges (métabolique / musculaire
  / osseux), replacés sur des références **sexe-spécifiques**.
- **Adaptation automatique** : références homme/femme, mode « tendances » (≥ 2 scans)
  ou « baseline » (1 scan), détection d'asymétrie des bras, alerte RED-S pour un
  profil féminin mince, textes d'interprétation et actions priorisées.
- **Images** DXA du PDF réintégrées proprement (squelette + carte de composition).

## Architecture

```
generate.py            CLI : PDF -> HTML
dxa2/
  parse.py             PDF Hologic -> dict structuré (+ extraction images)
  references.py        seuils & barèmes sexe-spécifiques  ← À CALIBRER ICI
  analyze.py           âge biologique, jauges, statuts, interprétation, tendances
  render.py            dict analysé -> HTML autonome
  style.css            design system (palette validée, clair/sombre)
```

## Calibration (« figer le contenu »)

Tout ce qui relève du jugement clinique/coaching est regroupé dans
**`dxa2/references.py`** : seuils de TAV, médianes/plafonds ALMI, plages de masse
grasse, et **pondérations de l'âge biologique** (`BIOAGE_WEIGHTS`). Ajustez ces
valeurs pour coller à votre discours ; le reste du code s'adapte.

## Confidentialité

- **Aucune** donnée patient n'est envoyée sur le réseau : tout est traité en local.
- Les PDF patients et les rapports générés sont **exclus du dépôt** (`.gitignore`).
  Ne versionnez jamais de données nominatives.

## Limites

- L'**âge biologique DXA** est un indice pédagogique dérivé des mesures DXA et de
  populations de référence publiées — **pas** un diagnostic ni un biomarqueur validé.
- Le parseur suit la mise en page APEX 13.6.x observée. Un changement majeur de
  format Hologic peut nécessiter un ajustement des ancres (`dxa2/parse.py`).
- Voie d'amélioration : brancher l'export **DICOM SR** (données structurées) en
  entrée, plus robuste que le parsing PDF.
