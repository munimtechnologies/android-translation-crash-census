"""Tests for qt_args.py (python -m unittest -v test_qt_args).

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import csv
import json
import os
import shutil
import tempfile
import unittest

import qt_args as q

TS = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="ko_KR" sourcelanguage="en">
<context>
    <name>SyncStatus</name>
    <message>
        <location filename="../src/gui/status.cpp" line="42"/>
        <source>Syncing %1 of %2</source>
        <translation>%2 중 %1 동기화 중</translation>
    </message>
    <message>
        <source>Copied %1 to %2</source>
        <translation>%2 복사됨</translation>
    </message>
    <message>
        <source>Open %1</source>
        <translation type="unfinished">%1 열기</translation>
    </message>
    <message>
        <source>Old %1</source>
        <translation type="vanished">옛 %1</translation>
    </message>
    <message numerus="yes">
        <source>%n file(s) in %1</source>
        <translation><numerusform>%n 파일</numerusform></translation>
    </message>
    <message>
        <source>Empty %1</source>
        <translation></translation>
    </message>
    <message>
        <source>Plain</source>
        <translation>평범</translation>
    </message>
</context>
</TS>
"""


class Names(unittest.TestCase):
    def test_lang_code(self):
        self.assertEqual(q.lang_code("zh_CN"), "zh")
        self.assertEqual(q.lang_code("sr@latin"), "sr")
        self.assertEqual(q.lang_code("pt-BR"), "pt")
        self.assertEqual(q.lang_code("iw"), "he")
        self.assertEqual(q.lang_code(None), "")

    def test_file_lang(self):
        self.assertEqual(q.file_lang("keepassxc_zh_CN.ts"), "zh")
        self.assertEqual(q.file_lang("translations.ts"), "")

    def test_qt_own(self):
        self.assertTrue(q.QT_OWN_RE.match("qtbase_zh_CN.ts"))
        self.assertFalse(q.QT_OWN_RE.match("qterminal_fa.ts"))


class Markers(unittest.TestCase):
    def test_markers(self):
        self.assertEqual(q.markers("Page %1 of %2"), [1, 2])
        self.assertEqual(q.markers("%L2 / %L1 / %2"), [1, 2])
        self.assertEqual(q.markers("%100 done"), [10])       # Qt reads at most two digits
        self.assertEqual(q.markers("%0 and %01"), [0, 1])    # %0 is a marker; %01 is %1
        self.assertEqual(q.markers("100% done, % 1"), [])
        self.assertEqual(q.markers("কপি %১"), [])
        self.assertEqual(q.markers("কপি %১", unicode_digits=True), [1])


class Classify(unittest.TestCase):
    def cat(self, s, t, **kw):
        return q.classify(s, t, **kw)[0]

    def test_ok(self):
        self.assertEqual(self.cat("Syncing %1 of %2", "%2 중 %1 동기화 중"), "ok")
        self.assertEqual(self.cat("Size %1", "Boyut %L1"), "ok")
        # A Turkish percentage above the source's markers stays as text.
        self.assertEqual(self.cat("Done %1", "%50 tamam: %1"), "ok")

    def test_no_markers(self):
        self.assertIsNone(q.classify("Plain", "%1 anything"))

    def test_dropped(self):
        got = q.classify("Copied %1 to %2", "%1 kopiert")
        self.assertEqual(got[0], "dropped")
        self.assertEqual(got[4], [2])
        self.assertEqual(self.cat("%1 %2", "%1 %1"), "dropped")
        self.assertEqual(self.cat("Open %1", "Open"), "dropped")

    def test_value_moved(self):
        # Without %1, the first argument lands in %2.
        got = q.classify("Copied %1 to %2", "%2 복사됨")
        self.assertEqual(got[0], "wrong_value")
        self.assertEqual(got[3], [(2, 2, 1)])
        self.assertEqual(got[4], [2])
        self.assertEqual(q.wrong_kinds(got[3]), ["value_moved"])

    def test_text_marker_takes_value(self):
        got = q.classify("Done %1", "%50 tamam")
        self.assertEqual(got[0], "wrong_value")
        self.assertEqual(q.wrong_kinds(got[3]), ["text_marker_takes_value"])

    def test_marker_left_as_text(self):
        got = q.classify("%1 of %2", "%0 %1 %2")
        self.assertEqual(got[0], "wrong_value")
        self.assertEqual(sorted(q.wrong_kinds(got[3])), ["marker_left_as_text", "text_marker_takes_value",
                                                          "value_moved"])

    def test_renumbered(self):
        # %1 and %3 for a two-marker source: the second argument lands in %3,
        # which the source lacks, so it counts as a misplacement.
        self.assertEqual(self.cat("%1 / %2", "%1 / %3"), "wrong_value")

    def test_non_ascii_digits(self):
        s, t = "Copy %1", "কপি %১"
        self.assertEqual(self.cat(s, t), "dropped")
        self.assertEqual(self.cat(s, t, unicode_digits=True), "ok")

    def test_hints(self):
        self.assertEqual(q.hints("Copy %1", "Copy 1%"), ["reversed:1%"])
        self.assertEqual(q.hints("Copy %1", "Copy % 1"), ["spaced:% 1"])
        self.assertEqual(q.hints("Copy %1", "نسخ ٪1"), ["percent_sign:1"])
        self.assertEqual(q.hints("Copy %1", "কপি %১"), ["non_ascii_digit:1"])
        self.assertEqual(q.hints("Copy %1", "Copier %s"), ["printf"])
        self.assertEqual(q.hints("Copy %1 at 50%", "Copier 50%"), [])


class Files(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def write_ts(self):
        path = os.path.join(self.dir, "client_ko.ts")
        with open(path, "w", encoding="utf-8") as f:
            f.write(TS)
        return path

    def test_parse_ts(self):
        lang, source_lang, messages = q.parse_ts(self.write_ts())
        self.assertEqual((lang, source_lang), ("ko", "en"))
        self.assertEqual([m["state"] for m in messages],
                         ["finished", "finished", "unfinished", "obsolete", "numerus", "finished", "finished"])
        self.assertEqual(messages[0]["context"], "SyncStatus")
        self.assertEqual((messages[0]["location"], messages[0]["line"]), ("../src/gui/status.cpp", "42"))

    def test_typescript_is_skipped(self):
        path = os.path.join(self.dir, "index.ts")
        with open(path, "w", encoding="utf-8") as f:
            f.write("const x: number = 1;\n")
        self.assertIsNone(q.parse_ts(path))

    def test_scan_and_write(self):
        self.write_ts()
        t, record = q.Tally(), q.new_record("o/r")
        q.scan("o/r", self.dir, "abc123", t, record)
        self.assertEqual(record["finished_with_markers"], 2)
        self.assertEqual(record["finished_wrong_value"], 1)
        self.assertEqual(record["unfinished_with_markers"], 1)
        self.assertEqual(record["numerus_skipped"], 1)
        self.assertEqual(record["obsolete_skipped"], 1)
        record["status"] = "ok"
        out = os.path.join(self.dir, "out")
        summary = q.write(out, t, {"finished": "now"}, [record])
        self.assertEqual(summary["finished"]["wrong_value"], 1)
        self.assertEqual(summary["finished"]["wrong_kinds"], {"value_moved": 1})
        self.assertEqual(summary["unfinished"]["total"], 1)
        with open(os.path.join(out, "rows.csv"), encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["file"], rows[0]["wrong"]), ("client_ko.ts", "%2:2->1"))
        with open(os.path.join(out, "qt_args.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["repos"][0]["languages"], ["ko"])
        for name in ("qt_args.md", "by_language.csv", "repos.csv"):
            self.assertTrue(os.path.exists(os.path.join(out, name)), name)


if __name__ == "__main__":
    unittest.main()
