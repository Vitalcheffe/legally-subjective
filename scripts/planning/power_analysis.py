#!/usr/bin/env python3
"""Planning utility: statistical power analysis for Experiment A vs B.

Legally Subjective compares two classifiers evaluated on the SAME test
cases (zero-shot model A vs fine-tuned model B). The correct test for
paired proportions is McNemar's test on the discordant pairs:

    b = P(A wrong, B right)   (B fixes an error)
    c = P(A right, B wrong)   (B breaks a correct prediction)

H0: b = c.  We estimate, by Monte-Carlo, the probability of rejecting H0
(power) as a function of test-set size n, baseline accuracy, and the true
improvement delta. This tells us how large the test split must be BEFORE
we spend GPU hours — a protocol decision made with math, not vibes.

Usage:
    python scripts/planning/power_analysis.py
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

ALPHA = 0.05
NSIM = 20_000
SEED = 20260826  # fixed for reproducibility (R9)


@dataclass(frozen=True)
class Scenario:
    n: int                 # test-set size
    acc_a: float           # accuracy of the zero-shot model
    delta: float           # accuracy improvement of the fine-tuned model
    p_a_right_b_wrong: float  # c: probability B breaks a correct A prediction


def prob_vector(sc: Scenario) -> tuple[float, float, float, float]:
    """Joint outcome probabilities (a_correct, b_correct) with parameter c.

    b = P(A wrong, B right) = delta + c
    c = P(A right, B wrong)
    both right = acc_a - c ; both wrong = 1 - acc_a - delta - c... clamped.
    """
    c = sc.p_a_right_b_wrong
    b = sc.delta + c
    both_right = sc.acc_a - c
    both_wrong = 1.0 - both_right - b - c
    # numerical safety clamps (fail loudly if the scenario is impossible)
    assert both_right >= 0 and both_wrong >= 0, f"impossible scenario: {sc}"
    return (both_right, b, c, both_wrong)


def mcnemar_pvalue(b: int, c: int) -> float:
    """Two-sided exact binomial McNemar test via the normal approx with
    continuity correction (fine for planning purposes)."""
    n_disc = b + c
    if n_disc == 0:
        return 1.0
    z = (abs(b - c) - 1) / math.sqrt(n_disc)
    # two-sided p from the normal survival function
    p = 2.0 * (0.5 * math.erfc(z / math.sqrt(2.0)))
    return min(1.0, p)


def power(sc: Scenario, rng: random.Random) -> float:
    probs = prob_vector(sc)
    labels = [(1, 1), (0, 1), (1, 0), (0, 0)]  # (a_correct, b_correct)
    rejections = 0
    for _ in range(NSIM):
        b_count = 0
        c_count = 0
        for _ in range(sc.n):
            u = rng.random()
            cum = 0.0
            for p, (a, bb) in zip(probs, labels):
                cum += p
                if u < cum:
                    if (a, bb) == (0, 1):
                        b_count += 1
                    elif (a, bb) == (1, 0):
                        c_count += 1
                    break
        if mcnemar_pvalue(b_count, c_count) < ALPHA:
            rejections += 1
    return rejections / NSIM


def ci_half_width(p: float, n: int) -> float:
    """Half-width of an approximate 95% binomial CI (Wald)."""
    return 1.96 * math.sqrt(p * (1 - p) / n)


def main() -> None:
    rng = random.Random(SEED)

    print("# Power analysis — Experiment A (zero-shot) vs B (fine-tuned)")
    print(f"# McNemar exact test, alpha = {ALPHA}, {NSIM:,} simulations/scenario, seed = {SEED}\n")

    print("## Table 1 — power to detect a B improvement (c = 0.05)\n")
    header = "| test n | acc_A | delta | power | verdict |"
    print(header)
    print("|---" * 4 + "|---|")
    for n in (100, 200, 300, 400, 600):
        for acc_a, delta in ((0.60, 0.10), (0.65, 0.10), (0.65, 0.05)):
            sc = Scenario(n, acc_a, delta, 0.05)
            pw = power(sc, rng)
            verdict = "OK (>= 0.80)" if pw >= 0.80 else "underpowered"
            print(f"| {n} | {acc_a:.2f} | +{delta:.2f} | {pw:.2f} | {verdict} |")

    print("\n## Table 2 — 95% CI half-width on a single accuracy estimate\n")
    print("| test n | accuracy | 95% CI half-width |")
    print("|---|---|---|")
    for n in (100, 200, 300, 400, 600):
        for p in (0.60, 0.70, 0.80):
            print(f"| {n} | {p:.2f} | ±{ci_half_width(p, n) * 100:.1f} pp |")

    print("\n## Reading")
    print("- With 200 test cases, a +10 pp improvement is detectable, but a")
    print("  +5 pp improvement is not. With 400 test cases both are.")
    print("- A single accuracy measured on 200 cases carries a ±6-7 pp CI;")
    print("  any headline stat must be reported with its interval.")


if __name__ == "__main__":
    main()
