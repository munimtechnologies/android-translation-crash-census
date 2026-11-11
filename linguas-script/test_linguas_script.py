# Tests for linguas_script.py (pure functions only; no network, no git, no gettext needed).
# Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.
import unittest

import linguas_script as ls


class Codes(unittest.TestCase):
    def test_split(self):
        self.assertEqual(ls.split_code("zh_Hant_HK"), ("zh", ["Hant", "HK"], ""))
        self.assertEqual(ls.split_code("sr_RS.UTF-8@latin"), ("sr", ["RS"], "latin"))
        self.assertEqual(ls.split_code("de"), ("de", [], ""))

    def test_classify(self):
        for c in ("zh_Hans", "zh_Hant", "sr_Latn", "zh_Hant_HK", "uz_Cyrl", "zh_hans"):
            self.assertEqual(ls.classify(c), "script", c)
        for c in ("zh_CN", "zh_TW", "sr@latin", "pt_BR", "es_419", "de", "ca@valencia",
                  "de_FORM", "nb_NO", "kab"):
            self.assertEqual(ls.classify(c), "posix", c)
        for c in ("pt-BR", "zh-Hans"):
            self.assertEqual(ls.classify(c), "hyphen", c)

    def test_siblings(self):
        toks = ["de", "zh_Hans", "zh_Hant", "zh_TW", "sr_Latn", "sr", "zh-CN"]
        self.assertEqual(ls.reachable_siblings("zh_Hans", toks), ["zh_TW"])
        self.assertEqual(ls.reachable_siblings("sr_Latn", toks), ["sr"])
        self.assertEqual(ls.reachable_siblings("uz_Latn", toks), [])

    def test_dir_findings(self):
        f = ls.dir_findings(["ar", "zh_Hans", "zh_Hant", "pt-BR", "sr_Latn", "sr", "zh_Hans"])
        self.assertEqual(f["script"], ["zh_Hans", "zh_Hant", "sr_Latn"])
        self.assertEqual(f["hyphen"], ["pt-BR"])
        self.assertEqual(f["lost"], ["zh_Hans", "zh_Hant"])
        self.assertEqual(f["siblings"]["sr_Latn"], ["sr"])
        g = ls.dir_findings(["de", "fr"])
        self.assertEqual((g["script"], g["lost"], g["hyphen"]), ([], [], []))

    def test_linguas_readers(self):
        text = "# keep sorted\nde fr\nzh_Hans # simplified\n"
        self.assertEqual(ls.meson_linguas(text), ["de", "fr", "zh_Hans", "#", "simplified"])
        self.assertEqual(ls.gnu_linguas(text), ["de", "fr", "zh_Hans"])

    def test_locale_key(self):
        self.assertEqual(ls.locale_key("sr_RS.UTF-8@latin"), "sr_rs.utf8@latin")
        self.assertEqual(ls.locale_key("zh_CN.utf8"), "zh_cn.utf8")


class PoStats(unittest.TestCase):
    def test_counts(self):
        data = ('msgid ""\nmsgstr "Content-Type: text/plain; charset=UTF-8\\n"\n\n'
                'msgid "a"\nmsgstr "x"\n\n#, fuzzy\nmsgid "b"\nmsgstr "y"\n\n'
                'msgid "c"\nmsgstr ""\n\n#~ msgid "d"\n#~ msgstr "z"\n').encode("utf-8")
        self.assertEqual(ls.po_stats(data), {"entries": 3, "translated": 1, "fuzzy": 1})
        self.assertEqual(ls.substantive({"entries": 3, "translated": 1, "fuzzy": 1}), "no")
        self.assertEqual(ls.substantive({"entries": 4, "translated": 2, "fuzzy": 0}), "yes")
        self.assertEqual(ls.substantive(None), "unknown")


class Mechanism(unittest.TestCase):
    def good(self):
        c = {loc: [] for loc in ls.MECH_LOCALES}
        c["zh_CN.UTF-8"] = ["zh_CN"]
        c["zh_TW.UTF-8"] = ["zh_TW"]
        c["sr_RS.UTF-8@latin"] = ["sr@latin"]
        c["pt_BR.UTF-8"] = ["pt_BR"]
        lang = {code: True for code in ls.MECH_SCRIPT}
        return {"locales": {name: True for _, name in ls.LOCALEDEF}, "errors": [],
                "c": c, "py": dict(c), "c_language": lang, "py_language": dict(lang)}

    def test_held(self):
        self.assertEqual(ls.grade_mechanism(self.good()), {"M1": "HELD", "M2": "HELD"})

    def test_script_reached_fails(self):
        m = self.good()
        m["c"] = dict(m["c"])
        m["c"]["zh_CN.UTF-8"] = ["zh_CN", "zh_Hans"]
        v = ls.grade_mechanism(m)
        self.assertTrue(v["M1"].startswith("FAILED"))
        self.assertEqual(v["M2"], "HELD")

    def test_control_missing_fails(self):
        m = self.good()
        m["py"] = dict(m["py"])
        m["py"]["pt_BR.UTF-8"] = []
        self.assertTrue(ls.grade_mechanism(m)["M2"].startswith("FAILED"))

    def test_language_needed(self):
        m = self.good()
        m["py_language"] = dict(m["py_language"], sr_Latn=False)
        self.assertTrue(ls.grade_mechanism(m)["M2"].startswith("FAILED"))

    def test_locales_missing(self):
        m = self.good()
        m["locales"] = dict(m["locales"], **{"zh_HK.UTF-8": False})
        v = ls.grade_mechanism(m)
        self.assertEqual(v["M1"], "NOT TESTABLE (locales missing: zh_HK.UTF-8)")
        self.assertEqual(v["M2"], "HELD")

    def test_build_error(self):
        m = self.good()
        m["errors"] = ["msgfmt zh_Hans: boom"]
        self.assertTrue(ls.grade_mechanism(m)["M1"].startswith("NOT TESTABLE"))


def repo(name, group, script=(), lost=(), files=(), build="meson"):
    return {"repo": name, "group": group, "status": "ok", "commit": "c" * 40,
            "dirs": [{"dir": "po", "build": build, "linguas_read": True, "script": list(script),
                      "hyphen": [], "lost": list(lost), "remap": [],
                      "siblings": {t: [] for t in script}, "files": list(files)}]}


def lostfile(code, translated, entries):
    return {"code": code, "path": "po/%s.po" % code, "entries": entries,
            "translated": translated, "fuzzy": 0,
            "substantive": ls.substantive({"entries": entries, "translated": translated})}


class Grade(unittest.TestCase):
    def population(self):
        res = []
        for i in range(100):
            res.append(repo("https://x/w%d" % i, "weblate" if i < 30 else "none"))
        res.append(repo("https://x/o", "none", build="other", script=["zh_Hans"]))
        for i in range(950):
            res.append({"repo": "https://x/n%d" % i, "group": "none", "status": "ok",
                        "commit": "", "dirs": []})
        return res

    def test_gate_fails(self):
        v, counts, _ = ls.grade([repo("https://x/a", "none")])
        self.assertTrue(v["G"].startswith("FAILED"))
        self.assertEqual(v["P1"], "NOT TESTABLE (gate)")
        self.assertEqual(counts["governed_repos"], 1)

    def test_verdicts(self):
        res = self.population()
        # 150 governed: 100 above plus 50 more, five of them flagged (3.3%)
        for i in range(45):
            res.append(repo("https://x/g%d" % i, "none"))
        res.append(repo("https://x/f1", "weblate", ["zh_Hans", "zh_Hant"], ["zh_Hans", "zh_Hant"],
                        [lostfile("zh_Hans", 90, 100), lostfile("zh_Hant", 10, 100)]))
        res.append(repo("https://x/f2", "weblate", ["zh_Hans"], ["zh_Hans"],
                        [lostfile("zh_Hans", 80, 100)]))
        res.append(repo("https://x/f3", "none", ["sr_Latn"], [], []))
        res.append(repo("https://x/f4", "weblate", ["zh_Hans"], ["zh_Hans"],
                        [lostfile("zh_Hans", 100, 100)]))
        res.append(repo("https://x/f5", "none", ["zh_Hant"], ["zh_Hant"],
                        [lostfile("zh_Hant", 60, 100)]))
        v, counts, flagged = ls.grade(res)
        self.assertEqual(v["G"], "PASSED")
        self.assertEqual(counts["governed_repos"], 150)
        self.assertEqual(counts["flagged_repos"], 5)
        self.assertEqual(v["P1"], "HELD")
        self.assertEqual(counts["lost_repos"], 4)
        self.assertEqual(v["P2"], "HELD")
        # weblate: 3 of 33 flagged; other: 2 of 117
        self.assertEqual((counts["weblate_flagged"], counts["weblate_governed"]), (3, 33))
        self.assertEqual(v["P3"], "HELD")
        # 6 script codes, 5 of them zh: 20 >= 18
        self.assertEqual((counts["script_codes"], counts["zh_script_codes"]), (6, 5))
        self.assertEqual(v["P4"], "HELD")
        # 5 lost files read: 4 substantive (16 >= 15)
        self.assertEqual((counts["content_known"], counts["content_substantive"]), (5, 4))
        self.assertEqual(v["P5"], "HELD")
        self.assertEqual(counts["lost_translated_messages"], 340)
        rows = ls.sample_rows(flagged)
        self.assertEqual(len(rows), 4)
        self.assertEqual(sorted(r["repo"] for r in rows),
                         ["https://x/f1", "https://x/f2", "https://x/f4", "https://x/f5"])
        self.assertEqual([r["sample"] for r in rows], [1, 2, 3, 4])

    def test_p1_too_high(self):
        res = self.population()
        for i in range(50):
            res.append(repo("https://x/s%d" % i, "none", ["zh_Hans"], ["zh_Hans"],
                            [lostfile("zh_Hans", 1, 100)]))
        v, counts, _ = ls.grade(res)
        self.assertEqual(counts["flagged_repos"], 50)
        self.assertEqual(v["P1"], "FAILED")
        self.assertEqual(v["P3"], "FAILED")
        self.assertEqual(v["P5"], "FAILED")


if __name__ == "__main__":
    unittest.main()
