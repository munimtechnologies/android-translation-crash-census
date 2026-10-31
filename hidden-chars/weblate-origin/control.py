#!/usr/bin/env python3
# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Exploratory control for weblate-origin (NOT pre-registered; written after its results were seen).

weblate-origin found that none of the 90 stray U+200B on Weblate-platform apps was put there by a
Weblate commit. That is only meaningful if Weblate commits exist in these histories and the
classifier finds them. For the same rows and the same attribution rule (zwsp_origin.py, imported
unchanged), this counts:
  - Weblate commits anywhere on each repository's branch, and in each row's locale folder;
  - Weblate commits to the row's folder made after the U+200B arrived (it survived them);
  - which translation platform, if any, the introducing commit's message names.

Made with AI agents by MV2 of Munim, Inc. Standard library only; needs git.
"""
import argparse
import collections
import concurrent.futures
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zwsp_origin as zo  # noqa: E402

VERSION = "0.1.0"

# Ordered: the first match names the platform. Crowdin's default commit subject is
# "New translations <file> (<Language>)", which the census also used to detect Crowdin.
PLATFORMS = (
    ("weblate", re.compile(r"using Weblate|Translate-URL:|\bweblate\b", re.I)),
    ("localazy", re.compile(r"localazy", re.I)),
    ("crowdin", re.compile(r"crowdin|^New translations? .+\(.+\)", re.I | re.M)),
    ("transifex", re.compile(r"transifex|\btx pull\b", re.I)),
    ("lokalise", re.compile(r"lokalise", re.I)),
    ("pontoon", re.compile(r"pontoon", re.I)),
    ("translatewiki", re.compile(r"translatewiki", re.I)),
)


def named_platform(message):
    """Platform named anywhere in a commit message, or "" if none."""
    for name, rx in PLATFORMS:
        if rx.search(message or ""):
            return name
    return ""


def weblate_after(commits, intro_sha):
    """Weblate commits listed before (newer than) intro_sha in log order."""
    n = 0
    for c in commits:
        if c.sha == intro_sha:
            return n
        if zo.is_weblate(c.message, c.author_email, c.committer_email):
            n += 1
    return None


def weblate_stats(commits):
    """(count, first date, last date, hosts) of the Weblate commits in a list."""
    w = [c for c in commits if zo.is_weblate(c.message, c.author_email, c.committer_email)]
    dates = sorted(c.date[:10] for c in w)
    hosts = sorted({zo.translate_host(c.message) for c in w} - {""})
    return len(w), (dates[0] if dates else ""), (dates[-1] if dates else ""), hosts


LOG_FMT = "--format=%H%x1f%P%x1f%ae%x1f%ce%x1f%cI%x1f%B%x1e"


def process_repo(url, head, rows, tmp_root, clone_timeout):
    d = tempfile.mkdtemp(dir=tmp_root)
    t0 = time.time()
    res = {"repo": url, "head": head, "status": "ok", "rows": []}

    def fail(status):
        res["status"] = status
        res["rows"] = [dict(r, status=status) for r in rows]
        return res

    store = None
    try:
        g = os.path.join(d, "g")
        r = zo.git(["clone", "--quiet", "--bare", "--single-branch", "--no-tags", url, g], timeout=clone_timeout)
        if r.returncode != 0:
            return fail("clone-failed")
        if zo.git(["-C", g, "cat-file", "-e", head + "^{commit}"]).returncode != 0:
            zo.git(["-C", g, "fetch", "--quiet", "--no-tags", "origin", head], timeout=clone_timeout)
            if zo.git(["-C", g, "cat-file", "-e", head + "^{commit}"]).returncode != 0:
                return fail("head-missing")
        all_commits = zo.parse_log(zo.git(["-C", g, "log", "--no-merges", LOG_FMT, head]).stdout)
        n, first, last, hosts = weblate_stats(all_commits)
        res.update(commits_total=len(all_commits), weblate_total=n, weblate_first=first,
                   weblate_last=last, weblate_hosts=hosts)
        store = zo.Store(g)
        by_folder = collections.defaultdict(list)
        for row in rows:
            by_folder[row["folder"]].append(row)
        for folder, frows in sorted(by_folder.items()):
            keys = sorted({x["key"] for x in frows})
            cache = {}

            def state(sha, folder=folder, keys=keys, cache=cache):
                if sha not in cache:
                    cache[sha] = zo.folder_state(store, sha, folder, keys)
                return cache[sha]

            commits = zo.parse_log(zo.git(["-C", g, "log", "--no-merges", LOG_FMT, head, "--", folder + "/"]).stdout)
            fw = weblate_stats(commits)[0]
            for row in frows:
                out = dict(row, status="", commit="", kind="", platform_named="",
                           weblate_in_folder=fw, weblate_after_intro="")
                if not zo.has_zwsp(state(head), row["key"], row["index"]):
                    out["status"] = "not-at-head"
                else:
                    c, kind = zo.attribute(commits, state, row["key"], row["index"])
                    if c is None:
                        out["status"] = "unattributed"
                    else:
                        out.update(status="attributed", commit=c.sha, kind=kind,
                                   platform_named=named_platform(c.message),
                                   weblate_after_intro=weblate_after(commits, c.sha))
                res["rows"].append(out)
        return res
    except subprocess.TimeoutExpired:
        return fail("timeout")
    except Exception as e:  # keep going; record what broke
        res["error"] = repr(e)[:200]
        return fail("error")
    finally:
        if store:
            store.close()
        res["seconds"] = round(time.time() - t0, 1)
        shutil.rmtree(d, ignore_errors=True)


def summarize(repos, rows):
    att = [r for r in rows if r["status"] == "attributed"]
    ok = [r for r in repos if r["status"] == "ok"]
    return {
        "repos": len(repos),
        "repo_status_counts": dict(collections.Counter(r["status"] for r in repos)),
        "repos_with_weblate_commits": sum(1 for r in ok if r.get("weblate_total", 0) > 0),
        "weblate_commits_total": sum(r.get("weblate_total", 0) for r in ok),
        "rows": len(rows),
        "row_status_counts": dict(collections.Counter(r["status"] for r in rows)),
        "rows_folder_has_weblate_commits": sum(1 for r in att if r["weblate_in_folder"] > 0),
        "rows_weblate_after_intro": sum(1 for r in att if (r["weblate_after_intro"] or 0) > 0),
        "repos_weblate_after_intro": len({r["repo"] for r in att if (r["weblate_after_intro"] or 0) > 0}),
        "platform_named": dict(collections.Counter(r["platform_named"] or "none" for r in att)),
    }


REPO_COLS = ["repo", "head", "status", "commits_total", "weblate_total", "weblate_first", "weblate_last",
             "weblate_hosts", "seconds"]
ROW_COLS = ["repo", "folder", "lang", "key", "index", "status", "commit", "kind", "platform_named",
            "weblate_in_folder", "weblate_after_intro"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--hits", help="local hits.csv instead of downloading")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--clone-timeout", type=float, default=1500)
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    if a.hits:
        with open(a.hits, "rb") as f:
            raw = f.read()
    else:
        with urllib.request.urlopen(zo.HITS_URL, timeout=120) as resp:
            raw = resp.read()
    rows = zo.select_rows(raw.decode("utf-8"))
    by_repo = collections.defaultdict(list)
    for r in rows:
        by_repo[(r["repo"], r["head"])].append(r)
    print("weblate control %s: %d rows in %d repositories" % (VERSION, len(rows), len(by_repo)), flush=True)
    tmp_root = tempfile.mkdtemp(prefix="wbcontrol-")
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
        results = list(ex.map(lambda it: process_repo(it[0][0], it[0][1], it[1], tmp_root, a.clone_timeout),
                              sorted(by_repo.items())))
    shutil.rmtree(tmp_root, ignore_errors=True)
    out_rows = [row for r in results for row in r["rows"]]
    with open(os.path.join(a.out_dir, "control_repos.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=REPO_COLS, extrasaction="ignore")
        w.writeheader()
        for r in results:
            w.writerow(dict({k: r.get(k, "") for k in REPO_COLS},
                            weblate_hosts=" ".join(r.get("weblate_hosts") or [])))
    with open(os.path.join(a.out_dir, "control_rows.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ROW_COLS, extrasaction="ignore")
        w.writeheader()
        for row in out_rows:
            w.writerow({k: row.get(k, "") for k in ROW_COLS})
    summary = summarize(results, out_rows)
    summary.update({"version": VERSION, "zwsp_origin_version": zo.VERSION, "exploratory": True})
    with open(os.path.join(a.out_dir, "control_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1, sort_keys=True)
    print(json.dumps(summary, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
