# Offline tests for xcode_lproj_v3.py (needs xcode_lproj_v2.py next to it; fetch_v2.py gets it).
# Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.
import unittest

import xcode_lproj_v3 as v3

PBX = """// !$*UTF8*$!
{
 archiveVersion = 1;
 objects = {
  R0 = {isa = PBXProject; mainGroup = G0; knownRegions = (en, de, Base, ); };
  G0 = {isa = PBXGroup; children = (G1, ); sourceTree = "<group>"; };
  G1 = {isa = PBXGroup; children = (V1, ); path = App; sourceTree = "<group>"; };
  V1 = {isa = PBXVariantGroup; children = (F1, F2, ); name = Localizable.strings; sourceTree = "<group>"; };
  F1 = {isa = PBXFileReference; name = en; path = en.lproj/Localizable.strings; sourceTree = "<group>"; };
  F2 = {isa = PBXFileReference; name = de; path = de.lproj/Localizable.strings; sourceTree = "<group>"; };
 };
 rootObject = R0;
}
"""

EN = b'"hello" = "Hello";\n"bye" = "Goodbye";\n'
DE = b'"hello" = "Hallo";\n"bye" = "Tschuess";\n'
FR = b'"hello" = "Bonjour";\n"bye" = "Au revoir";\n'
NL_COPY = b'"hello" = "Hello";\n"bye" = "Goodbye";\n'

FILES = {
    "App.xcodeproj/project.pbxproj": PBX.encode("utf-8"),
    "App/en.lproj/Localizable.strings": EN,
    "App/de.lproj/Localizable.strings": DE,
    "App/fr.lproj/Localizable.strings": FR,
    "App/nl.lproj/Localizable.strings": NL_COPY,
    "App/en-GB.lproj/Localizable.strings": EN,
    "App/de-AT.lproj/Localizable.strings": DE,
    "App/zh-Hant.lproj/Localizable.strings": FR,
    "App/it.lproj/Other.strings": FR,
}
MASKS = ["App/*.lproj/Localizable.strings"]


def reader(p):
    return FILES.get(p)


class Rules(unittest.TestCase):
    def test_mask_regex(self):
        rx = v3.mask_regex("Maccy/*.lproj/Localizable.strings")
        self.assertTrue(rx.match("Maccy/id.lproj/Localizable.strings"))
        self.assertFalse(rx.match("Maccy/Settings/id.lproj/Localizable.strings"))
        self.assertFalse(rx.match("Maccy/id.lproj/Other.strings"))
        sp = v3.mask_regex("MeetingBar/Resources /Localization /*.lproj/Localizable.strings")
        self.assertTrue(sp.match("MeetingBar/Resources /Localization /fr.lproj/Localizable.strings"))

    def test_regional_copy(self):
        self.assertTrue(v3.regional_copy("ja_JP", {"ja", "en"}))
        self.assertTrue(v3.regional_copy("es-419", {"es"}))
        self.assertTrue(v3.regional_copy("de-AT", {"DE"}))
        self.assertFalse(v3.regional_copy("zh-Hant", {"zh"}))
        self.assertFalse(v3.regional_copy("pt-BR", {"en", "de"}))
        self.assertFalse(v3.regional_copy("fr", {"fr"}))


class Analyse(unittest.TestCase):
    def setUp(self):
        self.res = v3.analyse_paths(sorted(FILES), reader, MASKS)

    def test_tables(self):
        r = self.res
        self.assertEqual([p["status"] for p in r["projects"]], ["ok"])
        self.assertEqual(r["managed_files"], 7)
        self.assertEqual(r["tables"], 1)
        self.assertEqual(r["managed_tables"], 1)
        self.assertTrue(r["translated"])
        self.assertEqual(r["skipped"], {"english": 1, "regional copy": 1})

    def test_lost(self):
        r = self.res
        langs = sorted(f["lang"] for f in r["lost"])
        self.assertEqual(langs, ["fr", "nl", "zh-Hant"])
        self.assertEqual(r["n_lost"], 3)
        by = dict((f["lang"], f) for f in r["lost"])
        self.assertEqual(by["fr"]["confirmed"], "yes")
        self.assertEqual(by["fr"]["reference"], "en")
        self.assertEqual(by["nl"]["confirmed"], "no")
        self.assertEqual(by["zh-Hant"]["confirmed"], "yes")
        self.assertTrue(by["fr"]["whole"])
        self.assertTrue(by["fr"]["in_known_regions"] is False)
        self.assertEqual(r["n_confirmed"], 2)

    def test_unmanaged_mask(self):
        r = v3.analyse_paths(sorted(FILES), reader, ["Other/*.lproj/Localizable.strings"])
        self.assertEqual(r["managed_files"], 0)
        self.assertEqual(r["managed_tables"], 0)
        self.assertFalse(r["translated"])

    def test_whole_false_when_language_ships_elsewhere(self):
        # Italian ships through another (non-Weblate) table, so its lost Localizable.strings
        # is a partial loss, not a whole-language loss.
        files = dict(FILES)
        pbx = PBX.replace("children = (V1, );", "children = (V1, V2, );").replace(
            "\n };\n rootObject",
            '\n  V2 = {isa = PBXVariantGroup; children = (F3, ); name = Other.strings; '
            'sourceTree = "<group>"; };\n'
            '  F3 = {isa = PBXFileReference; name = it; path = it.lproj/Other.strings; '
            'sourceTree = "<group>"; };\n };\n rootObject')
        self.assertIn("F3 = {", pbx)
        files["App.xcodeproj/project.pbxproj"] = pbx.encode("utf-8")
        files["App/it.lproj/Localizable.strings"] = FR
        r = v3.analyse_paths(sorted(files), files.get, MASKS)
        by = dict((f["lang"], f) for f in r["lost"])
        self.assertEqual(by["it"]["confirmed"], "yes")
        self.assertFalse(by["it"]["whole"])
        self.assertTrue(by["fr"]["whole"])
        self.assertEqual(r["managed_tables"], 1)


class Population(unittest.TestCase):
    def test_population(self):
        csv_text = (
            "project,component,file_format,filemask,template,repo,branch,repo_norm,apple\n"
            "a,one,strings,X/*.lproj/A.strings,,https://github.com/o/r,dev,https://github.com/o/r,1\n"
            "a,two,strings,X/*.lproj/B.strings,,https://github.com/o/r/,dev,https://github.com/O/r,1\n"
            "a,three,strings,X/*.lproj/C.strings,,https://github.com/o/r,main,https://github.com/o/r,1\n"
            "g,gl,strings,*.tbx,,local:,main,local:,1\n"
            "b,one,strings,Y/*.lproj/A.strings,,https://gitlab.com/p/q,,https://gitlab.com/p/q,1\n")
        pop = v3.population(csv_text.encode("utf-8"))
        self.assertEqual([e["repo"] for e in pop], ["https://github.com/o/r",
                                                     "https://gitlab.com/p/q"])
        self.assertEqual(pop[0]["branch"], "dev")
        self.assertTrue(pop[0]["branch_conflict"])
        self.assertEqual(len(pop[0]["masks"]), 3)
        self.assertEqual(pop[0]["components"], ["a/one", "a/two", "a/three"])
        self.assertEqual(pop[1]["branch"], "")
        self.assertFalse(pop[1]["branch_conflict"])


def fake(i, gov, conf, langs=()):
    r = {"repo": "https://example.org/r%d" % i, "status": "ok", "projects": [
        {"path": "A.xcodeproj/project.pbxproj", "status": "ok"}], "generated": [],
        "translated": gov, "managed_tables": 1 if gov else 0, "n_lost": conf,
        "n_confirmed": conf, "skipped": {}, "ref": "main", "commit": "c" * 40,
        "lost": [{"lang": lang, "whole": whole, "confirmed": "yes", "path": "A/%s.lproj/L.strings"
                  % lang, "table": "L.strings", "entries": 2, "differs": 2, "translated": 2}
                 for lang, whole in langs]}
    return r


class Grade(unittest.TestCase):
    def test_gate_fails(self):
        v, c, f = v3.grade([fake(i, True, 0) for i in range(12)])
        self.assertTrue(v["G"].startswith("FAILED"))
        self.assertEqual(v["P1"], "NOT TESTABLE (gate)")

    def test_verdicts(self):
        rs = [fake(i, i < 10, 0) for i in range(30)]
        rs[0] = fake(0, True, 2, [("fr", True), ("id", True)])
        rs[1] = fake(1, True, 1, [("tr", False)])
        v, c, f = v3.grade(rs)
        self.assertEqual(v["G"], "PASSED")
        self.assertEqual(v["P1"], "HELD (2 of 10)")
        self.assertEqual(v["P2"], "HELD (2 of 3 whole)")
        self.assertEqual(c["lost_languages"], 3)
        rows = v3.sample_rows(f)
        self.assertEqual(len(rows), 2)

    def test_p1_bounds(self):
        rs = [fake(i, i < 10, 0) for i in range(30)]
        rs[0] = fake(0, True, 1, [("fr", False)])
        v, c, f = v3.grade(rs)
        self.assertEqual(v["P1"], "FAILED (1 of 10)")
        self.assertEqual(v["P2"], "NOT TESTABLE (1 lost languages)")
        for i in range(6):
            rs[i] = fake(i, True, 1, [("fr", False)])
        v, c, f = v3.grade(rs)
        self.assertEqual(v["P1"], "FAILED (6 of 10)")
        self.assertEqual(v["P2"], "FAILED (0 of 6 whole)")


if __name__ == "__main__":
    unittest.main()
