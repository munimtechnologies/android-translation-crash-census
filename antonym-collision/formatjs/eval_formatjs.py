#!/usr/bin/env python3
"""Evaluates l10n-guard 0.14.0's reading of FormatJS descriptor files on
Mattermost, the project the second held-out antonym-collision test could not
read, with the four other projects of that test as controls, against the
predictions in the census's antonym-collision/FORMATJS-PREREG.md, written
before any Mattermost translation was compared:

  P0 Mattermost's en.json is a descriptor file (every value an object with a
     string defaultMessage) and at least 20 locale files parse as objects.
  P1 With v0.14.0 Mattermost has at least 1,000 comparisons; with v0.13.0,
     on the same tarball, it has 0.
  P2 With v0.14.0, check_catalog(en.json, de.json) reports fewer than 5% of
     the source keys as missing (v0.13.0 reports every one).
  P3 At least 1 antonym-collision warning across Mattermost's locales, and
     at most 5.0 per 1,000 comparisons.
  P4 (graded by hand, from sample.csv) at least 60% of the judged Mattermost
     warnings are real defects; at least 5 must be judged or "not tested".
  P5 On the four control projects at their HOLDOUT2 commits, v0.14.0 raises
     exactly the 36 warnings outside the upload/download class that v0.12.0
     raised there (holdout2-results/warnings.csv), and no others.

  python eval_formatjs.py --fetch-guard --guard-dir /out/guard
  python eval_formatjs.py --guard-dir /out/guard --out-dir /out/formatjs

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
import random
import re
import sys
import tarfile
import urllib.request

RAW = "https://raw.githubusercontent.com/"
GUARD_URL = RAW + "munimtechnologies/l10n-guard/v0.14.0/l10n_guard.py"
BASELINE_URL = RAW + "munimtechnologies/l10n-guard/v0.13.0/l10n_guard.py"
GUARD_VERSION = "0.14.0"
BASELINE_VERSION = "0.13.0"
CENSUS = RAW + "munimtechnologies/android-translation-crash-census/main/antonym-collision/"
PREREG_URL = CENSUS + "FORMATJS-PREREG.md"
HOLDOUT2_URL = CENSUS + "holdout2-results/warnings.csv"
CODELOAD = "https://codeload.github.com/%s/tar.gz/%s"
LANG = r"(?P<lang>[A-Za-z]{2,3}(?:[-_@][A-Za-z0-9]{2,8})*)"
HEADERS = {"User-Agent": "mv2-l10n-guard-eval"}

# Mattermost's default branch at run time (commit recorded from the archive's
# pax header); the controls at the exact commits of the second held-out test.
PROJECTS = [
    {"name": "mattermost", "repo": "mattermost/mattermost", "ref": "master", "role": "test",
     "pattern": r"webapp/channels/src/i18n/" + LANG + r"\.json", "refs": ("en",), "keys_locale": "de"},
    {"name": "jellyfin-web", "repo": "jellyfin/jellyfin-web", "role": "control",
     "ref": "ee8efb417e5377ba444509a68ed22af33e45950b",
     "pattern": r"src/strings/" + LANG + r"\.json", "refs": ("en-us",)},
    {"name": "uptime-kuma", "repo": "louislam/uptime-kuma", "role": "control",
     "ref": "b092505f894d66669b67f46e1da72b51016eceab",
     "pattern": r"src/lang/" + LANG + r"\.json", "refs": ("en",)},
    {"name": "rocket-chat", "repo": "RocketChat/Rocket.Chat", "role": "control",
     "ref": "ad2047e71dbe67aebb21b37ed9e2dc21cf92721b",
     "pattern": r"packages/i18n/src/locales/" + LANG + r"\.i18n\.json", "refs": ("en",)},
    {"name": "bitwarden-web", "repo": "bitwarden/clients", "role": "control",
     "ref": "9e54ce7b43b14685eec31aaae49b1328f1378f8d",
     "pattern": r"apps/web/src/locales/" + LANG + r"/messages\.json", "refs": ("en",)},
]
SOURCE_EXT = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue", ".svelte", ".dart", ".html", ".py")
MAX_SOURCE_BYTES = 2000000
LITERAL = re.compile(r"""'([^'\\\n]{1,300})'|"([^"\\\n]{1,300})"|`([^`\\\n$]{1,300})`""")
PLURAL = re.compile(r"[._|](?:zero|one|two|few|many|other)$")
MESSAGE = re.compile(r"\.message$")
UPLOAD = "UPLOAD"
MIN_LOCALES = 20
MIN_COMPARISONS = 1000
MAX_MISSING_SHARE = 0.05
MAX_PER_1000 = 5.0
SAMPLE_SIZE = 40
SAMPLE_SEED = 140
FIELDS = ["project", "role", "locale", "key1", "key2", "en1", "en2", "value", "classes", "key1_used", "key2_used"]


def get(url, timeout=60):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_guard(guard_dir):
    """Fetches the released guards, but only once the pre-registration is
    public: without the guard the evaluation cannot run, so no translation is
    compared before FORMATJS-PREREG.md is on main."""
    try:
        prereg = get(PREREG_URL)
    except OSError as exc:
        print("pre-registration not public yet (%s); stopping" % exc)
        return 1
    print("FORMATJS-PREREG.md: %d bytes, sha256 %s" % (len(prereg), hashlib.sha256(prereg).hexdigest()[:16]))
    ok = True
    for url, version, sub in ((GUARD_URL, GUARD_VERSION, ""), (BASELINE_URL, BASELINE_VERSION, "baseline")):
        try:
            data = get(url)
        except OSError as exc:
            print("l10n-guard v%s not released yet (%s); stopping" % (version, exc))
            return 1
        folder = os.path.join(guard_dir, sub) if sub else guard_dir
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, "l10n_guard.py")
        with open(path, "wb") as f:
            f.write(data)
        g = load_guard(path, "guard_" + version.replace(".", "_"))
        print("l10n_guard.py %s: %d bytes, sha256 %s" % (g.__version__, len(data), hashlib.sha256(data).hexdigest()[:16]))
        ok = ok and g.__version__ == version
    return 0 if ok else 1


def load_guard(path, name="guard_formatjs"):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def unwrap(g, data):
    """0.14.0's unwrap_descriptors when the guard has it; older guards leave
    the catalog as it is."""
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


def read_project(project, fileobj, want_literals):
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
    """Per-project totals and one row per antonym-collision warning, with the
    given guard. check_catalog gets the raw catalogs, as the command line
    would; the comparison count uses the same unwrapping the guard applies."""
    res = {"guard": g.__version__, "locale_files": 0, "unparsed": [], "reference": None, "descriptor": False,
           "source_keys": 0, "pairs": 0, "comparisons": 0, "rows": [], "consistent": True,
           "identical": identical_files(project, files)}
    ref_lang = next((r for r in project["refs"] if r in files), None)
    ref = parse(files[ref_lang]) if ref_lang else None
    if ref is None:
        return res
    res["reference"] = ref_lang
    source = unwrap(g, ref)
    res["descriptor"] = source is not ref and all(isinstance(v, str) for v in source.values())
    src = g.flatten(source)
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
            res["rows"].append({"project": project["name"], "role": project["role"], "locale": lang,
                                "key1": k1, "key2": k2, "en1": src[k1], "en2": src[k2],
                                "value": tgt[k1].strip(), "classes": flip_classes(g, src[k1], src[k2])})
    return res


def key_counts(g, ref, target):
    """missing-key and extra-key counts of check_catalog on two raw catalogs,
    with the number of flattened source keys the guard compares against."""
    problems = g.check_catalog(ref, target)
    return {"guard": g.__version__,
            "missing": sum(1 for p in problems if p["code"] == "missing-key"),
            "extra": sum(1 for p in problems if p["code"] == "extra-key"),
            "source_keys": len(g.flatten(unwrap(g, ref)))}


def row_key(row):
    return (row["project"], row["locale"], row["key1"], row["key2"])


def expected_rows(csv_text):
    """The second held-out test's warnings outside the UPLOAD class, as sorted
    (project, locale, key1, key2) tuples; duplicates kept."""
    rows = csv.DictReader(io.StringIO(csv_text))
    return sorted(row_key(r) for r in rows if r["classes"] != UPLOAD)


def sample(rows, size, seed):
    ordered = sorted(rows, key=row_key)
    if len(ordered) <= size:
        return ordered
    picked = random.Random(seed).sample(range(len(ordered)), size)
    return [ordered[i] for i in sorted(picked)]


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
    parser.add_argument("--out-dir", default="/out/formatjs")
    parser.add_argument("--fetch-guard", action="store_true")
    args = parser.parse_args()
    if args.fetch_guard:
        return fetch_guard(args.guard_dir)
    g = load_guard(os.path.join(args.guard_dir, "l10n_guard.py"), "guard_new")
    b = load_guard(os.path.join(args.guard_dir, "baseline", "l10n_guard.py"), "guard_baseline")
    print("l10n-guard %s (baseline %s)" % (g.__version__, b.__version__))
    if g.__version__ != GUARD_VERSION or b.__version__ != BASELINE_VERSION:
        print("expected l10n-guard %s and %s; stopping" % (GUARD_VERSION, BASELINE_VERSION))
        return 1
    os.makedirs(args.out_dir, exist_ok=True)
    expected = expected_rows(get(HOLDOUT2_URL).decode("utf-8-sig"))
    print("holdout2 warnings outside UPLOAD: %d" % len(expected))

    results = {}
    for project in PROJECTS:
        name = project["name"]
        url = CODELOAD % (project["repo"], project["ref"])
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=900) as r:
                files, found, commit = read_project(project, r, want_literals=project["role"] == "test")
        except (OSError, EOFError, ValueError, tarfile.TarError) as exc:
            results[name] = {"error": "%s: %s" % (type(exc).__name__, exc)}
            print("%s: NOT DOWNLOADED (%s)" % (name, exc))
            continue
        res = {"repo": project["repo"], "ref": project["ref"], "commit": commit, "role": project["role"],
               "new": scan(g, project, files)}
        if project["role"] == "test":
            res["baseline"] = scan(b, project, files)
            res["code_literals"] = len(found)
            for row in res["new"]["rows"]:
                row["key1_used"] = used(row["key1"], found)
                row["key2_used"] = used(row["key2"], found)
            ref_lang, keys_lang = res["new"]["reference"], project.get("keys_locale")
            if ref_lang and keys_lang in files and parse(files[keys_lang]) is not None:
                ref, target = parse(files[ref_lang]), parse(files[keys_lang])
                res["keys"] = {"locale": keys_lang, "new": key_counts(g, ref, target),
                               "baseline": key_counts(b, ref, target)}
        results[name] = res
        for label in ("new", "baseline"):
            if label not in res:
                continue
            s = res[label]
            per = 1000.0 * len(s["rows"]) / s["comparisons"] if s["comparisons"] else 0.0
            print("%s @%s with %s: reference %s, descriptor %s, %d source keys, %d locale files, %d unparsed, "
                  "%d pairs, %d comparisons, %d warnings, %.2f per 1,000, identical files %s, consistent %s"
                  % (name, commit[:8] or "?", s["guard"], s["reference"], s["descriptor"], s["source_keys"],
                     s["locale_files"], len(s["unparsed"]), s["pairs"], s["comparisons"], len(s["rows"]), per,
                     s["identical"] or "none", s["consistent"]))
        if "keys" in res:
            for label in ("new", "baseline"):
                k = res["keys"][label]
                print("  %s en.json vs %s.json with %s: %d source keys, %d missing-key, %d extra-key"
                      % (name, res["keys"]["locale"], k["guard"], k["source_keys"], k["missing"], k["extra"]))
        for row in res["new"]["rows"]:
            print("  %s %s [%s]: %r / %r = %r used %s/%s" % (name, row["locale"], row["classes"], row["key1"],
                                                            row["key2"], row["value"], row.get("key1_used", "-"),
                                                            row.get("key2_used", "-")))

    def ok(name):
        return name in results and "error" not in results[name]

    mm = results.get("mattermost", {})
    mm_ok = ok("mattermost") and bool(mm["new"]["reference"])
    new, base = (mm["new"], mm["baseline"]) if mm_ok else ({}, {})
    rows_mm = new["rows"] if mm_ok else []
    per_mm = 1000.0 * len(rows_mm) / new["comparisons"] if mm_ok and new["comparisons"] else 0.0
    p0 = mm_ok and new["descriptor"] and new["locale_files"] >= MIN_LOCALES
    p1 = mm_ok and new["comparisons"] >= MIN_COMPARISONS and base["comparisons"] == 0
    keys = mm.get("keys") if mm_ok else None
    p2 = None if not keys else keys["new"]["missing"] < MAX_MISSING_SHARE * keys["new"]["source_keys"]
    p3 = mm_ok and len(rows_mm) >= 1 and per_mm <= MAX_PER_1000
    controls = [p["name"] for p in PROJECTS if p["role"] == "control"]
    controls_ok = all(ok(n) for n in controls)
    actual = sorted(row_key(r) for n in controls if ok(n) for r in results[n]["new"]["rows"])
    p5 = controls_ok and actual == expected
    consistent = all(results[n][label]["consistent"] for n in results if ok(n)
                     for label in ("new", "baseline") if label in results[n])

    checks = [
        ("P0", "Mattermost en.json is a descriptor file and >= %d locale files parse" % MIN_LOCALES, p0,
         "descriptor %s, %s locale files" % (new.get("descriptor"), new.get("locale_files"))),
        ("P1", "Mattermost: >= %d comparisons with %s and 0 with %s" % (MIN_COMPARISONS, GUARD_VERSION, BASELINE_VERSION),
         p1, "%s and %s" % (new.get("comparisons"), base.get("comparisons"))),
        ("P2", "Mattermost en.json vs de.json: < %d%% of source keys missing with %s"
               % (int(MAX_MISSING_SHARE * 100), GUARD_VERSION), p2,
         "%s" % ({l: (keys[l]["missing"], keys[l]["source_keys"]) for l in ("new", "baseline")} if keys else "no de.json")),
        ("P3", "Mattermost: >= 1 warning and <= %.1f per 1,000 comparisons" % MAX_PER_1000, p3,
         "%d warnings, %.2f per 1,000" % (len(rows_mm), per_mm)),
        ("P5", "controls: exactly the %d holdout2 warnings outside UPLOAD" % len(expected), p5,
         "%d rows; downloaded %s; only in new: %s; only in holdout2: %s"
         % (len(actual), controls_ok, sorted(set(actual) - set(expected)), sorted(set(expected) - set(actual)))),
    ]
    for name, text, held, value in checks:
        print("%s %s: %s (%s)" % (name, verdict(held), text, value))
    by_class = {}
    for r in rows_mm:
        by_class[r["classes"]] = by_class.get(r["classes"], 0) + 1
    print("Mattermost warnings by class: %s" % json.dumps(by_class, sort_keys=True))
    print("check_catalog and _antonym_collisions agree on every file: %s" % consistent)
    print("P4 is graded by hand from sample.csv")

    all_rows = rows_mm + [r for n in controls if ok(n) for r in results[n]["new"]["rows"]]
    write_csv(os.path.join(args.out_dir, "warnings.csv"), all_rows, FIELDS)
    write_csv(os.path.join(args.out_dir, "sample.csv"), sample(rows_mm, SAMPLE_SIZE, SAMPLE_SEED),
              FIELDS + ["verdict", "note"])
    summary = {"guard": g.__version__, "baseline": b.__version__, "consistent": consistent,
               "mattermost_by_class": by_class, "holdout2_expected": len(expected),
               "projects": {n: {k: ({kk: vv for kk, vv in v.items() if kk != "rows"} if isinstance(v, dict) else v)
                                for k, v in r.items()} for n, r in results.items()},
               "predictions": [{"id": n, "text": t, "held": h, "value": v} for n, t, h, v in checks]}
    with open(os.path.join(args.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
