"""
Traduction FR -> EN du rapport.

Approche : le rapport est construit en français, puis (si lang == 'en') on applique
une passe de remplacement de phrases FR -> EN sur le HTML final (libellés, notes,
fragments JS, libellés de barèmes). Les textes générés par analyze.py sont, eux,
déjà émis dans la langue cible.

Le remplacement se fait par phrases complètes et distinctives, de la plus longue à
la plus courte, pour éviter les collisions et ne pas toucher aux données (noms,
dates, nombres).
"""
from __future__ import annotations
import re

# FR -> EN. Garder des phrases COMPLÈTES et distinctives.
PHRASES = {
    # --- en-tête / patient ---
    "Bilan Corporel DXA": "Body Composition DXA",
    "Analyse de composition corporelle": "Body composition analysis",
    "IMC": "BMI",
    "Généré automatiquement depuis l'export Hologic": "Auto-generated from the Hologic export",
    "examens · suivi longitudinal": "exams · longitudinal follow-up",
    "Premier examen (baseline)": "First exam (baseline)",
    "Âge civil": "Age",
    "Taille": "Height",
    "Poids": "Weight",
    "Examen": "Exam",
    "Suivi": "Follow-up",
    "Appareil": "Device",
    "Client": "Client",
    "Maigreur": "Underweight",
    "Surpoids": "Overweight",
    "Obésité": "Obesity",
    "Normal": "Normal",
    "ans · ♀": "yrs · ♀",
    "ans · ♂": "yrs · ♂",
    "er scan · baseline": "st scan · baseline",
    "scans": "scans",
    # --- pastille doc ---
    "◆ Rapport&nbsp;2.0": "◆ Report&nbsp;2.0",
    "Rapport 2.0 · moteur v": "Report 2.0 · engine v",
    # --- titres de sections ---
    "Âge biologique &amp; score global": "Biological age &amp; overall score",
    "Composition en un coup d'œil": "Composition at a glance",
    "Muscle — masse maigre": "Muscle — lean mass",
    "Graisse &amp; risque cardiométabolique": "Fat &amp; cardiometabolic risk",
    "Os — densité minérale": "Bone — mineral density",
    "Depuis la dernière fois": "Since last time",
    "Métabolisme de base": "Basal metabolism",
    "Besoins nutritionnels": "Nutritional needs",
    "Répartition des repas": "Meal distribution",
    "Hydratation, fibres &amp; compléments": "Hydration, fibre &amp; supplements",
    "Recommandation d'entraînement": "Training recommendation",
    "Projecteur d'objectif": "Goal projector",
    "Évolution dans le temps": "Change over time",
    "Point de départ (baseline)": "Baseline",
    "Interprétation &amp; plan d'action": "Interpretation &amp; action plan",
    "Méthode, références &amp; limites": "Method, references &amp; limitations",
    "Diagnostic osseux — sites dédiés": "Bone diagnosis — dedicated sites",
    # --- notes de section (droite) ---
    "Synthèse en tête de rapport : le message clé d'abord, le détail ensuite.":
        "Summary up top: the key message first, the detail after.",
    "Références féminines (NHANES + cohortes récentes).": "Female references (NHANES + recent cohorts).",
    "Références masculines (NHANES + cohortes récentes).": "Male references (NHANES + recent cohorts).",
    "Références européennes féminines (Hologic).": "European female references (Hologic).",
    "Références européennes masculines (Hologic).": "European male references (Hologic).",
    "21–31 sain": "21–31 healthy", "38+ élevé": "38+ high",
    "64,9 kg répartis en trois compartiments — la lecture que l'IMC ne donne pas.":
        "split into three compartments — the reading BMI can't give.",
    "en trois compartiments — bien au-delà de l'IMC.": "in three compartments — well beyond BMI.",
    "Le compartiment le plus lié à la longévité fonctionnelle.":
        "The compartment most tied to functional longevity.",
    "Ce n'est pas la quantité de graisse qui compte, mais surtout sa localisation.":
        "It's not how much fat, but above all where it sits.",
    "Indicateur global. Le diagnostic OMS repose sur des sites dédiés (§ ci-dessous).":
        "Overall indicator. WHO diagnosis relies on dedicated sites (§ below).",
    "Ce qui a changé entre les deux derniers examens.": "What changed between the last two exams.",
    "Estimé par la formule de Cunningham (1991) à partir de la masse maigre mesurée.":
        "Estimated with the Cunningham (1991) equation from measured lean mass.",
    "Cible calorique et macros selon l'objectif — modifiables dans le panneau coach.":
        "Calorie target and macros by goal — editable in the coach panel.",
    "Protéines réparties pour maximiser la synthèse musculaire (~0,4 g/kg/prise).":
        "Protein spread to maximise muscle protein synthesis (~0.4 g/kg/meal).",
    "Repères pratiques dérivés de la composition et des besoins.":
        "Practical targets derived from composition and needs.",
    "Fondé sur les signaux DXA — principes evidence-based (volume, RIR, fréquence).":
        "Based on DXA signals — evidence-based principles (volume, RIR, frequency).",
    "Estimation à rythme constant — vitesse mesurée si un historique existe, sinon rythme type.":
        "Constant-rate estimate — measured speed if history exists, else a typical rate.",
    "examens — la vraie valeur d'un suivi DXA est la trajectoire.":
        "exams — the real value of DXA follow-up is the trajectory.",
    "Premier examen : les tendances apparaîtront dès le 2ᵉ scan.":
        "First exam: trends will appear from the 2nd scan.",
    "Traduire les chiffres en décisions.": "Turning numbers into decisions.",
    "Le pic de masse osseuse conditionne le risque de fracture des décennies plus tard.":
        "Peak bone mass drives fracture risk decades later.",
    "Rachis AP + hanche · classification sur le site le plus bas (ISCD/OMS).":
        "AP spine + hip · classified on the lowest site (ISCD/WHO).",
    # --- éléments composition / muscle / fat ---
    "Imagerie DXA — corps entier": "DXA imaging — whole body",
    "Carte osseuse": "Bone map",
    "Graisse / maigre / os": "Fat / lean / bone",
    "Image non destinée à un usage diagnostique": "Image not for diagnostic use",
    "Masse totale —": "Total mass —",
    "Masse maigre": "Lean mass",
    "Masse grasse": "Fat mass",
    "Contenu osseux": "Bone content",
    "Indices normalisés (taille²)": "Height-normalised indices (height²)",
    "Position vs jeunes adultes (même sexe)": "Position vs young adults (same sex)",
    "maigre appendiculaire / taille²": "appendicular lean / height²",
    "Masse maigre par région (kg)": "Lean mass by region (kg)",
    "Médiane de référence": "Reference median",
    "Bras droit": "Right arm", "Bras gauche": "Left arm",
    "Jambe droite": "Right leg", "Jambe gauche": "Left leg",
    "Tronc": "Trunk", "Bassin": "Pelvis", "Jambes": "Legs", "Bras": "Arms",
    "Rachis L.": "Lumbar sp.", "Rachis L1–L4": "Lumbar L1–L4",
    "Col fémoral": "Femoral neck", "Hanche totale": "Total hip",
    "Masse grasse totale — plages de santé": "Total fat mass — health ranges",
    "% masse grasse": "body fat %",
    "Graisse viscérale (TAV) — le marqueur qui compte": "Visceral fat (VAT) — the marker that matters",
    "grammes de TAV": "grams of VAT",
    "TAV sur l'échelle de risque": "VAT on the risk scale",
    "Ratio A/G": "A/G ratio", "androïde/gynoïde": "android/gynoid",
    "Tronc / membres": "Trunk / limbs", "distribution": "distribution",
    # --- os ---
    "DMO corps entier — indicateur, non diagnostique": "Whole-body BMD — indicator, not diagnostic",
    "DMO totale": "Total BMD",
    "Densité par région (g/cm²)": "Density by region (g/cm²)",
    "Densité osseuse": "Bone density",
    "corps entier · non diagnostique": "whole body · not diagnostic",
    "vs même âge/sexe": "vs same age/sex",
    # --- scorecards labels/status ---
    "Graisse viscérale": "Visceral fat",
    "Masse musculaire": "Muscle mass",
    "appendiculaire": "appendicular",
    "seuil ≈": "threshold ≈",
    "ALMI · médiane féminine": "ALMI · female median",
    "ALMI · appendiculaire": "ALMI · appendicular",
    "Au-dessus de la moyenne": "Above average",
    "OPTIMAL": "OPTIMAL", "CORRECT": "OK", "ÉLEVÉ": "HIGH",
    "À DÉVELOPPER": "TO BUILD", "FAIBLE": "LOW", "SOLIDE": "SOLID",
    "SUPÉRIEUR": "ABOVE AVG", "OSTÉOPÉNIE": "OSTEOPENIA", "OSTÉOPOROSE": "OSTEOPOROSIS",
    "ATHLÉTIQUE": "ATHLETIC", "SAIN": "HEALTHY", "TRÈS ÉLEVÉ": "VERY HIGH",
    "SOUS LA NORMALE ÂGE": "BELOW AGE NORM", "SUPÉRIEUR / ÂGE": "ABOVE / AGE",
    "NORMAL / ÂGE": "NORMAL / AGE",
    # --- métabolisme / nutrition ---
    "Masse maigre (FFM)": "Lean mass (FFM)",
    "mesurée au DXA": "measured by DXA",
    "Métabolisme de base": "Basal metabolism",
    "au repos (BMR)": "at rest (BMR)",
    "Dépense énergétique": "Energy expenditure",
    "BMR × activité (modéré)": "BMR × activity (moderate)",
    "Formule": "Formula",
    "Cible calorique": "Calorie target",
    "= dépense énergétique": "= energy expenditure",
    "Protéines": "Protein", "Glucides": "Carbs", "Lipides": "Fat",
    "Repas": "Meal",
    # --- hydratation ---
    "Eau corporelle totale": "Total body water",
    "≈ 72 % de la masse maigre": "≈ 72% of lean mass",
    "Apport hydrique cible": "Target water intake",
    "· + pertes à l'effort": "· + exercise losses",
    "Fibres": "Fibre",
    "Créatine": "Creatine",
    "monohydrate, en continu": "monohydrate, ongoing",
    # --- panneau coach ---
    "Panneau coach — n'apparaît pas dans le PDF": "Coach panel — hidden in the PDF",
    "Personnaliser le rapport selon le client": "Customise the report for the client",
    "Sections à inclure": "Sections to include",
    "Âge biologique": "Biological age",
    "Métabolisme (BMR)": "Metabolism (BMR)",
    "Évolution / tendances": "Change / trends",
    "Hydratation &amp; compléments": "Hydration &amp; supplements",
    "Objectif": "Goal",
    "Rythme (déficit/surplus)": "Rate (deficit/surplus)",
    "Niveau d'activité": "Activity level",
    "Pratique sportive (ratio lip./gluc.)": "Training type (fat/carb ratio)",
    "Repas / jour": "Meals / day",
    "— vide = auto": "— blank = auto",
    "Forcer macros (g) — vide = auto": "Force macros (g) — blank = auto",
    "Cible % gras": "Target body fat %",
    "Cible masse maigre (kg)": "Target lean mass (kg)",
    "Diagnostic osseux — scan dédié rachis + hanche (T-score ; Z si &lt;50 ou préménopause)":
        "Bone diagnosis — dedicated spine + hip scan (T-score; Z if &lt;50 or premenopausal)",
    "Statut": "Status", "Post-méno": "Post-meno", "Préméno": "Pre-meno",
    "🖨 Exporter en PDF": "🖨 Export to PDF",
    "Cochez/décochez les sections, ajustez l'objectif, saisissez le scan osseux dédié si disponible, puis « Exporter en PDF » : le PDF ne contiendra que ce qui est affiché.":
        "Tick/untick sections, adjust the goal, enter the dedicated bone scan if available, then “Export to PDF”: the PDF only contains what is shown.",
    "3 repas": "3 meals", "4 repas": "4 meals", "5 repas": "5 meals",
    "Endurance / beaucoup de cardio": "Endurance / lots of cardio",
    "Mixte cardio + musculation": "Mixed cardio + strength",
    "Musculation / force": "Strength / power",
    "Doux": "Gentle", "Modéré": "Moderate", "Agressif": "Aggressive",
    "Sédentaire (bureau)": "Sedentary (desk)",
    "Léger (1–3 séances/sem)": "Light (1–3 sessions/wk)",
    "Modéré (3–5 séances/sem)": "Moderate (3–5 sessions/wk)",
    "Intense (6–7 séances/sem)": "Intense (6–7 sessions/wk)",
    "Très intense (2×/j, physique)": "Very intense (2×/day, physical)",
    "Déficit (perte de gras)": "Deficit (fat loss)",
    "Maintien": "Maintenance",
    "Surplus (prise de muscle)": "Surplus (muscle gain)",
    "lip.": "fat",
    # --- projecteur / baseline ---
    "Objectif masse grasse": "Fat-mass goal",
    "Objectif masse maigre": "Lean-mass goal",
    "Réglez les cibles dans le panneau coach. Projection indicative, à rythme constant ; la réalité dépend de l'assiduité, du sommeil et de la nutrition.":
        "Set the targets in the coach panel. Indicative projection at a constant rate; reality depends on consistency, sleep and nutrition.",
    "Ce <b>premier DXA</b> devient la <b>référence personnelle</b> à laquelle les prochains examens seront comparés.":
        "This <b>first DXA</b> becomes the <b>personal reference</b> future exams are compared to.",
    # --- méthode ---
    "Comment est calculé l'âge biologique DXA": "How the DXA biological age is computed",
    "Chaque système est replacé sur la trajectoire d'âge d'une population de référence, puis converti en âge équivalent. Composite pondéré :":
        "Each system is placed on the age trajectory of a reference population, then converted to an equivalent age. Weighted composite:",
    "Sources des populations de référence": "Reference-population sources",
    "Sources — besoins nutritionnels": "Sources — nutritional needs",
    "Références scientifiques": "Scientific references",
    # titres des références (texte de lien) — pas de balises internes
    "Deep-learning body-composition ageing biomarker (DXA)": "Deep-learning body-composition ageing biomarker (DXA)",
    "Valeurs de référence DXA (âge adulte)": "DXA reference values (adult age)",
    "Seuils de graisse viscérale": "Visceral-fat thresholds",
    "Normes ALMI/FFMI (Hologic)": "ALMI/FFMI norms (Hologic)",
    "Plancher de masse grasse (athlète)": "Fat-mass floor (athlete)",
    # --- disclaimer / footer ---
    "L'« âge biologique DXA » est un indice pédagogique dérivé des mesures de composition corporelle et de populations de référence publiées ; ce n'est pas un diagnostic médical ni un biomarqueur validé cliniquement. Les images DXA ne sont pas destinées à un usage diagnostique. Toute interprétation clinique relève d'un professionnel de santé. Données : export Hologic Horizon Wi / APEX. Rapport généré automatiquement.":
        "The “DXA biological age” is an educational index derived from body-composition measures and published reference populations; it is not a medical diagnosis or a clinically validated biomarker. DXA images are not for diagnostic use. Any clinical interpretation is the responsibility of a health professional. Data: Hologic Horizon Wi / APEX export. Report generated automatically.",
    "Avertissement.": "Disclaimer.",
    # --- paragraphes longs (rendu) ---
    "Composite de trois systèmes tissulaires — os, muscle, métabolisme — chacun replacé sur la trajectoire d'âge d'une population de référence.":
        "Composite of three tissue systems — bone, muscle, metabolism — each placed on the age trajectory of a reference population.",
    "Le DXA mesure directement la masse maigre — le tissu qui consomme l'énergie — ce qui rend l'estimation du métabolisme bien plus précise que les formules basées sur le poids seul (Harris-Benedict, Mifflin).":
        "DXA measures lean mass directly — the tissue that burns energy — making the metabolism estimate far more accurate than weight-only formulas (Harris-Benedict, Mifflin).",
    "Échelle 20 → 40 ans. Indice éducatif pondéré": "Scale 20 → 40 yrs. Weighted educational index",
    "dérivé des mesures DXA. Ne remplace pas un avis médical.": "derived from DXA measures. Not a substitute for medical advice.",
    "Chaque système est replacé sur la trajectoire d'âge d'une population de référence, puis converti en âge équivalent. Composite pondéré :":
        "Each system is placed on the age trajectory of a reference population, then converted to an equivalent age. Weighted composite:",
    "Le poids seul ne dit pas tout : le DXA distingue ce qui vient du gras, du muscle et de l'os. Seuil de variation significative de la densité osseuse : ±0,014 g/cm².":
        "Weight alone doesn't tell all: DXA distinguishes what comes from fat, muscle and bone. Significant-change threshold for bone density: ±0.014 g/cm².",
    "Sous-régions du scan corps entier (sans T/Z) — non diagnostiques (ROI et base de référence différentes du rachis AP / hanche dédiés ; le bassin n'est pas un site reconnu). En revanche, le Δ vs examen précédent (même machine, même méthode) est une comparaison valide pour le suivi.":
        "Whole-body sub-regions (no T/Z) — not diagnostic (ROI and reference base differ from dedicated AP spine / hip; the pelvis is not a recognised site). However, the Δ vs previous exam (same machine, same method) is a valid comparison for follow-up.",
    "Timing péri-entraînement :": "Peri-workout timing:",
    "Repères généraux, à adapter au niveau, à la récupération et aux préférences du client.":
        "General guidance, to adapt to the client's level, recovery and preferences.",
    # --- barèmes (jauges) ---
    "3–5 essentiel": "3–5 essential", "6–13 athlète": "6–13 athlete",
    "14–24 sain": "14–24 healthy", "25+ élevé": "25+ high",
    "10–13 essentiel": "10–13 essential", "14–20 athlète": "14–20 athlete",
    "21–29 en forme": "21–29 fit", "32+ élevé": "32+ high",
    "7,0 seuil": "7.0 threshold", "8,6 médiane": "8.6 median", "10+ élite": "10+ elite",
    "5,5 seuil": "5.5 threshold", "6,1 médiane": "6.1 median", "7,5+ élite": "7.5+ elite",
    "16 sédentaire": "16 sedentary", "20 entraîné": "20 trained", "25 max naturel": "25 natural max",
    "13 sédentaire": "13 sedentary", "17 entraînée": "17 trained", "22 élevé": "22 high",
    "2 bas": "2 low", "5 sain": "5 healthy", "9+ élevé": "9+ high",
    "−2,5 ostéo": "−2.5 osteo", "0 moyenne": "0 mean", "−1,0": "−1.0",
    "seuil élevé": "high threshold", "risque": "risk",
    "Vous": "You", "Médiane · ": "Median · ", "Seuil sarcopénie · ": "Sarcopenia threshold · ",
    "Normal (T &gt; −1,0)": "Normal (T &gt; −1.0)", "Ostéopénie": "Osteopenia", "Ostéoporose": "Osteoporosis",
    # --- divers unités / mots ---
    "kcal/j": "kcal/day", "g/j": "g/day", "L/j": "L/day",
    "au-dessus du seuil de": "above the threshold of",
    "site déterminant": "deciding site", "significatif": "significant",
    "base : Z-score (vs âge) · sur le site le plus bas": "basis: Z-score (vs age) · on the lowest site",
    "base : T-score (OMS) · sur le site le plus bas": "basis: T-score (WHO) · on the lowest site",
    "Densité normale": "Normal density",
    "Sous la fourchette attendue pour l'âge": "Below the range expected for age",
    "Dans la fourchette attendue pour l'âge": "Within the range expected for age",
    # --- sous-âges (héros) ---
    "Décomposition par système": "Breakdown by system",
    "Métabolique": "Metabolic", "graisse viscérale": "visceral fat",
    "Osseux": "Bone", "densité minérale": "mineral density",
    "Musculaire": "Muscular", "masse maigre": "lean mass", "masse grasse": "fat mass",
    "masse maigre / taille²": "lean mass / height²",
    "masse grasse / taille²": "fat mass / height²",
    "maigre appendiculaire / taille²": "appendicular lean / height²",
    # --- tendances ---
    "% du corps": "% of body", "préservée pendant la perte de gras": "preserved during fat loss",
    "pts · ": "pts · ",
    "Lecture d'ensemble :": "Overview:",
    # --- fragments JS (repas / lipides / projecteur / bonedx) ---
    "g de protéines par repas": "g protein per meal",
    "au-dessus du seuil de ~": "above the ~",
    "g (": "g (",
    "g/kg) qui maximise la synthèse musculaire à chaque prise.":
        "g/kg) threshold that maximises muscle protein synthesis at each meal.",
    "g par repas": "g per meal",
    "est sous le seuil optimal de ~": "is below the optimal ~",
    "g. Regroupez sur moins de repas ou augmentez l\\'apport pour mieux stimuler le muscle.":
        "g. Combine into fewer meals or raise intake to better stimulate muscle.",
    "Lipides ≈ ": "Fat ≈ ", " % des kcal": "% of kcal",
    " — hors fourchette 30–40 % (surcharge)": " — outside the 30–40% band (override)",
    " (cible ": " (target ", "définir une cible inférieure à l\\'actuel": "set a target below current",
    "définir une cible supérieure à l\\'actuel": "set a target above current",
    "cible atteinte": "target reached", " mois · ": " months · ",
    "mesurée": "measured", "estimée": "estimated",
    "base : Z-score (vs âge)": "basis: Z-score (vs age)",
    "base : T-score (OMS)": "basis: T-score (WHO)",
    " · sur le site le plus bas (": " · on the lowest site (",
    "site déterminant": "deciding site",
    "Objectif masse grasse": "Fat-mass goal", "Objectif masse maigre": "Lean-mass goal",
    # --- répartition repas / labels ---
    "Repas ": "Meal ",
    # --- divers ---
    "Poids total": "Total weight",
    "au repos (BMR)": "at rest (BMR)",
}

_ORDERED = sorted(PHRASES.items(), key=lambda kv: len(kv[0]), reverse=True)

# Toute apostrophe dans une clé doit pouvoir matcher sa forme brute OU échappée HTML
# (esc() transforme ' en &#x27;). On rend aussi les motifs insensibles aux espaces /
# retours-ligne, pour les paragraphes rendus sur plusieurs lignes.
_APOS = r"(?:['’]|&#x27;|&#39;|&rsquo;|&apos;)"


def _compile(fr: str):
    parts = []
    for tok in fr.split():
        e = re.escape(tok)
        e = re.sub(r"['’]", _APOS, e)
        parts.append(e)
    return re.compile(r"\s+".join(parts))


_COMPILED = [(_compile(fr), en) for fr, en in _ORDERED]


def translate(text: str, lang: str) -> str:
    if lang != "en":
        return text
    # Protéger les data-URI (images base64) : leurs octets contiennent des sous-chaînes
    # qui peuvent coïncider avec des clés courtes (« IMC », etc.) et corrompre le JPEG.
    stash = []

    def _stash(m):
        stash.append(m.group(0))
        return f"\x00{len(stash) - 1}\x00"

    text = re.sub(r'data:[^"\'\s)]+', _stash, text)
    for pat, en in _COMPILED:
        text = pat.sub(lambda _m, _en=en: _en, text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], text)
    return text
