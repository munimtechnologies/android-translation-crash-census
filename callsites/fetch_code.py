#!/usr/bin/env python3
"""Downloads the census code this job reuses (census.py 0.3.0, census_fixes.py
0.3.1, census_plurals.py 0.4.0, l10n_guard.py, FormatCheck.java and
bootstrap.py) from the public munimtechnologies/android-translation-crash-census
repository into this folder, pinned to one commit, so the run reads exactly
the repositories and strings census 0.4.0 reads. census_callsites.py and the
hand audit it is scored against (referenced-crash-audit.csv) ship with this
job.

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import json
import os
import sys
import time
import urllib.request

REPO = "munimtechnologies/android-translation-crash-census"
FILES = ["census.py", "census_fixes.py", "census_plurals.py", "l10n_guard.py", "FormatCheck.java",
         "bootstrap.py"]
MARKERS = {"census.py": '__version__ = "0.3.0"', "census_fixes.py": '__version__ = "0.3.1"',
           "census_plurals.py": '__version__ = "0.4.0"'}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "mv2-census-callsites"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tries", type=int, default=5)
    args = parser.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    for attempt in range(args.tries):
        try:
            try:
                sha = json.loads(get("https://api.github.com/repos/%s/commits/main" % REPO))["sha"]
            except Exception as exc:  # API rate limit: fall back to the branch
                print("commit lookup failed (%s); using main" % exc, flush=True)
                sha = "main"
            raw = "https://raw.githubusercontent.com/%s/%s/" % (REPO, sha)
            got = {name: get(raw + name) for name in FILES}
            break
        except Exception as exc:  # network hiccup: try again
            print("fetch failed: %s" % exc, flush=True)
            time.sleep(60)
    else:
        return 1
    for name, marker in MARKERS.items():
        if marker not in got[name].decode("utf-8"):
            print("%s@%s: %s lacks %s" % (REPO, sha[:7], name, marker))
            return 1
    for name, data in got.items():
        with open(os.path.join(here, name), "wb") as f:
            f.write(data)
    with open(os.path.join(here, "census_commit.txt"), "w") as f:
        f.write(sha + "\n")
    print("census code from %s@%s: %s" % (REPO, sha, ", ".join(sorted(got))), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
