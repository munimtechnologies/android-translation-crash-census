#!/usr/bin/env python3
"""Tests for census_plurals.py (census 0.4.0). Standard library only; the
FormatCheck tests run when a JDK is on PATH or under $CENSUS_DATA_DIR/jdk.

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import os
import shutil
import tempfile
import unittest

import census_plurals as plurals
import census
import l10n_guard as g

plurals.apply()

# jellyfin-android's download_remove_description (values/strings.xml, master,
# 2026-10-16) and its Arabic forms at 960d37a.
JELLYFIN = ('<resources><plurals name="download_remove_description">'
            '<item quantity="one">Do you want to remove \\"%2$s\\" from your downloads?</item>'
            '<item quantity="other">Do you want to remove these %1$d downloads?</item>'
            '</plurals><string name="greeting">Hello %1$s</string></resources>')
JELLYFIN_AR = ('<resources><plurals name="download_remove_description">'
               '<item quantity="few">هل ترغب في حذف بعض ملفات %1$d من ملفات التحميل؟</item>'
               '<item quantity="other">هل ترغب في حذف ملفات %1$d اخرى من ملفات التحميل؟</item>'
               '</plurals><string name="greeting">مرحبا %1$d</string></resources>')
# A text argument shown in one form only: %1$d for it is still wrong.
NAMED = ('<resources><plurals name="files_from">'
         '<item quantity="one">File from %1$s</item>'
         '<item quantity="other">%2$d files from %1$s</item></plurals></resources>')
NAMED_FR = ('<resources><plurals name="files_from">'
            '<item quantity="one">Fichier de %1$d</item>'
            '<item quantity="other">%2$d fichiers de %1$s</item></plurals></resources>')
# The chosen form ([one]) doesn't show argument 1 and the other forms disagree
# on it (an int, a decimal): keep the chosen form's "any".
CLASH = ('<resources><plurals name="clash">'
         '<item quantity="one">Remove %2$s?</item>'
         '<item quantity="few">%1$d items</item>'
         '<item quantity="other">%1$.1f items</item></plurals></resources>')
CLASH_DE = ('<resources><plurals name="clash">'
            '<item quantity="other">%1$d Dinge</item></plurals></resources>')


def tree(files):
    root = tempfile.mkdtemp(prefix="census-plurals-")
    for sub, xml in files.items():
        folder = os.path.join(root, "app", "src", "main", "res", sub)
        os.makedirs(folder)
        with open(os.path.join(folder, "strings.xml"), "w", encoding="utf-8") as f:
            f.write(xml)
    return root


def scan(files):
    root = tree(files)
    try:
        pairs, stats = census.scan_tree(root)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    return {(p["locale"], p["key"]): p for p in pairs}, stats


class PluralTypesTest(unittest.TestCase):
    def test_applied(self):
        self.assertIs(census.scan_tree, plurals.scan_tree)
        self.assertEqual(census.__version__, "0.4.0")

    def test_jellyfin_argument_one_is_an_int(self):
        pairs, stats = scan({"values": JELLYFIN, "values-ar": JELLYFIN_AR})
        for q in ("few", "other"):
            p = pairs[("ar", "download_remove_description[%s]" % q)]
            self.assertEqual(p["source_key"], "download_remove_description[one]")
            self.assertEqual(p["types_before"], "S,S")
            self.assertEqual(p["types"], "I,S")
        self.assertEqual(stats["plural_types_changed"], 2)

    def test_plain_strings_untouched(self):
        pairs, _ = scan({"values": JELLYFIN, "values-ar": JELLYFIN_AR})
        p = pairs[("ar", "greeting")]
        self.assertEqual(p["types"], "S")
        self.assertNotIn("types_before", p)

    def test_text_argument_stays_text(self):
        pairs, stats = scan({"values": NAMED, "values-fr": NAMED_FR})
        p = pairs[("fr", "files_from[one]")]
        self.assertEqual(p["types"], "S,I")
        self.assertNotIn("types_before", p)
        self.assertEqual(stats["plural_types_changed"], 0)

    def test_disagreeing_forms_keep_old_type(self):
        src = g.parse_android(CLASH)
        specs = g.java_formatted(g._android_text(src["clash[one]"]))
        self.assertEqual(plurals.plural_types(src, "clash", specs), census.jvm_types(specs))
        self.assertEqual(plurals.plural_types(src, "clash", specs), "S,S")
        pairs, _ = scan({"values": CLASH, "values-de": CLASH_DE})
        self.assertNotIn("types_before", pairs[("de", "clash[other]")])

    def test_general_s_takes_the_other_forms_int(self):
        # %s prints an Int, so "%1$s" in [one] and "%1$d" in [other] agree: an Int.
        src = {"n[one]": "%1$s and %2$s", "n[other]": "%1$d items"}
        specs = g.java_formatted(src["n[one]"])
        self.assertEqual(plurals.plural_types(src, "n", specs), "I,S")


def start_jvm(tmp):
    return census.Jvm.start(os.environ.get("CENSUS_DATA_DIR", "/data"), tmp)


class FormatCheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="census-plurals-jvm-")
        cls.jvm = start_jvm(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        if cls.jvm is not None:
            cls.jvm.close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        if self.jvm is None:
            self.skipTest("no JDK")

    def verdicts(self, pair, types):
        return census.verdict(self.jvm.check([(types, pair["source"], pair["target"])])[0])[0]

    def test_jellyfin_false_positive_gone(self):
        pairs, _ = scan({"values": JELLYFIN, "values-ar": JELLYFIN_AR})
        p = pairs[("ar", "download_remove_description[few]")]
        self.assertEqual(self.verdicts(p, p["types_before"]), "crash-if-text")
        self.assertEqual(self.verdicts(p, p["types"]), "ok")

    def test_named_crash_kept(self):
        pairs, _ = scan({"values": NAMED, "values-fr": NAMED_FR})
        p = pairs[("fr", "files_from[one]")]
        self.assertIn(self.verdicts(p, p["types"]), ("crash", "crash-if-text"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
