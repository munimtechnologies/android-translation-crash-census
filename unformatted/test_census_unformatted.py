#!/usr/bin/env python3
"""Tests for census_unformatted.py. Run after fetch_code.py (needs census.py,
census_fixes.py and l10n_guard.py next to this file).

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import os
import shutil
import tempfile
import unittest

import census
import census_plurals
import census_unformatted as cu

SOURCE = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="plain">Hello %s</string>
    <string name="multi" formatted="false">Route \\"%s\\"\\nStation \\"%s\\"</string>
    <string name="literal" formatted="false">No placeholder here</string>
    <plurals name="trips" formatted="false">
        <item quantity="one">%d trip to %s</item>
        <item quantity="other">%d trips to %s</item>
    </plurals>
</resources>
"""

TRANSLATION = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="plain">你好 %</string>
    <string name="multi">%時刻表，站名%</string>
    <string name="literal">这里没有占位符</string>
    <plurals name="trips">
        <item quantity="other">%d 次 %</item>
    </plurals>
</resources>
"""


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class UnformattedTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="unformatted-test-")
        res = os.path.join(self.root, "app", "src", "main", "res")
        write(os.path.join(res, "values", "strings.xml"), SOURCE)
        write(os.path.join(res, "values-zh", "strings.xml"), TRANSLATION)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_census_skips_then_this_keeps_only_unformatted(self):
        census_plurals.apply()
        pairs, _ = census.scan_tree(self.root)
        self.assertEqual({p["key"] for p in pairs}, {"plain"})

        cu.apply()
        cu.apply()  # twice is the same as once
        pairs, stats = census.scan_tree(self.root)
        # "literal" has no argument, so census never counts it.
        self.assertEqual(sorted(p["key"] for p in pairs), ["multi", "trips[other]"])
        multi = [p for p in pairs if p["key"] == "multi"][0]
        self.assertEqual(multi["source"], 'Route "%s"\nStation "%s"')
        self.assertEqual(multi["target"], "%時刻表，站名%")
        self.assertEqual(multi["res"], "app/src/main/res")
        self.assertEqual(stats["pairs"], 2)
        self.assertEqual(stats["pairs_all"], 3)
        self.assertEqual(stats["unformatted_names"], 3)
        self.assertEqual(cu.UNFORMATTED, {})

    def test_predictions(self):
        summary = {"formatted_translation_pairs": 10000, "verdicts": {"crash": 6}}
        findings = [{"verdict": "crash", "use": "referenced",
                     "repo": "https://github.com/w32blaster/helsinki-timetables"},
                    {"verdict": "crash", "use": "formatted",
                     "repo": "https://github.com/w32blaster/helsinki-timetables"}]
        got = {p["id"]: p["held"] for p in cu.predictions(summary, findings)}
        self.assertEqual(got, {"P1": True, "P2": True, "P3": False})
        findings.append({"verdict": "crash", "use": "formatted", "repo": "https://github.com/a/b"})
        summary["verdicts"]["crash"] = 2
        got = {p["id"]: p["held"] for p in cu.predictions(summary, findings)}
        self.assertEqual(got, {"P1": True, "P2": False, "P3": True})


if __name__ == "__main__":
    unittest.main()
