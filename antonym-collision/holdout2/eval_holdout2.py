#!/usr/bin/env python3
"""Second held-out test of l10n-guard 0.12.0's antonym-collision warning, on
five projects it has never seen, graded against the predictions written
before any of their translations was read (census
antonym-collision/HOLDOUT2-PREREG.md):

  H0 all five codeload tarballs download; each project has its English
     reference and at least 10 locale files that parse.
  H1 at least 20 warnings in total, from at least 3 of the 5 projects.
  H2 (graded by hand, from sample-main.csv) of a seeded sample of up to 60
     warnings outside the UPLOAD class, at least 60% of those judged are real
     defects; at least 20 must be judged or H2 is "not tested".
  H3 (graded by hand, from sample-upload.csv) of a seeded sample of up to 30
     UPLOAD-class warnings, fewer than 50% of those judged are real defects;
     at least 5 must be judged or H3 is "not tested".
  H4 at least 50% of the warnings have both keys found as a string literal in
     the project's own code.
  H5 at least 50% of the UPLOAD-class warnings are in French or Arabic
     locales (codes starting fr or ar); at least 5 must exist or "not tested".

The guard is the released v0.12.0 file, unchanged:

  python eval_holdout2.py --fetch-guard --guard-dir /out/guard
  python eval_holdout2.py --guard-dir /out/guard --out-dir /out/holdout2

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

GUARD_URL = "https://raw.githubusercontent.com/munimtechnologies/l10n-guard/v0.12.0/l10n_guard.py"
GUARD_VERSION = "0.12.0"
PREREG_URL = ("https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/"
              "main/antonym-collision/HOLDOUT2-PREREG.md")
CODELOAD = "https://codeload.github.com/%s/tar.gz/%s"
LANG = r"(?P<lang>[A-Za-z]{2,3}(?:[-_@][A-Za-z0-9]{2,8})*)"

# Picked by layout only, before any of their translations was read. The
# default branch's head at run time is used; its commit is recorded from the
# archive's pax header.
PROJECTS = [
    {"name": "jellyfin-web", "repo": "jellyfin/jellyfin-web", "ref": "master",
     "pattern": r"src/strings/" + LANG + r"\.json", "refs": ("en-us",)},
    {"name": "uptime-kuma", "repo": "louislam/uptime-kuma", "ref": "master",
     "pattern": r"src/lang/" + LANG + r"\.json", "refs": ("en",)},
    {"name": "rocket-chat", "repo": "RocketChat/Rocket.Chat", "ref": "develop",
     "pattern": r"packages/i18n/src/locales/" + LANG + r"\.i18n\.json", "refs": ("en",)},
    {"name": "mattermost", "repo": "mattermost/mattermost", "ref": "master",
     "pattern": r"webapp/channels/src/i18n/" + LANG + r"\.json", "refs": ("en",)},
    {"name": "bitwarden-web", "repo": "bitwarden/clients", "ref": "main",
     "pattern": r"apps/web/src/locales/" + LANG + r"/messages\.json", "refs": ("en",)},
]
SOURCE_EXT = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue", ".svelte", ".dart", ".html", ".py")
MAX_SOURCE_BYTES = 2000000
LITERAL = re.compile(r"""'([^'\\\n]{1,300})'|"([^"\\\n]{1,300})"|`([^`\\\n$]{1,300})`""")
PLURAL = re.compile(r"[._|](?:zero|one|two|few|many|other)$")
MESSAGE = re.compile(r"\.message$")
UPLOAD = "UPLOAD"
MIN_LOCALES = 10
MIN_WARNINGS = 20
MIN_PROJECTS = 3
SAMPLE_MAIN = 60
SAMPLE_UPLOAD = 30
SEED_MAIN = 130
SEED_UPLOAD = 131
MIN_USED_SHARE = 0.5
MIN_UPLOAD = 5
FIELDS = ["project", "locale", "key1", "key2", "en1", "en2", "value", "classes", "key1_used", "key2_used"]


def fetch_guard(guard_dir):
    """Fetches the released guard, but only once the pre-registration is
    public: without the guard the evaluation cannot run, so no translation is
    read before HOLDOUT2-PREREG.md is on main."""
    req = urllib.request.Request(PREREG_URL, headers={"User-Agent": "mv2-l10n-guard-eval"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            prereg = r.read()
    except OSError as exc:
        print("pre-registration not public yet (%s); stopping" % exc)
        return 1
    print("HOLDOUT2-PREREG.md: %d bytes, sha256 %s" % (len(prereg), hashlib.sha256(prereg).hexdigest()[:16]))
    req = urllib.request.Request(GUARD_URL, headers={"User-Agent": "mv2-l10n-guard-eval"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    os.makedirs(guard_dir, exist_ok=True)
    path = os.path.join(guard_dir, "l10n_guard.py")
    with open(path, "wb") as f:
        f.write(data)
    g = load_guard(path)
    print("l10n_guard.py %s: %d bytes, sha256 %s" % (g.__version__, len(data), hashlib.sha256(data).hexdigest()[:16]))
    return 0 if g.__version__ == GUARD_VERSION else 1


def load_guard(path):
    spec = importlib.util.spec_from_file_location("guard_holdout2", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def read_project(project, fileobj, want_literals=True):
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
            elif (want_literals and path.endswith(SOURCE_EXT) and member.size <= MAX_SOURCE_BYTES
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
    """Per-project totals and one row per antonym-collision warning."""
    res = {"locale_files": 0, "unparsed": [], "reference": None, "pairs": 0, "comparisons": 0,
           "copies": 0, "rows": [], "consistent": True, "identical": identical_files(project, files)}
    ref_lang = next((r for r in project["refs"] if r in files), None)
    ref = parse(files[ref_lang]) if ref_lang else None
    if ref is None:
        return res
    res["reference"] = ref_lang
    src = g.flatten(ref)
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
            res["rows"].append({"project": project["name"], "locale": lang, "key1": k1, "key2": k2,
                                "en1": src[k1], "en2": src[k2], "value": tgt[k1].strip(),
                                "classes": flip_classes(g, src[k1], src[k2])})
    return res


def is_upload(row):
    return row["classes"] == UPLOAD


def sample(rows, size, seed):
    ordered = sorted(rows, key=lambda r: (r["project"], r["locale"], r["key1"], r["key2"]))
    if len(ordered) <= size:
        return ordered
    picked = random.Random(seed).sample(range(len(ordered)), size)
    return [ordered[i] for i in sorted(picked)]


def french_or_arabic(row):
    return row["locale"].lower().startswith(("fr", "ar"))


def write_csv(path, rows, fields):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--guard-dir", default="/out/guard")
    parser.add_argument("--out-dir", default="/out/holdout2")
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
        url = CODELOAD % (project["repo"], project["ref"])
        req = urllib.request.Request(url, headers={"User-Agent": "mv2-l10n-guard-eval"})
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                files, found, commit = read_project(project, r)
        except (OSError, EOFError, ValueError, tarfile.TarError) as exc:
            results[project["name"]] = {"error": "%s: %s" % (type(exc).__name__, exc)}
            print("%s: NOT DOWNLOADED (%s)" % (project["name"], exc))
            continue
        res = scan(g, project, files)
        for row in res["rows"]:
            row["key1_used"] = used(row["key1"], found)
            row["key2_used"] = used(row["key2"], found)
        res.update(repo=project["repo"], ref=project["ref"], commit=commit, code_literals=len(found))
        results[project["name"]] = res
        per = 1000.0 * len(res["rows"]) / res["comparisons"] if res["comparisons"] else 0.0
        print("%s @%s: reference %s, %d locale files, %d unparsed, %d pairs, %d comparisons, "
              "%d warnings, %d copies, %.2f per 1,000, identical files %s, consistent %s"
              % (project["name"], commit[:8] or "?", res["reference"], res["locale_files"],
                 len(res["unparsed"]), res["pairs"], res["comparisons"], len(res["rows"]), res["copies"],
                 per, res["identical"] or "none", res["consistent"]))
        for row in res["rows"]:
            print("  %s %s [%s]: %r / %r = %r used %s/%s" % (row["project"], row["locale"], row["classes"],
                                                            row["key1"], row["key2"], row["value"],
                                                            row["key1_used"], row["key2_used"]))

    def ok(name):
        return name in results and "error" not in results[name]

    h0_detail = {p["name"]: (results[p["name"]]["locale_files"] if ok(p["name"]) else "error") for p in PROJECTS}
    h0 = all(ok(p["name"]) and results[p["name"]]["reference"] and results[p["name"]]["locale_files"] >= MIN_LOCALES
             for p in PROJECTS)
    rows = [r for p in PROJECTS if ok(p["name"]) for r in results[p["name"]]["rows"]]
    projects_hit = sorted({r["project"] for r in rows})
    h1 = len(rows) >= MIN_WARNINGS and len(projects_hit) >= MIN_PROJECTS
    both = sum(1 for r in rows if r["key1_used"] and r["key2_used"])
    h4 = bool(rows) and both >= MIN_USED_SHARE * len(rows)
    upload = [r for r in rows if is_upload(r)]
    main_rows = [r for r in rows if not is_upload(r)]
    fr_ar = sum(1 for r in upload if french_or_arabic(r))
    h5 = None if len(upload) < MIN_UPLOAD else fr_ar >= 0.5 * len(upload)
    consistent = all(results[p["name"]]["consistent"] for p in PROJECTS if ok(p["name"]))
    by_class = {}
    for r in rows:
        by_class[r["classes"]] = by_class.get(r["classes"], 0) + 1

    checks = [
        ("H0", "all five tarballs download; each project has its reference and >= %d locale files" % MIN_LOCALES,
         h0, "locale files %s" % h0_detail),
        ("H1", ">= %d warnings, from >= %d of 5 projects" % (MIN_WARNINGS, MIN_PROJECTS), h1,
         "%d warnings from %s" % (len(rows), projects_hit or "none")),
        ("H4", ">= %d%% of the warnings have both keys found as literals in the project's code"
               % int(MIN_USED_SHARE * 100), h4,
         "%d of %d (%.0f%%)" % (both, len(rows), 100.0 * both / len(rows) if rows else 0.0)),
        ("H5", ">= 50%% of the UPLOAD-class warnings are in fr*/ar* locales (>= %d needed)" % MIN_UPLOAD, h5,
         "%d of %d" % (fr_ar, len(upload))),
    ]
    for name, text, held, value in checks:
        print("%s %s: %s (%s)" % (name, "NOT TESTED" if held is None else "HELD" if held else "FAILED",
                                  text, value))
    print("warnings by class: %s" % json.dumps(by_class, sort_keys=True))
    print("UPLOAD class: %d warnings; other classes: %d" % (len(upload), len(main_rows)))
    print("check_catalog and _antonym_collisions agree on every file: %s" % consistent)
    print("H2 and H3 are graded by hand from sample-main.csv and sample-upload.csv")

    write_csv(os.path.join(args.out_dir, "warnings.csv"), rows, FIELDS)
    write_csv(os.path.join(args.out_dir, "sample-main.csv"), sample(main_rows, SAMPLE_MAIN, SEED_MAIN),
              FIELDS + ["verdict", "note"])
    write_csv(os.path.join(args.out_dir, "sample-upload.csv"), sample(upload, SAMPLE_UPLOAD, SEED_UPLOAD),
              FIELDS + ["verdict", "note"])
    with open(os.path.join(args.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump({"guard": g.__version__, "consistent": consistent, "by_class": by_class,
                   "upload_warnings": len(upload), "other_warnings": len(main_rows),
                   "projects": {n: {k: v for k, v in r.items() if k != "rows"} for n, r in results.items()},
                   "predictions": [{"id": n, "text": t, "held": h, "value": v} for n, t, h, v in checks]},
                  f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
