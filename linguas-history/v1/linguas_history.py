#!/usr/bin/env python3
# Copyright 2026 Munim, Inc.
# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in the name of MV2 of Munim, Inc.
"""linguas-history v1 (pre-registered in PREREG.md before any repository is read).

For every translated .po file that its folder's LINGUAS leaves out (the 120 rows of
linguas-census-v1 out/dropped.csv), walk the main line (first parents) of that LINGUAS
file up to the census commit and ask: was this language ever listed, and if it was,
which commit dropped it and how (merge resolution, replaced by another language,
a commit that says it removes, ...)?

Usage: python linguas_history.py <dropped.csv> <out_dir>
"""
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter

GIT_ENV = dict(os.environ)
GIT_ENV.update({
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_AUTHOR_NAME": "linguas-history",
    "GIT_AUTHOR_EMAIL": "census@example.invalid",
    "GIT_COMMITTER_NAME": "linguas-history",
    "GIT_COMMITTER_EMAIL": "census@example.invalid",
    "LC_ALL": "C",
})

REMOVAL_WORDS = re.compile(
    r"\b(remov\w*|drop\w*|disabl\w*|delet\w*|exclud\w*|revert\w*|incomplete|unmaintained|outdated)\b",
    re.I)

# Kinds that look like an accident: the language disappeared while something else was done.
COLLATERAL = {"merge-resolution", "replace", "branch:merge-resolution", "branch:replace"}
# Kinds where the commit subject says it removes something.
DELIBERATE = {"subject-removal", "branch:subject-removal"}


class GitError(Exception):
    pass


def git(args, cwd, timeout=900, check=True):
    r = subprocess.run(["git"] + list(args), cwd=cwd, env=GIT_ENV, capture_output=True,
                       timeout=timeout, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise GitError("git %s: %s" % (" ".join(list(args)[:2]), r.stderr.strip()[:300]))
    return r


def parse_linguas(text):
    """Language codes as Meson and gettext read LINGUAS: whitespace-separated, '#' starts a comment."""
    langs = []
    for line in text.splitlines():
        langs.extend(line.split("#", 1)[0].split())
    return langs


def lang_at(repo, rev, path, cache):
    """(file_present, langs) of path at rev."""
    key = (rev, path)
    if key not in cache:
        r = git(["show", "%s:%s" % (rev, path)], repo, check=False)
        cache[key] = (r.returncode == 0, parse_linguas(r.stdout) if r.returncode == 0 else [])
    return cache[key]


def parents(repo, sha):
    return git(["rev-list", "--parents", "-n", "1", sha], repo).stdout.split()[1:]


def linguas_versions(repo, rev, path, cache=None):
    """Every first-parent commit up to rev that changed path, oldest first, with its parsed LINGUAS."""
    cache = {} if cache is None else cache
    out = git(["log", "--first-parent", "--format=%H%x09%ct%x09%s", rev, "--", path], repo).stdout
    versions = []
    for line in out.splitlines():
        if not line.strip():
            continue
        sha, ct, subject = (line.split("\t", 2) + ["", ""])[:3]
        versions.append({"sha": sha, "time": int(ct or 0), "subject": subject})
    versions.reverse()
    for v in versions:
        v["file_present"], v["langs"] = lang_at(repo, v["sha"], path, cache)
    return versions


def count_runs(flags):
    n, prev = 0, False
    for f in flags:
        if f and not prev:
            n += 1
        prev = f
    return n


def classify(stem, versions):
    """never / lost / listed / no-history for one language over the main-line versions."""
    if not versions:
        return {"class": "no-history"}
    present = [stem in v["langs"] for v in versions]
    if present[-1]:
        return {"class": "listed"}
    if not any(present):
        return {"class": "never"}
    first = present.index(True)
    last = max(i for i, p in enumerate(present) if p)
    prev, rem = versions[last], versions[last + 1]
    return {
        "class": "lost",
        "listed_sha": versions[first]["sha"],
        "listed_time": versions[first]["time"],
        "removed_sha": rem["sha"],
        "removed_time": rem["time"],
        "removed_subject": rem["subject"],
        "also_removed": sorted(set(prev["langs"]) - set(rem["langs"]) - {stem}),
        "added_same": sorted(set(rem["langs"]) - set(prev["langs"])),
        "file_deleted": not rem["file_present"],
        "listed_runs": count_runs(present),
    }


def simple_kind(subject, prev_langs, new_langs, file_present, stem, n_parents):
    """merge > subject names a removal > file deleted > another language added > bulk (3+) > other."""
    if n_parents > 1:
        return "merge-resolution"
    if REMOVAL_WORDS.search(subject or ""):
        return "subject-removal"
    if not file_present:
        return "file-deleted"
    if set(new_langs) - set(prev_langs):
        return "replace"
    if len(set(prev_langs) - set(new_langs) - {stem}) >= 2:
        return "bulk"
    return "other"


def explain_removal(repo, stem, info, path, cache):
    """How the main-line commit that dropped stem did it. For a merge, look into the merged branch."""
    sha = info["removed_sha"]
    ps = parents(repo, sha)
    base_out = {"kind_sha": sha, "kind_subject": info["removed_subject"], "n_parents": len(ps)}
    if len(ps) <= 1:
        prev = lang_at(repo, ps[0], path, cache)[1] if ps else []
        present, new = lang_at(repo, sha, path, cache)
        base_out["kind"] = simple_kind(info["removed_subject"], prev, new, present, stem, 1)
        return base_out
    p1, p2 = ps[0], ps[1]
    p2_has = stem in lang_at(repo, p2, path, cache)[1]
    base = git(["merge-base", p1, p2], repo, check=False).stdout.strip()
    base_has = bool(base) and stem in lang_at(repo, base, path, cache)[1]
    if p2_has or not base_has:
        base_out["kind"] = "merge-resolution"
        return base_out
    out = git(["log", "--reverse", "--format=%H%x09%s", "%s..%s" % (base, p2), "--", path], repo).stdout
    for line in out.splitlines():
        if not line.strip():
            continue
        c, subj = (line.split("\t", 1) + [""])[:2]
        cps = parents(repo, c)
        if not cps:
            continue
        before = lang_at(repo, cps[0], path, cache)[1]
        present, after = lang_at(repo, c, path, cache)
        if stem in before and stem not in after:
            return {"kind": "branch:" + simple_kind(subj, before, after, present, stem, len(cps)),
                    "kind_sha": c, "kind_subject": subj, "n_parents": len(ps)}
    base_out["kind"] = "branch-unknown"
    return base_out


def po_added(repo, rev, path):
    """(sha, time) of the oldest first-parent commit that added path, or ('', 0)."""
    out = git(["log", "--first-parent", "--diff-filter=A", "--format=%H%x09%ct", rev, "--", path],
              repo, check=False).stdout
    lines = [ln for ln in out.splitlines() if ln.strip()]
    if not lines:
        return "", 0
    sha, ct = (lines[-1].split("\t") + ["0"])[:2]
    return sha, int(ct or 0)


def iso(t):
    return time.strftime("%Y-%m-%d", time.gmtime(t)) if t else ""


def commit_url(repo, sha):
    if not sha:
        return ""
    if "gitlab" in repo:
        return "%s/-/commit/%s" % (repo, sha)
    return "%s/commit/%s" % (repo, sha)


def analyse_repo(url, rows, work):
    dest = os.path.join(work, "r")
    shutil.rmtree(dest, ignore_errors=True)
    results = []
    try:
        git(["clone", "--filter=blob:none", "--no-checkout", "--quiet", url, dest], work, timeout=1800)
        commit = rows[0]["commit"]
        found = git(["cat-file", "-e", commit + "^{commit}"], dest, check=False).returncode == 0
        rev = commit if found else "HEAD"
        cache, vers = {}, {}
        for row in rows:
            d, stem = row["dir"], row["stem"]
            path = d + "/LINGUAS"
            if d not in vers:
                vers[d] = linguas_versions(dest, rev, path, cache)
            info = classify(stem, vers[d])
            out = {k: row[k] for k in ("repo", "dir", "stem", "path", "group", "entries",
                                       "translated", "substantive")}
            out["census_commit_found"] = "yes" if found else "no"
            out["linguas_versions"] = len(vers[d])
            out.update(info)
            if info["class"] == "lost":
                out.update(explain_removal(dest, stem, info, path, cache))
            out["po_added_sha"], out["po_added_time"] = po_added(dest, rev, row["path"])
            out["listed_at_head"] = "yes" if stem in lang_at(dest, "HEAD", path, cache)[1] else "no"
            results.append(out)
    except (GitError, subprocess.TimeoutExpired, OSError) as e:
        results = []
        for row in rows:
            out = {k: row[k] for k in ("repo", "dir", "stem", "path", "group", "entries",
                                       "translated", "substantive")}
            out["class"] = "error"
            out["error"] = str(e)[:300]
            results.append(out)
    finally:
        shutil.rmtree(dest, ignore_errors=True)
    return results


def verdict(ok, testable=True):
    if not testable:
        return "NOT TESTABLE"
    return "HOLDS" if ok else "FAILS"


def removal_events(rows):
    """One entry per distinct (repo, dir, main-line removal commit)."""
    events = {}
    for r in rows:
        if r.get("class") == "lost":
            events.setdefault((r["repo"], r["dir"], r["removed_sha"]), r)
    return [events[k] for k in sorted(events)]


def hand_sample(events):
    """All events if 15 or fewer, else the 12 with the smallest removal sha (fixed, no choice)."""
    if len(events) <= 15:
        return list(events)
    return sorted(events, key=lambda e: e["removed_sha"])[:12]


def grade(rows):
    ok = [r for r in rows if r.get("class") in ("never", "lost")]
    repos_all = sorted({r["repo"] for r in rows})
    repos_ok = sorted({r["repo"] for r in rows if r.get("class") != "error"})
    gate_ok = len(repos_ok) >= 45 and len(ok) >= 105
    sub = [r for r in ok if r.get("substantive") == "yes"]
    sub_lost = [r for r in sub if r["class"] == "lost"]
    share = len(sub_lost) / len(sub) if sub else 0.0
    nonsub = [r for r in ok if r.get("substantive") != "yes"]
    ev = removal_events(ok)
    coll = [e for e in ev if e.get("kind") in COLLATERAL]
    deli = [e for e in ev if e.get("kind") in DELIBERATE]
    return {
        "gate": {"rule": "repos_analysed >= 45 and rows_classified (never or lost) >= 105",
                 "repos_analysed": len(repos_ok), "repos_total": len(repos_all),
                 "rows_classified": len(ok), "rows_total": len(rows), "verdict": verdict(gate_ok)},
        "P1": {"rule": "0.05 <= lost / substantive rows <= 0.35",
               "substantive_rows": len(sub), "lost": len(sub_lost), "share": round(share, 4),
               "verdict": verdict(0.05 <= share <= 0.35, bool(sub))},
        "P2": {"rule": "2 * collateral events >= removal events",
               "events": len(ev), "collateral": len(coll),
               "verdict": verdict(2 * len(coll) >= len(ev), bool(ev))},
        "P3": {"rule": "3 * deliberate events <= removal events",
               "events": len(ev), "deliberate": len(deli),
               "verdict": verdict(3 * len(deli) <= len(ev), bool(ev))},
        "H": {"rule": "hand check of hand_check.csv: >= 90% of events confirmed "
                      "(stem in the first parent's LINGUAS, absent after the commit)",
              "events_to_check": len(hand_sample(ev)), "verdict": "PENDING HAND CHECK"},
        "descriptive": {
            "classes": dict(Counter(r.get("class") for r in rows)),
            "nonsubstantive_rows": len(nonsub),
            "nonsubstantive_lost": sum(1 for r in nonsub if r["class"] == "lost"),
            "event_kinds": dict(Counter(e.get("kind") for e in ev)),
            "repos_with_substantive_lost": len({r["repo"] for r in sub_lost}),
            "lost_now_listed_at_head": sum(1 for r in ok if r["class"] == "lost"
                                           and r.get("listed_at_head") == "yes"),
            "never_now_listed_at_head": sum(1 for r in ok if r["class"] == "never"
                                            and r.get("listed_at_head") == "yes"),
        },
    }


ROW_FIELDS = ["repo", "dir", "stem", "path", "group", "entries", "translated", "substantive",
              "class", "census_commit_found", "linguas_versions", "listed_sha", "listed_date",
              "listed_runs", "removed_sha", "removed_date", "removed_url", "removed_subject",
              "kind", "kind_sha", "kind_subject", "n_parents", "also_removed", "added_same",
              "file_deleted", "po_added_sha", "po_added_date", "listed_at_head", "error"]


def flat(r):
    out = dict(r)
    out["listed_date"] = iso(r.get("listed_time", 0))
    out["removed_date"] = iso(r.get("removed_time", 0))
    out["po_added_date"] = iso(r.get("po_added_time", 0))
    out["removed_url"] = commit_url(r["repo"], r.get("removed_sha", ""))
    for k in ("also_removed", "added_same"):
        if isinstance(out.get(k), list):
            out[k] = " ".join(out[k])
    return {k: out.get(k, "") for k in ROW_FIELDS}


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ROW_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(flat(r))


def main(argv):
    src, out_dir = argv[1], argv[2]
    os.makedirs(out_dir, exist_ok=True)
    with open(src, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    by_repo = {}
    for r in rows:
        by_repo.setdefault(r["repo"], []).append(r)
    work = tempfile.mkdtemp(prefix="lhist-")
    results = []
    for i, (url, rs) in enumerate(sorted(by_repo.items())):
        t0 = time.time()
        res = analyse_repo(url, rs, work)
        results.extend(res)
        print("[%d/%d] %s rows=%d %s %.0fs" % (i + 1, len(by_repo), url, len(rs),
              dict(Counter(r["class"] for r in res)), time.time() - t0), flush=True)
    write_csv(os.path.join(out_dir, "rows.csv"), results)
    ok = [r for r in results if r.get("class") in ("never", "lost")]
    events = removal_events(ok)
    write_csv(os.path.join(out_dir, "events.csv"), events)
    write_csv(os.path.join(out_dir, "hand_check.csv"), hand_sample(events))
    summary = grade(results)
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1, sort_keys=True)
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
