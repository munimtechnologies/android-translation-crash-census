"""Tests for crash_age 0.1.0. Licensed under the Apache License, Version 2.0
(Apache-2.0). Made by MV2 of Munim, Inc. with AI agents."""

import csv
import os
import tempfile
import unittest

import crash_age as ca

O1, O2, O0 = "1" * 40, "2" * 40, "0" * 40


class Classify(unittest.TestCase):
    def test_platforms(self):
        self.assertEqual(ca.classify("Jo <j@x.org> Hosted Weblate <hosted@weblate.org> "
                                     "Translated using Weblate (German)"), "weblate")
        self.assertEqual(ca.classify("Crowdin Bot <support+bot@crowdin.com> GitHub "
                                     "<noreply@github.com> New translations strings.xml (French)"),
                         "crowdin")
        self.assertEqual(ca.classify("Ann <a@b.c> Ann <a@b.c> Merge pull request #3 from "
                                     "org/l10n_master"), "crowdin")
        self.assertEqual(ca.classify("Ann <a@b.c> Ann <a@b.c> Localisation updates from "
                                     "https://translatewiki.net."), "translatewiki")

    def test_bot_and_direct(self):
        self.assertEqual(ca.classify("github-actions[bot] <a@users.noreply.github.com> GitHub "
                                     "<noreply@github.com> Sync strings"), "other bot")
        self.assertEqual(ca.classify("Ann <a@b.c> Ann <a@b.c> Fix French typo"), "direct")


class Timeline(unittest.TestCase):
    def test_runs(self):
        self.assertEqual(ca.timeline([False, True, True]), (1, 1))
        self.assertEqual(ca.timeline([True, False, True, True]), (2, 2))
        self.assertEqual(ca.timeline([True, None, True]), (0, 1))
        self.assertEqual(ca.timeline([True, True, False]), (None, 1))
        self.assertEqual(ca.timeline([None, None]), (None, 0))

    def test_before(self):
        states = [ca.ABSENT, "x", ca.UNREADABLE, "bad"]
        self.assertEqual(ca.before(states, 3), "replaced")
        self.assertEqual(ca.before(states, 1), "new")
        self.assertEqual(ca.before(states, 0), "file start")
        self.assertEqual(ca.before([ca.UNREADABLE, "bad"], 1), "file start")


class Parsing(unittest.TestCase):
    def test_parse_log(self):
        path = "res/values-fr/strings.xml"
        text = "\n".join([
            "@@C\tbbbb\t200\tp1 p2\tA <a@x>\tW <w@weblate.org>\tTranslated using Weblate (French)",
            "",
            ":100644 100644 %s %s M\t%s" % (O1, O2, path),
            "@@C\taaaa\t100\t\tA <a@x>\tA <a@x>\tAdd French",
            "",
            ":000000 100644 %s %s A\t%s" % (O0, O1, path),
            ""])
        self.assertEqual(ca.parse_log(text), {path: [
            (100, "aaaa", False, "A <a@x> A <a@x> Add French", O1),
            (200, "bbbb", True, "A <a@x> W <w@weblate.org> Translated using Weblate (French)", O2)]})

    def test_parse_log_delete(self):
        text = "@@C\tcccc\t300\tp1\tA <a@x>\tA <a@x>\tRemove\n\n:100644 000000 %s %s D\tf.xml\n" % (
            O2, O0)
        self.assertEqual(ca.parse_log(text), {"f.xml": [(300, "cccc", False,
                                                          "A <a@x> A <a@x> Remove", None)]})

    def test_parse_batch(self):
        data = b"aaa blob 3\nxyz\nbbb missing\nccc blob 0\n\n"
        self.assertEqual(ca.parse_batch(data), {"aaa": b"xyz", "ccc": b""})

    def test_decode(self):
        self.assertEqual(ca.decode(b"\xef\xbb\xbfa\r\nb"), "a\nb")

    def test_values(self):
        data = ('<resources><string name="a">50%% de %1$s</string><plurals name="p">'
                '<item quantity="other">%d x</item></plurals></resources>').encode("utf-8")
        got = ca.values(data, ["a", "p[other]", "b"])
        self.assertEqual(got["a"], "50%% de %1$s")
        self.assertEqual(got["p[other]"], "%d x")
        self.assertIs(got["b"], ca.ABSENT)
        self.assertIs(ca.values(b"<resources><string", ["a"]), ca.UNREADABLE)


class DateRow(unittest.TestCase):
    def setUp(self):
        self.versions = [(100, "c1", False, "x Translated using Weblate", O1),
                         (200, "c2", False, "y fix", O2),
                         (300, "c3", False, "z", O1)]

    def pipe(self, version):
        return ca.classify(version[3])

    def test_new(self):
        row = ca.date_row({"translation": "bad"}, self.versions, [ca.ABSENT, "bad", "bad"], False,
                          self.pipe)
        self.assertEqual(row["status"], "dated")
        self.assertEqual(row["intro_commit"], "c2")
        self.assertEqual(row["pipeline"], "direct")
        self.assertEqual(row["before"], "new")
        self.assertEqual(row["episodes"], 1)
        self.assertEqual(row["first_at"], ca.iso(200))
        self.assertEqual(row["age_days"], round((ca.READ_AT.timestamp() - 200) / 86400.0, 1))
        self.assertEqual(row["versions"], 3)

    def test_came_back(self):
        row = ca.date_row({"translation": "bad"}, self.versions, ["bad", "good", "bad"], False,
                          self.pipe)
        self.assertEqual(row["status"], "dated")
        self.assertEqual(row["intro_commit"], "c3")
        self.assertEqual(row["before"], "replaced")
        self.assertEqual(row["episodes"], 2)
        self.assertEqual(row["first_at"], ca.iso(100))

    def test_lower_bound(self):
        row = ca.date_row({"translation": "bad"}, self.versions[:2], ["bad", "bad"], True, self.pipe)
        self.assertEqual(row["status"], "lower bound")
        self.assertEqual(row["before"], "cut")
        self.assertEqual(row["pipeline"], "weblate")
        row = ca.date_row({"translation": "bad"}, self.versions[:2], ["bad", "bad"], False,
                          self.pipe)
        self.assertEqual(row["before"], "file start")

    def test_not_found(self):
        row = ca.date_row({"translation": "bad"}, self.versions[:2], ["bad", ca.ABSENT], False,
                          self.pipe)
        self.assertEqual(row["status"], "not found")
        self.assertNotIn("age_days", row)


def _rows(weblate=6, direct=3):
    rows = []
    for _ in range(weblate):
        rows.append({"verdict": "crash", "status": "dated", "age_days": 400, "pipeline": "weblate",
                     "episodes": 1, "use": "formatted", "intro_at": "2025-09-12T00:00:00Z",
                     "repo": "r1", "before": "new"})
    for _ in range(direct):
        rows.append({"verdict": "crash", "status": "lower bound", "age_days": 800,
                     "pipeline": "direct", "episodes": 2, "use": "unreferenced",
                     "intro_at": "2024-08-08T00:00:00Z", "repo": "r2", "before": "file start"})
    rows.append({"verdict": "crash", "status": "not found", "repo": "r3"})
    for _ in range(5):
        rows.append({"verdict": "crash-if-text", "status": "dated", "age_days": 1, "pipeline": "direct",
                     "episodes": 1, "use": "formatted", "intro_at": "2026-10-16T00:00:00Z",
                     "repo": "r4", "before": "new"})
    return rows


class Scoring(unittest.TestCase):
    def test_all_held(self):
        checks = ca.predictions(_rows())
        self.assertEqual([c["id"] for c in checks], ["A1", "A2", "A3", "A4", "A5", "A6"])
        self.assertEqual([c["held"] for c in checks], [True] * 6)

    def test_tie_fails_a3(self):
        checks = {c["id"]: c["held"] for c in ca.predictions(_rows(weblate=3, direct=3))}
        self.assertFalse(checks["A3"])

    def test_summarize(self):
        s = ca.summarize([r for r in _rows() if r["verdict"] == "crash"])
        self.assertEqual(s["rows"], 10)
        self.assertEqual(s["dated"], 9)
        self.assertEqual(s["age_days"]["median"], 400)
        self.assertEqual(s["age_days_exact_only"]["n"], 6)
        self.assertEqual(s["intro_year"], {"2024": 3, "2025": 6})
        self.assertEqual(s["older_than_2_years"], 3)
        self.assertEqual(s["repo_median_age_days"]["n"], 2)


class LoadRows(unittest.TestCase):
    def test_filters_and_dedupes(self):
        fields = ["verdict", "use", "locale", "key", "file", "repo", "commit", "platform",
                  "translation", "callsite"]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "f.csv")
            with open(path, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=fields)
                w.writeheader()
                base = {"use": "formatted", "locale": "fr", "file": "res/values-fr/strings.xml",
                        "repo": "https://github.com/o/r", "commit": "c", "platform": "weblate",
                        "translation": "x\ny", "callsite": ""}
                w.writerow(dict(base, verdict="crash", key="a"))
                w.writerow(dict(base, verdict="crash", key="a"))
                w.writerow(dict(base, verdict="crash-if-text", key="b"))
                w.writerow(dict(base, verdict="crash-if-int", key="c"))
            rows = ca.load_rows(path)
        self.assertEqual([(r["verdict"], r["key"]) for r in rows], [("crash", "a"),
                                                                    ("crash-if-text", "b")])
        self.assertEqual(rows[0]["translation"], "x\ny")
        self.assertNotIn("callsite", rows[0])


if __name__ == "__main__":
    unittest.main()
