#!/usr/bin/env python3
"""Offline tests for eval_fp.py. Apache-2.0. Made by MV2 of Munim, Inc. with AI agents."""

import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import eval_fp  # noqa: E402

# As written in READING-LEAK-PREREG.md.
RULE = re.compile(r"(?<=[^\s＃])＃[ァ-ヺー]+＃")


def row(id_, group, expected, matched, sign, fetched=True):
    return {"id": id_, "group": group, "expected_rule_lines": expected,
            "rule_lines": [{}] * matched, "sign_lines": sign, "fetched": fetched}


class ScanTest(unittest.TestCase):
    def test_counts(self):
        text = ('{\n "Delete": "削除＃サクジョ＃",\n "Tag": "＃タグ",\n "Plain": "検索",\n'
                ' "Two": "ロード＃ロード＃ ロック＃ロック＃"\n}')
        s = eval_fp.scan(text, RULE)
        self.assertEqual(s["sign_lines"], 3)
        self.assertEqual([m["line"] for m in s["rule_lines"]], [2, 5])
        self.assertEqual(s["rule_lines"][0]["matches"], ["＃サクジョ＃"])
        self.assertEqual(s["rule_lines"][1]["matches"], ["＃ロード＃", "＃ロック＃"])
        self.assertEqual([m["line"] for m in s["katakana_after_sign"]], [2, 3, 5])

    def test_other_uses_of_the_sign(self):
        text = ('"A": "文字列の＃ 終わりからの＃",\n"B": "最後から＃へ",\n"C": "{count, plural, other {＃件}}",\n'
                '"D": "＃サクジョ＃",\n"E": "ルール＃1"')
        s = eval_fp.scan(text, RULE)
        self.assertEqual(s["sign_lines"], 5)
        self.assertEqual(s["rule_lines"], [])
        self.assertEqual([m["line"] for m in s["katakana_after_sign"]], [4])

    def test_value_start_is_listed_apart(self):
        text = ('"D": "＃サクジョ＃",\nkey=＃サクジョ＃\n<translation>＃ロード＃</translation>\n'
                '"E": "削除＃サクジョ＃ ＃ロード＃"')
        s = eval_fp.scan(text, RULE)
        self.assertEqual([m["line"] for m in s["value_start"]], [1, 2, 3])
        self.assertEqual([m["line"] for m in s["rule_lines"]], [4])
        self.assertEqual(s["rule_lines"][0]["matches"], ["＃サクジョ＃"])

    def test_no_sign(self):
        s = eval_fp.scan("検索けんさく\nplain", RULE)
        self.assertEqual(s, {"sign_lines": 0, "rule_lines": [], "value_start": [],
                             "katakana_after_sign": []})


class GradeTest(unittest.TestCase):
    def held(self, results):
        return {c[0]: c[2] for c in eval_fp.grade(results)}

    def test_all_held(self):
        checks = eval_fp.grade([row("a", "leak", 2, 2, 2), row("b", "other", 0, 0, 85)])
        self.assertEqual([c[0] for c in checks], ["F0", "F1", "F2"])
        self.assertTrue(all(c[2] for c in checks))

    def test_extra_match_fails_f1(self):
        self.assertEqual(self.held([row("a", "leak", 2, 2, 2), row("b", "other", 0, 1, 85)]),
                         {"F0": True, "F1": False, "F2": True})

    def test_short_count_fails_f1(self):
        self.assertEqual(self.held([row("a", "leak", 2, 1, 2), row("b", "other", 0, 0, 85)]),
                         {"F0": True, "F1": False, "F2": True})

    def test_missing_file_fails_all(self):
        self.assertEqual(self.held([row("a", "leak", 2, 0, 0, fetched=False), row("b", "other", 0, 0, 85)]),
                         {"F0": False, "F1": False, "F2": False})

    def test_too_few_signs_fails_f2(self):
        self.assertEqual(self.held([row("a", "leak", 2, 2, 2), row("b", "other", 0, 0, 79)]),
                         {"F0": True, "F1": True, "F2": False})


class PopulationTest(unittest.TestCase):
    def test_population(self):
        rows = eval_fp.read_population(os.path.join(HERE, "population.csv"))
        self.assertEqual(len(rows), 33)
        self.assertEqual(sum(r["group"] == "leak" for r in rows), 5)
        self.assertEqual(sum(r["group"] == "other" for r in rows), 28)
        self.assertEqual(sum(int(r["expected_rule_lines"]) for r in rows), 25)
        self.assertEqual(len({r["id"] for r in rows}), 33)
        self.assertEqual(len({(r["repo"], r["path"]) for r in rows}), 33)
        for r in rows:
            self.assertRegex(r["commit"], r"^[0-9a-f]{40}$")
            if r["group"] == "other":
                self.assertEqual(r["expected_rule_lines"], "0")


class LoadRuleTest(unittest.TestCase):
    def test_pattern_is_the_preregistered_one(self):
        self.assertEqual(eval_fp.PREREG_PATTERN, RULE.pattern)

    def test_load_rule(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "g.py")
            with open(path, "w", encoding="utf-8") as f:
                f.write('import re\n__version__ = "0.11.0"\n'
                        '_READING_LEAK_RE = re.compile(r"(?<=[^\\s＃])＃[ァ-ヺー]+＃")\n')
            version, rule = eval_fp.load_rule(path)
        self.assertEqual(version, "0.11.0")
        self.assertEqual(rule.pattern, RULE.pattern)


if __name__ == "__main__":
    unittest.main()
