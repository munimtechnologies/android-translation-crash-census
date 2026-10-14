#!/usr/bin/env python3
"""Compares two census findings.csv files: which crash rows appeared or went
away between runs (by repository, file and key), and the verdict counts.

  python compare.py OLD.csv|URL NEW.csv --out compare.md

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import collections
import csv
import io
import sys
import urllib.request


def load(path):
    if path.startswith("https://"):
        req = urllib.request.Request(path, headers={"User-Agent": "mv2-translation-crash-census"})
        with urllib.request.urlopen(req, timeout=120) as r:
            text = r.read().decode("utf-8")
    else:
        with open(path, encoding="utf-8", newline="") as f:
            text = f.read()
    return list(csv.DictReader(io.StringIO(text, newline="")))


def row_id(row):
    return (row["repo"], row["file"], row["key"])


def crashes(rows):
    return {row_id(r): r for r in rows if r["verdict"] == "crash"}


def compare(old_rows, new_rows):
    old, new = crashes(old_rows), crashes(new_rows)
    gone = [old[k] for k in sorted(set(old) - set(new))]
    added = [new[k] for k in sorted(set(new) - set(old))]
    lines = ["# Census findings compared", "",
             "| | old | new |", "|---|---:|---:|"]
    for verdict in ("crash", "crash-if-text"):
        lines.append("| %s rows | %d | %d |" % (
            verdict, sum(r["verdict"] == verdict for r in old_rows),
            sum(r["verdict"] == verdict for r in new_rows)))
    lines.append("| reachable crash rows (formatted) | %d | %d |" % (
        sum(r["verdict"] == "crash" and r["use"] == "formatted" for r in old_rows),
        sum(r["verdict"] == "crash" and r["use"] == "formatted" for r in new_rows)))
    lines.append("| repositories with a crash | %d | %d |" % (
        len({k[0] for k in old}), len({k[0] for k in new})))
    for title, rows in (("Crash rows no longer reported", gone), ("New crash rows", added)):
        by_app = collections.Counter(r["app"] for r in rows)
        lines += ["", "## %s: %d" % (title, len(rows)), ""]
        lines += ["- %s: %d" % (app, n) for app, n in by_app.most_common()]
        lines += ["", "| app | locale | key | use | exception |", "|---|---|---|---|---|"]
        lines += ["| %s | %s | `%s` | %s | %s |" % (r["app"], r["locale"], r["key"], r["use"],
                                                     r["exception"]) for r in rows]
    return "\n".join(lines) + "\n", gone, added


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("old")
    parser.add_argument("new")
    parser.add_argument("--out", default="compare.md")
    args = parser.parse_args()
    text, gone, added = compare(load(args.old), load(args.new))
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(text)
    print("%d crash rows gone, %d new" % (len(gone), len(added)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
