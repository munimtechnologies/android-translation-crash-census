# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made by MV2 of Munim, Inc. with AI agents.
"""Download the inputs checks_blind.py reads, pinned to fixed commits.

  weblate_format.py.txt        Weblate's weblate/checks/format.py (GPL-3.0-or-later; read for
                               its JAVA_MATCH pattern only, never imported or shipped)
  translate_standard.py.txt    translate-toolkit's translate/filters/checks/standard.py
                               (GPL-2.0-or-later; read for its printf_pat pattern only)
  StringFormatDetector.kt.txt  Android Lint's StringFormatDetector.kt (Apache-2.0; the test
                               compares its FORMAT pattern with the copy in checks_blind.py)
  weblate_blind.py, taxonomy.py   the census's own modules (Apache-2.0), pinned too

Only missing files are fetched unless --force is given. The Lint file comes from
android.googlesource.com, which serves sources base64-encoded with ?format=TEXT; the
branch is mirror-goog-studio-main (blob d9d20692b334fd2c524aba1377661eedd3ed7f69 when
this was written, 2026-10-15). A failed Lint download is reported, not fatal: the Lint
pattern test is skipped in that case.

Usage: python checks_deps.py [--dir .] [--force]
"""

import argparse
import base64
import os
import urllib.request

TRANSLATE_SHA = "8298558c6078e4f7734a08618b15d8bd088ab3b6"   # 2026-08-14, after the checks refactor
CENSUS_SHA = "54c1089"                                       # weblate_blind.py 0.1.0
LINT_BRANCH = "refs/heads/mirror-goog-studio-main"
LINT_PATH = "lint/libs/lint-checks/src/main/java/com/android/tools/lint/checks/StringFormatDetector.kt"

FILES = {
    "translate_standard.py.txt":
        "https://raw.githubusercontent.com/translate/translate/%s/translate/filters/checks/standard.py"
        % TRANSLATE_SHA,
    "weblate_blind.py":
        "https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/%s/weblate_blind.py"
        % CENSUS_SHA,
}
LINT_FILE = "StringFormatDetector.kt.txt"
LINT_URL = "https://android.googlesource.com/platform/tools/base/+/%s/%s?format=TEXT" % (LINT_BRANCH, LINT_PATH)


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "android-translation-crash-census (MV2, Munim, Inc.)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def fetch(dirpath=".", force=False):
    import weblate_deps   # ships next to this file in the census repo
    weblate_deps.fetch(dirpath, force)   # weblate_format.py.txt + taxonomy.py
    for name, url in FILES.items():
        path = os.path.join(dirpath, name)
        if os.path.exists(path) and not force:
            continue
        data = _get(url)
        with open(path, "wb") as f:
            f.write(data)
        print("%s <- %s (%d bytes)" % (name, url, len(data)))
    path = os.path.join(dirpath, LINT_FILE)
    if force or not os.path.exists(path):
        try:
            data = base64.b64decode(_get(LINT_URL))
        except Exception as e:  # noqa: BLE001 - report and go on; the Lint source test skips
            print("%s: download failed (%s)" % (LINT_FILE, e))
            return
        with open(path, "wb") as f:
            f.write(data)
        print("%s <- %s (%d bytes)" % (LINT_FILE, LINT_URL, len(data)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    fetch(a.dir, a.force)


if __name__ == "__main__":
    main()
