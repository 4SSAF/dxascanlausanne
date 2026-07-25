"""
Mémoire client (local) : accumule les examens dans le temps.

But : même si un PDF Hologic ne contient qu'un seul examen, on conserve chaque
passage pour bâtir des tendances au fil des visites. 100 % local, jamais réseau.

Emplacement par défaut :
  - macOS : ~/Library/Application Support/RapportDXA/clients.json
  - autre : ~/.rapportdxa/clients.json
Le fichier contient des données patient : ne jamais le versionner.
"""
from __future__ import annotations
import json
import os
import sys
import datetime as _dt


def default_db_path() -> str:
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support/RapportDXA")
    else:
        base = os.path.expanduser("~/.rapportdxa")
    return os.path.join(base, "clients.json")


def _key(demo) -> str:
    return f"{(demo.get('name') or '').strip().lower()}|{(demo.get('dob') or '').strip().lower()}"


def load(path) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"clients": {}}


def save(path, db) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2, default=str)
    os.replace(tmp, path)


def _iso(d):
    return d.isoformat() if isinstance(d, _dt.date) else str(d)


def _exams_from_data(data) -> dict:
    """Reconstruit un dict {date_iso: {métriques}} depuis le PDF courant."""
    exams = {}

    def ensure(diso):
        return exams.setdefault(diso, {})

    for h in data.get("bmd_history", []):
        e = ensure(_iso(h["date"]))
        e["age"] = h.get("age"); e["bmd"] = h.get("bmd"); e["t"] = h.get("t")
    for h in data.get("pct_history", []):
        ensure(_iso(h["date"]))["bf_pct"] = h.get("value")
    for h in data.get("lean_history", []):
        ensure(_iso(h["date"]))["lean_g"] = h.get("value")
    for h in data.get("fat_history", []):
        ensure(_iso(h["date"]))["fat_g"] = h.get("value")
    for h in data.get("mass_history", []):
        ensure(_iso(h["date"]))["mass_g"] = h.get("value")
    # instantané le plus récent
    d = data.get("latest_exam_date")
    s = data.get("snapshot", {})
    if d:
        e = ensure(_iso(d))
        for k_src, k_dst in [("bmd_total", "bmd"), ("bmd_t", "t"), ("bf_pct", "bf_pct"),
                             ("lean_g", "lean_g"), ("fat_g", "fat_g"), ("mass_g", "mass_g"),
                             ("almi", "almi"), ("vat_mass_g", "vat_mass_g")]:
            if s.get(k_src) is not None and e.get(k_dst) is None:
                e[k_dst] = s[k_src]
        if e.get("age") is None:
            e["age"] = data.get("age")
    return exams


def merge(data, path=None, write=True):
    """Enregistre l'examen courant et fusionne l'historique stocké dans `data`.
    Renvoie (data, n_stored_exams)."""
    path = path or default_db_path()
    db = load(path)
    clients = db.setdefault("clients", {})
    key = _key(data)
    rec = clients.setdefault(key, {"name": data.get("name"), "dob": data.get("dob"),
                                   "sex": data.get("sex"), "exams": {}})
    rec["name"] = data.get("name"); rec["dob"] = data.get("dob"); rec["sex"] = data.get("sex")

    # upsert des examens du PDF courant
    for diso, metrics in _exams_from_data(data).items():
        slot = rec["exams"].setdefault(diso, {})
        for k, v in metrics.items():
            if v is not None:
                slot[k] = v
    if write:
        save(path, db)

    # reconstruire les historiques depuis l'union stockée
    dates = sorted(rec["exams"].keys())
    bmd_h, pct_h, lean_h, fat_h, mass_h = [], [], [], [], []
    for diso in dates:
        e = rec["exams"][diso]
        d = _dt.date.fromisoformat(diso)
        if e.get("bmd") is not None:
            bmd_h.append({"date": d, "age": e.get("age"), "bmd": e["bmd"], "t": e.get("t")})
        if e.get("bf_pct") is not None:
            pct_h.append({"date": d, "value": e["bf_pct"]})
        if e.get("lean_g") is not None:
            lean_h.append({"date": d, "value": e["lean_g"]})
        if e.get("fat_g") is not None:
            fat_h.append({"date": d, "value": e["fat_g"]})
        if e.get("mass_g") is not None:
            mass_h.append({"date": d, "value": e["mass_g"]})

    data["bmd_history"] = bmd_h or data.get("bmd_history", [])
    data["pct_history"] = pct_h or data.get("pct_history", [])
    data["lean_history"] = lean_h or data.get("lean_history", [])
    data["fat_history"] = fat_h or data.get("fat_history", [])
    data["mass_history"] = mass_h or data.get("mass_history", [])
    n = len(dates)
    data["n_exams"] = max(data.get("n_exams", 0), n)
    return data, n
