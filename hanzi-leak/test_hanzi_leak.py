# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for hanzi_leak.py (no network). Made with AI agents by MV2 of Munim, Inc."""
import fractions
import os
import shutil
import tempfile
import unittest

import hanzi_leak as H

ST = """# comment
这\t這
设\t設
发\t發 髮
说\t說
台\t臺 檯 颱 台
只\t只 隻 祇
干\t幹 乾 干 榦
床\t牀
才\t纔
吃\t喫
峰\t峯
温\t溫
置\t置
"""
TS = """這\t这
設\t設 设
發\t发
說\t说
臺\t台
隻\t只
溫\t温
"""
TW = """牀\t床
纔\t才
喫\t吃
峯\t峰
"""
HK = """溫\t温
"""


def sets():
    return H.build_sets(H.parse_dict(ST), H.parse_dict(TS), H.parse_dict(TW), H.parse_dict(HK))


class TestSets(unittest.TestCase):
    def test_parse_dict(self):
        d = H.parse_dict(ST)
        self.assertEqual(d["发"], ["發", "髮"])
        self.assertNotIn("#", "".join(d))

    def test_simplified_only(self):
        s, t = sets()
        self.assertEqual(s, set("这设发说"))
        # self-mapping (台 只 干), Taiwan/HK standard forms (床 才 吃 峰 温) are never flagged
        for c in "台只干床才吃峰温置":
            self.assertNotIn(c, s)

    def test_traditional_only(self):
        s, t = sets()
        # 設 maps to itself too, so it is not Traditional-only in this toy dictionary
        self.assertEqual(t, set("這發說臺隻溫"))

    def test_foreign_ignores_source(self):
        s, _ = sets()
        self.assertEqual(H.foreign("这是设置", "Settings", s), ["设", "这"])
        self.assertEqual(H.foreign("这是设置", "这", s), ["设"])
        self.assertEqual(H.foreign("這是設定", "Settings", s), [])

    def test_control_passes_and_fails(self):
        s, t = sets()
        self.assertFalse(H.control(s, t))  # toy T lacks 設
        t2 = t | {"設"}
        self.assertTrue(H.control(s, t2))
        self.assertFalse(H.control(s | {"台"}, t2))
        self.assertFalse(H.control(s - {"这"}, t2))

    def test_han(self):
        self.assertTrue(H.has_han("設定"))
        self.assertTrue(H.has_han(chr(0x3400)))
        self.assertTrue(H.has_han(chr(0x20000)))
        self.assertFalse(H.has_han("Settings 設"[:8]))
        self.assertFalse(H.has_han("ひらがな"))


class TestFolders(unittest.TestCase):
    def test_groups(self):
        g = H.zh_group
        self.assertEqual(g("values-zh-rTW"), "hant")
        self.assertEqual(g("values-zh-rHK"), "hant")
        self.assertEqual(g("values-zh-rMO"), "hant")
        self.assertEqual(g("values-zh-rCN"), "hans")
        self.assertEqual(g("values-zh-rSG"), "hans")
        self.assertEqual(g("values-zh"), "plain")
        self.assertEqual(g("values-b+zh+Hant"), "hant")
        self.assertEqual(g("values-b+zh+Hant+TW"), "hant")
        self.assertEqual(g("values-b+zh+Hans"), "hans")
        self.assertEqual(g("values-b+zh+HANS+TW"), "hans")
        self.assertEqual(g("values-b+zh+TW"), "hant")
        self.assertEqual(g("values-b+zh"), "plain")
        self.assertIsNone(g("values-zh-rUS"))
        self.assertIsNone(g("values-zh-rTW-v21"))
        self.assertIsNone(g("values-ja"))
        self.assertIsNone(g("values"))

    def test_primary(self):
        dirs = ["values", "values-zh", "values-zh-rSG", "values-b+zh+Hans", "values-zh-rCN",
                "values-zh-rHK", "values-zh-rTW"]
        best = sorted(r for r in (H.primary_rank(d, "hans") for d in dirs) if r)[0][1]
        self.assertEqual(best, "values-zh-rCN")
        best = sorted(r for r in (H.primary_rank(d, "hans") for d in dirs[:3]) if r)[0][1]
        self.assertEqual(best, "values-zh-rSG")
        best = sorted(r for r in (H.primary_rank(d, "hant") for d in dirs) if r)[0][1]
        self.assertEqual(best, "values-zh-rTW")

    def test_decode(self):
        esc = "\\" + "u8FD9"
        self.assertEqual(H.decode_android(esc), chr(0x8FD9))


def write(root, d, body):
    os.makedirs(os.path.join(root, "res", d), exist_ok=True)
    with open(os.path.join(root, "res", d, "strings.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n' + body + "</resources>\n")


class TestScan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.s, t = sets()
        self.t = t | {"設"}
        write(self.tmp, "values",
              '<string name="a">Settings</string><string name="b">Send</string>'
              '<string name="c">Say</string><string name="d" translatable="false">x</string>'
              '<string-array name="arr"><item>One</item><item>Two</item></string-array>')
        write(self.tmp, "values-zh-rCN",
              '<string name="a">这是设置</string><string name="b">发送</string>'
              '<string name="c">说</string>'
              '<string-array name="arr"><item>一</item><item>二</item></string-array>')
        write(self.tmp, "values-zh-rTW",
              '<string name="a">这是设置</string><string name="b">發送这</string>'
              '<string name="c">說</string><string name="d">这</string>'
              '<string-array name="arr"><item>一</item><item>Two</item></string-array>')
        write(self.tmp, "values-zh",
              '<string name="a">這是設定</string><string name="b">发送</string>')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_scan(self):
        r = H.scan_strings(self.tmp, self.s, self.t)
        # TW units: a, b, c, arr[0] (d is not translatable, arr[1] has no Han character)
        self.assertEqual(r["units"]["hant"], 4)
        self.assertEqual(r["units"]["hans"], 5)
        self.assertEqual(r["flagged"]["hant"], 2)
        self.assertEqual(r["flagged"]["hans"], 0)
        self.assertEqual(r["plain"]["units"], 2)
        self.assertEqual(r["plain"]["with_t"], 1)
        self.assertEqual(r["plain"]["with_s"], 1)
        self.assertEqual(r["simplified_dirs"], 2)
        rows = {x["key"]: x for x in r["rows"]}
        self.assertTrue(rows["string:a"]["other_identical"])
        self.assertEqual(rows["string:a"]["other_dir"], "values-zh-rCN")
        self.assertFalse(rows["string:b"]["other_identical"])
        self.assertTrue(rows["string:b"]["other_available"])
        self.assertTrue(rows["string:b"]["has_own"])
        self.assertFalse(rows["string:a"]["has_own"])
        self.assertEqual(rows["string:a"]["chars"], "设这")
        self.assertEqual(rows["string:a"]["res_dir"], "res")

    def test_tables_and_grade(self):
        r = H.scan_strings(self.tmp, self.s, self.t)
        r.update(repo="x", status="ok")
        t, p2_sum, p2_n = H.tables([r])
        self.assertEqual(p2_n, 1)
        self.assertEqual(p2_sum, fractions.Fraction(1, 2))
        self.assertEqual(t["hant_with_simplified"]["units"], 4)
        self.assertEqual(t["hant_only"]["units"], 0)
        self.assertEqual(H.grade(t, p2_sum, p2_n)["P1"], "NOT TESTABLE (gate)")


def table(hant_units, hant_repos, hant_flagged, hant_rf, hans_units, hans_repos, hans_flagged,
          only_units, only_repos, only_flagged, both_units, both_flagged):
    return {
        "hant": {"units": hant_units, "repos": hant_repos, "flagged": hant_flagged,
                 "repos_flagged": hant_rf},
        "hans": {"units": hans_units, "repos": hans_repos, "flagged": hans_flagged,
                 "repos_flagged": 0},
        "hant_only": {"units": only_units, "repos": only_repos, "flagged": only_flagged},
        "hant_with_simplified": {"units": both_units, "repos": 1, "flagged": both_flagged},
    }


class TestGrade(unittest.TestCase):
    def test_all_held(self):
        t = table(300000, 700, 300, 70, 400000, 900, 50, 30000, 100, 10, 270000, 290)
        v = H.grade(t, fractions.Fraction(6), 12)
        self.assertEqual(v, {"P1": "HELD", "P2": "HELD", "P3": "HELD", "P4": "HELD"})

    def test_boundaries(self):
        # P1 exactly 10%: held. P2 just under half: failed. P3 equal shares: failed.
        t = table(300000, 700, 300, 70, 600000, 900, 600, 30000, 100, 30, 270000, 270)
        v = H.grade(t, fractions.Fraction(11, 2) + fractions.Fraction(-1, 1000), 11)
        self.assertEqual(v["P1"], "HELD")
        self.assertEqual(v["P2"], "FAILED")
        self.assertEqual(v["P3"], "FAILED")
        self.assertEqual(v["P4"], "FAILED")  # equal shares 30/30000 == 270/270000
        t["hant"]["repos_flagged"] = 69
        self.assertEqual(H.grade(t, fractions.Fraction(6), 12)["P1"], "FAILED")

    def test_gates(self):
        t = table(19999, 700, 300, 70, 400000, 900, 50, 30000, 100, 10, 270000, 290)
        self.assertEqual(set(H.grade(t, fractions.Fraction(6), 12).values()),
                         {"NOT TESTABLE (gate)"})
        t = table(300000, 700, 300, 70, 400000, 99, 50, 1999, 100, 10, 270000, 290)
        v = H.grade(t, fractions.Fraction(4), 9)
        self.assertEqual(v["P2"], "NOT TESTABLE")
        self.assertEqual(v["P3"], "NOT TESTABLE (gate)")
        self.assertEqual(v["P4"], "NOT TESTABLE (gate)")


if __name__ == "__main__":
    unittest.main()
