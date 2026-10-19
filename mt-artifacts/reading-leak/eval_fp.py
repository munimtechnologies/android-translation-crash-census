#!/usr/bin/env python3
"""Grades the false-positive test of l10n-guard 0.11.0's reading-leak rule
written before the run (census mt-artifacts/reading-leak/FP-PREREG.md).

The population (population.csv) is 33 Japanese translation files that contain
a fullwidth number sign ＃, found by Sourcegraph keyword search, at the commits
Sourcegraph had indexed: 5 known to ship katakana readings between ＃ signs
("leak") and 28 that use ＃ for other things ("other"). The rule is taken
from the released v0.11.0 file and run on every line of every file. This is
stricter than the shipped check, which also skips a string whose source has a
number sign, so a line-level miss here is a miss there too. A match right
after a quote, '=', ':' or '>' (the start of a value) is listed apart, since
the shipped check sees nothing before the sign there.

  F0 all 33 files fetch at their pinned commits.
  F1 the rule matches exactly the expected lines: 18 nostrmo, 1 and 2 in the
     two NetEase Meeting files, 3 NocoBase, 1 DuckPro-Kobra3 (25 lines), and
     no line in the 28 other files.
  F2 the 28 other files hold at least 80 lines with ＃, so the test has ＃
     to bite on.
  F3 (graded by hand, from lines.csv): every matched line is a reading leak.

  python eval_fp.py --pop population.csv --out-dir /out/fp

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

RAW = "https://raw.githubusercontent.com/"
GUARD_URL = RAW + "munimtechnologies/l10n-guard/v0.11.0/l10n_guard.py"
PREREG_PATTERN = r"(?<=[^\s＃])＃[ァ-ヺー]+＃"
SIGN = "＃"
# A ＃ followed by katakana, closed or not: listed for reading, not graded.
KATAKANA_AFTER_SIGN = re.compile(r"＃[ァ-ヺー]")
VALUE_START = "\"'=:>`"
MIN_OTHER_SIGN_LINES = 80


def fetch(url):
    """(bytes, text), or (None, reason) when the file can't be fetched."""
    req = urllib.request.Request(url, headers={"User-Agent": "mv2-l10n-guard-eval"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
    except urllib.error.HTTPError as exc:
        return None, "HTTP %d" % exc.code
    except (urllib.error.URLError, OSError) as exc:
        return None, "%s: %s" % (type(exc).__name__, exc)
    return data, data.decode("utf-8-sig", errors="replace").replace("\r\n", "\n").replace("\r", "\n")


def load_rule(path):
    """(version, compiled rule) from an l10n_guard.py file."""
    spec = importlib.util.spec_from_file_location("guard_fp", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.__version__, module._READING_LEAK_RE


def read_population(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def scan(text, rule):
    """Lines with ＃, lines the rule matches, and lines with ＃ then katakana.

    A match right after a quote, '=', ':' or '>' is at the start of a value,
    where the shipped check (which sees the value alone) has nothing before
    the sign; those are listed as value_start and not counted as matches."""
    sign_lines = 0
    rule_lines, value_start, katakana_lines = [], [], []
    for n, line in enumerate(text.split("\n"), 1):
        if SIGN not in line:
            continue
        sign_lines += 1
        found, at_start = [], []
        for m in rule.finditer(line):
            (at_start if line[m.start() - 1] in VALUE_START else found).append(m.group())
        if found:
            rule_lines.append({"line": n, "matches": found, "text": line.strip()[:300]})
        if at_start:
            value_start.append({"line": n, "matches": at_start, "text": line.strip()[:300]})
        if KATAKANA_AFTER_SIGN.search(line):
            katakana_lines.append({"line": n, "text": line.strip()[:300]})
    return {"sign_lines": sign_lines, "rule_lines": rule_lines, "value_start": value_start,
            "katakana_after_sign": katakana_lines}


def grade(results):
    """[(id, text, held, value)] for F0-F2."""
    missing = [r["id"] for r in results if not r["fetched"]]
    wrong = ["%s expected %d, matched %d" % (r["id"], r["expected_rule_lines"], len(r["rule_lines"]))
             for r in results if r["fetched"] and len(r["rule_lines"]) != r["expected_rule_lines"]]
    leak = [r for r in results if r["group"] == "leak"]
    other = [r for r in results if r["group"] == "other"]
    other_sign = sum(r["sign_lines"] for r in other if r["fetched"])
    return [
        ("F0", "all %d files fetch at their pinned commits" % len(results), not missing,
         "%d fetched; missing %s" % (len(results) - len(missing), missing or "none")),
        ("F1", "the rule matches exactly the expected lines in the %d known files and none in the "
               "%d others" % (len(leak), len(other)), not missing and not wrong,
         "known files %d lines (expected %d), other files %d lines; differences %s"
         % (sum(len(r["rule_lines"]) for r in leak), sum(r["expected_rule_lines"] for r in leak),
            sum(len(r["rule_lines"]) for r in other), wrong or "none")),
        ("F2", "the %d other files hold at least %d lines with ＃" % (len(other), MIN_OTHER_SIGN_LINES),
         not missing and other_sign >= MIN_OTHER_SIGN_LINES,
         "%d lines with ＃ in the other files" % other_sign),
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pop", default="population.csv")
    parser.add_argument("--out-dir", default="/out/fp")
    parser.add_argument("--guard-url", default=GUARD_URL)
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    data, text = fetch(args.guard_url)
    if data is None:
        print("l10n-guard v0.11.0 not found at %s (%s)" % (args.guard_url, text))
        return 1
    guard_path = os.path.join(args.out_dir, "l10n_guard_v0.11.0.py")
    with open(guard_path, "wb") as f:
        f.write(data)
    version, rule = load_rule(guard_path)
    print("l10n-guard %s, sha256 %s, rule %s" % (version, hashlib.sha256(data).hexdigest()[:16], rule.pattern))
    if version != "0.11.0" or rule.pattern != PREREG_PATTERN:
        print("refusing: not the pre-registered release (version %s, pattern %s)" % (version, rule.pattern))
        return 1

    results = []
    for row in read_population(args.pop):
        url = RAW + "%s/%s/%s" % (row["repo"], row["commit"], urllib.parse.quote(row["path"]))
        res = {"id": row["id"], "group": row["group"], "repo": row["repo"], "commit": row["commit"],
               "path": row["path"], "url": url, "expected_rule_lines": int(row["expected_rule_lines"]),
               "fetched": False, "reason": "", "sha256_16": "", "bytes": 0, "lines": 0,
               "sign_lines": 0, "rule_lines": [], "value_start": [], "katakana_after_sign": []}
        fdata, ftext = fetch(url)
        if fdata is None:
            res["reason"] = ftext
            print("%s %s %s: NOT FETCHED (%s)" % (row["id"], row["repo"], row["path"], ftext))
        else:
            res.update(scan(ftext, rule))
            res.update(fetched=True, sha256_16=hashlib.sha256(fdata).hexdigest()[:16],
                       bytes=len(fdata), lines=ftext.count("\n") + 1,
                       replacement_chars=ftext.count("�"))
            print("%s %s %s: %d lines, %d with ＃, %d matched (expected %d), %d with ＃ then katakana; "
                  "sha256 %s" % (row["id"], row["repo"], row["path"], res["lines"], res["sign_lines"],
                                 len(res["rule_lines"]), res["expected_rule_lines"],
                                 len(res["katakana_after_sign"]), res["sha256_16"]))
            for m in res["rule_lines"]:
                print("  match line %d: %s" % (m["line"], m["text"]))
            for m in res["value_start"]:
                print("  value-start line %d: %s" % (m["line"], m["text"]))
        results.append(res)

    checks = grade(results)
    for name, text, held, value in checks:
        print("%s %s: %s (%s)" % (name, "HELD" if held else "FAILED", text, value))
    print("F3 is graded by hand from lines.csv")
    out = {"guard": version, "guard_sha256_16": hashlib.sha256(data).hexdigest()[:16],
           "rule": rule.pattern, "files": results,
           "predictions": [{"id": n, "text": t, "held": h, "value": v} for n, t, h, v in checks]}
    with open(os.path.join(args.out_dir, "fp_eval.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    with open(os.path.join(args.out_dir, "lines.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "group", "repo", "path", "line", "kind", "text"])
        for r in results:
            for m in r["rule_lines"]:
                w.writerow([r["id"], r["group"], r["repo"], r["path"], m["line"], "rule", m["text"]])
            for m in r["value_start"]:
                w.writerow([r["id"], r["group"], r["repo"], r["path"], m["line"], "value-start", m["text"]])
            for m in r["katakana_after_sign"]:
                w.writerow([r["id"], r["group"], r["repo"], r["path"], m["line"], "katakana-after-sign",
                            m["text"]])
    os.remove(guard_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
