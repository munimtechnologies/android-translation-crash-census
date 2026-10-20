#!/usr/bin/env python3
"""Third held-out test of l10n-guard 0.14.0's antonym-collision check, on five
react-intl projects whose committed English catalogs are flat or nested
id -> string files (no FormatJS descriptor source was found; see the census's
antonym-collision/HOLDOUT3-PREREG.md), against the predictions written there
before any translation of these projects was compared:

  P0 Every reference parses; every project has at least 10 parsed non-English
     locale files; the five together have at least 120.
  P1 At least 10,000 comparisons pooled over the five projects.
  P2 Pooled warning rate between 0.5 and 5.0 per 1,000 comparisons, and at
     least 3 of the 5 projects raise at least one warning.
  P3 (graded by hand from sample.csv) at least 60% of judged warnings are real.
  P4 (graded by hand) at least 20% of the real rows name neither side.
  P5 At least 80% of warned rows have both keys found as literals in source;
     Open Collective is judged separately when under half its keys are found.

  python eval_holdout3.py --fetch-guard --guard-dir /out/guard
  python eval_holdout3.py --guard-dir /out/guard --out-dir /out/holdout3

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import random
import re
import sys
import tarfile
import urllib.request

RAW = "https://raw.githubusercontent.com/"
GUARD_URL = RAW + "munimtechnologies/l10n-guard/v0.14.0/l10n_guard.py"
GUARD_VERSION = "0.14.0"
CENSUS = RAW + "munimtechnologies/android-translation-crash-census/main/antonym-collision/"
PREREG_URL = CENSUS + "HOLDOUT3-PREREG.md"
CODELOAD = "https://codeload.github.com/%s/tar.gz/%s"
LANG = r"(?P<lang>[A-Za-z]{2,3}(?:[-_@][A-Za-z0-9]{2,8})*)"
HEADERS = {"User-Agent": "mv2-l10n-guard-eval"}
OC = "open-collective"

# Each project's default branch at run time; the commit is recorded from the
# archive's pax header.
PROJECTS = [
    {"name": "mastodon", "repo": "mastodon/mastodon", "ref": "main",
     "pattern": r"app/javascript/mastodon/locales/" + LANG + r"\.json", "refs": ("en",)},
    {"name": "bigbluebutton", "repo": "bigbluebutton/bigbluebutton", "ref": "develop",
     "pattern": r"bigbluebutton-html5/public/locales/" + LANG + r"\.json", "refs": ("en",)},
    {"name": "strapi-admin", "repo": "strapi/strapi", "ref": "develop",
     "pattern": r"packages/core/admin/admin/src/translations/" + LANG + r"\.json", "refs": ("en",)},
    {"name": "umami", "repo": "umami-software/umami", "ref": "master",
     "pattern": r"public/intl/messages/" + LANG + r"\.json", "refs": ("en-US",)},
    {"name": OC, "repo": "opencollective/opencollective-frontend", "ref": "main",
     "pattern": r"lang/" + LANG + r"\.json", "refs": ("en",)},
]
SOURCE_EXT = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue", ".svelte", ".dart", ".html", ".py")
MAX_SOURCE_BYTES = 2000000
LITERAL = re.compile(r"""'([^'\\\n]{1,300})'|"([^"\\\n]{1,300})"|`([^`\\\n$]{1,300})`""")
PLURAL = re.compile(r"[._|](?:zero|one|two|few|many|other)$")
MESSAGE = re.compile(r"\.message$")
MIN_LOCALES_PER_PROJECT = 10
MIN_LOCALES_TOTAL = 120
MIN_COMPARISONS = 10000
MIN_PER_1000 = 0.5
MAX_PER_1000 = 5.0
MIN_PROJECTS_WARNED = 3
MIN_USED_SHARE = 0.8
OC_USED_FLOOR = 0.5
SAMPLE_SIZE = 40
SAMPLE_SEED = 150
FIELDS = ["project", "locale", "key1", "key2", "en1", "en2", "value", "classes", "key1_used", "key2_used"]


def get(url, timeout=60):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_guard(guard_dir):
    """Fetches the released guard, but only once the pre-registration is
    public: without the guard the evaluation cannot run, so no translation is
    compared before HOLDOUT3-PREREG.md is on main."""
    try:
        prereg = get(PREREG_URL)
    except OSError as exc:
        print("pre-registration not public yet (%s); stopping" % exc)
        return 1
    print("HOLDOUT3-PREREG.md: %d bytes, sha256 %s" % (len(prereg), hashlib.sha256(prereg).hexdigest()[:16]))
    try:
        data = get(GUARD_URL)
    except OSError as exc:
        print("l10n-guard v%s not released yet (%s); stopping" % (GUARD_VERSION, exc))
        return 1
    os.makedirs(guard_dir, exist_ok=True)
    path = os.path.join(guard_dir, "l10n_guard.py")
    with open(path, "wb") as f:
        f.write(data)
    g = load_guard(path)
    print("l10n_guard.py %s: %d bytes, sha256 %s" % (g.__version__, len(data), hashlib.sha256(data).hexdigest()[:16]))
    return 0 if g.__version__ == GUARD_VERSION else 1


def load_guard(path, name="guard_holdout3"):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def unwrap(g, data):
    """0.14.0's unwrap_descriptors (a no-op on these flat catalogs); older
    guards leave the catalog as it is."""
    fn = getattr(g, "unwrap_descriptors", None)
    return fn(data) if fn else data


def locale_file(project, path):
    """The locale code when path is one of the project's locale files, else None."""
    if "node_modules" in path.split("/"):
        return None
    m = re.fullmatch(project["pattern"], path)
    return m.group("lang") if m else None


def skipped(project, lang):
    """The reference and other English variants are not compared."""
    return lang in project["refs"] or lang.lower().startswith("en")


def literals(text):
    """The contents of the single-, double- and back-quoted strings in text."""
    return {a or b or c for a, b, c in LITERAL.findall(text)}


def key_candidates(key):
    """Ways code may name a catalog key: as is, with | for ., without a
    plural suffix, and without a messages.json `.message` suffix."""
    out = {key}
    for pattern in (PLURAL, MESSAGE):
        base = pattern.sub("", key)
        if base != key:
            out.add(base)
    out.update(k.replace(".", "|") for k in list(out))
    return out


def used(key, found):
    return any(c in found for c in key_candidates(key))


def parse(data):
    try:
        obj = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


def read_project(project, fileobj):
    """({lang: bytes}, set of code literals, commit) from a .tar.gz stream."""
    files, found = {}, set()
    with tarfile.open(fileobj=fileobj, mode="r|gz") as tar:
        for member in tar:
            if not member.isfile() or "/" not in member.name:
                continue
            path = member.name.split("/", 1)[1]
            lang = locale_file(project, path)
            if lang:
                files[lang] = tar.extractfile(member).read()
            elif (path.endswith(SOURCE_EXT) and member.size <= MAX_SOURCE_BYTES
                  and "node_modules" not in path.split("/")):
                found |= literals(tar.extractfile(member).read().decode("utf-8", "replace"))
        commit = tar.pax_headers.get("comment", "")
    return files, found, commit


def flip_classes(g, en1, en2):
    """The word classes whose antonyms are swapped between two source texts."""
    s1, p1 = g._antonym_signature(en1)
    _, p2 = g._antonym_signature(en2)
    return "+".join(sorted({s1[i] for i, (a, b) in enumerate(zip(p1, p2)) if a and b and a != b}))


def identical_files(project, files):
    """Groups of compared locale files whose bytes are identical."""
    by_hash = {}
    for lang in sorted(files):
        if not skipped(project, lang):
            by_hash.setdefault(hashlib.sha256(files[lang]).hexdigest(), []).append(lang)
    return [langs for langs in by_hash.values() if len(langs) > 1]


def scan(g, project, files):
    """Per-project totals and one row per antonym-collision warning.
    check_catalog gets the raw catalogs, as the command line would; the
    comparison count uses the same flattening the guard applies."""
    res = {"guard": g.__version__, "locale_files": 0, "unparsed": [], "reference": None,
           "source_keys": 0, "pairs": 0, "comparisons": 0, "rows": [], "consistent": True,
           "identical": identical_files(project, files)}
    ref_lang = next((r for r in project["refs"] if r in files), None)
    ref = parse(files[ref_lang]) if ref_lang else None
    if ref is None:
        return res
    res["reference"] = ref_lang
    src = g.flatten(unwrap(g, ref))
    res["source_keys"] = len(src)
    pairs = g.antonym_pairs(src)
    res["pairs"] = len(pairs)
    for lang in sorted(files):
        if skipped(project, lang):
            continue
        target = parse(files[lang])
        if target is None:
            res["unparsed"].append(lang)
            continue
        res["locale_files"] += 1
        tgt = g.flatten(unwrap(g, target))
        for k1, k2 in pairs:
            v1, v2 = tgt.get(k1), tgt.get(k2)
            if isinstance(v1, str) and isinstance(v2, str) and v1.strip() and v2.strip():
                res["comparisons"] += 1
        warned = [p for p in g.check_catalog(ref, target) if p["code"] == "antonym-collision"]
        if len(warned) != len(g._antonym_collisions(src, tgt)):
            res["consistent"] = False
        for p in warned:
            k1, k2 = p["key"], p["other_key"]
            res["rows"].append({"project": project["name"], "locale": lang, "key1": k1, "key2": k2,
                                "en1": src[k1], "en2": src[k2], "value": tgt[k1].strip(),
                                "classes": flip_classes(g, src[k1], src[k2])})
    return res


def row_key(row):
    return (row["project"], row["locale"], row["key1"], row["key2"])


def sample(rows, size, seed):
    ordered = sorted(rows, key=row_key)
    if len(ordered) <= size:
        return ordered
    picked = random.Random(seed).sample(range(len(ordered)), size)
    return [ordered[i] for i in sorted(picked)]


def rate(warnings, comparisons):
    """Warnings per 1,000 comparisons (0.0 when nothing was compared)."""
    return 1000.0 * warnings / comparisons if comparisons else 0.0


def rate_in_range(per_1000):
    return MIN_PER_1000 <= per_1000 <= MAX_PER_1000


def used_counts(rows):
    """(rows whose two keys were both found in source, rows)."""
    both = sum(1 for r in rows if r.get("key1_used") and r.get("key2_used"))
    return both, len(rows)


def p5_check(rows):
    """P5 with the pre-registered Open Collective rule: when fewer than half of
    its warned rows have both keys in source, its hashed ids are taken as
    build-generated and the share is judged on the other projects.
    Returns (held, or None when nothing was warned; text)."""
    oc = [r for r in rows if r["project"] == OC]
    rest = [r for r in rows if r["project"] != OC]
    oc_both, oc_n = used_counts(oc)
    judged, note = rows, "all projects"
    if oc_n and oc_both < OC_USED_FLOOR * oc_n:
        judged, note = rest, "without %s (%d/%d found there)" % (OC, oc_both, oc_n)
    both, n = used_counts(judged)
    if n == 0:
        return None, "no warnings" if not rows else "no rows judged (%s)" % note
    return both >= MIN_USED_SHARE * n, "%d/%d rows with both keys in source, %s" % (both, n, note)


def write_csv(path, rows, fields):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def verdict(held):
    return "NOT TESTED" if held is None else "HELD" if held else "FAILED"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--guard-dir", default="/out/guard")
    parser.add_argument("--out-dir", default="/out/holdout3")
    parser.add_argument("--fetch-guard", action="store_true")
    args = parser.parse_args()
    if args.fetch_guard:
        return fetch_guard(args.guard_dir)
    g = load_guard(os.path.join(args.guard_dir, "l10n_guard.py"))
    print("l10n-guard %s" % g.__version__)
    if g.__version__ != GUARD_VERSION:
        print("expected l10n-guard %s; stopping" % GUARD_VERSION)
        return 1
    os.makedirs(args.out_dir, exist_ok=True)

    results = {}
    for project in PROJECTS:
        name = project["name"]
        url = CODELOAD % (project["repo"], project["ref"])
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=900) as r:
                files, found, commit = read_project(project, r)
        except (OSError, EOFError, ValueError, tarfile.TarError) as exc:
            results[name] = {"error": "%s: %s" % (type(exc).__name__, exc)}
            print("%s: NOT DOWNLOADED (%s)" % (name, exc))
            continue
        s = scan(g, project, files)
        for row in s["rows"]:
            row["key1_used"] = used(row["key1"], found)
            row["key2_used"] = used(row["key2"], found)
        results[name] = {"repo": project["repo"], "ref": project["ref"], "commit": commit,
                         "code_literals": len(found), "scan": s}
        print("%s @%s with %s: reference %s, %d source keys, %d locale files, %d unparsed, %d pairs, "
              "%d comparisons, %d warnings, %.2f per 1,000, identical files %s, consistent %s"
              % (name, commit[:8] or "?", s["guard"], s["reference"], s["source_keys"], s["locale_files"],
                 len(s["unparsed"]), s["pairs"], s["comparisons"], len(s["rows"]),
                 rate(len(s["rows"]), s["comparisons"]), s["identical"] or "none", s["consistent"]))
        for row in s["rows"]:
            print("  %s %s [%s]: %r / %r = %r used %s/%s" % (name, row["locale"], row["classes"], row["key1"],
                                                            row["key2"], row["value"], row["key1_used"],
                                                            row["key2_used"]))

    def ok(name):
        return name in results and "error" not in results[name]

    scans = {n: results[n]["scan"] for n in results if ok(n)}
    all_ok = all(ok(p["name"]) for p in PROJECTS)
    rows = [r for n in scans for r in scans[n]["rows"]]
    locale_files = sum(s["locale_files"] for s in scans.values())
    comparisons = sum(s["comparisons"] for s in scans.values())
    per = rate(len(rows), comparisons)
    warned = sorted(n for n in scans if scans[n]["rows"])
    consistent = all(s["consistent"] for s in scans.values())
    p0 = (all_ok and all(s["reference"] and s["locale_files"] >= MIN_LOCALES_PER_PROJECT for s in scans.values())
          and locale_files >= MIN_LOCALES_TOTAL)
    p1 = all_ok and comparisons >= MIN_COMPARISONS
    p2 = all_ok and len(rows) >= 1 and rate_in_range(per) and len(warned) >= MIN_PROJECTS_WARNED
    p5, p5_text = p5_check(rows)
    if not all_ok:
        p5 = False if p5 is not None else None

    checks = [
        ("P0", "every reference parses, >= %d locale files per project, >= %d in all"
               % (MIN_LOCALES_PER_PROJECT, MIN_LOCALES_TOTAL), p0,
         "%s; %d locale files" % ({n: s["locale_files"] for n, s in scans.items()}, locale_files)),
        ("P1", ">= %d comparisons pooled" % MIN_COMPARISONS, p1, "%d comparisons" % comparisons),
        ("P2", "pooled rate within %.1f-%.1f per 1,000 and >= %d projects warned"
               % (MIN_PER_1000, MAX_PER_1000, MIN_PROJECTS_WARNED), p2,
         "%d warnings, %.2f per 1,000, warned: %s" % (len(rows), per, warned or "none")),
        ("P5", ">= %d%% of warned rows have both keys in source" % int(MIN_USED_SHARE * 100), p5, p5_text),
    ]
    for name, text, held, value in checks:
        print("%s %s: %s (%s)" % (name, verdict(held), text, value))
    by_class = {}
    for r in rows:
        by_class[r["classes"]] = by_class.get(r["classes"], 0) + 1
    print("warnings by class: %s" % json.dumps(by_class, sort_keys=True))
    print("warnings by project: %s" % json.dumps({n: len(s["rows"]) for n, s in scans.items()}, sort_keys=True))
    print("check_catalog and _antonym_collisions agree on every file: %s" % consistent)
    print("P3 and P4 are graded by hand from sample.csv")

    write_csv(os.path.join(args.out_dir, "warnings.csv"), rows, FIELDS)
    write_csv(os.path.join(args.out_dir, "sample.csv"), sample(rows, SAMPLE_SIZE, SAMPLE_SEED),
              FIELDS + ["verdict", "note"])
    summary = {"guard": g.__version__, "consistent": consistent, "by_class": by_class,
               "pooled": {"locale_files": locale_files, "comparisons": comparisons, "warnings": len(rows),
                          "per_1000": round(per, 3), "projects_warned": warned},
               "projects": {n: {k: ({kk: vv for kk, vv in v.items() if kk != "rows"} if isinstance(v, dict) else v)
                                for k, v in r.items()} for n, r in results.items()},
               "predictions": [{"id": n, "text": t, "held": h, "value": v} for n, t, h, v in checks]}
    with open(os.path.join(args.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
