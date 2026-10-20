"""Offline tests for provenance_dropped.py (no network).

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import os
import unittest

import provenance_dropped as d

HERE = os.path.dirname(os.path.abspath(__file__))
B2_DATE = "2026-09-04T10:00:00Z"


def rows(cs, fi, hr, lt):
    """Rows shaped like dropped_rows.csv (cs 5, fi 3, hr 2, lt 2; 8 graded) with the given classes."""
    graded = {"cs": [True, True, True, False, False], "fi": [True, True, False],
              "hr": [True, False], "lt": [True, True]}
    out = []
    for locale, classes in (("cs", cs), ("fi", fi), ("hr", hr), ("lt", lt)):
        for flag, cls in zip(graded[locale], classes):
            out.append({"locale": locale, "graded": flag, "class": cls})
    return out


def held(rows_, b_date=B2_DATE):
    return {x["id"]: x["held"] for x in d.predictions(rows_, b_date)}


class InputsTest(unittest.TestCase):
    """The shipped dropped_rows.csv matches the pre-registration's counts."""

    def setUp(self):
        self.rows = d.read_rows(os.path.join(HERE, "dropped_rows.csv"))

    def test_counts(self):
        self.assertEqual(len(self.rows), 12)
        self.assertEqual(sum(r["graded"] for r in self.rows), 8)
        locales = [r["locale"] for r in self.rows]
        self.assertEqual([locales.count(x) for x in d.LOCALES], [5, 3, 2, 2])

    def test_hr_lt_rows_are_convert_permissions(self):
        for r in d.of(self.rows, ("hr", "lt")):
            self.assertIn(r["key1"], d.p.CONVERT_KEYS)
            self.assertIn(r["key2"], d.p.CONVERT_KEYS)


class PredictionsTest(unittest.TestCase):
    def test_all_inherited(self):
        r = rows(["INHERITED"] * 5, ["INHERITED"] * 3, ["INHERITED"] * 2, ["INHERITED"] * 2)
        self.assertEqual(held(r), {"S0": True, "S1": True, "S2": True, "S3": False})
        self.assertEqual(d.combined(r), 40)

    def test_edges(self):
        # cs 4 of 5 inherited (S2 edge), fi 2 of 3 not inherited (S3 edge), one hr row introduced (S1 fails).
        r = rows(["INHERITED"] * 4 + ["CHANGED"], ["INTRODUCED", "CHANGED", "INHERITED"],
                 ["INTRODUCED", "INHERITED"], ["INHERITED"] * 2)
        self.assertEqual(held(r), {"S0": True, "S1": False, "S2": True, "S3": True})
        # graded inherited: cs 3 + fi 0 + hr 0 + lt 2 = 5
        self.assertEqual(d.combined(r), 37)

    def test_s2_fails(self):
        r = rows(["INHERITED"] * 3 + ["INTRODUCED"] * 2, ["INHERITED"] * 3, ["INHERITED"] * 2, ["INHERITED"] * 2)
        self.assertFalse(held(r)["S2"])

    def test_s0_fails_not_tested(self):
        r = rows(["UNREADABLE"] + ["INHERITED"] * 4, ["INHERITED"] * 3, ["INHERITED"] * 2, ["INHERITED"] * 2)
        result = held(r)
        self.assertFalse(result["S0"])
        self.assertEqual([result[k] for k in ("S1", "S2", "S3")], [None, None, None])

    def test_s0_late_b2(self):
        r = rows(["INHERITED"] * 5, ["INHERITED"] * 3, ["INHERITED"] * 2, ["INHERITED"] * 2)
        self.assertFalse(held(r, "2026-09-05T00:00:01Z")["S0"])

    def test_s0_wrong_row_count(self):
        r = rows(["INHERITED"] * 5, ["INHERITED"] * 3, ["INHERITED"] * 2, ["INHERITED"] * 2)[:-1]
        self.assertFalse(held(r)["S0"])


if __name__ == "__main__":
    unittest.main()
