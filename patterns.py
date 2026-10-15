# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made by MV2 of Munim, Inc. with AI agents.
"""Tag the census's crashing translations with the translator's step that broke them.

taxonomy.py names what java.util.Formatter choked on (a stray %, a bad index...).
This names how the mistake got into the translation, comparing each translation
with its English source. A row gets at most one tag:

  escape-dropped        the source escapes a literal percent sign as %% and the
                        translation writes a single % (`(%1$d%%)` -> `(%1$d%)`)
  percent-sign-added    the source has no percent sign at all, but the
                        translation writes one after a number or a placeholder
                        (`25 percent` -> `25%`, `%1$d percent` -> `%1$d% ...`);
                        spells_percent says whether the English wrote the word
  extra-placeholder     the translation has more unindexed placeholders than
                        the source (`%d items` -> `%d ... %d`), so Formatter
                        runs out of arguments; plural and one_form_locale say
                        whether it is a plural item in a language with a
                        single plural form (both forms pasted into one)

Usage: python patterns.py findings.csv --out-dir out
       python patterns.py --url https://.../findings.csv --out-dir out
"""

import argparse
import collections
import csv
import io
import json
import os
import re
import urllib.request

VERSION = "0.1.0"

# A valid Formatter placeholder (same grammar as taxonomy.py), conversion included.
PLACEHOLDER = re.compile(r"%([0-9]+\$)?([-#+ 0,(<]*)?([0-9]+)?(\.[0-9]+)?([tT])?([bBhHsScCdoxXeEfgGaA%n])")
# A % used as a percent sign: after a digit or a placeholder's d/f/s, maybe one space,
# and not the start of an indexed placeholder or of a bare %s / %d.
PERCENT_USE = re.compile(
    r"(?:\d|%(?:[0-9]+\$)?[-#+ 0,(]*[0-9]*(?:\.[0-9]+)?[dfs])[   ]?"
    r"%(?![0-9]+\$|[sd](?![^\W\d_]))")
PERCENT_WORD = re.compile(r"per ?cent|percentage", re.I)
# Languages whose plurals have only the "other" form (CLDR); "in" is Android's old code for Indonesian.
ONE_FORM = {"ja", "ko", "zh", "vi", "th", "id", "in", "ms", "lo", "my", "km", "jv", "su", "bo", "yue"}

TAGS = ["escape-dropped", "percent-sign-added", "extra-placeholder"]


def percent_uses(text):
    return len(PERCENT_USE.findall(text.replace("%%", "")))


def unindexed(text):
    """Placeholders that take the next argument: no index, not %% or %n."""
    return sum(1 for m in PLACEHOLDER.finditer(text)
               if not m.group(1) and m.group(6) not in "%n" and "<" not in (m.group(2) or ""))


def base_language(locale):
    return re.split(r"[-_+]", locale.replace("b+", "", 1))[0].lower()


def tag(row):
    """(tag, details) for one findings row, or (None, {})."""
    source, translation = row["source"], row["translation"]
    if percent_uses(translation):
        if "%%" in source:
            return "escape-dropped", {}
        if not percent_uses(source):
            return "percent-sign-added", {"spells_percent": bool(PERCENT_WORD.search(source))}
    if unindexed(translation) > unindexed(source):
        return "extra-placeholder", {"plural": "[" in row["key"],
                                     "one_form_locale": base_language(row["locale"]) in ONE_FORM}
    return None, {}


def read_rows(path=None, url=None):
    if url:
        with urllib.request.urlopen(url, timeout=60) as r:
            text = r.read().decode("utf-8")
    else:
        with open(path, encoding="utf-8", newline="") as f:
            text = f.read()
    return list(csv.DictReader(io.StringIO(text, newline="")))


def summarise(rows):
    out = {"patterns_version": VERSION, "groups": {}, "tagged": []}
    crash = [r for r in rows if r["verdict"] == "crash"]
    groups = {"all-crash": crash, "formatted-crash": [r for r in crash if r["use"] == "formatted"]}
    for name, group in groups.items():
        counts = collections.Counter()
        repos = collections.defaultdict(set)
        flags = collections.defaultdict(collections.Counter)
        for r in group:
            t, details = tag(r)
            if not t:
                continue
            counts[t] += 1
            repos[t].add(r["repo"])
            for k, v in details.items():
                flags[t][k] += bool(v)
            if name == "all-crash":
                out["tagged"].append(dict(tag=t, app=r["app"], repo=r["repo"], locale=r["locale"],
                                          key=r["key"], use=r["use"], source=r["source"],
                                          translation=r["translation"], **details))
        out["groups"][name] = {
            "rows": len(group),
            "repos": len({r["repo"] for r in group}),
            "by_tag": {t: {"rows": counts[t], "repos": len(repos[t]), "flags": dict(flags[t])}
                       for t in TAGS if counts[t]},
        }
    return out


def report(s):
    lines = ["# How the mistake got into each crashing translation", "",
             "patterns.py %s (MV2 of Munim, Inc., made with AI agents)." % s["patterns_version"], ""]
    for name, g in s["groups"].items():
        lines += ["## %s: %d rows in %d repositories" % (name, g["rows"], g["repos"]), "",
                  "| tag | rows | repositories | flags (rows) |", "|---|---:|---:|---|"]
        for t, v in g["by_tag"].items():
            fl = ", ".join("%s %d" % kv for kv in v["flags"].items())
            lines.append("| %s | %d | %d | %s |" % (t, v["rows"], v["repos"], fl))
        lines.append("")
    lines += ["## Tagged rows (formatted first)", ""]
    for e in sorted(s["tagged"], key=lambda e: (e["use"] != "formatted", e["tag"], e["app"])):
        lines.append("- %s | %s %s `%s` | `%s` -> `%s` (%s)" % (
            e["tag"], e["app"], e["locale"], e["key"], e["source"].replace("\n", " "),
            e["translation"].replace("\n", " "), e["use"]))
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("findings", nargs="?")
    ap.add_argument("--url")
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args()
    if not a.findings and not a.url:
        ap.error("give findings.csv or --url")
    s = summarise(read_rows(a.findings, a.url))
    os.makedirs(a.out_dir, exist_ok=True)
    with open(os.path.join(a.out_dir, "patterns.json"), "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=1)
    with open(os.path.join(a.out_dir, "patterns.md"), "w", encoding="utf-8") as f:
        f.write(report(s))
    print(report(s))


if __name__ == "__main__":
    main()
