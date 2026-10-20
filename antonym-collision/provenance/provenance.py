#!/usr/bin/env python3
"""Provenance of the Mattermost antonym-collision warnings, as pre-registered in
antonym-collision/PROVENANCE-PREREG.md: for each warning row graded at T
(be207f89, 2026-10-20), reads the two keys' values at B (the first parent of
f5b9b0e, the 2026-10-01 merge that first filled the catalogs with the AI
translation pipeline's output) and classes the row INHERITED, INTRODUCED,
CHANGED or UNREADABLE. Waits for the pre-registration to be public on the
census's main branch first, and exits 1 if it never appears.

  python provenance.py --rows rows.csv --graded graded.csv --out-dir /out/provenance

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.request

T = "be207f89725df343da628e859d1ef25acde02fbc"
PIPELINE = "f5b9b0ed4742ffac6dba6bb0f20680fe92b93b87"
PIPELINE_DATE = "2026-10-01"
RAW = "https://raw.githubusercontent.com/mattermost/mattermost/%s/webapp/channels/src/i18n/%s.json"
API = "https://api.github.com/repos/mattermost/mattermost/commits/%s"
PREREG = ("https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/main/"
          "antonym-collision/PROVENANCE-PREREG.md")
CONVERT_KEYS = frozenset((
    "admin.permissions.group.convert_public_channel_to_private.name",
    "admin.permissions.group.convert_private_channel_to_public.name",
    "admin.permissions.permission.convert_public_channel_to_private.name",
    "admin.permissions.permission.convert_private_channel_to_public.name",
))
CLASSES = ("INHERITED", "INTRODUCED", "CHANGED", "UNREADABLE", "NOT_REPRODUCED")


def get(url, accept=None):
    headers = {"User-Agent": "mv2-census-provenance"}
    if accept:
        headers["Accept"] = accept
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8")


def wait_for_prereg(wait_seconds, step=30):
    deadline = time.time() + wait_seconds
    while True:
        try:
            text = get(PREREG)
            if "Pre-registered 2026-10-20" in text:
                return True
        except OSError as exc:
            print("pre-registration not public yet (%s)" % exc)
        if time.time() >= deadline:
            return False
        time.sleep(step)


def resolve_before():
    """First parent of the pipeline merge, and that commit's committer date."""
    merge = json.loads(get(API % PIPELINE, "application/vnd.github+json"))
    sha = merge["parents"][0]["sha"]
    parent = json.loads(get(API % sha, "application/vnd.github+json"))
    return sha, parent["commit"]["committer"]["date"]


def unwrap(data):
    """Flat {id: message}; FormatJS descriptors {id: {defaultMessage}} are unwrapped."""
    out = {}
    for key, value in data.items():
        if isinstance(value, dict):
            value = value.get("defaultMessage")
        if isinstance(value, str):
            out[key] = value
    return out


def load_catalog(sha, locale):
    try:
        data = json.loads(get(RAW % (sha, locale)))
    except (OSError, ValueError) as exc:
        print("%s at %s: unreadable (%s)" % (locale, sha[:8], exc))
        return None
    if not isinstance(data, dict):
        return None
    return unwrap(data)


def state(value, english):
    """'missing', 'empty', 'english' or 'translated'."""
    if value is None:
        return "missing"
    if not value.strip():
        return "empty"
    if english is not None and value == english:
        return "english"
    return "translated"


def classify(row, at_t, at_b, en_b):
    """Returns (class, ASCII detail) for one warning row."""
    k1, k2 = row["key1"], row["key2"]
    if at_t is None or at_b is None or en_b is None:
        return "UNREADABLE", "catalog not readable at %s" % ("T" if at_t is None else "B")
    t1, t2 = at_t.get(k1), at_t.get(k2)
    if not t1 or t1 != t2:
        return "NOT_REPRODUCED", "keys do not share one value at T"
    b1, b2 = at_b.get(k1), at_b.get(k2)
    s1, s2 = state(b1, en_b.get(k1)), state(b2, en_b.get(k2))
    if s1 != "translated" or s2 != "translated":
        parts = ["%s %s at B" % (name, s) for name, s in (("key1", s1), ("key2", s2)) if s != "translated"]
        return "INTRODUCED", "; ".join(parts)
    if b1 == t1 and b2 == t2:
        return "INHERITED", "both values identical at B and T"
    parts = ["%s changed after B" % name for name, b, t in (("key1", b1, t1), ("key2", b2, t2)) if b != t]
    return "CHANGED", "; ".join(parts)


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def pair(row):
    return (row["locale"], frozenset((row["key1"], row["key2"])))


def mark(rows, graded):
    """Adds 'graded' and 'group_a' to each row; returns the graded pairs not found in rows."""
    real = {pair(g) for g in graded if g.get("project", "mattermost") == "mattermost" and g["verdict"] == "real"}
    seen = set()
    for row in rows:
        p = pair(row)
        row["graded"] = p in real
        row["group_a"] = row["graded"] and p[1] <= CONVERT_KEYS
        if row["graded"]:
            seen.add(p)
    return sorted((loc, sorted(keys)) for loc, keys in real - seen)


def count(rows, cls, only_graded):
    return sum(1 for r in rows if r["class"] == cls and (r["graded"] or not only_graded))


def predictions(rows, b_date, unmatched):
    graded = [r for r in rows if r["graded"]]
    group_a = [r for r in rows if r["group_a"]]
    bad = [r for r in rows if r["class"] in ("UNREADABLE", "NOT_REPRODUCED")]
    r0 = (not bad and not unmatched and len(graded) == 40 and len(rows) == 67
          and bool(b_date) and b_date[:10] < PIPELINE_DATE)
    inherited_graded = count(rows, "INHERITED", True)
    introduced_graded = count(rows, "INTRODUCED", True)
    inherited_all = count(rows, "INHERITED", False)
    out = [{"id": "R0", "held": r0,
            "value": "%d rows, %d graded, %d unreadable or not reproduced, %d graded unmatched, B dated %s"
                     % (len(rows), len(graded), len(bad), len(unmatched), b_date)}]
    tests = [
        ("R1", inherited_graded >= 34, "%d of %d graded rows INHERITED" % (inherited_graded, len(graded))),
        ("R2", len(group_a) == 12 and all(r["class"] == "INHERITED" for r in group_a),
         "%d of %d Convert Channels rows INHERITED"
         % (sum(1 for r in group_a if r["class"] == "INHERITED"), len(group_a))),
        ("R3", introduced_graded <= 3, "%d of %d graded rows INTRODUCED" % (introduced_graded, len(graded))),
        ("R4", inherited_all * 5 >= len(rows) * 4, "%d of %d warning rows INHERITED" % (inherited_all, len(rows))),
    ]
    for pid, held, value in tests:
        out.append({"id": pid, "held": held if r0 else None, "value": value})
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", default="rows.csv")
    parser.add_argument("--graded", default="graded.csv")
    parser.add_argument("--out-dir", default="/out/provenance")
    parser.add_argument("--wait", type=int, default=600)
    args = parser.parse_args()
    if not wait_for_prereg(args.wait):
        print("PROVENANCE-PREREG.md is not public on main; not running")
        return 1
    b_sha, b_date = resolve_before()
    print("T %s\nB %s (%s), first parent of %s" % (T, b_sha, b_date, PIPELINE))
    rows = read_csv(args.rows)
    unmatched = mark(rows, read_csv(args.graded))
    locales = sorted({r["locale"] for r in rows})
    en_b = load_catalog(b_sha, "en")
    at_t = {loc: load_catalog(T, loc) for loc in locales}
    at_b = {loc: load_catalog(b_sha, loc) for loc in locales}
    for row in rows:
        row["class"], row["detail"] = classify(row, at_t[row["locale"]], at_b[row["locale"]], en_b)
    os.makedirs(args.out_dir, exist_ok=True)
    fields = ["locale", "key1", "key2", "graded", "group_a", "class", "detail"]
    with open(os.path.join(args.out_dir, "provenance.csv"), "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in fields})
    preds = predictions(rows, b_date, unmatched)
    summary = {
        "t": T, "b": b_sha, "b_date": b_date, "pipeline_merge": PIPELINE,
        "by_class_graded": {c: count(rows, c, True) for c in CLASSES},
        "by_class_all": {c: count(rows, c, False) for c in CLASSES},
        "unmatched_graded": unmatched,
        "predictions": preds,
    }
    with open(os.path.join(args.out_dir, "summary.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, indent=1)
        f.write("\n")
    for row in rows:
        if row["class"] != "INHERITED":
            print("%s %s | %s | %s: %s" % (row["locale"], row["key1"], row["key2"], row["class"], row["detail"]))
    for p in preds:
        print("%s %s: %s" % (p["id"], {True: "HELD", False: "FAILED", None: "NOT TESTED"}[p["held"]], p["value"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
