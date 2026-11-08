# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
# Unit tests for lint_gate.py (no network). Made with AI agents by MV2 of Munim, Inc.
import unittest

import lint_gate as g


def result(ci_lint=False, agp=True, fatal=False, sup=False, base=False, has_ci=True,
           repo="r", status="ok"):
    return {"repo": repo, "status": status, "ci_lint": ci_lint, "agp_ge_74": agp, "fatal": fatal,
            "suppressed": sup, "baselined": base, "has_ci": has_ci, "ci_files": [],
            "ci_lines": []}


def many(n, **flags):
    """n results; each flag is a count of results (from the start) where it is set."""
    out = []
    for i in range(n):
        out.append(result(repo="r%d" % i,
                          ci_lint=i < flags.get("ci_lint", 0),
                          agp=None if i < flags.get("agp_none", 0) else True,
                          fatal=i < flags.get("fatal", 0),
                          sup=i < flags.get("sup", 0)))
    return out


class Roles(unittest.TestCase):
    def test_ci(self):
        for p in (".github/workflows/android.yml", ".gitlab-ci.yml", "Jenkinsfile",
                  "fastlane/Fastfile", ".woodpecker/build.yaml", ".forgejo/workflows/ci.yaml",
                  ".circleci/config.yml"):
            self.assertTrue(g.is_ci(p), p)
        for p in (".github/dependabot.yml", ".gitlab/issue_templates/bug.md", "app/build.gradle",
                  "docs/workflows/ci.yml"):
            self.assertFalse(g.is_ci(p), p)

    def test_gradle_and_catalog(self):
        self.assertTrue(g.is_gradle_script("app/build.gradle.kts"))
        self.assertTrue(g.is_gradle_script("buildSrc/src/main/kotlin/AndroidConfig.kt"))
        self.assertTrue(g.is_gradle_script("build-logic/convention/src/main/kotlin/Lint.kt"))
        self.assertFalse(g.is_gradle_script("app/src/main/java/org/x/Foo.kt"))
        self.assertTrue(g.is_catalog("gradle/libs.versions.toml"))
        self.assertFalse(g.is_catalog("Cargo.toml"))
        self.assertTrue(g.is_properties("gradle.properties"))
        self.assertTrue(g.is_lint_xml("app/lint-baseline.xml"))
        self.assertTrue(g.is_res_xml("app/src/main/res/xml/locales_config.xml"))
        self.assertFalse(g.role("app/src/main/res/values/strings.xml"))


class Comments(unittest.TestCase):
    def test_strip(self):
        self.assertEqual(g.strip_comments('a = "http://x" // c\nb /* x\ny */ c'),
                         'a = "http://x" \nb \n c')
        self.assertEqual(g.strip_comments('exclude "**/*.so" // x'), 'exclude "**/*.so" ')

    def test_stray_apostrophe_ends_at_newline(self):
        text = g.strip_comments("x = it's // no\nwarningsAsErrors true")
        self.assertTrue(g.WAE.search(text))

    def test_commented_setting_ignored(self):
        r = g.analyse({"app/build.gradle": "android {\n  lint {\n    // warningsAsErrors true\n"
                                           "  }\n}\n"})
        self.assertFalse(r["fatal"])
        self.assertTrue(r["lint_block"])


class Agp(unittest.TestCase):
    def test_ver_tuple(self):
        self.assertEqual(g.ver_tuple("8.2.0-alpha01"), (8, 2))
        self.assertIsNone(g.ver_tuple("$x"))

    def test_catalog(self):
        toml = ('[versions]\nagp = "8.3.1"  # comment\nkotlin = "1.9.0"\n[plugins]\n'
                'android-application = { id = "com.android.application", version.ref = "agp" }\n'
                '[libraries]\n'
                'gradle = { module = "com.android.tools.build:gradle", version = "7.3.1" }\n'
                'legacy = "com.android.tools.build:gradle:7.2.0"\n')
        self.assertEqual(g.toml_agp(toml), ["8.3.1", "7.3.1", "7.2.0"])
        r = g.analyse({"gradle/libs.versions.toml": toml})
        self.assertEqual(r["agp"], "8.3")
        self.assertIs(r["agp_ge_74"], True)

    def test_plugin_dsl(self):
        r = g.analyse({"build.gradle.kts": 'plugins {\n    id("com.android.application") '
                                           'version "8.4.0" apply false\n}\n'})
        self.assertEqual(r["agp"], "8.4")
        r = g.analyse({"build.gradle": "plugins {\n  id 'com.android.library' version '7.3.0' "
                                       "apply false\n}\n"})
        self.assertEqual(r["agp"], "7.3")
        self.assertIs(r["agp_ge_74"], False)

    def test_variable_from_properties(self):
        r = g.analyse({"build.gradle": 'buildscript { dependencies { classpath '
                                       '"com.android.tools.build:gradle:${agpVersion}" } }\n',
                       "gradle.properties": "agpVersion=8.0.2\n"})
        self.assertEqual(r["agp"], "8.0")

    def test_unknown(self):
        r = g.analyse({"app/build.gradle": "android { }\n"})
        self.assertEqual(r["agp"], "")
        self.assertIsNone(r["agp_ge_74"])


class Ci(unittest.TestCase):
    def classes(self, path, text):
        r = g.analyse({path: text})
        return r["ci_lint"], r["ci_vital"], r["ci_implicit"]

    def test_vital_only(self):
        self.assertEqual(self.classes(".github/workflows/b.yml",
                                      "    - run: ./gradlew lintVitalRelease\n"),
                         (False, True, False))

    def test_kotlin_linters_not_android_lint(self):
        self.assertEqual(self.classes(".gitlab-ci.yml",
                                      "build:\n  script:\n    - ./gradlew ktlintCheck lintKotlin build\n"),
                         (False, False, True))

    def test_gradle_action_arguments(self):
        text = ("      - uses: gradle/gradle-build-action@v2\n        with:\n"
                "          arguments: lint\n")
        self.assertEqual(self.classes(".github/workflows/b.yml", text), (True, False, False))

    def test_fastfile(self):
        text = 'lane :test do\n  gradle(task: "lintDebug")\nend\n'
        self.assertEqual(self.classes("fastlane/Fastfile", text), (True, False, False))

    def test_commented_and_continued(self):
        self.assertEqual(self.classes(".github/workflows/b.yml", "#    - run: ./gradlew lint\n"),
                         (False, False, False))
        text = "      - run: ./gradlew \\\n          :app:lintFdroidDebug assembleDebug\n"
        self.assertEqual(self.classes(".github/workflows/b.yml", text), (True, False, False))

    def test_task_class(self):
        self.assertEqual(g.task_class("lint"), "lint")
        self.assertEqual(g.task_class("lintFix"), "lint")
        self.assertEqual(g.task_class("lintVitalAnalyzeRelease"), "vital")
        self.assertIsNone(g.task_class("lintKotlinMain"))
        self.assertIsNone(g.task_class("lintable"))
        self.assertIsNone(g.task_class("ktlintCheck"))
        self.assertEqual(g.task_class("check"), "implicit")
        self.assertIsNone(g.task_class("assembleRelease"))

    def test_ci_file_without_gradle(self):
        r = g.analyse({".github/workflows/stale.yml": "on: schedule\njobs: {}\n"})
        self.assertTrue(r["has_ci"])
        self.assertFalse(r["ci_lint"])


class LintSettings(unittest.TestCase):
    def test_lint_xml(self):
        f, s = g.lint_xml_rules('<?xml version="1.0"?>\n<lint>\n'
                                '  <issue id="UnusedTranslation" severity="error" />\n</lint>\n')
        self.assertEqual((f, s), (["lint.xml UnusedTranslation=error"], []))
        f, s = g.lint_xml_rules('<lint>\n  <issue severity="ignore" id="UnusedTranslation"/>\n'
                                '  <!-- <issue id="all" severity="fatal"/> -->\n</lint>\n')
        self.assertEqual((f, s), ([], ["lint.xml UnusedTranslation=ignore"]))

    def test_baseline(self):
        text = ('<?xml version="1.0" encoding="UTF-8"?>\n<issues format="6" by="lint 8.1.0">\n'
                '    <issue\n        id="UnusedTranslation"\n        severity="Warning"\n'
                '        message="The language tr is present"/>\n</issues>\n')
        r = g.analyse({"app/lint-baseline.xml": text})
        self.assertTrue(r["baselined"])
        self.assertFalse(r["suppressed"])
        self.assertFalse(r["fatal"])

    def test_tools_ignore(self):
        r = g.analyse({"app/src/main/AndroidManifest.xml":
                       '<application android:localeConfig="@xml/locales_config" '
                       'tools:ignore="UnusedTranslation,MissingTranslation">'})
        self.assertTrue(r["suppressed"])

    def test_gradle_rules(self):
        r = g.analyse({"app/build.gradle.kts": 'android { lint { error += "UnusedTranslation" } }'})
        self.assertTrue(r["fatal"])
        r = g.analyse({"app/build.gradle": "android {\n lintOptions {\n  warningsAsErrors true\n"
                                           "  abortOnError false\n  checkReleaseBuilds false\n"
                                           " }\n resConfigs 'en', 'de'\n}\n"})
        self.assertTrue(r["fatal"])
        self.assertTrue(r["abort_false"])
        self.assertTrue(r["check_release_false"])
        self.assertTrue(r["filters"])
        r = g.analyse({"app/build.gradle.kts": "kotlinOptions { allWarningsAsErrors = true }\n"
                                               'android { lint { warning += "UnusedTranslation" } }'})
        self.assertFalse(r["fatal"])
        self.assertFalse(r["suppressed"])
        self.assertEqual(len(r["other_rules"]), 1)

    def test_control(self):
        self.assertTrue(g.control())


class Grouping(unittest.TestCase):
    def test_groups(self):
        rows = [
            {"repo": "A", "head": "a1", "evaluable": "yes", "orphan": "uk:75", "drift": "yes"},
            {"repo": "A", "head": "a1", "evaluable": "yes", "orphan": "", "drift": "no"},
            {"repo": "B", "head": "b1", "evaluable": "yes", "orphan": "", "drift": "no"},
            {"repo": "C", "head": "c1", "evaluable": "yes", "orphan": "", "drift": "yes"},
            {"repo": "D", "head": "d1", "evaluable": "no", "orphan": "", "drift": "no"},
            {"repo": "E", "head": "e1", "evaluable": "yes", "orphan": "", "drift": "no"},
            {"repo": "E", "head": "e1", "evaluable": "no", "orphan": "tr:90", "drift": "no"},
        ]
        orphan, clean, heads = g.groups(rows)
        self.assertEqual(orphan, ["A"])
        self.assertEqual(clean, ["B", "E"])
        self.assertEqual(heads["D"], "d1")


class Grading(unittest.TestCase):
    def test_all_held(self):
        o = many(60, ci_lint=10, agp_none=10, fatal=4, sup=5)
        c = many(150, ci_lint=30)
        self.assertEqual(g.grade(o, c), {"L1": "HELD", "L2": "HELD", "L3": "HELD",
                                         "L4": "HELD", "L5": "HELD"})

    def test_failures_and_edges(self):
        o = many(60, ci_lint=18, fatal=5, sup=6)
        c = many(150, ci_lint=45)
        v = g.grade(o, c)
        self.assertEqual(v["L2"], "FAILED")
        self.assertEqual(v["L3"], "FAILED")   # exactly 30% is not "fewer than 30%"
        self.assertEqual(v["L5"], "FAILED")
        # 45/150 - 18/60 = 0 points apart
        self.assertEqual(v["L4"], "HELD")
        o = many(60, ci_lint=10)
        self.assertEqual(g.grade(o, c)["L4"], "FAILED")   # 30% vs 16.7%

    def test_l1(self):
        o = many(60, agp_none=21)
        self.assertTrue(g.grade(o, many(150))["L1"].startswith("NOT TESTABLE"))
        o = many(60)
        for r in o[:11]:
            r["agp_ge_74"] = False
        self.assertEqual(g.grade(o, many(150))["L1"], "HELD")    # 49/60 = 81.7%
        for r in o[:16]:
            r["agp_ge_74"] = False
        self.assertEqual(g.grade(o, many(150))["L1"], "FAILED")  # 44/60 = 73.3%

    def test_gates(self):
        v = g.grade(many(59), many(150))
        self.assertTrue(all(x.startswith("NOT TESTABLE") for x in v.values()))
        v = g.grade(many(60), many(149))
        self.assertTrue(v["L4"].startswith("NOT TESTABLE"))
        self.assertEqual(v["L3"], "HELD")


class Sampling(unittest.TestCase):
    def test_strata(self):
        rs = ([result(repo="l%d" % i, ci_lint=True) for i in range(8)]
              + [result(repo="n%d" % i) for i in range(3)]
              + [result(repo="x%d" % i, has_ci=False) for i in range(4)]
              + [result(repo="f", ci_lint=True, status="clone-failed")])
        s = g.draw_sample(rs)
        self.assertEqual([k for k, _ in s].count("ci-lint"), 6)
        self.assertEqual([k for k, _ in s].count("ci-no-lint"), 3)
        self.assertNotIn("f", [r["repo"] for _, r in s])


if __name__ == "__main__":
    unittest.main()
