# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Tests for cyrillic_meta.py (made with AI agents by MV2 of Munim, Inc.)."""
import os
import shutil
import tempfile
import unittest

import cyrillic_meta as cm


class ListingLang(unittest.TestCase):
    def test_names(self):
        self.assertEqual(cm.listing_lang("uk"), "uk")
        self.assertEqual(cm.listing_lang("uk-UA"), "uk")
        self.assertEqual(cm.listing_lang("be_BY"), "be")
        self.assertEqual(cm.listing_lang("ru-RU"), "ru")
        self.assertEqual(cm.listing_lang("sr-Cyrl"), "sr")
        self.assertIsNone(cm.listing_lang("sr-Latn"))
        self.assertIsNone(cm.listing_lang("en-US"))
        self.assertIsNone(cm.listing_lang("zh-TW"))
        self.assertIsNone(cm.listing_lang("kk"))
        self.assertIsNone(cm.listing_lang("changelogs"))


class Control(unittest.TestCase):
    def test_control(self):
        self.assertTrue(cm.control())

    def test_play_listings_and_no_source(self):
        d = tempfile.mkdtemp()
        try:
            loc = os.path.join(d, "app", "src", "main", "play", "listings", "uk-UA")
            os.makedirs(loc)
            with open(os.path.join(loc, "full-description.txt"), "w", encoding="utf-8") as f:
                f.write("Это\n\n   \n")
            r = cm.scan_checkout(d)
            self.assertEqual(r["roots"], 1)
            self.assertEqual(dict(r["units"]), {"uk": 1})
            self.assertEqual(len(r["rows"]), 1)
            row = r["rows"][0]
            self.assertEqual(row["path"], "app/src/main/play/listings/uk-UA/full-description.txt")
            self.assertEqual(row["letters"], "э")
            self.assertEqual(row["kind"], "full_description")
            self.assertFalse(row["native"])
        finally:
            shutil.rmtree(d, ignore_errors=True)


class Sample(unittest.TestCase):
    def test_one_per_repo(self):
        rows = [{"repo": "a", "path": "p", "line": 1}, {"repo": "a", "path": "p", "line": 2},
                {"repo": "b", "path": "q", "line": 1}]
        s = cm.draw_sample(rows)
        self.assertEqual(sorted(x["repo"] for x in s), ["a", "b"])
        a_pick = [x for x in s if x["repo"] == "a"][0]
        want = min((1, 2), key=lambda n: cm.sample_key("a", "p", n))
        self.assertEqual(a_pick["line"], want)
        keys = [cm.sample_key(x["repo"], x["path"], x["line"]) for x in s]
        self.assertEqual(keys, sorted(keys))

    def test_cap(self):
        rows = [{"repo": "r%d" % i, "path": "p", "line": 1} for i in range(50)]
        self.assertEqual(len(cm.draw_sample(rows)), 40)


class Grades(unittest.TestCase):
    def test_c1(self):
        self.assertEqual(cm.grade_c1(["defect"] * 12 + ["fine"] * 3), "HELD")
        self.assertEqual(cm.grade_c1(["defect"] * 11 + ["fine"] * 4), "FAILED")
        self.assertEqual(cm.grade_c1(["defect"] * 14), "NOT TESTABLE")
        self.assertEqual(cm.grade_c1(["defect"] * 30 + ["other"] * 10), "HELD")
        self.assertEqual(cm.grade_c1(["defect"] * 29 + ["other"] * 11), "FAILED")

    def test_c2(self):
        uk = {"units": 2000, "repos": 50, "repos_flagged": 10, "flagged": 4}
        self.assertEqual(cm.grade_c2(uk), "HELD")
        self.assertEqual(cm.grade_c2(dict(uk, repos_flagged=9)), "FAILED")
        self.assertEqual(cm.grade_c2(dict(uk, units=1999)), "NOT TESTABLE (gate)")
        self.assertEqual(cm.grade_c2(dict(uk, repos=49)), "NOT TESTABLE (gate)")

    def test_c3(self):
        listing = {"r1": (5, 1), "r2": (5, 0), "r3": (0, 0), "r4": (3, 1), "r5": (2, 2)}
        strings = {"r1": (10, 2), "r2": (10, 0), "r3": (10, 1), "r4": (0, 0)}
        t = cm.c3_table(listing, strings)
        self.assertEqual(t, {"strings_flagged": {"repos": 1, "listing_flagged": 1},
                             "strings_clean": {"repos": 1, "listing_flagged": 0}})
        self.assertEqual(cm.grade_c3(t), "NOT TESTABLE")
        big = {"strings_flagged": {"repos": 10, "listing_flagged": 3},
               "strings_clean": {"repos": 20, "listing_flagged": 2}}
        self.assertEqual(cm.grade_c3(big), "HELD")
        same = {"strings_flagged": {"repos": 10, "listing_flagged": 1},
                "strings_clean": {"repos": 20, "listing_flagged": 2}}
        self.assertEqual(cm.grade_c3(same), "FAILED")

    def test_c4(self):
        uk = {"units": 2000, "repos": 50, "repos_flagged": 10, "flagged": 4}
        be = {"units": 300, "repos": 10, "flagged": 1}
        self.assertEqual(cm.grade_c4(uk, be), "HELD")
        self.assertEqual(cm.grade_c4(uk, dict(be, flagged=0)), "FAILED")
        self.assertEqual(cm.grade_c4(uk, dict(be, repos=9)), "NOT TESTABLE (gate)")
        self.assertEqual(cm.grade_c4(dict(uk, units=10), be), "NOT TESTABLE (gate)")


if __name__ == "__main__":
    unittest.main()
