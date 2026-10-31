# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for zwsp_langs.py (no network, no git)."""
import os
import shutil
import tempfile
import unittest

import zwsp_langs as zl

Z = chr(0x200B)


class ShapeTest(unittest.TestCase):
    def test_pair_context(self):
        self.assertEqual(zl.pair_context("EXIF " + Z + Z + "ข้อมูล"), (True, "EXIF"))
        self.assertEqual(zl.pair_context("ก " + Z + Z + "ข"), (False, "ก"))
        self.assertEqual(zl.pair_context(" " + Z + Z + "a"), (False, ""))
        self.assertIsNone(zl.pair_context("a " + Z + "b"))
        self.assertIsNone(zl.pair_context("a " + Z + Z + Z + "b"))
        self.assertIsNone(zl.pair_context("a " + Z + Z + "1"))

    def test_count_unit(self):
        c = zl.new_counts()
        zl.count_unit(c, "a " + Z + Z + "b")
        self.assertEqual(c, [1, 1, 0, 1])
        zl.count_unit(c, "a " + Z + "b")
        self.assertEqual(c, [2, 1, 1, 2])
        zl.count_unit(c, "ก" + Z + "ข")
        self.assertEqual(c, [3, 1, 1, 3])
        zl.count_unit(c, "plain")
        self.assertEqual(c, [4, 1, 1, 3])

    def test_locale_of(self):
        self.assertEqual(zl.locale_of("values-th"), "th")
        self.assertEqual(zl.locale_of("values-b+my"), "my")
        self.assertEqual(zl.locale_of("values-km-rKH"), "km")
        self.assertIsNone(zl.locale_of("values-en-rXA"))
        self.assertIsNone(zl.locale_of("values"))
        self.assertIsNone(zl.locale_of("values-night"))


def write(path, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(('<?xml version="1.0" encoding="utf-8"?>\n<resources>' + body + "</resources>").encode("utf-8"))


class ScanTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        res = os.path.join(self.root, "app", "src", "main", "res")
        write(os.path.join(res, "values", "strings.xml"),
              '<string name="a">EXIF data</string><string name="b">Hello world</string>'
              '<string name="c">Has ' + Z + ' zw</string><string name="d" translatable="false">X</string>')
        write(os.path.join(res, "values-th", "strings.xml"),
              '<string name="a">EXIF ' + Z + Z + 'ข้อมูล</string><string name="b">ก' + Z + 'ข</string>'
              '<string name="c">anything ' + Z + Z + 'x</string>')
        write(os.path.join(res, "values-de", "strings.xml"),
              '<string name="a">EXIF ' + Z + Z + 'Daten</string><string name="b">Hallo Welt</string>')
        write(os.path.join(res, "values-en-rXA", "strings.xml"), '<string name="a">x ' + Z + Z + 'y</string>')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_scan(self):
        out = zl.scan_checkout(self.root)
        self.assertEqual(out["Z"], [2, 1, 0, 2])
        self.assertEqual(out["N"], [2, 1, 0, 1])
        self.assertEqual(out["langs"], {"th": [2, 1, 0, 2]})
        self.assertEqual(len(out["rows"]), 1)
        row = out["rows"][0]
        self.assertEqual((row["res_dir"], row["locale_dir"], row["lang"], row["key"], row["index"]),
                         ("app/src/main/res", "values-th", "th", "string:a", 0))
        self.assertEqual((row["latin_before"], row["word_before"]), (1, "EXIF"))
        self.assertEqual(row["source"], "EXIF data")
        self.assertEqual(row["target"], "EXIF <U+200B><U+200B>ข้อมูล")


def stats(z, n, z_repos=60, z_pair_repos=3, z_latin=(10, 5)):
    return {"Z": list(z), "N": list(n), "z_repos": z_repos, "z_pair_repos": z_pair_repos, "z_latin": list(z_latin)}


class GradeTest(unittest.TestCase):
    def test_gate(self):
        g = zl.grade(stats([9999, 10, 0, 0], [10 ** 6, 40, 0, 0]))
        self.assertEqual(g, {p: "NOT TESTABLE (gate)" for p in ("P1", "P2", "P3")})
        g = zl.grade(stats([20000, 10, 0, 0], [10 ** 6, 40, 0, 0], z_repos=49))
        self.assertEqual(g["P1"], "NOT TESTABLE (gate)")

    def test_all_held(self):
        g = zl.grade(stats([20000, 10, 0, 0], [10 ** 6, 40, 0, 0]))
        self.assertEqual(g, {"P1": "HELD", "P2": "HELD", "P3": "HELD"})

    def test_boundaries(self):
        # 4/20000 against 400/1e6: exactly half -> P2 HELD. 401/1e6 -> FAILED.
        g = zl.grade(stats([20000, 4, 0, 0], [10 ** 6, 400, 0, 0], z_pair_repos=4, z_latin=(4, 1)))
        self.assertEqual(g, {"P1": "FAILED", "P2": "HELD", "P3": "FAILED"})
        g = zl.grade(stats([20000, 4, 0, 0], [10 ** 6, 401, 0, 0], z_pair_repos=4, z_latin=(4, 2)))
        self.assertEqual(g, {"P1": "FAILED", "P2": "FAILED", "P3": "HELD"})
        g = zl.grade(stats([20000, 10, 0, 0], [10 ** 6, 40, 0, 0], z_pair_repos=2))
        self.assertEqual(g["P1"], "FAILED")

    def test_not_testable(self):
        g = zl.grade(stats([20000, 0, 0, 0], [10 ** 6, 0, 0, 0], z_pair_repos=0, z_latin=(0, 0)))
        self.assertEqual(g, {"P1": "FAILED", "P2": "NOT TESTABLE", "P3": "NOT TESTABLE"})


class AggregateTest(unittest.TestCase):
    def test_aggregate(self):
        results = [
            {"repo": "r1", "status": "ok", "Z": [100, 2, 1, 50], "N": [1000, 1, 0, 1],
             "langs": {"th": [100, 2, 1, 50]},
             "rows": [{"latin_before": 1, "word_before": "EXIF"}, {"latin_before": 0, "word_before": "ก"}]},
            {"repo": "r2", "status": "ok", "Z": [0, 0, 0, 0], "N": [500, 0, 0, 0], "langs": {}, "rows": []},
            {"repo": "r3", "status": "clone-failed"},
        ]
        s = zl.aggregate(results)
        self.assertEqual(s["repos_ok"], 2)
        self.assertEqual((s["Z"]["units"], s["Z"]["pair"], s["Z"]["single_after_space"], s["Z"]["any_zwsp"]),
                         (100, 2, 1, 50))
        self.assertEqual((s["N"]["units"], s["N"]["pair"]), (1500, 1))
        self.assertEqual((s["z_repos"], s["z_pair_repos"], s["z_pairs_latin_before"]), (1, 1, 1))
        self.assertEqual(s["exploratory_pair_repos"], {"r1": [100, 2]})
        self.assertEqual(s["exploratory_word_before"], [["EXIF", 1], ["ก", 1]])
        self.assertEqual(s["exploratory_langs"]["th"]["units"], 100)
        self.assertAlmostEqual(s["ratio_Z_over_N"], 30.0, places=4)
        self.assertEqual(s["verdicts"]["P1"], "NOT TESTABLE (gate)")


if __name__ == "__main__":
    unittest.main()
