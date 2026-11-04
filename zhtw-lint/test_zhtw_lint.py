# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Tests for zhtw_lint.py (no network; a fake zhtw-mcp stands in for the binary).
Made with AI agents."""
import os
import shutil
import stat
import sys
import tempfile
import unittest

import zhtw_lint as zl

FAKE = '''#!%s
import json, sys
text = sys.stdin.buffer.read().decode("utf-8")
if "ERR" in text:
    sys.stderr.write("boom")
    sys.exit(2)
issues = []
for term, to in (("軟件", "軟體"), ("默認", "預設")):
    if term in text:
        issues.append({"line": 1, "col": text.index(term) + 1, "found": term,
                       "suggestions": [to], "rule_type": "cross_strait", "severity": "warning"})
if "。。" in text:
    issues.append({"line": 1, "found": "。。", "rule_type": "punctuation"})
print(json.dumps(issues, ensure_ascii=False))
sys.exit(1 if issues else 0)
'''

SOFTWARE = "軟件"       # mainland "software"
DEFAULT = "默認"        # mainland "default"


def write(path, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n' + body + "</resources>\n")


class TestOutput(unittest.TestCase):
    def test_findings_flat(self):
        data = [{"found": SOFTWARE, "rule_type": "cross_strait"},
                {"found": "。。", "rule_type": "punctuation"}]
        f = zl.findings(data)
        self.assertEqual(len(f), 1)
        self.assertEqual(zl.found_text(f[0]), SOFTWARE)

    def test_findings_nested(self):
        data = {"files": [{"path": "-", "issues": [
            {"span": {"text": SOFTWARE}, "rule": {"type": "CrossStrait", "id": 7}},
            {"rule": {"type": "spacing"}, "found": "a"}]}]}
        f = zl.findings(data)
        self.assertEqual(len(f), 1)
        self.assertEqual(zl.found_text(f[0]), SOFTWARE)

    def test_found_order(self):
        self.assertEqual(zl.found_text({"text": "整句話", "found": SOFTWARE, "t": "x"}), SOFTWARE)
        self.assertEqual(zl.found_text({"t": "cross_strait"}), "")

    def test_norm(self):
        self.assertEqual(zl.norm_type("cross_strait"), "crossstrait")
        self.assertEqual(zl.norm_type("Cross-Strait"), "crossstrait")
        self.assertNotEqual(zl.norm_type("cross_strait term"), "crossstrait")

    def test_overlaps(self):
        self.assertTrue(zl.overlaps(["文件"], ["文件名"]))
        self.assertTrue(zl.overlaps(["應用程序"], ["程序"]))
        self.assertFalse(zl.overlaps(["數據"], ["聲明"]))
        self.assertFalse(zl.overlaps([""], ["聲明"]))
        self.assertFalse(zl.overlaps([], ["聲明"]))


@unittest.skipIf(os.name == "nt", "fake binary needs a POSIX shebang")
class TestFakeBinary(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.bin = os.path.join(self.dir, "zhtw-mcp")
        with open(self.bin, "w", encoding="utf-8") as f:
            f.write(FAKE % sys.executable)
        os.chmod(self.bin, os.stat(self.bin).st_mode | stat.S_IEXEC)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_lint(self):
        self.assertEqual(zl.lint(self.bin, "這個" + SOFTWARE), ([SOFTWARE], None))
        self.assertEqual(zl.lint(self.bin, "好。。"), ([], None))
        found, err = zl.lint(self.bin, "ERR")
        self.assertIsNone(found)
        self.assertTrue(err.startswith("exit 2"))

    def test_control(self):
        ok, rec = zl.control(self.bin)
        self.assertTrue(ok)
        self.assertEqual(len(rec), 3)

    def test_control_fails_on_broken_binary(self):
        with open(self.bin, "w", encoding="utf-8") as f:
            f.write("#!%s\nprint('[]')\n" % sys.executable)
        ok, _ = zl.control(self.bin)
        self.assertFalse(ok)


class TestScan(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        res = os.path.join(self.root, "app", "src", "main", "res")
        write(os.path.join(res, "values", "strings.xml"),
              '<string name="a">Software settings</string>\n'
              '<string name="b">Default</string>\n'
              '<string name="c">OK</string>\n'
              '<string name="d" translatable="false">x</string>\n'
              '<string name="e">軟件</string>\n')
        write(os.path.join(res, "values-zh-rTW", "strings.xml"),
              '<string name="a">軟件設定</string>\n'
              '<string name="b">預設</string>\n'
              '<string name="c">OK</string>\n'
              '<string name="d">某</string>\n'
              '<string name="e">軟體</string>\n')
        write(os.path.join(res, "values-zh-rTW", "extra.xml"),
              '<string name="z">無來源</string>\n')
        write(os.path.join(res, "values-zh-rCN", "strings.xml"),
              '<string name="a">软件设置</string>\n')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_scan(self):
        rows, failed = zl.scan_tw(self.root)
        self.assertEqual(failed, 0)
        self.assertEqual([r["key"] for r in rows], ["string:a", "string:b", "string:e"])
        a = rows[0]
        self.assertEqual(a["text"], "軟件設定")
        self.assertEqual(a["source"], "Software settings")
        self.assertEqual(a["res_dir"], "app/src/main/res")
        self.assertEqual(a["locale_dir"], "values-zh-rTW")
        self.assertTrue(zl.z.has_han(rows[2]["source"]))


SAMPLE = "n,repo,head,res_dir,locale_dir,file,key,index,terms,taiwan,text,source\n" + "".join(
    "%d,R%d,h,res,values-zh-rTW,strings.xml,string:k%d,0,T%d,x,text %d,src\n" % (n, n, n, n, n)
    for n in range(1, 41))


def labels(mainland=None):
    mainland = set(zl.MAINLAND_TERMS) if mainland is None else mainland
    return "n,repo,key,terms,label,note\n" + "".join(
        "%d,R%d,string:k%d,T%d,%s,note\n" % (n, n, n, n, "mainland" if n in mainland else "fine")
        for n in range(1, 41))


class TestKnown(unittest.TestCase):
    def test_join(self):
        rows = zl.known_rows(SAMPLE, labels())
        self.assertEqual(len(rows), 40)
        self.assertEqual(rows[4]["label"], "mainland")      # n = 5
        self.assertEqual(rows[0]["terms"], ["T1"])
        self.assertEqual(rows[0]["text"], "text 1")

    def test_join_rejects_other_labels(self):
        with self.assertRaises(ValueError):
            zl.known_rows(SAMPLE, labels(set(zl.MAINLAND_TERMS) - {5}))

    def test_mainland_terms(self):
        self.assertEqual(len(zl.MAINLAND_TERMS), 16)

    def test_grade_known(self):
        rows = zl.known_rows(SAMPLE, labels())
        for r in rows:
            r["error"] = None
            r["found"] = []
        mainland = [r for r in rows if r["label"] == "mainland"]
        for r in mainland[:12]:
            r["found"] = [zl.MAINLAND_TERMS[r["n"]][0]]
        fine = [r for r in rows if r["label"] == "fine"]
        for r in fine[:6]:
            r["found"] = r["terms"]
        fine[6]["found"] = ["other"]          # a different term: not a repeated false alarm
        v, d = zl.grade_known(rows)
        self.assertEqual(v, {"Z2": "HELD", "Z3": "HELD"})
        self.assertEqual(len(d["z2_caught"]), 12)
        self.assertEqual(len(d["z3_repeated"]), 6)
        mainland[0]["found"] = []
        fine[6]["found"] = fine[6]["terms"]
        v, _ = zl.grade_known(rows)
        self.assertEqual(v, {"Z2": "FAILED", "Z3": "FAILED"})
        rows[0]["error"] = "timeout"
        v, _ = zl.grade_known(rows)
        self.assertTrue(v["Z2"].startswith("NOT TESTABLE"))


def unit(repo, key, zhtw=("x",), opencc=()):
    return {"repo": repo, "res_dir": "res", "locale_dir": "values-zh-rTW", "file": "strings.xml",
            "key": key, "index": 0, "zhtw": list(zhtw), "opencc": list(opencc)}


class TestSampleAndGrades(unittest.TestCase):
    def test_sample(self):
        rows = [unit("R%d" % i, "k%d" % j) for i in range(60) for j in range(3)]
        rows += [unit("NONE", "k", zhtw=()), unit("KNOWN", "k")]
        s = zl.draw_sample(rows, exclude={("KNOWN", "k")})
        self.assertEqual(len(s), 40)
        self.assertEqual(len({x["repo"] for x in s}), 40)
        self.assertFalse({"NONE", "KNOWN"} & {x["repo"] for x in s})
        self.assertEqual(s, zl.draw_sample(list(reversed(rows)), exclude={("KNOWN", "k")}))

    def test_z1(self):
        self.assertEqual(zl.grade_z1(["mainland"] * 30 + ["fine"] * 10), "HELD")
        self.assertEqual(zl.grade_z1(["mainland"] * 29 + ["fine"] * 11), "FAILED")
        self.assertEqual(zl.grade_z1(["mainland"] * 19), "NOT TESTABLE")

    def test_tables_z4(self):
        units = [unit("A", "a", zhtw=("軟件",), opencc=("軟件",)),
                 unit("A", "b", zhtw=(), opencc=("權限",)),
                 unit("B", "c", zhtw=("默認",), opencc=())]
        t, top = zl.tables(units)
        self.assertEqual(t["units"], 3)
        self.assertEqual(t["zhtw"], 2)
        self.assertEqual(t["opencc"], 2)
        self.assertEqual(t["both"], 1)
        self.assertEqual(t["repos_zhtw"], 2)
        self.assertEqual(t["repos_opencc_only"], 1)
        self.assertEqual(zl.grade_z4(t), "FAILED")          # equal is not fewer
        t["opencc"] = 3
        self.assertEqual(zl.grade_z4(t), "HELD")
        self.assertEqual(top[0][1], 1)

    def test_constants(self):
        self.assertEqual(zl.PREREG_MARK, "zhtw-lint PREREG v1")
        self.assertTrue(zl.PREREG_URL.endswith("zhtw-lint/PREREG.md"))
        self.assertEqual(zl.z.VERSION, "0.1.0")
        self.assertIn("cross_strait".replace("_", ""), zl.VOCAB_TYPE)


if __name__ == "__main__":
    unittest.main()
