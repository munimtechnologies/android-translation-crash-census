#!/usr/bin/env python3
"""Tests for placeholder_order.py.

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import gzip
import json
import os
import tempfile
import unittest

import placeholder_order as po


class Specs(unittest.TestCase):
    def test_unnumbered(self):
        self.assertEqual(po.specs("%s has %d"), [(None, False, "s"), (None, False, "d")])

    def test_literal_percent_and_newline_take_no_argument(self):
        self.assertEqual(po.specs("100%% done%n%s"), [(None, False, "s")])

    def test_numbered(self):
        self.assertEqual(po.specs("%2$d of %1$s"), [(2, False, "d"), (1, False, "s")])

    def test_kinds(self):
        self.assertEqual([k for _, _, k in po.specs("%x %.2f %c %b %tY %S %X")],
                         ["d", "f", "c", "b", "t", "s", "d"])

    def test_throwing_conversions(self):
        self.assertIsNone(po.specs("%y"))
        self.assertIsNone(po.specs("%D"))
        self.assertIsNone(po.specs("%0$s"))

    def test_prose_percent_is_read_as_java_reads_it(self):
        self.assertEqual(po.specs("50 % de"), [(None, False, "d")])

    def test_relative(self):
        self.assertEqual(po.specs("%s %<s"), [(None, False, "s"), (None, True, "s")])


class Classify(unittest.TestCase):
    def check(self, source, target, kind, category):
        self.assertEqual(po.classify(source, target), (kind, category))

    def test_mixed_unnumbered_source(self):
        self.check("%s has %d", "%s a %d", "unnumbered_mixed", "kept_unnumbered")
        self.check("%s has %d", "%d ... %s", "unnumbered_mixed", "unnumbered_reordered")
        self.check("%s has %d", "%2$d ... %1$s", "unnumbered_mixed", "numbered_reordered")
        self.check("%s has %d", "%1$s ... %2$d", "unnumbered_mixed", "numbered_in_order")

    def test_wrong_kinds_and_counts_are_other(self):
        self.check("%s has %d", "%2$s ... %1$d", "unnumbered_mixed", "other")
        self.check("%s has %d", "%s", "unnumbered_mixed", "other")
        self.check("%s has %d", "%s %d %d", "unnumbered_mixed", "other")
        self.check("%s has %d", "%1$s %d", "unnumbered_mixed", "other")
        self.check("%s has %d", "%s %y", "unnumbered_mixed", "other")
        self.check("%s has %d", "%s %<s", "unnumbered_mixed", "other")

    def test_same_kind_source(self):
        self.check("%s and %s", "%s y %s", "unnumbered_same", "kept_unnumbered")
        self.check("%s and %s", "%2$s y %1$s", "unnumbered_same", "numbered_reordered")

    def test_numbered_source(self):
        self.check("%1$s of %2$s", "%2$sの%1$s", "numbered", "numbered_reordered")
        self.check("%1$s of %2$s", "%1$s de %2$s", "numbered", "numbered_in_order")
        self.check("%1$s of %2$s", "%s de %s", "numbered", "kept_unnumbered")
        self.check("%1$s has %2$d", "%d ... %s", "numbered", "unnumbered_reordered")

    def test_numbered_source_out_of_order(self):
        self.check("%2$s of %1$s", "%2$s de %1$s", "numbered", "numbered_in_order")
        self.check("%2$s of %1$s", "%1$s de %2$s", "numbered", "numbered_reordered")
        self.check("%2$s of %1$s", "%s de %s", "numbered", "other")

    def test_not_counted(self):
        self.assertEqual(po.classify("%s", "%s"), (None, None))
        self.assertEqual(po.classify("%1$s %1$s", "%1$s"), (None, None))
        self.assertEqual(po.classify("%s %<s", "%s"), (None, None))
        self.assertEqual(po.classify("%1$s %s", "%s %s"), (None, None))
        self.assertEqual(po.classify("%1$s %3$s", "%s %s"), (None, None))


class Helpers(unittest.TestCase):
    def test_language(self):
        self.assertEqual(po.language("pt-rBR"), "pt")
        self.assertEqual(po.language("b+sr+Latn"), "sr")
        self.assertEqual(po.language("iw"), "he")
        self.assertEqual(po.language("zh-rTW"), "zh")

    def test_order_text(self):
        self.assertEqual(po.order_text("%2$d of %1$s"), "2$d 1$s")
        self.assertEqual(po.order_text("%s %d"), "s d")

    def test_word_order(self):
        self.assertEqual(po.WORD_ORDER["ja"], "SOV")
        self.assertEqual(po.WORD_ORDER["fr"], "SVO")
        self.assertEqual(po.WORD_ORDER["de"], "no dominant order")

    def test_cluster_ci(self):
        low, high = po.cluster_ci([(1, 10), (2, 10), (0, 10), (5, 10)])
        self.assertLessEqual(low, 0.2)
        self.assertGreaterEqual(high, 0.2)
        self.assertEqual(po.cluster_ci([(1, 10)]), (None, None))


def sample_tally():
    t = po.Tally()
    rows = []
    for i in range(25):
        repo = "https://example.org/r%d" % i
        for lang, src, tgt in [("ja", "%1$s of %2$s", "%2$sの%1$s"),
                               ("ja", "%s has %d", "%d ... %s"),
                               ("ja", "%s has %d", "%2$d ... %1$s"),
                               ("ko", "%1$s of %2$s", "%2$s %1$s"),
                               ("fr", "%1$s of %2$s", "%1$s de %2$s"),
                               ("fr", "%s has %d", "%s a %d"),
                               ("fr", "%s and %s", "%1$s et %2$s")]:
            kind, cat = po.classify(src, tgt)
            t.add(repo, lang, kind, cat, src + str(i), tgt)
            rows.append({"repo": repo, "res": "app/src/main/res", "locale": lang, "lang": lang,
                         "key": "k", "kind": kind, "category": cat,
                         "source_order": po.order_text(src), "target_order": po.order_text(tgt),
                         "source": src, "target": tgt, "link": ""})
    return t, rows


class Aggregates(unittest.TestCase):
    def test_rows(self):
        t, _ = sample_tally()
        ja = t.row("lang:ja", "unnumbered_mixed")
        self.assertEqual((ja["valid"], ja["reordered"], ja["unsafe"]), (50, 50, 25))
        self.assertAlmostEqual(ja["unsafe_share"], 0.5)
        fr = t.row("group:SVO", "numbered")
        self.assertEqual(fr["reorder_rate"], 0.0)
        self.assertEqual(fr["repos"], 25)
        self.assertEqual(t.row("all", "unnumbered_same")["numbered_in_order"], 25)

    def test_predictions(self):
        t, _ = sample_tally()
        got = {n: ok for n, _, ok in po.predictions(t)}
        self.assertEqual(sorted(got), ["P1", "P2", "P3", "P4", "P5", "P6"])
        self.assertTrue(got["P1"])
        self.assertTrue(got["P2"])
        self.assertTrue(got["P4"])

    def test_write(self):
        t, rows = sample_tally()
        records = [{"repo": "r", "status": "ok"}, {"repo": "s", "status": "error"}]
        with tempfile.TemporaryDirectory() as out:
            summary = po.write(out, t, rows, records, {"index_url": "x", "finished": "y"})
            self.assertEqual(summary["unnumbered_reordered"], 25)
            for name in ("report.md", "summary.json", "by_language.csv",
                         "unnumbered_reordered.csv", "pairs.csv.gz"):
                self.assertTrue(os.path.exists(os.path.join(out, name)), name)
            with gzip.open(os.path.join(out, "pairs.csv.gz"), "rt", encoding="utf-8") as f:
                self.assertEqual(len(f.read().splitlines()), len(rows) + 1)
            with open(os.path.join(out, "summary.json"), encoding="utf-8") as f:
                self.assertEqual(len(json.load(f)["predictions"]), 6)
            with open(os.path.join(out, "report.md"), encoding="utf-8") as f:
                self.assertIn("## Predictions", f.read())


if __name__ == "__main__":
    unittest.main()
