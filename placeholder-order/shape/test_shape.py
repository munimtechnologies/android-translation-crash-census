"""Tests for shape.py (no network). Apache-2.0. MV2 of Munim, Inc., made with AI agents."""

import os
import tempfile
import unittest

import shape as s


def rows(lang, shape_source, n, reordered, kind="numbered", category=None, repos=10):
    """n scan rows for one language and source; the first `reordered` are reordered."""
    out = []
    for i in range(n):
        cat = category or ("numbered_reordered" if i < reordered else "numbered_in_order")
        out.append({"repo": "https://example.org/%s/%d" % (lang, i % repos), "lang": lang, "kind": kind,
                    "category": cat, "source": shape_source, "target": "t%d %s" % (i, shape_source)})
    return out


class ShapeTests(unittest.TestCase):
    def test_known(self):
        for text, want in s.KNOWN:
            self.assertEqual(s.shape(s.between(text)), want, text)

    def test_arg_spans_skip_percent_and_newline(self):
        self.assertEqual(len(s.arg_spans("%1$d%% done%n of %2$d")), 2)
        self.assertEqual(s.between("%1$d%% done%n of %2$d"), "%% done%n of ")
        self.assertEqual(len(s.arg_spans("%1$tR to %2$tR")), 2)
        self.assertIsNone(s.between("only %1$s"))

    def test_shapes(self):
        cases = {"%1$s, from %2$s": "adposition", "%1$s to the %2$s": "adposition",
                 "%1$s in a %2$s": "adposition", "%1$d out of %2$d": "of",
                 "%1$s of the %2$s": "of", "%1$d of total %2$d": "other", "%1$s%2$s": "no_words",
                 "%1$s\n%2$s": "no_words", "%1$s (%2$s)": "no_words", "%1$s の %2$s": "other",
                 "%1$s and then %2$s": "other", "%1$s or %2$s": "and_or",
                 "%1$s to a new %2$s": "other", "%1$s 5 %2$s": "no_words"}
        for text, want in cases.items():
            self.assertEqual(s.shape(s.between(text)), want, text)


class TallyTests(unittest.TestCase):
    def test_add_filters(self):
        t = s.Tally()
        for r in rows("ja", "%1$s of %2$s", 3, 1) + rows("ja", "%1$s, %2$s of %3$s", 2, 0) \
                + rows("ja", "%1$s of %2$s", 2, 0, category="other") \
                + rows("ja", "%s of %d", 2, 0, kind="unnumbered_mixed"):
            t.add(r)
        self.assertEqual(t.skipped["three_or_more_arguments"], 2)
        self.assertEqual(t.skipped["not_valid"], 2)
        r = t.row("group:SOV", ["of"])
        self.assertEqual((r["valid"], r["reordered"]), (3, 1))
        self.assertEqual(t.row("lang:ja", s.SHAPES)["valid"], 3)
        self.assertEqual(t.sov_sources[("%1$s of %2$s", "of")]["reordered"], 1)

    def full(self):
        t = s.Tally()
        data = [("ja", "Page %1$d of %2$d", 300, 100), ("ja", "%1$s: %2$s", 300, 3),
                ("ja", "Move %1$s to %2$s", 300, 60), ("ja", "%1$s sent you %2$s", 300, 30),
                ("fr", "Page %1$d of %2$d", 300, 3), ("fr", "%1$s: %2$s", 300, 0),
                ("fr", "Move %1$s to %2$s", 300, 3), ("fr", "%1$s sent you %2$s", 300, 3)]
        for lang, text, n, k in data:
            for r in rows(lang, text, n, k):
                t.add(r)
        return t

    def test_predictions_all_held(self):
        preds = s.predictions(self.full())
        self.assertEqual([p[0] for p in preds], ["S1", "S2", "S3", "S4", "S5", "S6"])
        self.assertEqual([s.verdict(p[2]) for p in preds], ["HELD"] * 6)
        self.assertAlmostEqual(preds[5][3]["share"], 160 / 193)

    def test_predictions_not_testable(self):
        t = s.Tally()
        for r in rows("ja", "Page %1$d of %2$d", 50, 10) + rows("fr", "%1$s: %2$s", 50, 0):
            t.add(r)
        preds = s.predictions(t)
        self.assertEqual([s.verdict(p[2]) for p in preds], ["NOT TESTABLE"] * 6)

    def test_write(self):
        with tempfile.TemporaryDirectory() as d:
            checks = [{"text": x, "want": w, "got": w} for x, w in s.KNOWN]
            s.write(d, self.full(), {"index_url": "x", "finished": "y", "repos_scanned": 20}, True, checks)
            for name in ("shape.md", "shape.json", "by_language.csv", "top_sources.csv"):
                self.assertTrue(os.path.exists(os.path.join(d, name)), name)
            with open(os.path.join(d, "shape.md"), encoding="utf-8") as f:
                md = f.read()
            self.assertIn("S1 HELD", md)
            self.assertIn("ratio other 10.00x", md)
            self.assertIn("`Page %1$d of %2$d` | of | 300 | 100 | 10 |", md)


if __name__ == "__main__":
    unittest.main()
