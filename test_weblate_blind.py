# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made by MV2 of Munim, Inc. with AI agents.
"""Tests for weblate_blind.py, run against Weblate's real pattern.

weblate_deps.py downloads any missing input first (network needed once). The strings
are the census's hand-verified cases (data/verified-cases.csv), with the source
shortened where only its placeholders matter.
"""

import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import weblate_deps  # noqa: E402

weblate_deps.fetch(HERE)

import weblate_blind as wb  # noqa: E402


def row(source, translation, key="k", locale="fr", repo="o/app", exception="UnknownFormatConversionException"):
    return dict(verdict="crash", exception=exception, use="formatted", source=source, translation=translation,
                key=key, locale=locale, repo=repo, app="App")


class WeblateCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rx = wb.load_pattern(os.path.join(HERE, "weblate_format.py.txt"))

    def check(self, source, target, **kw):
        return wb.check(self.rx, source, target, **kw)

    def test_pattern_is_weblates(self):
        self.assertIn("(?![\\s])", self.rx.pattern)
        self.assertTrue(self.rx.flags & re.VERBOSE)

    def test_valid_translations_pass(self):
        self.assertIsNone(self.check("%1$s of %2$d", "%2$d de %1$s"))
        self.assertIsNone(self.check("%s and %d", "%s et %d"))
        self.assertIsNone(self.check("50%% done", "50%% fait"))

    def test_flashy_percent_sign_added_is_invisible(self):
        src = "%1$d ms, plus an additional 25 percent of it."
        for tgt in ("%1$d ms, augmentée de 25%.", "%1$d ms, 额外的 25%。", "%1$d ms, un 25% adicional da mesma."):
            self.assertIsNone(self.check(src, tgt), tgt)

    def test_cashiro_escape_dropped_is_invisible(self):
        self.assertIsNone(self.check("(%1$d%%)", "(%1$d%)"))

    def test_element_x_and_mastodon_stray_percent_is_invisible(self):
        self.assertIsNone(self.check("%1$d percents of total votes", "総投票数うち%1$d% パーセント"))
        self.assertIsNone(self.check("%,d quote", "%,d% цытата"))

    def test_space_inside_placeholder_is_flagged(self):
        self.assertEqual(self.check("Message: %s", "Mesaj:% s"), {"missing": ["s"], "extra": []})
        self.assertEqual(self.check("%s ms", "% ms"), {"missing": ["s"], "extra": []})
        self.assertEqual(self.check("%1$s of %2$s", "% 1 $ s / % 2 $ s"),
                         {"missing": ["1$s", "2$s"], "extra": []})

    def test_missing_or_native_conversion_is_flagged(self):
        self.assertTrue(self.check("%1$s uploaded", "%1$ ატვირთულია"))
        self.assertTrue(self.check("%1$dM", "%1$дмлн."))
        self.assertTrue(self.check("Est. %1$ds", "Εκτ. %1$δδ"))

    def test_extra_placeholder_is_flagged(self):
        self.assertEqual(self.check("Deleting videos: %1$d done", "Eliminazione video: %1$d riusciti, %2$d falliti"),
                         {"missing": [], "extra": ["2$d"]})

    def test_plural_leniency(self):
        v, _ = wb.verdict(self.rx, row("%d items", "one item", key="x[one]"))
        self.assertEqual(v, "plural-dependent")
        v, _ = wb.verdict(self.rx, row("%d items", "%d x %d", key="x[other]"))
        self.assertEqual(v, "flagged")
        v, _ = wb.verdict(self.rx, row("(%1$d%%)", "(%1$d%)"))
        self.assertEqual(v, "unflagged")

    def test_select_drops_cleared_rows(self):
        rows = [row("%1$s", "%1$s %2$s", repo="https://github.com/wikimedia/apps-android-wikipedia"),
                row("%1$s", "x %", locale="qq"),
                row("%1$d h", "%1$tH h"),
                row("%1$d", "%1$d%"),
                dict(row("%s", "%s"), verdict="ok")]
        kept, dropped = wb.select(rows)
        self.assertEqual(len(kept), 1)
        self.assertEqual(sum(dropped.values()), 3)

    def test_summarise(self):
        rows = [row("(%1$d%%)", "(%1$d%)"), row("Message: %s", "Mesaj:% s", repo="o/b",
                                                exception="FormatFlagsConversionMismatchException")]
        s = wb.summarise(self.rx, rows)
        g = s["groups"]["all-crash"]
        self.assertEqual(g["weblate"]["flagged"]["rows"], 1)
        self.assertEqual(g["weblate"]["unflagged"]["rows"], 1)
        self.assertEqual(g["by_kind"]["stray-percent"]["unflagged"], 1)
        self.assertEqual(g["by_kind"]["flag-mismatch"]["flagged"], 1)
        self.assertIn("(%1$d%)", wb.report(s))


if __name__ == "__main__":
    unittest.main()
