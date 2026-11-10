# Tests for xcode_lproj_v2.py (standard library only). Made with AI agents by MV2 of
# Munim, Inc. Licence: Apache-2.0.
import json
import unittest

import xcode_lproj_v2 as c

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
NL_COPY = '"hello" = "Hello";\n"bye" = "Bye";\n'

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
    "ios/App/nl.lproj/Localizable.strings": NL_COPY.encode("utf-8"),
    "ios/App/sv.lproj/Localizable.strings": b"",
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

    def test_refs_and_regions(self):
        refs, regions = c.project_refs(PROJ, c.parse_plist(PBX))
        self.assertEqual(sorted(refs), ["ios/App/en.lproj/Localizable.strings",
                                        "ios/App/fr.lproj/Localizable.strings",
                                        "ios/App/it.lproj", "ios/Assets"])
        self.assertEqual(regions, ["en", "fr", "Base"])

    def test_utf16_with_bom(self):
        self.assertEqual(c.strings_table(c.decode_strings(DE.encode("utf-16"))),
                         {"hello": "Hallo", "bye": "Tschuess"})


class ContentTest(unittest.TestCase):
    """The six kinds of false finding seen in the v1 hand check must not count."""

    def test_not_translations(self):
        self.assertFalse(c.is_translated("k", "  ", None))
        self.assertFalse(c.is_translated("All notes off.", "All notes off.", None))
        self.assertFalse(c.is_translated("CFBundleName", "$(PRODUCT_NAME)", None))
        self.assertFalse(c.is_translated("CFBundleName", "${PRODUCT_NAME} ", None))
        tmpl = ("Copyright " + chr(0xA9) + " " + chr(0xAB) + "YEAR" + chr(0xBB) + " "
                + chr(0xAB) + "ORGANIZATIONNAME" + chr(0xBB))
        self.assertFalse(c.is_translated("NSHumanReadableCopyright", tmpl, None))
        self.assertFalse(c.is_translated("NSHumanReadableCopyright",
                                         "Copyright __MyCompanyName__", None))
        self.assertFalse(c.is_translated("CFBundleDisplayName", "Table Habit (Dev)",
                                         {"CFBundleDisplayName": "Table Habit (Dev)"}))
        self.assertFalse(c.is_translated("count", "%d", None))
        self.assertFalse(c.is_translated("a", "b", {"a": "b "}))

    def test_translations(self):
        self.assertTrue(c.is_translated("home", chr(0xD648), None))
        self.assertTrue(c.is_translated("items", "%1$@ Elemente", {"items": "%1$@ items"}))
        self.assertTrue(c.is_translated("hello", "Hallo", {"hello": "Hello"}))

    def test_stats_and_confirmed(self):
        st = c.content_stats({"a": "x", "b": "B", "z": "q"}, {"a": "A", "b": "B"})
        self.assertEqual(st, {"entries": 3, "compared": 2, "differs": 1, "translated": 2})
        self.assertEqual(c.confirmed(st), "yes")
        self.assertEqual(c.confirmed(None), "unread")
        self.assertEqual(c.confirmed({"entries": 0, "compared": 0, "differs": 0,
                                      "translated": 0}), "no")
        self.assertEqual(c.confirmed({"entries": 3, "compared": 3, "differs": 1,
                                      "translated": 1}), "no")
        self.assertEqual(c.confirmed({"entries": 2, "compared": 0, "differs": 0,
                                      "translated": 2}), "yes")
        self.assertEqual(c.content_stats({}, None),
                         {"entries": 0, "compared": 0, "differs": 0, "translated": 0})

    def test_english_and_generators(self):
        self.assertTrue(c.english("en-GB"))
        self.assertTrue(c.english("Base"))
        self.assertTrue(c.english("English"))
        self.assertTrue(c.english("en"))
        self.assertFalse(c.english("eu"))
        self.assertFalse(c.english("enm"))
        self.assertEqual(c.generators(["project.yml", "a/b.swift"]), ["project.yml"])
        self.assertEqual(c.generators(["KsApi/models/Project.swift"]), [])
        self.assertEqual(c.generators(["Project.swift", "Tuist/Config.swift"]),
                         ["Project.swift"])
        self.assertEqual(c.generators(["Pods/X/project.yml"]), [])


class AnalyseTest(unittest.TestCase):
    def test_finds_only_the_unlisted_language(self):
        res = c.analyse_paths(PATHS, reader(FILES))
        self.assertTrue(res["translated"])
        self.assertEqual(res["tables"], 2)
        self.assertEqual(res["managed_tables"], 1)
        self.assertEqual(res["n_unreferenced"], 1)
        self.assertEqual(res["n_confirmed"], 1)
        f = res["unreferenced"][0]
        self.assertEqual((f["path"], f["lang"], f["table"], f["listed"]),
                         ("ios/App/de.lproj/Localizable.strings", "de",
                          "Localizable.strings", 2))
        self.assertEqual((f["entries"], f["compared"], f["differs"], f["translated"],
                          f["reference"], f["confirmed"]), (2, 2, 2, 2, "en", "yes"))
        self.assertTrue(c.governed(dict(res, status="ok")))

    def test_copies_and_empty_files_are_not_confirmed(self):
        paths = PATHS + ["ios/App/nl.lproj/Localizable.strings",
                         "ios/App/sv.lproj/Localizable.strings"]
        res = c.analyse_paths(paths, reader(FILES))
        self.assertEqual(res["n_unreferenced"], 3)
        self.assertEqual(res["n_confirmed"], 1)
        got = dict((f["lang"], f["confirmed"]) for f in res["unreferenced"])
        self.assertEqual(got, {"de": "yes", "nl": "no", "sv": "no"})

    def test_untranslated_repository_is_not_governed(self):
        paths = [PROJ, "ios/App/en.lproj/Localizable.strings"]
        res = c.analyse_paths(paths, reader(FILES))
        self.assertFalse(res["translated"])
        self.assertEqual(res["managed_tables"], 1)
        self.assertFalse(c.governed(dict(res, status="ok")))

    def test_generated_and_model_files(self):
        res = c.analyse_paths(PATHS + ["project.yml", "crowdin.yml"], reader(FILES))
        self.assertEqual(res["generated"], ["project.yml"])
        self.assertEqual(res["platform"], ["crowdin.yml"])
        self.assertFalse(c.governed(dict(res, status="ok")))
        res = c.analyse_paths(PATHS + ["KsApi/models/Project.swift"], reader(FILES))
        self.assertEqual(res["generated"], [])
        self.assertTrue(c.governed(dict(res, status="ok")))

    def test_package_folders_are_left_out(self):
        res = c.analyse_paths(PATHS + ["ios/App/Package.swift"], reader(FILES))
        self.assertEqual(res["excluded_package"], 6)
        self.assertEqual(res["tables"], 0)
        self.assertEqual(res["n_unreferenced"], 0)


def fake(i, governed, flagged, unref, platform=False):
    f = {"path": "A/de.lproj/L.strings", "lang": "de", "table": "L.strings", "listed": 2,
         "in_known_regions": False, "entries": 2, "compared": 2, "differs": 2,
         "translated": 2 if flagged else 0, "confirmed": "yes" if flagged else "no"}
    return {"repo": "https://github.com/o/r%d" % i, "commit": "c%d" % i,
            "committed": "2026-01-01T00:00:00Z", "status": "ok", "translated": True,
            "generated": [], "platform": ["crowdin.yml"] if platform else [],
            "managed_tables": 1 if governed else 0,
            "n_unreferenced": 1 if (flagged or unref) else 0,
            "n_confirmed": 1 if flagged else 0,
            "projects": [{"path": "A.xcodeproj/project.pbxproj", "status": "ok"}],
            "unreferenced": [f] if (flagged or unref) else []}


class GradeTest(unittest.TestCase):
    def test_verdicts(self):
        rs = [fake(i, governed=i < 120, flagged=i < 12, unref=i < 30, platform=i < 30)
              for i in range(300)]
        v, counts, flagged = c.grade(rs)
        self.assertEqual(v["G"], "PASSED")
        self.assertEqual(v["P1"], "HELD (12 of 120)")
        self.assertEqual(v["P2"], "HELD (12 of 30)")
        self.assertEqual(v["P3"], "HELD (12 of 30 vs 0 of 90)")
        self.assertEqual((counts["governed"], counts["any_unreferenced"],
                          counts["active_governed"], counts["active_flagged"],
                          counts["files_unread"]), (120, 30, 120, 12, 0))
        rows = c.sample_rows(flagged)
        self.assertEqual(len(rows), 12)
        self.assertEqual(sorted(r["sample"] for r in rows), list(range(1, 13)))

    def test_gate_and_p2_not_testable(self):
        rs = [fake(i, governed=i < 50, flagged=i < 5, unref=False) for i in range(300)]
        v, _, _ = c.grade(rs)
        self.assertTrue(v["G"].startswith("FAILED"))
        self.assertEqual(v["P1"], "NOT TESTABLE (gate)")
        rs = [fake(i, governed=i < 120, flagged=i < 5, unref=False) for i in range(300)]
        v, _, _ = c.grade(rs)
        self.assertEqual(v["P2"], "NOT TESTABLE (5 repositories with any unreferenced file)")


class PopulationTest(unittest.TestCase):
    def test_population(self):
        apps = {"applications": [
            {"repo_url": "https://github.com/A/One"},
            {"repo_url": "https://github.com/a/one.git"},
            {"repo_url": "https://github.com/borgbase"},
            {"repo_url": "https://gitlab.com/x/y"},
            {"repo_url": "https://github.com/b/two/tree/master/sub"},
            {"repo_url": "https://github.com/c/old"},
            {"title": "no url"},
            "junk"]}
        old = "repo,commit,status,translated\nhttps://github.com/C/Old,c1,ok,yes\n"
        repos, n = c.population(json.dumps(apps).encode("utf-8"), old.encode("utf-8"))
        self.assertEqual(n, 8)
        self.assertEqual(repos, ["https://github.com/A/One", "https://github.com/b/two"])
        self.assertIsNone(c.gh_repo("https://github.com/orgs/foo"))


if __name__ == "__main__":
    unittest.main()
