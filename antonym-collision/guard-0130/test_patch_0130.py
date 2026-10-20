"""Offline tests for patch_0130.py and patch_index6.py (no network).

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import unittest

import patch_0130 as p
import patch_index6 as q

GUARD = ('import re\n__version__ = "0.12.0"\n\n'
         '# antonyms outside them\n# ("Visible" / "Hidden") are missed.\n_ANTONYM_CLASSES = {\n'
         '    "IMPORT": ("import imported", "export exported"),\n'
         '    "UPLOAD": ("upload uploaded", "download downloaded"),\n'
         '    "START": ("start starts started", "end ends ended"),\n'
         '}\n_ANTONYMS = {}\n')

README = ("# l10n-guard\n\n- **Antonym collisions** (0.12.0): text\n"
          "  ([scan](" + p.CENSUS + "antonym-collision/RESULTS.md),\n" + p.README_PREREG +
          "- **Apple**\n\n- uses: munimtechnologies/l10n-guard@v0.12.0\n"
          "- uses: munimtechnologies/l10n-guard@v0.12.0\n")

CENSUS = ("# Census\n\n## Sub-studies\n\n- [antonym-collision/](antonym-collision/RESULTS.md): scan\n"
          "  \"Upload failed\" in French or Arabic. A second held-out test on five more projects, with a rule fixed\n"
          + q.END_LINE + "\nsteps\n")


class GuardTest(unittest.TestCase):
    def test_patch(self):
        out = p.patch_guard(GUARD)
        self.assertIn('__version__ = "0.13.0"', out)
        self.assertNotIn('"UPLOAD"', out)
        self.assertIn('"IMPORT": ("import imported", "export exported"),\n    "START"', out)
        self.assertIn("HOLDOUT2-RESULTS.md).\n_ANTONYM_CLASSES = {\n", out)
        scope = {}
        exec(out, scope)
        self.assertEqual(sorted(scope["_ANTONYM_CLASSES"]), ["IMPORT", "START"])

    def test_refuses_twice(self):
        with self.assertRaises(p.PatchError):
            p.patch_guard(p.patch_guard(GUARD))

    def test_refuses_other_version(self):
        with self.assertRaises(p.PatchError):
            p.patch_guard(GUARD.replace("0.12.0", "0.11.0"))


class ReadmeTest(unittest.TestCase):
    def test_patch(self):
        out = p.patch_readme(README)
        self.assertNotIn("@v0.12.0", out)
        self.assertEqual(out.count("l10n-guard@v0.13.0"), 2)
        for target in ("RESULTS.md", "GUARD-PREREG.md", "GUARD-RESULTS.md", "HOLDOUT2-RESULTS.md"):
            self.assertIn("antonym-collision/%s)" % target, out)
        self.assertIn("39 word classes remain.\n- **Apple**", out)

    def test_refuses_twice(self):
        with self.assertRaises(p.PatchError):
            p.patch_readme(p.patch_readme(README))


class IndexTest(unittest.TestCase):
    def test_patch(self):
        out = q.patch_readme(CENSUS)
        self.assertIn("](antonym-collision/HOLDOUT2-RESULTS.md)", out)
        self.assertLess(out.index("HOLDOUT2-PREREG.md"), out.index("HOLDOUT2-RESULTS.md"))
        self.assertLess(out.index("HOLDOUT2-RESULTS.md"), out.index("## Method"))
        self.assertTrue(out.endswith("\n\n## Method\n\nsteps\n"))
        for line in CENSUS.split("\n"):
            self.assertIn(line, out)

    def test_refuses_twice(self):
        with self.assertRaises(q.PatchError):
            q.patch_readme(q.patch_readme(CENSUS))

    def test_refuses_without_anchor(self):
        with self.assertRaises(q.PatchError):
            q.patch_readme(CENSUS.replace("## Method", "## Methods"))


if __name__ == "__main__":
    unittest.main()
