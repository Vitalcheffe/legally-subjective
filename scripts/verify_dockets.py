#!/usr/bin/env python3
"""
Legally Subjective — vérification des sceaux LS-1.0.

Rejoue le scellement de chaque docket FILED : le sceau est le SHA-256 de la
sérialisation JSON compacte (UTF-8, séparateurs compacts, ordre des clés du
fichier) sans chain.sha256, écrite en dernier. Vérifie aussi que le
MANIFEST.json porte les mêmes sceaux. Sortie : OK/FAIL par docket, code de
retour non nul si un sceau ne se reproduit pas.

Usage :  python3 scripts/verify_dockets.py [LS-J-001 …]
"""
import hashlib
import json
import os
import sys

DOCKETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "data", "dockets")


def seal_of(docket: dict) -> str:
    sealed = {k: v for k, v in docket.items() if k != "chain"}
    sealed["chain"] = {k: v for k, v in docket["chain"].items() if k != "sha256"}
    return hashlib.sha256(
        json.dumps(sealed, ensure_ascii=False, separators=(",", ":"))
        .encode("utf-8")).hexdigest().upper()


def main() -> int:
    requested = [a for a in sys.argv[1:] if a.startswith("LS-J-")]
    files = sorted(f for f in os.listdir(DOCKETS)
                   if f.startswith("LS-J-") and f.endswith(".json"))
    if requested:
        files = [f for f in files if f[:-5] in requested]
    manifest = json.load(open(os.path.join(DOCKETS, "MANIFEST.json"), encoding="utf-8"))
    failures = 0
    print(f"{'docket':<12} {'sceau':<18} verdict")
    for fname in files:
        did = fname[:-5]
        with open(os.path.join(DOCKETS, fname), encoding="utf-8") as f:
            d = json.load(f)
        claimed = (d.get("chain") or {}).get("sha256")
        recomputed = seal_of(d)
        in_manifest = manifest.get("dockets", {}).get(did)
        ok = claimed == recomputed == in_manifest
        if not ok:
            failures += 1
        print(f"{did:<12} {(claimed or '—')[:16]:<18} "
              f"{'OK — sceau reproduit' if ok else 'FAIL'}"
              f"{'' if ok else f' (recalculé {recomputed[:16]}…, manifeste {in_manifest and in_manifest[:16] + chr(8230)})'}")
    print(f"\n{len(files)} dockets vérifiés — "
          f"{'tous les sceaux se reproduisent.' if failures == 0 else f'{failures} ÉCHEC(S).'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
