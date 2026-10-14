# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made by MV2 of Munim, Inc. with AI agents.
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taxonomy  # noqa: E402

U = "UnknownFormatConversionException"


class ClassifyTest(unittest.TestCase):
    def check(self, translation, kind, exception=U):
        self.assertEqual(taxonomy.classify(exception, translation), kind, translation)

    def test_stray_percent(self):
        self.check("(%1$d%)", "stray-percent")
        self.check("%1$d%", "stray-percent")
        self.check("%,d% цытата", "stray-percent")
        self.check("%Каждую минуту", "stray-percent")
        self.check("电量 %1$d %", "stray-percent")
        self.check("% Delinger", "stray-percent")

    def test_malformed_index(self):
        self.check("% 1 $ s faylda", "malformed-index")
        self.check("%$1s", "malformed-index")
        self.check("%1 $s", "malformed-index")

    def test_conversion_missing(self):
        # Formatter reads the space after `$` as a flag; the letter is still missing.
        self.check("%1$ musikspelare", "conversion-missing")
        self.check("%1$ ઘ %2$ મિ", "conversion-missing")
        self.check("s$%1", "conversion-missing")
        self.check("Dauer: %1$", "conversion-missing")

    def test_conversion_native(self):
        self.check("%1$ч %2$м", "conversion-native")
        self.check("Отложить на %1$с", "conversion-native")
        self.check("%1$دم", "conversion-native")
        self.check("Εκτ. %1$δδ", "conversion-native")
        # A dropped letter followed by a CJK word looks the same to Formatter.
        self.check("未找到符合%1$的维基数据项目。", "conversion-native")

    def test_lookalikes(self):
        self.assertTrue(taxonomy.is_lookalike("с"))
        self.assertTrue(taxonomy.is_lookalike("д"))
        self.assertTrue(taxonomy.is_lookalike("د"))
        self.assertFalse(taxonomy.is_lookalike("的"))
        self.assertFalse(taxonomy.is_lookalike("ч"))

    def test_conversion_invalid(self):
        self.check("%1$DH %2$DM", "conversion-invalid")
        self.check("%1$h %2$m", "conversion-invalid")
        self.check("Avètz convidat %1$s a venir al grop « %2$vs»", "conversion-invalid")

    def test_by_exception(self):
        self.check("%1$tp %2$g", "wrong-type", "IllegalFormatConversionException")
        self.check("Mesaj:% s", "flag-mismatch", "FormatFlagsConversionMismatchException")
        self.check("%1$d, %2$d", "argument-not-passed", "MissingFormatArgumentException")

    def test_valid_specs_are_skipped(self):
        self.assertIsNone(taxonomy.first_unknown("%1$d%% done, %2$tm %s %n"))
        self.assertEqual(taxonomy.first_unknown("ok %d then 50% plus")[1:], ("% ", "p"))

    def test_script_of(self):
        self.assertEqual(taxonomy.script_of("ч"), "CYRILLIC")
        self.assertEqual(taxonomy.script_of("د"), "ARABIC")

    def test_summarise(self):
        rows = [
            {"verdict": "crash", "exception": U, "use": "formatted", "translation": "%1$ч",
             "repo": "r1", "locale": "ru", "key": "k", "source": "%1$dh", "app": "A"},
            {"verdict": "crash", "exception": U, "use": "unreferenced", "translation": "50%",
             "repo": "r2", "locale": "fr", "key": "k", "source": "%1$d", "app": "B"},
            {"verdict": "crash-if-text", "exception": "IllegalFormatConversionException",
             "use": "formatted", "translation": "%d", "repo": "r3", "locale": "de", "key": "k",
             "source": "%s", "app": "C"},
        ]
        s = taxonomy.summarise(rows)
        self.assertEqual(s["groups"]["all-crash"]["rows"], 2)
        self.assertEqual(s["groups"]["formatted-crash"]["rows"], 1)
        self.assertEqual(s["groups"]["formatted-crash"]["by_kind"]["conversion-native"]["rows"], 1)
        self.assertEqual(s["groups"]["formatted-crash"]["conversion_native_scripts"], {"CYRILLIC": 1})
        self.assertEqual(s["groups"]["formatted-crash"]["conversion_native_lookalikes"], 0)
        self.assertIn("conversion-native", taxonomy.report(s))


if __name__ == "__main__":
    unittest.main()
