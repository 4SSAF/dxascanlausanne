"""
Références sexe-spécifiques, seuils et barèmes d'interprétation.

⚠️ Paramètres pédagogiques et CALIBRABLES par le coach (étape « figer le contenu »).
Sources : NHANES/BMDCS (natif Hologic), Pratt 2025, Meredith-Jones 2021 (TAV),
Radecka 2025 / Yamada 2021 (ALMI), Hew-Butler 2025 (% masse grasse athlète),
Trexler 2017 (FFMI). Ne constitue pas un barème diagnostique.
"""

# Ancres physiologiques par sexe
ANCHORS = {
    "M": dict(
        vat_mass_thr=1000.0,   # g, seuil de risque cardiométabolique (<40 ans)
        vat_area_thr=100.0,    # cm²
        vat_area_max=200.0,    # borne d'échelle
        bf_athletic=13.0, bf_healthy_mid=18.0,
        bf_scale=(3.0, 35.0),
        bf_zones=[(3, 6, "warn"), (6, 14, "brand"), (14, 24, "good"), (24, 31, "warn"), (31, 35, "risk")],
        bf_scale_labels=["3–5 essentiel", "6–13 athlète", "14–24 sain", "25+ élevé"],
        almi_median=8.6, almi_thr=7.0, almi_sd=1.0,
        almi_scale=(6.5, 11.0),
        almi_zones=[(6.5, 7.0, "risk"), (7.0, 8.6, "warn"), (8.6, 10.0, "good"), (10.0, 11.0, "brand")],
        almi_scale_labels=["7,0 seuil", "8,6 médiane", "10+ élite"],
        ffmi_scale=(16.0, 25.0),
        ffmi_zones=[(16, 20, "warn"), (20, 23, "good"), (23, 25, "brand")],
        ffmi_scale_labels=["16 sédentaire", "20 entraîné", "25 max naturel"],
        fmi_scale=(2.0, 11.0),
        fmi_zones=[(2, 5, "brand"), (5, 8, "good"), (8, 11, "warn")],
        fmi_scale_labels=["2 bas", "5 sain", "9+ élevé"],
    ),
    "F": dict(
        vat_mass_thr=700.0,
        vat_area_thr=90.0,
        vat_area_max=160.0,
        bf_athletic=20.0, bf_healthy_mid=25.0,
        bf_scale=(10.0, 45.0),
        bf_zones=[(10, 14, "warn"), (14, 21, "brand"), (21, 29, "good"), (29, 35, "warn"), (35, 45, "risk")],
        bf_scale_labels=["10–13 essentiel", "14–20 athlète", "21–29 en forme", "32+ élevé"],
        almi_median=6.1, almi_thr=5.5, almi_sd=0.8,
        almi_scale=(4.5, 8.0),
        almi_zones=[(4.5, 5.5, "risk"), (5.5, 6.1, "warn"), (6.1, 7.2, "good"), (7.2, 8.0, "brand")],
        almi_scale_labels=["5,5 seuil", "6,1 médiane", "7,5+ élite"],
        ffmi_scale=(13.0, 22.0),
        ffmi_zones=[(13, 16, "warn"), (16, 20, "good"), (20, 22, "brand")],
        ffmi_scale_labels=["13 sédentaire", "17 entraînée", "22 élevé"],
        fmi_scale=(2.0, 11.0),
        fmi_zones=[(2, 5, "brand"), (5, 8, "good"), (8, 11, "warn")],
        fmi_scale_labels=["2 bas", "5 sain", "9+ élevé"],
    ),
}

# Barème DMO (identique H/F, T-score)
BMD_SCALE = (-2.5, 2.0)
BMD_ZONES = [(-2.5, -1.0, "warn"), (-1.0, 2.0, "good")]
BMD_SCALE_LABELS = ["−2,5 ostéo", "−1,0", "0 moyenne", "+2"]

# Seuil de variation significative DMO (VMS Hologic typique)
BMD_LSC = 0.014

# Pondérations de l'âge biologique (calibrables)
BIOAGE_WEIGHTS = dict(metabolic=0.40, muscle=0.35, bone=0.25)


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def scale_pos(value, lo, hi):
    """Position en % (2..98) sur une échelle linéaire."""
    if value is None:
        return None
    return clamp((value - lo) / (hi - lo) * 100.0, 2.0, 98.0)


def zones_to_widths(zones, lo, hi):
    """Convertit des zones (v0, v1, token) en (largeur %, token) sur l'échelle."""
    span = hi - lo
    return [((v1 - v0) / span * 100.0, tok) for (v0, v1, tok) in zones]


# ---------------------------------------------------------------------------
# Métabolisme & nutrition (modules optionnels)
# ---------------------------------------------------------------------------
# BMR — Cunningham et al. (1991) : RMR = 500 + 22 x masse maigre (FFM, kg)
CUNNINGHAM = dict(base=500.0, coef=22.0)

# Niveaux d'activité (PAL) appliqués au BMR pour estimer la DEJ (TDEE)
ACTIVITY = [
    ("sedentaire", "Sédentaire (bureau)", 1.20),
    ("leger", "Léger (1–3 séances/sem)", 1.375),
    ("modere", "Modéré (3–5 séances/sem)", 1.55),
    ("intense", "Intense (6–7 séances/sem)", 1.725),
    ("extreme", "Très intense (2×/j, physique)", 1.90),
]
ACTIVITY_DEFAULT = "modere"

# Ajustement calorique selon l'objectif
GOALS = [
    ("deficit", "Déficit (perte de gras)", -0.20),
    ("maintien", "Maintien", 0.0),
    ("surplus", "Surplus (prise de muscle)", 0.10),
]
GOAL_DEFAULT = "maintien"

# Protéines cibles selon l'objectif.
#   PROTEIN_BASIS : "ffm" = g par kg de MASSE MAIGRE (choix coach — plus juste),
#                   "bw"  = g par kg de poids total.
PROTEIN_BASIS = "ffm"
PROTEIN_G_PER_KG_FFM = dict(deficit=2.6, maintien=2.2, surplus=2.2)   # Helms 2014 (sèche)
PROTEIN_G_PER_KG_BW = dict(deficit=2.2, maintien=1.8, surplus=1.8)    # Morton 2018
FAT_G_PER_KG = 0.9          # lipides (min hormonal ~0.6) — g/kg de poids total
KCAL = dict(prot=4, carb=4, fat=9)

# Répartition par repas : seuil de stimulation optimale de la synthèse protéique
# ~0,4 g de protéines / kg / prise (Moore 2015 ; Schoenfeld & Aragon 2018)
PROTEIN_PER_MEAL_G_PER_KG = 0.4
MEALS_DEFAULT = 4


# ---------------------------------------------------------------------------
# Projecteur d'objectif (estimation à rythme constant)
# ---------------------------------------------------------------------------
# Vitesses par défaut si aucun historique mesuré n'est disponible
PROJ_FAT_LOSS_PCT_PER_MONTH = 0.7    # perte de %MG/mois en déficit modéré
PROJ_LEAN_GAIN_KG_PER_MONTH = 0.3    # gain de masse maigre/mois (entraîné, surplus)
