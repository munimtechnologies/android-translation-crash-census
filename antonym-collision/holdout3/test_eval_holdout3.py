"""Offline tests for eval_holdout3.py (no network, no guard).

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import re
import unittest

import eval_holdout3 as e

BY_NAME = {p["name"]: p for p in e.PROJECTS}


def row(project, used1=True, used2=True, i=0):
    return {"project": project, "locale": "l%02d" % i, "key1": "a", "key2": "b",
            "key1_used": used1, "key2_used": used2}


class ProjectsTest(unittest.TestCase):
    def test_five_projects_on_default_branches(self):
        self.assertEqual([p["name"] for p in e.PROJECTS],
                         ["mastodon", "bigbluebutton", "strapi-admin", "umami", "open-collective"])
        self.assertEqual([p["ref"] for p in e.PROJECTS], ["main", "develop", "develop", "master", "main"])
        self.assertEqual(BY_NAME["umami"]["refs"], ("en-US",))
        self.assertEqual(e.OC, "open-collective")

    def test_mastodon_pattern(self):
        p = BY_NAME["mastodon"]
        self.assertEqual(e.locale_file(p, "app/javascript/mastodon/locales/de.json"), "de")
        self.assertEqual(e.locale_file(p, "app/javascript/mastodon/locales/sr-Latn.json"), "sr-Latn")
        self.assertEqual(e.locale_file(p, "app/javascript/mastodon/locales/nan-TW.json"), "nan-TW")
        self.assertEqual(e.locale_file(p, "app/javascript/mastodon/locales/en.json"), "en")
        self.assertIsNone(e.locale_file(p, "app/javascript/mastodon/locales/index.ts"))
        self.assertIsNone(e.locale_file(p, "app/javascript/mastodon/locales/defaultMessages.json"))
        self.assertIsNone(e.locale_file(p, "config/locales/de.yml"))
        self.assertIsNone(e.locale_file(p, "node_modules/x/app/javascript/mastodon/locales/de.json"))

    def test_other_patterns(self):
        self.assertEqual(e.locale_file(BY_NAME["bigbluebutton"], "bigbluebutton-html5/public/locales/es_419.json"), "es_419")
        self.assertEqual(e.locale_file(BY_NAME["bigbluebutton"], "bigbluebutton-html5/public/locales/bg_BG.json"), "bg_BG")
        self.assertIsNone(e.locale_file(BY_NAME["bigbluebutton"], "bigbluebutton-html5/private/locales/de.json"))
        strapi = BY_NAME["strapi-admin"]
        self.assertEqual(e.locale_file(strapi, "packages/core/admin/admin/src/translations/zh-Hans.json"), "zh-Hans")
        self.assertIsNone(e.locale_file(strapi, "packages/core/admin/admin/src/translations/en-GB.js"))
        self.assertIsNone(e.locale_file(strapi, "packages/core/admin/admin/src/translations/tests/x.json"))
        self.assertIsNone(e.locale_file(strapi, "packages/plugins/i18n/admin/src/translations/de.json"))
        umami = BY_NAME["umami"]
        self.assertEqual(e.locale_file(umami, "public/intl/messages/de-DE.json"), "de-DE")
        self.assertEqual(e.locale_file(umami, "public/intl/messages/en-US.json"), "en-US")
        self.assertIsNone(e.locale_file(umami, "public/intl/other/de-DE.json"))
        oc = BY_NAME["open-collective"]
        self.assertEqual(e.locale_file(oc, "lang/sk-SK.json"), "sk-SK")
        self.assertEqual(e.locale_file(oc, "lang/en.json"), "en")
        self.assertIsNone(e.locale_file(oc, "src/lang/de.json"))

    def test_english_variants_skipped(self):
        for name in BY_NAME:
            self.assertTrue(e.skipped(BY_NAME[name], "en"))
            self.assertTrue(e.skipped(BY_NAME[name], "en-GB"))
            self.assertFalse(e.skipped(BY_NAME[name], "de"))
        self.assertTrue(e.skipped(BY_NAME["umami"], "en-US"))
        self.assertFalse(e.skipped(BY_NAME["umami"], "de-DE"))

    def test_urls(self):
        self.assertIn("/v0.14.0/", e.GUARD_URL)
        self.assertTrue(e.PREREG_URL.endswith("antonym-collision/HOLDOUT3-PREREG.md"))
        self.assertTrue(re.fullmatch(r"\(\?P<lang>.*", e.LANG))


class RulesTest(unittest.TestCase):
    def test_thresholds_match_prereg(self):
        self.assertEqual((e.MIN_LOCALES_PER_PROJECT, e.MIN_LOCALES_TOTAL, e.MIN_COMPARISONS), (10, 120, 10000))
        self.assertEqual((e.MIN_PER_1000, e.MAX_PER_1000, e.MIN_PROJECTS_WARNED), (0.5, 5.0, 3))
        self.assertEqual((e.MIN_USED_SHARE, e.OC_USED_FLOOR), (0.8, 0.5))
        self.assertEqual((e.SAMPLE_SIZE, e.SAMPLE_SEED), (40, 150))

    def test_rate(self):
        self.assertEqual(e.rate(0, 0), 0.0)
        self.assertEqual(e.rate(5, 1000), 5.0)
        self.assertEqual(e.rate(1, 2000), 0.5)
        self.assertTrue(e.rate_in_range(0.5))
        self.assertTrue(e.rate_in_range(5.0))
        self.assertFalse(e.rate_in_range(0.49))
        self.assertFalse(e.rate_in_range(5.01))

    def test_p5_no_warnings(self):
        self.assertEqual(e.p5_check([]), (None, "no warnings"))

    def test_p5_pooled(self):
        rows = [row("mastodon", i=i) for i in range(4)] + [row("mastodon", used2=False, i=4)]
        held, text = e.p5_check(rows)
        self.assertTrue(held)
        self.assertEqual(text, "4/5 rows with both keys in source, all projects")
        rows.append(row("umami", used1=False, i=5))
        self.assertFalse(e.p5_check(rows)[0])

    def test_p5_open_collective_rule(self):
        rows = [row("mastodon", i=i) for i in range(4)] + [row("open-collective", False, False, i=4)]
        held, text = e.p5_check(rows)
        self.assertTrue(held)
        self.assertEqual(text, "4/4 rows with both keys in source, without open-collective (0/1 found there)")
        rows = [row("mastodon", i=i) for i in range(4)] + [row("open-collective", i=4), row("open-collective", i=5)]
        held, text = e.p5_check(rows)
        self.assertTrue(held)
        self.assertEqual(text, "6/6 rows with both keys in source, all projects")
        rows = [row("open-collective", False, False, i=i) for i in range(3)]
        self.assertEqual(e.p5_check(rows), (None, "no rows judged (without open-collective (0/3 found there))"))

    def test_used_counts(self):
        self.assertEqual(e.used_counts([row("x"), row("x", used1=False), {"project": "x"}]), (1, 3))


class RowsTest(unittest.TestCase):
    def test_row_key(self):
        self.assertEqual(e.row_key({"project": "umami", "locale": "de-DE", "key1": "a", "key2": "b", "value": "v"}),
                         ("umami", "de-DE", "a", "b"))

    def test_sample_is_deterministic_and_bounded(self):
        rows = [row("mastodon", i=i) for i in range(50)]
        one = e.sample(rows, e.SAMPLE_SIZE, e.SAMPLE_SEED)
        two = e.sample(list(reversed(rows)), e.SAMPLE_SIZE, e.SAMPLE_SEED)
        self.assertEqual(one, two)
        self.assertEqual(len(one), e.SAMPLE_SIZE)
        self.assertEqual(e.sample(rows[:3], e.SAMPLE_SIZE, e.SAMPLE_SEED), rows[:3])

    def test_key_candidates_and_literals(self):
        self.assertIn("label.add", e.key_candidates("label.add"))
        self.assertIn("label|add", e.key_candidates("label.add"))
        self.assertIn("item", e.key_candidates("item_other"))
        self.assertIn("+1FQ+", e.key_candidates("+1FQ+"))
        found = e.literals("defineMessages({ a: { id: 'label.add' }, b: { id: \"+1FQ+\" } })")
        self.assertTrue(e.used("label.add", found))
        self.assertTrue(e.used("+1FQ+", found))
        self.assertFalse(e.used("label.remove", found))

    def test_parse(self):
        self.assertEqual(e.parse(b'\xef\xbb\xbf{"a": "b"}'), {"a": "b"})
        self.assertIsNone(e.parse(b'["a"]'))
        self.assertIsNone(e.parse(b'{'))

    def test_verdict(self):
        self.assertEqual([e.verdict(True), e.verdict(False), e.verdict(None)], ["HELD", "FAILED", "NOT TESTED"])


if __name__ == "__main__":
    unittest.main()
