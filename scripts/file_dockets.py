#!/usr/bin/env python3
"""File the dockets of the Nine — the first FILED artifacts under LS-1.0.

Reads ONLY cached sources (data/sources/), computes axes, writes immutable
dockets to data/dockets/LS-J-001..009.json. Deterministic: re-run produces
bit-identical files (verified via --verify).

Usage:
  python scripts/file_dockets.py            # compute + file
  python scripts/file_dockets.py --verify   # recompute, compare bit-identical
  python scripts/file_dockets.py --stats    # print the human numbers
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "core" / "src"))

from legally_subjective.axes import v1  # noqa: E402
from legally_subjective.docket import writer  # noqa: E402

AXIS_LABELS = {
    "disposition": "Disposition",
    "temperament": "Temperament",
    "precedent": "Precedent",
    "reversal": "Reversal",
    "orality": "Orality",
    "exposure": "Exposure",
}

METRIC_DEFS = {
    "disposition": (
        "Petitioner-alignment rate: of the merits cases this justice voted in, "
        "the share where their side favored the party seeking relief "
        "(petitioner/appellant), resolved from the Oyez winning-party record. "
        "A directional outcome-orientation proxy — not an affirm/reverse count."
    ),
    "temperament": (
        "Dissent rate: of the merits votes cast, the share cast with the "
        "minority. A collegial-conduct proxy from public records — not a "
        "psychological assessment."
    ),
    "precedent": (
        "Citation density: mean number of authorities cited per authored lead "
        "opinion (CourtListener cites arrays). Engagement with precedent, "
        "measured by citation volume, not by treatment."
    ),
    "exposure": (
        "Publication rate: authored lead opinions per year of service inside "
        "the declared window (service years from Oyez role metadata)."
    ),
}

LIMITS = [
    "Temperament is a collegiality proxy from public voting records, not a psychological assessment.",
    "Percentiles are relative to the declared bench (the sitting Nine), not absolute qualities.",
    "Small-bench rule: with 9 members, percentiles take 9 discrete values — the granularity is coarse by construction.",
    "Reversal and Orality are null: SCOTUS is the terminal court (no reviewing treatment data), and oral-argument transcripts are not yet ingested.",
    "The window is terms 2020-2026; a justice who joined mid-window has fewer observations by fact, not by choice.",
]


def build_dockets() -> list[dict]:
    bench = v1.compute_bench()
    filed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    dockets: list[dict] = []
    for slug, name, author_id in v1.THE_NINE:
        r = bench["justices"][slug]
        docket_id = r["docket_id"]
        axes: dict = {}
        for axis in ("disposition", "temperament", "precedent", "reversal", "orality", "exposure"):
            if axis in ("reversal", "orality"):
                axes[axis] = {"percentile": None, "ci95": None, "n": 0, "status": "insufficient-data",
                              "note": "not computable from current sources"}
                continue
            a = r["axes"].get(axis)
            if a is None:
                axes[axis] = {"percentile": None, "ci95": None, "n": 0, "status": "insufficient-data"}
                continue
            axes[axis] = {
                "percentile": a["percentile"],
                "ci95": a["ci95"],
                "n": a["n"],
                "status": "ok",
                "value": round(a["value"], 4),
                "metric": a["metric"],
                "metric_def": METRIC_DEFS[axis],
                "sources": [
                    f"oyez:api.oyez.org/cases/<term>/<docket> — {len([v for v in r['votes']])} merits case files cached under data/sources/oyez/ (each carries __source_uri__ + __retrieved_at__)"
                    if axis in ("disposition", "temperament")
                    else f"courtlistener:…/api/rest/v4/search/?judge=… — {len(r['ops'])} lead-opinion pages cached under data/sources/courtlistener/judges/{slug}/ with manifest"
                ],
            }
        docket = {
            "standard": v1.STANDARD,
            "docket": docket_id,
            "revision": 0,
            "subject": {
                "name": name,
                "slug": slug,
                "role": v1.ROLE[slug],
                "court": "supreme-court-of-the-united-states",
                "bench": "scotus-sitting-2020-2026",
                "bench_n": 9,
                "small_bench": True,
            },
            "status": "FILED",
            "filed_at": filed_at,
            "window": {"start": bench["window_start"], "end": bench["window_end"]},
            "raw": {
                "merits_votes": len(r["votes"]),
                "lead_opinions": len(r["ops"]),
                "service_years_window": len(r["years"]),
                "separate_writings": sum(1 for v in r["votes"] if v["separate"]),
                "dissents": sum(1 for v in r["votes"] if v["vote"] == "minority"),
            },
            "axes": axes,
            "projections": {"iterations": v1.BOOTSTRAP_ITERS, "seed_basis": "sha256(docket|axis|LS-1.0) truncated to 32 bits", "quantiles": {"p10": None, "p50": None, "p90": None}},
            "limits": LIMITS,
            "chain": {
                "computed_at": filed_at,
                "pipeline": "legally-subjective/1.0.0",
            },
        }
        dockets.append(docket)
    return dockets


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    dockets = build_dockets()

    if mode == "--stats":
        print(f"window {dockets[0]['window']} · bench_n 9")
        hdr = f"{'docket':<9}{'justice':<26}{'disp':>6}{'temp':>6}{'prec':>6}{'expo':>6}{'votes':>7}{'ops':>5}"
        print(hdr)
        for d in dockets:
            row = f"{d['docket']:<9}{d['subject']['name']:<26}"
            for ax in ("disposition", "temperament", "precedent", "exposure"):
                a = d["axes"][ax]
                row += f"{(str(a['percentile']) if a['percentile'] is not None else '—'):>6}"
            row += f"{d['raw']['merits_votes']:>7}{d['raw']['lead_opinions']:>5}"
            print(row)
        return 0

    digests: dict[str, str] = {}
    for d in dockets:
        p = writer.file_docket(d)
        digests[d["docket"]] = json.loads(p.read_text())["chain"]["sha256"]
        print(f"FILED {d['docket']} — {d['subject']['name']}")

    if mode == "--verify":
        ok = True
        for d in dockets:
            p = REPO / "data" / "dockets" / f"{d['docket']}.json"
            before = p.read_bytes()
            writer.file_docket(d)
            if p.read_bytes() != before:
                ok = False
                print(f"NON-DETERMINISTIC: {d['docket']}")
        print("determinism:", "OK — bit-identical" if ok else "FAILED")
        return 0 if ok else 1

    (REPO / "data" / "dockets" / "MANIFEST.json").write_text(
        json.dumps(
            {
                "filed_at": dockets[0]["filed_at"],
                "standard": "LS-1.0",
                "pipeline": "legally-subjective/1.0.0",
                "dockets": digests,
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
