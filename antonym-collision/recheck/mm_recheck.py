#!/usr/bin/env python3
"""Re-checks the 67 antonym-collision warnings l10n-guard 0.14.0 raised on
Mattermost's webapp catalogs at be207f89 (2026-10-20; the census's
antonym-collision/formatjs-results/warnings.csv) against current `master`,
before any of them goes upstream as a translation fix.

For every 10-20 row it records whether the shared value is still there
(still), the pair still collides with another value (changed), or the
collision is gone (gone), with both keys' current values. New warnings on
master are listed too. For each still-present row it lists how the same
locale translates each side's English text under OTHER keys of the same
catalog ("the catalog's own wording"), so a fix can reuse the project's
existing terminology instead of new wording. Descriptive only: nothing here
is a pre-registered prediction.

  python mm_recheck.py --out-dir /out

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
import re
import sys
import tarfile
import urllib.request

RAW = "https://raw.githubusercontent.com/"
GUARD_URL = RAW + "munimtechnologies/l10n-guard/v0.14.0/l10n_guard.py"
GUARD_VERSION = "0.14.0"
OLD_URL = RAW + "munimtechnologies/android-translation-crash-census/main/antonym-collision/formatjs-results/warnings.csv"
GRADED_URL = RAW + "munimtechnologies/android-translation-crash-census/main/antonym-collision/formatjs-sample-graded.csv"
OLD_COMMIT = "be207f89"
TARBALL = "https://codeload.github.com/mattermost/mattermost/tar.gz/master"
LANG = r"(?P<lang>[A-Za-z]{2,3}(?:[-_@][A-Za-z0-9]{2,8})*)"
PATTERN = r"webapp/channels/src/i18n/" + LANG + r"\.json"
HEADERS = {"User-Agent": "mv2-l10n-guard-recheck"}
TRAILING = re.compile(r"[\s.:!?…]+$")
SPACE = re.compile(r"\s+")
FIELDS = ["locale", "key1", "key2", "en1", "en2", "old_value", "status", "value1_now", "value2_now",
          "graded", "alt1", "alt2"]


def get(url, timeout=60):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def load_guard(path):
    spec = importlib.util.spec_from_file_location("guard_recheck", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse(data):
    try:
        obj = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


def read_catalogs(fileobj):
    """({lang: bytes}, commit) for the webapp i18n files in a .tar.gz stream."""
    files = {}
    with tarfile.open(fileobj=fileobj, mode="r|gz") as tar:
        for member in tar:
            if not member.isfile() or "/" not in member.name:
                continue
            m = re.fullmatch(PATTERN, member.name.split("/", 1)[1])
            if m:
                files[m.group("lang")] = tar.extractfile(member).read()
        commit = tar.pax_headers.get("comment", "")
    return files, commit


def norm(text):
    """English text as compared across keys: case-folded, whitespace
    collapsed, trailing punctuation and ellipses dropped."""
    return TRAILING.sub("", SPACE.sub(" ", text.strip().casefold()))


def alternatives(src, tgt, key, exclude):
    """{translation: [keys]} for the other keys whose English equals key's
    (by norm) and whose translation is non-empty and differs from exclude."""
    want = norm(src[key])
    out = {}
    for k in sorted(src):
        if k == key or not isinstance(src[k], str) or norm(src[k]) != want:
            continue
        v = tgt.get(k)
        if isinstance(v, str) and v.strip() and v.strip() != exclude:
            out.setdefault(v.strip(), []).append(k)
    return out


def show(alts):
    """'value (key; key) | value (key)', most-used first."""
    ranked = sorted(alts.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    return " | ".join("%s (%s)" % (v, "; ".join(ks)) for v, ks in ranked)


def status(old_value, v1, v2):
    """still: both keys still share the 10-20 value; changed: they share
    another value; gone: they no longer share one (or one is missing)."""
    if not isinstance(v1, str) or not isinstance(v2, str):
        return "gone"
    v1, v2 = v1.strip(), v2.strip()
    if not v1 or v1 != v2:
        return "gone"
    return "still" if v1 == old_value else "changed"


def row_key(locale, key1, key2):
    return (locale, key1, key2)


def recheck(old_rows, graded, current, src, catalogs):
    """One output row per 10-20 Mattermost row, then one per new warning.
    current: {(locale, key1, key2): value} of warnings on master."""
    out, seen = [], set()
    for r in old_rows:
        k = row_key(r["locale"], r["key1"], r["key2"])
        seen.add(k)
        tgt = catalogs.get(r["locale"], {})
        v1, v2 = tgt.get(r["key1"]), tgt.get(r["key2"])
        st = status(r["value"], v1, v2)
        row = {"locale": r["locale"], "key1": r["key1"], "key2": r["key2"], "en1": r["en1"], "en2": r["en2"],
               "old_value": r["value"], "status": st,
               "value1_now": v1.strip() if isinstance(v1, str) else "",
               "value2_now": v2.strip() if isinstance(v2, str) else "",
               "graded": graded.get(k, ""), "alt1": "", "alt2": ""}
        if st != "gone" and r["key1"] in src and r["key2"] in src:
            shared = row["value1_now"]
            row["alt1"] = show(alternatives(src, tgt, r["key1"], shared))
            row["alt2"] = show(alternatives(src, tgt, r["key2"], shared))
        out.append(row)
    for k in sorted(current):
        if k in seen:
            continue
        locale, key1, key2 = k
        tgt = catalogs.get(locale, {})
        out.append({"locale": locale, "key1": key1, "key2": key2, "en1": src.get(key1, ""), "en2": src.get(key2, ""),
                    "old_value": "", "status": "new", "value1_now": current[k], "value2_now": current[k],
                    "graded": "", "alt1": show(alternatives(src, tgt, key1, current[k])) if key1 in src else "",
                    "alt2": show(alternatives(src, tgt, key2, current[k])) if key2 in src else ""})
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="/out")
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    guard_path = os.path.join(args.out_dir, "l10n_guard.py")
    data = get(GUARD_URL)
    with open(guard_path, "wb") as f:
        f.write(data)
    g = load_guard(guard_path)
    print("l10n_guard.py %s: %d bytes, sha256 %s" % (g.__version__, len(data), hashlib.sha256(data).hexdigest()[:16]))
    if g.__version__ != GUARD_VERSION:
        print("expected l10n-guard %s; stopping" % GUARD_VERSION)
        return 1

    old = [r for r in csv.DictReader(io.StringIO(get(OLD_URL).decode("utf-8-sig"))) if r["project"] == "mattermost"]
    graded = {row_key(r["locale"], r["key1"], r["key2"]): r["verdict"]
              for r in csv.DictReader(io.StringIO(get(GRADED_URL).decode("utf-8-sig")))
              if r["project"] == "mattermost"}
    print("10-20 rows: %d; graded in the sample: %d" % (len(old), len(graded)))

    with urllib.request.urlopen(urllib.request.Request(TARBALL, headers=HEADERS), timeout=900) as r:
        files, commit = read_catalogs(r)
    print("mattermost master @%s: %d i18n files" % (commit[:8] or "?", len(files)))
    ref = parse(files.get("en", b""))
    if ref is None:
        print("en.json missing or unparsed; stopping")
        return 1
    src = g.flatten(g.unwrap_descriptors(ref))

    catalogs, current, unparsed = {}, {}, []
    for lang in sorted(files):
        if lang.lower().startswith("en"):
            continue
        target = parse(files[lang])
        if target is None:
            unparsed.append(lang)
            continue
        catalogs[lang] = g.flatten(g.unwrap_descriptors(target))
        for p in g.check_catalog(ref, target):
            if p["code"] == "antonym-collision":
                current[row_key(lang, p["key"], p["other_key"])] = catalogs[lang][p["key"]].strip()

    rows = recheck(old, graded, current, src, catalogs)
    by_status = {}
    for r in rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    for r in rows:
        print("%s %s %s / %s: %r -> %r / %r" % (r["status"], r["locale"], r["key1"], r["key2"], r["old_value"],
                                               r["value1_now"], r["value2_now"]))
        for side in ("alt1", "alt2"):
            if r[side]:
                print("   %s: %s" % (side, r[side]))
    print("by status: %s" % json.dumps(by_status, sort_keys=True))

    with open(os.path.join(args.out_dir, "recheck.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    summary = {"guard": g.__version__, "old_commit": OLD_COMMIT, "commit": commit, "i18n_files": len(files),
               "locales_compared": len(catalogs), "unparsed": unparsed, "old_rows": len(old),
               "warnings_now": len(current), "by_status": by_status}
    with open(os.path.join(args.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
