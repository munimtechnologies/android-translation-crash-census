# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Tests for locale_config.py (made with AI agents by MV2 of Munim, Inc.)."""
import unittest

import locale_config as lc


def _row(repo, manifest, status="ok", regenerated=False, phantom=(), orphan=(), weak=()):
    x = {"manifest": manifest, "module": "app", "xml": "x", "status": status, "default": "en",
         "regenerated": regenerated, "listed": ["en"], "phantom": list(phantom),
         "orphan": list(orphan), "weak_orphan": list(weak), "module_langs": 1}
    return lc.list_row(repo, "h", x)


class Names(unittest.TestCase):
    def test_parse_dir(self):
        self.assertEqual(lc.parse_dir("values-de"), ("de", None, None))
        self.assertEqual(lc.parse_dir("values-zh-rCN"), ("zh", "CN", None))
        self.assertEqual(lc.parse_dir("values-b+sr+Latn"), ("sr", None, "Latn"))
        for bad in ("values", "values-v21", "values-night", "values-car", "values-en-rXA"):
            self.assertIsNone(lc.parse_dir(bad), bad)

    def test_tag_lang(self):
        cases = {"en-US": "en", "zh-Hans-CN": "zh", "pt_BR": "pt", "b+sr+Latn": "sr",
                 "iw": "he", "IN": "id", " de ": "de", "": "", None: ""}
        for tag, want in cases.items():
            self.assertEqual(lc.tag_lang(tag), want, tag)

    def test_not_a_language(self):
        self.assertTrue(lc.not_a_language("ua"))
        self.assertFalse(lc.not_a_language("uk"))
        self.assertFalse(lc.not_a_language("iw"))
        self.assertFalse(lc.not_a_language("fil"))

    def test_module_of(self):
        cases = {"app/src/main/res": "app", "src/android/app/src/main/res": "src/android/app",
                 "res": "", "app/res": "app", "AndroidManifest.xml": "",
                 "app/src/main/AndroidManifest.xml": "app", "src/main/res": "",
                 "app/src/fdroid/res": "app"}
        for path, want in cases.items():
            self.assertEqual(lc.module_of(path), want, path)


class Parsers(unittest.TestCase):
    def test_gradle_generates(self):
        yes = ["android {\n  androidResources {\n    generateLocaleConfig = true\n  }\n}",
               "androidResources { generateLocaleConfig true }",
               "generateLocaleConfig=true // on"]
        no = ["generateLocaleConfig = false", "  // generateLocaleConfig = true",
              "/* generateLocaleConfig = true */", "x // generateLocaleConfig = true",
              "android { }"]
        for t in yes:
            self.assertTrue(lc.gradle_generates(t), t)
        for t in no:
            self.assertFalse(lc.gradle_generates(t), t)

    def test_manifest_locale_config(self):
        self.assertEqual(lc.manifest_locale_config(
            '<application android:localeConfig="@xml/locales_config" />'), "locales_config")
        self.assertIsNone(lc.manifest_locale_config(
            '<!-- <application android:localeConfig="@xml/locales_config" /> -->'))
        self.assertIsNone(lc.manifest_locale_config("<manifest/>"))

    def test_parse_locale_config(self):
        data = ('<?xml version="1.0" encoding="utf-8"?>\n<locale-config '
                'xmlns:android="http://schemas.android.com/apk/res/android">'
                '<locale android:name="en"/><locale android:name="uk"/></locale-config>')
        self.assertEqual(lc.parse_locale_config(data.encode("utf-8")), ["en", "uk"])
        self.assertIsNone(lc.parse_locale_config(b"<resources/>"))
        self.assertIsNone(lc.parse_locale_config(b"<locale-config"))

    def test_default_language(self):
        self.assertEqual(lc.default_language("unqualifiedResLocale=en-US\n"), "en")
        self.assertEqual(lc.default_language("# x\nunqualifiedResLocale = de\n"), "de")
        self.assertEqual(lc.default_language(None), "en")
        self.assertEqual(lc.default_language(""), "en")

    def test_keys_of(self):
        default = (b'<resources><string name="a">A</string>'
                   b'<string name="b" translatable="false">B</string>'
                   b'<plurals name="p"><item quantity="one">x</item></plurals>'
                   b'<string-array name="s"><item>y</item></string-array>'
                   b'<color name="c">#fff</color></resources>')
        self.assertEqual(lc.keys_of(default, True), {"a", "p", "s"})
        self.assertEqual(lc.keys_of(default, False), {"a", "b", "p", "s"})
        self.assertEqual(lc.keys_of(b'<resources><string name="a"> </string></resources>'),
                         set())
        self.assertIsNone(lc.keys_of(b"<resources>"))
        self.assertEqual(lc.keys_of(b"<other/>"), set())


class Analyse(unittest.TestCase):
    def test_control(self):
        self.assertTrue(lc.control())

    def test_control_details(self):
        files = lc.control_files()
        rec = lc.analyse(sorted(files), files.get)
        self.assertEqual(rec["generated"], ["other/build.gradle"])
        x = rec["lists"][0]
        self.assertEqual(x["listed"], ["en-US", "de", "fr", "zh-Hans-CN", "he"])
        self.assertEqual((x["phantom"], x["orphan"], x["weak_orphan"]),
                         (["fr"], ["uk:75"], ["ko:25"]))

    def test_regenerated(self):
        files = lc.control_files()
        files["app/build.gradle"] = (b"tasks.register('locales') {\n"
                                     b"  file('src/main/res/xml/locales_config.xml')\n}\n")
        x = lc.analyse(sorted(files), files.get)["lists"][0]
        self.assertTrue(x["regenerated"])
        self.assertFalse(lc.evaluable(x))
        self.assertFalse(lc.drift(x))

    def test_default_from_properties(self):
        files = lc.control_files()
        files["app/src/main/res/resources.properties"] = b"unqualifiedResLocale=fr\n"
        x = lc.analyse(sorted(files), files.get)["lists"][0]
        self.assertEqual(x["default"], "fr")
        self.assertEqual(x["phantom"], ["en"])
        self.assertEqual(x["orphan"], ["uk:75"])

    def test_missing_list(self):
        files = lc.control_files()
        files["app/src/main/AndroidManifest.xml"] = (
            b'<manifest><application android:localeConfig="@xml/nope"/></manifest>')
        x = lc.analyse(sorted(files), files.get)["lists"][0]
        self.assertEqual(x["status"], "missing")
        self.assertFalse(lc.evaluable(x))

    def test_list_in_other_module_used_when_none_in_module(self):
        files = lc.control_files()
        data = files.pop("app/src/main/res/xml/locales_config.xml")
        files["shared/src/main/res/xml/locales_config.xml"] = data
        x = lc.analyse(sorted(files), files.get)["lists"][0]
        self.assertEqual(x["xml"], "shared/src/main/res/xml/locales_config.xml")
        self.assertEqual(x["status"], "ok")

    def test_empty_list(self):
        files = lc.control_files()
        files["app/src/main/res/xml/locales_config.xml"] = b"<locale-config/>"
        x = lc.analyse(sorted(files), files.get)["lists"][0]
        self.assertEqual(x["status"], "empty")
        self.assertEqual(x["orphan"], ["de:100", "he:100", "uk:75", "zh:75"])
        self.assertTrue(lc.drift(x))

    def test_unreadable_file_is_not_a_parse_failure(self):
        files = lc.control_files()
        read = lambda p: None if p.endswith("values-de/strings.xml") else files.get(p)
        rec = lc.analyse(sorted(files), read)
        self.assertEqual(rec["parse_failed"], 0)
        self.assertNotIn("de", rec["langs"])

    def test_broken_xml_counts(self):
        files = lc.control_files()
        files["app/src/main/res/values-de/strings.xml"] = b"<resources><string"
        rec = lc.analyse(sorted(files), files.get)
        self.assertEqual(rec["parse_failed"], 1)


class Grading(unittest.TestCase):
    def counts(self, c1=100, ev=20, dr=5, orph=3, phan=2):
        return {"c1_repos_with_list": c1, "evaluable_repos": ev, "drift_repos": dr,
                "orphan_repos": orph, "phantom_repos": phan}

    def test_gate(self):
        v = lc.grade(3999, self.counts(), 16)
        self.assertTrue(all(x.startswith("NOT TESTABLE") for x in v.values()))
        self.assertEqual(sorted(v), ["C1", "C2", "C3", "C4"])

    def test_thresholds(self):
        v = lc.grade(4000, self.counts(), 8)
        self.assertEqual((v["C1"], v["C2"], v["C3"]), ("HELD", "HELD", "HELD"))
        self.assertTrue(v["C4"].startswith("PENDING"))
        v = lc.grade(4000, self.counts(c1=99, dr=4, orph=2, phan=2), 7)
        self.assertEqual((v["C1"], v["C2"], v["C3"]), ("FAILED", "FAILED", "FAILED"))
        self.assertTrue(v["C4"].startswith("NOT TESTABLE"))
        v = lc.grade(4000, self.counts(ev=19), 16)
        self.assertTrue(v["C2"].startswith("NOT TESTABLE"))
        self.assertTrue(v["C3"].startswith("NOT TESTABLE"))

    def test_grade_c4(self):
        self.assertEqual(lc.grade_c4(["real"] * 12 + ["not-real"] * 4), "HELD")
        self.assertEqual(lc.grade_c4(["real"] * 11 + ["other"] * 5), "FAILED")
        self.assertEqual(lc.grade_c4(["real"] * 7), "NOT TESTABLE")

    def test_repo_counts(self):
        rows = [_row("r1", "a", phantom=["fr"]), _row("r1", "b", orphan=["uk:75"]),
                _row("r2", "a", regenerated=True, orphan=["uk:75"]),
                _row("r3", "a", status="missing"), _row("r4", "a", weak=["ko:10"]),
                _row("r5", "a", status="parse-failed")]
        c = lc.repo_counts(rows)
        self.assertEqual(c, {"c1_repos_with_list": 4, "evaluable_repos": 2, "drift_repos": 1,
                             "orphan_repos": 1, "phantom_repos": 1})

    def test_sample(self):
        rows = [_row("r%02d" % i, m, orphan=["uk:75"]) for i in range(30) for m in ("a", "b")]
        rows.append(_row("rx", "a"))
        s = lc.draw_sample(rows)
        self.assertEqual(len(s), 16)
        self.assertEqual(len({x["repo"] for x in s}), 16)
        self.assertNotIn("rx", {x["repo"] for x in s})
        self.assertEqual(s, lc.draw_sample(list(reversed(rows))))
        keys = [lc.sample_key(x["repo"], x["manifest"]) for x in s]
        self.assertEqual(keys, sorted(keys))


if __name__ == "__main__":
    unittest.main()
