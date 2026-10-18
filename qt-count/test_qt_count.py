"""Tests for qt_count.py (Apache-2.0; MV2 of Munim, Inc., made with AI agents)."""

import os
import shutil
import tempfile
import unittest

import qt_count as qc

ARABIC_PERCENT = "٪"
FULLWIDTH_PERCENT = "％"

AR_TS = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="ar" sourcelanguage="en">
<context><name>Main</name>
<message numerus="yes"><source>%n file(s)</source><translation>
<numerusform>ملف %n</numerusform><numerusform>{p}n ملفات</numerusform></translation></message>
<message numerus="yes"><source>%n item(s)</source><translation>
<numerusform>%n عنصر</numerusform><numerusform>%n عناصر</numerusform></translation></message>
<message numerus="yes"><source>%n day(s)</source><translation type="unfinished">
<numerusform>{p}n يوم</numerusform></translation></message>
<message numerus="yes"><source>%n hour(s)</source><translation type="obsolete">
<numerusform>{p}n ساعة</numerusform></translation></message>
<message><source>Open %1</source><translation>فتح %1</translation></message>
</context>
</TS>
""".format(p=ARABIC_PERCENT)


def file_row(corpus, repo, lang, total, lookalike):
    row = {"corpus": corpus, "repo": repo, "file": "%s_%s.ts" % (repo.split("/")[1], lang), "lang": lang,
           "group": qc.group(lang)}
    row.update({k: 0 for k in qc.COUNTS})
    row.update(total=total, lookalike=lookalike, ok=total - lookalike)
    return row


class TestQtCount(unittest.TestCase):
    def test_guard_version(self):
        self.assertEqual(qc.g.__version__, "0.7.0")

    def test_corpora(self):
        fresh, old = dict(qc.CORPORA)["fresh"], dict(qc.CORPORA)["qt-args"]
        self.assertEqual((len(fresh), len(old)), (40, 39))
        self.assertFalse({r.lower() for r in fresh} & {r.lower() for r in old})
        self.assertEqual(qc.CORPORA[0][0], "fresh")

    def test_groups(self):
        for lang in ("ar", "fa", "ur", "zh", "ja", "ko"):
            self.assertEqual(qc.group(lang), "arabic_cjk", lang)
        for lang in ("de", "he", "ru", "tr"):
            self.assertEqual(qc.group(lang), "other", lang)

    def test_kinds(self):
        self.assertEqual(qc.kind_of("%n file(s)", ["%n Datei", "%n Dateien"]), "ok")
        self.assertEqual(qc.kind_of("%n file(s)", ["%Ln Dateien"]), "ok")
        self.assertEqual(qc.kind_of("%n file(s)", [FULLWIDTH_PERCENT + "n 個のファイル"]), "lookalike")
        self.assertEqual(qc.kind_of("%n file(s)", [ARABIC_PERCENT + "n ملف", "%n ملفات"]), "lookalike")
        self.assertEqual(qc.kind_of("%n file(s)", ["% n Dateien"]), "spaced")
        self.assertEqual(qc.kind_of("%n file(s)", ["%1 Dateien"]), "marker")
        self.assertEqual(qc.kind_of("%n file(s)", ["Dateien"]), "missing")
        self.assertEqual(qc.kind_of("%n file(s)", ["Datei", ""]), "missing")
        self.assertIsNone(qc.kind_of("Open %1", ["%1"]))
        # A word after the percent sign is not a count.
        self.assertEqual(qc.kind_of("%n file(s)", ["%n " + FULLWIDTH_PERCENT + "nicht"]), "ok")

    def test_scan_ts_file(self):
        root = tempfile.mkdtemp()
        try:
            with open(os.path.join(root, "app_ar.ts"), "w", encoding="utf-8") as f:
                f.write(AR_TS)
            t, record = qc.Tally(), qc.new_record("fresh", "o/app")
            qc.scan("fresh", "o/app", root, "abc", t, record)
            self.assertEqual(record["ts_files"], 1)
            self.assertEqual((record["finished"], record["finished_lookalike"], record["unfinished"]), (2, 1, 1))
            f = t.files[("o/app", "app_ar.ts")]
            self.assertEqual((f["total"], f["ok"], f["lookalike"], f["unfinished"], f["unfinished_bad"]),
                             (2, 1, 1, 1, 1))
            self.assertEqual(f["group"], "arabic_cjk")
            self.assertEqual([(r["state"], r["kind"]) for r in t.rows],
                             [("finished", "lookalike"), ("unfinished", "lookalike")])
            self.assertIn(ARABIC_PERCENT + "n", t.rows[0]["forms"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_evaluate(self):
        files = [file_row("fresh", "a/x", "ar", 150, 3), file_row("fresh", "b/y", "zh", 100, 1),
                 file_row("fresh", "a/x", "de", 1500, 0), file_row("fresh", "b/y", "fr", 1500, 0),
                 file_row("qt-args", "bitcoin/bitcoin", "ar", 80, 40)]
        r = qc.evaluate(files)
        self.assertTrue(r["P1"])
        self.assertEqual(r["fresh_repos_with_lookalike"], ["a/x", "b/y"])
        self.assertTrue(r["enough_data_for_P2"])
        self.assertTrue(r["P2"])
        self.assertLess(r["fresh"]["p"], 0.01)
        self.assertEqual(r["known"]["bitcoin/bitcoin ar"]["lookalike"], 40)
        # One fresh repository is not enough for P1; too few messages leave P2 ungraded.
        r = qc.evaluate([file_row("fresh", "a/x", "ar", 150, 3), file_row("fresh", "a/x", "de", 1500, 0)])
        self.assertFalse(r["P1"])
        self.assertIsNone(r["P2"])
        # Enough data and no difference: P2 fails. P1 counts look-alikes in any language.
        r = qc.evaluate([file_row("fresh", "a/x", "ar", 300, 0), file_row("fresh", "b/y", "de", 3000, 2),
                         file_row("fresh", "c/z", "de", 3000, 2)])
        self.assertTrue(r["P1"])
        self.assertFalse(r["P2"])

    def test_write(self):
        out = tempfile.mkdtemp()
        try:
            t = qc.Tally()
            t.add("fresh", "o/r", "abc", "r_ja.ts", "ja", {
                "numerus": True, "state": "finished", "context": "C", "source": "%n file(s)",
                "forms": [FULLWIDTH_PERCENT + "n 個"]})
            record = qc.new_record("fresh", "o/r")
            record.update({"status": "ok", "commit": "abc"})
            result = qc.write(out, t, {"finished": "now"}, [record])
            self.assertFalse(result["P1"])
            self.assertIsNone(result["P2"])
            for name in ("qt_count.md", "qt_count.json", "rows.csv", "files.csv", "repos.csv"):
                self.assertTrue(os.path.isfile(os.path.join(out, name)), name)
        finally:
            shutil.rmtree(out, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
