# Tests for xcproj_l10n (standard library only, no network).
# Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.
import json
import os
import shutil
import tempfile
import unittest

import xcproj_l10n as x

# A synthetic project.xcproj written from Apple's published model of the format: comments,
# trailing commas, a group, two variant groups, a synchronized folder, a <PROJECT>/ path, an
# SDK path and strings that contain comment and comma look-alikes.
FIXTURE_A = r'''{
  // Synthetic project.xcproj for tests.
  "default-configuration": "Release",
  "configurations": [ "Debug", "Release", ],
  "localizations": {
    "development": "en",
    "supported": [ "Base", "de", "fr", ],
  },
  "files": [
    {
      "kind": "group",
      "path": "App",
      "children": [
        { "path": "AppDelegate.swift", "target-membership": [ "App/compile-sources" ] },
        {
          "kind": "variant-group",
          "name": "Localizable.strings",
          "target-membership": [ "App/resources" ],
          "children": [
            { "path": "en.lproj/Localizable.strings" },
            { "path": "de.lproj/Localizable.strings" },
            { "path": "fr.lproj/Localizable.strings" },
          ],
        },
        /* the storyboard is base-internationalized */
        {
          "kind": "variant-group",
          "name": "Main.storyboard",
          "children": [ { "path": "Base.lproj/Main.storyboard" }, ],
        },
      ],
    },
    { "kind": "folder", "path": "Widgets", "target-membership": [ "Widgets" ] },
    { "path": "<PROJECT>/Shared/Strings.swift" },
    { "path": "<SDK>/System/Library/Frameworks/UIKit.framework" },
    { "kind": "group", "name": "Products", "children": [] },
  ],
  "targets": [ { "name": "App", "notes": "a // b, ] c", "say": "quote \" // not, }" }, ],
}'''

PROJ_A = "MyApp/MyApp.xcodeproj/project.xcproj"

REFS_A = {
    "MyApp/App/AppDelegate.swift",
    "MyApp/App/en.lproj/Localizable.strings",
    "MyApp/App/de.lproj/Localizable.strings",
    "MyApp/App/fr.lproj/Localizable.strings",
    "MyApp/App/Base.lproj/Main.storyboard",
    "MyApp/Widgets",
    "MyApp/Shared/Strings.swift",
}

PATHS_A = [
    PROJ_A,
    "MyApp/App/en.lproj/Localizable.strings",
    "MyApp/App/de.lproj/Localizable.strings",
    "MyApp/App/fr.lproj/Localizable.strings",
    "MyApp/App/ja.lproj/Localizable.strings",
    "MyApp/App/pt-BR.lproj/Localizable.strings",
    "MyApp/App/de-AT.lproj/Localizable.strings",
    "MyApp/App/en-GB.lproj/Localizable.strings",
    "MyApp/Widgets/ja.lproj/Widget.strings",
    "MyApp/Other/ko.lproj/Orphan.strings",
    "MyApp/Pods/Foo/es.lproj/Foo.strings",
]


class StripTests(unittest.TestCase):
    def test_comments_and_trailing_commas(self):
        text = '{"a": [1, 2, ], /* c */ "b": "x//y", // end\n}'
        self.assertEqual(x.loads_xcproj(text), {"a": [1, 2], "b": "x//y"})

    def test_strings_keep_lookalikes(self):
        data = x.loads_xcproj(FIXTURE_A)
        self.assertEqual(data["targets"][0]["notes"], "a // b, ] c")
        self.assertEqual(data["targets"][0]["say"], 'quote " // not, }')
        self.assertEqual(data["configurations"], ["Debug", "Release"])

    def test_bom(self):
        self.assertEqual(x.loads_xcproj(chr(0xFEFF) + '{"files": [],}'), {"files": []})

    def test_unterminated_block_comment(self):
        with self.assertRaises(ValueError):
            x.loads_xcproj('{"a": 1 /* never closed }')

    def test_bad_json_is_value_error(self):
        with self.assertRaises(ValueError):
            x.loads_xcproj('{"a": }')


class ResolveTests(unittest.TestCase):
    def test_bases(self):
        self.assertEqual(x.resolve("A/B", "c.strings", "A"), "A/B/c.strings")
        self.assertEqual(x.resolve("A/B", "", "A"), "A/B")
        self.assertEqual(x.resolve("A/B", "<PROJECT>/S/t.swift", "A"), "A/S/t.swift")
        self.assertEqual(x.resolve("", "<PROJECT>/t.swift", ""), "t.swift")
        self.assertIsNone(x.resolve("A", "<SDK>/usr/lib", "A"))
        self.assertIsNone(x.resolve("A", "<USER:MY_ROOT>/x", "A"))
        self.assertIsNone(x.resolve("A", "/abs/x", "A"))
        self.assertIsNone(x.resolve("", "../outside/x", ""))
        self.assertIsNone(x.resolve(None, "x", "A"))
        self.assertEqual(x.resolve("A", "../b/./c", ""), "b/c")


class ProjectRefsTests(unittest.TestCase):
    def test_fixture_refs(self):
        refs, regions = x.project_refs(PROJ_A, x.loads_xcproj(FIXTURE_A))
        self.assertEqual(refs, REFS_A)

    def test_development_language_is_a_region(self):
        # Apple's model: "supported" never repeats the development language.
        refs, regions = x.project_refs(PROJ_A, x.loads_xcproj(FIXTURE_A))
        self.assertEqual(regions, ["en", "Base", "de", "fr"])

    def test_project_at_repository_root(self):
        data = {"files": [{"path": "Info.plist"}], "localizations": {"development": "fr"}}
        self.assertEqual(x.project_refs("App.xcodeproj/project.xcproj", data),
                         ({"Info.plist"}, ["fr"]))

    def test_version_group(self):
        data = {"files": [{"kind": "version-group", "path": "Model.xcdatamodeld",
                           "children": [{"path": "Model.xcdatamodel"}]}]}
        refs, _ = x.project_refs("App.xcodeproj/project.xcproj", data)
        self.assertEqual(refs, {"Model.xcdatamodeld", "Model.xcdatamodeld/Model.xcdatamodel"})

    def test_empty_path_reference_covers_nothing(self):
        data = {"files": [{"kind": "group", "path": "A", "children": [{"name": "x"},
                                                                     {"kind": "folder"}]}]}
        refs, _ = x.project_refs("App.xcodeproj/project.xcproj", data)
        self.assertEqual(refs, set())

    def test_unknown_kind_skipped(self):
        data = {"files": [{"kind": "something-new", "path": "z"}, {"path": "y"}]}
        refs, _ = x.project_refs("App.xcodeproj/project.xcproj", data)
        self.assertEqual(refs, {"y"})

    def test_no_files_list(self):
        with self.assertRaises(ValueError):
            x.project_refs(PROJ_A, {"localizations": {"development": "en"}})

    def test_too_deep(self):
        node = {"path": "leaf"}
        for _ in range(x.MAX_DEPTH + 2):
            node = {"kind": "group", "path": "g", "children": [node]}
        with self.assertRaises(ValueError):
            x.project_refs("App.xcodeproj/project.xcproj", {"files": [node]})


def reader_for(files):
    return lambda p: files.get(p)


class AnalyseTests(unittest.TestCase):
    def setUp(self):
        self.res = x.analyse(PATHS_A, reader_for({PROJ_A: FIXTURE_A.encode("utf-8")}))

    def test_project_read(self):
        self.assertEqual(self.res["projects"], [{"path": PROJ_A, "status": "ok",
                                                 "refs": len(REFS_A),
                                                 "regions": ["en", "Base", "de", "fr"],
                                                 "pbxproj_too": False}])

    def test_lost(self):
        self.assertEqual(self.res["managed_tables"], 1)
        self.assertEqual(self.res["lost"], [
            {"dir": "MyApp/App", "table": "Localizable.strings", "lang": "ja",
             "path": "MyApp/App/ja.lproj/Localizable.strings", "in_regions": False,
             "whole": False},
            {"dir": "MyApp/App", "table": "Localizable.strings", "lang": "pt-BR",
             "path": "MyApp/App/pt-BR.lproj/Localizable.strings", "in_regions": False,
             "whole": True},
        ])

    def test_skipped(self):
        self.assertEqual(self.res["skipped"], {"english": 1, "regional copy": 1})

    def test_parse_error_recorded(self):
        res = x.analyse([PROJ_A], reader_for({PROJ_A: b'{"files": [ }'}))
        self.assertTrue(res["projects"][0]["status"].startswith("parse error"))
        self.assertEqual(res["lost"], [])

    def test_unread_and_pbxproj_too(self):
        pbx = "MyApp/MyApp.xcodeproj/project.pbxproj"
        res = x.analyse([PROJ_A, pbx], reader_for({}))
        self.assertEqual(res["projects"][0]["status"], "unread")
        self.assertTrue(res["projects"][0]["pbxproj_too"])

    def test_vendored_project_ignored(self):
        p = "Pods/Lib/Lib.xcodeproj/project.xcproj"
        res = x.analyse([p], reader_for({p: b'{"files": []}'}))
        self.assertEqual(res["projects"], [])


class ScanDirTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="xcproj-test-")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def put(self, rel, data):
        full = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as fh:
            fh.write(data)

    def test_scan_dir_matches_analyse(self):
        for p in PATHS_A:
            self.put(p, FIXTURE_A.encode("utf-8") if p == PROJ_A else b'"k" = "v";\n')
        self.put(".git/objects/xx", b"ignored")
        res = x.scan_dir(self.root)
        self.assertEqual([f["lang"] for f in res["lost"]], ["ja", "pt-BR"])
        self.assertEqual(res["projects"][0]["path"], PROJ_A)

    def test_main_strict_exit_code(self):
        for p in PATHS_A:
            self.put(p, FIXTURE_A.encode("utf-8") if p == PROJ_A else b'"k" = "v";\n')
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            self.assertEqual(x.main([self.root]), 0)
            self.assertEqual(x.main([self.root, "--strict"]), 1)
        first = buf.getvalue().split("\n}\n")[0] + "\n}"
        self.assertEqual(len(json.loads(first)["lost"]), 2)


if __name__ == "__main__":
    unittest.main()
