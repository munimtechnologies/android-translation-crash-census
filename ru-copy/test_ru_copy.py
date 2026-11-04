# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Tests for ru_copy.py (no network). Made with AI agents.

0.1.1 (DEVIATIONS.md): the fixture string "b" was "Настройки сохранены", which the 0.1.0 tests
wrongly took to be free of Russian-only letters (сохранены ends in ы). It is now "Удалить файл"."""
import collections
import fractions
import os
import shutil
import tempfile
import unittest

import ru_copy as r


def write(path, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n' + body + "</resources>\n")


class TestCopyKind(unittest.TestCase):
    def test_control(self):
        self.assertTrue(r.control())
        self.assertTrue(r.cl.control())
        self.assertEqual(r.cl.VERSION, "0.1.0")
        self.assertEqual(r.VERSION, "0.1.1")

    def test_gating_marks(self):
        self.assertTrue(r.PREREG_URL.endswith("ru-copy/PREREG.md"))
        self.assertTrue(r.DEVIATIONS_URL.endswith("ru-copy/DEVIATIONS.md"))
        self.assertEqual(r.PREREG_MARK, "ru-copy PREREG v1")
        self.assertEqual(r.DEVIATIONS_MARK, "ru-copy DEVIATION 1")

    def test_words(self):
        self.assertEqual(r.words("Ім'я користувача SSH"), ["Ім", "користувача"])
        self.assertEqual(r.words("Файл: %s"), ["Файл"])
        self.assertEqual(r.words("OK"), [])

    def test_kinds(self):
        k = r.copy_kind("uk", "Не удалось сохранить файл", "Не удалось сохранить файл", "Not saved")
        self.assertEqual(k, {"words": 4, "multi": True, "not_russian": False, "letters": ""})
        k = r.copy_kind("uk", "Не удалось открыть файл", "Не удалось открыть файл", "Not opened")
        self.assertEqual(k["letters"], "ы")
        k = r.copy_kind("uk", "Настройки сохранены", "Настройки сохранены", "Settings saved")
        self.assertEqual(k["letters"], "ы")                      # the 0.1.0 control's mistake
        k = r.copy_kind("uk", "Удалить файл", "Удалить файл", "Delete file")
        self.assertEqual(k["letters"], "")
        self.assertIsNone(r.copy_kind("uk", "Не вдалося", "Не удалось", "Failed"))
        k = r.copy_kind("uk", "Это файл", "Это файл", "This is a file")
        self.assertEqual(k["letters"], "э")
        k = r.copy_kind("uk", "Это файл", "Это файл", "Это")      # source has it: not counted
        self.assertEqual(k["letters"], "")
        k = r.copy_kind("be", "Выдаліць файл", "Выдаліць файл", "Delete file")
        self.assertTrue(k["not_russian"])

    def test_broken_control_detected(self):
        saved = r.NOT_RUSSIAN
        try:
            r.NOT_RUSSIAN = ""
            self.assertFalse(r.control())
        finally:
            r.NOT_RUSSIAN = saved

    def test_ru_folder(self):
        self.assertEqual(r.ru_folder(["values", "values-ru-rRU", "values-ru", "values-uk"]),
                         "values-ru")
        self.assertEqual(r.ru_folder(["values", "values-ru-rRU", "values-uk"]), "values-ru-rRU")
        self.assertIsNone(r.ru_folder(["values", "values-uk"]))

    def test_clean_text(self):
        self.assertEqual(r.clean_text("a" + chr(0xD83D) + chr(0xDE00)), "a" + chr(0x1F600))
        self.assertNotIn(chr(0xD83D), r.clean_text("a" + chr(0xD83D) + "b"))
        self.assertIsNone(r.clean_text(None))


class TestScan(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        res = os.path.join(self.root, "app", "src", "main", "res")
        write(os.path.join(res, "values", "strings.xml"),
              '<string name="a">Choose a file</string>\n'
              '<string name="b">Delete file</string>\n'
              '<string name="c">Server</string>\n'
              '<string name="d">Import key</string>\n'
              '<string name="e">Settings</string>\n'
              '<string name="f">Только русский</string>\n'
              '<string name="g">Not in Russian file</string>\n'
              '<string name="h" translatable="false">x</string>\n'
              '<plurals name="p"><item quantity="one">%d file</item>'
              '<item quantity="other">%d files</item></plurals>\n')
        write(os.path.join(res, "values-ru", "strings.xml"),
              '<string name="a">Выберите файл</string>\n'
              '<string name="b">Удалить файл</string>\n'
              '<string name="c">Сервер</string>\n'
              '<string name="d">Ключ імпорту</string>\n'
              '<string name="e">Настройки</string>\n'
              '<string name="f">Только русский</string>\n'
              '<string name="h">Нет</string>\n'
              '<plurals name="p"><item quantity="one">%d файл</item>'
              '<item quantity="other">%d файлов</item></plurals>\n')
        write(os.path.join(res, "values-uk", "strings.xml"),
              '<string name="a">Выберите файл</string>\n'
              '<string name="b">Удалить файл</string>\n'
              '<string name="c">Сервер</string>\n'
              '<string name="d">Ключ імпорту</string>\n'
              '<string name="e">Налаштування</string>\n'
              '<string name="f">Только русский</string>\n'
              '<string name="g">Не в російському файлі</string>\n'
              '<string name="h">Ні</string>\n'
              '<plurals name="p"><item quantity="one">%d файл</item>'
              '<item quantity="other">%d файлів</item></plurals>\n')
        write(os.path.join(res, "values-be", "strings.xml"),
              '<string name="b">Удалить файл</string>\n'
              '<string name="e">Налады</string>\n')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_scan(self):
        t = r.scan_strings(self.root)
        # uk units: a b c d e f g p1 p2 (h is not translatable) = 9
        self.assertEqual(t["units"]["uk"], 9)
        self.assertEqual(t["source_cyrillic"]["uk"], 1)          # f
        self.assertEqual(t["pairs"]["uk"], 7)                    # a b c d e p1 p2
        self.assertEqual(t["copies"]["uk"], 5)                   # a b c d p1
        self.assertEqual(t["multi"]["uk"], 3)                    # a b d
        self.assertEqual(t["not_russian"]["uk"], 1)              # d
        self.assertEqual(t["cand"]["uk"], 2)                     # a b
        self.assertEqual(t["cand_flagged"]["uk"], 1)             # a
        self.assertEqual(t["units"]["be"], 2)
        self.assertEqual(t["cand"]["be"], 1)
        self.assertEqual(t["cand_flagged"]["be"], 1)             # и
        rows = {(x["lang"], x["key"], x["index"]): x for x in t["rows"]}
        self.assertEqual(len(rows), 6)
        a = rows[("uk", "string:a", 0)]
        self.assertTrue(a["cand"])
        self.assertEqual(a["letters"], "ы")
        self.assertEqual(a["ru_dir"], "values-ru")
        self.assertEqual(a["res_dir"], "app/src/main/res")
        self.assertEqual(rows[("uk", "string:b", 0)]["letters"], "")
        self.assertEqual(rows[("be", "string:b", 0)]["letters"], "и")
        self.assertFalse(rows[("uk", "plurals:p", 0)]["multi"])
        self.assertFalse(rows[("uk", "string:d", 0)]["cand"])

    def test_no_russian_folder(self):
        shutil.rmtree(os.path.join(self.root, "app", "src", "main", "res", "values-ru"))
        t = r.scan_strings(self.root)
        self.assertEqual(t["units"]["uk"], 9)
        self.assertEqual(t["pairs"]["uk"], 0)
        self.assertEqual(t["rows"], [])


def repo(name, cand=0, flagged=0, pairs=1000, lang="uk"):
    c = collections.Counter
    return {"repo": name, "status": "ok", "pairs": c({lang: pairs}), "cand": c({lang: cand}),
            "cand_flagged": c({lang: flagged}), "units": c({lang: pairs})}


class TestGrading(unittest.TestCase):
    def table(self, results):
        t = r.tables(results)
        return t, {lang: r.recall_sum(results, lang) for lang in r.LANGS}

    def test_gate(self):
        t, s = self.table([repo("A%d" % i, pairs=1000) for i in range(99)])
        self.assertEqual(set(r.grade(t, s).values()), {"NOT TESTABLE (gate)"})
        t, s = self.table([repo("A%d" % i, pairs=400) for i in range(120)])   # 48,000 pairs
        self.assertEqual(set(r.grade(t, s).values()), {"NOT TESTABLE (gate)"})

    def test_r1_r2(self):
        base = [repo("A%d" % i) for i in range(100)]
        with_cand = [repo("C%d" % i, cand=2, flagged=1) for i in range(20)]
        t, s = self.table(base + with_cand)
        v = r.grade(t, s)
        self.assertEqual(v["R1"], "HELD")
        self.assertEqual(v["R2"], "FAILED")             # mean exactly 1/2 is not < 1/2
        self.assertEqual(v["R3"], "NOT TESTABLE")
        self.assertTrue(v["R4"].startswith("PENDING"))
        t, s = self.table(base + with_cand[:19] + [repo("Z", cand=3, flagged=1)])
        v = r.grade(t, s)
        self.assertEqual(v["R2"], "HELD")               # 19/2 + 1/3 < 10
        t, s = self.table(base + with_cand[:19])
        self.assertEqual(r.grade(t, s)["R1"], "FAILED")
        t, s = self.table(base + with_cand[:9])
        self.assertEqual(r.grade(t, s)["R2"], "NOT TESTABLE")

    def test_r3(self):
        base = [repo("A%d" % i) for i in range(100)]
        uk = [repo("C%d" % i, cand=4, flagged=1) for i in range(20)]       # mean 1/4
        be_hi = [repo("B%d" % i, cand=2, flagged=1, lang="be") for i in range(20)]
        be_lo = [repo("B%d" % i, cand=4, flagged=1, lang="be") for i in range(20)]
        t, s = self.table(base + uk + be_hi)
        self.assertEqual(r.grade(t, s)["R3"], "HELD")
        t, s = self.table(base + uk + be_lo)
        self.assertEqual(r.grade(t, s)["R3"], "FAILED")                    # equal is not more
        t, s = self.table(base + uk + be_hi[:9])
        self.assertEqual(r.grade(t, s)["R3"], "NOT TESTABLE")
        self.assertEqual(t["uk"]["recall_sum"], "5/1")
        self.assertEqual(t["uk"]["recall_repos"], 20)

    def test_r4(self):
        self.assertEqual(r.grade_r4(["russian"] * 30 + ["both"] * 10), "HELD")
        self.assertEqual(r.grade_r4(["russian"] * 29 + ["both"] * 11), "FAILED")
        self.assertEqual(r.grade_r4(["russian"] * 3), "NOT TESTABLE")


def row(repo_name, key, lang="uk", cand=True):
    return {"repo": repo_name, "res_dir": "res", "locale_dir": "values-uk", "file": "strings.xml",
            "key": key, "index": 0, "lang": lang, "cand": cand}


class TestSample(unittest.TestCase):
    def test_one_per_repo_fixed(self):
        rows = [row("R%d" % i, "k%d" % j) for i in range(60) for j in range(3)]
        rows += [row("BE", "x", lang="be"), row("NC", "x", cand=False)]
        s = r.draw_sample(rows)
        self.assertEqual(len(s), 40)
        self.assertEqual(len({x["repo"] for x in s}), 40)
        self.assertFalse({"BE", "NC"} & {x["repo"] for x in s})
        self.assertEqual(s, r.draw_sample(list(reversed(rows))))


if __name__ == "__main__":
    unittest.main()
