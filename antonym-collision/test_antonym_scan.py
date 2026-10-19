#!/usr/bin/env python3
"""Offline tests for antonym_scan.py. Apache-2.0. Made by MV2 of Munim, Inc. with AI agents."""

import io
import json
import os
import sys
import tarfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import antonym_scan as ac  # noqa: E402

NOCO = ac.PROJECTS[0]
MASTO = ac.PROJECTS[1]


def tarball(files, top="nocobase-10810697"):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path, text in files.items():
            data = text.encode("utf-8")
            info = tarfile.TarInfo(top + "/" + path)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    buf.seek(0)
    return buf


def dumps(d):
    return json.dumps(d, ensure_ascii=False)


class SignatureTest(unittest.TestCase):
    def test_classes_and_polarity(self):
        self.assertEqual(ac.signature("Default expanded"), (("default", "EXPAND"), (0, 1)))
        self.assertEqual(ac.signature("Default collapse"), (("default", "EXPAND"), (0, -1)))
        self.assertEqual(ac.signature("Unblock @{name}"), (("BLOCK", "name"), (-1, 0)))

    def test_no_word_in_two_classes(self):
        words = [w for plus, minus in ac._CLASSES.values() for w in (plus + " " + minus).split()]
        self.assertEqual(len(words), len(set(words)))


class PairsTest(unittest.TestCase):
    def test_pairs(self):
        ref = {"Default expanded": "Default expanded", "Default collapse": "Default collapse",
               "Default collapsed": "Default collapsed", "Show": "Show", "Hide": "Hide",
               "Shown": "Shown", "Plain": "Plain", "Expand all": "Expand all"}
        self.assertEqual(ac.antonym_pairs(ref), [
            ("Default collapse", "Default expanded"), ("Default collapsed", "Default expanded"),
            ("Hide", "Show"), ("Hide", "Shown")])

    def test_two_flips_cancel(self):
        ref = {"a": "Show hidden", "b": "Hide shown", "c": "Show shown"}
        self.assertEqual(ac.antonym_pairs(ref), [("a", "c"), ("b", "c")])

    def test_same_side_inflections_are_not_pairs(self):
        self.assertEqual(ac.antonym_pairs({"a": "Collapse", "b": "Collapsed"}), [])


class ScanDirTest(unittest.TestCase):
    REF = {"Default collapse": "Default collapse", "Default expanded": "Default expanded",
           "Default collapsed": "Default collapsed", "Show": "Show", "Hide": "Hide"}

    def test_kinds(self):
        locales = {
            "de-DE": {"Default collapse": "Standardmäßig eingeklappt",
                      "Default expanded": "Standardmäßig eingeklappt",
                      "Default collapsed": "Default collapsed", "Show": "Anzeigen", "Hide": "Ausblenden"},
            "pt-BR": {"Default collapse": "Default collapse", "Default expanded": "Default collapse"},
            "zh-CN": {"Default collapse": "默认折叠", "Default expanded": "默认展开", "Show": " ", "Hide": "隐藏"},
        }
        pairs, comparisons, rows = ac.scan_dir(self.REF, locales)
        self.assertEqual(pairs, 3)
        # de-DE: 3 pairs; pt-BR: 1 (collapsed missing); zh-CN: 1 (Show blank, collapsed missing).
        self.assertEqual(comparisons, 5)
        self.assertEqual([(r["locale"], r["kind"], r["key1"], r["key2"]) for r in rows], [
            ("de-DE", "flagged", "Default collapse", "Default expanded"),
            ("pt-BR", "copy", "Default collapse", "Default expanded")])
        self.assertEqual(rows[0]["value"], "Standardmäßig eingeklappt")


class TarballTest(unittest.TestCase):
    def test_select_and_scan(self):
        ref = {"Default collapse": "Default collapse", "Default expanded": "Default expanded"}
        files = {
            "packages/core/client/src/locale/en-US.json": dumps(ref),
            "packages/core/client/src/locale/ja-JP.json": dumps(
                {"Default collapse": "デフォルト閉じる", "Default expanded": "デフォルト閉じる"}),
            "packages/core/client/src/locale/zh-CN.json": dumps(
                {"Default collapse": "默认折叠", "Default expanded": "默认展开"}),
            "packages/core/client/src/locale/broken.json": "{not json",
            "packages/core/client/src/locale/cron/ja-JP.json": dumps(ref),
            "packages/core/client/src/locale/index.ts": "export {}",
            "packages/plugins/x/src/locale/zh-CN.json": dumps(ref),
            "locales/en-US.json": dumps({"Show": "Show", "Hide": "Hide"}),
            "locales/fr-FR.json": dumps({"Show": "Afficher", "Hide": "Afficher"}),
            "node_modules/a/locale/en.json": dumps(ref),
        }
        got = ac.read_tarball(tarball(files), NOCO)
        self.assertEqual(sorted(got), sorted(p for p in files if p.endswith(".json")
                                             and "/cron/" not in p and not p.startswith("node_modules")))
        res = ac.scan_project(got)
        self.assertEqual(res["dirs"], 2)  # the plugin dir has no English file
        self.assertEqual(res["locale_files"], 3)
        self.assertEqual(res["unparsed"], ["packages/core/client/src/locale/broken.json"])
        self.assertEqual(res["comparisons"], 3)
        self.assertEqual([(r["dir"], r["locale"]) for r in res["rows"]],
                         [("locales", "fr-FR"), ("packages/core/client/src/locale", "ja-JP")])
        self.assertEqual(res["flagged"], 2)

    def test_mastodon_selection(self):
        self.assertTrue(ac.selected(MASTO, "app/javascript/mastodon/locales/de.json"))
        self.assertFalse(ac.selected(MASTO, "app/javascript/mastodon/locales/sub/de.json"))
        self.assertFalse(ac.selected(MASTO, "config/locales/de.json"))
        self.assertFalse(ac.selected(MASTO, "app/javascript/mastodon/locales/index.js"))

    def test_non_object_and_nested(self):
        self.assertIsNone(ac.load(b"[1, 2]"))
        self.assertEqual(ac.load('﻿{"a": {"b": "x", "c": 1}, "d": "y"}'.encode("utf-8")),
                         {"a.b": "x", "d": "y"})


def a1_rows(values=None, copies=ac.A1_COPY):
    values = dict(ac.EXPECTED_VALUES) if values is None else values
    rows = [{"dir": ac.A1_DIR, "locale": loc, "kind": "flagged", "key1": ac.A1_PAIR[0],
             "key2": ac.A1_PAIR[1], "value": v} for loc, v in values.items()]
    rows += [{"dir": ac.A1_DIR, "locale": loc, "kind": "copy", "key1": ac.A1_PAIR[0],
              "key2": ac.A1_PAIR[1], "value": "Default collapse"} for loc in copies]
    return rows


def other_rows(n):
    return [{"dir": "packages/plugins/p%d/src/locale" % i, "locale": "de-DE", "kind": "flagged",
             "key1": "Hide", "key2": "Show", "value": "x"} for i in range(n)]


class GradeTest(unittest.TestCase):
    def results(self, rows, comparisons=2000, m_flagged=1, m_comparisons=4000, files=(150, 90)):
        flagged = sum(1 for r in rows if r["kind"] == "flagged")
        return {"nocobase": {"locale_files": files[0], "rows": rows, "flagged": flagged,
                             "comparisons": comparisons},
                "mastodon": {"locale_files": files[1], "rows": [], "flagged": m_flagged,
                             "comparisons": m_comparisons}}

    def held(self, results):
        return {c[0]: c[2] for c in ac.grade(results)}

    def test_all_hold(self):
        self.assertEqual(self.held(self.results(a1_rows() + other_rows(10))),
                         {"A0": True, "A1": True, "A2": True, "A3": True, "A4": True})

    def test_failures(self):
        values = dict(ac.EXPECTED_VALUES)
        values["de-DE"] = "Standardmäßig ausgeklappt"
        del values["zh-TW"]
        h = self.held(self.results(a1_rows(values, copies=["pt-BR"]) + other_rows(9), files=(99, 90)))
        self.assertEqual(h, {"A0": False, "A1": False, "A2": False, "A3": False, "A4": True})

    def test_nfc_only_difference_holds(self):
        values = dict(ac.EXPECTED_VALUES)
        values["vi-VN"] = __import__("unicodedata").normalize("NFD", values["vi-VN"])
        checks = {c[0]: c for c in ac.grade(self.results(a1_rows(values) + other_rows(10)))}
        self.assertTrue(checks["A2"][2])
        self.assertIn("vi-VN", checks["A2"][3])

    def test_a4(self):
        rows = a1_rows() + other_rows(10)  # 23 flagged in 2000 = 11.5 per 1,000
        self.assertTrue(self.held(self.results(rows, m_flagged=0))["A4"])
        self.assertFalse(self.held(self.results(rows, m_flagged=0, m_comparisons=499))["A4"])
        self.assertTrue(self.held(self.results(rows, m_flagged=9))["A4"])    # 2.25 per 1,000
        self.assertFalse(self.held(self.results(rows, m_flagged=10))["A4"])  # 2.5 per 1,000

    def test_download_error(self):
        r = self.results(a1_rows() + other_rows(10))
        r["mastodon"] = {"error": "URLError: down"}
        h = self.held(r)
        self.assertFalse(h["A0"])
        self.assertFalse(h["A4"])


class ZeroWidthTest(unittest.TestCase):
    def test_count(self):
        import zw_count
        text = "﻿\"a\": \"お待​​ちください\",\n\"b\": \"x​y\",\nc=待\\u200bつ\n"
        total, inside, samples = zw_count.count(text)
        self.assertEqual(total, 4)   # the leading BOM is not counted; the escape is
        self.assertEqual(inside, 2)  # one run of two, one escaped
        self.assertEqual([s["line"] for s in samples], [1, 3])
        self.assertIn("お待<U+200B><U+200B>ち", samples[0]["text"])


if __name__ == "__main__":
    unittest.main()
