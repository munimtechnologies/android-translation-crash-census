# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Tests for zh_vocab.py (no network). Made with AI agents."""
import fractions
import os
import shutil
import tempfile
import unittest

import zh_vocab as z

TABLE_TEXT = (
    "# comment line\n"
    "\n"
    "軟件\t軟體\n"
    "默認\t預設\n"
    "用戶\t使用者\n"
    "信息\t資訊\n"
    "內存\t記憶體\n"
    "文件\t檔案\n"
    "文件夾\t資料夾\n"
    "數據\t資料 數據\n"
    "程序\t程式\n"
    "程序正義\t程序正義\n"
)

ST_TEXT = "软\t軟\n认\t認\n户\t戶\n这\t這\n设\t設\n据\t據\n数\t數\n发\t發 髮\n"
TS_TEXT = "軟\t软\n認\t认\n戶\t户\n這\t这\n設\t设\n據\t据\n數\t数\n發\t发\n髮\t发\n"


def phrases():
    return z.Phrases(z.parse_dict(TABLE_TEXT, single=False))


class TestDicts(unittest.TestCase):
    def test_parse_phrases_keeps_multi_char_keys(self):
        t = z.parse_dict(TABLE_TEXT, single=False)
        self.assertEqual(t["軟件"], ["軟體"])
        self.assertEqual(t["數據"], ["資料", "數據"])
        self.assertEqual(len(t), 10)

    def test_parse_single_drops_phrases(self):
        self.assertEqual(z.parse_dict(TABLE_TEXT), {})
        self.assertEqual(z.parse_dict(ST_TEXT)["发"], ["發", "髮"])

    def test_s_set(self):
        st, ts = z.parse_dict(ST_TEXT), z.parse_dict(TS_TEXT)
        s = z.build_s_set(st, ts, {}, {})
        self.assertIn("这", s)
        self.assertNotIn("這", s)


class TestMatching(unittest.TestCase):
    def test_flagged_key(self):
        p = phrases()
        self.assertTrue(p.flagged_key("軟件"))
        self.assertFalse(p.flagged_key("數據"))      # Taiwan usage includes it
        self.assertFalse(p.flagged_key("程序正義"))

    def test_longest_match_wins(self):
        p = phrases()
        self.assertEqual(p.matches("程序正義很重要"), [(0, "程序正義")])
        self.assertEqual(p.terms("程序正義很重要", "Due process"), [])
        self.assertEqual(p.terms("打開文件夾", "Open folder"), ["文件夾"])
        self.assertEqual(p.terms("這個程序", "This program"), ["程序"])

    def test_terms_order_no_repeats_source_excluded(self):
        p = phrases()
        self.assertEqual(p.terms("軟件和用戶，軟件", "x"), ["軟件", "用戶"])
        self.assertEqual(p.terms("軟件和用戶", "軟件"), ["用戶"])
        self.assertEqual(p.terms("軟體與使用者", "x"), [])
        self.assertEqual(p.terms("數據", "x"), [])

    def test_control_passes_on_good_table(self):
        st, ts = z.parse_dict(ST_TEXT), z.parse_dict(TS_TEXT)
        self.assertTrue(z.control(phrases(), z.build_s_set(st, ts, {}, {})))

    def test_control_fails_on_broken_table(self):
        st, ts = z.parse_dict(ST_TEXT), z.parse_dict(TS_TEXT)
        broken = z.Phrases({"軟件": ["軟件"], "默認": ["預設"], "用戶": ["使用者"],
                            "信息": ["資訊"], "內存": ["記憶體"]})
        self.assertFalse(z.control(broken, z.build_s_set(st, ts, {}, {})))


class TestCharEquivalent(unittest.TestCase):
    def test_conversion(self):
        st = z.parse_dict(ST_TEXT)
        self.assertTrue(z.char_equivalent("默认软件", "默認軟件", st))
        self.assertTrue(z.char_equivalent("头发", "头髮", st))
        self.assertTrue(z.char_equivalent("同样", "同样", st))
        self.assertFalse(z.char_equivalent("默认软件", "預設軟體", st))
        self.assertFalse(z.char_equivalent("软件", "軟件。", st))


class TestGroups(unittest.TestCase):
    def test_zh_group(self):
        g = z.zh_group
        self.assertEqual(g("values-zh-rTW"), "tw")
        self.assertEqual(g("values-zh-rHK"), "hk")
        self.assertEqual(g("values-zh-rMO"), "hk")
        self.assertEqual(g("values-zh-rCN"), "hans")
        self.assertEqual(g("values-zh"), "plain")
        self.assertEqual(g("values-b+zh+Hant+TW"), "tw")
        self.assertEqual(g("values-b+zh+Hant+HK"), "hk")
        self.assertEqual(g("values-b+zh+Hant"), "hant")
        self.assertEqual(g("values-b+zh+Hans"), "hans")
        self.assertEqual(g("values-b+zh+Hans+TW"), "hans")
        self.assertIsNone(g("values-zh-rTW-v21"))
        self.assertIsNone(g("values-ja"))

    def test_hans_rank(self):
        dirs = ["values-zh", "values-zh-rSG", "values-zh-rCN", "values-zh-rTW"]
        best = sorted(r for r in (z.hans_rank(d) for d in dirs) if r)[0][1]
        self.assertEqual(best, "values-zh-rCN")
        self.assertIsNone(z.hans_rank("values-zh-rTW"))


def write(path, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n' + body + "</resources>\n")


class TestScan(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        res = os.path.join(self.root, "app", "src", "main", "res")
        write(os.path.join(res, "values", "strings.xml"),
              '<string name="a">Default software</string>\n'
              '<string name="b">Users</string>\n'
              '<string name="c">Settings</string>\n'
              '<string name="d" translatable="false">x</string>\n'
              '<plurals name="p"><item quantity="other">%d files</item></plurals>\n')
        write(os.path.join(res, "values-zh-rCN", "strings.xml"),
              '<string name="a">默认软件</string>\n'
              '<string name="b">用户</string>\n'
              '<string name="c">设置</string>\n')
        write(os.path.join(res, "values-zh-rTW", "strings.xml"),
              '<string name="a">默認軟件</string>\n'
              '<string name="b">使用者用戶</string>\n'
              '<string name="c">設定</string>\n'
              '<string name="d">軟件</string>\n'
              '<plurals name="p"><item quantity="other">%d 個文件</item></plurals>\n')
        write(os.path.join(res, "values-zh-rHK", "strings.xml"),
              '<string name="a">預設軟件</string>\n'
              '<string name="c">Settings</string>\n')
        st, ts = z.parse_dict(ST_TEXT), z.parse_dict(TS_TEXT)
        self.st, self.s = st, z.build_s_set(st, ts, {}, {})

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_scan(self):
        r = z.scan_strings(self.root, phrases(), self.st, self.s)
        self.assertEqual(r["units"]["tw"], 4)      # a, b, c, p (d is not translatable)
        self.assertEqual(r["units"]["hk"], 1)      # c is untranslated English
        self.assertEqual(r["flagged"]["tw"], 3)
        self.assertEqual(r["flagged"]["hk"], 1)
        self.assertEqual(r["terms"]["tw\t軟件"], 1)
        self.assertEqual(r["terms"]["tw\t文件"], 1)
        rows = {(x["group"], x["key"]): x for x in r["rows"]}
        a = rows[("tw", "string:a")]
        self.assertEqual(a["terms"], "默認 軟件")
        self.assertEqual(a["taiwan"], "預設 | 軟體")
        self.assertTrue(a["hans_available"])
        self.assertFalse(a["hans_identical"])
        self.assertTrue(a["char_equivalent"])
        self.assertEqual(a["source"], "Default software")
        self.assertEqual(a["res_dir"], "app/src/main/res")
        b = rows[("tw", "string:b")]
        self.assertFalse(b["char_equivalent"])
        p = rows[("tw", "plurals:p")]
        self.assertFalse(p["hans_available"])
        self.assertEqual(p["hans_dir"], "")


def row(repo, key, group="tw", avail=True, equiv=False):
    return {"repo": repo, "res_dir": "res", "locale_dir": "values-zh-rTW", "file": "strings.xml",
            "key": key, "index": 0, "group": group, "hans_available": avail,
            "char_equivalent": equiv, "hans_identical": False, "has_s": False}


class TestGrading(unittest.TestCase):
    def tw(self, repos, units, flagged, repos_flagged):
        return {"repos": repos, "units": units, "flagged": flagged, "repos_flagged": repos_flagged}

    def test_gate(self):
        t = {"tw": self.tw(99, 50000, 10, 50), "hk": self.tw(30, 5000, 1, 1)}
        v = z.grade(t, fractions.Fraction(0), 0)
        self.assertEqual(set(v.values()), {"NOT TESTABLE (gate)"})

    def test_v1_boundary(self):
        hk = self.tw(30, 3000, 0, 0)
        held = z.grade({"tw": self.tw(300, 30000, 500, 100), "hk": hk}, fractions.Fraction(0), 0)
        failed = z.grade({"tw": self.tw(300, 30000, 500, 99), "hk": hk}, fractions.Fraction(0), 0)
        self.assertEqual(held["V1"], "HELD")
        self.assertEqual(failed["V1"], "FAILED")
        self.assertEqual(held["V3"], "NOT TESTABLE")
        self.assertTrue(held["V4"].startswith("PENDING"))

    def test_v2(self):
        tw = self.tw(300, 30000, 300, 100)                 # 1.0%
        more = z.grade({"tw": tw, "hk": self.tw(30, 3000, 31, 5)}, fractions.Fraction(0), 0)
        same = z.grade({"tw": tw, "hk": self.tw(30, 3000, 30, 5)}, fractions.Fraction(0), 0)
        small = z.grade({"tw": tw, "hk": self.tw(19, 3000, 300, 5)}, fractions.Fraction(0), 0)
        self.assertEqual(more["V2"], "HELD")
        self.assertEqual(same["V2"], "FAILED")
        self.assertEqual(small["V2"], "NOT TESTABLE (gate)")

    def test_v3(self):
        tw, hk = self.tw(300, 30000, 300, 100), self.tw(30, 3000, 0, 0)
        held = z.grade({"tw": tw, "hk": hk}, fractions.Fraction(5), 10)
        failed = z.grade({"tw": tw, "hk": hk}, fractions.Fraction(49, 10), 10)
        self.assertEqual(held["V3"], "HELD")
        self.assertEqual(failed["V3"], "FAILED")

    def test_tables_v3_mean_per_repo(self):
        results = [
            {"repo": "A", "units": {"tw": 10}, "flagged": {"tw": 2}, "terms": {"tw\t軟件": 2},
             "rows": [row("A", "a", equiv=True), row("A", "b", equiv=False)]},
            {"repo": "B", "units": {"tw": 10}, "flagged": {"tw": 1}, "terms": {"tw\t軟件": 1},
             "rows": [row("B", "a", equiv=True)]},
            {"repo": "C", "units": {"tw": 10}, "flagged": {"tw": 1}, "terms": {"tw\t用戶": 1},
             "rows": [row("C", "a", avail=False)]},
        ]
        t, total, n = z.tables(results)
        self.assertEqual(n, 2)
        self.assertEqual(total, fractions.Fraction(3, 2))
        self.assertEqual(t["tw"]["top_terms"][0], ["軟件", 3, 2])
        self.assertEqual(t["tw"]["repos_flagged"], 3)

    def test_v4(self):
        self.assertEqual(z.grade_v4(["mainland"] * 30 + ["fine"] * 10), "HELD")
        self.assertEqual(z.grade_v4(["mainland"] * 29 + ["fine"] * 11), "FAILED")
        self.assertEqual(z.grade_v4(["mainland"] * 3 + ["other"]), "HELD")
        self.assertEqual(z.grade_v4([]), "NOT TESTABLE")
        self.assertEqual(z.grade_v4(["mainland"] * 3), "NOT TESTABLE")


class TestSample(unittest.TestCase):
    def test_one_per_repo_fixed(self):
        rows = [row("R%d" % i, "k%d" % j) for i in range(60) for j in range(3)]
        rows.append(row("HK", "x", group="hk"))
        s = z.draw_sample(rows)
        self.assertEqual(len(s), 40)
        self.assertEqual(len({x["repo"] for x in s}), 40)
        self.assertNotIn("HK", {x["repo"] for x in s})
        self.assertEqual(s, z.draw_sample(list(reversed(rows))))


if __name__ == "__main__":
    unittest.main()
