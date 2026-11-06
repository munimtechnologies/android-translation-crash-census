# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Tests for locale_mismatch.py (no network). Made with AI agents by MV2 of Munim, Inc."""
import os
import shutil
import tempfile
import unittest

import locale_mismatch as lm


def pairs(texts, source="Open file"):
    return [(t, source, source) for t in texts]


class Control(unittest.TestCase):
    def test_control(self):
        self.assertTrue(lm.control())


class ParseDir(unittest.TestCase):
    def test_folders(self):
        self.assertEqual(lm.parse_dir("values-ru-rUA"), ("ru", "UA", None))
        self.assertEqual(lm.parse_dir("values-ua"), ("ua", None, None))
        self.assertEqual(lm.parse_dir("values-b+sr+Latn"), ("sr", None, "Latn"))
        self.assertEqual(lm.parse_dir("values-b+zh+Hans+CN"), ("zh", "CN", "Hans"))
        self.assertEqual(lm.parse_dir("values-b+es+419"), ("es", "419", None))
        self.assertEqual(lm.parse_dir("values-ckb"), ("ckb", None, None))
        for name in ("values", "values-night", "values-land", "values-v21", "values-car",
                     "values-en-rXA", "values-ar-rXB", "values-ru-rUA-v21", "values-sw600dp"):
            self.assertIsNone(lm.parse_dir(name), name)


class Codes(unittest.TestCase):
    def test_iso(self):
        self.assertEqual(len(lm.ISO639_1), 183)
        self.assertEqual(len(lm.EXPECT), 52)  # PREREG.md: 52 language codes
        for c in ("ua", "jp", "cn", "cz", "gr", "dk"):
            self.assertTrue(lm.not_a_language(c), c)
        for c in ("uk", "ja", "zh", "cs", "el", "da", "se", "si", "iw", "in", "ji"):
            self.assertFalse(lm.not_a_language(c), c)
        self.assertFalse(lm.not_a_language("fil"))  # three-letter codes are not checked


class Scripts(unittest.TestCase):
    def test_script_of(self):
        self.assertEqual(lm.scripts("Open 5 %s"), {"Latin"})
        self.assertEqual(lm.scripts("ファイル"), {"Kana"})
        self.assertEqual(lm.scripts("ー"), {"Kana"})
        self.assertEqual(lm.scripts("設定"), {"Han"})
        self.assertEqual(lm.scripts("설정"), {"Hangul"})
        self.assertEqual(lm.scripts("Настройки"), {"Cyrillic"})
        self.assertEqual(lm.scripts("ρυθμίσεις"), {"Greek"})
        self.assertEqual(lm.scripts("הגדרות"), {"Hebrew"})
        self.assertEqual(lm.scripts("الإعدادات"), {"Arabic"})
        self.assertEqual(lm.scripts("123 !? \U0001F600"), set())
        self.assertEqual(lm.scripts("\ud83d"), set())


class Metrics(unittest.TestCase):
    def test_identical_copies_skipped(self):
        m = lm.folder_metrics("ja", [("打开", "打开", "打开")])
        self.assertEqual(m["units"], 0)

    def test_source_scripts_subtracted(self):
        m = lm.folder_metrics("ko", [("언어: Русский", "Language: Русский", "Language: Русский")])
        self.assertEqual((m["units"], m["own"], dict(m["other"])), (1, 1, {}))

    def test_ja_thresholds(self):
        han = ["设置%d" % n for n in range(19)]
        m = lm.folder_metrics("ja", pairs(han))
        self.assertEqual(lm.classify("ja", None, m), [])          # 19 CJK strings: too few
        m = lm.folder_metrics("ja", pairs(han + ["设置x"]))
        self.assertEqual(lm.classify("ja", None, m), ["ja-no-kana"])
        m = lm.folder_metrics("ja", pairs(han + ["设置x", "ファイル1", "ファイル2"]))
        self.assertEqual((m["cjk"], m["kana"]), (22, 2))
        self.assertEqual(lm.classify("ja", None, m), ["ja-no-kana"])  # 20 < 22
        m = lm.folder_metrics("ja", pairs(han + ["设置x", "ファイル1", "ファイル2", "ファイル3"]))
        self.assertEqual(lm.classify("ja", None, m), [])          # 30 >= 23

    def test_zh_threshold(self):
        texts = ["设置%d" % n for n in range(15)] + ["ファイル%d" % n for n in range(5)]
        m = lm.folder_metrics("zh", pairs(texts))
        self.assertEqual(lm.classify("zh", None, m), ["zh-kana"])  # 5 * 4 >= 20
        m = lm.folder_metrics("zh", pairs(texts + ["设置x"]))
        self.assertEqual(lm.classify("zh", None, m), [])           # 20 < 21
        self.assertEqual(lm.classify("zh", "Hant", lm.folder_metrics("zh", pairs(texts))),
                         ["zh-kana"])

    def test_cyrillic_rule_needs_majority(self):
        uk = ["Відкрити %d" % n for n in range(10)]
        ru = ["Открыть %d" % n for n in range(10)]
        m = lm.folder_metrics("ru", pairs(uk + ru))
        self.assertEqual((m["cyr_a"], m["cyr_b"]), (10, 10))
        self.assertEqual(lm.classify("ru", None, m), [])
        m = lm.folder_metrics("ru", pairs(uk + ru[:9]))
        self.assertEqual(lm.classify("ru", None, m), ["cyrillic-letters"])
        m = lm.folder_metrics("be", pairs(["Выберите файл %d" % n for n in range(10)]))
        self.assertEqual((m["cyr_a"], m["cyr_b"]), (10, 0))
        self.assertEqual(lm.classify("be", None, m), ["cyrillic-letters"])

    def test_wrong_script_and_latin(self):
        m = lm.folder_metrics("ka", pairs(["Открыть %d" % n for n in range(10)]))
        self.assertEqual(lm.classify("ka", None, m), ["wrong-script:Cyrillic"])
        m = lm.folder_metrics("ka", pairs(["Открыть %d" % n for n in range(9)]))
        self.assertEqual(lm.classify("ka", None, m), [])
        m = lm.folder_metrics("si", pairs(["Odpri datoteko %d" % n for n in range(10)]))
        self.assertEqual(lm.classify("si", None, m), ["latin"])
        self.assertEqual(lm.examples(["latin"], m),
                         ["Odpri datoteko 0", "Odpri datoteko 1", "Odpri datoteko 2"])
        # a script subtag (sr-Latn) or a language without one script is not checked
        self.assertEqual(lm.classify("sr", "Latn", m), [])
        self.assertEqual(lm.classify("de", None, m), [])
        self.assertEqual(lm.classify("ua", None, m), ["not-a-language"])


class Refs(unittest.TestCase):
    def test_find_refs(self):
        d = tempfile.mkdtemp()
        try:
            def write(rel, text):
                p = os.path.join(d, *rel.split("/"))
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, "w", encoding="utf-8") as f:
                    f.write(text)
            write("app/src/main/java/A.java", 'Locale l = new Locale("ua_UA");\n')
            write("app/src/main/res/values/arrays.xml", "<item> cz </item>\n")
            write("app/src/main/res/values-gr/strings.xml", '<string name="gr">"gr"</string>\n')
            write("app/src/main/kotlin/B.kt", 'val s = "ruby"; val t = "jpg"\n')
            write("README.md", '"dk"\n')
            got = lm.find_refs(d, ["ua", "cz", "gr", "jp", "dk", "ru"])
            self.assertEqual(got, {"ua": True, "cz": True, "gr": False, "jp": False,
                                   "dk": False, "ru": False})
        finally:
            shutil.rmtree(d, ignore_errors=True)


class Grading(unittest.TestCase):
    def test_grade(self):
        v = lm.grade(3999, 9, 40, 9, 9)
        self.assertTrue(all(x.startswith("NOT TESTABLE (gate") for x in v.values()))
        self.assertEqual(lm.grade(4000, 5, 8, 5, 3),
                         {"L1": "HELD", "L2": "PENDING HAND CHECK (sample of 8)", "L3": "HELD",
                          "L4": "HELD"})
        self.assertEqual(lm.grade(4000, 4, 7, 4, 4),
                         {"L1": "FAILED", "L2": "NOT TESTABLE (sample of 7)", "L3": "FAILED",
                          "L4": "NOT TESTABLE (4 repositories)"})
        self.assertEqual(lm.grade(4000, 5, 8, 6, 2)["L4"], "FAILED")
        self.assertEqual(lm.grade(4000, 5, 8, 6, 3)["L4"], "HELD")

    def test_grade_l2(self):
        self.assertEqual(lm.grade_l2(["defect"] * 7), "NOT TESTABLE")
        self.assertEqual(lm.grade_l2(["defect"] * 6 + ["fine"] * 2), "HELD")
        self.assertEqual(lm.grade_l2(["defect"] * 5 + ["other"] * 3), "FAILED")

    def test_dead_and_sample(self):
        def row(repo, d, flags, ref=""):
            return {"repo": repo, "res_dir": "res", "locale_dir": d, "flags": flags,
                    "code_referenced": ref}
        rows = [row("a", "values-ua", "not-a-language", "no"),
                row("a", "values-jp", "not-a-language", "yes"),
                row("b", "values-cz", "not-a-language", "unknown"),
                row("c", "values-ja", "ja-no-kana"),
                row("c", "values-ko", "wrong-script:Cyrillic latin"),
                row("d", "values-ru-rUA", "cyrillic-letters")]
        l3, dead = lm.dead_repos(rows)
        self.assertEqual((l3, dead), ({"a", "b"}, {"a"}))
        s = lm.draw_sample(rows)
        self.assertEqual(sorted(x["repo"] for x in s), ["c", "d"])
        self.assertEqual(s, lm.draw_sample(list(reversed(rows))))


if __name__ == "__main__":
    unittest.main()
