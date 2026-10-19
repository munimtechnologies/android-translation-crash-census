#!/usr/bin/env python3
"""Pre-registered antonym-collision scan (census antonym-collision/PREREG.md).

An antonym collision is two keys of one translation file whose English texts
differ only by antonyms ("Default expanded" / "Default collapse") while their
translations are the same string. One of the two labels then says the
opposite of what it does, or the two can no longer be told apart. It is a
narrow case of Weblate's "Reused translation" check (different source strings
translated the same), limited to sources that are antonym-only variants.

Projects, read from codeload tarballs at pinned commits:
  nocobase  10810697c31f85d6f2ad7eaa0a0e1990970ea93b  every */locale/*.json, */locales/*.json
  mastodon  cab53a591ec66159c31b4853271fd15f9e2bbb80  app/javascript/mastodon/locales/*.json
In each directory the English file (en-US.json, en.json, en_US.json) gives
the English text of each key; every other JSON object file there is a locale.

  A0 both tarballs download; at least 100 NocoBase and 50 Mastodon locale
     files parse.
  A1 in NocoBase packages/core/client/src/locale, the pair ("Default
     collapse", "Default expanded") is flagged in exactly the 13 locales of
     EXPECTED_VALUES and is an untranslated copy in exactly pt-BR and tr-TR
     (so zh-CN is neither).
  A2 the shared values in those 13 locales are exactly EXPECTED_VALUES (NFC).
  A3 NocoBase has at least 10 flagged instances besides A1's pair.
  A4 NocoBase's flagged instances per 1,000 comparisons are at least 5 times
     Mastodon's, with at least 500 Mastodon comparisons.
  A5 (graded by hand, from collisions.csv): of the first 60 NocoBase flagged
     instances, at least 60% of those judged are real defects.

  python antonym_scan.py --out-dir /out/ac

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import csv
import json
import os
import re
import sys
import tarfile
import unicodedata
import urllib.request

PROJECTS = [
    {"name": "nocobase", "repo": "nocobase/nocobase",
     "commit": "10810697c31f85d6f2ad7eaa0a0e1990970ea93b", "select": "locale-dirs"},
    {"name": "mastodon", "repo": "mastodon/mastodon",
     "commit": "cab53a591ec66159c31b4853271fd15f9e2bbb80",
     "select": "app/javascript/mastodon/locales/"},
]
CODELOAD = "https://codeload.github.com/%s/tar.gz/%s"
REFERENCES = ("en-US.json", "en.json", "en_US.json")

# Each class: (words of one polarity, words of the other). Fixed before the run.
_CLASSES = {
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
ANTONYMS = {}
for _cls, (_plus, _minus) in _CLASSES.items():
    for _word in _plus.split():
        ANTONYMS[_word] = (_cls, 1)
    for _word in _minus.split():
        ANTONYMS[_word] = (_cls, -1)
TOKEN = re.compile(r"[a-z]+")

A1_DIR = "packages/core/client/src/locale"
A1_PAIR = ("Default collapse", "Default expanded")
EXPECTED_VALUES = {
    "de-DE": "Standardmäßig eingeklappt",
    "es-ES": "Contraer por defecto",
    "fr-FR": "Développé/réduit par défaut",
    "hu-HU": "Alapértelmezett összecsukás",
    "id-ID": "Ciutkan default",
    "it-IT": "Comprimi di default",
    "ja-JP": "デフォルト閉じる",
    "ko-KR": "기본 축소",
    "nl-NL": "Standaard inklappen",
    "ru-RU": "Сворачивание по умолчанию",
    "uk-UA": "Згорнути за замовчуванням",
    "vi-VN": "Thu gọn mặc định",
    "zh-TW": "預設展開",
}
A1_COPY = ("pt-BR", "tr-TR")
MIN_FILES = {"nocobase": 100, "mastodon": 50}
MIN_OTHER_FLAGGED = 10
MIN_RATE_RATIO = 5
MIN_MASTODON_COMPARISONS = 500


def signature(text):
    """(tokens with antonyms replaced by their class, polarity of each token)."""
    sig, pol = [], []
    for tok in TOKEN.findall(text.lower()):
        if tok in ANTONYMS:
            cls, p = ANTONYMS[tok]
            sig.append(cls)
            pol.append(p)
        else:
            sig.append(tok)
            pol.append(0)
    return tuple(sig), tuple(pol)


def antonym_pairs(ref):
    """Sorted (key1, key2) whose English texts differ only by an odd number of
    antonym flips (inflections of the same side don't count)."""
    groups = {}
    for key, text in ref.items():
        sig, pol = signature(text)
        if any(pol):
            groups.setdefault(sig, []).append((key, pol))
    pairs = []
    for members in groups.values():
        members.sort()
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                (k1, p1), (k2, p2) = members[i], members[j]
                if sum(1 for a, b in zip(p1, p2) if a and a != b) % 2:
                    pairs.append((k1, k2))
    return sorted(pairs)


def flatten(obj, prefix=""):
    """{dotted key: string} for the string leaves of a JSON object."""
    out = {}
    for key, value in obj.items():
        name = "%s.%s" % (prefix, key) if prefix else str(key)
        if isinstance(value, str):
            out[name] = value
        elif isinstance(value, dict):
            out.update(flatten(value, name))
    return out


def load(data):
    """The flattened strings of a JSON object file, or None."""
    try:
        obj = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError):
        return None
    return flatten(obj) if isinstance(obj, dict) else None


def scan_dir(ref, locales):
    """(pairs, comparisons, rows) for one directory. A comparison is one pair
    in one locale where both keys have a non-empty value; equal values are
    'copy' when they equal either English text, else 'flagged'."""
    pairs = antonym_pairs(ref)
    comparisons, rows = 0, []
    for loc in sorted(locales):
        tr = locales[loc]
        for k1, k2 in pairs:
            v1, v2 = tr.get(k1, "").strip(), tr.get(k2, "").strip()
            if not v1 or not v2:
                continue
            comparisons += 1
            if v1 != v2:
                continue
            english = {ref[k1].strip().casefold(), ref[k2].strip().casefold()}
            rows.append({"locale": loc, "kind": "copy" if v1.casefold() in english else "flagged",
                         "key1": k1, "key2": k2, "en1": ref[k1], "en2": ref[k2], "value": v1})
    return len(pairs), comparisons, rows


def selected(project, path):
    parts = path.split("/")
    if not parts[-1].endswith(".json") or "node_modules" in parts:
        return False
    if project["select"] == "locale-dirs":
        return len(parts) >= 2 and parts[-2] in ("locale", "locales")
    prefix = project["select"]
    return path.startswith(prefix) and "/" not in path[len(prefix):]


def read_tarball(fileobj, project):
    """{path inside the repo: bytes} for the selected files of a .tar.gz stream."""
    files = {}
    with tarfile.open(fileobj=fileobj, mode="r|gz") as tar:
        for member in tar:
            if not member.isfile() or "/" not in member.name:
                continue
            path = member.name.split("/", 1)[1]
            if selected(project, path):
                files[path] = tar.extractfile(member).read()
    return files


def scan_project(files):
    """Totals and rows for one project's selected files."""
    by_dir = {}
    for path, data in files.items():
        d, _, name = path.rpartition("/")
        by_dir.setdefault(d, {})[name] = data
    res = {"dirs": 0, "locale_files": 0, "unparsed": [], "pairs": 0, "comparisons": 0, "rows": []}
    for d in sorted(by_dir):
        names = by_dir[d]
        ref_name = next((r for r in REFERENCES if r in names), None)
        if ref_name is None:
            continue
        ref = load(names[ref_name])
        if ref is None:
            res["unparsed"].append("%s/%s" % (d, ref_name))
            continue
        locales = {}
        for name in sorted(names):
            if name in REFERENCES:
                continue
            flat = load(names[name])
            if flat is None:
                res["unparsed"].append("%s/%s" % (d, name))
            else:
                locales[name[:-len(".json")]] = flat
        pairs, comparisons, rows = scan_dir(ref, locales)
        res["dirs"] += 1
        res["locale_files"] += len(locales)
        res["pairs"] += pairs
        res["comparisons"] += comparisons
        for row in rows:
            row["dir"] = d
        res["rows"].extend(rows)
    res["flagged"] = sum(1 for r in res["rows"] if r["kind"] == "flagged")
    res["copies"] = sum(1 for r in res["rows"] if r["kind"] == "copy")
    return res


def rate(res):
    return 1000.0 * res["flagged"] / res["comparisons"] if res.get("comparisons") else 0.0


def nfc(s):
    return unicodedata.normalize("NFC", s)


def grade(results):
    """[(id, text, held, value)] for A0-A4."""
    noco, masto = results.get("nocobase", {}), results.get("mastodon", {})
    ok = all("error" not in results.get(n, {"error": "missing"}) for n in MIN_FILES)
    counts = {n: results.get(n, {}).get("locale_files", 0) for n in MIN_FILES}
    a0 = ok and all(counts[n] >= MIN_FILES[n] for n in MIN_FILES)

    a1_rows = [r for r in noco.get("rows", []) if r["dir"] == A1_DIR and (r["key1"], r["key2"]) == A1_PAIR]
    flagged = {r["locale"]: r["value"] for r in a1_rows if r["kind"] == "flagged"}
    copies = sorted(r["locale"] for r in a1_rows if r["kind"] == "copy")
    a1 = sorted(flagged) == sorted(EXPECTED_VALUES) and copies == sorted(A1_COPY)
    wrong = sorted(loc for loc, v in EXPECTED_VALUES.items() if nfc(flagged.get(loc, "")) != nfc(v))
    not_raw = sorted(loc for loc, v in EXPECTED_VALUES.items()
                     if loc in flagged and nfc(flagged[loc]) == nfc(v) and flagged[loc] != v)

    other = sum(1 for r in noco.get("rows", []) if r["kind"] == "flagged" and r not in a1_rows)
    r_noco, r_masto = rate(noco), rate(masto)
    enough = masto.get("comparisons", 0) >= MIN_MASTODON_COMPARISONS
    if r_masto:
        a4 = enough and r_noco >= MIN_RATE_RATIO * r_masto
    else:
        a4 = enough and noco.get("flagged", 0) > 0
    return [
        ("A0", "both tarballs download; >= %d NocoBase and >= %d Mastodon locale files parse"
               % (MIN_FILES["nocobase"], MIN_FILES["mastodon"]), a0,
         "locale files %s; errors %s" % (counts, {n: results.get(n, {}).get("error") for n in MIN_FILES})),
        ("A1", "%s %s flagged in exactly the 13 expected locales, copy in exactly %s" % (A1_DIR, A1_PAIR, A1_COPY),
         a1, "flagged %s; copy %s" % (sorted(flagged), copies)),
        ("A2", "the 13 shared values are exactly as expected (NFC)", not wrong,
         "differing %s; equal only after NFC %s" % (wrong or "none", not_raw or "none")),
        ("A3", "at least %d NocoBase flagged instances besides A1's pair" % MIN_OTHER_FLAGGED,
         other >= MIN_OTHER_FLAGGED, "%d others" % other),
        ("A4", "NocoBase flagged rate >= %dx Mastodon's, with >= %d Mastodon comparisons"
               % (MIN_RATE_RATIO, MIN_MASTODON_COMPARISONS), a4,
         "NocoBase %d/%d = %.2f per 1,000; Mastodon %d/%d = %.2f per 1,000"
         % (noco.get("flagged", 0), noco.get("comparisons", 0), r_noco,
            masto.get("flagged", 0), masto.get("comparisons", 0), r_masto)),
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="/out/ac")
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    results = {}
    for project in PROJECTS:
        url = CODELOAD % (project["repo"], project["commit"])
        req = urllib.request.Request(url, headers={"User-Agent": "mv2-antonym-scan"})
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                files = read_tarball(r, project)
        except (OSError, EOFError, ValueError, tarfile.TarError) as exc:
            results[project["name"]] = {"error": "%s: %s" % (type(exc).__name__, exc)}
            print("%s: NOT DOWNLOADED (%s)" % (project["name"], exc))
            continue
        res = scan_project(files)
        res.update(repo=project["repo"], commit=project["commit"], selected_files=len(files))
        results[project["name"]] = res
        print("%s @%s: %d files selected, %d dirs with an English file, %d locale files, %d unparsed, "
              "%d antonym pairs, %d comparisons, %d flagged, %d copies, %.2f flagged per 1,000"
              % (project["name"], project["commit"][:8], len(files), res["dirs"], res["locale_files"],
                 len(res["unparsed"]), res["pairs"], res["comparisons"], res["flagged"], res["copies"],
                 rate(res)))
        for row in res["rows"]:
            if row["kind"] == "flagged":
                print("  flagged %s %s: %r / %r = %r" % (row["dir"], row["locale"], row["key1"], row["key2"],
                                                         row["value"]))

    checks = grade(results)
    for name, text, held, value in checks:
        print("%s %s: %s (%s)" % (name, "HELD" if held else "FAILED", text, value))
    print("A5 is graded by hand from collisions.csv")
    with open(os.path.join(args.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump({"projects": {n: {k: v for k, v in r.items() if k != "rows"} for n, r in results.items()},
                   "predictions": [{"id": n, "text": t, "held": h, "value": v} for n, t, h, v in checks]},
                  f, ensure_ascii=False, indent=1)
    with open(os.path.join(args.out_dir, "collisions.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["project", "dir", "locale", "kind", "key1", "key2", "en1", "en2", "value"])
        for name in sorted(results):
            for r in results[name].get("rows", []):
                w.writerow([name, r["dir"], r["locale"], r["kind"], r["key1"], r["key2"],
                            r["en1"], r["en2"], r["value"]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
