#!/usr/bin/env python3
"""test_m4_metrics.py — tests du noyau statistique de l'Épreuve.

Stdlib uniquement, aucune dépendance. Chaque valeur attendue est calculée
à la main ou vérifiable en une ligne — le protocole mérite des tests qu'on
peut relire en trente secondes.
"""

import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from m4_metrics import (BOOT_SEED, accuracy, bootstrap_ci,  # noqa: E402
                         bootstrap_paired_diff, brier, condition_report,
                         ece, f1_macro, log_loss, mcnemar_exact,
                         mcnemar_table, paired_report, reliability,
                         wilson)


class TestWilson(unittest.TestCase):

    def test_reference_values(self):
        # wilson(6, 8) : p=0,75 → [0,409 ; 0,929] (calcul manuel)
        lo, hi = wilson(6, 8)
        self.assertAlmostEqual(lo, 0.4093, places=3)
        self.assertAlmostEqual(hi, 0.9285, places=3)

    def test_extremes(self):
        self.assertEqual(wilson(0, 0), (0.0, 0.0))
        lo, hi = wilson(0, 10)
        self.assertEqual(lo, 0.0)
        self.assertLess(hi, 0.35)  # borne sup d'aucun succès sur 10

    def test_ordering(self):
        for k, n in [(3, 10), (5, 7), (12, 40)]:
            lo, hi = wilson(k, n)
            self.assertLessEqual(lo, k / n)
            self.assertGreaterEqual(hi, k / n)


class TestBootstrap(unittest.TestCase):

    def test_perfect_and_zero(self):
        labels = [1, 0, 1, 1, 0]
        lo, hi, pt = bootstrap_ci(labels, list(labels), n_boot=500)
        self.assertEqual((lo, hi, pt), (1.0, 1.0, 1.0))
        # toutes fausses : aucune prédiction ne coïncide avec le label
        anti = [0, 1, 0, 0, 1]
        lo, hi, pt = bootstrap_ci(labels, anti, n_boot=500)
        self.assertEqual((lo, hi, pt), (0.0, 0.0, 0.0))

    def test_determinism(self):
        labels = [1, 0, 1, 1, 0, 1, 0, 0]
        preds = [1, 0, 0, 1, 0, 1, 1, 0]
        a = bootstrap_ci(labels, preds, n_boot=300, seed=BOOT_SEED)
        b = bootstrap_ci(labels, preds, n_boot=300, seed=BOOT_SEED)
        self.assertEqual(a, b)

    def test_covers_point(self):
        rng = random.Random(7)
        labels = [rng.randint(0, 1) for _ in range(60)]
        preds = [rng.randint(0, 1) for _ in range(60)]
        lo, hi, pt = bootstrap_ci(labels, preds, n_boot=2000)
        self.assertLessEqual(lo, pt)
        self.assertGreaterEqual(hi, pt)
        self.assertGreaterEqual(hi - lo, 0.0)


class TestMcNemar(unittest.TestCase):

    def test_no_discordance(self):
        self.assertEqual(mcnemar_exact(0, 0), 1.0)

    def test_known_values(self):
        # b=5, c=0 : p = 2*comb(5,0)/2^5 = 2/32 = 0,0625
        self.assertAlmostEqual(mcnemar_exact(5, 0), 0.0625, places=6)
        # b=8, c=0 : p = 2/256 = 0,0078125
        self.assertAlmostEqual(mcnemar_exact(8, 0), 0.0078125, places=6)
        # symétrie parfaite : p = 1
        self.assertAlmostEqual(mcnemar_exact(3, 3), 1.0, places=6)
        # symétrie des arguments
        self.assertEqual(mcnemar_exact(2, 9), mcnemar_exact(9, 2))

    def test_table(self):
        labels = [1, 1, 0, 0, 1, 0]
        a = [1, 0, 0, 0, 1, 1]
        b = [1, 1, 0, 1, 0, 1]
        # cas2 : A faux B juste ; cas4 et cas5 : A juste B faux ;
        # cas6 : les deux faux → (n01, n10) = (2, 1)
        self.assertEqual(mcnemar_table(labels, a, b), (2, 1))


class TestProbabilistic(unittest.TestCase):

    def test_log_loss_extremes(self):
        self.assertAlmostEqual(log_loss([0.999], [1]), -(
            0.999 and __import__("math").log(0.999)), places=6)
        self.assertAlmostEqual(log_loss([1.0, 0.0], [1, 0]), 0.0, places=12)
        self.assertAlmostEqual(log_loss([0.0, 1.0], [1, 0]), 34.5388,
                               places=3)  # clampée : -ln(1e-15) ≈ 34,54

    def test_brier(self):
        self.assertEqual(brier([1, 0], [1, 0]), 0.0)
        self.assertEqual(brier([1, 0], [0, 1]), 1.0)
        self.assertAlmostEqual(brier([0.5, 0.5], [1, 0]), 0.25)

    def test_ece(self):
        self.assertEqual(ece([1, 0, 1, 0], [1, 0, 1, 0]), 0.0)
        self.assertEqual(ece([0, 1], [1, 0]), 1.0)
        # calibration parfaite en moyenne : 100 prédictions à 0,7,
        # 70 % de succès → ECE = 0
        probs = [0.7] * 100
        labels = [1] * 70 + [0] * 30
        self.assertAlmostEqual(ece(probs, labels), 0.0, places=9)

    def test_reliability_shape(self):
        r = reliability([0.05, 0.95, 0.55], [0, 1, 1])
        self.assertEqual([bin_n for _, bin_n, _, _ in r], [1, 1, 1])
        self.assertEqual(sum(bin_n for _, bin_n, _, _ in r), 3)


class TestF1(unittest.TestCase):

    def test_known_value(self):
        # classe 0 : tp=1, fp=0, fn=1 → préc 1, rappel 1/2 → F1 2/3
        # classe 1 : tp=2, fp=1, fn=0 → préc 2/3, rappel 1 → F1 4/5
        # macro = (2/3 + 4/5)/2 = 11/15 ≈ 0,7333
        self.assertAlmostEqual(
            f1_macro([0, 0, 1, 1], [0, 1, 1, 1]), 11 / 15, places=6)

    def test_perfect(self):
        self.assertEqual(f1_macro([0, 1, 2], [0, 1, 2]), 1.0)
        self.assertEqual(f1_macro([], []), 0.0)


class TestReports(unittest.TestCase):

    def test_condition_report(self):
        labels = [1, 0, 1, 1, 0]
        preds = [1, 0, 1, 0, 0]
        probs = [0.9, 0.2, 0.8, 0.6, 0.3]
        rep = condition_report(labels, preds, probs, n_boot=300)
        self.assertEqual(rep["n"], 5)
        self.assertEqual(rep["correct"], 4)
        self.assertEqual(rep["accuracy"], 0.8)
        self.assertIn("log_loss", rep)
        self.assertIn("ece", rep)
        self.assertEqual(len(rep["wilson95"]), 2)

    def test_paired_report(self):
        labels = [1, 0, 1, 0]
        a = [1, 0, 1, 0]
        b = [1, 0, 0, 0]
        rep = paired_report(labels, a, b, n_boot=300)
        self.assertEqual(rep["n01_a_juste_b_faux"], 1)
        self.assertEqual(rep["n10_a_faux_b_juste"], 0)
        self.assertGreaterEqual(rep["mcnemar_p_exact"], 0.5)  # n=1 → p=1
        self.assertIn("diff_bootstrap95", rep)

    def test_paired_diff_bounds(self):
        labels = [1] * 30 + [0] * 30
        a = [1] * 25 + [0] * 5 + [0] * 25 + [1] * 5   # 50/60
        b = [1] * 15 + [0] * 15 + [0] * 30            # 45/60
        lo, hi, pt = bootstrap_paired_diff(labels, a, b, n_boot=500)
        self.assertAlmostEqual(pt, 5 / 60, places=6)
        self.assertLessEqual(lo, pt)
        self.assertGreaterEqual(hi, pt)


class TestAccuracy(unittest.TestCase):

    def test_basic(self):
        self.assertEqual(accuracy([1, 1], [1, 0]), 0.5)
        self.assertEqual(accuracy([], []), 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
