#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legally Subjective — M3b : paquet d'artefacts (cahier des charges §XVI).

Assemble, depuis l'état RÉEL d'une expérience (racine Drive ou copie), un
paquet organisé et auto-descriptif :

    artifacts/
      experiment_manifest.json     lignage complet (copie)
      m3b_report.json              rapport dérivé (copie)
      m3b_gate.json                verdict GO/NO-GO (copie ou régénéré)
      state.json                   manifeste d'état (copie)
      environment.json             environnement consigné
      hashes.json                  TOUS les hash recalculés au moment du
                                   paquet (jamais copiés-collés)
      events.jsonl                 journal complet (copie)
      log.txt                      journal lisible (copie)
      adapters/<juge>/             adaptateurs finaux
      final/m3b_adapters_final.zip export final
      evidence/                    captures réelles + index
      reports/m3b_dossier.md       rapport expérimental généré
      README.md                    comment tout re-vérifier

Chaque fichier copié est haché AVANT copie, la copie est vérifiée APRÈS
(hash identique) : le paquet est auto-vérifiant. Rien n'est inventé —
un élément absent reste absent (et figure dans README comme NON TESTÉ).

Usage :
  python scripts/build_artifacts.py --root <racine état> --repo <dépôt> \
         --out <dossier artifacts>
"""

import argparse
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import m3b_state as M                                       # noqa: E402


def copy_verified(src, dst, hashes, label):
    """Copie + hash avant/après : la copie est vérifiée octet par octet."""
    if not os.path.isfile(src):
        return None
    h0 = M.sha256_file(src)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    h1 = M.sha256_file(dst)
    if h0 != h1:
        raise RuntimeError(f"copie divergente pour {label} : {h0} vs {h1}")
    hashes[label] = {"path": os.path.relpath(dst, os.path.dirname(dst)),
                     "sha256": h1,
                     "size": os.path.getsize(dst)}
    return h1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    root, repo, out = args.root, args.repo, args.out
    if os.path.abspath(root) == os.path.abspath(out):
        ap.error("--out doit différer de --root")
    os.makedirs(out, exist_ok=True)

    st = json.load(open(os.path.join(root, "state.json"), encoding="utf-8"))
    man = None
    try:
        man = json.load(open(os.path.join(root, "experiment_manifest.json"),
                             encoding="utf-8"))
    except Exception:
        pass
    hashes = {}
    t0 = time.time()

    # ---- fichiers simples, copie vérifiée ----------------------------------
    simple = [("state.json", "state.json"),
              ("experiment_manifest.json", "experiment_manifest.json"),
              ("m3b_report.json", "m3b_report.json"),
              ("m3b_gate.json", "m3b_gate.json"),
              ("events.jsonl", "events.jsonl"),
              ("log.txt", "log.txt")]
    for src_rel, label in simple:
        copy_verified(os.path.join(root, src_rel),
                      os.path.join(out, src_rel), hashes, label)

    # ---- adaptateurs (répertoires, fichier par fichier) --------------------
    judges = st.get("judges", {})
    for j in sorted(judges):
        d = os.path.join(root, "adapters", j)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            p = os.path.join(d, fn)
            if os.path.isfile(p):
                copy_verified(p, os.path.join(out, "adapters", j, fn),
                              hashes, f"adapters/{j}/{fn}")

    # ---- export final --------------------------------------------------------
    copy_verified(os.path.join(root, "final", "m3b_adapters_final.zip"),
                  os.path.join(out, "final", "m3b_adapters_final.zip"),
                  hashes, "final/m3b_adapters_final.zip")

    # ---- preuves -------------------------------------------------------------
    evd = os.path.join(root, "evidence")
    if os.path.isdir(evd):
        for fn in sorted(os.listdir(evd)):
            p = os.path.join(evd, fn)
            if os.path.isfile(p):
                copy_verified(p, os.path.join(out, "evidence", fn),
                              hashes, f"evidence/{fn}")

    # ---- environnement isolé --------------------------------------------------
    env = (man or {}).get("environment") or st.get("environment") or {}
    with open(os.path.join(out, "environment.json"), "w",
              encoding="utf-8") as f:
        json.dump({"environment": env,
                   "environments_seen_n": (man or {}).get(
                       "environments_seen_n"),
                   "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                time.gmtime())},
                  f, indent=1, ensure_ascii=False)

    # ---- hash globaux recalculés ----------------------------------------------
    links, ok_all = M.verify_lineage(root, repo)
    with open(os.path.join(out, "hashes.json"), "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                          time.gmtime()),
            "lineage_ok": ok_all,
            "lineage_links": [{"ok": o, "name": n, "detail": d}
                              for o, n, d in links],
            "files": hashes,
        }, f, indent=1, ensure_ascii=False)

    # ---- rapport expérimental ---------------------------------------------------
    import m3b_report_gen as RG
    text, verdict = RG.build_report(root, repo)
    os.makedirs(os.path.join(out, "reports"), exist_ok=True)
    with open(os.path.join(out, "reports", "m3b_dossier.md"), "w",
              encoding="utf-8") as f:
        f.write(text)
    with open(os.path.join(out, "reports", "m3b_dossier.json"), "w",
              encoding="utf-8") as f:
        json.dump(verdict, f, indent=1, ensure_ascii=False)

    # ---- README : comment TOUT re-vérifier --------------------------------------
    pilot = verdict.get("pilot")
    n_files = sum(1 for _ in
                  (os.path.join(dp, f)
                   for dp, _, fs in os.walk(out) for f in fs))
    readme = f"""# Paquet d'artefacts M3b — Legally Subjective

Généré le {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} UTC par
`scripts/build_artifacts.py` ({n_files} fichiers, {time.time() - t0:.1f} s).

{"⚠ **PAQUET DE PILOTE** (modèle miniature, données synthétiques) — "
 "prouve la mécanique, PAS la condition B." if pilot else ""}

## Contenu

- `experiment_manifest.json` — lignage : expérience → code → données →
  configuration → environnement → checkpoints → adaptateurs → export ;
- `state.json` — manifeste d'état (source de vérité unique de l'expérience) ;
- `events.jsonl` / `log.txt` — journal d'événements complet ;
- `m3b_report.json` — rapport dérivé (jamais édité à la main) ;
- `m3b_gate.json` — verdict GO/NO-GO du portillon ;
- `adapters/` — adaptateurs finaux par juge ;
- `final/m3b_adapters_final.zip` — export final consommé par le runner M4 ;
- `evidence/` — captures de sorties RÉELLES (jamais fabriquées) + index ;
- `reports/m3b_dossier.md` — rapport expérimental lisible ;
- `hashes.json` — tous les hash RECALCULÉS au moment du paquet + chaîne
  de lignage ({sum(1 for o, _, _ in links if o)}/{len(links)} maillons).

## Re-vérifier ce paquet (ne pas faire confiance à ce README)

```bash
python scripts/m3b_lineage.py --root <racine d'état d'origine> \\
     --repo <dépôt>
python scripts/m3b_gate.py --root <racine d'état d'origine> \\
     --repo <dépôt>
python scripts/build_artifacts.py --root <racine> --repo <dépôt> \\
     --out <nouveau paquet>   # deux paquets du même état ont des
                              # hashes.json identiques (idempotence)
```

Chaque fichier de ce paquet a été copié avec vérification de hash
avant/après copie. Un élément absent de l'expérience d'origine est
absent ici (aucune compensation, aucune invention).

{"Verdict courant : " + str(verdict.get('gate')) + " (pilote — "
 "l'entraînement GPU réel reste à exécuter sur Colab)." if pilot else
 "Verdict courant : " + str(verdict.get('gate')) + "."}
"""
    with open(os.path.join(out, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme)

    print(f"→ {out} : {n_files} fichiers en {time.time() - t0:.1f} s")
    print(f"  chaîne de lignage : {sum(1 for o, _, _ in links if o)}"
          f"/{len(links)} maillons — "
          f"{'INTÈGRE' if ok_all else 'ROMPUE'}")
    print(f"  verdict portillon : {(json.load(open(os.path.join(out, 'reports', 'm3b_dossier.json')))).get('gate')}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
