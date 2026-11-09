# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Tests for latin_langid.py (made with AI agents by MV2 of Munim, Inc.)."""
import collections
import os
import shutil
import tempfile
import unittest

import latin_langid as ll


def xml(pairs):
    body = "".join('  <string name="%s">%s</string>\n' % kv for kv in pairs)
    return '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n%s</resources>\n' % body


def rec(key, loc, doc, repo="r", source=False):
    r = {"repo": repo, "head": "h", "res_dir": "res", "locale_dir": loc, "key": key,
         "units": 10, "letters": 100, "latin": 100, "doc": doc, "siblings": [key], "ex": []}
    if source:
        r["source"] = True
    return r


IT = {"a": 0, "b": 1, "c": 2, "d": 3}
HU = {"w": 0, "x": 1, "y": 2, "z": 3}
EN = {"e": 0, "f": 1, "g": 2, "h": 3}


class TextTest(unittest.TestCase):
    def test_ngrams(self):
        self.assertEqual(list(ll.ngrams("ab")), ["a", "b", "_a", "ab", "b_", "_ab", "ab_"])

    def test_words(self):
        self.assertEqual(ll.words("Ops, qualcosa è andato storto dell\\'account! %1$s <b>x</b>"),
                         ["ops", "qualcosa", "è", "andato", "storto", "dell", "account", "x"])
        self.assertEqual(ll.words("{count} files &amp; https://x.org/a"), ["files"])

    def test_doc_stats(self):
        counts, letters, latin = ll.doc_stats(["ab", "Ab c"])
        self.assertEqual((letters, latin), (5, 5))
        self.assertEqual(counts["ab"], 2)
        self.assertEqual(counts["_c_"], 1)
        self.assertEqual(sum(counts.values()), 18)
        _, letters, latin = ll.doc_stats(["Открыть file"])
        self.assertEqual((letters, latin), (11, 4))

    def test_ranked_and_distance(self):
        self.assertEqual(ll.ranked(collections.Counter({"b": 2, "a": 2, "c": 1}), 2), ["a", "b"])
        self.assertEqual(ll.distance(["a", "b", "c"], {"b": 0, "a": 1}, 400), 402)

    def test_keys(self):
        self.assertEqual(ll.lang_key("in", ""), "id")
        self.assertEqual(ll.lang_key("no", None), "nb")
        self.assertEqual(ll.lang_key("sr", "Latn"), "sr-Latn")
        self.assertEqual(ll.lang_key("pt", ""), "pt")
        self.assertTrue(ll.close("nb", "da"))
        self.assertTrue(ll.close("sr-Latn", "hr"))
        self.assertTrue(ll.close("tr", "az"))
        self.assertFalse(ll.close("es", "it"))
        self.assertFalse(ll.close("hu", "ast"))
        self.assertFalse(ll.close("pt", "es"))


class ProfileTest(unittest.TestCase):
    def test_contrib_and_profiles(self):
        c = ll.repo_contrib({"x": [collections.Counter({"a": 3, "b": 1}),
                                   collections.Counter({"a": 1})]})
        self.assertAlmostEqual(c["x"]["a"], 0.875)
        self.assertAlmostEqual(c["x"]["b"], 0.125)
        glob = {}
        ll.merge_contrib(glob, c)
        ll.merge_contrib(glob, {"x": {"b": 1.0}, "y": {"q": 1.0}})
        self.assertEqual(glob["x"]["repos"], 2)
        self.assertAlmostEqual(glob["x"]["freq"]["b"], 1.125)
        self.assertEqual(ll.build_profiles(glob, min_repos=2, size=1), {"x": {"b": 0}})
        self.assertEqual(sorted(ll.build_profiles(glob, min_repos=1, size=5)), ["x", "y"])


class ClassifyTest(unittest.TestCase):
    def test_other_language(self):
        records = [
            rec("en", "values", ["a"], source=True),
            rec("it", "values-it", ["a", "b", "c", "d"]),        # r1
            rec("it", "values-it-rCH", ["a", "b", "d", "c"]),    # r2
            rec("hu", "values-hu", ["w", "x", "y", "z"]),        # r3
            rec("hu", "values-hu-rHU", ["x", "w", "y", "z"]),    # r4
            rec("it", "values-b+it", ["w", "x", "z", "y"]),      # r5: Hungarian in an it folder
            rec("ast", "values-ast", ["w", "x", "y", "z"]),      # r6: no ast profile
            rec("it", "values-it-rSM", ["a", "w", "b", "c"]),    # r7
        ]
        rows, q = ll.classify_rows(records, {"it": IT, "hu": HU}, size=4)
        self.assertEqual(len(rows), 7)
        self.assertEqual(q, {"it": 1.0, "hu": 0.125})
        got = [(r["locale_dir"], r["holds"], r["category"]) for r in rows if r["flagged"]]
        self.assertEqual(got, [("values-b+it", "hu", "other-language"),
                               ("values-ast", "hu", "other-language")])
        self.assertEqual([r["consistent"] for r in rows],
                         [True, True, True, True, False, None, True])
        self.assertEqual(rows[6]["d_holds"], 13)
        self.assertIsNone(rows[5]["d_own"])

    def test_english(self):
        records = [rec("en", "values", ["e", "f", "g", "h"], source=True),
                   rec("it", "values-it", ["e", "f", "g", "h"]),
                   rec("it", "values-it-rIT", ["a", "b", "c", "d"])]
        rows, q = ll.classify_rows(records, {"en": EN, "it": IT}, size=4)
        self.assertEqual(q, {"en": 0.0, "it": 1.0})
        self.assertEqual([r["category"] for r in rows], ["english", ""])

    def test_close_language_not_flagged(self):
        records = [rec("nb", "values-nb", ["a", "b", "c", "d"]),
                   rec("da", "values-da", ["w", "x", "y", "z"]),
                   rec("da", "values-da-rDK", ["a", "b", "c", "d"])]
        rows, _ = ll.classify_rows(records, {"nb": IT, "da": HU}, size=4)
        self.assertEqual([r["holds"] for r in rows], ["", "", ""])
        self.assertFalse(any(r["flagged"] for r in rows))
        self.assertEqual([r["consistent"] for r in rows], [True, True, True])


class GradeTest(unittest.TestCase):
    def row(self, repo, category="", holds="", siblings=(), consistent=True):
        return {"repo": repo, "res_dir": "res", "locale_dir": "values-x", "own_profile": True,
                "consistent": consistent, "category": category, "holds": holds,
                "siblings": list(siblings)}

    def test_gate(self):
        v = ll.grade(3999, 30, [], [])
        self.assertTrue(all(x.startswith("NOT TESTABLE (gate") for x in v.values()))
        v = ll.grade(4000, 19, [], [])
        self.assertTrue(v["S1"].startswith("NOT TESTABLE (gate"))

    def test_verdicts(self):
        rows = [self.row("r%d" % i) for i in range(600)]
        rows += [self.row("f%d" % i, "other-language", "hu", ["it", "hu"] if i < 3 else ["it"],
                          consistent=False) for i in range(5)]
        known = [{"checked": True, "right": True}, {"checked": True, "right": True},
                 {"checked": False, "right": False}]
        v = ll.grade(4000, 20, rows, known)
        # 600 of 605 consistent: 100*600 = 60000 >= 95*605 = 57475
        self.assertEqual(v, {"S0": "HELD", "S1": "HELD", "S2": "HELD", "S3": "HELD",
                             "S4": "HELD"})
        v = ll.grade(4000, 20, rows[:300] + rows[600:], known[:1])
        # 100*5 = 500 < 305 fails S2; 300 of 305 consistent still holds S0
        self.assertEqual((v["S0"], v["S2"], v["S3"]),
                         ("HELD", "FAILED", "NOT TESTABLE (1 known folders checked)"))

    def test_sample_and_h1(self):
        rows = [self.row("a", "other-language", "hu"), self.row("a", "other-language", "hu"),
                self.row("b", "english", "en"), self.row("c", "other-language", "it")]
        rows[1]["locale_dir"] = "values-y"
        s = ll.draw_sample(rows, size=24)
        self.assertEqual(sorted(r["repo"] for r in s), ["a", "c"])
        self.assertEqual(ll.grade_h1(["real"] * 6 + ["not"] * 2), "HELD")
        self.assertEqual(ll.grade_h1(["real"] * 5 + ["not"] * 3), "FAILED")
        self.assertEqual(ll.grade_h1(["real"] * 7), "NOT TESTABLE")

    def test_known_cases(self):
        r = {"repo": ll.THUNDERBIRD.upper(), "res_dir": ll.TB_RES, "locale_dir": "values-ast",
             "holds": "hu", "category": "other-language"}
        k = ll.known_cases([r])
        self.assertEqual([x["checked"] for x in k], [True, False, False])
        self.assertTrue(k[0]["right"])


class ScanTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        res = os.path.join(self.d, "app", "src", "main", "res")
        files = {
            "values": [("s0", "Open file"), ("s1", "Save"), ("s2", "OK")],
            "values-ast": [("s0", "Abrir ficheru")],
            "values-de": [("s0", "Открыть файл")],
            "values-it": [("s0", "Apri file"), ("s1", "Salva"), ("s2", "OK")],
            "values-ru": [("s0", "Открыть файл")],
            "values-ua": [("s0", "Відкрити файл")],
        }
        for folder, pairs in files.items():
            os.makedirs(os.path.join(res, folder))
            with open(os.path.join(res, folder, "strings.xml"), "w", encoding="utf-8") as f:
                f.write(xml(pairs))

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_scan_and_records(self):
        tree, failed = ll.scan_tree(self.d)
        self.assertEqual(failed, 0)
        self.assertEqual(len(tree), 1)
        rel, folders, src = tree[0]
        self.assertEqual(rel, "app/src/main/res")
        self.assertEqual([(f["locale_dir"], f["units"]) for f in folders],
                         [("values-ast", ["Abrir ficheru"]), ("values-de", ["Открыть файл"]),
                          ("values-it", ["Apri file", "Salva"]),
                          ("values-ru", ["Открыть файл"]), ("values-ua", ["Відкрити файл"])])
        self.assertEqual(src, ["Open file", "Save"])
        recs, contrib, elig = ll.build_records("r", "h", tree, min_units=1, min_letters=1)
        self.assertEqual([(r["key"], r.get("source", False)) for r in recs],
                         [("ast", False), ("it", False), ("en", True)])
        self.assertEqual(recs[1]["letters"], 13)
        self.assertEqual(recs[0]["siblings"], ["ast", "de", "it", "ru", "ua"])
        self.assertEqual(sorted(contrib), ["ast", "en", "it"])
        self.assertEqual(dict(elig), {"folders": 5, "not_a_language": 1, "non_latin_language": 1,
                                      "not_latin": 1, "checked": 2, "source_checked": 1})
        recs, _, elig = ll.build_records("r", "h", tree)
        self.assertEqual(recs, [])
        self.assertEqual(elig["too_small"], 3)


if __name__ == "__main__":
    unittest.main()
