#!/usr/bin/env python3
"""Tests for census_fixes.py (census 0.3.1). Standard library only.

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import os
import shutil
import tempfile
import unittest

import census_fixes as fixes
import census
import l10n_guard as g

# Wikipedia's temp_account_edit_status (values/strings.xml) and the shapes its
# translations take (values-pt, values-ru, values-de) at 3f4feaf.
SOURCE = ('<resources><string name="temp_account_edit_status"><![CDATA[<b>You are using a '
          'temporary account.</b> Your edit will be attributed to %1$s. <a href="%2$s">'
          'Learn more</a>.]]></string></resources>')
GOOD = ('<resources><string name="temp_account_edit_status">&lt;b&gt;Du benutzt ein '
        'temporäres Konto.&lt;/b&gt; %1$s. &lt;a href=\\"%2$s\\"&gt;Mehr&lt;/a&gt;.'
        '</string></resources>')
BROKEN_PT = ('<resources><string name="temp_account_edit_status">&lt;b&gt;Está a utilizar uma '
             'conta temporária.&lt;/b&gt; %1$s. &lt;a href=\\"%2$s2Saiba mais.</string></resources>')
SPAN_RU = ('<resources><string name="temp_account_edit_status">%1$s. &lt;a href=\\"&lt;span '
           'class=\\"notranslate\\" translate=\\"no\\"&gt;%2$s \\"&gt;Узнать больше&lt;/a&gt;.'
           '</string></resources>')
WRONG_INDEX = ('<resources><string name="temp_account_edit_status">%1$s. &lt;a href=\\"%3$s\\"'
               '&gt;Mehr&lt;/a&gt;.</string></resources>')


def text(xml, version=None):
    raw = g.parse_android(xml)["temp_account_edit_status"]
    return (version or fixes.android_text)(raw)


class AndroidTextTest(unittest.TestCase):
    def test_cdata_href_placeholder_is_kept(self):
        source = text(SOURCE)
        self.assertIn("%2$s", source)
        self.assertEqual(max(n for n, _ in g.java_formatted(source)), 2)

    def test_051_dropped_it(self):
        # The false positive this release fixes.
        self.assertNotIn("%2$s", text(SOURCE, fixes._android_text_051))

    def test_escaped_href_placeholder_is_kept(self):
        self.assertIn("%2$s", text(GOOD))

    def test_wikipedia_translations_do_not_crash(self):
        for xml in (GOOD, BROKEN_PT, SPAN_RU):
            self.assertEqual(g.check_java_format(text(SOURCE), text(xml)), [], xml)

    def test_wikipedia_translations_crashed_in_051(self):
        old = fixes._android_text_051
        problems = g.check_java_format(text(SOURCE, old), text(BROKEN_PT, old))
        self.assertTrue(problems and problems[0]["level"] == g.ERROR)

    def test_argument_hidden_in_a_link_is_still_caught(self):
        problems = g.check_java_format(text(SOURCE), text(WRONG_INDEX))
        self.assertEqual(len(problems), 1)
        self.assertIn("uses argument 3 but the source passes 2", problems[0]["message"])

    def test_real_elements_lose_markup_and_attributes(self):
        xml = ('<resources><string name="s">Hi <b>%1$s</b>, <a href="%2$s">more</a> '
               '<xliff:g xmlns:xliff="urn:oasis:names:tc:xliff:document:1.2" id="n">%3$d</xliff:g>'
               '</string></resources>')
        self.assertEqual(fixes.android_text(g.parse_android(xml)["s"]), "Hi %1$s, more %3$d")

    def test_unchanged_without_text_markup(self):
        for raw in ['Say \\"%1$s\\"', "  a   b %d ", "50 < 60 %1$s", "\\u00e9 %s",
                    '"keep   spaces" %1$s', "<b>x</b> %2$d of %1$d"]:
            self.assertEqual(fixes.android_text(raw), fixes._android_text_051(raw), raw)

    def test_text_markup_is_kept_literally(self):
        self.assertEqual(fixes.android_text('&lt;a href=\\"%1$s\\"&gt;'.replace("&lt;", "<")
                                            .replace("&gt;", ">")), '<a href="%1$s">')
        self.assertEqual(fixes.android_text("<0>%1$s</0>"), "<0>%1$s</0>")


class ApplyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        res = os.path.join(self.tmp, "app", "src", "main", "res")
        for folder, xml in (("values", SOURCE), ("values-pt", BROKEN_PT), ("values-qq", WRONG_INDEX),
                            ("values-de", WRONG_INDEX)):
            os.makedirs(os.path.join(res, folder))
            with open(os.path.join(res, folder, "strings.xml"), "w", encoding="utf-8") as f:
                f.write('<?xml version="1.0" encoding="utf-8"?>\n' + xml)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_apply(self):
        fixes.apply()
        fixes.apply()
        self.assertIs(g._android_text, fixes.android_text)
        self.assertEqual(census.__version__, "0.3.1")
        self.assertIn("/0.3.1 ", census.USER_AGENT)
        pairs, _ = census.scan_tree(self.tmp)
        by_locale = {p["locale"]: p for p in pairs}
        self.assertEqual(sorted(by_locale), ["de", "pt"])  # values-qq is skipped
        self.assertEqual(by_locale["pt"]["static"], "ok")
        self.assertEqual(by_locale["de"]["static"], "crash")
        self.assertEqual(by_locale["de"]["types"], "S,S")


if __name__ == "__main__":
    unittest.main(verbosity=2)
