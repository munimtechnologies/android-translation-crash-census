"""Offline tests for provenance.py (no network).

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import os
import unittest

import provenance as p

HERE = os.path.dirname(os.path.abspath(__file__))
ROW = {"locale": "it", "key1": "channel_header.delete", "key2": "channel_header.unarchive"}
EN_B = {"channel_header.delete": "Archive Channel", "channel_header.unarchive": "Unarchive Channel"}
AT_T = {"channel_header.delete": "Archivia Canale", "channel_header.unarchive": "Archivia Canale"}


class UnwrapTest(unittest.TestCase):
    def test_flat_and_descriptor(self):
        data = {"a": "Mute", "b": {"defaultMessage": "Unmute", "description": "menu"}, "c": {"x": 1}, "d": 3}
        self.assertEqual(p.unwrap(data), {"a": "Mute", "b": "Unmute"})


class StateTest(unittest.TestCase):
    def test_states(self):
        self.assertEqual(p.state(None, "Mute"), "missing")
        self.assertEqual(p.state("  ", "Mute"), "empty")
        self.assertEqual(p.state("Mute", "Mute"), "english")
        self.assertEqual(p.state("Silenzia", "Mute"), "translated")
        self.assertEqual(p.state("Silenzia", None), "translated")


class ClassifyTest(unittest.TestCase):
    def test_inherited(self):
        self.assertEqual(p.classify(ROW, AT_T, dict(AT_T), EN_B)[0], "INHERITED")

    def test_introduced_missing(self):
        at_b = {"channel_header.delete": "Archivia Canale"}
        cls, detail = p.classify(ROW, AT_T, at_b, EN_B)
        self.assertEqual(cls, "INTRODUCED")
        self.assertEqual(detail, "key2 missing at B")

    def test_introduced_english(self):
        at_b = {"channel_header.delete": "Archivia Canale", "channel_header.unarchive": "Unarchive Channel"}
        self.assertEqual(p.classify(ROW, AT_T, at_b, EN_B), ("INTRODUCED", "key2 english at B"))

    def test_introduced_empty(self):
        at_b = {"channel_header.delete": "", "channel_header.unarchive": "Archivia Canale"}
        self.assertEqual(p.classify(ROW, AT_T, at_b, EN_B), ("INTRODUCED", "key1 empty at B"))

    def test_changed(self):
        at_b = {"channel_header.delete": "Archivia Canale", "channel_header.unarchive": "Ripristina Canale"}
        self.assertEqual(p.classify(ROW, AT_T, at_b, EN_B), ("CHANGED", "key2 changed after B"))

    def test_not_reproduced(self):
        at_t = {"channel_header.delete": "Archivia Canale", "channel_header.unarchive": "Ripristina Canale"}
        self.assertEqual(p.classify(ROW, at_t, AT_T, EN_B)[0], "NOT_REPRODUCED")

    def test_unreadable(self):
        self.assertEqual(p.classify(ROW, AT_T, None, EN_B)[0], "UNREADABLE")
        self.assertEqual(p.classify(ROW, None, AT_T, EN_B)[0], "UNREADABLE")
        self.assertEqual(p.classify(ROW, AT_T, AT_T, None)[0], "UNREADABLE")


class InputsTest(unittest.TestCase):
    """The shipped rows.csv and graded.csv match the pre-registration's counts."""

    def setUp(self):
        self.rows = p.read_csv(os.path.join(HERE, "rows.csv"))
        self.graded = p.read_csv(os.path.join(HERE, "graded.csv"))
        self.unmatched = p.mark(self.rows, self.graded)

    def test_counts(self):
        self.assertEqual(len(self.rows), 67)
        self.assertEqual(len(self.graded), 40)
        self.assertEqual(self.unmatched, [])
        self.assertEqual(sum(r["graded"] for r in self.rows), 40)
        self.assertEqual(sum(r["group_a"] for r in self.rows), 12)
        self.assertEqual(len({r["locale"] for r in self.rows}), 17)

    def test_group_a_locales(self):
        locales = sorted(r["locale"] for r in self.rows if r["group_a"])
        self.assertEqual(locales, ["bg", "hr", "ko", "ko", "ko", "lt", "lt", "pt-BR", "ro", "vi", "zh-TW", "zh-TW"])

    def test_no_duplicate_rows(self):
        self.assertEqual(len({p.pair(r) for r in self.rows}), 67)


class PredictionsTest(unittest.TestCase):
    def rows(self, classes, graded=40, group_a=12):
        out = []
        for i, cls in enumerate(classes):
            out.append({"class": cls, "graded": i < graded, "group_a": i < group_a})
        return out

    def test_all_inherited(self):
        preds = p.predictions(self.rows(["INHERITED"] * 67), "2026-09-30T12:00:00Z", [])
        self.assertEqual([x["held"] for x in preds], [True, True, True, True, True])

    def test_thresholds(self):
        # 34 of 40 graded inherited (R1 edge), 6 introduced (R3 fails), group_a all inherited;
        # all rows: 34 + 20 = 54 of 67 inherited, 54 * 5 = 270 >= 268 (R4 holds).
        classes = ["INHERITED"] * 12 + ["INTRODUCED"] * 6 + ["INHERITED"] * 22 + ["INHERITED"] * 20 + ["CHANGED"] * 7
        preds = {x["id"]: x["held"] for x in p.predictions(self.rows(classes), "2026-09-30T12:00:00Z", [])}
        self.assertEqual(preds, {"R0": True, "R1": True, "R2": True, "R3": False, "R4": True})

    def test_r4_edge(self):
        # 53 of 67: 265 < 268, fails.
        classes = ["INHERITED"] * 40 + ["INHERITED"] * 13 + ["CHANGED"] * 14
        preds = {x["id"]: x["held"] for x in p.predictions(self.rows(classes), "2026-09-30T12:00:00Z", [])}
        self.assertFalse(preds["R4"])

    def test_group_a_one_introduced(self):
        classes = ["INTRODUCED"] + ["INHERITED"] * 66
        preds = {x["id"]: x["held"] for x in p.predictions(self.rows(classes), "2026-09-30T12:00:00Z", [])}
        self.assertFalse(preds["R2"])
        self.assertTrue(preds["R3"])

    def test_r0_fails_not_tested(self):
        classes = ["UNREADABLE"] + ["INHERITED"] * 66
        preds = p.predictions(self.rows(classes), "2026-09-30T12:00:00Z", [])
        self.assertFalse(preds[0]["held"])
        self.assertEqual([x["held"] for x in preds[1:]], [None, None, None, None])

    def test_r0_late_b(self):
        preds = p.predictions(self.rows(["INHERITED"] * 67), "2026-10-01T09:00:00Z", [])
        self.assertFalse(preds[0]["held"])

    def test_r0_unmatched(self):
        preds = p.predictions(self.rows(["INHERITED"] * 67), "2026-09-30T12:00:00Z", [("ko", ["a", "b"])])
        self.assertFalse(preds[0]["held"])


if __name__ == "__main__":
    unittest.main()
