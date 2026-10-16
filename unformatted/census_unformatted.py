#!/usr/bin/env python3
"""The strings the translation-crash census skips: translations of strings
whose default (values/) text is marked formatted="false".

aapt2 reads formatted="false" only to skip its "multiple substitutions
specified in non-positional format" check; the compiled text is the same,
and getString(id, args) or String.format still runs it through
java.util.Formatter. Census 0.4.0 leaves these strings out (scan_tree's
`if base in unformatted: continue`), as Android Lint's format checks do, so a
translation of one that throws is never counted. This runs census 0.4.0 over
the same F-Droid repositories and keeps only those strings.

  python census_unformatted.py --data-dir /data --out-dir /out   # same options as census.py

Writes census.py's apps.jsonl, findings.csv, summary.json and report.md (their
counts cover only formatted="false" strings) and unformatted.json, which
checks the predictions in PREDICTIONS.md and a known answer: Helsinki
Timetables' Chinese header_times ("%時刻表，站名%", formatted with
String.format in StationsListOfTrips.getHeaderNextScreen) must be a crash.

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import collections
import csv
import json
import os
import sys
import threading

import census
import census_plurals
import l10n_guard as g

__version__ = "0.1.0"

# census 0.4.0's totals over the same index (data/v6/summary.json).
CENSUS_PAIRS = 1269051
CENSUS_CRASH = 360
KNOWN = ("w32blaster/helsinki-timetables", "zh", "header_times")

_read_resources = census.read_resources
_scan_tree_040 = None
_lock = threading.Lock()
UNFORMATTED = {}  # normalized values folder -> names marked formatted="false"
TOTALS = collections.Counter()


def read_resources(folder):
    """census.read_resources, remembering the names marked formatted="false"
    and returning none, so scan_tree keeps every string."""
    strings, unformatted, bad = _read_resources(folder)
    if unformatted:
        with _lock:
            UNFORMATTED[os.path.normpath(folder)] = set(unformatted)
    return strings, set(), bad


def _base(key):
    q = g._QUANTITY_KEY_RE.match(key)
    return q.group(1) if q else key


def scan_tree(root):
    """census 0.4.0's scan_tree, keeping only translations of strings whose
    values/ text is marked formatted="false"."""
    pairs, stats = _scan_tree_040(root)
    prefix = os.path.normpath(root) + os.sep
    with _lock:
        mine = {k: UNFORMATTED.pop(k) for k in [k for k in UNFORMATTED if k.startswith(prefix)]}
    keep = [p for p in pairs
            if _base(p["key"]) in mine.get(os.path.normpath(os.path.join(root, p["res"], "values")),
                                           ())]
    marked = sum(len(v) for k, v in mine.items() if os.path.basename(k) == "values")
    stats["pairs_all"] = stats.get("pairs", 0)
    stats["pairs"] = len(keep)
    stats["unformatted_names"] = marked
    with _lock:
        TOTALS["names_marked"] += marked
        TOTALS["repos_with_marked"] += 1 if marked else 0
        TOTALS["strings_with_pairs"] += len({(p["res"], _base(p["key"])) for p in keep})
        TOTALS["repos_with_pairs"] += 1 if keep else 0
    return keep, stats


def apply():
    """census 0.4.0 (census_plurals), restricted to formatted="false" strings."""
    global _scan_tree_040
    census_plurals.apply()
    census.read_resources = read_resources
    if census.scan_tree is not scan_tree:
        _scan_tree_040 = census.scan_tree
        census.scan_tree = scan_tree


def predictions(summary, findings):
    pairs = summary.get("formatted_translation_pairs") or 0
    crash = (summary.get("verdicts") or {}).get("crash", 0)
    rate = crash * 1e5 / pairs if pairs else 0.0
    base = CENSUS_CRASH * 1e5 / CENSUS_PAIRS
    formatted = [r for r in findings if r["verdict"] == "crash" and r["use"] == "formatted"
                 and KNOWN[0] not in r["repo"]]
    return [
        {"id": "P1", "text": "at least 2,000 translations of formatted=\"false\" strings are "
         "checked: %d" % pairs, "held": pairs >= 2000},
        {"id": "P2", "text": "their crash rate is at least twice census 0.4.0's (%.1f per 100,000): "
         "%.1f per 100,000 (%d crash)" % (base, rate, crash), "held": rate >= 2 * base},
        {"id": "P3", "text": "at least one crash in a string the code formats, outside Helsinki "
         "Timetables: %d" % len(formatted), "held": bool(formatted)},
    ]


def main(argv=None):
    apply()
    out_dir = "/out"
    args = list(sys.argv[1:] if argv is None else argv)
    if "--out-dir" in args:
        out_dir = args[args.index("--out-dir") + 1]
    code = census.main(args)
    with open(os.path.join(out_dir, "summary.json"), encoding="utf-8") as f:
        summary = json.load(f)
    with open(os.path.join(out_dir, "findings.csv"), encoding="utf-8", newline="") as f:
        findings = list(csv.DictReader(f))
    known = [r for r in findings if KNOWN[0] in r["repo"] and r["locale"] == KNOWN[1]
             and r["key"] == KNOWN[2]]
    gate = bool(known) and known[0]["verdict"] == "crash"
    checks = predictions(summary, findings)
    commit = ""
    if os.path.isfile("census_commit.txt"):
        with open("census_commit.txt") as f:
            commit = f.read().strip()
    result = dict(TOTALS, version=__version__, census_version=census.__version__,
                  census_commit=commit, pairs=summary.get("formatted_translation_pairs"),
                  verdicts=summary.get("verdicts"), crash_by_code_use=summary.get("crash_by_code_use"),
                  repos_attempted=summary.get("repos_attempted"),
                  repos_not_reached=summary.get("repos_not_reached"),
                  known_answer={"repo": KNOWN[0], "locale": KNOWN[1], "key": KNOWN[2],
                                "verdict": known[0]["verdict"] if known else "missing",
                                "held": gate},
                  predictions=checks)
    with open(os.path.join(out_dir, "unformatted.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print("unformatted: %d names marked formatted=\"false\" in %d repositories; %d translations "
          "checked; verdicts %s; crash by code use %s"
          % (TOTALS["names_marked"], TOTALS["repos_with_marked"], result["pairs"] or 0,
             json.dumps(result["verdicts"]), json.dumps(result["crash_by_code_use"])), flush=True)
    print("known answer %s: Helsinki Timetables zh header_times = %s"
          % ("HELD" if gate else "FAILED", result["known_answer"]["verdict"]), flush=True)
    for p in checks:
        print("%s %s: %s" % (p["id"], "HELD" if p["held"] else "FAILED", p["text"]), flush=True)
    return code or (0 if gate else 1)


if __name__ == "__main__":
    sys.exit(main())
