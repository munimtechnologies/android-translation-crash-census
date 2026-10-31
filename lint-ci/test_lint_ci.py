#!/usr/bin/env python3
# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Tests for lint_ci.py: the CI rule, exposure, the java-format positive control and the grading.
No network. Needs l10n_guard.py 0.15.0 next to lint_ci.py. Made with AI agents by MV2 of Munim, Inc."""
import os
import shutil
import tempfile
import unittest

import lint_ci as lc

SRC = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="files">%1$d files</string>
    <string name="title">Settings</string>
    <string name="done">%d%% done</string>
    <plurals name="items"><item quantity="one">%d item</item><item quantity="other">%d items</item></plurals>
    <string name="fixed" translatable="false">%s</string>
</resources>
"""
TGT_OK = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="files">%1$d Dateien</string>
    <string name="title">Einstellungen</string>
    <string name="done">%d%% fertig</string>
    <plurals name="items"><item quantity="one">%d Element</item><item quantity="other">%d Elemente</item></plurals>
</resources>
"""
TGT_BAD = TGT_OK.replace("%1$d Dateien", "%1$z Dateien")


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class LintRuleTest(unittest.TestCase):
    def lint(self, line):
        return bool(lc.lint_evidence(line)[0])

    def check(self, line):
        return bool(lc.lint_evidence(line)[1])

    def test_android_lint_tasks(self):
        for line in ("run: ./gradlew lintDebug", "  - ./gradlew assembleDebug lint testDebugUnitTest",
                     "run: ./gradlew :app:lintFossRelease", "        arguments: lint",
                     "script: gradle lintVitalRelease", "run: ./gradlew lint --continue"):
            self.assertTrue(self.lint(line), line)

    def test_not_android_lint(self):
        for line in ("run: ./gradlew ktlintCheck", "run: ./gradlew lintKotlin", "run: npx lint-staged",
                     "- name: Run lint with Gradle", "# run: ./gradlew lint", "run: ./gradlew detekt",
                     "path: app/build/reports/lint-results-debug.html  # gradle", "run: lint",
                     "uses: gradle/gradle-build-action@v3"):
            self.assertFalse(self.lint(line), line)

    def test_check_or_build(self):
        self.assertTrue(self.check("run: ./gradlew build"))
        self.assertTrue(self.check("run: ./gradlew :app:check"))
        self.assertFalse(self.check("uses: gradle/gradle-build-action@v3"))
        self.assertFalse(self.check("run: ./gradlew assembleDebug --build-cache"))


class ScanTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_exposure_counts_formatted_sources_only(self):
        s = {k: v for k, v in lc.parse_values_text(SRC).items() if v}
        t = {k: v for k, v in lc.parse_values_text(TGT_OK).items() if v}
        self.assertEqual(lc.exposure(s, t), 4)  # files, done, two plural items; not title

    def test_positive_control_java_format(self):
        self.assertEqual(lc.java_format_rows(SRC, TGT_OK), {})
        self.assertEqual(len(lc.java_format_rows(SRC, TGT_BAD)), 1)

    def test_scan_strings_and_ci(self):
        res = os.path.join(self.root, "app", "src", "main", "res")
        write(os.path.join(res, "values", "strings.xml"), SRC)
        write(os.path.join(res, "values-de", "strings.xml"), TGT_BAD)
        write(os.path.join(res, "values-fr", "strings.xml"), TGT_OK)
        write(os.path.join(res, "values-en-rXA", "strings.xml"), TGT_BAD)  # pseudo-locale: skipped
        write(os.path.join(res, "values-night", "colors.xml"), "<resources/>")
        write(os.path.join(self.root, ".github", "workflows", "ci.yml"),
              "jobs:\n  build:\n    steps:\n      - name: Lint\n        run: ./gradlew lintDebug\n")
        write(os.path.join(self.root, "app", "build.gradle"), "lint { abortOnError false }\n")
        out = lc.scan_strings(self.root)
        self.assertEqual((out["pairs"], out["exposure"], out["errors"]), (2, 8, 1))
        self.assertEqual(out["rows"][0]["locale_dir"], "values-de")
        ci = lc.scan_ci(self.root)
        self.assertEqual(ci["ci_files"], [".github/workflows/ci.yml"])
        self.assertTrue(ci["lint"])
        self.assertFalse(ci["check_build"])
        self.assertEqual(ci["gradle_lint_settings"], ["abortOnError false"])
        self.assertEqual(lc.platform(ci["ci_files"][0]), ".github/workflows")


def rows(n, lint, exposure, with_error, errors=1):
    return [{"lint": lint, "exposure": exposure, "errors": errors if i < with_error else 0}
            for i in range(n)]


class GradeTest(unittest.TestCase):
    def test_gate(self):
        v, _ = lc.grade(rows(49, True, 1000, 0) + rows(500, False, 1000, 10))
        self.assertEqual(set(v.values()), {"NOT TESTABLE (gate)"})

    def test_all_held(self):
        r = (rows(20, True, 10, 0) + rows(20, True, 100, 1) + rows(20, True, 1000, 2)
             + rows(100, False, 10, 5) + rows(100, False, 100, 20) + rows(100, False, 1000, 30))
        v, strata = lc.grade(r)
        self.assertEqual(v, {"P1": "HELD", "P2": "HELD", "P3": "HELD"})
        self.assertEqual([s["testable"] for s in strata], [True, True, True])

    def test_failed(self):
        # L is 60 of 120 repos (50%: P1 fails) and has the higher error rate.
        r = (rows(30, True, 100, 10, 3) + rows(30, True, 1000, 10, 3)
             + rows(30, False, 100, 1) + rows(30, False, 1000, 1))
        v, _ = lc.grade(r)
        self.assertEqual(v, {"P1": "FAILED", "P2": "FAILED", "P3": "FAILED"})

    def test_p3_needs_two_testable_strata(self):
        r = rows(60, True, 1000, 1) + rows(300, False, 1000, 30) + rows(5, True, 10, 0)
        v, _ = lc.grade(r)
        self.assertEqual(v["P3"], "NOT TESTABLE")

    def test_platform_counts(self):
        res = [{"status": "ok", "lint": False, "check_build": False, "exposure": 5, "errors": 0,
                "gradle_lint_settings": [], "ci_files": [".github/workflows/a.yml", ".github/workflows/b.yml",
                                                         ".gitlab-ci.yml"]}]
        s = lc.aggregate(res)
        self.assertEqual(s["exploratory_ci_platforms"], {".github/workflows": 1, ".gitlab-ci.yml": 1})


if __name__ == "__main__":
    unittest.main()
