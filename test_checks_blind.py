# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made by MV2 of Munim, Inc. with AI agents.
"""Tests for checks_blind.py, run against the real patterns of all three checks.

checks_deps.py downloads any missing input first (network needed once). The strings are
the census's hand-verified cases (data/verified-cases.csv), with sources shortened where
only their placeholders matter; the "%25" row is synthetic (Turkish typography puts the
percent sign before the number) and is labelled so.
"""

import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import checks_deps  # noqa: E402

checks_deps.fetch(HERE)

import checks_blind as cb  # noqa: E402
import weblate_blind as wb  # noqa: E402


def row(source, translation, key="k", locale="fr", repo="o/app", exception="UnknownFormatConversionException"):
    return dict(verdict="crash", exception=exception, use="formatted", source=source, translation=translation,
                key=key, locale=locale, repo=repo, app="App")


class Patterns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rx_w = wb.load_pattern(os.path.join(HERE, "weblate_format.py.txt"))
        cls.rx_p = wb.load_pattern(os.path.join(HERE, "translate_standard.py.txt"), "printf_pat")

    def test_printf_pat_is_translate_toolkits(self):
        self.assertTrue(self.rx_p.flags & re.VERBOSE)
        for group in ("boost_ord", "ord", "key", "fullvar", "type"):
            self.assertIn(group, self.rx_p.groupindex)

    def test_lint_pattern_matches_the_kotlin_source(self):
        path = os.path.join(HERE, "StringFormatDetector.kt.txt")
        if not os.path.exists(path):
            self.skipTest("StringFormatDetector.kt could not be downloaded")
        with open(path, encoding="utf-8") as f:
            src = f.read()
        seg = src[src.index("val FORMAT: Pattern"):]
        seg = seg[: seg.index('"([a-zA-Z%])"') + len('"([a-zA-Z%])"')]
        seg = "\n".join(line.split("//")[0] for line in seg.splitlines())
        pieces = re.findall(r'"((?:\\.|[^"\\])*)"', seg)
        pattern = "".join(re.sub(r"\\(.)", r"\1", p) for p in pieces)
        self.assertEqual(pattern, cb.LINT_FORMAT.pattern)
        self.assertIn('listOf(SdkConstants.TAG_STRING)', src)      # visits <string> only
        self.assertNotIn("TAG_PLURALS", src)


class Pofilter(Patterns):
    def check(self, s, t, **kw):
        return cb.pofilter_check(self.rx_p, s, t, **kw)

    def test_valid_translations_pass(self):
        self.assertIsNone(self.check("%1$s of %2$d", "%2$d de %1$s"))
        self.assertIsNone(self.check("%s and %d", "%s et %d"))
        self.assertIsNone(self.check("50%% done", "50%% fait"))

    def test_stray_percent_added_is_invisible(self):
        src = "%1$d ms, plus an additional 25 percent of it."
        for tgt in ("%1$d ms, augmentée de 25%.", "%1$d ms, 额外的 25%。", "%1$d ms, un 25% adicional da mesma."):
            self.assertIsNone(self.check(src, tgt), tgt)
        self.assertIsNone(self.check("%d ms, plus an additional 25 percent of it.", "%d ms, mais 25% adicionais."))
        self.assertIsNone(self.check("(%1$d%%)", "(%1$d%)"))
        self.assertIsNone(self.check("%1$d percents of total votes", "総投票数うち%1$d% パーセント"))
        self.assertIsNone(self.check("%,d quote", "%,d% цытата"))   # %,d is no placeholder to printf_pat either

    def test_lost_placeholder_is_flagged(self):
        self.assertEqual(self.check("Message: %s", "Mesaj:% s"), "Missing printf variable: %s")
        self.assertEqual(self.check("%1$s of %2$s", "% 1 $ s / % 2 $ s"), "Missing printf variable: %1$s, %2$s")
        self.assertEqual(self.check("%s deleted", "تم حذف %"), "Missing printf variable: %s")
        self.assertTrue(self.check("%d new entries", "d% مقالات جديدة", plural=True))

    def test_native_or_unknown_letter_is_flagged(self):
        self.assertEqual(self.check("%1$dM", "%1$дмлн."), "Different printf variable: %1$д")
        self.assertEqual(self.check("Est. %1$ds", "Εκτ. %1$δδ"), "Different printf variable: %1$δ")
        self.assertEqual(self.check("%d disabled", "%D vô hiệu hóa"), "Different printf variable: %D")
        self.assertTrue(self.check("%1$s uploaded", "%1$ ატვირთულია"))

    def test_percent_before_digit_is_flagged(self):
        # synthetic: a literal "25%" written Turkish-style as "%25" in a string the app formats
        self.assertEqual(self.check("25%% extra", "%25 ekstra"), "Different number of printf variables")

    def test_extra_placeholder_and_count(self):
        self.assertEqual(self.check("Deleting videos: %1$d done", "Eliminazione video: %1$d riusciti, %2$d falliti"),
                         "Added printf variable: %2$d")
        self.assertEqual(self.check("%s", "%s %s"), "Different number of printf variables")

    def test_plural_dot_zero_s(self):
        self.assertIsNone(self.check("%(n)d items", "%(n).0s item", plural=True))
        self.assertTrue(self.check("%(n)d items", "%(n).0s item"))


class Lint(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(cb.lint_classify("%1$s of %2$d"), cb.FORMATTED)
        self.assertEqual(cb.lint_classify("Battery charge is 100%!"), cb.NOT_FORMATTED)
        self.assertEqual(cb.lint_classify("%1$d ms, augmentée de 25%."), cb.NOT_FORMATTED)
        self.assertEqual(cb.lint_classify("%d ms, mais 25% adicionais."), cb.FORMATTED)   # "% a" is a placeholder
        self.assertEqual(cb.lint_classify("(%1$d%%)"), cb.FORMATTED)
        self.assertEqual(cb.lint_classify("(%1$d%)"), cb.NOT_FORMATTED)
        self.assertEqual(cb.lint_classify("%D vô hiệu hóa"), cb.IGNORE)
        self.assertEqual(cb.lint_classify("%1$tH:%1$tM"), cb.IGNORE)
        self.assertEqual(cb.lint_classify("@string/other"), cb.IGNORE)
        self.assertEqual(cb.lint_classify("plain text"), cb.NOT_FORMATTED)
        self.assertEqual(cb.lint_classify("100\\% sure"), cb.NOT_FORMATTED)

    def test_args(self):
        self.assertEqual([n for n, _ in cb.lint_args("%1$s of %2$d")], [1, 2])
        self.assertEqual([n for n, _ in cb.lint_args("%s and %d, %% done")], [1, 2])
        self.assertEqual([n for n, _ in cb.lint_args("%2$s then %s")], [2, 3])

    def test_valid_translations_pass(self):
        self.assertEqual(cb.lint_check("%1$s of %2$d", "%2$d de %1$s"), [])
        self.assertEqual(cb.lint_check("%s and %d", "%s et %d"), [])
        self.assertEqual(cb.lint_check("50%% done", "50%% fait"), [])

    def test_stray_percent_is_reported_as_a_count_mismatch(self):
        src = "%1$d ms, plus an additional 25 percent of it."
        for tgt in ("%1$d ms, augmentée de 25%.", "%1$d ms, 额外的 25%。"):
            self.assertEqual(cb.lint_check(src, tgt), [cb.STRING_FORMAT_COUNT], tgt)
        self.assertEqual(cb.lint_check("(%1$d%%)", "(%1$d%)"), [cb.STRING_FORMAT_COUNT])
        self.assertEqual(cb.lint_check("%1$d percents of total votes", "総投票数うち%1$d% パーセント"),
                         [cb.STRING_FORMAT_COUNT])
        self.assertEqual(cb.lint_check("%,d quote", "%,d% цытата"), [cb.STRING_FORMAT_COUNT])
        self.assertEqual(cb.lint_check("%s deleted", "تم حذف %"), [cb.STRING_FORMAT_COUNT])

    def test_stray_percent_before_a_conversion_letter_is_an_error(self):
        # Flashy gl/pt/pt-rBR: "25% adicional" -> "% a" parses as %a with a space flag, a second argument
        # (Formatter: MissingFormatArgumentException). Lint counts it and rejects the space flag on a float.
        src = "%d ms, plus an additional 25 percent of it."
        for tgt in ("%d ms, máis un 25% adicional da mesma.", "%d ms, mais 25% adicionais."):
            self.assertEqual(cb.lint_check(src, tgt), [cb.STRING_FORMAT_COUNT, cb.STRING_FORMAT_INVALID], tgt)

    def test_space_flag_is_invalid(self):
        self.assertEqual(cb.lint_check("Message: %s", "Mesaj:% s"), [cb.STRING_FORMAT_INVALID])
        self.assertEqual(cb.lint_check("%1$s of %2$s", "% 1 $ s / % 2 $ s"), [cb.STRING_FORMAT_COUNT])

    def test_native_letter_is_a_count_mismatch(self):
        self.assertEqual(cb.lint_check("%1$dM", "%1$дмлн."), [cb.STRING_FORMAT_COUNT])
        self.assertEqual(cb.lint_check("Est. %1$ds", "Εκτ. %1$δδ"), [cb.STRING_FORMAT_COUNT])
        self.assertEqual(cb.lint_check("%1$s uploaded", "%1$ ატვირთულია"), [cb.STRING_FORMAT_COUNT])

    def test_unknown_latin_letter_is_ignored(self):
        self.assertIsNone(cb.lint_check("%d disabled", "%D vô hiệu hóa"))

    def test_percent_before_digit_with_literal_source_is_invisible(self):
        self.assertEqual(cb.lint_check("25%% extra", "%25 ekstra"), [])

    def test_type_and_count(self):
        self.assertEqual(cb.lint_check("%1$s items", "%1$d elementi"), [cb.STRING_FORMAT_MATCHES])
        self.assertEqual(cb.lint_check("Deleting videos: %1$d done", "Eliminazione video: %1$d riusciti, %2$d falliti"),
                         [cb.STRING_FORMAT_COUNT])


class Matrix(Patterns):
    def v(self, source, translation, **kw):
        return cb.verdicts(self.rx_w, self.rx_p, row(source, translation, **kw))

    def test_flashy_only_lint_sees_it(self):
        v = self.v("%1$d ms, plus an additional 25 percent of it.", "%1$d ms, augmentée de 25%.")
        self.assertEqual((v["weblate"], v["pofilter"], v["lint"]), ("unflagged", "unflagged", "flagged"))
        self.assertEqual(v["lint_issues"], cb.STRING_FORMAT_COUNT)

    def test_flashy_gl_lint_reports_an_error(self):
        v = self.v("%d ms, plus an additional 25 percent of it.", "%d ms, máis un 25% adicional da mesma.",
                   locale="gl", exception="MissingFormatArgumentException")
        self.assertEqual((v["weblate"], v["pofilter"], v["lint"]), ("unflagged", "unflagged", "flagged"))
        self.assertEqual(v["lint_issues"], "StringFormatCount StringFormatInvalid")

    def test_inure_lint_is_the_blind_one(self):
        v = self.v("%d disabled", "%D vô hiệu hóa")
        self.assertEqual((v["weblate"], v["pofilter"], v["lint"]), ("flagged", "flagged", "ignored"))

    def test_plural_row_is_not_visited_by_lint(self):
        v = self.v("%d new entries", "d% مقالات جديدة", key="number_of_new_entries[few]")
        self.assertEqual(v["lint"], "not-visited")
        self.assertEqual(v["weblate"], "plural-dependent")
        self.assertEqual(v["pofilter"], "flagged")

    def test_synthetic_percent_before_digit_only_pofilter_sees_it(self):
        v = self.v("25%% extra", "%25 ekstra")
        self.assertEqual((v["weblate"], v["pofilter"], v["lint"]), ("unflagged", "flagged", "unflagged"))

    def test_summarise_and_report(self):
        rows = [row("(%1$d%%)", "(%1$d%)"),
                row("Message: %s", "Mesaj:% s", repo="o/b", exception="FormatFlagsConversionMismatchException"),
                row("%d disabled", "%D vô hiệu hóa", repo="o/c"),
                row("%1$s", "x %", locale="qq")]
        s = cb.summarise(self.rx_w, self.rx_p, rows)
        g = s["groups"]["all-crash"]
        self.assertEqual(g["rows"], 3)
        self.assertEqual(g["seen_by"]["lint"]["rows"], 1)
        self.assertEqual(g["seen_by"]["weblate pofilter lint"]["rows"], 1)
        self.assertEqual(g["seen_by"]["weblate pofilter"]["rows"], 1)
        self.assertEqual(g["checks"]["lint"], {"flagged": 2, "ignored": 1})
        self.assertEqual(g["by_kind"]["stray-percent"]["none"], 0)
        self.assertEqual(s["dropped"], {"translator notes (qq)": 1})
        self.assertIn("| seen by | rows | repos |", cb.report(s))


if __name__ == "__main__":
    unittest.main()
