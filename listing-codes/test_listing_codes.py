# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Tests for listing_codes.py (standard library only). Made with AI agents by MV2 of Munim, Inc."""
import unittest

import listing_codes as lc


def _rec(typ, subtag, extra=""):
    return "%%%%\nType: %s\nSubtag: %s\nDescription: x\n%sAdded: 2005-10-16\n" % (typ, subtag, extra)


MINI = "File-Date: 2026-01-01\n" + "".join(
    [_rec("language", s) for s in ("en", "zh", "pt", "kr", "fil", "ckb", "sr", "ja", "de", "es",
                                    "cs", "uk")]
    + [_rec("language", "iw", "Deprecated: 1989-01-01\nPreferred-Value: he\n"),
       _rec("language", "qaa..qtz"), _rec("extlang", "yue"),
       _rec("script", "Hans"), _rec("script", "Hant"), _rec("script", "Latn"),
       _rec("region", "US"), _rec("region", "CN"), _rec("region", "BR"), _rec("region", "IL"),
       _rec("region", "419"), _rec("region", "CH"), _rec("variant", "1996"),
       "%%\nType: grandfathered\nTag: i-klingon\nDescription: Klingon\n  (continued line)\n"
       "Added: 1999-05-26\n",
       "%%\nType: redundant\nTag: zh-Hans\nDescription: simplified Chinese\nAdded: 2005-04-26\n"])


class RegistryTest(unittest.TestCase):
    def setUp(self):
        self.reg = lc.Registry(MINI)

    def test_parse(self):
        self.assertEqual(self.reg.date, "2026-01-01")
        self.assertEqual(self.reg.count("language"), 14)
        self.assertTrue(self.reg.has("language", "IW"))
        self.assertTrue(self.reg.has("language", "qab"))
        self.assertFalse(self.reg.has("language", "qa"))
        self.assertFalse(self.reg.has("language", "jp"))
        self.assertTrue(self.reg.has("region", "419"))
        self.assertIn("i-klingon", self.reg.tags)

    def test_control_list(self):
        ok, got = lc.control(self.reg)
        self.assertTrue(ok, got)

    def test_more_classes(self):
        for key, want in (("qab", "valid"), ("zh-yue", "valid"), ("i-klingon", "valid"),
                          ("x-foo", "valid"), ("en-US ", "malformed"), ("", "malformed"),
                          ("values-ja", "unregistered-language"), ("pt-rBR", "android-r"),
                          ("b+zh+Hans", "android-r"), ("zh_CN", "underscore"),
                          ("en_UK", "malformed"), ("jp_JP", "malformed"),
                          ("pt-br", "valid"), ("zh-Hans", "valid"), ("cz", "unregistered-language")):
            self.assertEqual(lc.classify(key, self.reg), want, key)

    def test_language_of(self):
        self.assertEqual(lc.language_of("zh-rCN"), "zh")
        self.assertEqual(lc.language_of("b+sr+Latn"), "sr")
        self.assertEqual(lc.language_of("pt_BR"), "pt")
        self.assertEqual(lc.language_of("JP"), "jp")

    def test_canonical_case(self):
        self.assertTrue(lc.canonical_case("zh-Hans-CN"))
        self.assertTrue(lc.canonical_case("es-419"))
        self.assertFalse(lc.canonical_case("pt-br"))
        self.assertFalse(lc.canonical_case("EN"))


INDEX = {"repo": {"timestamp": 1},
         "packages": {
             "a.one": {"metadata": {"name": {"en-US": "One"},
                                    "description": {"en-US": "Hello", "jp": "こんにちは"}}},
             "b.two": {"metadata": {"summary": {"en-US": "S", "zh-rCN": "简介", "zh-CN": "简介"}}},
             "c.three": {"metadata": {"description": {"pt_BR": "Olá"}}},
             "d.four": {"metadata": {"screenshots": {"phone": {"en-US": ["a.png"],
                                                               "ja-JA": ["b.png"]}}},
                        "versions": {"v1": {"whatsNew": {"en-US": "fix", "cz": "oprava"}}}},
             "e.five": {"metadata": {"name": {"en-US": "E", "de": "E"}}},
         }}


class ScanTest(unittest.TestCase):
    def setUp(self):
        self.reg = lc.Registry(MINI)
        self.rows, self.key_pkgs, self.stats, _ = lc.scan_index(INDEX, self.reg)

    def test_rows(self):
        got = {(r["package"], r["key"], r["class"], r["meant"], r["meant_has_valid_key"],
                r["reach"], r["fields"]) for r in self.rows}
        self.assertEqual(got, {
            ("a.one", "jp", "unregistered-language", "ja", "no", "fallback-en", "description"),
            ("b.two", "zh-rCN", "android-r", "zh", "yes", "fallback-en", "summary"),
            ("c.three", "pt_BR", "underscore", "pt", "no", "only-key", "description"),
            ("d.four", "ja-JA", "unregistered-subtag", "", "", "fallback-en", "screenshots.phone"),
            ("d.four", "cz", "unregistered-language", "cs", "no", "fallback-en", "whatsNew"),
        })

    def test_texts(self):
        by = {(r["package"], r["key"]): r for r in self.rows}
        self.assertEqual(by[("a.one", "jp")]["text"], "こんにちは")
        self.assertEqual(by[("a.one", "jp")]["en_text"], "Hello")
        self.assertEqual(by[("d.four", "cz")]["text"], "oprava")
        self.assertEqual(by[("d.four", "cz")]["text_field"], "whatsNew")
        self.assertEqual(by[("b.two", "zh-rCN")]["same_as_en"], "no")

    def test_stats(self):
        self.assertEqual(self.stats["packages"], 5)
        self.assertEqual(self.stats["packages_localized"], 5)
        self.assertEqual(self.key_pkgs["en-US"], 4)
        self.assertEqual(lc.class_packages(self.rows),
                         {"android-r": 1, "underscore": 1, "unregistered-language": 2,
                          "unregistered-subtag": 1, "malformed": 0})
        self.assertEqual(lc.k3_counts(self.rows), (2, 2))

    def test_sample(self):
        s = lc.draw_sample(self.rows)
        self.assertEqual(len(s), 4)  # one per package, ja-JA's package via cz, no subtag rows
        self.assertEqual(len({r["package"] for r in s}), 4)
        self.assertNotIn("unregistered-subtag", {r["class"] for r in s})
        self.assertEqual(s, lc.draw_sample(list(reversed(self.rows))))


def _rows(cls, n, start=0, meant="", lost=0):
    return [{"package": "p%d" % (start + i), "class": cls, "meant": meant,
             "meant_has_valid_key": ("no" if i < lost else "yes") if meant else ""}
            for i in range(n)]


class GradeTest(unittest.TestCase):
    def test_all_held(self):
        rows = _rows("unregistered-language", 20, 0, "ja", lost=12) + _rows("android-r", 25, 100)
        v = lc.grade(3000, 8000, rows)
        self.assertEqual(v, {"K1": "HELD", "K2": "HELD", "K3": "HELD", "K4": "HELD"})

    def test_gate(self):
        v = lc.grade(2999, 8000, [])
        self.assertTrue(all(x.startswith("NOT TESTABLE") for x in v.values()))
        v = lc.grade(3000, 7999, [])
        self.assertTrue(all(x.startswith("NOT TESTABLE") for x in v.values()))

    def test_failures(self):
        rows = _rows("unregistered-language", 20, 0, "ja", lost=9) + _rows("android-r", 20, 100)
        v = lc.grade(3000, 8000, rows)
        self.assertEqual(v["K3"], "FAILED")   # 18 < 20
        self.assertEqual(v["K4"], "FAILED")   # tie is not "more"
        self.assertEqual(lc.grade(3000, 8000, _rows("android-r", 14))["K1"], "FAILED")
        self.assertEqual(lc.grade(3000, 8000, _rows("android-r", 15))["K1"], "HELD")
        self.assertEqual(lc.grade(3000, 8000, _rows("android-r", 180))["K1"], "HELD")
        self.assertEqual(lc.grade(3000, 8000, _rows("android-r", 181))["K1"], "FAILED")
        self.assertEqual(lc.grade(3000, 8000, _rows("unregistered-language", 7))["K2"], "FAILED")
        self.assertEqual(lc.grade(3000, 8000, _rows("unregistered-language", 3, 0, "ja"))["K3"],
                         "NOT TESTABLE (3 packages)")
        self.assertEqual(lc.grade(3000, 8000, [])["K4"], "NOT TESTABLE (no invalid keys)")

    def test_h1(self):
        self.assertEqual(lc.grade_h1(["translation"] * 6 + ["english"] * 2), "HELD")
        self.assertEqual(lc.grade_h1(["translation"] * 5 + ["english"] * 3), "FAILED")
        self.assertEqual(lc.grade_h1(["translation"] * 7 + [""] * 5), "NOT TESTABLE")


if __name__ == "__main__":
    unittest.main()
