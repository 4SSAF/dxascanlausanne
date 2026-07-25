#!/usr/bin/env python3
"""
Générateur de Rapport DXA 2.0 (Motion LAB).

Usage :
    python generate.py entree.pdf                 # -> entree.rapport2.html
    python generate.py entree.pdf -o sortie.html
    python generate.py entree.pdf --json          # affiche aussi les données extraites
    python generate.py *.pdf                       # traite plusieurs fichiers

Le HTML produit est autonome (CSS + images embarqués), thème clair/sombre,
imprimable. Aucune donnée patient n'est envoyée sur le réseau.
"""
import argparse
import json
import os
import sys

from dxa2 import parse, analyze, render, store


def build_report(pdf_path: str, out_path: str | None = None, dump_json=False,
                 use_store=True, db_path=None) -> str:
    data = parse.parse_pdf(pdf_path)
    if use_store:
        try:
            data, _ = store.merge(data, db_path)
        except Exception as e:  # noqa: BLE001
            print(f"  (mémoire client ignorée : {e})")
    A = analyze.analyze(data)
    skeletal, thermal = parse.extract_images(pdf_path)
    html = render.render(A, img_skeletal=skeletal, img_thermal=thermal)

    if out_path is None:
        base = os.path.splitext(os.path.basename(pdf_path))[0]
        out_path = os.path.join(os.path.dirname(pdf_path) or ".", f"{base}.rapport2.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    b = A["bioage"]
    print(f"✓ {os.path.basename(pdf_path)} → {out_path}")
    print(f"  {A['demo']['name']} · {A['demo']['sex']} · {A['demo']['age']} ans · "
          f"{A['n_exams']} examen(s)")
    print(f"  Âge biologique ≈ {b['composite']} ans "
          f"(métab {b['metabolic']} / muscle {b['muscle']} / os {b['bone']})")
    if dump_json:
        printable = {k: v for k, v in data.items() if k != "snapshot"}
        printable["snapshot"] = data["snapshot"]
        print(json.dumps(printable, indent=2, ensure_ascii=False, default=str))
    return out_path


def main(argv=None):
    ap = argparse.ArgumentParser(description="Génère un Rapport DXA 2.0 depuis un export Hologic PDF.")
    ap.add_argument("pdf", nargs="+", help="fichier(s) PDF Hologic APEX")
    ap.add_argument("-o", "--output", help="fichier HTML de sortie (un seul PDF)")
    ap.add_argument("--json", action="store_true", help="affiche les données extraites")
    ap.add_argument("--no-store", action="store_true", help="ne pas utiliser la mémoire client")
    ap.add_argument("--db", help="chemin du fichier de mémoire client (JSON)")
    args = ap.parse_args(argv)

    if args.output and len(args.pdf) > 1:
        ap.error("-o ne peut être utilisé qu'avec un seul PDF.")

    rc = 0
    for p in args.pdf:
        if not os.path.exists(p):
            print(f"✗ introuvable : {p}", file=sys.stderr)
            rc = 1
            continue
        try:
            build_report(p, args.output, args.json,
                         use_store=not args.no_store, db_path=args.db)
        except Exception as e:  # noqa: BLE001
            print(f"✗ échec {p} : {e}", file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
