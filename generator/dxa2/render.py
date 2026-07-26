"""
Rendu HTML du Rapport 2.0 à partir des données analysées.
Auto-suffisant (CSS embarqué, images en data-URI), thème clair/sombre, imprimable.
"""
from __future__ import annotations
import os
import html as _html
import json as _json

from . import references as R

_ZONE_BG = {"risk": "var(--risk-bg)", "warn": "var(--warn-bg)",
            "good": "var(--good-bg)", "brand": "var(--brand-bg)"}
_STYLE = os.path.join(os.path.dirname(__file__), "style.css")
_LOGO_FILE = os.path.join(os.path.dirname(__file__), "logo.b64")


def _logo_uri():
    try:
        with open(_LOGO_FILE, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return None

_MOIS = ["", "janvier", "février", "mars", "avril", "mai", "juin", "juillet",
         "août", "septembre", "octobre", "novembre", "décembre"]


def fr(x, dec=1):
    """Nombre au format FR (virgule décimale)."""
    if x is None:
        return "—"
    s = f"{x:.{dec}f}" if dec else f"{x:.0f}"
    return s.replace(".", ",")


def _date_fr(d):
    return f"{d.day:02d}.{d.month:02d}.{d.year}" if d else "—"


def esc(s):
    return _html.escape(str(s)) if s is not None else ""


# --- composants ---------------------------------------------------------------
def _zones_html(zones):
    return "".join(
        f'<div class="z" style="width:{w:.2f}%;background:{_ZONE_BG.get(tok, "var(--inset)")}"></div>'
        for (w, tok) in zones)


def _meter(name, sub, read, meter, legend_html=""):
    ref = ""
    if meter.get("ref") is not None:
        ref = f'<span class="mkref" style="left:{meter["ref"]:.1f}%"></span>'
    mk = ""
    if meter.get("marker") is not None:
        mk = f'<span class="mk" style="left:{meter["marker"]:.1f}%"></span>'
    labels = "".join(f"<span>{esc(l)}</span>" for l in meter["labels"])
    return f'''<div class="metric">
      <div class="row"><span class="name">{name} <small>{sub}</small></span>
        <span class="read">{read}</span></div>
      <div class="meter"><div class="track"><div class="zones">{_zones_html(meter["zones"])}</div>
        {ref}{mk}</div>
        <div class="scale">{labels}</div>
      </div>{legend_html}
    </div>'''


def _rbar(label, pct, value, dim=False):
    op = ";opacity:.72" if dim else ""
    return (f'<div class="rbar"><span class="rl">{esc(label)}</span>'
            f'<div class="rt"><span class="rf" style="width:{pct:.0f}%;background:var(--muscle){op}"></span></div>'
            f'<span class="rv">{esc(value)}</span></div>')


def _rbar_bone(label, pct, value):
    # value peut contenir du HTML de confiance (delta) -> ne pas échapper
    return (f'<div class="rbar"><span class="rl">{esc(label)}</span>'
            f'<div class="rt"><span class="rf" style="width:{pct:.0f}%;background:var(--bone)"></span></div>'
            f'<span class="rv">{value}</span></div>')


def _line_svg(points, color, label):
    """points: list of (x_label_date, value). Renvoie un SVG 260x120."""
    if not points:
        return ""
    vals = [p["value"] for p in points]
    vmin, vmax = min(vals), max(vals)
    if vmax == vmin:
        vmax += 1
    pad = (vmax - vmin) * 0.15 or 1
    lo, hi = vmin - pad, vmax + pad
    n = len(points)
    xs = [46 + (205 * i / (n - 1)) if n > 1 else 150 for i in range(n)]
    ys = [100 - (p["value"] - lo) / (hi - lo) * 90 for p in points]
    poly = " ".join(f"{x:.0f},{y:.0f}" for x, y in zip(xs, ys))
    circles = ""
    for i, (x, y, p) in enumerate(zip(xs, ys, points)):
        r = 4 if i == n - 1 else 3
        ring = ' stroke="var(--surface)" stroke-width="1.5"' if i == n - 1 else ""
        circles += (f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="{color}"{ring}>'
                    f'<title>{_date_fr(p["date"])} — {fr(p["value"], 2)}</title></circle>')
    return f'''<svg viewBox="0 0 260 120" role="img" aria-label="{esc(label)}">
      <line x1="30" y1="10" x2="30" y2="100" stroke="var(--hairline-2)" stroke-width="1"/>
      <line x1="30" y1="100" x2="252" y2="100" stroke="var(--hairline-2)" stroke-width="1"/>
      <text x="4" y="16" class="num" font-size="8" fill="var(--muted)">{fr(hi, 2)}</text>
      <text x="4" y="99" class="num" font-size="8" fill="var(--muted)">{fr(lo, 2)}</text>
      <polyline fill="none" stroke="{color}" stroke-width="2.5" stroke-linejoin="round"
        stroke-linecap="round" points="{poly}"/>{circles}
    </svg>'''


# --- sections -----------------------------------------------------------------
def _header(A, subtitle):
    name = R.CLINIC_NAME or R.DOC_TITLE
    if R.SHOW_LOGO and _logo_uri():
        mark = f'<img class="mark-img" src="{_logo_uri()}" alt="">'
    else:
        mark = '<div class="mark" style="font-size:12px;letter-spacing:.02em">DXA</div>'
    return f'''<header class="topbar">
    <div class="brand">{mark}
      <div><div class="name">{esc(name)}</div>
        <div class="sub">{esc(R.CLINIC_TAGLINE)}</div></div></div>
    <div class="doc-tag"><span class="pill tag">◆ Rapport&nbsp;2.0</span>
      <div style="margin-top:8px;font-size:11px;color:var(--muted);font-family:var(--font-mono)">
        {subtitle}</div></div>
  </header>'''


def _patient(A):
    d = A["demo"]
    sexsym = "♀" if d["sex"] == "F" else "♂"
    suivi = (f'{A["n_exams"]} <small>scans</small>' if A["n_exams"] > 1
             else '1<small>er scan · baseline</small>')
    return f'''<div class="patient">
    <div class="chip"><div class="k">Client</div><div class="v">{esc(d["name"])}</div></div>
    <div class="chip"><div class="k">Âge civil</div><div class="v">{d["age"]} <small>ans · {sexsym}</small></div></div>
    <div class="chip"><div class="k">Taille</div><div class="v">{fr(d["height_cm"],0)} <small>cm</small></div></div>
    <div class="chip"><div class="k">Poids</div><div class="v">{fr(d["weight_kg"])} <small>kg</small></div></div>
    <div class="chip"><div class="k">IMC</div><div class="v">{fr(A["bmi"])} <small>{_bmi_class(A["bmi"])}</small></div></div>
    <div class="chip"><div class="k">Examen</div><div class="v">{_date_fr(A["latest_exam_date"])}</div></div>
    <div class="chip"><div class="k">Suivi</div><div class="v">{suivi}</div></div>
    <div class="chip"><div class="k">Appareil</div><div class="v">Horizon Wi</div></div>
  </div>'''


def _bmi_class(bmi):
    if bmi is None:
        return ""
    if bmi < 18.5:
        return "Maigreur"
    if bmi < 25:
        return "Normal"
    if bmi < 30:
        return "Surpoids"
    return "Obésité"


def _status_pill(st):
    tone, label = st
    return f'<span class="status {tone}"><span class="d"></span>{label}</span>'


def _hero(A):
    b = A["bioage"]
    d = A["demo"]
    civil_pos = _apos(d["age"])
    bio_pos = _apos(b["composite"])
    delta = b["delta"]
    if delta < 0:
        dtxt = f'▼ {abs(delta)} an{"s" if abs(delta) > 1 else ""} plus jeune que l\'âge civil ({d["age"]})'
        dcls = "delta"
    elif delta > 0:
        dtxt = f'▲ {delta} an{"s" if delta > 1 else ""} au-dessus de l\'âge civil ({d["age"]})'
        dcls = "delta"
    else:
        dtxt = f'≈ égal à l\'âge civil ({d["age"]})'
        dcls = "delta"

    def sub(lbl, small, age, color):
        w = max(4, min(96, (age - 18) / 22 * 100))
        return f'''<div class="subage">
          <div class="lbl">{lbl}<small>{small}</small></div>
          <div class="track"><span class="fill" style="width:{w:.0f}%;background:{color}"></span></div>
          <div class="val" style="color:{color}">≈ {age}</div></div>'''

    refs = "féminines" if d["sex"] == "F" else "masculines"
    return f'''<section data-mod="bioage">
    <div class="sec-head"><span class="idx">01</span><h2>Âge biologique &amp; score global</h2>
      <span class="note">Références {refs} (NHANES + cohortes récentes).</span></div>
    <div class="hero"><div class="hero-in">
      <div class="hero-left">
        <div class="eyebrow">Âge biologique DXA — estimation</div>
        <div class="bigage"><span class="n">{b["composite"]}</span><span class="u">ans<br>biologiques</span></div>
        <span class="{dcls}">{dtxt}</span>
        <div class="axis"><div class="bar">
          <span class="tick" style="left:{civil_pos:.0f}%" title="Âge civil {d['age']}"></span>
          <span class="lab" style="left:{civil_pos:.0f}%;color:var(--ink-2)">civil {d['age']}</span>
          <span class="tick you" style="left:{bio_pos:.0f}%" title="Âge biologique {b['composite']}"></span>
          <span class="lab" style="left:{bio_pos:.0f}%;color:var(--brand);font-weight:700;top:-24px">bio {b['composite']}</span>
        </div><div class="scaleline"><span>20</span><span>25</span><span>30</span><span>35</span><span>40</span></div></div>
        <p style="font-size:13px;color:var(--ink-2);margin-top:16px;line-height:1.55">
          Composite de trois systèmes tissulaires — <b style="color:var(--bone)">os</b>,
          <b style="color:var(--muscle)">muscle</b>, <b style="color:var(--metab)">métabolisme</b> — chacun replacé
          sur la trajectoire d'âge d'une population de référence.</p>
      </div>
      <div class="hero-right">
        <div class="eyebrow" style="margin-bottom:14px">Décomposition par système</div>
        <div class="subages">
          {sub("Métabolique", "graisse viscérale", b["metabolic"], "var(--metab)")}
          {sub("Osseux", "densité minérale", b["bone"], "var(--bone)")}
          {sub("Musculaire", "masse maigre", b["muscle"], "var(--muscle)")}
        </div>
        <p style="font-size:11.5px;color:var(--muted);margin-top:16px;line-height:1.5;font-family:var(--font-mono)">
          Échelle 20 → 40 ans. Indice éducatif pondéré ({int(b['weights']['metabolic']*100)}/{int(b['weights']['muscle']*100)}/{int(b['weights']['bone']*100)}),
          dérivé des mesures DXA. Ne remplace pas un avis médical.</p>
      </div>
    </div></div>
    {_scorecards(A)}
  </section>'''


def _apos(age):
    return max(2, min(98, (age - 20) / 20 * 100))


def _scorecards(A):
    s = A["snap"]; st = A["status"]
    cards = []
    if "vat" in st:
        cards.append(_scard("VG", "var(--metab)", "Graisse viscérale",
                            f'{fr(s.get("vat_mass_g"),0)} <span style="font-size:13px;color:var(--muted)">g</span>',
                            f'{fr(s.get("vat_area_cm2"))} cm² · seuil ≈ {int(A["vat_mass_thr"])} g', st["vat"]))
    if "muscle" in st:
        cards.append(_scard("MM", "var(--muscle)", "Masse musculaire",
                            f'{fr(s.get("almi"),2)} <span style="font-size:13px;color:var(--muted)">kg/m²</span>',
                            "ALMI · appendiculaire", st["muscle"]))
    if "bone" in st:
        basis = A.get("bmd_basis", "T")
        val = s.get("bmd_z") if basis == "Z" else s.get("bmd_t")
        cards.append(_scard("OS", "var(--bone)", "Densité osseuse",
                            f'{fr(val, 1)} <span style="font-size:13px;color:var(--muted)">{basis}</span>',
                            f'corps entier · non diagnostique', st["bone"]))
    if "bf" in st:
        cards.append(_scard("%G", "var(--brand)", "Masse grasse",
                            f'{fr(s.get("bf_pct"))} <span style="font-size:13px;color:var(--muted)">%</span>',
                            f'{fr(s.get("fat_g",0)/1000 if s.get("fat_g") else None)} kg', st["bf"]))
    return f'<div class="score">{"".join(cards)}</div>'


def _scard(ic, color, title, big, cap, st):
    return f'''<div class="scard"><div class="top">
      <div class="ic" style="background:{color}">{ic}</div><h4>{title}</h4></div>
      <div class="big">{big}</div><div class="cap">{cap}</div>{_status_pill(st)}</div>'''


def _composition(A, img_skeletal, img_thermal):
    m = A.get("mass")
    if not m:
        return ""
    imgs = ""
    if img_skeletal or img_thermal:
        figs = ""
        if img_skeletal:
            figs += f'<figure class="scan-fig"><img src="{img_skeletal}" alt="Squelette DXA"><figcaption>Carte osseuse</figcaption></figure>'
        if img_thermal:
            figs += f'<figure class="scan-fig"><img src="{img_thermal}" alt="Composition DXA"><figcaption>Graisse / maigre / os</figcaption></figure>'
        imgs = f'''<div class="card">
          <div class="eyebrow" style="margin-bottom:12px">Imagerie DXA — corps entier ({_date_fr(A["latest_exam_date"])})</div>
          <div class="scan-imgs">{figs}</div>
          <p style="font-size:11px;color:var(--muted);text-align:center;margin-top:10px;font-family:var(--font-mono)">
            Image non destinée à un usage diagnostique</p></div>'''

    meters = _meter("FFMI", "masse maigre / taille²",
                    f'{fr(A["ffmi"])} <small>kg/m²</small>', A["meters"]["ffmi"])
    if A["meters"]["fmi"]["value"] is not None:
        meters += _meter("FMI", "masse grasse / taille²",
                         f'{fr(A["snap"].get("fmi"))} <small>kg/m²</small>', A["meters"]["fmi"])

    grid_class = "g-scan" if imgs else "g-2"
    return f'''<section>
    <div class="sec-head"><span class="idx">02</span><h2>Composition en un coup d'œil</h2>
      <span class="note">{fr(m["total_kg"])} kg en trois compartiments — bien au-delà de l'IMC.</span></div>
    <div class="grid {grid_class}">{imgs}
      <div class="card">
        <div class="eyebrow" style="margin-bottom:12px">Masse totale — {fr(m["total_kg"])} kg</div>
        <div class="massbar">
          <div class="seg" style="width:{m["lean_pct"]:.1f}%;background:var(--muscle)">Masse maigre&nbsp;·&nbsp;{fr(m["lean_kg"])}&nbsp;kg</div>
          <div class="seg" style="width:{m["fat_pct"]:.1f}%;background:var(--metab)">{fr(m["fat_kg"])}</div>
          <div class="seg" style="width:{m["bmc_pct"]:.1f}%;background:var(--bone)"></div></div>
        <div class="masskey">
          <div class="item"><span class="sw" style="background:var(--muscle)"></span><span class="t">Masse maigre <b>{fr(m["lean_kg"])} kg</b> · {fr(m["lean_pct"])} %</span></div>
          <div class="item"><span class="sw" style="background:var(--metab)"></span><span class="t">Masse grasse <b>{fr(m["fat_kg"])} kg</b> · {fr(m["fat_pct"])} %</span></div>
          <div class="item"><span class="sw" style="background:var(--bone)"></span><span class="t">Os <b>{fr(m["bmc_kg"])} kg</b> · {fr(m["bmc_pct"])} %</span></div></div>
        <div style="height:1px;background:var(--hairline);margin:18px 0"></div>
        <div class="eyebrow" style="margin-bottom:10px">Indices normalisés (taille²)</div>
        {meters}
      </div></div></section>'''


def _muscle(A):
    mt = A["meters"]["almi"]
    s = A["snap"]
    legend = f'''<div class="legend">
      <span><i style="background:var(--ink)"></i>Vous · {fr(s.get("almi"),2)}</span>
      <span><i style="background:var(--ink-2)"></i>Médiane · {fr(mt.get("ref_val", None) if False else None)}</span></div>'''
    # legend simple
    legend = ('<div class="legend"><span><i style="background:var(--ink)"></i>Vous</span>'
              '<span><i style="background:var(--ink-2)"></i>Médiane de référence</span></div>')
    rl = s.get("regional_lean", {})
    bars = ""
    if rl:
        mx = max([v for v in rl.values()] + [1])
        asym = A.get("arm_asym")
        order = [("bras_d", "Bras droit"), ("bras_g", "Bras gauche"),
                 ("jambe_d", "Jambe droite"), ("jambe_g", "Jambe gauche"), ("tronc", "Tronc")]
        for key, lbl in order:
            if key in rl:
                v = rl[key]
                dim = bool(asym and asym["flag"] and key == ("bras_g" if asym["bigger"] == "droit" else "bras_d"))
                bars += _rbar(lbl, v / mx * 100, f'{fr(v/1000,2)} kg', dim=dim)
    note = ""
    asym = A.get("arm_asym")
    if asym and asym["flag"]:
        note = (f'<div class="tag-note"><span>⚠</span><div><b>Asymétrie bras {fr(asym["pct"])} %</b> '
                f'({asym["bigger"]} &gt; controlatéral). À corriger par du travail unilatéral.</div></div>')
    elif asym:
        note = ('<div class="tag-note good"><span>✓</span><div><b>Symétrie excellente</b> — '
                'écart bras &lt; 10 %. Le travail peut être bilatéral et global.</div></div>')
    interp = ("À la médiane de référence : marge de progression nette (sécurité, force, os)."
              if (s.get("almi") and s["almi"] < R_median(A))
              else "Au-dessus de la médiane — bon niveau musculaire à entretenir.")
    return f'''<section>
    <div class="sec-head"><span class="idx">03</span><h2 style="color:var(--muscle)">Muscle — masse maigre</h2>
      <span class="note">Le compartiment le plus lié à la longévité fonctionnelle.</span></div>
    <div class="grid g-2">
      <div class="card"><div class="eyebrow" style="margin-bottom:14px">Position vs jeunes adultes (même sexe)</div>
        {_meter("ALMI", "maigre appendiculaire / taille²", f'{fr(s.get("almi"),2)} <small>kg/m²</small>', mt, legend)}
        <p style="font-size:13px;color:var(--ink-2);margin-top:14px;line-height:1.55">{interp}</p></div>
      <div class="card"><div class="eyebrow" style="margin-bottom:14px">Masse maigre par région (kg)</div>
        {bars}{note}</div></div></section>'''


def R_median(A):
    from . import references as R
    return R.ANCHORS[A["demo"]["sex"]]["almi_median"]


def _fat(A):
    s = A["snap"]
    ratio = A.get("vat_ref_txt", "")
    thr_mass = int(A["vat_mass_thr"])
    ag = s.get("ag_ratio")
    tl = s.get("trunk_limb_mass")
    return f'''<section>
    <div class="sec-head"><span class="idx">04</span><h2 style="color:var(--metab)">Graisse &amp; risque cardiométabolique</h2>
      <span class="note">Ce n'est pas la quantité de graisse qui compte, mais surtout sa localisation.</span></div>
    <div class="grid g-2">
      <div class="card"><div class="eyebrow" style="margin-bottom:14px">Masse grasse totale — plages de santé</div>
        {_meter("% masse grasse", "", f'{fr(s.get("bf_pct"))} <small>%</small>', A["meters"]["bf"])}
      </div>
      <div class="card"><div class="eyebrow" style="margin-bottom:14px">Graisse viscérale (TAV) — le marqueur qui compte</div>
        <div class="callout"><div class="cn">{fr(s.get("vat_mass_g"),0)}<small>grammes de TAV</small></div>
          <div class="cc">Soit <b>{ratio} sous le seuil de risque</b> ({thr_mass} g). Surface estimée <b>{fr(s.get("vat_area_cm2"))} cm²</b>.</div></div>
        <div style="margin-top:18px">{_meter("TAV sur l'échelle de risque", "", f'{fr(s.get("vat_area_cm2"))} <small>cm²</small>', A["meters"]["vat_area"])}</div>
        <div style="display:flex;gap:10px;margin-top:16px;flex-wrap:wrap">
          <div style="flex:1;min-width:120px;background:var(--surface-2);border:1px solid var(--hairline);border-radius:9px;padding:11px">
            <div class="eyebrow">Ratio A/G</div><div class="num" style="font-size:19px;font-weight:700;margin-top:3px">{fr(ag,2)}</div>
            <div style="font-size:11px;color:var(--muted)">androïde/gynoïde</div></div>
          <div style="flex:1;min-width:120px;background:var(--surface-2);border:1px solid var(--hairline);border-radius:9px;padding:11px">
            <div class="eyebrow">Tronc / membres</div><div class="num" style="font-size:19px;font-weight:700;margin-top:3px">{fr(tl,2)}</div>
            <div style="font-size:11px;color:var(--muted)">distribution</div></div></div></div></div></section>'''


def _bone(A):
    s = A["snap"]
    t = s.get("bmd_t")
    above = t is not None and t >= 0.3
    rb = s.get("regional_bmd", {})
    prev_rb = A.get("regional_bmd_prev") or {}
    bars = ""
    if rb:
        mx = max([v for v in rb.values()] + [1])
        order = [("bassin", "Bassin"), ("jambe_g", "Jambes"), ("rachis_lomb", "Rachis L."), ("bras_g", "Bras")]
        seen = set()
        for key, lbl in order:
            if key in rb and lbl not in seen:
                val = f'{fr(rb[key],3)} g/cm²'
                if key in prev_rb:
                    dv = round(rb[key] - prev_rb[key], 3)
                    col = "var(--good)" if dv > 0 else ("var(--warn)" if dv < 0 else "var(--muted)")
                    val += (f' <span style="color:{col};font-size:10.5px;font-family:var(--font-mono)">'
                            f'{"+" if dv>=0 else ""}{fr(dv,3)}</span>')
                bars += _rbar_bone(lbl, rb[key] / mx * 100, val)
                seen.add(lbl)
    # panneau droit : tendance si historique, sinon "point de départ"
    trend = A["trends"]["bmd"]
    if len(trend) > 1:
        first, last = trend[0], trend[-1]
        change = round(last["value"] - first["value"], 3)
        sig = abs(change) >= 0.014
        right = f'''<div class="callout" style="background:var(--good-bg);border-color:transparent">
          <div class="cn" style="color:var(--good)">{"+" if change>=0 else ""}{fr(change,3)}<small>g/cm² depuis {trend[0]["date"].year}</small></div>
          <div class="cc" style="color:var(--ink-2)">{"Gain <b style='color:var(--good)'>significatif</b> (> seuil 0,014)." if sig else "Variation dans le bruit de mesure."} T-score {fr(first["t"])} → {fr(last["t"])}.</div></div>'''
    else:
        z = s.get("bmd_z")
        right = f'''<div class="callout" style="background:var(--good-bg);border-color:transparent">
          <div class="cn" style="color:var(--good)">Z {fr(z) if z is not None else "—"}<small>vs même âge/sexe</small></div>
          <div class="cc" style="color:var(--ink-2)">Point de départ {"<b style='color:var(--good)'>excellent</b>" if above else "établi"}. À maintenir via charges et impacts ; première tendance au prochain scan.</div></div>'''
    basis = A.get("bmd_basis", "T")
    z = s.get("bmd_z")
    if basis == "Z":
        if z is not None and z <= -2.0:
            interp = "densité <b style='color:var(--warn)'>sous la fourchette attendue pour l'âge</b> (Z ≤ −2,0)."
        else:
            interp = "densité <b style='color:var(--good)'>dans la fourchette attendue pour l'âge</b> (Z-score)."
        basis_note = ("À cet âge/sexe, c'est le <b>Z-score</b> (vs même âge) qui fait foi — "
                      "les termes « ostéopénie / ostéoporose » ne s'appliquent pas.")
    else:
        interp = ("densité osseuse <b style='color:var(--good)'>au-dessus</b> de la moyenne du jeune adulte."
                  if above else "densité osseuse <b>normale</b> (T &gt; −1,0).")
        basis_note = "Chez la femme ménopausée / l'homme ≥ 50 ans, le <b>T-score</b> classe selon l'OMS."
    return f'''<section>
    <div class="sec-head"><span class="idx">05</span><h2 style="color:var(--bone)">Os — densité minérale</h2>
      <span class="note">Indicateur global. Le diagnostic OMS repose sur des sites dédiés (§ ci-dessous).</span></div>
    <div class="grid g-2">
      <div class="card"><div class="eyebrow" style="margin-bottom:14px">DMO corps entier — indicateur, non diagnostique</div>
        {_meter("DMO totale", "", f'{fr(s.get("bmd_total"),3)} <small>g/cm² · T {fr(t)} · Z {fr(z)}</small>', A["meters"]["bmd"])}
        <p style="font-size:13px;color:var(--ink-2);margin-top:14px;line-height:1.55">T-score <b>{fr(t)}</b>, Z-score <b>{fr(z)}</b> : {interp}</p>
        <div class="tag-note"><span>ⓘ</span><div>Le DXA <b>corps entier</b> n'est pas l'outil de diagnostic de l'ostéoporose.
          {basis_note} Diagnostic fiable = <b>rachis AP (L1–L4) + col fémoral + hanche totale</b>, sur le site le plus bas.</div></div></div>
      <div class="card"><div class="eyebrow" style="margin-bottom:14px">Densité par région (g/cm²)</div>
        {right}<div style="margin-top:18px">{bars}</div>
        <p style="font-size:11px;color:var(--muted);margin-top:12px;line-height:1.5">
          Sous-régions du scan corps entier (sans T/Z) — <b>non diagnostiques</b> (ROI et base de référence
          différentes du rachis AP / hanche dédiés ; le bassin n'est pas un site reconnu). En revanche, le
          <b>Δ vs examen précédent</b> (même machine, même méthode) est une comparaison valide pour le suivi.</p></div></div></section>'''


def _trends_section(A):
    tr = A["trends"]
    if A["has_history"] and tr["bf"] and tr["lean"] and tr["bmd"]:
        c1 = _line_svg(tr["bf"], "var(--metab)", "Tendance masse grasse")
        c2 = _line_svg(tr["lean"], "var(--muscle)", "Tendance masse maigre")
        c3 = _line_svg(tr["bmd"], "var(--bone)", "Tendance densité osseuse")
        bf0, bf1 = tr["bf"][0]["value"], tr["bf"][-1]["value"]
        return f'''<section data-mod="trends">
      <div class="sec-head"><span class="idx">06</span><h2>Évolution dans le temps</h2>
        <span class="note">{A["n_exams"]} examens — la vraie valeur d'un suivi DXA est la trajectoire.</span></div>
      <div class="card"><div class="trend-grid">
        <div class="trend"><h4>Masse grasse</h4><div class="cap">% du corps</div>{c1}
          <div class="delta2 down">▼ {fr(bf0-bf1)} pts · {fr(bf0)} → {fr(bf1)} %</div></div>
        <div class="trend"><h4>Masse maigre</h4><div class="cap">kg</div>{c2}
          <div class="delta2 flat">préservée pendant la perte de gras</div></div>
        <div class="trend"><h4>Densité osseuse</h4><div class="cap">g/cm²</div>{c3}
          <div class="delta2 up">▲ {fr(tr["bmd"][-1]["value"]-tr["bmd"][0]["value"],3)}</div></div>
      </div></div></section>'''
    # baseline
    s = A["snap"]
    return f'''<section data-mod="trends">
    <div class="sec-head"><span class="idx">06</span><h2>Point de départ (baseline)</h2>
      <span class="note">Premier examen : les tendances apparaîtront dès le 2ᵉ scan.</span></div>
    <div class="card">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
        <div style="width:34px;height:34px;border-radius:9px;background:var(--brand-bg);color:var(--brand);display:grid;place-items:center;font-size:18px">◷</div>
        <p style="font-size:14px;color:var(--ink-2);margin:0">Ce <b>premier DXA</b> devient la <b>référence personnelle</b> à laquelle les prochains examens seront comparés.</p></div>
      <div class="grid g-4">
        <div style="background:var(--surface-2);border:1px solid var(--hairline);border-radius:11px;padding:14px"><div class="eyebrow">Masse grasse</div><div class="num" style="font-size:24px;font-weight:700;margin-top:4px;color:var(--metab)">{fr(s.get("bf_pct"))} %</div></div>
        <div style="background:var(--surface-2);border:1px solid var(--hairline);border-radius:11px;padding:14px"><div class="eyebrow">Masse maigre</div><div class="num" style="font-size:24px;font-weight:700;margin-top:4px;color:var(--muscle)">{fr(s.get("lean_g",0)/1000 if s.get("lean_g") else None)} kg</div></div>
        <div style="background:var(--surface-2);border:1px solid var(--hairline);border-radius:11px;padding:14px"><div class="eyebrow">Densité osseuse</div><div class="num" style="font-size:24px;font-weight:700;margin-top:4px;color:var(--bone)">{fr(s.get("bmd_total"),3)}</div></div>
        <div style="background:var(--surface-2);border:1px solid var(--hairline);border-radius:11px;padding:14px"><div class="eyebrow">Graisse viscérale</div><div class="num" style="font-size:24px;font-weight:700;margin-top:4px;color:var(--brand)">{fr(s.get("vat_mass_g"),0)} g</div></div>
      </div></div></section>'''


def _interp_section(A):
    it = A["interp"]
    acts = ""
    for i, (h, p, pri) in enumerate(it["actions"], 1):
        acts += f'''<div class="act"><div class="rank">{i}</div><div>
          <h4>{esc(h)}</h4><p>{esc(p)}</p><span class="pri">{esc(pri)}</span></div></div>'''
    return f'''<section>
    <div class="sec-head"><span class="idx">07</span><h2>Interprétation &amp; plan d'action</h2>
      <span class="note">Traduire les chiffres en décisions.</span></div>
    <div class="interp"><div class="readbox">
      <p class="lead">{esc(it["lead"])}</p><p>{esc(it["para"])}</p></div>
      <div class="actions">{acts}</div></div></section>'''


def _method(A):
    b = A["bioage"]; d = A["demo"]
    w = b["weights"]
    refs_sex = "femme blanche" if d["sex"] == "F" else "homme blanc"
    return f'''<section>
    <div class="sec-head"><span class="idx">08</span><h2>Méthode, références &amp; limites</h2></div>
    <div class="grid g-2">
      <div class="card method"><h4 style="margin-top:0">Comment est calculé l'âge biologique DXA</h4>
        <p>Chaque système est replacé sur la trajectoire d'âge d'une population de référence, puis converti en âge équivalent. Composite pondéré :</p>
        <div class="formula">Âge_bio = {w['metabolic']:.2f}·Âge<sub>métab</sub> + {w['muscle']:.2f}·Âge<sub>muscle</sub> + {w['bone']:.2f}·Âge<sub>os</sub><br>
          = {w['metabolic']:.2f}·({b['metabolic']}) + {w['muscle']:.2f}·({b['muscle']}) + {w['bone']:.2f}·({b['bone']})<br>
          ≈ {b['composite']} ans &nbsp;(vs {d['age']} civil)</div>
        <h4>Sources des populations de référence</h4>
        <p>Natif Hologic : NHANES/BMDCS 2012 ({refs_sex}). Enrichi : Pratt 2025 (valeurs DXA par âge),
          Meredith-Jones 2021 (seuils TAV), Radecka 2025 / Yamada 2021 (ALMI), Hew-Butler 2025 (% masse grasse athlète).</p>
        <h4>Sources — besoins nutritionnels</h4>
        <p><b>BMR</b> Cunningham 1991 (500 + 22·masse maigre). <b>DEJ</b> = BMR × facteur d'activité (PAL, Harris-Benedict).
          <b>Calories</b> déficit −20 % / surplus +10 %. <b>Protéines</b> Morton 2018 (1,6–2,2 g/kg) ; Helms 2014
          (2,3–3,1 g/kg de masse maigre en sèche). <b>Lipides</b> 30–40 % des kcal selon la pratique (min hormonal ~0,6 g/kg).
          <b>Répartition/repas</b> ~0,4 g protéines/kg/prise (Moore 2015 ; Schoenfeld &amp; Aragon 2018). Énergie 4/4/9 (Atwater).</p>
      </div>
      <div class="card method"><h4 style="margin-top:0">Références scientifiques</h4>
        <ol class="refs">
          <li>Lian et al. <a href="https://consensus.app/papers/details/71eb54ae63975314a60c657f8a00fdef/">Deep-learning body-composition ageing biomarker (DXA)</a>. <i>Comm. Medicine</i>, 2025.</li>
          <li>Fermín-Martínez et al. <a href="https://consensus.app/papers/details/9a3bf2c8337e56ef8776aa165ff70c0e/">AnthropoAge</a>. <i>Aging Cell</i>, 2021.</li>
          <li>Pratt et al. <a href="https://consensus.app/papers/details/0377acb63ed154798153e56d92631aa5/">Valeurs de référence DXA (âge adulte)</a>. <i>Clin. Nutrition</i>, 2025.</li>
          <li>Meredith-Jones et al. <a href="https://consensus.app/papers/details/59d49981d6295acf86622a334f853972/">Seuils de graisse viscérale</a>. <i>Int. J. Obesity</i>, 2021.</li>
          <li>Radecka et al. <a href="https://consensus.app/papers/details/d0d1468b4a455df4adc33803cf731259/">Normes ALMI/FFMI (Hologic)</a>. <i>Aging</i>, 2025.</li>
          <li>Hew-Butler et al. <a href="https://consensus.app/papers/details/1169ecbb7dcd5936b80916645d06bf58/">Plancher de masse grasse (athlète)</a>. <i>J. Clin. Densitometry</i>, 2025.</li>
        </ol></div></div>
    <p class="disclaimer"><b>Avertissement.</b> L'« âge biologique DXA » est un indice pédagogique dérivé des mesures de
      composition corporelle et de populations de référence publiées ; ce n'est pas un diagnostic médical ni un biomarqueur
      validé cliniquement. Les images DXA ne sont pas destinées à un usage diagnostique. Toute interprétation clinique relève
      d'un professionnel de santé. Données : export Hologic Horizon Wi / APEX. Rapport généré automatiquement.</p>
    <div class="foot"><span>{esc(R.CLINIC_FOOTER)}</span>
      <span>Rapport 2.0 · moteur v{R.VERSION} ({R.VERSION_DATE})</span></div></section>'''


def _coach_panel(A):
    """Panneau de configuration coach — écran seulement, masqué au PDF."""
    has_nut = bool(A.get("metabolism"))
    has_proj = bool(A["snap"].get("bf_pct") and A["snap"].get("lean_g"))
    has_since = bool(A.get("since_last"))
    mods = [("bioage", "Âge biologique", True), ("since", "Depuis la dernière fois", has_since),
            ("metabolism", "Métabolisme (BMR)", has_nut),
            ("nutrition", "Besoins nutritionnels", has_nut), ("meals", "Répartition des repas", has_nut),
            ("projector", "Projecteur d'objectif", has_proj), ("trends", "Évolution / tendances", True)]
    checks = ""
    for key, lab, on in mods:
        dis = "" if on else " disabled"
        chk = " checked" if on else ""
        checks += (f'<label class="cp-check"><input type="checkbox" data-toggle="{key}"{chk}{dis}>'
                   f'{esc(lab)}</label>')
    if not has_nut:
        nut_controls = ""
    else:
        acts = "".join(f'<option value="{k}"{" selected" if k == R.ACTIVITY_DEFAULT else ""}>{esc(lab)}</option>'
                       for k, lab, _ in R.ACTIVITY)
        goals = "".join(f'<option value="{k}"{" selected" if k == R.GOAL_DEFAULT else ""}>{esc(lab)}</option>'
                        for k, lab, _ in R.GOALS)
        trainings = "".join(f'<option value="{k}"{" selected" if k == R.TRAINING_DEFAULT else ""}>{esc(lab)} ({pct}% lip.)</option>'
                            for k, lab, pct in R.TRAINING)
        nut_controls = f'''
      <div class="cp-group"><label>Objectif</label>
        <select class="cp-select" id="nut-goal">{goals}</select></div>
      <div class="cp-group"><label>Niveau d'activité</label>
        <select class="cp-select" id="nut-activity">{acts}</select></div>
      <div class="cp-group"><label>Pratique sportive (ratio lip./gluc.)</label>
        <select class="cp-select" id="nut-training">{trainings}</select></div>
      <div class="cp-group"><label>Repas / jour</label>
        <select class="cp-select" id="nut-meals"><option value="3">3 repas</option>
          <option value="4" selected>4 repas</option><option value="5">5 repas</option></select></div>
      <div class="cp-group"><label>Forcer macros (g) — vide = auto</label>
        <div class="dxin"><input class="ov-in" type="number" min="0" step="1" id="ov-prot" placeholder="P">
          <input class="ov-in" type="number" min="0" step="1" id="ov-carb" placeholder="G">
          <input class="ov-in" type="number" min="0" step="1" id="ov-fat" placeholder="L"></div></div>'''
    proj_controls = ""
    if has_proj:
        proj_controls = '''
      <div class="cp-group"><label>Cible % gras</label>
        <input class="cp-select" type="number" step="0.5" id="proj-bf" style="min-width:100px"></div>
      <div class="cp-group"><label>Cible masse maigre (kg)</label>
        <input class="cp-select" type="number" step="0.5" id="proj-lean" style="min-width:120px"></div>'''
    # diagnostic osseux — sites dédiés (saisie manuelle depuis un scan rachis+hanche)
    meno = ""
    if A["demo"]["sex"] == "F":
        post = " selected" if A["demo"]["age"] >= 51 else ""
        pre = " selected" if A["demo"]["age"] < 51 else ""
        meno = (f'<div class="dxsite"><span>Statut</span><select id="dx-meno" class="dxsel">'
                f'<option value="post"{post}>Post-méno</option><option value="pre"{pre}>Préméno</option></select></div>')
    bonedx = f'''<div class="cp-group" style="flex-basis:100%">
      <label>Diagnostic osseux — scan dédié rachis + hanche (T-score ; Z si &lt;50 ou préménopause)</label>
      <div class="dxrow">
        <div class="dxsite"><span>Rachis L1–L4</span><div class="dxin"><input type="number" step="0.1" id="dx-spine-t" placeholder="T"><input type="number" step="0.1" id="dx-spine-z" placeholder="Z"></div></div>
        <div class="dxsite"><span>Col fémoral</span><div class="dxin"><input type="number" step="0.1" id="dx-neck-t" placeholder="T"><input type="number" step="0.1" id="dx-neck-z" placeholder="Z"></div></div>
        <div class="dxsite"><span>Hanche totale</span><div class="dxin"><input type="number" step="0.1" id="dx-hip-t" placeholder="T"><input type="number" step="0.1" id="dx-hip-z" placeholder="Z"></div></div>
        {meno}
      </div></div>'''
    return f'''<div class="coach-panel no-print">
    <span class="cp-tag">Panneau coach — n'apparaît pas dans le PDF</span>
    <h3>Personnaliser le rapport selon le client</h3>
    <div class="cp-row">
      <div class="cp-group"><label>Sections à inclure</label>
        <div class="cp-checks">{checks}</div></div>
      {nut_controls}{proj_controls}
      <button class="cp-export" onclick="window.print()">🖨 Exporter en PDF</button>
    </div>
    <div class="cp-row" style="margin-top:14px">{bonedx}</div>
    <div class="cp-hint">Cochez/décochez les sections, ajustez l'objectif, saisissez le scan osseux dédié si disponible, puis « Exporter en PDF » : le PDF ne contiendra que ce qui est affiché.</div>
  </div>'''


def _metabolism(A):
    mb = A["metabolism"]; nu = A["nutrition"]
    return f'''<section data-mod="metabolism">
    <div class="sec-head"><span class="idx">·</span><h2>Métabolisme de base</h2>
      <span class="note">Estimé par la formule de Cunningham (1991) à partir de la masse maigre mesurée.</span></div>
    <div class="card">
      <div class="kpi-row">
        <div class="kpi"><div class="kpi-lab">Masse maigre (FFM)</div>
          <div class="kpi-val">{fr(mb["ffm_kg"])} <small>kg</small></div>
          <div class="kpi-sub">mesurée au DXA</div></div>
        <div class="kpi"><div class="kpi-lab">Métabolisme de base</div>
          <div class="kpi-val" style="color:var(--metab)">{mb["bmr"]} <small>kcal/j</small></div>
          <div class="kpi-sub">au repos (BMR)</div></div>
        <div class="kpi"><div class="kpi-lab">Dépense énergétique</div>
          <div class="kpi-val" style="color:var(--brand)"><span id="tdee">{nu["tdee"]}</span> <small>kcal/j</small></div>
          <div class="kpi-sub" id="tdee-sub">BMR × activité (modéré)</div></div>
        <div class="kpi"><div class="kpi-lab">Formule</div>
          <div class="kpi-val" style="font-size:16px">500 + 22×FFM</div>
          <div class="kpi-sub">Cunningham 1991</div></div>
      </div>
      <p style="font-size:12.5px;color:var(--ink-2);margin-top:14px;line-height:1.55">
        Le DXA mesure directement la masse maigre — le tissu qui consomme l'énergie — ce qui rend l'estimation du
        métabolisme <b>bien plus précise</b> que les formules basées sur le poids seul (Harris-Benedict, Mifflin).</p>
    </div></section>'''


def _nutrition(A):
    nu = A["nutrition"]
    return f'''<section data-mod="nutrition">
    <div class="sec-head"><span class="idx">·</span><h2>Besoins nutritionnels</h2>
      <span class="note">Cible calorique et macros selon l'objectif — modifiables dans le panneau coach.</span></div>
    <div class="card">
      <div class="kpi-row" style="grid-template-columns:1.1fr 1fr 1fr 1fr">
        <div class="kpi"><div class="kpi-lab">Cible calorique <span id="nut-goal-lab">(maintien)</span></div>
          <div class="kpi-val" style="color:var(--brand)"><span id="kcal-target">{nu["kcal"]}</span> <small>kcal/j</small></div>
          <div class="kpi-sub" id="kcal-sub">= dépense énergétique</div></div>
        <div class="kpi"><div class="kpi-lab">Protéines</div>
          <div class="kpi-val" style="color:var(--muscle)"><span id="m-prot">{nu["protein"]}</span> <small>g</small></div>
          <div class="kpi-sub"><span id="m-prot-kg">{fr(nu["p_per_kg"])}</span> g/kg {"FFM" if R.PROTEIN_BASIS == "ffm" else "poids"} · <span id="m-prot-kcal">{nu["kcal_p"]}</span> kcal</div></div>
        <div class="kpi"><div class="kpi-lab">Glucides</div>
          <div class="kpi-val" style="color:var(--metab)"><span id="m-carb">{nu["carbs"]}</span> <small>g</small></div>
          <div class="kpi-sub"><span id="m-carb-kcal">{nu["kcal_c"]}</span> kcal</div></div>
        <div class="kpi"><div class="kpi-lab">Lipides</div>
          <div class="kpi-val" style="color:var(--warn)"><span id="m-fat">{nu["fat"]}</span> <small>g</small></div>
          <div class="kpi-sub"><span id="m-fat-kcal">{nu["kcal_f"]}</span> kcal</div></div>
      </div>
      <div class="macrobar" id="macrobar" style="margin-top:16px"></div>
      <div class="macrokey">
        <div class="mk"><span class="msw" style="background:var(--muscle)"></span>Protéines <b id="pct-prot"></b></div>
        <div class="mk"><span class="msw" style="background:var(--metab)"></span>Glucides <b id="pct-carb"></b></div>
        <div class="mk"><span class="msw" style="background:var(--warn)"></span>Lipides <b id="pct-fat"></b></div>
      </div>
      <p id="fat-note" style="font-size:11.5px;color:var(--muted);margin-top:10px;font-family:var(--font-mono)"></p>
    </div></section>'''


def _meals(A):
    return f'''<section data-mod="meals">
    <div class="sec-head"><span class="idx">·</span><h2>Répartition des repas</h2>
      <span class="note">Protéines réparties pour maximiser la synthèse musculaire (~0,4 g/kg/prise).</span></div>
    <div class="card">
      <div class="meals-grid" id="meals-container"></div>
      <div id="mps-note" style="margin-top:14px"></div>
    </div></section>'''


def _bone_dx(A):
    """Bloc diagnostic osseux sur sites dédiés — masqué tant qu'aucune valeur saisie (JS)."""
    return '''<section data-mod="bonedx" class="hidden" id="bonedx-block">
    <div class="sec-head"><span class="idx">·</span><h2 style="color:var(--bone)">Diagnostic osseux — sites dédiés</h2>
      <span class="note">Rachis AP + hanche · classification sur le site le plus bas (ISCD/OMS).</span></div>
    <div class="card">
      <div id="bonedx-verdict" style="display:flex;align-items:center;flex-wrap:wrap;margin-bottom:8px"></div>
      <div id="bonedx-rows"></div>
      <p style="font-size:11.5px;color:var(--muted);margin-top:12px;line-height:1.5">
        T-score (femme ménopausée / homme ≥ 50 ans) : ostéoporose ≤ −2,5 · ostéopénie −1 à −2,5 · normal &gt; −1.
        Sinon Z-score : « sous la fourchette attendue pour l'âge » si ≤ −2,0. Diagnostic clinique réservé au médecin.</p>
    </div></section>'''


def _since(A):
    s = A.get("since_last")
    if not s:
        return ""
    arrows = {"up": "▲", "down": "▼", "flat": "■"}
    rows_html = ""
    goods, warns = [], []
    for r in s["rows"]:
        sign = "+" if r["delta"] > 0 else ""
        dtxt = f'{sign}{fr(r["delta"], r["dec"])} {r["unit"]}'
        sig = '<span class="since-sig">significatif</span>' if r.get("sig") else ""
        rows_html += (f'<div class="since-row"><span class="sl">{esc(r["label"])}</span>'
                      f'<span class="sv">{fr(r["prev"], r["dec"])} → {fr(r["curr"], r["dec"])} {esc(r["unit"])}</span>'
                      f'<span class="delta-chip {r["verdict"]}">{arrows[r["dir"]]} {dtxt}{sig}</span></div>')
        short = f'{r["label"].lower()} {dtxt}'
        if r["verdict"] == "good":
            goods.append(short)
        elif r["verdict"] == "warn":
            warns.append(short)
    lead = f'En {fr(s["months"])} mois'
    if goods:
        lead += " : " + ", ".join(goods)
    if warns:
        lead += (" — à surveiller : " if not goods else " ; à surveiller : ") + ", ".join(warns)
    if not goods and not warns:
        lead += " : composition globalement stable."
    else:
        lead += "."
    when = f'{_date_fr(s["prev_date"])} → {_date_fr(s["curr_date"])}'
    return f'''<section data-mod="since">
    <div class="sec-head"><span class="idx">·</span><h2>Depuis la dernière fois</h2>
      <span class="note">Ce qui a changé entre les deux derniers examens.</span></div>
    <div class="card">
      <div class="since-head"><p class="since-lead">{esc(lead)}</p><span class="since-when">{when}</span></div>
      <div class="since-grid">{rows_html}</div>
      <p style="font-size:11.5px;color:var(--muted);margin-top:12px;line-height:1.5">
        Le poids seul ne dit pas tout : le DXA distingue ce qui vient du <b>gras</b>, du <b>muscle</b> et de l'<b>os</b>.
        Seuil de variation significative de la densité osseuse : ±0,014 g/cm².</p>
    </div></section>'''


def _projector(A):
    return '''<section data-mod="projector">
    <div class="sec-head"><span class="idx">·</span><h2>Projecteur d'objectif</h2>
      <span class="note">Estimation à rythme constant — vitesse mesurée si un historique existe, sinon rythme type.</span></div>
    <div class="card">
      <div class="kpi-row" style="grid-template-columns:1fr 1fr">
        <div class="kpi"><div class="kpi-lab">Objectif masse grasse</div>
          <div class="kpi-val" style="color:var(--metab);font-size:20px"><span id="proj-fat-date">—</span></div>
          <div class="kpi-sub" id="proj-fat-cur">—</div>
          <div class="kpi-sub" id="proj-fat-rate" style="margin-top:4px;color:var(--muted)">—</div></div>
        <div class="kpi"><div class="kpi-lab">Objectif masse maigre</div>
          <div class="kpi-val" style="color:var(--muscle);font-size:20px"><span id="proj-lean-date">—</span></div>
          <div class="kpi-sub" id="proj-lean-cur">—</div>
          <div class="kpi-sub" id="proj-lean-rate" style="margin-top:4px;color:var(--muted)">—</div></div>
      </div>
      <p style="font-size:12px;color:var(--muted);margin-top:14px;line-height:1.5">
        Réglez les cibles dans le panneau coach. Projection indicative, à rythme constant ; la réalité dépend de
        l'assiduité, du sommeil et de la nutrition.</p>
    </div></section>'''


def _script(A):
    mb = A.get("metabolism")
    cfg = {
        "sex": A["demo"]["sex"], "age": A["demo"]["age"],
        "curBF": A["snap"].get("bf_pct"),
        "curLean": round(A["snap"]["lean_g"] / 1000, 1) if A["snap"].get("lean_g") else None,
        "velFat": A["velocity"]["fat_pct_per_month"], "velLean": A["velocity"]["lean_kg_per_month"],
        "defFatLoss": R.PROJ_FAT_LOSS_PCT_PER_MONTH, "defLeanGain": R.PROJ_LEAN_GAIN_KG_PER_MONTH,
        "bfFloor": R.ANCHORS[A["demo"]["sex"]]["bf_athletic"] - 3,
    }
    if mb:
        cfg.update({
            "weight": A["demo"]["weight_kg"], "bmr": mb["bmr"], "ffm": mb["ffm_kg"],
            "activity": {k: v for k, _, v in R.ACTIVITY},
            "activityLab": {k: lab for k, lab, _ in R.ACTIVITY},
            "goalAdj": {k: v for k, _, v in R.GOALS},
            "goalLab": {k: lab for k, lab, _ in R.GOALS},
            "proteinBasis": R.PROTEIN_BASIS,
            "protFFM": R.PROTEIN_G_PER_KG_FFM, "protBW": R.PROTEIN_G_PER_KG_BW,
            "mpsPerKg": R.PROTEIN_PER_MEAL_G_PER_KG,
            "trainingFat": {k: v for k, _, v in R.TRAINING},
        })
    return f'''<script>
const CFG = {_json.dumps(cfg)};
function $(id){{return document.getElementById(id);}}

function renumber(){{
  const secs = [...document.querySelectorAll('section')].filter(s => !s.classList.contains('hidden'));
  let n = 1;
  for (const s of secs){{
    const idx = s.querySelector('.sec-head .idx');
    if (idx){{ idx.textContent = String(n).padStart(2,'0'); n++; }}
  }}
}}

function _ovVal(id){{ const el=$(id); if(!el) return NaN; const v=parseFloat(el.value); return (!isNaN(v)&&v>0)?v:NaN; }}
function computeNutrition(){{
  if(!$('nut-goal')) return;
  const goal = $('nut-goal').value, act = $('nut-activity').value, meals = +$('nut-meals').value;
  const training = $('nut-training') ? $('nut-training').value : 'mixte';
  const tdee = Math.round(CFG.bmr * CFG.activity[act]);
  const kcalTarget = Math.round(tdee * (1 + CFG.goalAdj[goal]));
  const useFFM = (CFG.proteinBasis === 'ffm' && CFG.ffm);
  const base = useFFM ? CFG.ffm : CFG.weight;
  // surcharges manuelles (grammes forcés) sinon calcul
  const ovP=_ovVal('ov-prot'), ovC=_ovVal('ov-carb'), ovF=_ovVal('ov-fat');
  const protein = !isNaN(ovP) ? Math.round(ovP) : Math.round(base * (useFFM?CFG.protFFM[goal]:CFG.protBW[goal]));
  const fatPct = CFG.trainingFat[training] || 35;
  const fat = !isNaN(ovF) ? Math.round(ovF) : Math.round(kcalTarget * fatPct/100/9);
  const carbs = !isNaN(ovC) ? Math.round(ovC) : Math.max(0, Math.round((kcalTarget - protein*4 - fat*9)/4));
  const kp = protein*4, kc = carbs*4, kf = fat*9, kcal = kp+kc+kf, tot = Math.max(1, kcal);
  const forced = (!isNaN(ovP)||!isNaN(ovC)||!isNaN(ovF));
  if($('tdee')) $('tdee').textContent = tdee;
  if($('tdee-sub')) $('tdee-sub').textContent = 'BMR × activité (' + CFG.activityLab[act].split(' ')[0].toLowerCase() + ')';
  if($('kcal-target')){{
    $('kcal-target').textContent = kcal;
    $('nut-goal-lab').textContent = '(' + CFG.goalLab[goal].split(' ')[0].toLowerCase() + (forced?', forcé':'') + ')';
    const diff = kcal - tdee;
    $('kcal-sub').textContent = (diff===0?'= dépense énergétique':(diff>0?'+':'')+diff+' kcal vs dépense');
    const perKg = (protein/base);
    $('m-prot').textContent = protein; $('m-prot-kg').textContent = perKg.toFixed(1).replace('.',',');
    $('m-prot-kcal').textContent = kp;
    $('m-carb').textContent = carbs; $('m-carb-kcal').textContent = kc;
    $('m-fat').textContent = fat; $('m-fat-kcal').textContent = kf;
    const pp=Math.round(kp/tot*100), pc=Math.round(kc/tot*100), pf=100-pp-pc;
    $('macrobar').innerHTML =
      '<div class="mseg" style="width:'+pp+'%;background:var(--muscle)">P '+pp+'%</div>'+
      '<div class="mseg" style="width:'+pc+'%;background:var(--metab)">G '+pc+'%</div>'+
      '<div class="mseg" style="width:'+pf+'%;background:var(--warn)">L '+pf+'%</div>';
    $('pct-prot').textContent = protein+' g'; $('pct-carb').textContent = carbs+' g'; $('pct-fat').textContent = fat+' g';
    if($('fat-note')){{
      const out = pf<30 || pf>40;
      $('fat-note').textContent = 'Lipides ≈ '+pf+' % des kcal' + (out ? ' — hors fourchette 30–40 % (surcharge)' : ' (cible '+fatPct+' % · '+training+')');
      $('fat-note').style.color = out ? 'var(--warn)' : 'var(--muted)';
    }}
  }}
  if($('meals-container')){{
    const perK = Math.round(kcal/meals), perP = Math.round(protein/meals);
    const mpsMin = Math.round(CFG.weight * CFG.mpsPerKg);
    let html='';
    for(let i=1;i<=meals;i++){{
      html += '<div class="meal"><div class="mn">Repas '+i+'</div>'+
        '<div class="mk2">'+perK+' <span style="font-size:12px;color:var(--muted)">kcal</span></div>'+
        '<div class="mp">Protéines <b>'+perP+' g</b></div></div>';
    }}
    $('meals-container').innerHTML = html;
    const ok = perP >= mpsMin;
    $('mps-note').innerHTML = '<div class="tag-note '+(ok?'good':'')+'"><span>'+(ok?'✓':'⚠')+'</span><div>'+
      (ok
        ? '<b>'+perP+' g de protéines par repas</b> — au-dessus du seuil de ~'+mpsMin+' g ('+CFG.mpsPerKg.toString().replace('.',',')+' g/kg) qui maximise la synthèse musculaire à chaque prise.'
        : '<b>'+perP+' g par repas</b> est sous le seuil optimal de ~'+mpsMin+' g. Regroupez sur moins de repas ou augmentez l\\'apport pour mieux stimuler le muscle.')+
      '</div></div>';
  }}
}}

function fmtDate(d){{
  return d.toLocaleDateString('fr-CH', {{month:'long', year:'numeric'}});
}}
function computeProjector(){{
  if(!$('proj-fat-date')) return;
  const today = new Date();
  // masse grasse
  const tBf = parseFloat($('proj-bf').value);
  const cBf = CFG.curBF;
  const fatLine = $('proj-fat-rate'), fatDate = $('proj-fat-date'), fatCur = $('proj-fat-cur');
  fatCur.textContent = (cBf!=null?cBf.toString().replace('.',','):'—') + ' % → ' + (isNaN(tBf)?'—':tBf.toString().replace('.',',')) + ' %';
  if(cBf!=null && !isNaN(tBf) && tBf < cBf){{
    const measured = (CFG.velFat!=null && CFG.velFat < -0.05);
    const rate = measured ? -CFG.velFat : CFG.defFatLoss;
    const months = (cBf - tBf) / rate;
    const d = new Date(today); d.setMonth(d.getMonth()+Math.round(months));
    fatDate.textContent = fmtDate(d);
    fatLine.textContent = '≈ ' + months.toFixed(1).replace('.',',') + ' mois · ' + rate.toFixed(1).replace('.',',') + ' %/mois (' + (measured?'mesurée':'estimée') + ')';
  }} else {{
    fatDate.textContent = cBf!=null && !isNaN(tBf) && tBf>=cBf ? 'cible atteinte' : '—';
    fatLine.textContent = 'définir une cible inférieure à l\\'actuel';
  }}
  // masse maigre
  const tLean = parseFloat($('proj-lean').value);
  const cLean = CFG.curLean;
  const leanLine = $('proj-lean-rate'), leanDate = $('proj-lean-date'), leanCur = $('proj-lean-cur');
  leanCur.textContent = (cLean!=null?cLean.toString().replace('.',','):'—') + ' kg → ' + (isNaN(tLean)?'—':tLean.toString().replace('.',',')) + ' kg';
  if(cLean!=null && !isNaN(tLean) && tLean > cLean){{
    const measured = (CFG.velLean!=null && CFG.velLean > 0.02);
    const rate = measured ? CFG.velLean : CFG.defLeanGain;
    const months = (tLean - cLean) / rate;
    const d = new Date(today); d.setMonth(d.getMonth()+Math.round(months));
    leanDate.textContent = fmtDate(d);
    leanLine.textContent = '≈ ' + months.toFixed(1).replace('.',',') + ' mois · +' + rate.toFixed(2).replace('.',',') + ' kg/mois (' + (measured?'mesurée':'estimée') + ')';
  }} else {{
    leanDate.textContent = cLean!=null && !isNaN(tLean) && tLean<=cLean ? 'cible atteinte' : '—';
    leanLine.textContent = 'définir une cible supérieure à l\\'actuel';
  }}
}}

function computeBone(){{
  const blk = $('bonedx-block'); if(!blk) return;
  let basis, basisLbl;
  if(CFG.sex === 'M'){{ basis = CFG.age >= 50 ? 'T' : 'Z'; }}
  else {{ const m = $('dx-meno'); basis = (m ? m.value : (CFG.age>=51?'post':'pre')) === 'post' ? 'T' : 'Z'; }}
  basisLbl = basis === 'T' ? 'T-score (OMS)' : 'Z-score (vs âge)';
  const sites = [['Rachis L1–L4','dx-spine'], ['Col fémoral','dx-neck'], ['Hanche totale','dx-hip']];
  const rows = [];
  for(const [lab,id] of sites){{
    const t = parseFloat($(id+'-t').value), z = parseFloat($(id+'-z').value);
    const v = basis === 'T' ? t : z;
    if(!isNaN(v)) rows.push({{lab, v, t, z}});
  }}
  if(!rows.length){{ blk.classList.add('hidden'); renumber(); return; }}
  blk.classList.remove('hidden');
  rows.sort((a,b)=>a.v-b.v);
  const low = rows[0];
  let verdict, cls;
  if(basis === 'T'){{
    if(low.v <= -2.5){{verdict='Ostéoporose'; cls='risk';}}
    else if(low.v < -1.0){{verdict='Ostéopénie'; cls='warn';}}
    else {{verdict='Densité normale'; cls='good';}}
  }} else {{
    if(low.v <= -2.0){{verdict='Sous la fourchette attendue pour l\\'âge'; cls='warn';}}
    else {{verdict='Dans la fourchette attendue pour l\\'âge'; cls='good';}}
  }}
  const fmt = x => isNaN(x) ? '—' : (x>0?'+':'') + x.toString().replace('.',',');
  let tbl = '<div class="since-grid">';
  for(const r of rows){{
    const isLow = (r === low);
    tbl += '<div class="since-row"><span class="sl">'+r.lab+(isLow?' <span style=\\'font-family:var(--font-mono);font-size:10px;color:var(--muted)\\'>· site déterminant</span>':'')+'</span>'+
      '<span class="sv">T '+fmt(r.t)+' · Z '+fmt(r.z)+'</span>'+
      '<span class="delta-chip '+(isLow?cls:'neutral')+'">'+basis+' '+fmt(r.v)+'</span></div>';
  }}
  tbl += '</div>';
  $('bonedx-verdict').innerHTML = '<span class="delta-chip '+cls+'" style="min-width:0">'+verdict+'</span>'+
    '<span style="font-size:12.5px;color:var(--ink-2);margin-left:10px">base : '+basisLbl+' · sur le site le plus bas ('+low.lab+')</span>';
  $('bonedx-rows').innerHTML = tbl;
}}

function bindToggles(){{
  document.querySelectorAll('.cp-check input[data-toggle]').forEach(cb => {{
    cb.addEventListener('change', () => {{
      document.querySelectorAll('section[data-mod="'+cb.dataset.toggle+'"]').forEach(s =>
        s.classList.toggle('hidden', !cb.checked));
      renumber();
    }});
  }});
  ['nut-goal','nut-activity','nut-meals','nut-training'].forEach(id => {{
    const el = $(id); if(el) el.addEventListener('change', computeNutrition);
  }});
  ['ov-prot','ov-carb','ov-fat'].forEach(id => {{
    const el = $(id); if(el) el.addEventListener('input', computeNutrition);
  }});
  ['proj-bf','proj-lean'].forEach(id => {{
    const el = $(id); if(el) el.addEventListener('input', computeProjector);
  }});
  ['dx-spine-t','dx-spine-z','dx-neck-t','dx-neck-z','dx-hip-t','dx-hip-z','dx-meno'].forEach(id => {{
    const el = $(id); if(el) el.addEventListener('input', computeBone);
    if(el) el.addEventListener('change', computeBone);
  }});
}}

function initProjectorDefaults(){{
  if($('proj-bf') && CFG.curBF!=null && !$('proj-bf').value)
    $('proj-bf').value = Math.max(CFG.bfFloor, Math.round((CFG.curBF-3)*10)/10);
  if($('proj-lean') && CFG.curLean!=null && !$('proj-lean').value)
    $('proj-lean').value = Math.round((CFG.curLean+2)*10)/10;
}}

document.addEventListener('DOMContentLoaded', () => {{
  bindToggles(); initProjectorDefaults(); computeNutrition(); computeProjector(); computeBone(); renumber();
}});
</script>'''


def render(A: dict, img_skeletal=None, img_thermal=None) -> str:
    with open(_STYLE, encoding="utf-8") as f:
        css = f.read()
    name = A["demo"]["name"] or "Client"
    subtitle = ("Généré automatiquement depuis l'export Hologic<br>"
                + (f'{A["n_exams"]} examens · suivi longitudinal' if A["n_exams"] > 1
                   else "Premier examen (baseline)"))
    nutri = ""
    if A.get("metabolism"):
        nutri = _metabolism(A) + _nutrition(A) + _meals(A)
    proj = _projector(A) if (A["snap"].get("bf_pct") and A["snap"].get("lean_g")) else ""
    script = _script(A)

    body = "".join([
        _header(A, subtitle),
        _patient(A),
        _coach_panel(A),
        _hero(A),
        _composition(A, img_skeletal, img_thermal),
        _since(A),
        _muscle(A),
        _fat(A),
        _bone(A),
        _bone_dx(A),
        nutri,
        proj,
        _trends_section(A),
        _interp_section(A),
        _method(A),
    ])
    return f'''<!doctype html><html lang="fr"><head><meta charset="utf-8">
<title>Bilan Corporel DXA 2.0 — {esc(name)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{css}</style></head><body><div class="wrap">{body}</div>
<button class="pdf-fab no-print" onclick="window.print()" title="Enregistrer le rapport en PDF">🖨 Exporter en PDF</button>
{script}</body></html>'''
