# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made by MV2 of Munim, Inc. with AI agents.
import csv
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patterns  # noqa: E402

FIELDS = ["verdict", "exception", "use", "static", "static_detail", "locale", "key", "source_key",
          "source", "translation", "file", "link", "repo", "commit", "packages", "app"]


def row(source, translation, key="k", locale="fr", verdict="crash", use="formatted", repo="r", app="A"):
    r = dict.fromkeys(FIELDS, "")
    r.update(verdict=verdict, use=use, locale=locale, key=key, source_key=key.split("[")[0],
             source=source, translation=translation, repo=repo, app=app,
             exception="UnknownFormatConversionException")
    return r


class TagTest(unittest.TestCase):
    def test_escape_dropped(self):
        # Cashiro hu and ro (hand-verified, issue #189)
        self.assertEqual(patterns.tag(row("(%1$d%%)", "(%1$d%)", locale="hu"))[0], "escape-dropped")
        self.assertEqual(patterns.tag(row("%1$d%%", "%1$d%", locale="ro"))[0], "escape-dropped")

    def test_percent_sign_added_spelled(self):
        # Flashy fr and gl: the English writes "25 percent"
        src = "A dit lasts %1$d ms, plus an additional 25 percent of it."
        t, d = patterns.tag(row(src, "Un point dure %1$d ms, augmentée de 25%."))
        self.assertEqual((t, d), ("percent-sign-added", {"spells_percent": True}))
        t, d = patterns.tag(row(src, "Un punto dura %1$d ms, un 25% adicional da mesma.", locale="gl"))
        self.assertEqual(t, "percent-sign-added")
        # Element X ja: a percent sign right after the placeholder
        t, d = patterns.tag(row("%1$d percent of total votes", "%1$d% パーセント", locale="ja"))
        self.assertEqual((t, d["spells_percent"]), ("percent-sign-added", True))

    def test_percent_sign_added_unspelled(self):
        t, d = patterns.tag(row("Volume %1$d", "Lautstärke %1$d %", locale="de"))
        self.assertEqual((t, d), ("percent-sign-added", {"spells_percent": False}))

    def test_extra_placeholder_pasted_plural(self):
        # pretixSCAN ko: both English forms pasted into Korean's single plural form
        t, d = patterns.tag(row("%d items", "단수형: %d개 / 복수형: %d개", key="sync[other]", locale="ko"))
        self.assertEqual((t, d), ("extra-placeholder", {"plural": True, "one_form_locale": True}))
        t, d = patterns.tag(row("%d of %s", "%d de %s (%d)", locale="b+zh+Hans"))
        self.assertEqual((t, d), ("extra-placeholder", {"plural": False, "one_form_locale": True}))

    def test_no_tag(self):
        self.assertEqual(patterns.tag(row("%s left", "1 %s"))[0], None)
        self.assertEqual(patterns.tag(row("%1$d%%", "%1$d %%"))[0], None)
        self.assertEqual(patterns.tag(row("%1$s and %1$s", "%1$s et %1$s"))[0], None)
        self.assertEqual(patterns.tag(row("via %1$s", "trí% 1$s"))[0], None)
        # a percent sign in the source too: not "added"
        self.assertEqual(patterns.tag(row("50% off %s", "50% de %s"))[0], None)
        # 25%sur (no space) is still a percent sign; 25%s is a placeholder
        self.assertEqual(patterns.percent_uses("de 25%sur"), 1)
        self.assertEqual(patterns.percent_uses("de 25 %s"), 0)

    def test_counters(self):
        self.assertEqual(patterns.unindexed("%d %1$s %% %n %<d %s"), 2)
        self.assertEqual(patterns.base_language("zh-rCN"), "zh")
        self.assertEqual(patterns.base_language("b+sr+Latn"), "sr")
        self.assertEqual(patterns.base_language("in"), "in")


class SummaryTest(unittest.TestCase):
    def test_summary_and_files(self):
        rows = [row("(%1$d%%)", "(%1$d%)", repo="cashiro"),
                row("%1$d%%", "%1$d%", repo="cashiro", use="unreferenced"),
                row("%d items", "%d / %d", key="x[other]", locale="ja", repo="pretix"),
                row("%1$s", "%1$", repo="other"),
                row("%1$d%%", "%1$d%", verdict="crash-if-text", repo="ignored")]
        s = patterns.summarise(rows)
        g = s["groups"]["all-crash"]
        self.assertEqual((g["rows"], g["repos"]), (4, 3))
        self.assertEqual(g["by_tag"]["escape-dropped"], {"rows": 2, "repos": 1, "flags": {}})
        self.assertEqual(g["by_tag"]["extra-placeholder"]["flags"], {"plural": 1, "one_form_locale": 1})
        f = s["groups"]["formatted-crash"]
        self.assertEqual(f["by_tag"]["escape-dropped"]["rows"], 1)
        self.assertEqual(len(s["tagged"]), 3)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "findings.csv")
            with open(path, "w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=FIELDS)
                w.writeheader()
                w.writerows(rows)
            self.assertEqual(patterns.summarise(patterns.read_rows(path)), s)
            sys.argv = ["patterns.py", path, "--out-dir", os.path.join(d, "out")]
            patterns.main()
            with open(os.path.join(d, "out", "patterns.json"), encoding="utf-8") as fh:
                self.assertEqual(json.load(fh)["groups"]["all-crash"]["rows"], 4)
            with open(os.path.join(d, "out", "patterns.md"), encoding="utf-8") as fh:
                self.assertIn("| escape-dropped | 2 | 1 |", fh.read())


if __name__ == "__main__":
    unittest.main()
