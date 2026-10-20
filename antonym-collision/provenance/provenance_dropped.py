#!/usr/bin/env python3
"""Follow-up to the Mattermost provenance test, as pre-registered in
antonym-collision/PROVENANCE-DROPPED-PREREG.md. The first run could not read
cs, fi, hr and lt at B: Mattermost removed those locales on 2026-09-04
(#38219, e937969) and restored them on 2026-10-02 (#38944, 70c1732) from the
commit before the removal. This reads the 12 warning rows of those four
locales at B2, the first parent of e937969, and classes each row with
provenance.classify (INHERITED, INTRODUCED, CHANGED, UNREADABLE or
NOT_REPRODUCED). Waits for the pre-registration to be public on the census's
main branch first, and exits 1 if it never appears.

  python provenance_dropped.py --rows dropped_rows.csv --out-dir /out/dropped

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import csv
import json
import os
import sys
import time

import provenance as p

REMOVAL = "e937969"
REMOVAL_DATE = "2026-09-04"
LOCALES = ("cs", "fi", "hr", "lt")
PREREG = ("https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/main/"
          "antonym-collision/PROVENANCE-DROPPED-PREREG.md")
# mm-provenance-v1: all 32 graded rows that were readable at B were INHERITED.
FIRST_RUN_GRADED_INHERITED = 32


def wait_for_prereg(wait_seconds, step=30):
    deadline = time.time() + wait_seconds
    while True:
        try:
            if "Pre-registered 2026-10-20" in p.get(PREREG):
                return True
        except OSError as exc:
            print("pre-registration not public yet (%s)" % exc)
        if time.time() >= deadline:
            return False
        time.sleep(step)


def resolve_before_removal():
    """Full sha of the removal commit, its first parent, and the parent's committer date."""
    removal = json.loads(p.get(p.API % REMOVAL, "application/vnd.github+json"))
    sha = removal["parents"][0]["sha"]
    parent = json.loads(p.get(p.API % sha, "application/vnd.github+json"))
    return removal["sha"], sha, parent["commit"]["committer"]["date"]


def read_rows(path):
    rows = [r for r in p.read_csv(path) if r["locale"] in LOCALES]
    for row in rows:
        row["graded"] = row["graded"] == "True"
    return rows


def of(rows, locales):
    return [r for r in rows if r["locale"] in locales]


def not_inherited(rows):
    return sum(1 for r in rows if r["class"] in ("INTRODUCED", "CHANGED"))


def combined(rows):
    """Graded rows INHERITED across both snapshots (post hoc, not a test)."""
    return FIRST_RUN_GRADED_INHERITED + p.count(rows, "INHERITED", True)


def predictions(rows, b_date):
    graded = [r for r in rows if r["graded"]]
    bad = [r for r in rows if r["class"] in ("UNREADABLE", "NOT_REPRODUCED")]
    s0 = (not bad and len(rows) == 12 and len(graded) == 8
          and bool(b_date) and b_date[:10] <= REMOVAL_DATE)
    convert, cs, fi = of(rows, ("hr", "lt")), of(rows, ("cs",)), of(rows, ("fi",))
    inherited_convert = p.count(convert, "INHERITED", False)
    inherited_cs = p.count(cs, "INHERITED", False)
    out = [{"id": "S0", "held": s0,
            "value": "%d rows, %d graded, %d unreadable or not reproduced, B2 dated %s"
                     % (len(rows), len(graded), len(bad), b_date)}]
    tests = [
        ("S1", len(convert) == 4 and inherited_convert == 4,
         "%d of %d hr and lt rows INHERITED" % (inherited_convert, len(convert))),
        ("S2", len(cs) == 5 and inherited_cs >= 4, "%d of %d cs rows INHERITED" % (inherited_cs, len(cs))),
        ("S3", len(fi) == 3 and not_inherited(fi) >= 2,
         "%d of %d fi rows INTRODUCED or CHANGED" % (not_inherited(fi), len(fi))),
    ]
    for pid, held, value in tests:
        out.append({"id": pid, "held": held if s0 else None, "value": value})
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", default="dropped_rows.csv")
    parser.add_argument("--out-dir", default="/out/dropped")
    parser.add_argument("--wait", type=int, default=600)
    args = parser.parse_args()
    if not wait_for_prereg(args.wait):
        print("PROVENANCE-DROPPED-PREREG.md is not public on main; not running")
        return 1
    removal, b_sha, b_date = resolve_before_removal()
    print("T %s\nB2 %s (%s), first parent of %s" % (p.T, b_sha, b_date, removal))
    rows = read_rows(args.rows)
    en_b = p.load_catalog(b_sha, "en")
    at_t = {loc: p.load_catalog(p.T, loc) for loc in LOCALES}
    at_b = {loc: p.load_catalog(b_sha, loc) for loc in LOCALES}
    for row in rows:
        row["class"], row["detail"] = p.classify(row, at_t[row["locale"]], at_b[row["locale"]], en_b)
    os.makedirs(args.out_dir, exist_ok=True)
    fields = ["locale", "key1", "key2", "graded", "class", "detail"]
    with open(os.path.join(args.out_dir, "provenance_dropped.csv"), "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in fields})
    preds = predictions(rows, b_date)
    summary = {
        "t": p.T, "b2": b_sha, "b2_date": b_date, "removal": removal,
        "by_class_graded": {c: p.count(rows, c, True) for c in p.CLASSES},
        "by_class_all": {c: p.count(rows, c, False) for c in p.CLASSES},
        "predictions": preds,
        "combined_graded_inherited_post_hoc": combined(rows),
    }
    with open(os.path.join(args.out_dir, "summary.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, indent=1)
        f.write("\n")
    for row in rows:
        print("%s %s | %s | %s: %s" % (row["locale"], row["key1"], row["key2"], row["class"], row["detail"]))
    for x in preds:
        print("%s %s: %s" % (x["id"], {True: "HELD", False: "FAILED", None: "NOT TESTED"}[x["held"]], x["value"]))
    print("post hoc, not a test: %d of 40 graded rows INHERITED across B and B2" % combined(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
