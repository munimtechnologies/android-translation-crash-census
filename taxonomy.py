# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made by MV2 of Munim, Inc. with AI agents.
"""Sort the census's crashing translations by the kind of mistake that broke them.

Reads findings.csv from the Android translation-crash census and, for every
row the JVM rejected whatever the app passes (verdict "crash"), names the
mistake behind the first placeholder java.util.Formatter could not use:

  stray-percent         a % with no argument index, followed by a space,
                        punctuation, the end, or a word (`50% `, `(%1$d%)`,
                        `% ms`, `%Каждую`)
  malformed-index       an index spaced out or misplaced (`% 1 $ s`, `%$1s`)
  conversion-missing    an indexed placeholder with nothing after it (`%1$ `,
                        `%1$` at the end, `%1$ musikspelare`)
  conversion-native     an indexed placeholder followed directly by a letter of
                        another script: the conversion letter was replaced
                        (`%1$с`, `%1$ч`, `%1$د`) or dropped before a word
                        (`%1$的`); Formatter can't tell these apart either
  conversion-invalid    an indexed placeholder followed by a Latin letter
                        Formatter doesn't know (`%1$DH`, `%2$m`, `%2$vs`)
  flag-mismatch         prose read as a flag (`% s`, `100 % sûr`)
  argument-not-passed   an argument index the app doesn't pass (`%2$d`, `%,d` twice)
  wrong-type            a valid placeholder of the wrong type (`%g` for `%d`)
  other                 anything else

Usage: python taxonomy.py findings.csv --out-dir out
       python taxonomy.py --url https://.../findings.csv --out-dir out
"""

import argparse
import collections
import csv
import io
import json
import os
import re
import unicodedata
import urllib.request

VERSION = "0.1.1"

# Formatter's specifier grammar (java.util.Formatter), with ASCII digits only.
PREFIX = re.compile(r"%([0-9]+\$)?([-#+ 0,(<]*)?([0-9]+)?(\.[0-9]+)?([tT])?")
CONVERSIONS = set("bBhHsScCdoxXeEfgGaA%n")
DATE_CONVERSIONS = set("HIklMSLNpzZsQBbhAaCYyjmdeRTrDFc")
# `% 1 $ s`, `%1 $s`, `%$1s`: the index is there but spaced out or in the wrong place.
MALFORMED_INDEX = re.compile(r"%(\s*\$|\s+[0-9]+\s*\$|[0-9]+\s+\$)")

# Letters of other scripts that look like, or transliterate, a Latin conversion letter:
# d (д δ د ד द ड), s (с σ ς س ס स), f (ф φ ف), x (х χ), e (е ε), a (а α), o (о ο).
LOOKALIKES = set("дДδΔدדदड" "сСσςΣسסस" "фФφف" "хХχ" "еЕε" "аАα" "оОο")

KINDS = ["stray-percent", "malformed-index", "conversion-missing", "conversion-native",
         "conversion-invalid", "flag-mismatch", "argument-not-passed", "wrong-type", "other"]


def first_unknown(text):
    """(position, prefix, next character) at the first % Formatter can't read, or None."""
    i = 0
    while True:
        i = text.find("%", i)
        if i < 0:
            return None
        m = PREFIX.match(text, i)
        end = m.end()
        nxt = text[end] if end < len(text) else ""
        if m.group(5):
            valid = nxt in DATE_CONVERSIONS
        else:
            valid = nxt in CONVERSIONS
        if not valid:
            return i, m.group(0), nxt
        i = end + 1


def classify(exception, translation):
    if exception == "MissingFormatArgumentException":
        return "argument-not-passed"
    if exception == "IllegalFormatConversionException":
        return "wrong-type"
    if exception in ("FormatFlagsConversionMismatchException", "IllegalFormatFlagsException"):
        return "flag-mismatch"
    if exception != "UnknownFormatConversionException":
        return "other"
    found = first_unknown(translation)
    if found is None:
        return "other"
    at, prefix, nxt = found
    if MALFORMED_INDEX.match(translation, at):
        return "malformed-index"
    indexed = bool(re.search(r"[0-9]", prefix))
    if not indexed:
        return "stray-percent"
    # `%1$ word`: Formatter reads the space as a flag, but it separates the
    # index from the next word, so the conversion is missing.
    if prefix.endswith(" ") or nxt == "" or not nxt.isalpha():
        return "conversion-missing"
    if nxt.isascii():
        return "conversion-invalid"
    return "conversion-native"


def is_lookalike(ch):
    return ch in LOOKALIKES


def script_of(ch):
    """First word of the character's Unicode name: CYRILLIC, ARABIC, GREEK..."""
    try:
        return unicodedata.name(ch).split()[0]
    except ValueError:
        return "UNKNOWN"


def read_rows(path=None, url=None):
    if url:
        with urllib.request.urlopen(url, timeout=60) as r:
            text = r.read().decode("utf-8")
    else:
        with open(path, encoding="utf-8", newline="") as f:
            text = f.read()
    return list(csv.DictReader(io.StringIO(text, newline="")))


def summarise(rows):
    out = {"taxonomy_version": VERSION, "groups": {}}
    groups = {"all-crash": [r for r in rows if r["verdict"] == "crash"]}
    groups["formatted-crash"] = [r for r in groups["all-crash"] if r["use"] == "formatted"]
    examples = collections.defaultdict(list)
    for name, group in groups.items():
        kinds = collections.Counter()
        repos = collections.defaultdict(set)
        locales = collections.defaultdict(collections.Counter)
        scripts = collections.Counter()
        lookalikes = 0
        for r in group:
            k = classify(r["exception"], r["translation"])
            kinds[k] += 1
            repos[k].add(r["repo"])
            locales[k][r["locale"]] += 1
            if k == "conversion-native":
                letter = first_unknown(r["translation"])[2]
                scripts[script_of(letter)] += 1
                lookalikes += is_lookalike(letter)
            if name == "formatted-crash" and len(examples[k]) < 8:
                examples[k].append({"app": r["app"], "locale": r["locale"], "key": r["key"],
                                    "source": r["source"], "translation": r["translation"]})
        out["groups"][name] = {
            "rows": len(group),
            "repos": len({r["repo"] for r in group}),
            "by_kind": {k: {"rows": kinds[k], "repos": len(repos[k]),
                            "top_locales": dict(locales[k].most_common(8))}
                        for k in KINDS if kinds[k]},
            "conversion_native_scripts": dict(scripts.most_common()),
            "conversion_native_lookalikes": lookalikes,
        }
    out["examples_formatted"] = dict(examples)
    return out


def report(s):
    lines = ["# What kind of mistake breaks each crashing translation", "",
             "taxonomy.py %s (MV2 of Munim, Inc., made with AI agents)." % s["taxonomy_version"], ""]
    for name, g in s["groups"].items():
        lines += ["## %s: %d rows in %d repositories" % (name, g["rows"], g["repos"]), "",
                  "| kind | rows | repositories | top languages |", "|---|---:|---:|---|"]
        for k, v in g["by_kind"].items():
            tops = ", ".join("%s %d" % kv for kv in v["top_locales"].items())
            lines.append("| %s | %d | %d | %s |" % (k, v["rows"], v["repos"], tops))
        if g["conversion_native_scripts"]:
            lines += ["", "Scripts of the letters right after an indexed placeholder: " + ", ".join(
                "%s %d" % kv for kv in g["conversion_native_scripts"].items()),
                      "%d of them look like or transliterate a Latin conversion letter "
                      "(Cyrillic с for s, Greek δ for d...)." % g["conversion_native_lookalikes"]]
        lines.append("")
    lines += ["## Examples (formatted strings)", ""]
    for k, ex in s["examples_formatted"].items():
        lines.append("- **%s**: " % k + "; ".join(
            "%s %s `%s` -> `%s`" % (e["app"], e["locale"], e["source"], e["translation"]) for e in ex[:4]))
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
    with open(os.path.join(a.out_dir, "taxonomy.json"), "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=1)
    with open(os.path.join(a.out_dir, "taxonomy.md"), "w", encoding="utf-8") as f:
        f.write(report(s))
    print(report(s))


if __name__ == "__main__":
    main()
