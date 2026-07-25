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
    return (f'<div class="rbar"><span class="rl">{esc(label)}</span>'
            f'<div class="rt"><span class="rf" style="width:{pct:.0f}%;background:var(--bone)"></span></div>'
            f'<span class="rv">{esc(value)}</span></div>')


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
    d = A["demo"]
    return f'''<header class="topbar">
    <div class="brand"><div class="mark">M</div>
      <div><div class="name">Motion LAB</div>
        <div class="sub">Analyse de composition corporelle · Lausanne</div></div></div>
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
        cards.append(_scard("OS", "var(--bone)", "Densité osseuse",
                            f'{fr(s.get("bmd_t"),1)} <span style="font-size:13px;color:var(--muted)">T</span>',
                            f'DMO {fr(s.get("bmd_total"),3)} g/cm²', st["bone"]))
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
    bars = ""
    if rb:
        mx = max([v for v in rb.values()] + [1])
        order = [("bassin", "Bassin"), ("jambe_g", "Jambes"), ("rachis_lomb", "Rachis L."), ("bras_g", "Bras")]
        seen = set()
        for key, lbl in order:
            if key in rb and lbl not in seen:
                bars += _rbar_bone(lbl, rb[key] / mx * 100, f'{fr(rb[key],3)} g/cm²')
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
    interp = ("densité osseuse <b style='color:var(--good)'>au-dessus</b> de la moyenne du jeune adulte."
              if above else "densité osseuse <b>normale</b>.")
    return f'''<section>
    <div class="sec-head"><span class="idx">05</span><h2 style="color:var(--bone)">Os — densité minérale</h2>
      <span class="note">Le pic de masse osseuse conditionne le risque de fracture des décennies plus tard.</span></div>
    <div class="grid g-2">
      <div class="card"><div class="eyebrow" style="margin-bottom:14px">T-score corps entier vs jeune adulte</div>
        {_meter("DMO totale", "", f'{fr(s.get("bmd_total"),3)} <small>g/cm² · T {fr(t)}</small>', A["meters"]["bmd"])}
        <p style="font-size:13px;color:var(--ink-2);margin-top:14px;line-height:1.55">T-score <b>{fr(t)}</b>, Z-score <b>{fr(s.get("bmd_z"))}</b> : {interp}</p></div>
      <div class="card"><div class="eyebrow" style="margin-bottom:14px">Densité par région (g/cm²)</div>
        {right}<div style="margin-top:18px">{bars}</div></div></div></section>'''


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
      d'un professionnel de santé. Données : export Hologic Horizon Wi / APEX (Motion LAB, Lausanne). Rapport généré automatiquement.</p>
    <div class="foot"><span>Motion LAB · Chemin du Petit-Flon 29 · 1052 Le Mont-sur-Lausanne · 021 512 40 00</span>
      <span>Rapport 2.0</span></div></section>'''


def _coach_panel(A):
    """Panneau de configuration coach — écran seulement, masqué au PDF."""
    has_nut = bool(A.get("metabolism"))
    mods = [("bioage", "Âge biologique", True), ("metabolism", "Métabolisme (BMR)", has_nut),
            ("nutrition", "Besoins nutritionnels", has_nut), ("meals", "Répartition des repas", has_nut),
            ("trends", "Évolution / tendances", True)]
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
        nut_controls = f'''
      <div class="cp-group"><label>Objectif</label>
        <select class="cp-select" id="nut-goal">{goals}</select></div>
      <div class="cp-group"><label>Niveau d'activité</label>
        <select class="cp-select" id="nut-activity">{acts}</select></div>
      <div class="cp-group"><label>Repas / jour</label>
        <select class="cp-select" id="nut-meals"><option value="3">3 repas</option>
          <option value="4" selected>4 repas</option><option value="5">5 repas</option></select></div>'''
    return f'''<div class="coach-panel no-print">
    <span class="cp-tag">Panneau coach — n'apparaît pas dans le PDF</span>
    <h3>Personnaliser le rapport selon le client</h3>
    <div class="cp-row">
      <div class="cp-group"><label>Sections à inclure</label>
        <div class="cp-checks">{checks}</div></div>
      {nut_controls}
      <button class="cp-export" onclick="window.print()">🖨 Exporter en PDF</button>
    </div>
    <div class="cp-hint">Cochez/décochez les sections, ajustez l'objectif, puis « Exporter en PDF » : le PDF ne contiendra que ce qui est affiché.</div>
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
          <div class="kpi-sub"><span id="m-prot-kg">{fr(nu["p_per_kg"])}</span> g/kg · <span id="m-prot-kcal">{nu["kcal_p"]}</span> kcal</div></div>
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
    </div></section>'''


def _meals(A):
    return f'''<section data-mod="meals">
    <div class="sec-head"><span class="idx">·</span><h2>Répartition des repas</h2>
      <span class="note">Protéines réparties pour maximiser la synthèse musculaire (~0,4 g/kg/prise).</span></div>
    <div class="card">
      <div class="meals-grid" id="meals-container"></div>
      <div id="mps-note" style="margin-top:14px"></div>
    </div></section>'''


def _script(A):
    mb = A["metabolism"]
    cfg = {
        "weight": A["demo"]["weight_kg"], "bmr": mb["bmr"],
        "activity": {k: v for k, _, v in R.ACTIVITY},
        "activityLab": {k: lab for k, lab, _ in R.ACTIVITY},
        "goalAdj": {k: v for k, _, v in R.GOALS},
        "goalLab": {k: lab for k, lab, _ in R.GOALS},
        "protPerKg": R.PROTEIN_G_PER_KG, "fatPerKg": R.FAT_G_PER_KG,
        "mpsPerKg": R.PROTEIN_PER_MEAL_G_PER_KG,
    }
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

function computeNutrition(){{
  if(!$('nut-goal')) return;
  const goal = $('nut-goal').value, act = $('nut-activity').value, meals = +$('nut-meals').value;
  const tdee = Math.round(CFG.bmr * CFG.activity[act]);
  const kcal = Math.round(tdee * (1 + CFG.goalAdj[goal]));
  const pPerKg = CFG.protPerKg[goal];
  const protein = Math.round(CFG.weight * pPerKg);
  const fat = Math.round(CFG.weight * CFG.fatPerKg);
  const kcalPF = protein*4 + fat*9;
  const carbs = Math.max(0, Math.round((kcal - kcalPF)/4));
  const kp = protein*4, kc = carbs*4, kf = fat*9, tot = Math.max(1, kp+kc+kf);
  // métabolisme
  if($('tdee')) $('tdee').textContent = tdee;
  if($('tdee-sub')) $('tdee-sub').textContent = 'BMR × activité (' + CFG.activityLab[act].split(' ')[0].toLowerCase() + ')';
  // nutrition
  if($('kcal-target')){{
    $('kcal-target').textContent = kcal;
    $('nut-goal-lab').textContent = '(' + CFG.goalLab[goal].split(' ')[0].toLowerCase() + ')';
    const diff = kcal - tdee;
    $('kcal-sub').textContent = diff===0 ? '= dépense énergétique' : (diff>0?'+':'') + diff + ' kcal vs dépense';
    $('m-prot').textContent = protein; $('m-prot-kg').textContent = pPerKg.toString().replace('.',',');
    $('m-prot-kcal').textContent = kp;
    $('m-carb').textContent = carbs; $('m-carb-kcal').textContent = kc;
    $('m-fat').textContent = fat; $('m-fat-kcal').textContent = kf;
    const pp=Math.round(kp/tot*100), pc=Math.round(kc/tot*100), pf=100-pp-pc;
    $('macrobar').innerHTML =
      '<div class="mseg" style="width:'+pp+'%;background:var(--muscle)">P '+pp+'%</div>'+
      '<div class="mseg" style="width:'+pc+'%;background:var(--metab)">G '+pc+'%</div>'+
      '<div class="mseg" style="width:'+pf+'%;background:var(--warn)">L '+pf+'%</div>';
    $('pct-prot').textContent = protein+' g'; $('pct-carb').textContent = carbs+' g'; $('pct-fat').textContent = fat+' g';
  }}
  // repas
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

function bindToggles(){{
  document.querySelectorAll('.cp-check input[data-toggle]').forEach(cb => {{
    cb.addEventListener('change', () => {{
      document.querySelectorAll('section[data-mod="'+cb.dataset.toggle+'"]').forEach(s =>
        s.classList.toggle('hidden', !cb.checked));
      renumber();
    }});
  }});
  ['nut-goal','nut-activity','nut-meals'].forEach(id => {{
    const el = $(id); if(el) el.addEventListener('change', computeNutrition);
  }});
}}

document.addEventListener('DOMContentLoaded', () => {{ bindToggles(); computeNutrition(); renumber(); }});
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

    body = "".join([
        _header(A, subtitle),
        _patient(A),
        _coach_panel(A),
        _hero(A),
        _composition(A, img_skeletal, img_thermal),
        _muscle(A),
        _fat(A),
        _bone(A),
        nutri,
        _trends_section(A),
        _interp_section(A),
        _method(A),
    ])
    script = _script(A) if A.get("metabolism") else ""
    return f'''<!doctype html><html lang="fr"><head><meta charset="utf-8">
<title>Bilan Corporel DXA 2.0 — {esc(name)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{css}</style></head><body><div class="wrap">{body}</div>{script}</body></html>'''
