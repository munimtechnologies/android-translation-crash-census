#!/usr/bin/env python3
"""Builds l10n-guard 0.12.0 from the 0.11.0 on main in the
munimtechnologies/l10n-guard repository. Changes:

- antonym-collision (a warning): two keys of a JSON or .arb catalog whose
  source texts differ only by antonyms ("Default expanded" / "Default
  collapse", "Mute" / "Unmute") but share one translation, so one of the two
  labels says the opposite of what it does. The 40 word classes and the rule
  are the ones fixed in the census's antonym-collision/PREREG.md; the check
  and its predictions are in antonym-collision/GUARD-PREREG.md, written
  before this code ran. It runs in check_catalog, so it covers the json and
  arb kinds and the JSON files of dir.

Nothing is written unless every anchor is found the expected number of times.

  python patch_0120.py --out-dir /out/0120

Writes l10n_guard.py and README.md (patched), action.yml and the tests on
main, and test_0120.py, to --out-dir; the unpatched 0.11.0 to
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
         "test_0100.py", "test_0110.py")

CATALOG = "def check_catalog(source, target):\n"
FLATTENED = "    src, tgt = flatten(source), flatten(target)\n"
RETURN = "\n    return problems\n"
RETURN_NEW = "\n    problems.extend(_antonym_collisions(src, tgt))\n    return problems\n"
ANTONYM = r'''# Two keys whose source texts differ only by antonyms ("Default expanded" /
# "Default collapse", "Mute" / "Unmute") but share one translation: one of the
# two labels says the opposite of what it does, or users can't tell them
# apart. A source fix that keeps the old translations leaves this shape
# (0.12.0). A warning. The word classes were fixed in the census's
# antonym-collision/PREREG.md before any scan; antonyms outside them
# ("Visible" / "Hidden") are missed.
_ANTONYM_CLASSES = {
    "EXPAND": ("expand expands expanded expanding unfold unfolded",
               "collapse collapses collapsed collapsing fold folded"),
    "SHOW": ("show shows showing shown", "hide hides hiding hidden"),
    "ENABLE": ("enable enables enabled enabling", "disable disables disabled disabling"),
    "OPEN": ("open opens opened opening", "close closes closed closing"),
    "LOCK": ("lock locks locked locking", "unlock unlocks unlocked unlocking"),
    "ALLOW": ("allow allows allowed allowing",
              "deny denies denied denying disallow disallowed forbid forbidden"),
    "VISIBLE": ("visible", "invisible"),
    "SORT": ("ascending asc", "descending desc"),
    "INCREASE": ("increase increases increased", "decrease decreases decreased"),
    "MAX": ("max maximum", "min minimum"),
    "INCLUDE": ("include includes included including", "exclude excludes excluded excluding"),
    "SELECT": ("select selected", "deselect deselected unselect unselected"),
    "PIN": ("pin pinned", "unpin unpinned"),
    "MUTE": ("mute muted", "unmute unmuted"),
    "FOLLOW": ("follow followed", "unfollow unfollowed"),
    "BLOCK": ("block blocked", "unblock unblocked"),
    "FAVOURITE": ("favourite favorite favourited favorited",
                  "unfavourite unfavorite unfavourited unfavorited"),
    "BOOKMARK": ("bookmark bookmarked", "unbookmark unbookmarked"),
    "SUBSCRIBE": ("subscribe subscribed", "unsubscribe unsubscribed"),
    "ARCHIVE": ("archive archived", "unarchive unarchived"),
    "ADD": ("add added", "remove removed"),
    "IMPORT": ("import imported", "export exported"),
    "UPLOAD": ("upload uploaded", "download downloaded"),
    "START": ("start starts started", "end ends ended"),
    "BEFORE": ("before", "after"),
    "ABOVE": ("above", "below"),
    "LEFT": ("left", "right"),
    "FIRST": ("first", "last"),
    "NEXT": ("next", "previous prev"),
    "MORE": ("more", "less"),
    "IN": ("in", "out"),
    "ON": ("on", "off"),
    "YES": ("yes", "no"),
    "TRUE": ("true", "false"),
    "READ": ("read", "unread"),
    "PUBLIC": ("public", "private"),
    "ONLINE": ("online", "offline"),
    "CONNECT": ("connect connected", "disconnect disconnected"),
    "LOGIN": ("login", "logout"),
    "REQUIRED": ("required", "optional"),
}
_ANTONYMS = {}
for _cls, (_plus, _minus) in _ANTONYM_CLASSES.items():
    for _word in _plus.split():
        _ANTONYMS[_word] = (_cls, 1)
    for _word in _minus.split():
        _ANTONYMS[_word] = (_cls, -1)
_WORD_RE = re.compile(r"[a-z]+")


def _antonym_signature(text):
    """(words with antonyms replaced by their class, polarity of each word)."""
    sig, pol = [], []
    for word in _WORD_RE.findall(text.lower()):
        cls, p = _ANTONYMS.get(word, (word, 0))
        sig.append(cls)
        pol.append(p)
    return tuple(sig), tuple(pol)


def antonym_pairs(source):
    """Sorted (key1, key2) of keys whose source texts differ only by an odd
    number of antonym flips (inflections of one side don't count)."""
    groups = {}
    for key, text in source.items():
        if not isinstance(text, str):
            continue
        sig, pol = _antonym_signature(text)
        if any(pol):
            groups.setdefault(sig, []).append((key, pol))
    pairs = []
    for members in groups.values():
        members.sort()
        for i, (k1, p1) in enumerate(members):
            for k2, p2 in members[i + 1:]:
                if sum(1 for a, b in zip(p1, p2) if a and a != b) % 2:
                    pairs.append((k1, k2))
    return sorted(pairs)


def _antonym_collisions(source, target):
    """antonym-collision warnings for two flattened catalogs. A shared value
    equal to either source text is an untranslated copy, not a collision."""
    problems = []
    for k1, k2 in antonym_pairs(source):
        v1, v2 = target.get(k1), target.get(k2)
        if not isinstance(v1, str) or not isinstance(v2, str):
            continue
        v1, v2 = v1.strip(), v2.strip()
        if not v1 or v1 != v2:
            continue
        if v1.casefold() in (source[k1].strip().casefold(), source[k2].strip().casefold()):
            continue
        p = issue(WARNING, "antonym-collision",
                  "same translation as %s (%r), though the sources say opposite things: %r / %r"
                  % (k2, v1, source[k1], source[k2]), k1)
        p["other_key"] = k2
        problems.append(p)
    return problems


'''

CENSUS = "https://github.com/munimtechnologies/android-translation-crash-census/blob/main/"
README_AFTER_READING = "mt-artifacts/KATAKANA-READING.md)).\n- **Apple `.strings` and String Catalogs**"
README_ANTONYM = (
    "mt-artifacts/KATAKANA-READING.md)).\n"
    "- **Antonym collisions** (0.12.0, code `antonym-collision`, JSON and `.arb`): two keys whose source\n"
    "  texts differ only by antonyms (\"Default expanded\" / \"Default collapse\", \"Mute\" / \"Unmute\") but\n"
    "  share one translation, so one of the two labels says the opposite of what it does. A source fix\n"
    "  that keeps the old translations leaves this shape: in NocoBase, a switch relabelled \"Default\n"
    "  expanded\" still read \"collapse\" in 13 of 16 locales. A shared value equal to either source text\n"
    "  is left to the untranslated check. The 40 word classes were fixed before any scan, and antonyms\n"
    "  outside them (\"Visible\" / \"Hidden\") are missed, so it is a warning\n"
    "  ([scan](" + CENSUS + "antonym-collision/RESULTS.md),\n"
    "  [pre-registration of this check](" + CENSUS + "antonym-collision/GUARD-PREREG.md)).\n"
    "- **Apple `.strings` and String Catalogs**")


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
    guard = replace(guard, '__version__ = "0.11.0"', '__version__ = "0.12.0"')
    if "antonym-collision" in guard or "_antonym_collisions" in guard:
        raise PatchError("0.12.0 changes are already in l10n_guard.py")
    start = guard.find(CATALOG)
    if start < 0 or guard.count(CATALOG) != 1:
        raise PatchError("expected 1 check_catalog, found %d" % guard.count(CATALOG))
    end = guard.find("\ndef ", start + len(CATALOG))
    if end < 0:
        raise PatchError("no function after check_catalog")
    body = guard[start:end]
    if body.count(FLATTENED) != 1:
        raise PatchError("check_catalog doesn't flatten source and target as expected")
    if body.count(RETURN) != 1:
        raise PatchError("expected 1 return in check_catalog, found %d" % body.count(RETURN))
    body = body.replace(RETURN, RETURN_NEW)
    guard = guard[:start] + ANTONYM + body + guard[end:]
    compile(guard, "l10n_guard.py", "exec")
    return guard


def patch_readme(readme):
    if "l10n-guard@v0.11.0" not in readme:
        raise PatchError("no l10n-guard@v0.11.0 in README.md")
    readme = replace(readme, README_AFTER_READING, README_ANTONYM)
    return readme.replace("l10n-guard@v0.11.0", "l10n-guard@v0.12.0")


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="/out/0120")
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
    shutil.copy(os.path.join(here, "test_0120.py"), args.out_dir)
    for name, text in (("l10n_guard.py 0.11.0", original), ("l10n_guard.py 0.12.0", guard)):
        data = text.encode("utf-8")
        print("%s: %d bytes, sha256 %s" % (name, len(data), hashlib.sha256(data).hexdigest()[:16]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
