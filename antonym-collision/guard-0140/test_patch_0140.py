"""Offline tests for patch_0140.py (no network).

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import unittest

import patch_0140 as p

GUARD = ('import re\n__version__ = "0.13.0"\n\n\n'
         'def flatten(data, prefix=""):\n'
         '    flat = {}\n'
         '    if isinstance(data, dict):\n'
         '        for k, v in data.items():\n'
         '            path = "%s.%s" % (prefix, k) if prefix else str(k)\n'
         '            flat.update(flatten(v, path))\n'
         '    else:\n'
         '        flat[prefix] = data\n'
         '    return flat\n\n\n'
         + p.CHECK_HEAD +
         '    return sorted(set(src) ^ set(tgt))\n')

DESC = {"a": {"defaultMessage": "Mute", "description": "menu"}, "b": {"defaultMessage": "Unmute", "description": ""}}

README = ("# l10n-guard\n\n- **Antonym collisions** (0.12.0): text\n" + p.JSON_LINE +
          "  and extra keys, value types, and plural keys (`_one`, `_few`, `_many`, `_other`), checked per\n"
          "  language, so Japanese with only `_other` or Polish with `_few`/`_many` doesn't raise false alarms.\n"
          + p.PO_LINE +
          "  fuzzy and untranslated counts.\n\n- uses: munimtechnologies/l10n-guard@v0.13.0\n"
          "- uses: munimtechnologies/l10n-guard@v0.13.0\n")


def run(code):
    scope = {}
    exec(code, scope)
    return scope


class GuardTest(unittest.TestCase):
    def test_patch(self):
        out = p.patch_guard(GUARD)
        self.assertIn('__version__ = "0.14.0"', out)
        self.assertEqual(out.count("def check_catalog("), 1)
        self.assertEqual(out.count("def unwrap_descriptors("), 1)
        self.assertLess(out.index("def unwrap_descriptors("), out.index("def check_catalog("))
        scope = run(out)
        self.assertEqual(scope["unwrap_descriptors"](DESC), {"a": "Mute", "b": "Unmute"})
        flat = {"a": "x"}
        self.assertIs(scope["unwrap_descriptors"](flat), flat)
        self.assertEqual(scope["check_catalog"](DESC, {"a": "Stumm", "b": "Laut"}), [])
        self.assertEqual(run(GUARD)["check_catalog"](DESC, {"a": "Stumm", "b": "Laut"}),
                         ["a", "a.defaultMessage", "a.description", "b", "b.defaultMessage", "b.description"])

    def test_refuses_twice(self):
        with self.assertRaises(p.PatchError):
            p.patch_guard(p.patch_guard(GUARD))

    def test_refuses_other_version(self):
        with self.assertRaises(p.PatchError):
            p.patch_guard(GUARD.replace("0.13.0", "0.12.0"))

    def test_refuses_without_anchor(self):
        with self.assertRaises(p.PatchError):
            p.patch_guard(GUARD.replace("Returns a list of issues.", "Returns issues."))


class ReadmeTest(unittest.TestCase):
    def test_patch(self):
        out = p.patch_readme(README)
        self.assertNotIn("@v0.13.0", out)
        self.assertEqual(out.count("l10n-guard@v0.14.0"), 2)
        self.assertIn("doesn't raise false alarms.\n" + p.FORMATJS + p.PO_LINE, out)
        # Only the inserted paragraph names defaultMessage (twice).
        self.assertEqual(out.count("defaultMessage"), p.FORMATJS.count("defaultMessage"))
        for line in README.split("\n"):
            self.assertIn(line.replace("@v0.13.0", "@v0.14.0"), out)

    def test_refuses_twice(self):
        with self.assertRaises(p.PatchError):
            p.patch_readme(p.patch_readme(README))

    def test_refuses_without_gettext_bullet(self):
        with self.assertRaises(p.PatchError):
            p.patch_readme(README.replace(p.PO_LINE, "- **gettext**: other text\n"))

    def test_refuses_when_bullets_are_apart(self):
        apart = README.replace(p.PO_LINE, "- **Other**\n  a\n  b\n  c\n" + p.PO_LINE)
        with self.assertRaises(p.PatchError):
            p.patch_readme(apart)

    def test_refuses_other_version(self):
        with self.assertRaises(p.PatchError):
            p.patch_readme(README.replace("@v0.13.0", "@v0.12.0"))


if __name__ == "__main__":
    unittest.main()
