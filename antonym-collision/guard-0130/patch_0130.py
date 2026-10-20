#!/usr/bin/env python3
"""Builds l10n-guard 0.13.0 from the 0.12.0 on main in the
munimtechnologies/l10n-guard repository. Change:

- antonym-collision no longer uses the upload/download word class. The
  census's antonym-collision/HOLDOUT2-PREREG.md fixed this in advance: if
  fewer than half of the graded upload/download warnings on five new projects
  were real (H3), 0.13.0 drops the class. H3 held, 1 of 6
  (antonym-collision/HOLDOUT2-RESULTS.md): in Russian, Ukrainian and Finnish,
  as in French and Arabic before, one word covers both directions.

Nothing is written unless every anchor is found the expected number of times.

  python patch_0130.py --out-dir /out/0130

Writes l10n_guard.py and README.md (patched), action.yml and the tests on
main, and test_0130.py, to --out-dir; the unpatched 0.12.0 to
--out-dir/baseline/.

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import hashlib
import os
import shutil
import sys
import urllib.request

BASE = "https://raw.githubusercontent.com/munimtechnologies/l10n-guard/main/"
TESTS = ("test_l10n_guard.py", "test_android_text_052.py", "test_java_060.py",
         "test_qt_070.py", "test_071.py", "test_072.py", "test_080.py", "test_090.py",
         "test_0100.py", "test_0110.py", "test_0120.py")

UPLOAD = '    "UPLOAD": ("upload uploaded", "download downloaded"),\n'
COMMENT = '# ("Visible" / "Hidden") are missed.\n_ANTONYM_CLASSES = {\n'
COMMENT_NEW = ('# ("Visible" / "Hidden") are missed. 0.13.0 drops upload/download: in French,\n'
               '# Arabic, Russian, Ukrainian and Finnish one word covers both directions, so\n'
               '# its warnings were mostly not defects (the census\'s\n'
               '# antonym-collision/HOLDOUT2-RESULTS.md).\n'
               '_ANTONYM_CLASSES = {\n')

CENSUS = "https://github.com/munimtechnologies/android-translation-crash-census/blob/main/"
README_PREREG = ("  [pre-registration of this check](" + CENSUS + "antonym-collision/GUARD-PREREG.md)).\n")
README_NEW = (
    "  [pre-registration of this check](" + CENSUS + "antonym-collision/GUARD-PREREG.md),\n"
    "  [test results](" + CENSUS + "antonym-collision/GUARD-RESULTS.md)). Since 0.13.0 the upload/download\n"
    "  class is left out, as fixed in advance by a\n"
    "  [second held-out test](" + CENSUS + "antonym-collision/HOLDOUT2-RESULTS.md): in French, Arabic,\n"
    "  Russian, Ukrainian and Finnish one word covers both directions, so 11 of the 12 warnings graded in\n"
    "  that class were not defects, while all 49 graded in the other classes were real (graded by AI\n"
    "  agents, not native speakers). 39 word classes remain.\n")


class PatchError(Exception):
    pass


def fetch(name):
    req = urllib.request.Request(BASE + name, headers={"User-Agent": "mv2-l10n-guard-patch"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8").replace("\r\n", "\n")


def replace(text, old, new, times=1):
    count = text.count(old)
    if count != times:
        raise PatchError("expected %d match(es), found %d: %r" % (times, count, old[:60]))
    return text.replace(old, new)


def patch_guard(guard):
    guard = replace(guard, '__version__ = "0.12.0"', '__version__ = "0.13.0"')
    guard = replace(guard, UPLOAD, "")
    guard = replace(guard, COMMENT, COMMENT_NEW)
    if "upload" in guard[guard.find("_ANTONYM_CLASSES = {"):guard.find("_ANTONYMS = {}")]:
        raise PatchError("upload is still in the word classes")
    compile(guard, "l10n_guard.py", "exec")
    return guard


def patch_readme(readme):
    if "HOLDOUT2-RESULTS" in readme:
        raise PatchError("README.md already links HOLDOUT2-RESULTS")
    if "l10n-guard@v0.12.0" not in readme:
        raise PatchError("no l10n-guard@v0.12.0 in README.md")
    readme = replace(readme, README_PREREG, README_NEW)
    return readme.replace("l10n-guard@v0.12.0", "l10n-guard@v0.13.0")


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="/out/0130")
    args = parser.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    original = fetch("l10n_guard.py")
    try:
        guard = patch_guard(original)
        readme = patch_readme(fetch("README.md"))
    except PatchError as exc:
        print("patch failed, nothing written: %s" % exc)
        return 1
    os.makedirs(os.path.join(args.out_dir, "baseline"), exist_ok=True)
    write(os.path.join(args.out_dir, "baseline", "l10n_guard.py"), original)
    write(os.path.join(args.out_dir, "l10n_guard.py"), guard)
    write(os.path.join(args.out_dir, "README.md"), readme)
    write(os.path.join(args.out_dir, "action.yml"), fetch("action.yml"))
    for name in TESTS:
        write(os.path.join(args.out_dir, name), fetch(name))
    shutil.copy(os.path.join(here, "test_0130.py"), args.out_dir)
    for name, text in (("l10n_guard.py 0.12.0", original), ("l10n_guard.py 0.13.0", guard)):
        data = text.encode("utf-8")
        print("%s: %d bytes, sha256 %s" % (name, len(data), hashlib.sha256(data).hexdigest()[:16]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
