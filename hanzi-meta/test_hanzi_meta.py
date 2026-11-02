# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Tests for hanzi_meta.py (standard library only; needs hanzi_leak.py next to it)."""
import os
import shutil
import tempfile
import unittest

import hanzi_meta as hm

S = set("这设发说个们")
T = set("這設發說個們")


def write(root, rel, text, raw=None):
    p = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(raw if raw is not None else text.encode("utf-8"))


class LocaleTest(unittest.TestCase):
    def test_groups(self):
        cases = {"zh-TW": "hant", "zh_HK": "hant", "zh-MO": "hant", "zh-Hant": "hant",
                 "zh-Hant-TW": "hant", "ZH-tw": "hant", "zh-CN": "hans", "zh_SG": "hans",
                 "zh-Hans": "hans", "zh-Hans-TW": "hans", "zh": None, "zh-US": None,
                 "ja-JP": None, "en-US": None, "zh-rTW": None}
        for name, want in cases.items():
            self.assertEqual(hm.locale_group(name), want, name)

    def test_roots(self):
        yes = ["fastlane/metadata/android", "app/fastlane/metadata/android",
               "app/src/main/play/listings", "play/release-notes", "metadata"]
        no = ["app/metadata", "xfastlane/metadata/android", "fastlane/metadata",
              "fastlane/metadata/android/zh-TW", "play"]
        for r in yes:
            self.assertTrue(hm.is_root(r), r)
        for r in no:
            self.assertFalse(hm.is_root(r), r)

    def test_kinds(self):
        root = "fastlane/metadata/android"
        self.assertEqual(hm.file_kind(root, "title.txt"), "title")
        self.assertEqual(hm.file_kind(root, "short_description.txt"), "short_description")
        self.assertEqual(hm.file_kind("play/listings", "full-description.txt"), "full_description")
        self.assertEqual(hm.file_kind(root, "changelogs/1042.txt"), "changelog")
        self.assertEqual(hm.file_kind("app/src/main/play/release-notes", "default.txt"),
                         "changelog")
        self.assertEqual(hm.file_kind(root, "video.txt"), "other")


class ScanTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        f = "fastlane/metadata/android/"
        write(self.d, f + "en-US/full_description.txt", "Hello 这\nSecond line\n")
        write(self.d, f + "en-US/title.txt", "App\n")
        # zh-TW: line 1 has only 这 (in the source) -> not flagged; line 2 flagged (设);
        # line 3 clean Traditional; line 4 English only (not a unit); blank lines skipped.
        write(self.d, f + "zh-TW/full_description.txt",
              "你好 这\n设置\n\n設定\nEnglish only\n")
        write(self.d, f + "zh-TW/title.txt", "说明\n")
        write(self.d, f + "zh-TW/changelogs/7.txt", "修正 个 问题\n")
        write(self.d, f + "zh-HK/title.txt", "說明\n")
        write(self.d, f + "zh-CN/title.txt", "说明\n")
        write(self.d, f + "zh-CN/full_description.txt", "设置\n設定\n")
        write(self.d, f + "zh/title.txt", "说明\n")          # plain zh: not read
        write(self.d, f + "ja-JP/title.txt", "说明\n")       # not Chinese folder
        write(self.d, f + "zh-Hant/bad.txt", "", raw=b"\xff\xfe" + "们".encode("utf-8"))
        write(self.d, "app/src/main/play/release-notes/zh-TW/default.txt", "发布\n")
        write(self.d, "app/metadata/zh-TW/title.txt", "这\n")  # not a root
        self.r = hm.scan_checkout(self.d, S, T)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_counts(self):
        r = self.r
        self.assertEqual(r["roots"], 2)
        # hant units: full_description 3 (你好 这, 设置, 設定), title 1, changelog 1, zh-HK title 1,
        # zh-Hant bad 1, release-notes 1 = 8.
        self.assertEqual(r["units"]["hant"], 8)
        # flagged: 设置, 说明 (title), 修正 个 问题, 们 (bad), 发布 = 5.
        self.assertEqual(r["flagged"]["hant"], 5)
        # hans: zh-CN title 说明 (no T), full_description 设置 / 設定 -> 設定 flagged.
        self.assertEqual(r["units"]["hans"], 3)
        self.assertEqual(r["flagged"]["hans"], 1)
        self.assertEqual(r["bad_files"], 1)

    def test_rows(self):
        hant = sorted((x["path"], x["line"]) for x in self.r["rows"] if x["group"] == "hant")
        self.assertEqual(hant, [
            ("app/src/main/play/release-notes/zh-TW/default.txt", 1),
            ("fastlane/metadata/android/zh-Hant/bad.txt", 1),
            ("fastlane/metadata/android/zh-TW/changelogs/7.txt", 1),
            ("fastlane/metadata/android/zh-TW/full_description.txt", 2),
            ("fastlane/metadata/android/zh-TW/title.txt", 1),
        ])
        by = {x["path"]: x for x in self.r["rows"] if x["group"] == "hant"}
        fd = by["fastlane/metadata/android/zh-TW/full_description.txt"]
        self.assertEqual(fd["chars"], "设")
        self.assertTrue(fd["available"])
        self.assertTrue(fd["identical"])
        self.assertEqual(fd["other_dir"], "zh-CN")
        self.assertEqual(fd["kind"], "full_description")
        ch = by["fastlane/metadata/android/zh-TW/changelogs/7.txt"]
        self.assertEqual(ch["kind"], "changelog")
        self.assertFalse(ch["available"])
        self.assertEqual(ch["other_dir"], "")
        rn = by["app/src/main/play/release-notes/zh-TW/default.txt"]
        self.assertEqual(rn["kind"], "changelog")
        self.assertEqual(rn["chars"], "发")
        title = by["fastlane/metadata/android/zh-TW/title.txt"]
        self.assertTrue(title["identical"])

    def test_kind_counts(self):
        self.assertEqual(self.r["kind_units"]["hant:full_description"], 3)
        self.assertEqual(self.r["kind_flagged"]["hant:changelog"], 2)
        self.assertEqual(self.r["kind_flagged"]["hant:title"], 1)
        self.assertEqual(self.r["kind_flagged"]["hant:other"], 1)


class SampleTest(unittest.TestCase):
    def rows(self, repos, per):
        return [{"group": "hant", "repo": "r%03d" % i, "path": "p", "line": j}
                for i in range(repos) for j in range(per)]

    def test_cap_per_repo_and_size(self):
        s = hm.draw_sample(self.rows(50, 5))
        self.assertEqual(len(s), 60)
        counts = {}
        for x in s:
            counts[x["repo"]] = counts.get(x["repo"], 0) + 1
        self.assertLessEqual(max(counts.values()), 2)

    def test_small_and_deterministic(self):
        rows = self.rows(7, 3) + [{"group": "hans", "repo": "x", "path": "p", "line": 1}]
        a = hm.draw_sample(rows)
        b = hm.draw_sample(list(reversed(rows)))
        self.assertEqual(len(a), 14)
        self.assertEqual(a, b)
        self.assertTrue(all(x["group"] == "hant" for x in a))


class GradeTest(unittest.TestCase):
    def test_m1(self):
        self.assertEqual(hm.grade_m1(["defect"] * 16 + ["deliberate"] * 4), "HELD")
        self.assertEqual(hm.grade_m1(["defect"] * 15 + ["regional"] * 5), "FAILED")
        self.assertEqual(hm.grade_m1(["defect"] * 19), "NOT TESTABLE")
        self.assertEqual(hm.grade_m1(["defect"] * 48 + ["name_or_quote"] * 12), "HELD")
        self.assertEqual(hm.grade_m1(["defect"] * 47 + ["name_or_quote"] * 13), "FAILED")

    def test_m2(self):
        self.assertEqual(hm.grade_m2(50, 2000, 5), "HELD")
        self.assertEqual(hm.grade_m2(50, 2000, 4), "FAILED")
        self.assertEqual(hm.grade_m2(49, 5000, 40), "NOT TESTABLE (gate)")
        self.assertEqual(hm.grade_m2(80, 1999, 40), "NOT TESTABLE (gate)")

    def test_m3(self):
        listing = {"a%d" % i: (10, 1 if i < 4 else 0) for i in range(10)}
        listing.update({"b%d" % i: (10, 1 if i < 2 else 0) for i in range(10)})
        listing["c"] = (0, 0)          # no listing units: not counted
        listing["d"] = (5, 1)          # not in strings: not counted
        strings = {"a%d" % i: (100, 3) for i in range(10)}
        strings.update({"b%d" % i: (100, 0) for i in range(10)})
        strings["c"] = (100, 3)
        t = hm.m3_table(listing, strings)
        self.assertEqual(t["strings_flagged"], {"repos": 10, "listing_flagged": 4})
        self.assertEqual(t["strings_clean"], {"repos": 10, "listing_flagged": 2})
        self.assertEqual(hm.grade_m3(t), "HELD")
        t2 = {"strings_flagged": {"repos": 10, "listing_flagged": 2},
              "strings_clean": {"repos": 20, "listing_flagged": 4}}
        self.assertEqual(hm.grade_m3(t2), "FAILED")    # equal shares do not hold
        t3 = {"strings_flagged": {"repos": 9, "listing_flagged": 9},
              "strings_clean": {"repos": 20, "listing_flagged": 0}}
        self.assertEqual(hm.grade_m3(t3), "NOT TESTABLE")

    def test_control(self):
        self.assertTrue(hm.control(S, T))
        self.assertFalse(hm.control(set(), T))


if __name__ == "__main__":
    unittest.main()
