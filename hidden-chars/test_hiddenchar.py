# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for hiddenchar.py (no network, no git)."""
import os
import shutil
import tempfile
import unittest

import hiddenchar as hc

SOURCE = r'''<?xml version="1.0" encoding="utf-8"?>
<resources>
  <string name="hello">Hello</string>
  <string name="keep" translatable="false">Keep</string>
  <string name="esc">Line</string>
  <plurals name="items"><item quantity="one">%d item</item><item quantity="other">%d items</item></plurals>
  <string-array name="arr"><item>One</item><item>Two</item></string-array>
  <string name="rtl">UTC</string>
</resources>
'''

GERMAN = r'''<?xml version="1.0" encoding="utf-8"?>
<resources>
  <string name="hello">Hal​lo</string>
  <string name="keep">K&#8203;eep</string>
  <string name="esc">Zei&#173;le</string>
  <plurals name="items"><item quantity="one">%d Element</item><item quantity="other">%d Elemente&#8297;</item></plurals>
  <string-array name="arr"><item>Eins</item><item>Zwei</item></string-array>
  <string name="rtl">UTC&#8207;</string>
  <string name="orphan">x&#8203;</string>
</resources>
'''

HEBREW = r'''<?xml version="1.0" encoding="utf-8"?>
<resources>
  <string name="hello">Shalom</string>
  <string name="rtl">UTC&#8207;</string>
</resources>
'''

NIGHT = r'''<?xml version="1.0" encoding="utf-8"?>
<resources>
  <string name="hello">Hel&#8203;lo</string>
</resources>
'''


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class CharTests(unittest.TestCase):
    def test_classes(self):
        self.assertEqual(hc.char_class(0x200B), "zwsp")
        self.assertEqual(hc.char_class(0x00AD), "shy")
        self.assertEqual(hc.char_class(0x200D), "joiner")
        self.assertEqual(hc.char_class(0x200F), "mark")
        self.assertEqual(hc.char_class(0x202E), "bidi")
        self.assertEqual(hc.char_class(0x2066), "bidi")
        self.assertEqual(hc.char_class(0xFEFF), "wj-bom")
        self.assertEqual(hc.char_class(0x2061), "other-cf")
        self.assertIsNone(hc.char_class(0x0600))
        self.assertIsNone(hc.char_class(0xE0067))
        self.assertIsNone(hc.char_class(ord("a")))
        self.assertIsNone(hc.char_class(0x00A0))

    def test_decode(self):
        self.assertEqual(hc.decode_android("a\\u200Bb"), "a​b")
        self.assertEqual(hc.decode_android("\\\\u200B"), "\\\\u200B")

    def test_extra_only_when_missing_from_source(self):
        self.assertEqual(hc.extra_chars("a", "a​"), {"zwsp": [0x200B]})
        self.assertEqual(hc.extra_chars("a​", "b​"), {})
        self.assertEqual(hc.extra_chars("a", "a b"), {})

    def test_primary(self):
        self.assertTrue(hc.is_primary({"zwsp": [0x200B]}, "de"))
        self.assertFalse(hc.is_primary({"zwsp": [0x200B]}, "km"))
        self.assertFalse(hc.is_primary({"zwsp": [0x200B]}, "th"))
        self.assertFalse(hc.is_primary({"mark": [0x200F]}, "ar"))
        self.assertTrue(hc.is_primary({"mark": [0x200F]}, "de"))
        self.assertFalse(hc.is_primary({"joiner": [0x200C]}, "de"))
        self.assertTrue(hc.is_primary({"shy": [0xAD]}, "fa"))
        self.assertFalse(hc.is_control({"zwsp": [0x200B]}, "de"))
        self.assertTrue(hc.is_control({"bidi": [0x202E]}, "de"))

    def test_show(self):
        self.assertEqual(hc.show("a​b"), "a<U+200B>b")
        s = hc.show("x" * 300)
        self.assertEqual(len(s), 203)
        self.assertTrue(s.endswith("..."))


class LocaleTests(unittest.TestCase):
    def test_locale_dirs(self):
        self.assertEqual(hc.locale_of("values-de"), "de")
        self.assertEqual(hc.locale_of("values-pt-rBR"), "pt")
        self.assertEqual(hc.locale_of("values-b+sr+Latn"), "sr")
        self.assertEqual(hc.locale_of("values-iw"), "iw")
        for d in ("values", "values-night", "values-v21", "values-car", "values-en-rXA",
                  "values-land", "values-sw600dp"):
            self.assertIsNone(hc.locale_of(d), d)


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        res = os.path.join(self.root, "app", "src", "main", "res")
        write(os.path.join(res, "values", "strings.xml"), SOURCE)
        write(os.path.join(res, "values-de", "strings.xml"), GERMAN)
        write(os.path.join(res, "values-de", "broken.xml"), "<resources><string")
        write(os.path.join(res, "values-iw", "strings.xml"), HEBREW)
        write(os.path.join(res, "values-night", "strings.xml"), NIGHT)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_scan(self):
        locales, hits, errors = hc.scan_checkout(self.root)
        self.assertEqual(sorted(locales), ["app/src/main/res/values-de", "app/src/main/res/values-iw"])
        de = locales["app/src/main/res/values-de"]
        self.assertEqual(de["lang"], "de")
        self.assertEqual(de["units"], 7)
        self.assertEqual(de["extra"], {"zwsp": 1, "shy": 1, "bidi": 1, "mark": 1})
        self.assertEqual(de["primary"], 4)
        self.assertEqual(de["control"], 3)
        iw = locales["app/src/main/res/values-iw"]
        self.assertEqual(iw["units"], 2)
        self.assertEqual(iw["extra"], {"mark": 1})
        self.assertEqual(iw["primary"], 0)
        self.assertEqual(iw["control"], 0)
        self.assertEqual(len(hits), 4)
        self.assertTrue(all(h["lang"] == "de" for h in hits))
        hello = [h for h in hits if h["key"] == "string:hello"][0]
        self.assertEqual(hello["target"], "Hal<U+200B>lo")
        self.assertEqual(hello["codepoints"], "U+200B")
        self.assertEqual(hello["res_dir"], "app/src/main/res")
        self.assertEqual(len(errors), 1)


class PlatformTests(unittest.TestCase):
    def test_detect(self):
        sep = "\x1f"
        weblate = sep.join(["hosted@weblate.org", "Hosted Weblate", "u@x.org", "User",
                            "Translated using Weblate (German)"])
        crowdin = sep.join(["noreply@github.com", "GitHub", "support+bot@crowdin.com", "Crowdin Bot",
                            "New translations strings.xml (French)"])
        other = sep.join(["a@b.org", "A", "a@b.org", "A", "Fix bug"])
        self.assertEqual(hc.detect_platform(weblate + "\n" + other), "weblate")
        self.assertEqual(hc.detect_platform(crowdin + "\n" + other), "crowdin")
        self.assertEqual(hc.detect_platform(crowdin + "\n" + weblate), "weblate")
        self.assertEqual(hc.detect_platform(other), "other")

    def test_clone_url(self):
        self.assertEqual(hc.clone_url("https://github.com/foo/bar/tree/main/app"), "https://github.com/foo/bar")
        self.assertEqual(hc.clone_url("https://gitlab.com/group/sub/proj/-/tree/master"),
                         "https://gitlab.com/group/sub/proj")
        self.assertEqual(hc.clone_url("https://www.github.com/Foo/Bar.git"), "https://github.com/Foo/Bar")
        self.assertEqual(hc.clone_url("https://codeberg.org/u/r/src/branch/main"), "https://codeberg.org/u/r")
        self.assertIsNone(hc.clone_url("ftp://x.org/a/b"))
        self.assertIsNone(hc.clone_url("https://example.org"))
        self.assertIsNone(hc.clone_url(None))

    def test_load_sources(self):
        index = {"packages": {
            "a": {"metadata": {"sourceCode": "https://github.com/x/y"}},
            "b": {"metadata": {"sourceCode": "https://github.com/X/Y/"}},
            "c": {"metadata": {}}}}
        self.assertEqual(hc.load_sources(index), ["https://github.com/x/y"])


def loc(lang, units, extra, primary, control):
    return {"lang": lang, "units": units, "extra": extra, "primary": primary, "control": control}


class AggregateTests(unittest.TestCase):
    def results(self, w_zwsp=1):
        return [
            {"repo": "w", "status": "ok", "platform": "weblate",
             "locales": {"res/values-de": loc("de", 1000, {"zwsp": w_zwsp, "shy": 5}, 5 + w_zwsp, 5)}},
            {"repo": "n", "status": "ok", "platform": "other",
             "locales": {"res/values-fr": loc("fr", 1000, {"zwsp": 10, "shy": 5}, 15, 5)}},
            {"repo": "n2", "status": "ok", "platform": "crowdin",
             "locales": {"res/values-km": loc("km", 100, {"zwsp": 50}, 0, 0)}},
            {"repo": "u", "status": "ok", "platform": "unknown",
             "locales": {"res/values-es": loc("es", 10, {}, 0, 0),
                         "res/values-ar": loc("ar", 10, {"mark": 4}, 0, 0)}},
            {"repo": "f", "status": "clone-failed"},
        ]

    def test_held(self):
        s = hc.aggregate(self.results())
        self.assertEqual(s["repos_ok"], 4)
        self.assertEqual(s["repos_with_primary"], 2)
        self.assertEqual(s["weblate"]["repos"], 1)
        self.assertEqual(s["non_weblate"]["repos"], 2)
        self.assertEqual(s["non_weblate"]["zwsp_units"], 1000)
        self.assertEqual(s["non_weblate"]["units"], 1100)
        self.assertAlmostEqual(s["zwsp_rate_ratio_W_over_N"], 0.1)
        self.assertAlmostEqual(s["control_rate_ratio_W_over_N"], 1.1)
        self.assertEqual(s["primary_class_hits"]["zwsp"], 11)
        self.assertEqual(s["mark_units_all"], 4)
        self.assertEqual(s["verdicts"], {"P1": "HELD", "P2": "HELD", "P3": "HELD", "P4": "HELD"})

    def test_p2_failed(self):
        s = hc.aggregate(self.results(w_zwsp=10))
        self.assertAlmostEqual(s["zwsp_rate_ratio_W_over_N"], 1.0)
        self.assertEqual(s["verdicts"]["P2"], "FAILED")

    def test_without_top(self):
        r = self.results()
        rest = hc.without_top(r, "non-weblate")
        self.assertEqual(len(rest), len(r) - 1)
        self.assertNotIn("n", [x["repo"] for x in rest])
        self.assertIsNone(hc.aggregate(rest)["zwsp_rate_ratio_W_over_N"])


if __name__ == "__main__":
    unittest.main()
