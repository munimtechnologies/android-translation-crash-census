# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made by MV2 of Munim, Inc. with AI agents.
import json
import unittest
import xml.etree.ElementTree as ET

import slint_blind as sb


def row(app, kind, use="formatted", pofilter="flagged", weblate="flagged", lint="flagged", src="%1$s", tr="%1$d"):
    return dict(app=app, repo="r/" + app, locale="xx", key="k", use=use, exception="E", kind=kind,
                weblate=weblate, pofilter=pofilter, lint=lint, source=src, translation=tr)


class Finding:
    def __init__(self, rule):
        self.rule = rule


class TestHelpers(unittest.TestCase):
    def test_po_quote_round_trip(self):
        for s in ['a "b" %1$s', "back\\slash %1\\$s", "two\nlines\tand tab"]:
            q = sb.po_quote(s)
            self.assertTrue(q.startswith('"') and q.endswith('"'))
            self.assertNotIn("\n", q)
            self.assertEqual(q[1:-1].encode().decode("unicode_escape"), s)

    def test_po_entry_shape(self):
        self.assertEqual(sb.po_entry("%s", "%d"), 'msgid "%s"\nmsgstr "%d"\n')

    def test_xliff_doc_parses_and_keeps_text(self):
        doc = sb.xliff_doc([("a <b> & %1$s", "c %1$d"), ("x", "y")])
        root = ET.fromstring(doc.encode("utf-8"))
        units = root.findall(".//trans-unit")
        self.assertEqual(len(units), 2)
        self.assertEqual(units[0].find("source").text, "a <b> & %1$s")
        self.assertEqual(units[0].find("target").text, "c %1$d")

    def test_android_xml_parses(self):
        root = ET.fromstring(sb.android_xml([(n, t) for n, _, t in sb.ANDROID_PAIRS]).encode("utf-8"))
        self.assertEqual([e.get("name") for e in root], [n for n, _, _ in sb.ANDROID_PAIRS])
        self.assertEqual(root[1].text, "%1$d% hecho")

    def test_is_flagged(self):
        self.assertTrue(sb.is_flagged(["FORMAT_SPECIFIER_DRIFT"]))
        self.assertTrue(sb.is_flagged(["XSS_PAYLOAD", "INTERPOLATION_DRIFT"]))
        self.assertFalse(sb.is_flagged(["BIDI_OVERRIDE"]))
        self.assertFalse(sb.is_flagged([]))

    def test_api_rules(self):
        fake = lambda s, t: [Finding("FORMAT_SPECIFIER_DRIFT"), Finding("FORMAT_SPECIFIER_DRIFT")] if s != t else []
        self.assertEqual(sb.api_rules(fake, "%s", "%d"), ["FORMAT_SPECIFIER_DRIFT"])
        self.assertEqual(sb.api_rules(fake, "%s", "%s"), [])

    def test_cli_rules(self):
        parsed = {"f.po": {"3": [{"rule": "FORMAT_SPECIFIER_DRIFT"}, {"rule": "INTERPOLATION_DRIFT"}]}}
        self.assertEqual(sb.cli_rules(parsed), ["FORMAT_SPECIFIER_DRIFT", "INTERPOLATION_DRIFT"])
        self.assertEqual(sb.cli_rules({}), [])
        self.assertEqual(sb.cli_rules(None), [])

    def test_run_cli(self):
        def fake_main(argv):
            print("noise " + json.dumps({"f": {"1": [{"rule": "X_DRIFT"}]}}))
            return 1 if "--strict" in argv else 0
        self.assertEqual(sb.run_cli(fake_main, ["--json", "f"]), (0, {"f": {"1": [{"rule": "X_DRIFT"}]}}, ""))
        self.assertEqual(sb.run_cli(fake_main, ["--strict", "f"]), (1, None, ""))

        def boom(argv):
            raise ValueError("bad")
        rc, parsed, err = sb.run_cli(boom, ["--json", "f"])
        self.assertEqual((rc, parsed), (None, None))
        self.assertIn("ValueError", err)

        def exits(argv):
            raise SystemExit(2)
        self.assertEqual(sb.run_cli(exits, ["--strict", "f"])[0], 2)


class TestSummary(unittest.TestCase):
    def setUp(self):
        self.rows = [row("a", "stray-percent"),
                     row("b", "stray-percent", weblate="unflagged", pofilter="unflagged", lint="not-visited"),
                     row("c", "wrong-type", use="referenced", pofilter="unflagged"),
                     row("d", "wrong-type", weblate="unflagged", pofilter="unflagged", lint="ignored")]
        self.api = [["FORMAT_SPECIFIER_DRIFT"], [], [], ["INTERPOLATION_DRIFT"]]
        self.po = [["FORMAT_SPECIFIER_DRIFT"], [], None, []]

    def test_groups(self):
        out, groups = sb.summarise(self.rows, self.api, self.po)
        g = groups["all-crash"]
        self.assertEqual(g["rows"], 4)
        self.assertEqual(g["slint_api"], {"flagged": 2, "unflagged": 2})
        self.assertEqual(g["slint_po"], {"flagged": 1, "unflagged": 2, "error": 1})
        self.assertEqual(g["none_of_three"], 2)
        self.assertEqual(g["slint_only"], 1)
        self.assertEqual(g["none_of_four"], 1)
        self.assertEqual(g["by_kind"]["wrong-type"], {"rows": 2, "slint_flagged": 1, "pofilter_flagged": 0})
        self.assertEqual(groups["formatted-crash"]["rows"], 3)
        self.assertEqual(out[2]["slint_po"], "error")
        self.assertEqual(out[0]["others_seen_by"], "weblate pofilter lint")
        self.assertEqual(set(out[0]), set(sb.FIELDS))

    def test_predictions(self):
        out, groups = sb.summarise(self.rows, self.api, self.po)
        android = {"x": {"findings": 0, "strict_rc": 0, "error": ""}}
        preds, flagged, agree = sb.predictions(groups, out, android, 0)
        held = {p: ok for p, _, ok in preds}
        self.assertTrue(held["P1"])
        self.assertTrue(held["P2"])
        self.assertFalse(held["P3"])   # none_of_three is 2 here, not 12, and one is flagged
        self.assertTrue(held["P4"])
        self.assertFalse(held["P5"])   # only 2 of 4 agree
        self.assertEqual((flagged, agree), (2, 2))
        android["x"]["strict_rc"] = 1
        self.assertFalse({p: ok for p, _, ok in sb.predictions(groups, out, android, 0)[0]}["P1"])

    def test_report_renders(self):
        out, groups = sb.summarise(self.rows, self.api, self.po)
        android = {"x": {"findings": 0, "strict_rc": 0, "error": ""}}
        preds, _, _ = sb.predictions(groups, out, android, 0)
        meta = {"slint_version": "0.2.1", "rows_commit": "abc", "rows": 4}
        text = sb.report(meta, groups, preds, android, 0, [e for e in out if e["slint_api"] != "flagged"])
        self.assertIn("P3 FAILED", text)
        self.assertIn("| wrong-type | 2 | 1 | 0 |", text)


if __name__ == "__main__":
    unittest.main()
