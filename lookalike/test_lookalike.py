# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Tests for lookalike.py. Made with AI agents by MV2 of Munim, Inc."""
import collections
import os
import shutil
import tempfile
import unittest

import lookalike as lk

A = chr(0x0430)    # Cyrillic a
DZE = chr(0x0455)  # Cyrillic dze, looks like s
I_UK = chr(0x0456)  # Ukrainian i

TGT = ('<resources>\n<string name="one">Привет</string>\n'
       '<string-array name="arr">\n<item>%1$' + DZE + '</item>\n</string-array>\n'
       '<string name="two"><![CDATA[по <a href="u">ссылке</' + A + '>]]></string>\n'
       '</resources>\n')
SRC = ('<resources>\n<string name="one">Hi</string>\n'
       '<string-array name="arr">\n<item>%1$s</item>\n</string-array>\n'
       '<string name="two"><![CDATA[at <a href="u">link</a>]]></string>\n'
       '</resources>\n')


class ControlTest(unittest.TestCase):
    def test_control(self):
        self.assertTrue(lk.control())

    def test_table(self):
        self.assertEqual(lk.CONFUSABLE[A], "a")
        self.assertEqual(lk.CONFUSABLE[DZE], "s")
        self.assertEqual(lk.CONFUSABLE[chr(0xFF53)], "s")
        self.assertEqual(lk.CONFUSABLE[chr(0xFF24)], "D")
        self.assertNotIn(chr(0x0431), lk.CONFUSABLE)  # Cyrillic be: no Latin look-alike


class LocaleTest(unittest.TestCase):
    def test_locale_of(self):
        self.assertIsNone(lk.locale_of("values"))
        self.assertEqual(lk.locale_of("values-ru"), "ru")
        self.assertEqual(lk.locale_of("values-ru-rRU"), "ru")
        self.assertEqual(lk.locale_of("values-zh-rTW"), "zh")
        self.assertEqual(lk.locale_of("values-b+sr+Latn"), "b+sr+Latn")
        for d in ("values-night", "values-v21", "values-car", "values-land", "values-sw600dp"):
            self.assertIsNone(lk.locale_of(d), d)


class ScanTest(unittest.TestCase):
    def test_ascii_counts(self):
        text = ('<string name="a">%1$s и %d</string>\n'
                '<string name="b"><![CDATA[<b>x</b>]]></string>')
        hits, counts = lk.scan_text(text)
        self.assertEqual(hits, [])
        self.assertEqual(counts["ascii_fmt"], 2)
        self.assertEqual(counts["ascii_tag"], 2)

    def test_hits_keys_and_source(self):
        hits, _ = lk.scan_text(TGT)
        self.assertEqual([(h["kind"], h["letters"], h["script"]) for h in hits],
                         [("fmt", DZE, "cyrillic"), ("tag", A, "cyrillic")])
        self.assertEqual(hits[0]["token"], "%1$" + DZE)
        self.assertEqual(hits[1]["token"], "</" + A)
        starts = lk.element_starts(TGT)
        self.assertEqual([k for _, k in starts],
                         ["string:one", "string-array:arr", "string:two"])
        self.assertEqual(lk.key_at(starts, hits[0]["pos"]), "string-array:arr")
        self.assertEqual(lk.key_at(starts, hits[1]["pos"]), "string:two")
        self.assertEqual(lk.key_at(starts, 0), "")
        self.assertEqual(lk.source_block(SRC, "string-array:arr"), "\n<item>%1$s</item>\n")
        self.assertEqual(lk.source_block(SRC, "string:two"),
                         '<![CDATA[at <a href="u">link</a>]]>')
        self.assertIsNone(lk.source_block(SRC, "string:missing"))
        self.assertTrue(lk.source_has(hits[0], lk.source_block(SRC, "string-array:arr")))
        self.assertTrue(lk.source_has(hits[1], lk.source_block(SRC, "string:two")))
        self.assertFalse(lk.source_has(hits[0], "Delete %1$d"))
        self.assertFalse(lk.source_has(hits[0], None))

    def test_script(self):
        self.assertEqual(lk.script(A), "cyrillic")
        self.assertEqual(lk.script(chr(0x03BF)), "greek")
        self.assertEqual(lk.script(chr(0xFF53)), "fullwidth")
        self.assertEqual(lk.script("a"), "other")

    def test_scan_repo(self):
        root = tempfile.mkdtemp()
        try:
            res = os.path.join(root, "app", "res")
            for d, name, text in (("values", "strings.xml", SRC), ("values-ru", "strings.xml", TGT),
                                  ("values-night", "colors.xml", TGT)):
                os.makedirs(os.path.join(res, d), exist_ok=True)
                with open(os.path.join(res, d, name), "w", encoding="utf-8") as f:
                    f.write(text)
            counts, rows = lk.scan_repo(root)
            self.assertEqual(counts["locale_files"], 1)
            self.assertEqual(counts["hit_tag"], 1)
            self.assertEqual(counts["hit_fmt"], 1)
            self.assertEqual([(r["res_dir"], r["locale_dir"], r["key"], r["kind"],
                               r["source_has"]) for r in rows],
                             [("app/res", "values-ru", "string-array:arr", "fmt", True),
                              ("app/res", "values-ru", "string:two", "tag", True)])
            self.assertEqual(rows[1]["codepoints"], "U+0430")
        finally:
            shutil.rmtree(root, ignore_errors=True)


class GradeTest(unittest.TestCase):
    def test_grade(self):
        t = {"repos_read": 4693, "repos_any": 12, "repos_cyrillic": 7, "repos_tag": 9,
             "repos_fmt": 4}
        self.assertEqual(lk.grade(t), {"K1": "HELD", "K2": "HELD", "K3": "HELD",
                                       "K4": "PENDING (hand check of sample.csv)"})
        t2 = dict(t, repos_any=8, repos_cyrillic=4, repos_tag=2, repos_fmt=2)
        self.assertEqual(lk.grade(t2)["K1"], "FAILED")
        self.assertEqual(lk.grade(t2)["K2"], "FAILED")
        self.assertEqual(lk.grade(t2)["K3"], "FAILED")
        self.assertEqual(lk.grade(dict(t, repos_read=100))["K1"], "NOT TESTABLE (gate)")
        t3 = dict(t, repos_any=0, repos_cyrillic=0, repos_tag=0, repos_fmt=0)
        self.assertEqual(lk.grade(t3)["K1"], "FAILED")
        self.assertEqual(lk.grade(t3)["K2"], "NOT TESTABLE (no hits)")

    def test_grade_k4(self):
        self.assertEqual(lk.grade_k4(["defect"] * 6 + ["fine"] * 2), "HELD")
        self.assertEqual(lk.grade_k4(["defect"] * 5 + ["fine", "other", "fine"]), "FAILED")
        self.assertEqual(lk.grade_k4(["defect"] * 7), "NOT TESTABLE")

    def test_tables(self):
        C = collections.Counter
        results = [
            {"repo": "r1", "counts": C(locale_files=3, hit_tag=1),
             "rows": [{"script": "cyrillic", "source_has": True, "locale_dir": "values-ru"}]},
            {"repo": "r2", "counts": C(locale_files=2, hit_fmt=1, ascii_fmt=4),
             "rows": [{"script": "fullwidth", "source_has": False,
                       "locale_dir": "values-zh-rTW"}]},
            {"repo": "r3", "counts": C(), "rows": []},
        ]
        t = lk.tables(results)
        self.assertEqual((t["repos_read"], t["repos_locale"], t["locale_files"], t["ascii_fmt"]),
                         (3, 2, 5, 4))
        self.assertEqual((t["repos_tag"], t["repos_fmt"], t["repos_any"], t["repos_cyrillic"]),
                         (1, 1, 2, 1))
        self.assertEqual(t["hits_source_has"], 1)
        self.assertEqual(t["hits_by_locale"], {"ru": 1, "zh": 1})
        self.assertEqual(t["hits_by_script"], {"cyrillic": 1, "fullwidth": 1})

    def test_draw_sample(self):
        def row(repo, key):
            return {"repo": repo, "res_dir": "res", "locale_dir": "values-ru",
                    "file": "strings.xml", "key": key, "index": 0}
        rows = [row("r1", "string:a"), row("r1", "string:b"), row("r2", "string:a")]
        s = lk.draw_sample(rows)
        self.assertEqual(sorted(x["repo"] for x in s), ["r1", "r2"])
        self.assertEqual(s, lk.draw_sample(list(reversed(rows))))
        self.assertEqual(len(lk.draw_sample(rows, size=1)), 1)


if __name__ == "__main__":
    unittest.main()
