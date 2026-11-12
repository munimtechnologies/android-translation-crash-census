# Tests for linguas_spelling.py (no network). Made with AI agents by MV2 of Munim, Inc.
# Licence: Apache-2.0.
import unittest

import linguas_spelling as ls


def res(repo, group, tokens, po, build="meson", status="ok"):
    ent = [dict(e, dir="po") for e in ls.check_dir(po, tokens)]
    return {"repo": repo, "group": group, "status": status, "commit": "c" * 40,
            "dirs": [{"dir": "po", "build": build, "linguas_read": True, "n_po": len(po),
                      "n_listed": len(tokens), "entries": ent}]}


def pos(*stems):
    return {s: "po/%s.po" % s for s in stems}


class Classify(unittest.TestCase):
    def test_ok(self):
        for t in ("de", "pt_BR", "zh_CN", "nb_NO", "es_419", "sr@latin", "ca@valencia",
                  "sr_RS@latin", "ckb", "fil"):
            self.assertEqual(ls.classify(t), ("ok", ""), t)

    def test_misspelled(self):
        cases = {"zh_cn": "zh_CN", "pt-BR": "pt_BR", "pt_br": "pt_BR", "nb-no": "nb_NO",
                 "zh-TW": "zh_TW", "es-419": "es_419", "DE": "de", "Zh_CN": "zh_CN",
                 "sr-RS@latin": "sr_RS@latin"}
        for t, p in cases.items():
            self.assertEqual(ls.classify(t), ("misspelled", p), t)

    def test_script(self):
        for t in ("zh_Hans", "zh_Hant", "sr_Latn", "zh-Hant-TW", "uz_Cyrl@x"):
            self.assertEqual(ls.classify(t), ("script", ""), t)

    def test_other(self):
        for t in ("de_FORM", "en_US_POSIX", "zh_CN.UTF-8", "zh_hans", "#", "x"):
            self.assertEqual(ls.classify(t), ("other", ""), t)


class CheckDir(unittest.TestCase):
    def test_entries(self):
        po = pos("de", "zh_cn", "pt-BR", "pt_BR", "zh_Hans")
        got = ls.check_dir(po, ["de", "zh_cn", "pt-BR", "pt_BR", "zh_Hans", "fr", "zh_cn"])
        self.assertEqual([e["token"] for e in got], ["zh_cn", "pt-BR", "zh_Hans"])
        zh, pt, hans = got
        self.assertEqual((zh["class"], zh["proposed"], zh["shadowed"], zh["proposed_po"]),
                         ("misspelled", "zh_CN", False, False))
        self.assertEqual((pt["shadowed"], pt["proposed_po"]), (True, True))
        self.assertEqual((hans["class"], hans["shadowed"], hans["proposed_po"]),
                         ("script", False, False))
        self.assertTrue(ls.is_flag(zh))
        self.assertFalse(ls.is_flag(pt))
        self.assertFalse(ls.is_flag(hans))

    def test_unbuilt_skipped(self):
        self.assertEqual(ls.check_dir(pos("de"), ["zh_cn", "de"]), [])


class Population(unittest.TestCase):
    def test_rows(self):
        data = ("repo,commit,group,status,seconds,n_paths,n_linguas_dirs,governed,dropped\n"
                "https://github.com/b/b,1,none,ok,1,1,1,yes,0\n"
                "https://github.com/a/a,2,gnome,ok,1,1,1,yes,0\n"
                "https://github.com/A/A,3,gnome,ok,1,1,1,yes,0\n"
                "https://github.com/c/c,4,none,ok,1,1,0,no,0\n"
                "https://github.com/d/d,5,none,error: x,1,1,1,yes,0\n").encode("utf-8")
        got = ls.population(data)
        self.assertEqual([(e["repo"], e["group"], e["v1_commit"]) for e in got],
                         [("https://github.com/a/a", "gnome", "2"),
                          ("https://github.com/b/b", "none", "1")])


class Grade(unittest.TestCase):
    def build(self, flagged_gnome=False):
        out = []
        for i in range(30):
            out.append(res("https://x/g%02d" % i, "gnome", ["de"], pos("de")))
        for i in range(60):
            out.append(res("https://x/o%02d" % i, "other", ["de", "fr"], pos("de", "fr")))
        out.append(res("https://x/f1", "other", ["zh_cn"], pos("zh_cn")))
        out.append(res("https://x/f2", "none", ["pt-BR", "de"], pos("pt-BR", "de")))
        out.append(res("https://x/f3", "none", ["nb-no", "pt_br"], pos("nb-no", "pt_br")))
        out.append(res("https://x/s1", "none", ["pt-BR", "pt_BR"], pos("pt-BR", "pt_BR")))
        out.append(res("https://x/h1", "weblate", ["zh_Hans"], pos("zh_Hans")))
        out.append(res("https://x/e1", "none", ["zh_cn"], pos("zh_cn"), status="timeout"))
        out.append(res("https://x/a1", "none", ["zh_cn"], pos("zh_cn"), build="other"))
        if flagged_gnome:
            out.append(res("https://x/gf", "gnome", ["zh_cn"], pos("zh_cn")))
        return out

    def test_verdicts(self):
        v, c, flagged = ls.grade(self.build(), gate_read=90, gate_governed=90)
        # read 96 (the timeout is not read); governed 95 (a1's build is not governed)
        self.assertEqual((c["read"], c["governed_repos"], c["flagged_repos"]), (96, 95, 3))
        self.assertEqual(v["G"], "PASSED")
        self.assertEqual(v["P1"], "HELD")  # 3/95 = 3.2%
        self.assertEqual(c["flagged_entries"], 4)
        self.assertEqual(c["flagged_zh_pt"], 3)
        self.assertEqual(c["flagged_hyphen"], 2)
        self.assertEqual(v["P2"], "HELD")
        self.assertEqual(v["P3"], "HELD")
        self.assertEqual(c["non_ok_entries_by_class"],
                         {"misspelled": 4, "misspelled (shadowed)": 1, "script": 1})
        self.assertEqual(c["flagged_tokens"], {"nb-no": 1, "pt-BR": 1, "pt_br": 1, "zh_cn": 1})
        rows = ls.sample_rows(flagged)
        self.assertEqual(len(rows), 3)
        self.assertEqual(sorted(r["repo"] for r in rows),
                         ["https://x/f1", "https://x/f2", "https://x/f3"])

    def test_gnome_flag_fails_p3(self):
        v, c, _ = ls.grade(self.build(flagged_gnome=True), gate_read=90, gate_governed=90)
        self.assertEqual(c["gnome_flagged"], 1)
        self.assertEqual(v["P3"], "FAILED")

    def test_p1_bounds(self):
        def run(n_ok, n_flag):
            rs = [res("https://x/o%03d" % i, "other", ["de"], pos("de")) for i in range(n_ok)]
            rs += [res("https://x/f%03d" % i, "other", ["zh_cn"], pos("zh_cn"))
                   for i in range(n_flag)]
            return ls.grade(rs, gate_read=10, gate_governed=10)[0]
        v = run(398, 0)
        self.assertEqual(v["P1"], "FAILED")  # 0 flagged
        self.assertEqual(v["P2"], "NOT TESTABLE (0 flagged entries)")
        self.assertEqual(run(398, 1)["P1"], "FAILED")  # 1/399 < 0.5%
        self.assertEqual(run(398, 2)["P1"], "HELD")  # 2/400 = 0.5%
        self.assertEqual(run(380, 20)["P1"], "HELD")  # 20/400 = 5%
        self.assertEqual(run(379, 21)["P1"], "FAILED")  # 21/400 > 5%

    def test_gate(self):
        v, _, _ = ls.grade(self.build())
        self.assertTrue(v["G"].startswith("FAILED"))
        self.assertEqual(v["P1"], "NOT TESTABLE (gate)")


if __name__ == "__main__":
    unittest.main()
