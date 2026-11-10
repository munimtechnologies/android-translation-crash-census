# Tests for xcode_lproj_census.py (standard library only). Made with AI agents by MV2 of
# Munim, Inc. Licence: Apache-2.0.
import unittest

import xcode_lproj_census as c

PBX = """// !$*UTF8*$!
{
	archiveVersion = 1;
	classes = {
	};
	objectVersion = 56;
	objects = {
		A1 /* Project object */ = {
			isa = PBXProject;
			developmentRegion = en;
			knownRegions = (
				en,
				fr,
				Base,
			);
			mainGroup = G0;
			projectDirPath = "";
		};
		G0 = {
			isa = PBXGroup;
			children = (
				G1 /* App */,
				F9 /* Assets */,
				F8 /* abs */,
			);
			sourceTree = "<group>";
		};
		G1 /* App */ = {
			isa = PBXGroup;
			children = (
				V1 /* Localizable.strings */,
				F7 /* it.lproj */,
			);
			path = App;
			sourceTree = "<group>";
		};
		V1 /* Localizable.strings */ = {
			isa = PBXVariantGroup;
			children = (
				F1 /* en */,
				F2 /* fr */,
			);
			name = Localizable.strings;
			sourceTree = "<group>";
		};
		F1 /* en */ = {isa = PBXFileReference; lastKnownFileType = text.plist.strings; name = en; path = en.lproj/Localizable.strings; sourceTree = "<group>"; };
		F2 /* fr */ = {isa = PBXFileReference; lastKnownFileType = text.plist.strings; name = fr; path = "fr.lproj/Localizable.strings"; sourceTree = "<group>"; };
		F7 /* it.lproj */ = {isa = PBXFileReference; lastKnownFileType = folder; path = it.lproj; sourceTree = "<group>"; };
		F8 /* abs */ = {isa = PBXFileReference; path = /abs/x.strings; sourceTree = "<absolute>"; };
		F9 /* Assets */ = {isa = PBXFileReference; lastKnownFileType = folder; path = Assets; sourceTree = SOURCE_ROOT; };
	};
	rootObject = A1 /* Project object */;
}
"""

PROJ = "ios/App.xcodeproj/project.pbxproj"
EN = '/* greeting */\n"hello" = "Hello";\n"bye" = "Bye";\n'
DE = '"hello" = "Hallo";\n// farewell\n"bye" = "Tschuess";\n'

PATHS = [
    PROJ,
    "ios/App/en.lproj/Localizable.strings",
    "ios/App/fr.lproj/Localizable.strings",
    "ios/App/de.lproj/Localizable.strings",
    "ios/App/it.lproj/Localizable.strings",
    "ios/App/en.lproj/InfoPlist.strings",
    "ios/App/de.lproj/InfoPlist.strings",
    "ios/Pods/Lib/ja.lproj/Localizable.strings",
    "README.md",
]

FILES = {
    PROJ: PBX.encode("utf-8"),
    "ios/App/en.lproj/Localizable.strings": EN.encode("utf-8"),
    "ios/App/de.lproj/Localizable.strings": DE.encode("utf-16"),
}


def reader(files):
    return lambda p: files.get(p)


class PlistTest(unittest.TestCase):
    def test_parse_values(self):
        v = c.parse_plist('{ a = "x\\"y"; b = ( 1, two, ); c = {}; /* note */ d = "\\U00e9"; }')
        self.assertEqual(v["a"], 'x"y')
        self.assertEqual(v["b"], ["1", "two"])
        self.assertEqual(v["c"], {})
        self.assertEqual(v["d"], chr(0xE9))

    def test_bad_input_raises(self):
        with self.assertRaises(ValueError):
            c.parse_plist("{ a = (1 2); }")

    def test_norm(self):
        self.assertEqual(c.norm("a/./b/../c"), "a/c")
        self.assertEqual(c.norm("/"), "")
        self.assertIsNone(c.norm("../x"))


class ProjectTest(unittest.TestCase):
    def test_refs_and_regions(self):
        refs, regions = c.project_refs(PROJ, c.parse_plist(PBX))
        self.assertEqual(sorted(refs), ["ios/App/en.lproj/Localizable.strings",
                                        "ios/App/fr.lproj/Localizable.strings",
                                        "ios/App/it.lproj", "ios/Assets"])
        self.assertEqual(regions, ["en", "fr", "Base"])

    def test_project_at_root(self):
        refs, _ = c.project_refs("App.xcodeproj/project.pbxproj", c.parse_plist(PBX))
        self.assertIn("App/fr.lproj/Localizable.strings", refs)
        self.assertIn("Assets", refs)

    def test_covered(self):
        refs = {"ios/App/it.lproj", "x/y.strings"}
        self.assertTrue(c.covered("ios/App/it.lproj/Localizable.strings", refs))
        self.assertTrue(c.covered("x/y.strings", refs))
        self.assertFalse(c.covered("ios/App/de.lproj/Localizable.strings", refs))


class StringsTest(unittest.TestCase):
    def test_utf16_with_bom(self):
        self.assertEqual(c.strings_table(c.decode_strings(DE.encode("utf-16"))),
                         {"hello": "Hallo", "bye": "Tschuess"})

    def test_unquoted_key_and_fallback(self):
        self.assertEqual(c.strings_table('CFBundleName = "Kalender";'),
                         {"CFBundleName": "Kalender"})
        self.assertEqual(c.strings_table('"a" = "b";\n"c" = "d"'), {"a": "b"})

    def test_stats(self):
        st = c.content_stats({"a": "x", "b": "B", "z": "q"}, {"a": "A", "b": "B"})
        self.assertEqual(st, {"entries": 3, "compared": 2, "differs": 1})
        self.assertEqual(c.substantive(st), "yes")
        self.assertEqual(c.substantive({"entries": 3, "compared": 3, "differs": 1}), "no")
        self.assertEqual(c.substantive({"entries": 0, "compared": 0, "differs": 0}), "no")
        self.assertEqual(c.substantive({"entries": 2, "compared": 0, "differs": 0}), "unknown")
        self.assertEqual(c.substantive(None), "unknown")


class AnalyseTest(unittest.TestCase):
    def test_finds_only_the_unlisted_language(self):
        res = c.analyse_paths(PATHS, reader(FILES))
        self.assertEqual(res["tables"], 2)
        self.assertEqual(res["managed_tables"], 1)
        self.assertEqual(res["n_unreferenced"], 1)
        f = res["unreferenced"][0]
        self.assertEqual((f["path"], f["lang"], f["table"], f["listed"]),
                         ("ios/App/de.lproj/Localizable.strings", "de",
                          "Localizable.strings", 2))
        self.assertFalse(f["in_known_regions"])
        self.assertEqual((f["entries"], f["compared"], f["differs"], f["reference"]),
                         (2, 2, 2, "en"))
        self.assertEqual(f["substantive"], "yes")
        self.assertEqual(res["projects"][0]["status"], "ok")
        self.assertEqual(res["generated"], [])

    def test_package_folders_are_left_out(self):
        res = c.analyse_paths(PATHS + ["ios/App/Package.swift"], reader(FILES))
        self.assertEqual(res["excluded_package"], 6)
        self.assertEqual(res["tables"], 0)
        self.assertEqual(res["n_unreferenced"], 0)

    def test_generated_projects_are_not_governed(self):
        res = c.analyse_paths(PATHS + ["project.yml", "crowdin.yml"], reader(FILES))
        self.assertEqual(res["generated"], ["project.yml"])
        self.assertEqual(res["platform"], ["crowdin.yml"])
        self.assertFalse(c.governed(dict(res, status="ok")))
        res = c.analyse_paths(PATHS, reader(FILES))
        self.assertTrue(c.governed(dict(res, status="ok")))

    def test_unparsable_project(self):
        files = dict(FILES)
        files[PROJ] = b"{ objects = ( ; }"
        res = c.analyse_paths(PATHS, reader(files))
        self.assertTrue(res["projects"][0]["status"].startswith("parse error"))
        self.assertEqual(res["managed_tables"], 0)


def fake(i, governed, flagged, platform=False):
    return {"repo": "https://github.com/o/r%d" % i, "commit": "c%d" % i, "status": "ok",
            "generated": [], "platform": ["crowdin.yml"] if platform else [],
            "managed_tables": 1 if governed else 0, "n_unreferenced": 1 if flagged else 0,
            "projects": [{"path": "A.xcodeproj/project.pbxproj", "status": "ok"}],
            "unreferenced": [{"path": "A/de.lproj/L.strings", "lang": "de", "table": "L.strings",
                              "listed": 2, "in_known_regions": False, "entries": 2,
                              "compared": 2, "differs": 2, "substantive": "yes"}]
            if flagged else []}


class GradeTest(unittest.TestCase):
    def test_verdicts(self):
        rs = [fake(i, governed=i < 120, flagged=i < 12, platform=i < 30) for i in range(300)]
        v, counts, flagged = c.grade(rs)
        self.assertEqual(v["G"], "PASSED")
        self.assertEqual(v["P1"], "HELD (12 of 120)")
        self.assertEqual(v["P2"], "HELD (12 of 12)")
        self.assertEqual(v["P3"], "HELD (12 of 30 vs 0 of 90)")
        self.assertEqual(counts["governed"], 120)
        rows = c.sample_rows(flagged)
        self.assertEqual(len(rows), 12)
        self.assertEqual(sorted(r["sample"] for r in rows), list(range(1, 13)))

    def test_gate(self):
        rs = [fake(i, governed=i < 50, flagged=i < 5) for i in range(300)]
        v, _, _ = c.grade(rs)
        self.assertTrue(v["G"].startswith("FAILED"))
        self.assertEqual(v["P1"], "NOT TESTABLE (gate)")

    def test_population(self):
        raw = ("repo,commit,status,translated\nhttps://github.com/a/b,c1,ok,yes\n"
               "https://github.com/a/c,,error: x,no\nhttps://github.com/a/d,c3,ok,no\n"
               "https://github.com/A/B,c9,ok,yes\n").encode("utf-8")
        self.assertEqual(c.population(raw), [{"repo": "https://github.com/a/b", "commit": "c1"}])


if __name__ == "__main__":
    unittest.main()
