# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made by MV2 of Munim, Inc. with AI agents.
"""Would Weblate's own format check have caught the census's crashing translations?

Weblate turns its "Java format" check (java_printf_format) on by itself for Android
string resources. It pulls the placeholders out of the source and the translation
with its JAVA_MATCH pattern and fails the translation when the two lists differ.
This runs that check over every row the census found crashing in java.util.Formatter
and reports which rows it flags and which it can't see.

The pattern is read from Weblate's real weblate/checks/format.py (weblate_deps.py pins
the commit), never copied: ast finds `JAVA_MATCH = re.compile(...)` and compiles the
same string with the same flags. The comparison follows BaseFormatCheck.check_format
at that commit: placeholders are group 1 of each match, apostrophes removed, a bare
"%" (from %%) dropped; if any source placeholder has no "$" index the lists are
compared in order, else as multisets. For plural items Weblate may forgive missing
(never extra) placeholders in some forms, so plural rows are checked both ways.

Weblate's check is a warning unless a project enforces it, so "flagged" means a
translator or reviewer was shown it, not that it was blocked.

Usage: python weblate_blind.py findings.csv --weblate weblate_format.py.txt --out-dir out
       python weblate_blind.py --url https://.../findings.csv --weblate ... --out-dir out
"""

import argparse
import ast
import collections
import csv
import io
import json
import os
import re
import urllib.request

import taxonomy

VERSION = "0.1.0"

# Rows the census has since cleared by hand (see data/verified-cases.csv).
EXCLUDE_REPOS = ["apps-android-wikipedia"]
DATE_PLACEHOLDER = re.compile(r"%([0-9]+\$)?[tT]")


def _flags(node):
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _flags(node.left) | _flags(node.right)
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "re":
        return getattr(re, node.attr)
    raise ValueError("unexpected re flag expression: %s" % ast.dump(node))


def load_pattern(path, name="JAVA_MATCH"):
    """Compile Weblate's `name = re.compile(<str>, <flags>)` from its source file."""
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else [getattr(node, "target", None)]
        if (isinstance(node, (ast.Assign, ast.AnnAssign)) and len(targets) == 1
                and isinstance(targets[0], ast.Name) and targets[0].id == name):
            call = node.value
            if not (isinstance(call, ast.Call) and isinstance(call.args[0], ast.Constant)):
                raise ValueError("%s is not re.compile(<literal>, ...)" % name)
            flags = 0
            for arg in call.args[1:]:
                flags |= _flags(arg)
            for kw in call.keywords:
                if kw.arg == "flags":
                    flags |= _flags(kw.value)
            return re.compile(call.args[0].value, flags)
    raise ValueError("%s not found in %s" % (name, path))


def extract(regexp, text):
    """Weblate's printf placeholders: group 1, apostrophes removed, bare % dropped."""
    out = []
    for m in regexp.finditer(text):
        s = m.group(1)
        if "'" in s:
            s = s.replace("'", "")
        if s != "%":
            out.append(s)
    return out


def check(regexp, source, target, ignore_missing=False):
    """None if Weblate passes the translation, else {"missing": [...], "extra": [...]}."""
    if not source or not target:
        return None
    src, tgt = extract(regexp, source), extract(regexp, target)
    in_order = True
    if src:
        in_order = any("$" not in x and x != "%" for x in src)
    missing, extra = [], []
    if not in_order:
        a, b = collections.Counter(src), collections.Counter(tgt)
        if a != b:
            missing, extra = sorted(a - b), sorted(b - a)
    elif src != tgt:
        for x, y in zip(src, tgt):
            if x != y:
                missing.append(x)
                extra.append(y)
        missing.extend(src[len(tgt):])
        extra.extend(tgt[len(src):])
    if ignore_missing and missing and not extra:
        return None
    if missing or extra:
        return {"missing": missing, "extra": extra}
    return None


def verdict(regexp, row):
    """flagged / unflagged / plural-dependent, plus Weblate's missing/extra lists."""
    strict = check(regexp, row["source"], row["translation"])
    if "[" not in row["key"]:
        return ("flagged" if strict else "unflagged"), strict
    lenient = check(regexp, row["source"], row["translation"], ignore_missing=True)
    if strict and lenient:
        return "flagged", strict
    if not strict:
        return "unflagged", None
    return "plural-dependent", strict


def read_rows(path=None, url=None):
    if url:
        with urllib.request.urlopen(url, timeout=60) as r:
            text = r.read().decode("utf-8")
    else:
        with open(path, encoding="utf-8", newline="") as f:
            text = f.read()
    return list(csv.DictReader(io.StringIO(text, newline="")))


def select(rows, exclude_repos=EXCLUDE_REPOS):
    """Crash rows minus those cleared by hand; returns (kept, dropped counts)."""
    kept, dropped = [], collections.Counter()
    for r in rows:
        if r["verdict"] != "crash":
            continue
        if any(x in r["repo"] for x in exclude_repos):
            dropped["cleared repo"] += 1
        elif r["locale"] == "qq":
            dropped["translator notes (qq)"] += 1
        elif DATE_PLACEHOLDER.search(r["translation"]) and not DATE_PLACEHOLDER.search(r["source"]):
            dropped["date conversion (%t), wrong output not crash"] += 1
        else:
            kept.append(r)
    return kept, dropped


def summarise(regexp, rows, exclude_repos=EXCLUDE_REPOS):
    kept, dropped = select(rows, exclude_repos)
    out = {"weblate_blind_version": VERSION, "dropped": dict(dropped), "groups": {}, "rows": []}
    for r in kept:
        v, diff = verdict(regexp, r)
        out["rows"].append(dict(app=r["app"], repo=r["repo"], locale=r["locale"], key=r["key"],
                                use=r["use"], exception=r["exception"],
                                kind=taxonomy.classify(r["exception"], r["translation"]),
                                weblate=v, missing=" ".join((diff or {}).get("missing", [])),
                                extra=" ".join((diff or {}).get("extra", [])),
                                source=r["source"], translation=r["translation"]))
    groups = {"all-crash": out["rows"],
              "formatted-crash": [e for e in out["rows"] if e["use"] == "formatted"]}
    for name, group in groups.items():
        g = {"rows": len(group), "repos": len({e["repo"] for e in group}), "weblate": {}, "by_kind": {}}
        for v in ("flagged", "unflagged", "plural-dependent"):
            sel = [e for e in group if e["weblate"] == v]
            g["weblate"][v] = {"rows": len(sel), "repos": len({e["repo"] for e in sel})}
        for kind in taxonomy.KINDS:
            sel = [e for e in group if e["kind"] == kind]
            if sel:
                c = collections.Counter(e["weblate"] for e in sel)
                g["by_kind"][kind] = {"rows": len(sel), "repos": len({e["repo"] for e in sel}),
                                      "flagged": c["flagged"], "unflagged": c["unflagged"],
                                      "plural_dependent": c["plural-dependent"],
                                      "unflagged_repos": len({e["repo"] for e in sel
                                                              if e["weblate"] == "unflagged"})}
        out["groups"][name] = g
    return out


def report(s):
    lines = ["# Which crashing translations Weblate's own format check can see", "",
             "weblate_blind.py %s (MV2 of Munim, Inc., made with AI agents). Pattern: Weblate's JAVA_MATCH, "
             "read from weblate/checks/format.py at the commit pinned in weblate_deps.py." % s["weblate_blind_version"],
             "", "Dropped before counting: %s." % (
                 ", ".join("%s %d" % kv for kv in s["dropped"].items()) or "nothing"), ""]
    for name, g in s["groups"].items():
        w = g["weblate"]
        lines += ["## %s: %d rows in %d repositories" % (name, g["rows"], g["repos"]), "",
                  "Flagged %d (%d repos), not flagged %d (%d repos), plural-dependent %d." % (
                      w["flagged"]["rows"], w["flagged"]["repos"], w["unflagged"]["rows"],
                      w["unflagged"]["repos"], w["plural-dependent"]["rows"]), "",
                  "| mistake kind | rows | flagged | not flagged | plural-dependent | repos not flagged |",
                  "|---|---:|---:|---:|---:|---:|"]
        for kind, v in g["by_kind"].items():
            lines.append("| %s | %d | %d | %d | %d | %d |" % (kind, v["rows"], v["flagged"], v["unflagged"],
                                                           v["plural_dependent"], v["unflagged_repos"]))
        lines.append("")
    lines += ["## Rows Weblate's check passes (formatted first)", ""]
    for e in sorted(s["rows"], key=lambda e: (e["use"] != "formatted", e["kind"], e["app"])):
        if e["weblate"] == "unflagged":
            lines.append("- %s | %s %s `%s` | `%s` -> `%s` (%s, %s)" % (
                e["kind"], e["app"], e["locale"], e["key"], e["source"].replace("\n", " "),
                e["translation"].replace("\n", " "), e["exception"], e["use"]))
    return "\n".join(lines) + "\n"


FIELDS = ["app", "repo", "locale", "key", "use", "exception", "kind", "weblate", "missing", "extra",
          "source", "translation"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("findings", nargs="?")
    ap.add_argument("--url")
    ap.add_argument("--weblate", default="weblate_format.py.txt")
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args()
    if not a.findings and not a.url:
        ap.error("give findings.csv or --url")
    s = summarise(load_pattern(a.weblate), read_rows(a.findings, a.url))
    os.makedirs(a.out_dir, exist_ok=True)
    with open(os.path.join(a.out_dir, "weblate_blind.json"), "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in s.items() if k != "rows"}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(a.out_dir, "weblate_blind_rows.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(s["rows"])
    with open(os.path.join(a.out_dir, "weblate_blind.md"), "w", encoding="utf-8") as f:
        f.write(report(s))
    print(report(s))


if __name__ == "__main__":
    main()
