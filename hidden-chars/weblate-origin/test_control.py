# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for control.py (no network, no git)."""
import unittest

import control as ct
import zwsp_origin as zo


def commit(sha, message="Update", email="dev@example.org", date="2025-01-02T03:04:05+00:00"):
    return zo.Commit(sha, [], email, email, date, message)


class PlatformTest(unittest.TestCase):
    def test_named_platform(self):
        self.assertEqual(ct.named_platform("Translated using Weblate (Dutch)"), "weblate")
        self.assertEqual(ct.named_platform("- quality suggestions from weblate"), "weblate")
        self.assertEqual(ct.named_platform("Sync Strings from Localazy (#5904)"), "localazy")
        self.assertEqual(ct.named_platform("Sync Strings (#6921)\n\nStrings pulled from Localazy."), "localazy")
        self.assertEqual(ct.named_platform("New translations strings.xml (Belarusian)"), "crowdin")
        self.assertEqual(ct.named_platform("New Crowdin updates (#231)"), "crowdin")
        self.assertEqual(ct.named_platform("from Transifex"), "transifex")
        self.assertEqual(ct.named_platform("Add new transifex translations"), "transifex")
        self.assertEqual(ct.named_platform("Added initial support for 9 new languages"), "")
        self.assertEqual(ct.named_platform("Add new translations"), "")
        self.assertEqual(ct.named_platform(""), "")


class CountTest(unittest.TestCase):
    log = [
        commit("c5", "Translated using Weblate (Dutch)", date="2026-03-01T00:00:00+00:00"),
        commit("c4", "Fix typo"),
        commit("c3", "Update", email="noreply@weblate.org", date="2025-06-01T00:00:00+00:00"),
        commit("c2", "Add Dutch"),
        commit("c1", "x\nTranslate-URL: https://translate.example.org/p/c/nl/", date="2024-01-01T00:00:00+00:00"),
    ]

    def test_weblate_after(self):
        self.assertEqual(ct.weblate_after(self.log, "c2"), 2)  # c5 and c3
        self.assertEqual(ct.weblate_after(self.log, "c5"), 0)
        self.assertEqual(ct.weblate_after(self.log, "c4"), 1)
        self.assertIsNone(ct.weblate_after(self.log, "zz"))

    def test_weblate_stats(self):
        n, first, last, hosts = ct.weblate_stats(self.log)
        self.assertEqual(n, 3)
        self.assertEqual(first, "2024-01-01")
        self.assertEqual(last, "2026-03-01")
        self.assertEqual(hosts, ["translate.example.org"])
        self.assertEqual(ct.weblate_stats([]), (0, "", "", []))

    def test_summarize(self):
        repos = [{"repo": "a", "status": "ok", "weblate_total": 3},
                 {"repo": "b", "status": "ok", "weblate_total": 0},
                 {"repo": "c", "status": "clone-failed"}]
        rows = [
            {"repo": "a", "status": "attributed", "weblate_in_folder": 2, "weblate_after_intro": 1, "platform_named": ""},
            {"repo": "a", "status": "attributed", "weblate_in_folder": 2, "weblate_after_intro": 0,
             "platform_named": "localazy"},
            {"repo": "b", "status": "attributed", "weblate_in_folder": 0, "weblate_after_intro": 0,
             "platform_named": "crowdin"},
            {"repo": "b", "status": "unattributed", "weblate_in_folder": 0, "weblate_after_intro": "",
             "platform_named": ""},
        ]
        s = ct.summarize(repos, rows)
        self.assertEqual(s["repos_with_weblate_commits"], 1)
        self.assertEqual(s["weblate_commits_total"], 3)
        self.assertEqual(s["rows_folder_has_weblate_commits"], 2)
        self.assertEqual(s["rows_weblate_after_intro"], 1)
        self.assertEqual(s["repos_weblate_after_intro"], 1)
        self.assertEqual(s["platform_named"], {"none": 1, "localazy": 1, "crowdin": 1})
        self.assertEqual(s["row_status_counts"], {"attributed": 3, "unattributed": 1})
        self.assertEqual(s["repo_status_counts"], {"ok": 2, "clone-failed": 1})


if __name__ == "__main__":
    unittest.main()
