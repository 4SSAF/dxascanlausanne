"""
Moteur d'analyse : instantané parsé -> valeurs enrichies prêtes à afficher
(âge biologique, barèmes de jauges, statuts, asymétrie, interprétation, tendances).
"""
from __future__ import annotations
from . import references as R


def _meter(value, scale, zones, scale_labels, ref=None):
    """Construit la config d'une jauge."""
    lo, hi = scale
    return {
        "value": value,
        "marker": R.scale_pos(value, lo, hi),
        "ref": R.scale_pos(ref, lo, hi) if ref is not None else None,
        "zones": R.zones_to_widths(zones, lo, hi),
        "labels": scale_labels,
    }


def _ffmi(snap, height_m):
    if snap.get("lean_bmc_g") and height_m:
        return round(snap["lean_bmc_g"] / 1000.0 / (height_m ** 2), 1)
    return None


def metabolism(snap, weight_kg):
    """BMR (Cunningham 1991) à partir de la masse maigre (FFM) mesurée au DXA."""
    ffm_g = snap.get("lean_bmc_g")
    if ffm_g is None and snap.get("lean_g") and snap.get("bmc_g"):
        ffm_g = snap["lean_g"] + snap["bmc_g"]
    if not ffm_g:
        return None
    ffm = ffm_g / 1000.0
    bmr = round(R.CUNNINGHAM["base"] + R.CUNNINGHAM["coef"] * ffm)
    return {"ffm_kg": round(ffm, 1), "bmr": bmr, "weight_kg": weight_kg}


def nutrition(bmr, weight_kg, ffm_kg=None, activity_key=None, goal_key=None, meals=None):
    """Besoins caloriques + macros + répartition par repas (valeurs par défaut)."""
    act = dict((k, v) for k, _, v in R.ACTIVITY)[activity_key or R.ACTIVITY_DEFAULT]
    gadj = dict((k, v) for k, _, v in R.GOALS)[goal_key or R.GOAL_DEFAULT]
    goal_key = goal_key or R.GOAL_DEFAULT
    meals = meals or R.MEALS_DEFAULT
    tdee = round(bmr * act)
    kcal = round(tdee * (1 + gadj))
    # protéines : base FFM (masse maigre) ou poids total selon la config
    if R.PROTEIN_BASIS == "ffm" and ffm_kg:
        p_per_kg = R.PROTEIN_G_PER_KG_FFM[goal_key]
        protein = round(ffm_kg * p_per_kg)
    else:
        p_per_kg = R.PROTEIN_G_PER_KG_BW[goal_key]
        protein = round(weight_kg * p_per_kg)
    fat = round(weight_kg * R.FAT_G_PER_KG)
    kcal_pf = protein * R.KCAL["prot"] + fat * R.KCAL["fat"]
    carbs = max(0, round((kcal - kcal_pf) / R.KCAL["carb"]))
    per_meal_p = round(protein / meals)
    mps_min = round(weight_kg * R.PROTEIN_PER_MEAL_G_PER_KG)
    return {
        "activity": activity_key or R.ACTIVITY_DEFAULT, "goal": goal_key, "meals": meals,
        "tdee": tdee, "kcal": kcal, "protein": protein, "carbs": carbs, "fat": fat,
        "p_per_kg": p_per_kg,
        "kcal_p": protein * 4, "kcal_c": carbs * 4, "kcal_f": fat * 9,
        "per_meal_p": per_meal_p, "mps_min": mps_min,
        "per_meal_kcal": round(kcal / meals),
    }


# ---------------------------------------------------------------------------
# Âge biologique (heuristique transparente et calibrable)
# ---------------------------------------------------------------------------
def bio_age(demo, snap):
    sex = demo["sex"]
    a = R.ANCHORS[sex]
    chrono = demo["age"]

    # -- métabolique : TAV (primaire) + % masse grasse
    dm = 0.0
    parts_metab = []
    if snap.get("vat_mass_g") is not None:
        r = snap["vat_mass_g"] / a["vat_mass_thr"]
        dm += (r - 0.5) * 8.0
        parts_metab.append(f"TAV {snap['vat_mass_g']:.0f} g ({r*100:.0f}% du seuil)")
    if snap.get("bf_pct") is not None:
        dm += (snap["bf_pct"] - a["bf_healthy_mid"]) * 0.35
        parts_metab.append(f"%MG {snap['bf_pct']:.1f}")
    dm = R.clamp(dm, -9, 12)
    metab = round(R.clamp(chrono + dm, 18, 90))

    # -- musculaire : percentile ALMI pour l'âge, sinon ALMI vs médiane jeune
    parts_mus = []
    if snap.get("almi_am_pct") is not None:
        dmu = (50 - snap["almi_am_pct"]) * 0.14
        parts_mus.append(f"ALMI {snap.get('almi')} ({snap['almi_am_pct']:.0f}e perc. âge)")
    elif snap.get("almi") is not None:
        z = (snap["almi"] - a["almi_median"]) / a["almi_sd"]
        dmu = -z * 4.0
        parts_mus.append(f"ALMI {snap['almi']} vs médiane {a['almi_median']}")
    else:
        dmu = 0.0
    dmu = R.clamp(dmu, -10, 12)
    muscle = round(R.clamp(chrono + dmu, 18, 90))

    # -- osseux : Z-score (sinon T-score)
    z = snap.get("bmd_z")
    if z is None:
        z = snap.get("bmd_t")
    if z is not None:
        db = R.clamp(-z * 6.0, -8, 10)
        bone = round(R.clamp(chrono + db, 18, 90))
        parts_bone = [f"{'Z' if snap.get('bmd_z') is not None else 'T'}-score {z:+.1f}"]
    else:
        bone = chrono
        parts_bone = ["indisponible"]

    w = R.BIOAGE_WEIGHTS
    composite = round(w["metabolic"] * metab + w["muscle"] * muscle + w["bone"] * bone)
    return {
        "composite": composite,
        "metabolic": metab, "muscle": muscle, "bone": bone,
        "delta": composite - chrono,
        "weights": w,
        "explain": {"metabolic": parts_metab, "muscle": parts_mus, "bone": parts_bone},
    }


# ---------------------------------------------------------------------------
# Analyse complète
# ---------------------------------------------------------------------------
def analyze(data: dict) -> dict:
    demo = {k: data[k] for k in ("name", "age", "sex", "sex_label", "height_cm",
                                 "weight_kg", "ethnicity", "dob")}
    snap = data["snapshot"]
    sex = demo["sex"]
    a = R.ANCHORS[sex]
    h_m = (demo["height_cm"] or 0) / 100.0

    out = {"demo": demo, "snap": snap, "n_exams": data["n_exams"],
           "latest_exam_date": data["latest_exam_date"]}

    # dérivés
    ffmi = _ffmi(snap, h_m)
    out["ffmi"] = ffmi
    out["bmi"] = snap.get("bmi") or (round(demo["weight_kg"] / (h_m ** 2), 1) if h_m else None)

    # masse : parts pour la barre empilée
    if snap.get("mass_g"):
        m = snap["mass_g"]
        out["mass"] = {
            "total_kg": round(m / 1000, 1),
            "lean_kg": round(snap["lean_g"] / 1000, 1),
            "fat_kg": round(snap["fat_g"] / 1000, 1),
            "bmc_kg": round(snap["bmc_g"] / 1000, 1),
            "lean_pct": round(snap["lean_g"] / m * 100, 1),
            "fat_pct": round(snap["fat_g"] / m * 100, 1),
            "bmc_pct": round(snap["bmc_g"] / m * 100, 1),
        }

    # jauges
    out["meters"] = {
        "bf": _meter(snap.get("bf_pct"), a["bf_scale"], a["bf_zones"], a["bf_scale_labels"]),
        "fmi": _meter(snap.get("fmi"), a["fmi_scale"], a["fmi_zones"], a["fmi_scale_labels"]),
        "ffmi": _meter(ffmi, a["ffmi_scale"], a["ffmi_zones"], a["ffmi_scale_labels"]),
        "almi": _meter(snap.get("almi"), a["almi_scale"], a["almi_zones"], a["almi_scale_labels"],
                       ref=a["almi_median"]),
        "bmd": _meter(snap.get("bmd_t"), R.BMD_SCALE, R.BMD_ZONES, R.BMD_SCALE_LABELS, ref=0.0),
        "vat_area": _meter(snap.get("vat_area_cm2"), (0.0, a["vat_area_max"]),
                           [(0, a["vat_area_thr"], "good"),
                            (a["vat_area_thr"], a["vat_area_thr"] * 1.4, "warn"),
                            (a["vat_area_thr"] * 1.4, a["vat_area_max"], "risk")],
                           ["0", f"{a['vat_area_thr']:.0f} seuil élevé", "risque"]),
    }

    # statuts (scorecards)
    out["status"] = _statuses(snap, a, sex)

    # âge biologique
    out["bioage"] = bio_age(demo, snap)

    # asymétrie des bras
    rl = snap.get("regional_lean", {})
    if rl.get("bras_g") and rl.get("bras_d"):
        g, d = rl["bras_g"], rl["bras_d"]
        hi, lo = max(g, d), min(g, d)
        pct = (hi - lo) / lo * 100
        out["arm_asym"] = {"pct": round(pct, 1),
                           "bigger": "droit" if d >= g else "gauche",
                           "flag": pct >= 10.0}
    else:
        out["arm_asym"] = None

    # tendances
    out["has_history"] = data["n_exams"] > 1 and len(data.get("bmd_history", [])) > 1
    out["trends"] = _trends(data)
    out["velocity"] = _velocity(data)
    out["since_last"] = _since_last(data)

    # métabolisme (BMR Cunningham) + nutrition par défaut
    out["metabolism"] = metabolism(snap, demo["weight_kg"])
    if out["metabolism"]:
        out["nutrition"] = nutrition(out["metabolism"]["bmr"], demo["weight_kg"],
                                     ffm_kg=out["metabolism"]["ffm_kg"])
    else:
        out["nutrition"] = None

    # interprétation + actions
    out["interp"] = _interpret(out)

    # méta VAT / seuils pour l'affichage
    out["vat_mass_thr"] = a["vat_mass_thr"]
    out["vat_ref_txt"] = f"~{'4' if sex=='M' else '6'}×"  # informatif, remplacé ci-dessous
    if snap.get("vat_mass_g"):
        ratio = a["vat_mass_thr"] / snap["vat_mass_g"]
        out["vat_ref_txt"] = f"~{ratio:.0f}×"
    return out


def _statuses(snap, a, sex):
    st = {}
    # graisse viscérale
    vm = snap.get("vat_mass_g")
    if vm is not None:
        if vm < a["vat_mass_thr"] * 0.5:
            st["vat"] = ("good", "OPTIMAL")
        elif vm < a["vat_mass_thr"]:
            st["vat"] = ("warn", "CORRECT")
        else:
            st["vat"] = ("risk", "ÉLEVÉ")
    # muscle (ALMI)
    almi = snap.get("almi")
    if almi is not None:
        if almi < a["almi_thr"]:
            st["muscle"] = ("risk", "FAIBLE")
        elif almi < a["almi_median"]:
            st["muscle"] = ("warn", "À DÉVELOPPER")
        else:
            st["muscle"] = ("good", "SOLIDE")
    # os
    t = snap.get("bmd_t")
    if t is not None:
        if t <= -2.5:
            st["bone"] = ("risk", "OSTÉOPOROSE")
        elif t < -1.0:
            st["bone"] = ("warn", "OSTÉOPÉNIE")
        elif t >= 0.3:
            st["bone"] = ("good", "SUPÉRIEUR")
        else:
            st["bone"] = ("good", "NORMAL")
    # masse grasse
    bf = snap.get("bf_pct")
    if bf is not None:
        if bf <= a["bf_athletic"]:
            st["bf"] = ("good", "ATHLÉTIQUE")
        elif bf <= a["bf_healthy_mid"] + 6:
            st["bf"] = ("good", "SAIN")
        elif bf <= a["bf_healthy_mid"] + 13:
            st["bf"] = ("warn", "ÉLEVÉ")
        else:
            st["bf"] = ("risk", "TRÈS ÉLEVÉ")
    return st


def _trends(data):
    def series(hist, div=1.0):
        return [{"date": h["date"], "value": round(h["value"] / div, 3)} for h in hist]
    return {
        "bmd": [{"date": h["date"], "value": h["bmd"], "t": h["t"]} for h in data.get("bmd_history", [])],
        "bf": [{"date": h["date"], "value": h["value"]} for h in data.get("pct_history", [])],
        "lean": series(data.get("lean_history", []), 1000.0),
    }


def _since_last(data):
    """Comparatif entre les deux examens les plus récents (None si <2)."""
    def last_two(hist, div=1.0):
        pts = [h for h in hist if h.get("date")]
        if len(pts) < 2:
            return None
        a, b = pts[-2], pts[-1]
        return (a["date"], round(a["value"] / div, 3), b["date"], round(b["value"] / div, 3))

    specs = [  # (clé histo, div, label, unité, décimales, sens_favorable)
        ("mass_history", 1000.0, "Poids total", "kg", 1, "neutre"),
        ("pct_history", 1.0, "% masse grasse", "%", 1, "bas"),
        ("fat_history", 1000.0, "Masse grasse", "kg", 1, "bas"),
        ("lean_history", 1000.0, "Masse maigre", "kg", 1, "haut"),
    ]
    rows, dates = [], None
    for key, div, label, unit, dec, favor in specs:
        lt = last_two(data.get(key, []), div)
        if not lt:
            continue
        d0, v0, d1, v1 = lt
        v0, v1 = round(v0, dec), round(v1, dec)   # cohérence affichage/delta
        dates = (d0, d1)
        delta = round(v1 - v0, dec)
        if abs(delta) < (0.2 if unit == "kg" else 0.3):
            verdict = "neutral"
        elif favor == "neutre":
            verdict = "neutral"
        elif (favor == "bas" and delta < 0) or (favor == "haut" and delta > 0):
            verdict = "good"
        else:
            verdict = "warn"
        rows.append({"label": label, "unit": unit, "prev": v0, "curr": v1,
                     "delta": delta, "dir": "up" if delta > 0 else ("down" if delta < 0 else "flat"),
                     "verdict": verdict, "dec": dec})

    # DMO (avec seuil de significativité)
    bmd = [h for h in data.get("bmd_history", []) if h.get("date")]
    if len(bmd) >= 2:
        a, b = bmd[-2], bmd[-1]
        dates = (a["date"], b["date"])
        delta = round(b["bmd"] - a["bmd"], 3)
        sig = abs(delta) >= R.BMD_LSC
        verdict = "neutral" if not sig else ("good" if delta > 0 else "warn")
        rows.append({"label": "Densité osseuse", "unit": "g/cm²", "prev": a["bmd"], "curr": b["bmd"],
                     "delta": delta, "dir": "up" if delta > 0 else ("down" if delta < 0 else "flat"),
                     "verdict": verdict, "dec": 3, "sig": sig})

    if not rows or not dates:
        return None
    months = round((dates[1] - dates[0]).days / 30.44, 1)
    return {"prev_date": dates[0], "curr_date": dates[1], "months": months, "rows": rows}


def _velocity(data):
    """Vitesse mensuelle mesurée (points, sinon None) : %MG/mois et kg maigre/mois."""
    def rate(hist, div=1.0):
        pts = [h for h in hist if h.get("date")]
        if len(pts) < 2:
            return None
        a, b = pts[-2], pts[-1]
        months = (b["date"] - a["date"]).days / 30.44
        if months <= 0:
            return None
        return round((b["value"] - a["value"]) / div / months, 3)
    return {"fat_pct_per_month": rate(data.get("pct_history", [])),
            "lean_kg_per_month": rate(data.get("lean_history", []), 1000.0)}


def _interpret(out):
    """Génère lead + paragraphe + actions priorisées à partir des signaux."""
    snap = out["snap"]; a = R.ANCHORS[out["demo"]["sex"]]; sex = out["demo"]["sex"]
    female = sex == "F"
    flags = []

    muscle_low = snap.get("almi") is not None and snap["almi"] < a["almi_median"]
    bf_floor = snap.get("bf_pct") is not None and snap["bf_pct"] <= a["bf_athletic"] + 1
    vat_great = snap.get("vat_mass_g") is not None and snap["vat_mass_g"] < a["vat_mass_thr"] * 0.5
    bone_great = snap.get("bmd_t") is not None and snap["bmd_t"] >= 0.3
    bone_normal = snap.get("bmd_t") is not None and snap["bmd_t"] > -1.0
    lean_bmi = out["bmi"] is not None and out["bmi"] < 20
    asym = out.get("arm_asym") and out["arm_asym"]["flag"]

    # lead
    strengths = []
    if vat_great:
        strengths.append("métabolique")
    if bone_great:
        strengths.append("osseux")
    lead_strength = " et ".join(strengths) if strengths else "de composition"
    if muscle_low:
        lead = (f"Un profil {lead_strength} excellent, dont le principal axe de progrès "
                f"est la construction de muscle.")
    else:
        lead = f"Un profil {lead_strength} solide et équilibré, à entretenir."

    # paragraphe
    para = []
    if vat_great:
        para.append("La graisse viscérale est remarquablement basse : le risque cardiométabolique lié à la composition corporelle est minime.")
    if bone_great:
        para.append("La densité osseuse dépasse la moyenne du jeune adulte — un atout à préserver.")
    elif bone_normal:
        para.append("La densité osseuse est normale.")
    if muscle_low:
        para.append("La masse musculaire se situe autour de la médiane de référence : c'est le poste où un gain apporterait le plus (force, métabolisme, protection osseuse).")
    if bf_floor:
        if female:
            para.append("La masse grasse est déjà basse : combinée à un IMC modeste, la priorité est un apport énergétique suffisant, pas une perte de poids.")
        else:
            para.append("La masse grasse est en zone athlétique, proche du plancher : descendre plus bas n'apporterait aucun bénéfice santé.")
    interp_para = " ".join(para)

    # actions priorisées
    actions = []
    if muscle_low:
        target = round(snap["almi"] + 0.6, 1)
        actions.append(("Renforcement musculaire progressif",
                        f"Musculation orientée hypertrophie/force. Objectif : ALMI {snap['almi']} → {target}+ kg/m² sur 12 mois.",
                        "Priorité — levier n°1 sur l'âge biologique"))
    if female and (bf_floor or lean_bmi):
        actions.append(("Disponibilité énergétique (éviter le RED-S)",
                        "Énergie suffisante et protéines 1,6–2,2 g/kg/j. Protéger cycle hormonal et capital osseux — ne pas viser plus maigre.",
                        "Nutrition · santé féminine"))
    elif bf_floor:
        actions.append(("Nourrir la performance, pas la restriction",
                        "Protéines 1,6–2,2 g/kg/j et énergie suffisante. À ce niveau de masse grasse, la priorité est l'apport, pas le déficit.",
                        "Nutrition"))
    if asym:
        ar = out["arm_asym"]
        actions.append(("Corriger l'asymétrie des bras",
                        f"Écart bras {ar['pct']:.0f} % ({ar['bigger']} plus fort). Travail unilatéral en démarrant par le côté faible.",
                        "Prévention blessure · esthétique"))
    actions.append(("Entretenir le capital osseux",
                    "Charges lourdes et impacts, apports calcium/vitamine D adéquats.",
                    "Prévention long terme"))
    if out["has_history"]:
        actions.append(("Poursuivre le suivi",
                        "Re-scan dans 6–12 mois pour prolonger les tendances (seuil DMO significatif ±0,014 g/cm²).",
                        "Suivi"))
    else:
        actions.append(("Créer la première tendance",
                        "Ce premier examen devient la référence. Re-scan dans 6–12 mois pour mesurer objectivement les gains.",
                        "Suivi"))

    return {"lead": lead, "para": interp_para, "actions": actions[:4]}
