# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made by MV2 of Munim, Inc. with AI agents.
"""Download the two inputs weblate_blind.py reads, pinned to fixed commits.

  weblate_format.py.txt  Weblate's weblate/checks/format.py (GPL-3.0-or-later; only
                         read for its JAVA_MATCH pattern, never imported or shipped)
  taxonomy.py            the census's mistake taxonomy (already in the census repo)

Only missing files are fetched unless --force is given.

Usage: python weblate_deps.py [--dir .] [--force]
"""

import argparse
import os
import urllib.request

WEBLATE_SHA = "975741101388783c5fbd577ae07db61b89ff4c27"
CENSUS_SHA = "7d81669"
FILES = {
    "weblate_format.py.txt":
        "https://raw.githubusercontent.com/WeblateOrg/weblate/%s/weblate/checks/format.py" % WEBLATE_SHA,
    "taxonomy.py":
        "https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/%s/taxonomy.py"
        % CENSUS_SHA,
}


def fetch(dirpath=".", force=False):
    for name, url in FILES.items():
        path = os.path.join(dirpath, name)
        if os.path.exists(path) and not force:
            continue
        with urllib.request.urlopen(url, timeout=60) as r:
            data = r.read()
        with open(path, "wb") as f:
            f.write(data)
        print("%s <- %s (%d bytes)" % (name, url, len(data)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    fetch(a.dir, a.force)


if __name__ == "__main__":
    main()
