#!/usr/bin/env python3
"""Grades l10n-guard 0.12.0's antonym-collision warning against the
predictions written before any code ran (census
antonym-collision/GUARD-PREREG.md):

  G0 all seven codeload tarballs download; each of the five new projects has
     its English reference and at least 10 locale files that parse.
  G1 (graded from the job's test steps) the patch applies, the ten test files
     on main pass unchanged, and test_0120's U1-U10 pass.
  G2 on NocoBase @10810697 and Mastodon @cab53a59, the guard's warnings are
     exactly the 27 flagged rows of the published antonym-collision/
     collisions.csv (same dir, locale, key1, key2).
  G3 on the five new projects, at least 20 warnings in total, from at least
     3 of the 5 projects.
  G4 (graded by hand, from sample.csv) of a seeded sample of up to 60
     warnings, at least 60% of those judged are real defects; at least 20
     must be judged or G4 is "not tested".
  G5 at least 50% of the new projects' warnings have both keys found as a
     string literal in the project's own code.

  python eval_0120.py --guard-dir /out/0120 --out-dir /out/0120-eval

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import csv
import importlib.util
import io
import json
import os
import random
import re
import sys
import tarfile
import urllib.request

CODELOAD = "https://codeload.github.com/%s/tar.gz/%s"
PUBLISHED = ("https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/"
             "main/antonym-collision/collisions.csv")
SCAN_REFS = ("en-US", "en", "en_US")

# The scan's two projects (G2): the layout of antonym_scan.py, reproduced.
OLD = [
    {"name": "nocobase", "repo": "nocobase/nocobase", "commit": "10810697c31f85d6f2ad7eaa0a0e1990970ea93b",
     "pattern": r"(?P<group>(?:[^/]+/)*locales?)/(?P<lang>[^/]+)\.json", "refs": SCAN_REFS,
     "skip_en": False},
    {"name": "mastodon", "repo": "mastodon/mastodon", "commit": "cab53a591ec66159c31b4853271fd15f9e2bbb80",
     "pattern": r"(?P<group>app/javascript/mastodon/locales)/(?P<lang>[^/]+)\.json", "refs": SCAN_REFS,
     "skip_en": False},
]
# The new population (G0, G3-G5), pinned before any of it was read.
NEW = [
    {"name": "excalidraw", "repo": "excalidraw/excalidraw", "commit": "e1b7aacb356a492aa1e0fc6eb57b8896124027f0",
     "pattern": r"packages/excalidraw/locales/(?P<lang>[a-z]{2,3}(?:-[A-Za-z]{2,4})?)\.json", "refs": ("en",),
     "skip_en": True},
    {"name": "immich", "repo": "immich-app/immich", "commit": "53618ff7496ee313d1cff7b3bcdf19c82b765cdf",
     "pattern": r"i18n/(?P<lang>[a-z]{2,3}(?:_[A-Za-z]{2,4})?)\.json", "refs": ("en",), "skip_en": True},
    {"name": "lobe-chat", "repo": "lobehub/lobe-chat", "commit": "5310a6f1d0f2c530819f7328433988ea2b892eae",
     "pattern": r"locales/(?P<lang>[a-z]{2}(?:-[A-Z]{2})?)/(?P<group>[A-Za-z-]+)\.json", "refs": ("en-US",),
     "skip_en": True},
    {"name": "element-web", "repo": "element-hq/element-web", "commit": "fc4d45cce130f3dce0d824ecef87bd948bcef842",
     "pattern": r"apps/web/src/i18n/strings/(?P<lang>[a-z]{2,3}(?:_[A-Za-z]{2,4})?)\.json", "refs": ("en_EN",),
     "skip_en": True},
    {"name": "jitsi-meet", "repo": "jitsi/jitsi-meet", "commit": "f4a1c17e45a7d6d5b8e51a57af276fdcfa2d2473",
     "pattern": r"lang/main(?:-(?P<lang>[A-Za-z]{2,3}(?:-[A-Za-z]{2,4})?))?\.json", "refs": ("en",),
     "skip_en": True},
]
SOURCE_EXT = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue", ".svelte", ".dart", ".html", ".py")
MAX_SOURCE_BYTES = 2000000
LITERAL = re.compile(r"""'([^'\\\n]{1,300})'|"([^"\\\n]{1,300})"|`([^`\\\n$]{1,300})`""")
PLURAL = re.compile(r"[._|](?:zero|one|two|few|many|other)$")
MIN_LOCALES = 10
MIN_WARNINGS = 20
MIN_PROJECTS = 3
SAMPLE = 60
SEED = 120
MIN_USED_SHARE = 0.5


def load_guard(path):
    spec = importlib.util.spec_from_file_location("guard_0120", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def locale_file(project, path):
    """(group, lang) when path is one of the project's locale files, else None."""
    if "node_modules" in path.split("/"):
        return None
    m = re.fullmatch(project["pattern"], path)
    if not m:
        return None
    d = m.groupdict()
    return d.get("group") or "", d.get("lang") or project["refs"][0]


def literals(text):
    """The contents of the single-, double- and back-quoted strings in text."""
    return {a or b or c for a, b, c in LITERAL.findall(text)}


def key_candidates(key, group=""):
    """Ways code may name a catalog key: as is, with | for . (Element's _t),
    without a plural suffix, and namespaced (i18next's ns:key)."""
    out = {key, key.replace(".", "|")}
    base = PLURAL.sub("", key)
    if base != key:
        out.update({base, base.replace(".", "|")})
    if group:
        out.update("%s:%s" % (group, k) for k in list(out))
    return out


def used(key, group, found):
    return any(c in found for c in key_candidates(key, group))


def parse(data):
    try:
        obj = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


def read_project(project, fileobj, want_literals):
    """({group: {lang: bytes}}, set of code literals) from a .tar.gz stream."""
    files, found = {}, set()
    with tarfile.open(fileobj=fileobj, mode="r|gz") as tar:
        for member in tar:
            if not member.isfile() or "/" not in member.name:
                continue
            path = member.name.split("/", 1)[1]
            loc = locale_file(project, path)
            if loc:
                files.setdefault(loc[0], {})[loc[1]] = tar.extractfile(member).read()
            elif (want_literals and path.endswith(SOURCE_EXT) and member.size <= MAX_SOURCE_BYTES
                  and "node_modules" not in path.split("/")):
                found |= literals(tar.extractfile(member).read().decode("utf-8", "replace"))
    return files, found


def scan(g, project, files):
    """Per-project totals and one row per antonym-collision warning."""
    res = {"groups": 0, "locale_files": 0, "unparsed": [], "no_reference": [], "pairs": 0,
           "comparisons": 0, "copies": 0, "rows": [], "consistent": True}
    for group in sorted(files):
        langs = files[group]
        ref_lang = next((r for r in project["refs"] if r in langs), None)
        if ref_lang is None:
            res["no_reference"].append(group)
            continue
        ref = parse(langs[ref_lang])
        if ref is None:
            res["unparsed"].append("%s/%s" % (group, ref_lang))
            continue
        src = g.flatten(ref)
        pairs = g.antonym_pairs(src)
        res["groups"] += 1
        res["pairs"] += len(pairs)
        for lang in sorted(langs):
            if lang in project["refs"] or (project["skip_en"] and lang.lower().startswith("en")):
                continue
            target = parse(langs[lang])
            if target is None:
                res["unparsed"].append("%s/%s" % (group, lang))
                continue
            res["locale_files"] += 1
            tgt = g.flatten(target)
            for k1, k2 in pairs:
                v1, v2 = tgt.get(k1), tgt.get(k2)
                if isinstance(v1, str) and isinstance(v2, str) and v1.strip() and v2.strip():
                    res["comparisons"] += 1
                    if v1.strip() == v2.strip() and v1.strip().casefold() in (
                            src[k1].strip().casefold(), src[k2].strip().casefold()):
                        res["copies"] += 1
            warned = [p for p in g.check_catalog(ref, target) if p["code"] == "antonym-collision"]
            if len(warned) != len(g._antonym_collisions(src, tgt)):
                res["consistent"] = False
            for p in warned:
                k1, k2 = p["key"], p["other_key"]
                res["rows"].append({"project": project["name"], "group": group, "locale": lang,
                                    "key1": k1, "key2": k2, "en1": src[k1], "en2": src[k2],
                                    "value": tgt[k1].strip()})
    return res


def published_rows():
    req = urllib.request.Request(PUBLISHED, headers={"User-Agent": "mv2-l10n-guard-eval"})
    with urllib.request.urlopen(req, timeout=60) as r:
        text = r.read().decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    return sorted((r["project"], r["dir"], r["locale"], r["key1"], r["key2"])
                  for r in rows if r["kind"] == "flagged")


def sample(rows):
    ordered = sorted(rows, key=lambda r: (r["project"], r["group"], r["locale"], r["key1"], r["key2"]))
    if len(ordered) <= SAMPLE:
        return ordered
    picked = random.Random(SEED).sample(range(len(ordered)), SAMPLE)
    return [ordered[i] for i in sorted(picked)]


def write_csv(path, rows, fields):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--guard-dir", default="/out/0120")
    parser.add_argument("--out-dir", default="/out/0120-eval")
    args = parser.parse_args()
    g = load_guard(os.path.join(args.guard_dir, "l10n_guard.py"))
    print("l10n-guard %s" % g.__version__)
    os.makedirs(args.out_dir, exist_ok=True)

    results = {}
    for project in OLD + NEW:
        new = project in NEW
        url = CODELOAD % (project["repo"], project["commit"])
        req = urllib.request.Request(url, headers={"User-Agent": "mv2-l10n-guard-eval"})
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                files, found = read_project(project, r, new)
        except (OSError, EOFError, ValueError, tarfile.TarError) as exc:
            results[project["name"]] = {"error": "%s: %s" % (type(exc).__name__, exc)}
            print("%s: NOT DOWNLOADED (%s)" % (project["name"], exc))
            continue
        res = scan(g, project, files)
        if new:
            for row in res["rows"]:
                row["key1_used"] = used(row["key1"], row["group"], found)
                row["key2_used"] = used(row["key2"], row["group"], found)
            res["code_literals"] = len(found)
        res.update(repo=project["repo"], commit=project["commit"])
        results[project["name"]] = res
        per = 1000.0 * len(res["rows"]) / res["comparisons"] if res["comparisons"] else 0.0
        print("%s @%s: %d groups, %d locale files, %d unparsed, %d without reference, %d pairs, "
              "%d comparisons, %d warnings, %d copies, %.2f per 1,000, consistent %s"
              % (project["name"], project["commit"][:8], res["groups"], res["locale_files"],
                 len(res["unparsed"]), len(res["no_reference"]), res["pairs"], res["comparisons"],
                 len(res["rows"]), res["copies"], per, res["consistent"]))
        for row in res["rows"]:
            print("  %s %s %s: %r / %r = %r%s" % (row["project"], row["group"], row["locale"], row["key1"],
                                                  row["key2"], row["value"],
                                                  " used %s/%s" % (row["key1_used"], row["key2_used"])
                                                  if new else ""))

    def ok(name):
        return name in results and "error" not in results[name]

    g0_detail = {p["name"]: (results.get(p["name"], {}).get("locale_files", 0) if ok(p["name"]) else "error")
                 for p in NEW}
    g0 = (all(ok(p["name"]) for p in OLD + NEW)
          and all(results[p["name"]]["groups"] > 0 and results[p["name"]]["locale_files"] >= MIN_LOCALES
                  for p in NEW))

    try:
        expected = published_rows()
        g2_error = None
    except (OSError, ValueError, KeyError) as exc:
        expected, g2_error = [], "%s: %s" % (type(exc).__name__, exc)
    got = sorted((r["project"], r["group"], r["locale"], r["key1"], r["key2"])
                 for p in OLD if ok(p["name"]) for r in results[p["name"]]["rows"])
    g2 = (g2_error is None and all(ok(p["name"]) for p in OLD) and got == expected and len(expected) == 27)

    new_rows = [r for p in NEW if ok(p["name"]) for r in results[p["name"]]["rows"]]
    projects_hit = sorted({r["project"] for r in new_rows})
    g3 = len(new_rows) >= MIN_WARNINGS and len(projects_hit) >= MIN_PROJECTS
    both = sum(1 for r in new_rows if r["key1_used"] and r["key2_used"])
    g5 = bool(new_rows) and both >= MIN_USED_SHARE * len(new_rows)
    consistent = all(results[p["name"]]["consistent"] for p in OLD + NEW if ok(p["name"]))

    checks = [
        ("G0", "all seven tarballs download; each new project has its reference and >= %d locale files"
               % MIN_LOCALES, g0, "locale files %s" % g0_detail),
        ("G2", "NocoBase and Mastodon warnings = the 27 flagged rows of the published collisions.csv", g2,
         "published %d, guard %d, missing %s, extra %s%s"
         % (len(expected), len(got), sorted(set(expected) - set(got))[:5] or "none",
            sorted(set(got) - set(expected))[:5] or "none", "; error %s" % g2_error if g2_error else "")),
        ("G3", ">= %d warnings on the new projects, from >= %d of 5" % (MIN_WARNINGS, MIN_PROJECTS), g3,
         "%d warnings from %s" % (len(new_rows), projects_hit or "none")),
        ("G5", ">= %d%% of the new warnings have both keys found as literals in the project's code"
               % int(MIN_USED_SHARE * 100), g5,
         "%d of %d (%.0f%%)" % (both, len(new_rows), 100.0 * both / len(new_rows) if new_rows else 0.0)),
    ]
    for name, text, held, value in checks:
        print("%s %s: %s (%s)" % (name, "HELD" if held else "FAILED", text, value))
    print("check_catalog and _antonym_collisions agree on every file: %s" % consistent)
    print("G1 is graded from the test steps; G4 by hand from sample.csv")

    fields = ["project", "group", "locale", "key1", "key2", "en1", "en2", "value", "key1_used", "key2_used"]
    write_csv(os.path.join(args.out_dir, "warnings.csv"),
              [r for p in OLD + NEW if ok(p["name"]) for r in results[p["name"]]["rows"]], fields)
    write_csv(os.path.join(args.out_dir, "sample.csv"), sample(new_rows), fields + ["verdict", "note"])
    with open(os.path.join(args.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump({"guard": g.__version__, "consistent": consistent,
                   "projects": {n: {k: v for k, v in r.items() if k != "rows"} for n, r in results.items()},
                   "predictions": [{"id": n, "text": t, "held": h, "value": v} for n, t, h, v in checks]},
                  f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
