#!/usr/bin/env python3
"""Exploratory, not graded: zero-width characters inside Japanese words.

A page summary said DuckPro-Kobra3's Japanese file has zero-width spaces
inside words (お待<U+200B><U+200B>ちください). This counts, in the 33 Japanese files of
the reading-leak false-positive test (population.csv, pinned commits), every
zero-width character (U+200B, U+200C, U+200D, U+2060, and U+FEFF after the
first byte), and how many sit between two Japanese characters. A \\u200b-style
escape counts too (as in .properties files). Nothing is predicted; the counts
decide whether a pre-registered study is worth writing.

  python zw_count.py --pop population.csv --out-dir /out/zw

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

RAW = "https://raw.githubusercontent.com/"
ZW = "​‌‍⁠﻿"
JA = "぀-ヿ㐀-䶿一-鿿"
_ESCAPE = re.compile(r"\\u(200[bBcCdD]|2060|[fF][eE][fF][fF])")
_INSIDE = re.compile("(?<=[%s])[%s]+(?=[%s])" % (JA, ZW, JA))


def unescape(text):
    return _ESCAPE.sub(lambda m: chr(int(m.group(1), 16)), text)


def count(text):
    """(zero-width characters, runs between two Japanese characters, sample lines)."""
    text = unescape(text[1:] if text.startswith("﻿") else text)
    total = sum(text.count(c) for c in ZW)
    inside, samples = 0, []
    for n, line in enumerate(text.split("\n"), 1):
        runs = _INSIDE.findall(line)
        if runs:
            inside += len(runs)
            if len(samples) < 10:
                shown = line.strip()[:200]
                for c in ZW:
                    shown = shown.replace(c, "<U+%04X>" % ord(c))
                samples.append({"line": n, "text": shown})
    return total, inside, samples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pop", default="population.csv")
    parser.add_argument("--out-dir", default="/out/zw")
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    with open(args.pop, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    out = []
    for row in rows:
        url = RAW + "%s/%s/%s" % (row["repo"], row["commit"], urllib.parse.quote(row["path"]))
        req = urllib.request.Request(url, headers={"User-Agent": "mv2-zw-count"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                text = r.read().decode("utf-8", errors="replace").replace("\r\n", "\n")
        except (urllib.error.URLError, OSError) as exc:
            print("%s %s: NOT FETCHED (%s)" % (row["id"], row["path"], exc))
            out.append({"id": row["id"], "fetched": False})
            continue
        total, inside, samples = count(text)
        print("%s %s %s: %d zero-width, %d inside Japanese words"
              % (row["id"], row["repo"], row["path"], total, inside))
        for s in samples:
            print("  line %d: %s" % (s["line"], s["text"]))
        out.append({"id": row["id"], "repo": row["repo"], "path": row["path"], "fetched": True,
                    "zero_width": total, "inside": inside, "samples": samples})
    print("files with a zero-width character inside a Japanese word: %d of %d fetched"
          % (sum(1 for o in out if o.get("inside")), sum(1 for o in out if o["fetched"])))
    with open(os.path.join(args.out_dir, "zw_count.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
