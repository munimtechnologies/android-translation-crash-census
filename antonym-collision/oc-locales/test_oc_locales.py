"""Offline tests for oc_locales.py (no network, no guard).

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import unittest

import oc_locales as o


class FakeGuard:
    """Flat catalogs, one antonym pair (a, b), a collision when both translate alike."""
    __version__ = "0.14.0"

    def flatten(self, data):
        return dict(data)

    def antonym_pairs(self, src):
        return [("a", "b")]

    def check_catalog(self, ref, tgt):
        if tgt.get("a") == tgt.get("b"):
            return [{"code": "antonym-collision", "key": "a", "other_key": "b"},
                    {"code": "placeholder-missing", "key": "c", "other_key": None}]
        return []

    def _antonym_signature(self, text):
        return (["dir"], [text])


def group(comparisons, warnings):
    return {"comparisons": comparisons, "warnings": warnings}


class PatternsTest(unittest.TestCase):
    def test_locale_files(self):
        self.assertEqual(o.locale_of("lang/pt-BR.json"), "pt-BR")
        self.assertEqual(o.locale_of("lang/sk-SK.json"), "sk-SK")
        self.assertEqual(o.locale_of("lang/en.json"), "en")
        self.assertIsNone(o.locale_of("src/lang/de.json"))
        self.assertIsNone(o.locale_of("lang/index.js"))
        self.assertIsNone(o.locale_of("node_modules/x/lang/de.json"))

    def test_workflow_files(self):
        self.assertEqual(o.workflow_locale(".github/workflows/i18n-translate-pt-BR.md"), "pt-BR")
        self.assertEqual(o.workflow_locale(".github/workflows/i18n-translate-de.md"), "de")
        self.assertIsNone(o.workflow_locale(".github/workflows/i18n-translate-de.lock.yml"))
        self.assertIsNone(o.workflow_locale(".github/workflows/i18n/shared/i18n-translate.md"))
        self.assertIsNone(o.workflow_locale(".github/workflows/ci.yml"))

    def test_skipped(self):
        self.assertTrue(o.skipped("en"))
        self.assertTrue(o.skipped("en-GB"))
        self.assertFalse(o.skipped("de"))
        self.assertFalse(o.skipped("es"))

    def test_key_kind(self):
        self.assertEqual(o.key_kind("++1FQ+"), "hashed")
        self.assertEqual(o.key_kind("/66Po2"), "hashed")
        self.assertEqual(o.key_kind("0b9yMU"), "hashed")
        self.assertEqual(o.key_kind("cXyqhA"), "ambiguous")
        self.assertEqual(o.key_kind("Accept"), "ambiguous")
        self.assertEqual(o.key_kind("Account.Freeze"), "named")
        self.assertEqual(o.key_kind("All"), "named")
        self.assertEqual(o.key_kind("AcceptedOn"), "named")
        self.assertEqual(o.key_kind("ACH Debit"), "named")

    def test_group_of(self):
        agents = {"de", "es", "fr", "pt-BR"}
        self.assertEqual(o.group_of("de", agents), "agent")
        self.assertEqual(o.group_of("pt-BR", agents), "agent")
        self.assertEqual(o.group_of("pt", agents), "crowdin")
        self.assertEqual(o.group_of("ja", agents), "crowdin")

    def test_constants(self):
        self.assertEqual(o.EXPECTED_AGENT, ("de", "es", "fr", "pt-BR"))
        self.assertEqual(o.GROUPS, ("agent", "crowdin"))
        self.assertEqual((o.MIN_LOCALES, o.MIN_AGENT_SHARE), (18, 0.5))
        self.assertEqual((o.MIN_GROUP_COMPARISONS, o.MIN_WARNINGS_FOR_Q2), (500, 5))
        self.assertIn("/v0.14.0/", o.GUARD_URL)
        self.assertTrue(o.PREREG_URL.endswith("antonym-collision/OC-LOCALES-PREREG.md"))
        self.assertEqual(o.REPO, "opencollective/opencollective-frontend")


class ScanTest(unittest.TestCase):
    def setUp(self):
        self.g = FakeGuard()
        self.ref = {"a": "Open", "b": "Close", "c": "Other"}
        self.src = self.g.flatten(self.ref)
        self.pairs = self.g.antonym_pairs(self.src)

    def test_collision(self):
        s = o.scan_locale(self.g, self.ref, self.src, self.pairs, {"a": "Offen", "b": "Offen", "c": "Other"})
        self.assertEqual((s["keys"], s["translated"], s["comparisons"], s["both_translated"]), (3, 2, 1, 1))
        self.assertEqual(len(s["rows"]), 1)
        row = s["rows"][0]
        self.assertEqual((row["key1"], row["key2"], row["kind1"], row["kind2"]), ("a", "b", "named", "named"))
        self.assertEqual((row["en1"], row["en2"], row["value"], row["classes"]), ("Open", "Close", "Offen", "dir"))

    def test_no_collision_and_untranslated_copy(self):
        s = o.scan_locale(self.g, self.ref, self.src, self.pairs, {"a": "Offen", "b": "Close", "c": "x"})
        self.assertEqual((s["keys"], s["translated"], s["comparisons"], s["both_translated"]), (3, 2, 1, 0))
        self.assertEqual(s["rows"], [])

    def test_blank_and_missing_not_compared(self):
        s = o.scan_locale(self.g, self.ref, self.src, self.pairs, {"a": "  ", "c": "Autre"})
        self.assertEqual((s["keys"], s["translated"], s["comparisons"], s["both_translated"]), (2, 1, 0, 0))
        self.assertEqual(s["rows"], [])

    def test_parse(self):
        self.assertEqual(o.parse(b'\xef\xbb\xbf{"a": "b"}'), {"a": "b"})
        self.assertIsNone(o.parse(b'["a"]'))
        self.assertIsNone(o.parse(b'{'))
        self.assertIsNone(o.parse(b''))


class StatsTest(unittest.TestCase):
    def test_rate(self):
        self.assertEqual(o.rate(0, 0), 0.0)
        self.assertEqual(o.rate(5, 1000), 5.0)
        self.assertEqual(o.rate(1, 2000), 0.5)

    def test_wilson(self):
        self.assertEqual(o.wilson(0, 0), (0.0, 1.0))
        low, high = o.wilson(0, 100)
        self.assertAlmostEqual(low, 0.0, places=9)
        self.assertTrue(0.036 < high < 0.038)
        low, high = o.wilson(50, 100)
        self.assertAlmostEqual(low + high, 1.0)
        self.assertTrue(0.40 < low < 0.41)
        low, high = o.wilson(5, 1000)
        self.assertTrue(0.0 < low < 0.005 < high < 0.02)
        self.assertEqual(o.wilson(100, 100)[1], 1.0)

    def test_overlap(self):
        self.assertTrue(o.intervals_overlap((0.0, 0.1), (0.05, 0.2)))
        self.assertTrue(o.intervals_overlap((0.0, 0.1), (0.1, 0.2)))
        self.assertFalse(o.intervals_overlap((0.0, 0.1), (0.2, 0.3)))
        self.assertFalse(o.intervals_overlap((0.2, 0.3), (0.0, 0.1)))

    def test_group_totals(self):
        locales = [{"group": "agent", "comparisons": 600, "warnings": 1},
                   {"group": "crowdin", "comparisons": 300, "warnings": 0},
                   {"group": "crowdin", "comparisons": 100, "warnings": 1}]
        t = o.group_totals(locales)
        self.assertEqual((t["agent"]["locales"], t["agent"]["comparisons"], t["agent"]["warnings"]), (1, 600, 1))
        self.assertEqual((t["crowdin"]["locales"], t["crowdin"]["comparisons"], t["crowdin"]["warnings"]), (2, 400, 1))
        self.assertEqual((t["agent"]["per_1000"], t["crowdin"]["per_1000"]), (1.667, 2.5))
        self.assertEqual(len(t["agent"]["per_1000_interval"]), 2)
        empty = o.group_totals([])
        self.assertEqual(empty["agent"]["comparisons"], 0)
        self.assertEqual(empty["agent"]["per_1000_interval"], [0.0, 1000.0])

    def test_q1(self):
        self.assertEqual(o.q1_check({"agent": group(600, 1), "crowdin": group(400, 1)}),
                         (True, "agent locales 600 of 1000 comparisons (60.0%)"))
        self.assertTrue(o.q1_check({"agent": group(500, 0), "crowdin": group(500, 0)})[0])
        self.assertFalse(o.q1_check({"agent": group(400, 0), "crowdin": group(600, 0)})[0])
        self.assertEqual(o.q1_check({"agent": group(0, 0), "crowdin": group(0, 0)}), (None, "no comparisons"))

    def test_q2_not_tested(self):
        held, text = o.q2_check({"agent": group(600, 3), "crowdin": group(400, 2)})
        self.assertIsNone(held)
        self.assertEqual(text, "agent 3/600, crowdin 2/400 warnings/comparisons (too few to test)")
        self.assertIsNone(o.q2_check({"agent": group(1000, 2), "crowdin": group(1000, 2)})[0])

    def test_q2_overlap_and_not(self):
        held, text = o.q2_check({"agent": group(1000, 3), "crowdin": group(1000, 2)})
        self.assertTrue(held)
        self.assertTrue(text.startswith("agent 3/1000, crowdin 2/1000 warnings/comparisons; per 1,000: agent 3.00 ("))
        held, text = o.q2_check({"agent": group(1000, 0), "crowdin": group(1000, 50)})
        self.assertFalse(held)
        self.assertIn("crowdin 50.00 (", text)

    def test_verdict(self):
        self.assertEqual([o.verdict(True), o.verdict(False), o.verdict(None)], ["HELD", "FAILED", "NOT TESTED"])


if __name__ == "__main__":
    unittest.main()
