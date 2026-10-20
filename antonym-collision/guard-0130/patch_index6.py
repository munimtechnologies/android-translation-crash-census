#!/usr/bin/env python3
"""Updates the census README's Sub-studies index after the second held-out
test of the antonym-collision warning: extends the antonym-collision bullet
with its result and a link to HOLDOUT2-RESULTS.md. Fetches README.md from
main, makes one exact once-only change, and writes the patched file to
--out-dir. If the anchor is missing, or the README already has the change,
nothing is written and the exit code is 1.

  python patch_index6.py --out-dir /out/census

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import hashlib
import os
import sys
import urllib.request

BASE = "https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/main/"

END_LINE = ("  in advance for that word class, is [pre-registered](antonym-collision/HOLDOUT2-PREREG.md).\n"
            "\n## Method\n")
END_NEW = ("  in advance for that word class, is [pre-registered](antonym-collision/HOLDOUT2-PREREG.md). It raised\n"
           "  42 warnings in four of the five (Mattermost's English file has a layout the check can't read yet);\n"
           "  AI agents graded all 36 outside that class real and 5 of its 6 not defects (Russian, Ukrainian and\n"
           "  Finnish use one verb for both directions), so l10n-guard 0.13.0 drops the class\n"
           "  ([results](antonym-collision/HOLDOUT2-RESULTS.md)).\n"
           "\n## Method\n")


class PatchError(Exception):
    pass


def fetch(path):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "mv2-census-patch"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8").replace("\r\n", "\n")


def patch_readme(text):
    if "HOLDOUT2-RESULTS" in text:
        raise PatchError("README.md already links HOLDOUT2-RESULTS")
    if "## Sub-studies" not in text:
        raise PatchError("README.md has no Sub-studies section")
    count = text.count(END_LINE)
    if count != 1:
        raise PatchError("expected 1 end-of-bullet anchor, found %d" % count)
    return text.replace(END_LINE, END_NEW)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="/out/census")
    args = parser.parse_args()
    path = "README.md"
    original = fetch(path)
    try:
        text = patch_readme(original)
    except PatchError as exc:
        print("%s: patch failed, not written: %s" % (path, exc))
        return 1
    write(os.path.join(args.out_dir, path), text)
    for name, t in (("before", original), ("after", text)):
        data = t.encode("utf-8")
        print("%s %s: %d bytes, sha256 %s" % (path, name, len(data),
                                             hashlib.sha256(data).hexdigest()[:16]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
