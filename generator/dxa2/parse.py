"""
Parseur d'export Hologic APEX (PDF) -> dictionnaire structuré.

Gère les deux mises en page rencontrées :
  - rapport mono-examen (ex. Flora : 4 pages, 1 date)
  - rapport multi-examens (ex. Cédrian : plusieurs dates, tableaux de tendance)

Stratégie : on classe chaque page par les ancres de texte qu'elle contient,
on extrait ce qu'elle porte, on tague chaque bloc par sa date d'examen, puis on
assemble un "instantané le plus récent" (la valeur la plus récente disponible
pour chaque champ) + l'historique pour les tendances.

Dépendance : PyMuPDF (import fitz).
"""
from __future__ import annotations
import re
import datetime as _dt

import fitz  # PyMuPDF

# --- mois FR pour parser "13 Juillet 2025" ---
_MOIS = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5,
    "juin": 6, "juillet": 7, "août": 8, "aout": 8, "septembre": 9,
    "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12,
}
_NUM = re.compile(r"^-?\d+(?:[.,]\d+)?$")


def _f(tok: str):
    """Token -> float (ou None). Retire un éventuel '*' de significativité."""
    if tok is None:
        return None
    t = tok.strip().rstrip("*").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def _lines(page_text: str):
    return [l.strip() for l in page_text.splitlines() if l.strip()]


def _nums_after(lines, i, n):
    """Retourne les n premiers tokens numériques à partir de la ligne i+1."""
    out = []
    j = i + 1
    while j < len(lines) and len(out) < n:
        v = _f(lines[j])
        if v is not None:
            out.append(v)
        elif out:
            # on s'arrête dès qu'on retombe sur du texte après avoir commencé
            break
        j += 1
    return out


def _find(lines, needle, start=0):
    for i in range(start, len(lines)):
        if needle in lines[i]:
            return i
    return -1


def _exam_date(lines):
    """Trouve la date d'examen (format '13 Juillet 2025') -> date."""
    for i, l in enumerate(lines):
        m = re.search(r"Date d'examen\s*:\s*(\d{1,2})\s+([A-Za-zéûôàèç]+)\s+(\d{4})", l)
        if not m:
            # parfois la date est sur la ligne suivante
            if "Date d'examen" in l and i + 1 < len(lines):
                m = re.search(r"(\d{1,2})\s+([A-Za-zéûôàèç]+)\s+(\d{4})", lines[i + 1])
        if m:
            d, mo, y = int(m.group(1)), m.group(2).lower(), int(m.group(3))
            if mo in _MOIS:
                return _dt.date(y, _MOIS[mo], d)
    return None


# ----------------------------------------------------------------------------
# Démographie
# ----------------------------------------------------------------------------
def parse_demographics(full_text: str) -> dict:
    def g(pat, cast=str, default=None):
        m = re.search(pat, full_text)
        if not m:
            return default
        try:
            return cast(m.group(1).strip())
        except Exception:
            return default

    sexe = g(r"Sexe\s*:\s*(Masculin|Féminin|Feminin)")
    sex = "F" if (sexe or "").lower().startswith("f") else "M"
    nom = g(r"Nom\s*:\s*([^\n]+)")
    return {
        "name": nom,
        "age": g(r"Age\s*:\s*(\d+)", int),
        "dob": g(r"DDN\s*:\s*([^\n]+)"),
        "sex": sex,
        "sex_label": sexe,
        "ethnicity": g(r"Ethnie\s*:\s*([^\n]+)"),
        "height_cm": g(r"Height:\s*([\d.]+)", float),
        "weight_kg": g(r"Poids\s*:\s*([\d.,]+)", lambda s: float(s.replace(",", "."))),
    }


# ----------------------------------------------------------------------------
# Pages typées
# ----------------------------------------------------------------------------
def _parse_bmd_regional(lines) -> dict:
    """Page DMO régionale : total DMO/T/Z + DMO par région."""
    out = {"regional_bmd": {}}
    # DMO régionale : "<Région>\n<surface>\n<cmo>\n<dmo>"
    region_map = {
        "Bras G": "bras_g", "Bras D": "bras_d",
        "Jambe G": "jambe_g", "Jambe D": "jambe_d",
        "Bassin": "bassin", "Rachis Lomb": "rachis_lomb",
        "T Rachis": "t_rachis",
    }
    for label, key in region_map.items():
        i = _find(lines, label)
        if i >= 0:
            v = _nums_after(lines, i, 3)  # surface, cmo, dmo
            if len(v) >= 3:
                out["regional_bmd"][key] = v[2]
    # Total : surface, cmo, dmo, T, Z  (on choisit le "Total" plausible)
    for i, l in enumerate(lines):
        if l == "Total" or l.startswith("Total"):
            v = _nums_after(lines, i, 5)
            if len(v) >= 3 and 0.3 <= v[2] <= 3.0:
                out["bmd_total"] = v[2]
                if len(v) >= 5 and -6 <= v[3] <= 6 and -6 <= v[4] <= 6:
                    out["bmd_t"] = v[3]
                    out["bmd_z"] = v[4]
                break
    return out


def _parse_composition_full(lines) -> dict:
    """Page composition détaillée : CMO/Graisse/Maigre/Maigre+/Total/%graisse."""
    out = {"regional_lean": {}, "regional_fatpct": {}}
    region_map = {
        "Bras G": "bras_g", "Bras D": "bras_d",
        "Jambe G": "jambe_g", "Jambe D": "jambe_d", "Tronc": "tronc",
    }
    for label, key in region_map.items():
        i = _find(lines, label)
        if i >= 0:
            v = _nums_after(lines, i, 6)  # cmo, fat, lean, lean+cmo, total, %fat
            if len(v) >= 6:
                out["regional_lean"][key] = v[2]
                out["regional_fatpct"][key] = v[5]
    # Total row (6 nombres)
    i = _find(lines, "Total")
    # prendre le Total suivi de 6 nombres, dont le dernier ~%fat (<60) et total_mass grand
    for j, l in enumerate(lines):
        if l == "Total":
            v = _nums_after(lines, j, 6)
            if len(v) >= 6 and v[4] > 10000 and v[5] < 70:
                out["bmc_g"] = v[0]
                out["fat_g"] = v[1]
                out["lean_g"] = v[2]
                out["lean_bmc_g"] = v[3]
                out["mass_g"] = v[4]
                out["bf_pct"] = v[5]
                break
    return out


def _parse_indices(lines) -> dict:
    """Page indices : TAV, FMI, A/G, tronc/membres, ALMI, LMI, %BF percentiles."""
    out = {}

    def val_after(label, n=1):
        i = _find(lines, label)
        if i < 0:
            return None if n == 1 else []
        v = _nums_after(lines, i, n)
        if n == 1:
            return v[0] if v else None
        return v

    out["vat_mass_g"] = val_after("Masse de TAV est.")
    out["vat_vol_cm3"] = val_after("Volume de TAV est.")
    out["vat_area_cm2"] = val_after("Surface de TAV est.")
    out["ag_ratio"] = val_after("Ratio Androïde/Gynoïde")
    out["trunk_limb_mass"] = val_after("Ratio MG Tronc/Membres")
    out["fmi"] = val_after("Masse Grasse/Taille")
    out["lmi"] = val_after("Masse maigre/Taille")
    # %BF + percentiles JN/AM (3 nombres après "Total % graisse corps")
    bf = val_after("Total % graisse corps", 3)
    if bf:
        out["bf_pct"] = bf[0]
        if len(bf) >= 3:
            out["bf_jn_pct"], out["bf_am_pct"] = bf[1], bf[2]
    # ALMI + percentiles JN/AM
    almi = val_after("Appen.M.maigre/Taille", 3)
    if almi:
        out["almi"] = almi[0]
        if len(almi) >= 3:
            out["almi_jn_pct"], out["almi_am_pct"] = almi[1], almi[2]
    # IMC (parfois sur cette page)
    i = _find(lines, "IMC =")
    if i >= 0:
        m = re.search(r"IMC\s*=\s*([\d.,]+)", lines[i])
        if m:
            out["bmi"] = _f(m.group(1))
    return out


def _parse_bmd_history(lines) -> list:
    """Tableau 'Résumé des résultats DXA' : [(date, age, dmo, t), ...]."""
    hist = []
    date_re = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4})$")
    i = 0
    while i < len(lines):
        m = date_re.match(lines[i])
        if m:
            # age, dmo, t doivent suivre
            rest = _nums_after(lines, i, 3)
            if len(rest) >= 3 and 0.5 <= rest[1] <= 2.2 and -6 <= rest[2] <= 6:
                d = _dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                hist.append({"date": d, "age": int(rest[0]),
                             "bmd": rest[1], "t": rest[2]})
        i += 1
    return hist


# en-têtes de sous-sections des pages de tendance (servent de bornes)
_TREND_HEADERS = [
    "Résultats Masse grasse totale",
    "Résultats totaux % graisse corps",
    "Total Lean Mass Results",
    "Résultats Masse totale",
]


def _parse_comp_history(lines, anchor, lo, hi) -> list:
    """Tableau de tendance (date, age, valeur) sous une ancre, borné à sa sous-section."""
    start = _find(lines, anchor)
    if start < 0:
        return []
    # borne haute : le prochain en-tête de sous-section après `start`
    end = len(lines)
    for h in _TREND_HEADERS:
        if h == anchor:
            continue
        k = _find(lines, h, start + 1)
        if 0 <= k < end:
            end = k
    seg = lines[start:end]
    hist = []
    date_re = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4})$")
    for i, l in enumerate(seg):
        m = date_re.match(l)
        if m:
            rest = _nums_after(seg, i, 2)  # age, valeur
            if len(rest) >= 2 and lo <= rest[1] <= hi:
                d = _dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                hist.append({"date": d, "age": int(rest[0]), "value": rest[1]})
    return hist


# ----------------------------------------------------------------------------
# Entrée principale
# ----------------------------------------------------------------------------
def parse_pdf(path: str) -> dict:
    doc = fitz.open(path)
    pages = [p.get_text() for p in doc]
    full = "\n".join(pages)

    data = parse_demographics(full)
    data["source_file"] = path
    data["n_pages"] = len(pages)

    # snapshots datés par page
    bmd_snaps, comp_snaps, idx_snaps = [], [], []
    bmd_history = []
    fat_hist, pct_hist, lean_hist, mass_hist = [], [], [], []

    def _longest(cur, new):
        return new if len(new) > len(cur) else cur

    for text in pages:
        lines = _lines(text)
        date = _exam_date(lines)

        if "Indices Adipeux" in text:
            s = _parse_indices(lines)
            s["date"] = date
            idx_snaps.append(s)

        if ("T -" in text and "Z -" in text) or "CV DMO TOTALE" in text:
            s = _parse_bmd_regional(lines)
            s["date"] = date
            if s.get("bmd_total"):
                bmd_snaps.append(s)

        if "Maigre +" in text and "% graisse" in text and "Indices Adipeux" not in text:
            s = _parse_composition_full(lines)
            s["date"] = date
            if s.get("mass_g"):
                comp_snaps.append(s)

        if "Résumé des résultats DXA" in text and "DMO" in text and "T -" in text:
            bmd_history = _parse_bmd_history(lines) or bmd_history

        if "Résultats totaux % graisse corps" in text or "Résultats Masse grasse totale" in text:
            fat_hist = _longest(fat_hist, _parse_comp_history(lines, "Résultats Masse grasse totale", 2000, 60000))
            pct_hist = _longest(pct_hist, _parse_comp_history(lines, "Résultats totaux % graisse corps", 3, 60))
            lean_hist = _longest(lean_hist, _parse_comp_history(lines, "Total Lean Mass Results", 20000, 90000))
            mass_hist = _longest(mass_hist, _parse_comp_history(lines, "Résultats Masse totale", 20000, 200000))

    def latest(snaps):
        dated = [s for s in snaps if s.get("date")]
        if dated:
            return sorted(dated, key=lambda s: s["date"])[-1]
        return snaps[-1] if snaps else {}

    bmd = latest(bmd_snaps)
    comp = latest(comp_snaps)
    idx = latest(idx_snaps)

    # instantané fusionné (le plus récent qui porte chaque champ)
    snap = {}
    for k in ("bmd_total", "bmd_t", "bmd_z", "regional_bmd"):
        if bmd.get(k) is not None:
            snap[k] = bmd[k]
    for k in ("fat_g", "lean_g", "bmc_g", "lean_bmc_g", "mass_g", "bf_pct",
              "regional_lean", "regional_fatpct"):
        if comp.get(k) is not None:
            snap[k] = comp[k]
    for k in ("vat_mass_g", "vat_vol_cm3", "vat_area_cm2", "ag_ratio",
              "trunk_limb_mass", "fmi", "lmi", "almi", "bmi",
              "bf_jn_pct", "bf_am_pct", "almi_jn_pct", "almi_am_pct"):
        if idx.get(k) is not None:
            snap[k] = idx[k]
    # %BF : préférer la composition la plus récente si l'indice manque
    if "bf_pct" not in snap and comp.get("bf_pct"):
        snap["bf_pct"] = comp["bf_pct"]

    data["snapshot"] = snap
    data["exam_dates"] = sorted({s["date"] for s in (bmd_snaps + comp_snaps + idx_snaps)
                                 if s.get("date")})
    data["latest_exam_date"] = data["exam_dates"][-1] if data["exam_dates"] else None
    data["bmd_history"] = bmd_history
    data["pct_history"] = pct_hist
    data["lean_history"] = lean_hist
    data["fat_history"] = fat_hist
    data["mass_history"] = mass_hist
    data["n_exams"] = max(len(data["exam_dates"]), len(bmd_history))
    return data


def extract_images(path: str):
    """Extrait (squelette, carte thermique) en data-URI depuis le PDF Hologic."""
    import base64
    doc = fitz.open(path)
    skeletal = thermal = None
    best_thermal_size = 0
    for pno in range(min(3, doc.page_count)):
        for im in doc[pno].get_images(full=True):
            d = doc.extract_image(im[0])
            w, h, ext, raw = d["width"], d["height"], d["ext"], d["image"]
            if ext != "jpeg" or h < 500:
                continue
            uri = f"data:image/{ext};base64," + base64.b64encode(raw).decode()
            if 300 <= w <= 340 and skeletal is None:      # squelette corps entier
                skeletal = uri
            elif 200 <= w <= 250:                          # composition (couleur = + gros)
                if len(raw) > best_thermal_size:
                    best_thermal_size = len(raw)
                    thermal = uri
    return skeletal, thermal
