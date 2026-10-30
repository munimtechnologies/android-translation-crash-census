# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Tests for exif_pair.py (hand-traced expected values). Made with AI agents."""
import os
import shutil
import tempfile
import unittest

import exif_pair as ep

Z = chr(0x200B)


class Words(unittest.TestCase):
    def test_caps_words(self):
        self.assertEqual(ep.words("Write EXIF tag and GPS data"), {"EXIF", "GPS"})
        self.assertEqual(ep.words("Use the API."), set())
        self.assertEqual(ep.words("EXIFTOOL x"), set())
        self.assertEqual(ep.words("ABCDEF x"), set())
        self.assertEqual(ep.words("HTTPS proxy"), {"HTTPS"})
        self.assertEqual(ep.words("Remove Exif data"), {"Exif"})
        self.assertEqual(ep.words("Hello"), set())

    def test_sig_after(self):
        self.assertTrue(ep.sig_after("EXIF", "tag EXIF " + Z + Z + "UserComment"))
        self.assertFalse(ep.sig_after("EXIF", "tag EXIF " + Z + "UserComment"))
        self.assertFalse(ep.sig_after("EXIF", "tag EXIF " + Z + Z + Z + "UserComment"))
        self.assertFalse(ep.sig_after("EXIF", "EXIF " + Z + Z + "1"))
        self.assertFalse(ep.sig_after("EXIF", "XEXIF " + Z + Z + "a"))
        self.assertTrue(ep.sig_after("URL", "URL " + Z + Z + "jetzt"))

    def test_unit_record(self):
        self.assertIsNone(ep.unit_record("Read EXIF" + Z + " data", "x"))
        self.assertIsNone(ep.unit_record("Hello", "Ciao"))
        rec = ep.unit_record("Read EXIF data", "Leggi EXIF " + Z + Z + "dati")
        self.assertEqual(rec, {"words": {"EXIF": True}, "any_zwsp": True, "pair": True})

    def test_show(self):
        self.assertEqual(ep.show("a " + Z + Z + "b\nc"), "a <U+200B><U+200B>b\\nc")


class Units(unittest.TestCase):
    def test_units_like_census(self):
        source = {"string:a": ["Read EXIF data"], "array:b": ["One", "Two EXIF x"], "string:c": ["  "]}
        target = {"string:a": ["X"], "array:b": ["Uno", "Dos"], "string:c": ["y"], "string:d": ["z"]}
        self.assertEqual(list(ep.units(source, target)), [
            ("string:a", 0, "Read EXIF data", "X"),
            ("array:b", 0, "One", "Uno"),
            ("array:b", 1, "Two EXIF x", "Dos"),
        ])


def _write(path, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("<resources>" + body + "</resources>")


class Scan(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        res = os.path.join(self.root, "app", "src", "main", "res")
        _write(os.path.join(res, "values", "strings.xml"),
               '<string name="a">Write EXIF tag</string><string name="b">Open URL now</string>'
               '<string name="c">Hello</string>'
               '<string name="d" translatable="false">EXIF data</string>')
        _write(os.path.join(res, "values-it", "strings.xml"),
               '<string name="a">Scrivi EXIF ' + Z + Z + 'tag</string><string name="b">Apri URL ora</string>'
               '<string name="c">Ciao</string><string name="d">EXIF ' + Z + Z + 'dati</string>')
        _write(os.path.join(res, "values-de", "strings.xml"),
               '<string name="a">EXIF-Tag schreiben</string>'
               '<string name="b">URL ' + Z + Z + 'jetzt öffnen</string>')
        _write(os.path.join(res, "values-th", "strings.xml"),
               '<string name="a">x EXIF ' + Z + Z + 'y</string>')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_scan(self):
        out = ep.scan_checkout(self.root)
        self.assertEqual(out["units"], 5)
        self.assertEqual(out["pair_units"], 2)
        self.assertEqual(out["tok"], {"EXIF": [2, 1, 1], "URL": [2, 1, 1]})
        self.assertEqual(out["control"], [2, 1])
        self.assertEqual([(r["lang"], r["signature"]) for r in out["rows"]], [("de", 0), ("it", 1)])
        self.assertEqual(out["rows"][1]["target"], "Scrivi EXIF <U+200B><U+200B>tag")


class Grade(unittest.TestCase):
    def stats(self, repos=2500, exif=(1000, 20, 25)):
        return {"repos_with_units": repos,
                "tok": {"EXIF": list(exif), "GPS": [300, 1, 1], "PDF": [100, 5, 5]},
                "control": [50000, 10],
                "exif_repo": {"a": [100, 15], "b": [50, 5], "c": [850, 0]},
                "exif_lang": {"it": [40, 3], "de": [35, 0], "fr": [10, 1]}}

    def test_verdicts(self):
        self.assertEqual(ep.grade(self.stats()),
                         {"P1": "HELD", "P2": "HELD", "P3": "FAILED", "P4": "HELD", "P5": "HELD"})

    def test_gate(self):
        self.assertEqual(set(ep.grade(self.stats(repos=1500)).values()), {"NOT TESTABLE (gate)"})

    def test_too_few_exif_units(self):
        v = ep.grade(self.stats(exif=(50, 5, 5)))
        self.assertEqual(v, {"P1": "NOT TESTABLE", "P2": "NOT TESTABLE", "P3": "FAILED",
                             "P4": "NOT TESTABLE", "P5": "NOT TESTABLE"})


class Aggregate(unittest.TestCase):
    def test_counts(self):
        results = [
            {"repo": "r1", "status": "ok", "units": 10, "pair_units": 1, "control": [3, 0],
             "tok": {"EXIF": [2, 1, 1], "GPS": [3, 0, 0]},
             "rows": [{"word": "EXIF", "lang": "it", "signature": 1, "source": "Write EXIF tag"},
                      {"word": "EXIF", "lang": "de", "signature": 0, "source": "Write EXIF tag"}]},
            {"repo": "r2", "status": "ok", "units": 5, "pair_units": 0, "control": [0, 0],
             "tok": {"Exif": [1, 0, 0]},
             "rows": [{"word": "Exif", "lang": "fr", "signature": 0, "source": "Remove Exif data"}]},
            {"repo": "r3", "status": "clone-failed"},
        ]
        s = ep.aggregate(results)
        self.assertEqual(s["repos_with_units"], 2)
        self.assertEqual(s["units_non_zwsp_langs"], 15)
        self.assertEqual(s["pair_units_anywhere"], 1)
        self.assertEqual(s["exif"], {"units": 2, "signature": 1, "any_zwsp": 1, "rate": 0.5, "repos": 1,
                                     "repos_with_signature": 1, "langs": 2, "langs_with_signature": 1})
        self.assertEqual(s["control"], {"units": 3, "signature": 0, "rate": 0.0})
        self.assertIsNone(s["ratio_exif_over_control"])
        self.assertEqual(s["named"], {"GPS": {"units": 3, "signature": 0, "rate": 0.0}})
        self.assertEqual(s["affected_repos"], {"r1": [2, 1]})
        self.assertEqual(s["exploratory_mixed_Exif"]["units"], 1)
        self.assertEqual(s["exploratory_exif_next_word"], [["tag", 2, 1]])
        self.assertEqual(set(s["verdicts"].values()), {"NOT TESTABLE (gate)"})
        self.assertEqual(s["words_table"][0], ["GPS", 3, 0, 0, 1])


if __name__ == "__main__":
    unittest.main()
