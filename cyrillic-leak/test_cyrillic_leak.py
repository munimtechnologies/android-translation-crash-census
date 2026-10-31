#!/usr/bin/env python3
"""Tests for cyrillic_leak.py: the letter tables (by code point), the positive control, locale
folders, one res/ folder end to end, and the pre-registered grading. Standard library only.

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""
import os
import shutil
import tempfile
import unittest

import cyrillic_leak as c


def cps(s):
    return ["%04X" % ord(ch) for ch in s]


def xml(entries):
    return "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<resources>\n%s\n</resources>\n" % "\n".join(entries)


class LetterTableTest(unittest.TestCase):
    def test_foreign_code_points(self):
        self.assertEqual(cps(c.FOREIGN["uk"]), ["0451", "044B", "044D", "044A"])
        self.assertEqual(cps(c.FOREIGN["be"]), ["0438", "0449", "044A", "0454", "0457"])
        self.assertEqual(cps(c.FOREIGN["ru"]), ["0456", "0457", "0454", "0491", "045E"])
        self.assertEqual(cps(c.FOREIGN["bg"]), ["044B", "044D", "0451", "0456", "0457", "0454", "0491", "045E"])
        self.assertEqual(cps(c.FOREIGN["sr"]), ["0439", "0449", "044A", "044B", "044C", "044D", "044E",
                                                "044F", "0451", "0456", "0457", "0454", "0491", "045E"])
        self.assertEqual(cps(c.FOREIGN["mk"]), cps(c.FOREIGN["sr"]) + ["0452", "045B"])

    def test_native_code_points(self):
        self.assertEqual(cps(c.NATIVE["uk"]), ["0456", "0457", "0454", "0491"])
        self.assertEqual(cps(c.NATIVE["be"]), ["0456", "045E"])
        self.assertEqual(cps(c.NATIVE["sr"]), ["0452", "0458", "0459", "045A", "045B", "045F"])
        self.assertEqual(cps(c.NATIVE["mk"]), ["0453", "045C", "0455", "0458", "0459", "045A", "045F"])

    def test_no_letter_is_both_foreign_and_native(self):
        for lang in c.LANGS:
            self.assertFalse(set(c.FOREIGN[lang]) & set(c.NATIVE[lang]), lang)
            for ch in c.FOREIGN[lang] + c.NATIVE[lang]:
                self.assertTrue(c.CYR.match(ch), (lang, ch))

    def test_cyrillic_block(self):
        self.assertTrue(c.CYR.search("abc " + chr(0x0400)))
        self.assertTrue(c.CYR.search(chr(0x04FF)))
        self.assertFalse(c.CYR.search("Hello %1$s " + chr(0x0500) + chr(0x03A9)))


class DetectorTest(unittest.TestCase):
    def test_positive_control(self):
        self.assertTrue(c.control())

    def test_upper_case_and_composed(self):
        self.assertEqual(c.foreign_letters("uk", "ЭКСПОРТ", "Export"), [chr(0x044D)])
        # е + combining diaeresis is ё after NFC
        self.assertEqual(c.foreign_letters("uk", "Вс" + chr(0x0435) + chr(0x0308), "All"), [chr(0x0451)])

    def test_latin_i_is_not_cyrillic_i(self):
        self.assertEqual(c.foreign_letters("ru", "Wi-Fi включен", "Wi-Fi on"), [])

    def test_several_letters_sorted(self):
        self.assertEqual(c.foreign_letters("uk", "Съёмка экрана", "Screen capture"),
                         sorted([chr(0x044A), chr(0x0451), chr(0x044D)]))

    def test_native(self):
        self.assertTrue(c.has_native("uk", "Відкрити ы"))
        self.assertFalse(c.has_native("uk", "Открыть"))
        self.assertFalse(c.has_native("ru", "Открыть"))


class LocaleTest(unittest.TestCase):
    def test_folders(self):
        self.assertEqual(c.cyrillic_lang("values-uk"), "uk")
        self.assertEqual(c.cyrillic_lang("values-uk-rUA"), "uk")
        self.assertEqual(c.cyrillic_lang("values-b+be"), "be")
        self.assertEqual(c.cyrillic_lang("values-sr"), "sr")
        self.assertIsNone(c.cyrillic_lang("values-b+sr+Latn"))
        self.assertIsNone(c.cyrillic_lang("values-de"))
        self.assertIsNone(c.cyrillic_lang("values-night"))
        self.assertIsNone(c.cyrillic_lang("values"))


class ResDirTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.res = os.path.join(self.tmp, "app", "src", "main", "res")
        files = {
            "values": [
                '<string name="open">Open</string>',
                '<string name="save">Save</string>',
                '<string name="name" translatable="false">App</string>',
                '<string name="choose">Choose a file</string>',
                '<plurals name="files"><item quantity="one">%d file</item><item quantity="other">%d files</item></plurals>',
                '<string name="wifi">Wi-Fi</string>',
            ],
            "values-ru": [
                '<string name="open">Открыть</string>',
                '<string name="save">Сохранить</string>',
                '<string name="choose">Выберите файл</string>',
                '<plurals name="files"><item quantity="one">%d файл</item><item quantity="other">%d файлов</item></plurals>',
            ],
            "values-uk": [
                '<string name="open">Відкрити</string>',
                '<string name="save">Зберегти</string>',
                '<string name="name">Програма</string>',
                '<string name="choose">Выберите файл</string>',
                '<plurals name="files"><item quantity="one">%d файл</item><item quantity="other">%d файлiв ы</item></plurals>',
                '<string name="wifi">Wi-Fi</string>',
            ],
            "values-b+sr+Latn": ['<string name="open">Otvori</string>'],
            "values-be": ['<string name="open">Открыть</string>', '<string name="save">Захаваць</string>'],
        }
        for d, entries in files.items():
            os.makedirs(os.path.join(self.res, d))
            with open(os.path.join(self.res, d, "strings.xml"), "w", encoding="utf-8") as f:
                f.write(xml(entries))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_counts_and_rows(self):
        out = c.scan_strings(self.tmp)
        # uk: open, save, choose, files one, files other (name: not translatable; wifi: no Cyrillic)
        self.assertEqual(out["units"]["uk"], 5)
        self.assertEqual(out["units"]["ru"], 5)
        self.assertEqual(out["units"]["be"], 2)
        self.assertNotIn("sr", out["units"])
        self.assertEqual(out["flagged"]["uk"], 2)
        self.assertEqual(out["flagged"]["be"], 0)  # Открыть has no и, щ, ъ, є, ї
        self.assertEqual(out["flagged"].get("ru", 0), 0)
        rows = {(r["key"], r["index"]): r for r in out["rows"]}
        choose = rows[("string:choose", 0)]
        self.assertEqual(choose["letters"], chr(0x044B))
        self.assertTrue(choose["ru_available"])
        self.assertTrue(choose["ru_identical"])
        self.assertEqual(choose["same_as"], "ru")
        self.assertFalse(choose["native"])
        self.assertEqual(choose["res_dir"], "app/src/main/res")
        other = rows[("plurals:files", 1)]
        self.assertTrue(other["ru_available"])
        self.assertFalse(other["ru_identical"])
        self.assertEqual(out["parse_failed"], 0)

    def test_broken_file_is_counted(self):
        with open(os.path.join(self.res, "values-ru", "strings.xml"), "w", encoding="utf-8") as f:
            f.write("<resources><string name='open'>Открыть</resources>")
        out = c.scan_strings(self.tmp)
        self.assertEqual(out["parse_failed"], 1)
        self.assertEqual(out["units"]["uk"], 5)
        self.assertFalse(any(r["ru_available"] for r in out["rows"]))


def lang(units, repos, flagged, repos_flagged=0, ru_available=0, ru_identical=0):
    return {"units": units, "repos": repos, "flagged": flagged, "repos_flagged": repos_flagged,
            "ru_available": ru_available, "ru_identical": ru_identical}


class GradeTest(unittest.TestCase):
    def table(self, uk, be, ru):
        t = {k: lang(0, 0, 0) for k in c.LANGS}
        t.update(uk=uk, be=be, ru=ru)
        return t

    def test_gate(self):
        v = c.grade(self.table(lang(9999, 500, 10, 30), lang(20000, 50, 50), lang(50000, 500, 1)))
        self.assertEqual(set(v.values()), {"NOT TESTABLE (gate)"})
        v = c.grade(self.table(lang(10000, 29, 10, 30), lang(20000, 50, 50), lang(50000, 500, 1)))
        self.assertEqual(set(v.values()), {"NOT TESTABLE (gate)"})

    def test_all_held(self):
        v = c.grade(self.table(lang(100000, 800, 100, 20, 60, 30), lang(10000, 30, 11),
                               lang(200000, 900, 199)))
        self.assertEqual(v, {"P1": "HELD", "P2": "HELD", "P3": "HELD", "P4": "HELD"})

    def test_all_failed(self):
        v = c.grade(self.table(lang(100000, 800, 100, 19, 60, 29), lang(10000, 30, 10),
                               lang(200000, 900, 200)))
        self.assertEqual(v, {"P1": "FAILED", "P2": "FAILED", "P3": "FAILED", "P4": "FAILED"})

    def test_small_p2_and_ungated_others(self):
        v = c.grade(self.table(lang(100000, 800, 100, 25, 29, 29), lang(9000, 30, 500),
                               lang(200000, 29, 0)))
        self.assertEqual(v, {"P1": "HELD", "P2": "NOT TESTABLE", "P3": "NOT TESTABLE (gate)",
                             "P4": "NOT TESTABLE (gate)"})


class ParseTest(unittest.TestCase):
    def test_escapes_and_not_translatable(self):
        m = c.parse_values_text('<resources><string name="a">\\u0401\\u043b\\u043a\\u0430</string>'
                                '<string name="b" translatable="false">x</string></resources>')
        self.assertEqual(m["string:a"], [chr(0x0401) + chr(0x043B) + chr(0x043A) + chr(0x0430)])
        self.assertIsNone(m["string:b"])


if __name__ == "__main__":
    unittest.main()
