# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in the name of MV2 of Munim, Inc.
import os
import shutil
import tempfile
import unittest

import linguas_history as lh


def sh(repo, *args):
    return lh.git(list(args), repo)


def write(repo, rel, text):
    p = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def commit(repo, msg):
    sh(repo, "add", "-A")
    sh(repo, "commit", "-q", "-m", msg)
    return sh(repo, "rev-parse", "HEAD").stdout.strip()


def v(sha, langs, subject="x", present=True):
    return {"sha": sha, "time": 1, "subject": subject, "langs": langs, "file_present": present}


class ParseTests(unittest.TestCase):
    def test_parse_comments_and_spacing(self):
        self.assertEqual(lh.parse_linguas("de\nfr # french\n# es\n  it  pt_BR\n\n"),
                         ["de", "fr", "it", "pt_BR"])

    def test_classify_never_listed_nohistory(self):
        vs = [v("a", ["de"]), v("b", ["de", "fr"])]
        self.assertEqual(lh.classify("tr", vs)["class"], "never")
        self.assertEqual(lh.classify("fr", vs)["class"], "listed")
        self.assertEqual(lh.classify("tr", [])["class"], "no-history")

    def test_classify_lost_replace(self):
        vs = [v("a", ["es", "tr"], "Add tr"),
              v("b", ["es", "it"], "Add Italian Translation"),
              v("c", ["es", "it", "th_TH"], "Add th")]
        info = lh.classify("tr", vs)
        self.assertEqual(info["class"], "lost")
        self.assertEqual(info["listed_sha"], "a")
        self.assertEqual(info["removed_sha"], "b")
        self.assertEqual(info["added_same"], ["it"])
        self.assertEqual(info["also_removed"], [])
        self.assertEqual(info["listed_runs"], 1)
        self.assertEqual(lh.simple_kind(info["removed_subject"], vs[0]["langs"], vs[1]["langs"],
                                        True, "tr", 1), "replace")

    def test_classify_relisted_then_lost(self):
        vs = [v("a", ["tr"]), v("b", []), v("c", ["tr"]), v("d", ["de"])]
        info = lh.classify("tr", vs)
        self.assertEqual(info["listed_sha"], "a")
        self.assertEqual(info["removed_sha"], "d")
        self.assertEqual(info["listed_runs"], 2)

    def test_simple_kind_order(self):
        self.assertEqual(lh.simple_kind("Remove incomplete translations", ["a", "b"], ["a", "c"],
                                        True, "b", 1), "subject-removal")
        self.assertEqual(lh.simple_kind("Dropped ru", ["a", "b"], ["a"], True, "b", 1),
                         "subject-removal")
        self.assertEqual(lh.simple_kind("Update", ["a", "b", "c", "d"], ["a"], True, "b", 1), "bulk")
        self.assertEqual(lh.simple_kind("Update", ["a", "b"], ["a"], True, "b", 1), "other")
        self.assertEqual(lh.simple_kind("Update", ["a", "b"], [], False, "b", 1), "file-deleted")
        self.assertEqual(lh.simple_kind("Update", ["a", "b"], ["a"], True, "b", 2), "merge-resolution")

    def test_commit_url(self):
        self.assertEqual(lh.commit_url("https://github.com/o/r", "abc"), "https://github.com/o/r/commit/abc")
        self.assertEqual(lh.commit_url("https://gitlab.com/o/r", "abc"), "https://gitlab.com/o/r/-/commit/abc")
        self.assertEqual(lh.commit_url("https://github.com/o/r", ""), "")


class GitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = os.path.join(self.tmp, "r")
        os.makedirs(self.repo)
        sh(self.repo, "init", "-q", "-b", "main")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_merge_resolution_loss(self):
        r = self.repo
        write(r, "po/LINGUAS", "de\n")
        write(r, "po/tr.po", "x\n")
        c1 = commit(r, "init")
        write(r, "po/LINGUAS", "de\ntr\n")
        c2 = commit(r, "Add Turkish")
        sh(r, "checkout", "-q", "-b", "feature")
        write(r, "po/LINGUAS", "de\ntr\nuk\n")
        commit(r, "Add uk")
        sh(r, "checkout", "-q", "main")
        write(r, "po/LINGUAS", "de\ntr\nfr\n")
        c3 = commit(r, "Add fr")
        lh.git(["merge", "-q", "--no-ff", "feature"], r, check=False)  # conflicts on purpose
        write(r, "po/LINGUAS", "de\nfr\nuk\n")
        m = commit(r, "Merge branch 'feature'")
        self.assertEqual(len(lh.parents(r, m)), 2)
        vers = lh.linguas_versions(r, "HEAD", "po/LINGUAS")
        self.assertEqual([x["sha"] for x in vers], [c1, c2, c3, m])
        info = lh.classify("tr", vers)
        self.assertEqual(info["class"], "lost")
        self.assertEqual(info["listed_sha"], c2)
        self.assertEqual(info["removed_sha"], m)
        ex = lh.explain_removal(r, "tr", info, "po/LINGUAS", {})
        self.assertEqual(ex["kind"], "merge-resolution")
        self.assertEqual(ex["kind_sha"], m)
        self.assertEqual(lh.po_added(r, "HEAD", "po/tr.po")[0], c1)

    def test_branch_replace_loss(self):
        r = self.repo
        write(r, "po/LINGUAS", "de\ntr\n")
        write(r, "po/tr.po", "x\n")
        c1 = commit(r, "init")
        sh(r, "checkout", "-q", "-b", "feature")
        write(r, "po/LINGUAS", "de\nit\n")
        b1 = commit(r, "Add Italian translation")
        sh(r, "checkout", "-q", "main")
        write(r, "README", "x\n")
        commit(r, "docs")
        sh(r, "merge", "-q", "--no-ff", "-m", "Merge pull request #2", "feature")
        m = sh(r, "rev-parse", "HEAD").stdout.strip()
        vers = lh.linguas_versions(r, "HEAD", "po/LINGUAS")
        self.assertEqual([x["sha"] for x in vers], [c1, m])
        info = lh.classify("tr", vers)
        self.assertEqual(info["removed_sha"], m)
        ex = lh.explain_removal(r, "tr", info, "po/LINGUAS", {})
        self.assertEqual(ex["kind"], "branch:replace")
        self.assertEqual(ex["kind_sha"], b1)

    def test_never_listed_and_direct_removal(self):
        r = self.repo
        write(r, "po/LINGUAS", "de\nfr\nru\n")
        write(r, "po/tr.po", "x\n")
        commit(r, "init")
        write(r, "po/LINGUAS", "de\n")
        c2 = commit(r, "Remove outdated translations")
        vers = lh.linguas_versions(r, "HEAD", "po/LINGUAS")
        self.assertEqual(lh.classify("tr", vers)["class"], "never")
        info = lh.classify("fr", vers)
        self.assertEqual(info["removed_sha"], c2)
        self.assertEqual(info["also_removed"], ["ru"])
        ex = lh.explain_removal(r, "fr", info, "po/LINGUAS", {})
        self.assertEqual(ex["kind"], "subject-removal")


class GradeTests(unittest.TestCase):
    def row(self, repo, cls, sub="yes", sha="", kind=""):
        return {"repo": repo, "dir": "po", "stem": "x", "substantive": sub, "class": cls,
                "removed_sha": sha, "kind": kind}

    def test_grade(self):
        rows = [self.row("r%d" % i, "never") for i in range(45)]
        rows += [self.row("r0", "never") for _ in range(56)]
        rows += [self.row("r1", "lost", sha="s1", kind="replace"),
                 self.row("r1", "lost", sha="s1", kind="replace"),
                 self.row("r2", "lost", sha="s2", kind="subject-removal"),
                 self.row("r3", "lost", sub="no", sha="s3", kind="merge-resolution")]
        rows += [self.row("r4", "error") for _ in range(5)]
        g = lh.grade(rows)
        self.assertEqual(g["gate"]["repos_analysed"], 45)
        self.assertEqual(g["gate"]["rows_classified"], 105)
        self.assertEqual(g["gate"]["verdict"], "HOLDS")
        self.assertEqual(g["P1"]["substantive_rows"], 104)
        self.assertEqual(g["P1"]["lost"], 3)
        self.assertEqual(g["P1"]["verdict"], "FAILS")
        self.assertEqual(g["P2"]["events"], 3)
        self.assertEqual(g["P2"]["collateral"], 2)
        self.assertEqual(g["P2"]["verdict"], "HOLDS")
        self.assertEqual(g["P3"]["deliberate"], 1)
        self.assertEqual(g["P3"]["verdict"], "HOLDS")
        self.assertEqual(g["H"]["events_to_check"], 3)

    def test_grade_empty_not_testable(self):
        g = lh.grade([self.row("r0", "error")])
        self.assertEqual(g["gate"]["verdict"], "FAILS")
        self.assertEqual(g["P1"]["verdict"], "NOT TESTABLE")
        self.assertEqual(g["P2"]["verdict"], "NOT TESTABLE")

    def test_hand_sample(self):
        ev = [{"removed_sha": "%02d" % i} for i in range(20, 0, -1)]
        s = lh.hand_sample(ev)
        self.assertEqual(len(s), 12)
        self.assertEqual(s[0]["removed_sha"], "01")
        self.assertEqual(len(lh.hand_sample(ev[:15])), 15)


if __name__ == "__main__":
    unittest.main()
