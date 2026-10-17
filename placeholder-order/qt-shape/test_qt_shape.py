"""Tests for qt_shape.py (run after fetch_code.py: python -m unittest -v test_qt_shape).

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import os
import shutil
import tempfile
import unittest

import qt_shape as q

TS = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="fa_IR" sourcelanguage="en">
<context>
    <name>Main</name>
    <message>
        <source>Page %1 of %2</source>
        <translation>Safhe %1 az %2</translation>
    </message>
    <message>
        <source>Open</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <source>Old</source>
        <translation type="vanished">Ghadimi</translation>
    </message>
    <message numerus="yes">
        <source>%n file(s)</source>
        <translation><numerusform>%n file</numerusform></translation>
    </message>
    <message>
        <source>Empty</source>
        <translation></translation>
    </message>
</context>
</TS>
"""


class Names(unittest.TestCase):
    def test_lang_code(self):
        self.assertEqual(q.lang_code("zh_CN"), "zh")
        self.assertEqual(q.lang_code("fa_IR"), "fa")
        self.assertEqual(q.lang_code("sr@latin"), "sr")
        self.assertEqual(q.lang_code("pt-BR"), "pt")
        self.assertEqual(q.lang_code("iw"), "he")
        self.assertEqual(q.lang_code(""), "")
        self.assertEqual(q.lang_code(None), "")

    def test_file_lang(self):
        self.assertEqual(q.file_lang("keepassxc_zh_CN.ts"), "zh")
        self.assertEqual(q.file_lang("client_fa.ts"), "fa")
        self.assertEqual(q.file_lang("bitcoin_sr@latin.ts"), "sr")
        self.assertEqual(q.file_lang("translations.ts"), "")

    def test_qt_own(self):
        self.assertTrue(q.QT_OWN_RE.match("qt_fa.ts"))
        self.assertTrue(q.QT_OWN_RE.match("qtbase_zh_CN.ts"))
        self.assertFalse(q.QT_OWN_RE.match("qterminal_fa.ts"))
        self.assertFalse(q.QT_OWN_RE.match("qbittorrent_fa.ts"))


class Strings(unittest.TestCase):
    def test_args(self):
        self.assertEqual([n for n, _ in q.qt_args("Page %1 of %2")], [1, 2])
        self.assertEqual([n for n, _ in q.qt_args("%L2 / %L1")], [2, 1])
        self.assertEqual([n for n, _ in q.qt_args("%12 files")], [12])
        self.assertEqual(q.qt_args("100% done"), [])

    def test_classify(self):
        self.assertEqual(q.classify("%1 of %2", "%2 zhong de %1"), ("of", True))
        self.assertEqual(q.classify("%1 of %2", "%1 / %2"), ("of", False))
        self.assertIsNone(q.classify("%1 of %2", "%1"))
        self.assertIsNone(q.classify("%1 of %2 in %3", "%1 %2 %3"))
        self.assertIsNone(q.classify("%1 of %1", "%1 %1"))
        self.assertEqual(q.classify("<b>%1</b> of <b>%2</b>", "<b>%2</b> de <b>%1</b>"), ("of", True))
        self.assertEqual(q.classify("Move %1 to %2", "%2 ni %1 wo idou"), ("adposition", True))
        self.assertEqual(q.classify("%2 sent %1", "%2 a envoye %1"), ("other", False))

    def test_known_shapes(self):
        for text, want in q.KNOWN:
            self.assertEqual(q.classify(text, text)[0], want, text)


class Files(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_parse_ts(self):
        path = os.path.join(self.dir, "app_fa.ts")
        with open(path, "w", encoding="utf-8") as f:
            f.write(TS)
        self.assertEqual(q.parse_ts(path), ("fa", "en", [("Page %1 of %2", "Safhe %1 az %2")]))

    def test_typescript_is_skipped(self):
        path = os.path.join(self.dir, "index.ts")
        with open(path, "w", encoding="utf-8") as f:
            f.write("const x: number = 1;\n")
        self.assertIsNone(q.parse_ts(path))


class Predictions(unittest.TestCase):
    GEN = {"ja": "Genitive-Noun", "fa": "Noun-Genitive", "zh": "Genitive-Noun", "hu": "Genitive-Noun",
           "fr": "Noun-Genitive"}

    def fill(self):
        t = q.Tally()
        for lang, shape, n, moved in (("ja", "of", 10, 6), ("ja", "no_words", 10, 0), ("fa", "of", 10, 0),
                                      ("zh", "of", 10, 3), ("hu", "of", 10, 1), ("fr", "of", 10, 0)):
            for i in range(n):
                t.add("repo%d" % (i % 2), lang, shape, i < moved, "%%1 of %%2 #%d" % i, "%s %d" % (lang, i),
                      self.GEN)
        return t

    def test_pools(self):
        t = self.fill()
        self.assertEqual(t.row("group:SOV", ["of"])["valid"], 20)
        self.assertEqual(t.row("group:SOV", ["of"])["reordered"], 6)
        self.assertEqual(t.row("pool:nonSOV:GenN", ["of"])["reordered"], 4)
        self.assertEqual(t.row("pool:nonSOV:GenN:nozh", ["of"])["valid"], 10)
        self.assertEqual(t.row("pool:SOV:NGen", ["of"])["valid"], 10)
        self.assertEqual(t.row("all", q.sh.SHAPES)["valid"], 60)

    def test_all_hold(self):
        got = {i: h for i, _, h, _ in q.predictions(self.fill(), minimum=1, lang_minimum=1)}
        self.assertEqual(got, {"Q1": True, "Q2": True, "Q3": True, "Q4": True, "Q5": True, "Q6": True})

    def test_empty_is_not_testable(self):
        got = {i: h for i, _, h, _ in q.predictions(q.Tally(), minimum=1, lang_minimum=1)}
        self.assertEqual(set(got.values()), {None})


if __name__ == "__main__":
    unittest.main()
