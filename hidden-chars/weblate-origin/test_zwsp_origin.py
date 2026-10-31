# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for zwsp_origin.py (no network, no git)."""
import unittest

import zwsp_origin as zo

Z = chr(0x200B)


def commit(sha, parents, message="Update", email="dev@example.org"):
    return zo.Commit(sha, parents, email, email, "2025-01-02T03:04:05+00:00", message)


class ParseTest(unittest.TestCase):
    def test_parse_and_has(self):
        xml = ('<?xml version="1.0" encoding="utf-8"?>\n<resources>'
               '<string name="a">Добавлена ' + Z + Z + 'функция</string>'
               '<string name="b">plain</string>'
               '<string name="c">x\\u200By</string>'
               '<string name="d" translatable="false">' + Z + '</string>'
               '<plurals name="p"><item quantity="one">one</item><item quantity="other">a ' + Z + Z + 'b</item></plurals>'
               '</resources>').encode("utf-8")
        v = zo.parse_values(xml)
        self.assertTrue(zo.has_zwsp(v, "string:a", 0))
        self.assertFalse(zo.has_zwsp(v, "string:b", 0))
        self.assertTrue(zo.has_zwsp(v, "string:c", 0))
        self.assertIsNone(v["string:d"])
        self.assertFalse(zo.has_zwsp(v, "string:d", 0))
        self.assertFalse(zo.has_zwsp(v, "plurals:p", 0))
        self.assertTrue(zo.has_zwsp(v, "plurals:p", 1))
        self.assertFalse(zo.has_zwsp(v, "plurals:p", 2))
        self.assertFalse(zo.has_zwsp(None, "string:a", 0))
        self.assertIsNotNone(zo.PAIR_RE.search(v["string:a"][0]))
        self.assertIsNone(zo.PAIR_RE.search(v["string:c"][0]))

    def test_tree_names(self):
        data = (b"100644 strings.xml\0" + b"\x01" * 20 + b"40000 sub\0" + b"\x02" * 20 +
                b"100644 arrays.xml\0" + b"\x03" * 20 + b"100644 notes.txt\0" + b"\x04" * 20)
        self.assertEqual(zo.tree_xml_names(data), ["arrays.xml", "strings.xml"])

    def test_weblate_classifier(self):
        msg = ("Translated using Weblate (Dutch)\n\nCurrently translated at 99.1% (500 of 504 strings)\n\n"
               "Translation: app/strings\nTranslate-URL: https://hosted.weblate.org/projects/app/strings/nl/\n")
        self.assertTrue(zo.is_weblate(msg))
        self.assertEqual(zo.translate_host(msg), "hosted.weblate.org")
        self.assertTrue(zo.is_weblate("Added translation using Weblate (Hebrew)"))
        self.assertTrue(zo.is_weblate("Update", "hosted@weblate.org", "x@example.org"))
        self.assertTrue(zo.is_weblate("x\nTranslate-URL: https://translate.example.org/p/c/uk/"))
        self.assertEqual(zo.translate_host("x\nTranslate-URL: https://translate.example.org/p/c/uk/"),
                         "translate.example.org")
        self.assertFalse(zo.is_weblate("Update Russian translation", "dev@example.org", "dev@example.org"))
        self.assertFalse(zo.is_weblate("Merge upstream Element X"))
        self.assertEqual(zo.translate_host("no url"), "")

    def test_parse_log(self):
        text = ("aaa\x1fppp\x1fa@x.org\x1fc@x.org\x1f2024-05-06T07:08:09+00:00\x1fFirst line\n\nbody\n\x1e\n"
                "bbb\x1f\x1fa@x.org\x1fc@x.org\x1f2023-01-01T00:00:00+00:00\x1fRoot\n\x1e\n")
        cs = zo.parse_log(text)
        self.assertEqual([c.sha for c in cs], ["aaa", "bbb"])
        self.assertEqual(cs[0].parents, ["ppp"])
        self.assertEqual(cs[1].parents, [])
        self.assertEqual(cs[0].message, "First line\n\nbody\n")

    def test_select_rows(self):
        text = ("repo,head,platform,res_dir,locale_dir,lang,key,index,classes,codepoints,source,target\n"
                "r1,h1,weblate,app/res,values-nl,nl,string:a,0,zwsp,U+200B,S,T\n"
                "r2,h2,crowdin,app/res,values-nl,nl,string:a,0,zwsp,U+200B,S,T\n"
                "r3,h3,weblate,app/res,values-de,de,string:b,0,zwsp+bidi,U+200B U+200E,S,T\n"
                "r4,h4,weblate,res,values-ru,ru,plurals:p,1,zwsp,U+200B,S,\"T, with comma\"\n")
        rows = zo.select_rows(text)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], {"repo": "r1", "head": "h1", "folder": "app/res/values-nl", "lang": "nl",
                                   "key": "string:a", "index": 0})
        self.assertEqual(rows[1]["folder"], "res/values-ru")
        self.assertEqual(rows[1]["index"], 1)


class AttributeTest(unittest.TestCase):
    # Folder states by commit; None = folder absent.
    states = {
        "c5": {"string:a": ["x " + Z + Z + "y"], "string:b": ["n " + Z + "o"]},
        "c4": {"string:a": ["x y"], "string:b": ["n " + Z + "o"]},
        "c3": {"string:a": ["x " + Z + Z + "y"], "string:b": ["n " + Z + "o"]},
        "c2": {"string:a": ["x y"]},
        "c1": None,
    }
    log = [commit("c5", ["c4"], "Translated using Weblate (Dutch)"), commit("c4", ["c3"]),
           commit("c3", ["c2"]), commit("c2", ["c1"]), commit("c1", [])]

    def state(self, sha):
        return self.states.get(sha)

    def test_newest_introduction_wins(self):
        c, kind = zo.attribute(self.log, self.state, "string:a", 0)
        self.assertEqual(c.sha, "c5")
        self.assertEqual(kind, "edited")

    def test_key_added(self):
        c, kind = zo.attribute(self.log, self.state, "string:b", 0)
        self.assertEqual(c.sha, "c3")
        self.assertEqual(kind, "key-added")

    def test_folder_created_and_root(self):
        states = {"c2": {"string:a": [Z]}, "c1": None}
        log = [commit("c2", ["c1"]), commit("c1", [])]
        c, kind = zo.attribute(log, states.get, "string:a", 0)
        self.assertEqual((c.sha, kind), ("c2", "folder-created"))
        c, kind = zo.attribute([commit("r", [])], {"r": {"string:a": [Z]}}.get, "string:a", 0)
        self.assertEqual((c.sha, kind), ("r", "folder-created"))

    def test_index_added(self):
        states = {"c2": {"plurals:p": ["a", "b" + Z]}, "c1": {"plurals:p": ["a"]}}
        c, kind = zo.attribute([commit("c2", ["c1"])], states.get, "plurals:p", 1)
        self.assertEqual(kind, "key-added")

    def test_unattributed(self):
        # The U+200B is already in the parent of the oldest listed commit (e.g. came in via a merge).
        states = {"c2": {"string:a": [Z]}, "c1": {"string:a": [Z]}}
        c, kind = zo.attribute([commit("c2", ["c1"])], states.get, "string:a", 0)
        self.assertIsNone(c)
        self.assertEqual(kind, "")


def rows_for(spec):
    """spec: list of (repo, n_rows, n_weblate, n_arrived_among_non_weblate)."""
    out = []
    for repo, n, w, arrived in spec:
        for i in range(n):
            wb = 1 if i < w else 0
            kind = "edited"
            if not wb and i - w < arrived:
                kind = "key-added"
            out.append({"repo": repo, "status": "attributed", "weblate": wb, "kind": kind, "pair": 1,
                        "translate_host": "", "date": "2025-01-01"})
    return out


class GradeTest(unittest.TestCase):
    def test_gate(self):
        rows = rows_for([("r%d" % i, 4, 0, 4) for i in range(14)] + [("r14", 3, 0, 3)])  # 59 rows
        self.assertEqual(zo.grade(rows)["P1"], "NOT TESTABLE (gate)")
        rows = rows_for([("r%d" % i, 5, 0, 5) for i in range(14)])  # 70 rows, 14 repos
        self.assertEqual(zo.grade(rows)["P3"], "NOT TESTABLE (gate)")
        rows = rows_for([("r%d" % i, 4, 0, 4) for i in range(15)])
        rows.append({"repo": "x", "status": "unattributed"})
        self.assertEqual(zo.grade(rows)["P1"], "HELD")

    def test_all_held(self):
        # 15 repos x 4 rows; first 5 repos have 4 Weblate rows each -> 20/60 Weblate.
        # Non-Weblate rows: 40, all key-added -> P2 HELD. Dropping a Weblate repo: 16/56; any other: 20/56.
        spec = [("r%d" % i, 4, 4 if i < 5 else 0, 4) for i in range(15)]
        self.assertEqual(zo.grade(rows_for(spec)), {"P1": "HELD", "P2": "HELD", "P3": "HELD"})

    def test_p1_failed_at_half(self):
        # 30/60 Weblate is not below one half.
        spec = [("r%d" % i, 4, 2, 0) for i in range(15)]
        v = zo.grade(rows_for(spec))
        self.assertEqual(v["P1"], "FAILED")
        self.assertEqual(v["P2"], "FAILED")  # all 30 non-Weblate rows are edits

    def test_p3_failed_by_one_repo(self):
        # Repo A: 32 non-Weblate rows; 14 repos x 2 Weblate rows = 28. 28/60 < 0.5, but without A 28/28.
        spec = [("A", 32, 0, 16)] + [("r%d" % i, 2, 2, 0) for i in range(14)]
        v = zo.grade(rows_for(spec))
        self.assertEqual(v["P1"], "HELD")
        self.assertEqual(v["P2"], "HELD")  # 16 of 32 arrived = exactly one half
        self.assertEqual(v["P3"], "FAILED")

    def test_p2_not_testable_when_all_weblate(self):
        spec = [("r%d" % i, 4, 4, 0) for i in range(15)]
        v = zo.grade(rows_for(spec))
        self.assertEqual(v["P1"], "FAILED")
        self.assertEqual(v["P2"], "NOT TESTABLE")

    def test_summary_counts(self):
        spec = [("r%d" % i, 4, 4 if i < 5 else 0, 4) for i in range(15)]
        s = zo.summarize(rows_for(spec) + [{"repo": "z", "status": "clone-failed"}])
        self.assertEqual(s["rows_total"], 61)
        self.assertEqual(s["attributed"]["rows"], 60)
        self.assertEqual(s["attributed"]["weblate"], 20)
        self.assertEqual(s["attributed_repos"], 15)
        self.assertEqual(s["status_counts"], {"attributed": 60, "clone-failed": 1})
        self.assertEqual(s["kinds_non_weblate"], {"key-added": 40})
        self.assertEqual(s["per_repo_rows_weblate"]["r0"], [4, 4])


if __name__ == "__main__":
    unittest.main()
