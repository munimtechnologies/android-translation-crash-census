"""Offline tests for eval_formatjs.py (no network, no guard).

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import re
import types
import unittest

import eval_formatjs as e

MM = e.PROJECTS[0]
CONTROLS = [p for p in e.PROJECTS if p["role"] == "control"]

CSV = ("project,locale,key1,key2,en1,en2,value,classes,key1_used,key2_used\r\n"
       "rocket-chat,bg,Mute_user,Unmute_user,Mute user,Unmute user,x,MUTE,True,True\r\n"
       "jellyfin-web,ru,Download,Upload,Download,Upload,y,UPLOAD,True,True\r\n"
       "bitwarden-web,ar,a.message,b.message,Confirm vault export,Confirm vault import,z,IMPORT,True,False\r\n"
       "rocket-chat,bg,Mute_user,Unmute_user,Mute user,Unmute user,x,MUTE,True,True\r\n")


class ProjectsTest(unittest.TestCase):
    def test_mattermost_pattern(self):
        self.assertEqual(MM["role"], "test")
        self.assertEqual(e.locale_file(MM, "webapp/channels/src/i18n/de.json"), "de")
        self.assertEqual(e.locale_file(MM, "webapp/channels/src/i18n/nb-NO.json"), "nb-NO")
        self.assertEqual(e.locale_file(MM, "webapp/channels/src/i18n/zh-CN.json"), "zh-CN")
        self.assertEqual(e.locale_file(MM, "webapp/channels/src/i18n/en.json"), "en")
        self.assertIsNone(e.locale_file(MM, "webapp/channels/src/i18n/i18n.ts"))
        self.assertIsNone(e.locale_file(MM, "webapp/channels/src/i18n/CLAUDE.OPTIONAL.md"))
        self.assertIsNone(e.locale_file(MM, "webapp/channels/node_modules/x/webapp/channels/src/i18n/de.json"))
        self.assertIsNone(e.locale_file(MM, "server/i18n/de.json"))

    def test_english_variants_skipped(self):
        self.assertTrue(e.skipped(MM, "en"))
        self.assertTrue(e.skipped(MM, "en-AU"))
        self.assertFalse(e.skipped(MM, "de"))
        jellyfin = CONTROLS[0]
        self.assertEqual(e.locale_file(jellyfin, "src/strings/en-us.json"), "en-us")
        self.assertTrue(e.skipped(jellyfin, "en-us"))
        self.assertTrue(e.skipped(jellyfin, "en-gb"))
        self.assertFalse(e.skipped(jellyfin, "eo"))

    def test_controls_pinned_to_holdout2_commits(self):
        self.assertEqual([p["name"] for p in CONTROLS], ["jellyfin-web", "uptime-kuma", "rocket-chat", "bitwarden-web"])
        for p in CONTROLS:
            self.assertRegex(p["ref"], r"^[0-9a-f]{40}$")
        self.assertEqual(MM["ref"], "master")
        self.assertEqual(e.locale_file(CONTROLS[2], "packages/i18n/src/locales/th-TH.i18n.json"), "th-TH")
        self.assertEqual(e.locale_file(CONTROLS[3], "apps/web/src/locales/pt_PT/messages.json"), "pt_PT")

    def test_urls(self):
        self.assertIn("/v0.14.0/", e.GUARD_URL)
        self.assertIn("/v0.13.0/", e.BASELINE_URL)
        self.assertTrue(e.PREREG_URL.endswith("antonym-collision/FORMATJS-PREREG.md"))
        self.assertTrue(e.HOLDOUT2_URL.endswith("antonym-collision/holdout2-results/warnings.csv"))


class UnwrapTest(unittest.TestCase):
    def test_old_guard_leaves_catalog(self):
        data = {"a": {"defaultMessage": "x", "description": ""}}
        self.assertIs(e.unwrap(types.SimpleNamespace(), data), data)

    def test_new_guard_is_used(self):
        g = types.SimpleNamespace(unwrap_descriptors=lambda d: {k: v["defaultMessage"] for k, v in d.items()})
        self.assertEqual(e.unwrap(g, {"a": {"defaultMessage": "x", "description": ""}}), {"a": "x"})


class RowsTest(unittest.TestCase):
    def test_expected_rows_drop_upload_and_keep_duplicates(self):
        rows = e.expected_rows(CSV)
        self.assertEqual(rows, [("bitwarden-web", "ar", "a.message", "b.message"),
                                ("rocket-chat", "bg", "Mute_user", "Unmute_user"),
                                ("rocket-chat", "bg", "Mute_user", "Unmute_user")])

    def test_row_key(self):
        row = {"project": "mattermost", "role": "test", "locale": "de", "key1": "a", "key2": "b", "value": "v"}
        self.assertEqual(e.row_key(row), ("mattermost", "de", "a", "b"))

    def test_sample_is_deterministic_and_bounded(self):
        rows = [{"project": "mattermost", "locale": "l%02d" % i, "key1": "a", "key2": "b"} for i in range(50)]
        one = e.sample(rows, e.SAMPLE_SIZE, e.SAMPLE_SEED)
        two = e.sample(list(reversed(rows)), e.SAMPLE_SIZE, e.SAMPLE_SEED)
        self.assertEqual(one, two)
        self.assertEqual(len(one), e.SAMPLE_SIZE)
        self.assertEqual(e.sample(rows[:3], e.SAMPLE_SIZE, e.SAMPLE_SEED), rows[:3])

    def test_key_candidates(self):
        self.assertIn("about.buildnumber", e.key_candidates("about.buildnumber"))
        self.assertIn("about|buildnumber", e.key_candidates("about.buildnumber"))
        self.assertIn("confirmVaultExport", e.key_candidates("confirmVaultExport.message"))
        self.assertIn("item", e.key_candidates("item_other"))

    def test_verdict(self):
        self.assertEqual([e.verdict(True), e.verdict(False), e.verdict(None)], ["HELD", "FAILED", "NOT TESTED"])

    def test_thresholds_match_prereg(self):
        self.assertEqual((e.MIN_LOCALES, e.MIN_COMPARISONS, e.MAX_MISSING_SHARE, e.MAX_PER_1000),
                         (20, 1000, 0.05, 5.0))
        self.assertEqual((e.SAMPLE_SIZE, e.SAMPLE_SEED), (40, 140))
        self.assertTrue(re.fullmatch(r"\(\?P<lang>.*", e.LANG))


if __name__ == "__main__":
    unittest.main()
