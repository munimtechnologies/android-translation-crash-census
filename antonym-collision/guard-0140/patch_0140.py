#!/usr/bin/env python3
"""Builds l10n-guard 0.14.0 from the 0.13.0 on main in the
munimtechnologies/l10n-guard repository. Change:

- FormatJS descriptor files are read as sources. `formatjs extract` writes
  {"id": {"defaultMessage": ..., "description": ...}} (Mattermost's en.json)
  while translations map each id to a string; flattened, no key matched, so
  l10n-guard reported every key missing and compared nothing (the census's
  antonym-collision/HOLDOUT2-RESULTS.md, Mattermost row). A new function
  unwrap_descriptors() turns such a catalog into {id: defaultMessage} at the
  top of check_catalog(); any other catalog is unchanged. Pre-registered in
  antonym-collision/FORMATJS-PREREG.md.

Nothing is written unless every anchor is found the expected number of times
and main is at 0.13.0.

  python patch_0140.py --out-dir /out/0140

Writes l10n_guard.py and README.md (patched), action.yml and the tests on
main, and test_0140.py, to --out-dir; the unpatched 0.13.0 to
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
         "test_0100.py", "test_0110.py", "test_0120.py", "test_0130.py")

CHECK_HEAD = ('def check_catalog(source, target):\n'
              '    """Compares two loaded JSON catalogs (dicts). Returns a list of issues."""\n'
              '    src, tgt = flatten(source), flatten(target)\n')
UNWRAP = ('def unwrap_descriptors(data):\n'
          '    """A FormatJS `extract` file maps each id to {"defaultMessage": ...,\n'
          '    "description": ...} (Mattermost\'s en.json). When every value of a catalog\n'
          '    is such an object with a string defaultMessage, returns {id: defaultMessage},\n'
          '    so the message is the text and descriptions are not compared. Any other\n'
          '    catalog is returned unchanged (0.14.0; the census\'s\n'
          '    antonym-collision/FORMATJS-PREREG.md)."""\n'
          '    if not isinstance(data, dict) or not data:\n'
          '        return data\n'
          '    for value in data.values():\n'
          '        if not isinstance(value, dict) or not isinstance(value.get("defaultMessage"), str):\n'
          '            return data\n'
          '    return {key: value["defaultMessage"] for key, value in data.items()}\n'
          '\n'
          '\n')
CHECK_NEW = (UNWRAP +
             'def check_catalog(source, target):\n'
             '    """Compares two loaded JSON catalogs (dicts). Returns a list of issues.\n'
             '    FormatJS descriptor files are read as {id: defaultMessage} first (0.14.0)."""\n'
             '    source, target = unwrap_descriptors(source), unwrap_descriptors(target)\n'
             '    src, tgt = flatten(source), flatten(target)\n')

JSON_LINE = "- **JSON catalogs** (i18next, vue-i18n, next-intl, flat or nested): placeholders, markup, missing\n"
PO_LINE = "- **gettext `.po`**: placeholders per entry, plural form count against the `Plural-Forms` header,\n"
FORMATJS = ('  Since 0.14.0 the source may be a FormatJS `extract` file (`{"id": {"defaultMessage": ...,\n'
            '  "description": ...}}`, as Mattermost\'s `en.json`): each `defaultMessage` is the source text,\n'
            '  descriptions are not compared, and flat translations of such a file are checked key by key.\n')
MAX_BULLET_LINES = 4


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
    if "unwrap_descriptors" in guard:
        raise PatchError("l10n_guard.py already has unwrap_descriptors")
    guard = replace(guard, '__version__ = "0.13.0"', '__version__ = "0.14.0"')
    guard = replace(guard, CHECK_HEAD, CHECK_NEW)
    compile(guard, "l10n_guard.py", "exec")
    return guard


def patch_readme(readme):
    if "defaultMessage" in readme:
        raise PatchError("README.md already describes FormatJS descriptor files")
    if "l10n-guard@v0.13.0" not in readme:
        raise PatchError("no l10n-guard@v0.13.0 in README.md")
    if readme.count(JSON_LINE) != 1 or readme.count(PO_LINE) != 1:
        raise PatchError("JSON catalogs or gettext bullet not found exactly once")
    i, j = readme.find(JSON_LINE), readme.find(PO_LINE)
    if not i < j or readme.count("\n", i, j) > MAX_BULLET_LINES:
        raise PatchError("the gettext bullet does not follow the JSON catalogs bullet")
    readme = replace(readme, PO_LINE, FORMATJS + PO_LINE)
    return readme.replace("l10n-guard@v0.13.0", "l10n-guard@v0.14.0")


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="/out/0140")
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
    shutil.copy(os.path.join(here, "test_0140.py"), args.out_dir)
    for name, text in (("l10n_guard.py 0.13.0", original), ("l10n_guard.py 0.14.0", guard)):
        data = text.encode("utf-8")
        print("%s: %d bytes, sha256 %s" % (name, len(data), hashlib.sha256(data).hexdigest()[:16]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
