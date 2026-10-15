# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made by MV2 of Munim, Inc. with AI agents.
"""Three open-source format checks, run over the census's crashing translations.

A project that takes Android translations can run three free checks on them before
they ship: Weblate's "Java format" check (on by itself for Android strings on Weblate),
translate-toolkit's `printf` test (what `pofilter` runs), and Android Lint's
StringFormatDetector (StringFormatInvalid / StringFormatCount / StringFormatMatches,
run by `gradle lint`). This runs all three over every translation the census found
crashing in java.util.Formatter and reports, per row, which of them would have said
anything, and which rows none of them can see.

Weblate: weblate_blind.py (JAVA_MATCH read from Weblate's own source at a pinned commit).
pofilter: `printf_pat` is read with ast from translate-toolkit's checks/standard.py at the
  commit pinned in checks_deps.py (GPL; never copied). The comparison rules of its `printf`
  test are mirrored: a target placeholder with an index must match a source placeholder with
  that index (or, when the source is unindexed, the one at that position) with the identical
  flags/width/type; a keyed one must match by key; unindexed ones are compared by position;
  a target with no placeholders fails when the source has some; and the counts must agree.
  In plural strings a `%.0s` target placeholder is forgiven. The test is a hard failure in
  pofilter ("critical").
Android Lint: the FORMAT pattern is copied from StringFormatDetector.kt (Apache-2.0, The
  Android Open Source Project); test_checks_blind.py compares it with the downloaded source.
  Lint first classifies a string: a "%" that no FORMAT match follows makes the whole string
  "not formatted"; a conversion letter Lint doesn't know (or a t/T date one) makes it
  "ignored", and an ignored translation is never compared. A translation that survives is
  compared with the default string: different argument count -> StringFormatCount (warning;
  a "not formatted" translation counts as zero arguments, so a stray % is reported here with
  a wrong message), a space flag before a non-integer conversion -> StringFormatInvalid
  (error), different conversion class for the same argument -> StringFormatMatches (error).
  The detector visits <string> only, never <plurals>, so plural rows are "not visited".
  (The `formatted="false"` attribute and lint suppressions aren't modelled: the census has
  the text, not the XML attributes.)

All three run on the census's extracted text, not on the raw XML.

Usage: python checks_blind.py findings.csv --out-dir out
       python checks_blind.py --url https://.../findings.csv --out-dir out
"""

import argparse
import collections
import csv
import json
import os
import re

import taxonomy
import weblate_blind as wb

VERSION = "0.1.0"

# Android Lint, StringFormatDetector.kt (Apache-2.0, Copyright (C) 2011 The Android Open Source Project):
# %[argument_index$][flags][width][.precision]conversion, groups 1-6.
LINT_FORMAT = re.compile(r"%(\d+\$)?([-+#, 0(<]*)?(\d+)?(\.\d+)?([tT])?([a-zA-Z%])")

LINT_CLASSES = {"datetime": "tT", "string": "sS", "character": "cC", "integer": "doxX",
                "float": "feEgGaA", "boolean": "bB", "hashcode": "hH", "percent": "%", "newline": "n"}
IGNORE, FORMATTED, NOT_FORMATTED = "ignore", "formatted", "not-formatted"
STRING_FORMAT_COUNT, STRING_FORMAT_INVALID, STRING_FORMAT_MATCHES = (
    "StringFormatCount", "StringFormatInvalid", "StringFormatMatches")
NAME = "name"   # what Lint compares a not-formatted string as: its resource name, zero arguments

CHECKS = ("weblate", "pofilter", "lint")


# ----- translate-toolkit (pofilter) -----

def pofilter_vars(regexp, text):
    out = []
    for i, m in enumerate(regexp.finditer(text)):
        boost = m.group("boost_ord")
        out.append(dict(text=m.group(), pos=i, ord=boost or m.group("ord"), key=m.group("key"),
                        full="%" if boost else m.group("fullvar")))
    return out


def pofilter_check(regexp, source, target, plural=False):
    """The failure pofilter's printf test would report, or None when it passes."""
    src, tgt = pofilter_vars(regexp, source or ""), pofilter_vars(regexp, target or "")
    if not tgt:
        return "Missing printf variable: " + ", ".join(v["text"] for v in src) if src else None
    for t in tgt:
        if t["ord"]:
            cands = [s for s in src if s["ord"] == t["ord"] or (not s["ord"] and int(t["ord"]) == s["pos"] + 1)]
            if not cands:
                return "Added printf variable: " + t["text"]
            if not any(s["full"] == t["full"] for s in cands):
                return "Different printf variable: " + t["text"]
        elif t["key"]:
            cands = [s for s in src if s["key"] and s["key"] == t["key"]]
            if not cands:
                return "Added printf variable: " + t["text"]
            if plural and t["full"] == ".0s":
                continue
            if any(s["full"] != t["full"] for s in cands):
                return "Different printf variable: " + t["text"]
        else:
            if plural and t["full"] == ".0s":
                continue
            if t["pos"] < len(src) and src[t["pos"]]["full"] != t["full"]:
                return "Different printf variable: " + t["text"]
    if len(src) != len(tgt):
        return "Different number of printf variables"
    return None


# ----- Android Lint -----

def lint_class(c):
    for name, letters in LINT_CLASSES.items():
        if c in letters:
            return name
    return "unknown"


def lint_classify(text):
    """FORMATTED / NOT_FORMATTED / IGNORE, the way checkTextNode decides it."""
    found = False
    j, m = 0, len(text)
    while j < m:
        c = text[j]
        if c == "\\":
            j += 1
        if c == "%":
            mt = LINT_FORMAT.search(text, j)
            if not mt:
                return NOT_FORMATTED
            if lint_class(mt.group(6)[0]) == "unknown" or mt.group(5) is not None:
                return IGNORE
            found = True
            j += 1
        j += 1
    if found:
        return FORMATTED
    stripped = text.strip()
    return IGNORE if stripped[:1] in ("@", "?") else NOT_FORMATTED


def lint_args(text):
    """(argument number, match) the way Lint's getFormatArgumentSequenceWithIndex counts."""
    out, index, next_number = [], 0, 1
    while True:
        mt = LINT_FORMAT.search(text, index)
        if not mt:
            return out
        if mt.group(6) in ("%", "n"):
            index = mt.end()
        elif mt.start() >= 1 and text[mt.start() - 1] == "\\":
            index = mt.start() + 1
        else:
            index = mt.end()
            if mt.group(1) is None:
                number = next_number
                next_number += 1
            else:
                number = int(mt.group(1)[:-1])
                next_number = number + 1
            out.append((number, mt))


def lint_check(source, translation):
    """Issue ids Lint reports for a <string> translation, [] if none, None if Lint ignores it."""
    pairs = []
    s_type, t_type = lint_classify(source or ""), lint_classify(translation or "")
    if s_type == FORMATTED:
        pairs.append(source)
    elif s_type == NOT_FORMATTED:
        pairs.append(NAME)
    if t_type == FORMATTED:
        pairs.append(translation)
    elif t_type == NOT_FORMATTED:
        pairs.append(NAME)
    else:
        return None
    issues = set()
    # checkArity
    prev = -1
    for fs in pairs:
        numbers = [n for n, _ in lint_args(fs)]
        count = max(numbers) if numbers else 0
        if prev != -1 and prev != count:
            issues.add(STRING_FORMAT_COUNT)
            break
        if any(i not in numbers for i in range(1, count + 1)):
            issues.add(STRING_FORMAT_COUNT)
            break
        prev = count
    # checkTypes
    types = {}
    for fs in pairs:
        for number, mt in lint_args(fs):
            s = mt.group(0)
            if len(s) > 2 and s[-2] == " " and s[-1] not in "doxX":
                issues.add(STRING_FORMAT_INVALID)
                continue
            fmt = mt.group(6)
            cur = types.get(number)
            if cur is None:
                types[number] = fmt
            elif cur != fmt:
                a, b = lint_class(cur[0]), lint_class(fmt[0])
                if a != b and "unknown" not in (a, b):
                    issues.add(STRING_FORMAT_MATCHES)
                    break
    return sorted(issues)


# ----- the matrix -----

def verdicts(rx_weblate, rx_printf, row):
    """Per-check verdicts for one census row."""
    plural = "[" in row["key"]
    w, diff = wb.verdict(rx_weblate, row)
    p = pofilter_check(rx_printf, row["source"], row["translation"], plural=plural)
    if plural:
        lint, lint_issues = "not-visited", None
    else:
        lint_issues = lint_check(row["source"], row["translation"])
        lint = "ignored" if lint_issues is None else ("flagged" if lint_issues else "unflagged")
    return dict(weblate=w, weblate_diff=diff or {}, pofilter="flagged" if p else "unflagged",
                pofilter_message=p or "", lint=lint, lint_issues=" ".join(lint_issues or []))


def summarise(rx_weblate, rx_printf, rows, exclude_repos=wb.EXCLUDE_REPOS):
    kept, dropped = wb.select(rows, exclude_repos)
    out = {"checks_blind_version": VERSION, "dropped": dict(dropped), "groups": {}, "rows": []}
    for r in kept:
        v = verdicts(rx_weblate, rx_printf, r)
        seen = [c for c in CHECKS if v[c] == "flagged"]
        out["rows"].append(dict(app=r["app"], repo=r["repo"], locale=r["locale"], key=r["key"], use=r["use"],
                                exception=r["exception"], kind=taxonomy.classify(r["exception"], r["translation"]),
                                weblate=v["weblate"], pofilter=v["pofilter"], lint=v["lint"],
                                lint_issues=v["lint_issues"], pofilter_message=v["pofilter_message"],
                                seen_by=" ".join(seen), source=r["source"], translation=r["translation"]))
    groups = {"all-crash": out["rows"], "formatted-crash": [e for e in out["rows"] if e["use"] == "formatted"]}
    for name, group in groups.items():
        g = {"rows": len(group), "repos": len({e["repo"] for e in group}), "checks": {}, "seen_by": {},
             "by_kind": {}}
        for c in CHECKS:
            cnt = collections.Counter(e[c] for e in group)
            g["checks"][c] = {k: cnt[k] for k in sorted(cnt)}
        combos = collections.Counter(e["seen_by"] or "none" for e in group)
        g["seen_by"] = {k: {"rows": n, "repos": len({e["repo"] for e in group if (e["seen_by"] or "none") == k})}
                        for k, n in sorted(combos.items())}
        for kind in taxonomy.KINDS:
            sel = [e for e in group if e["kind"] == kind]
            if sel:
                g["by_kind"][kind] = {"rows": len(sel), "repos": len({e["repo"] for e in sel}),
                                      "none": sum(1 for e in sel if not e["seen_by"]),
                                      **{c + "_flagged": sum(1 for e in sel if e[c] == "flagged") for c in CHECKS}}
        out["groups"][name] = g
    return out


def report(s):
    lines = ["# Which open-source format checks see the census's crashing translations", "",
             "checks_blind.py %s (MV2 of Munim, Inc., made with AI agents). Weblate's JAVA_MATCH and "
             "translate-toolkit's printf_pat are read from their sources at the commits pinned in "
             "weblate_deps.py / checks_deps.py; Android Lint's FORMAT pattern is copied from "
             "StringFormatDetector.kt (Apache-2.0)." % s["checks_blind_version"], "",
             "Dropped before counting: %s." % (", ".join("%s %d" % kv for kv in s["dropped"].items()) or "nothing"),
             ""]
    for name, g in s["groups"].items():
        lines += ["## %s: %d rows in %d repositories" % (name, g["rows"], g["repos"]), ""]
        for c in CHECKS:
            lines.append("- %s: %s" % (c, ", ".join("%s %d" % kv for kv in g["checks"][c].items())))
        lines += ["", "| seen by | rows | repos |", "|---|---:|---:|"]
        for k, v in g["seen_by"].items():
            lines.append("| %s | %d | %d |" % (k, v["rows"], v["repos"]))
        lines += ["", "| mistake kind | rows | repos | weblate | pofilter | lint | none |", "|---|---:|---:|---:|---:|---:|---:|"]
        for kind, v in g["by_kind"].items():
            lines.append("| %s | %d | %d | %d | %d | %d | %d |" % (
                kind, v["rows"], v["repos"], v["weblate_flagged"], v["pofilter_flagged"], v["lint_flagged"], v["none"]))
        lines.append("")
    lines += ["## Rows no check sees (formatted first)", ""]
    for e in sorted(s["rows"], key=lambda e: (e["use"] != "formatted", e["kind"], e["app"])):
        if not e["seen_by"]:
            lines.append("- %s | %s %s `%s` | `%s` -> `%s` (%s, %s; weblate %s, lint %s)" % (
                e["kind"], e["app"], e["locale"], e["key"], e["source"].replace("\n", " "),
                e["translation"].replace("\n", " "), e["exception"], e["use"], e["weblate"], e["lint"]))
    return "\n".join(lines) + "\n"


FIELDS = ["app", "repo", "locale", "key", "use", "exception", "kind", "weblate", "pofilter", "lint", "lint_issues",
          "pofilter_message", "seen_by", "source", "translation"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("findings", nargs="?")
    ap.add_argument("--url")
    ap.add_argument("--weblate", default="weblate_format.py.txt")
    ap.add_argument("--translate", default="translate_standard.py.txt")
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args()
    if not a.findings and not a.url:
        ap.error("give findings.csv or --url")
    s = summarise(wb.load_pattern(a.weblate), wb.load_pattern(a.translate, "printf_pat"),
                  wb.read_rows(a.findings, a.url))
    os.makedirs(a.out_dir, exist_ok=True)
    with open(os.path.join(a.out_dir, "checks_blind.json"), "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in s.items() if k != "rows"}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(a.out_dir, "checks_blind_rows.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(s["rows"])
    with open(os.path.join(a.out_dir, "checks_blind.md"), "w", encoding="utf-8") as f:
        f.write(report(s))
    print(report(s))


if __name__ == "__main__":
    main()
