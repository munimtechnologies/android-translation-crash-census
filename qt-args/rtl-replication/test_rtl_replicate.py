"""Tests for rtl_replicate.py (Apache-2.0; MV2 of Munim, Inc., made with AI agents)."""

import os
import shutil
import tempfile
import unittest

import rtl_replicate as rr

FA_TS = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="fa_IR" sourcelanguage="en">
<context><name>Main</name>
<message><source>Server %1 is down</source><translation>سرور 1% اکنون</translation></message>
<message><source>Copied %1 of %2</source><translation>%1 / %2</translation></message>
<message><source>Open %1</source><translation type="unfinished">1% open</translation></message>
<message><source>No marker</source><translation>بدون</translation></message>
</context>
</TS>
"""


def file_row(repo, lang, total, reversed_):
    return {"repo": repo, "file": "%s_%s.ts" % (repo.split("/")[1], lang), "lang": lang, "group": rr.group(lang),
            "total": total, "broken": reversed_, "reversed": reversed_, "reversed_any": reversed_}


class TestRtlReplicate(unittest.TestCase):
    def test_groups(self):
        self.assertEqual(rr.group("ar"), "rtl")
        self.assertEqual(rr.group("he"), "rtl")
        self.assertEqual(rr.group("ckb"), "excluded")
        self.assertEqual(rr.group("ku"), "excluded")
        self.assertEqual(rr.group("de"), "other")

    def test_repos_independent(self):
        self.assertEqual(len(rr.REPOS), 40)
        self.assertEqual(len(set(r.lower() for r in rr.REPOS)), 40)
        for repo in rr.REPOS:
            self.assertTrue(rr.independent(repo), repo)
        self.assertFalse(rr.independent("lxqt/lxqt-config"))
        self.assertFalse(rr.independent("scribusproject/scribus"))
        self.assertFalse(rr.independent("owncloud/client"))

    def test_fisher(self):
        self.assertAlmostEqual(rr.fisher_greater(1, 1, 0, 1), 0.5, places=9)
        self.assertAlmostEqual(rr.fisher_greater(3, 3, 0, 3), 0.05, places=9)
        self.assertAlmostEqual(rr.fisher_greater(0, 5, 3, 5), 1.0, places=9)

    def test_reversed_first(self):
        t = rr.Tally()
        got = t.add("o/r", "abc", "r_he.ts", "he", {
            "source": "Cannot open file %1", "translation": "לא ניתן 1%",
            "context": "C"})
        self.assertEqual(got, ("dropped", True))
        # A translation that keeps the marker is fine; a source percentage is not a reversal.
        self.assertEqual(t.add("o/r", "abc", "r_he.ts", "he", {
            "source": "%1% done", "translation": "%1% הושלם", "context": "C"}), ("ok", False))
        self.assertIsNone(t.add("o/r", "abc", "r_he.ts", "he", {"source": "Plain", "translation": "x",
                                                                 "context": "C"}))
        f = t.files[("o/r", "r_he.ts")]
        self.assertEqual((f["total"], f["broken"], f["reversed"], f["reversed_any"]), (2, 1, 1, 1))
        self.assertEqual(len(t.rows), 1)

    def test_scan_ts_file(self):
        root = tempfile.mkdtemp()
        try:
            with open(os.path.join(root, "app_fa.ts"), "w", encoding="utf-8") as f:
                f.write(FA_TS)
            t, record = rr.Tally(), rr.new_record("o/app")
            rr.scan("o/app", root, "abc", t, record)
            self.assertEqual(record["ts_files"], 1)
            self.assertEqual((record["rtl_total"], record["rtl_reversed"]), (2, 1))
            self.assertEqual(record["other_total"], 0)
            self.assertEqual(t.rows[0]["lang"], "fa")
            self.assertEqual(t.rows[0]["hints"], "reversed:1%")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_evaluate_replicated(self):
        files = [file_row("a/x", "ar", 400, 20), file_row("b/y", "fa", 300, 6), file_row("c/z", "he", 300, 4),
                 file_row("a/x", "de", 6000, 3), file_row("b/y", "fr", 6000, 2)]
        r = rr.evaluate(files)
        self.assertAlmostEqual(r["main"]["ratio"], 72.0, places=6)
        self.assertEqual(r["left_out_repo"], "a/x")
        self.assertEqual((r["leave_one_repo_out"]["rtl"], r["leave_one_repo_out"]["rtl_total"]), (10, 600))
        self.assertEqual((r["leave_one_repo_out"]["other"], r["leave_one_repo_out"]["other_total"]), (2, 6000))
        self.assertTrue(r["P1"] and r["P2"] and r["P3"])
        self.assertEqual(r["verdict"], "replicated")

    def test_evaluate_partly_and_too_little(self):
        files = [file_row("a/x", "ar", 400, 30), file_row("b/y", "fa", 300, 0), file_row("c/z", "he", 300, 0),
                 file_row("a/x", "de", 6000, 3), file_row("b/y", "fr", 6000, 2)]
        r = rr.evaluate(files)
        self.assertTrue(r["P1"])
        self.assertFalse(r["P2"])
        self.assertEqual(r["verdict"], "partly replicated")
        r = rr.evaluate(files[:4])
        self.assertFalse(r["enough_data"])
        self.assertEqual(r["verdict"], "too little data")

    def test_evaluate_not_replicated(self):
        files = [file_row("a/x", "ar", 600, 1), file_row("b/y", "fa", 400, 1),
                 file_row("a/x", "de", 6000, 6), file_row("b/y", "fr", 6000, 6)]
        r = rr.evaluate(files)
        self.assertTrue(r["enough_data"])
        self.assertFalse(r["P1"])
        self.assertEqual(r["verdict"], "not replicated")

    def test_write(self):
        out = tempfile.mkdtemp()
        try:
            t = rr.Tally()
            t.add("o/r", "abc", "r_ar.ts", "ar", {"source": "File %1", "translation": "ملف 1%",
                                                  "context": "C"})
            record = rr.new_record("o/r")
            record.update({"status": "ok", "commit": "abc"})
            result = rr.write(out, t, {"finished": "now"}, [record])
            self.assertEqual(result["verdict"], "too little data")
            for name in ("rtl_replication.md", "rtl_replication.json", "reversed_rows.csv", "files.csv",
                         "repos.csv"):
                self.assertTrue(os.path.isfile(os.path.join(out, name)), name)
        finally:
            shutil.rmtree(out, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
