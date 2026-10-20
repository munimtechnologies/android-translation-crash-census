#!/usr/bin/env python3
"""Within-project test on Open Collective's frontend catalogs: do the locales
kept by GitHub agentic workflows (de, es, fr, pt-BR) show a different
antonym-collision rate from the locales kept on Crowdin? Pre-registered in the
census's antonym-collision/OC-LOCALES-PREREG.md before any translation was
compared:

  Q0 en.json parses, >= 18 non-English locale files parse, and the agent
     group found in the archive is exactly de, es, fr, pt-BR.
  Q1 The agent locales carry at least half of all comparisons.
  Q2 The 95% Wilson intervals of the two groups' warning rates overlap
     (NOT TESTED under 500 comparisons in a group or under 5 warnings in all).
  Q3 (graded by hand) at least 60% of judged warnings are real.
  Q4 (graded by hand) among real rows with two hashed ids, under 20% are
     "neither".

  python oc_locales.py --fetch-guard --guard-dir /out/guard
  python oc_locales.py --guard-dir /out/guard --out-dir /out/oc-locales

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
import tarfile
import urllib.request

RAW = "https://raw.githubusercontent.com/"
GUARD_URL = RAW + "munimtechnologies/l10n-guard/v0.14.0/l10n_guard.py"
GUARD_VERSION = "0.14.0"
PREREG_URL = RAW + "munimtechnologies/android-translation-crash-census/main/antonym-collision/OC-LOCALES-PREREG.md"
REPO = "opencollective/opencollective-frontend"
REF = "main"
CODELOAD = "https://codeload.github.com/%s/tar.gz/%s"
HEADERS = {"User-Agent": "mv2-l10n-guard-eval"}
LANG = r"(?P<lang>[A-Za-z]{2,3}(?:[-_@][A-Za-z0-9]{2,8})*)"
LOCALE_FILE = re.compile(r"lang/" + LANG + r"\.json")
WORKFLOW_FILE = re.compile(r"\.github/workflows/i18n-translate-" + LANG + r"\.md")
BASE64_6 = re.compile(r"[A-Za-z0-9+/]{6}")
NON_LETTER = re.compile(r"[0-9+/]")
REFERENCE = "en"
EXPECTED_AGENT = ("de", "es", "fr", "pt-BR")
GROUPS = ("agent", "crowdin")
MIN_LOCALES = 18
MIN_AGENT_SHARE = 0.5
MIN_GROUP_COMPARISONS = 500
MIN_WARNINGS_FOR_Q2 = 5
Z = 1.96
FIELDS = ["locale", "group", "key1", "key2", "kind1", "kind2", "en1", "en2", "value", "classes"]
LOCALE_FIELDS = ["locale", "group", "keys", "translated", "pairs_both_translated", "comparisons",
                 "warnings", "per_1000"]


def get(url, timeout=60):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_guard(guard_dir):
    """Fetches the released guard, but only once the pre-registration is
    public: without the guard nothing can be compared before the page is on main."""
    try:
        prereg = get(PREREG_URL)
    except OSError as exc:
        print("pre-registration not public yet (%s); stopping" % exc)
        return 1
    print("OC-LOCALES-PREREG.md: %d bytes, sha256 %s" % (len(prereg), hashlib.sha256(prereg).hexdigest()[:16]))
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


def load_guard(path, name="guard_oc_locales"):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def unwrap(g, data):
    fn = getattr(g, "unwrap_descriptors", None)
    return fn(data) if fn else data


def locale_of(path):
    """The locale code when path is lang/<tag>.json at the repository root, else None."""
    m = LOCALE_FILE.fullmatch(path)
    return m.group("lang") if m else None


def workflow_locale(path):
    """The locale an agentic translation workflow file is for, else None."""
    m = WORKFLOW_FILE.fullmatch(path)
    return m.group("lang") if m else None


def skipped(lang):
    """The reference and other English variants are not compared."""
    return lang == REFERENCE or lang.lower().startswith("en")


def key_kind(key):
    """hashed: six base64 characters with a digit, + or / (a FormatJS content
    hash for sure); ambiguous: six letters only (a hash or an English word);
    named: anything else."""
    if not BASE64_6.fullmatch(key):
        return "named"
    return "hashed" if NON_LETTER.search(key) else "ambiguous"


def group_of(lang, agents):
    return "agent" if lang in agents else "crowdin"


def parse(data):
    try:
        obj = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


def read_tarball(fileobj):
    """({lang: bytes}, set of agent-workflow locales, commit) from a .tar.gz stream."""
    files, agents = {}, set()
    with tarfile.open(fileobj=fileobj, mode="r|gz") as tar:
        for member in tar:
            if not member.isfile() or "/" not in member.name:
                continue
            path = member.name.split("/", 1)[1]
            lang = locale_of(path)
            if lang:
                files[lang] = tar.extractfile(member).read()
                continue
            lang = workflow_locale(path)
            if lang:
                agents.add(lang)
        commit = tar.pax_headers.get("comment", "")
    return files, agents, commit


def flip_classes(g, en1, en2):
    """The word classes whose antonyms are swapped between two source texts."""
    s1, p1 = g._antonym_signature(en1)
    _, p2 = g._antonym_signature(en2)
    return "+".join(sorted({s1[i] for i, (a, b) in enumerate(zip(p1, p2)) if a and b and a != b}))


def filled(value):
    return isinstance(value, str) and bool(value.strip())


def scan_locale(g, ref, src, pairs, target):
    """Per-locale counts and one row per antonym-collision warning. check_catalog
    gets the raw catalogs, as the command line would."""
    tgt = g.flatten(unwrap(g, target))
    res = {"keys": len(tgt), "translated": 0, "comparisons": 0, "both_translated": 0, "rows": []}
    for k, en in src.items():
        v = tgt.get(k)
        if filled(v) and v != en:
            res["translated"] += 1
    for k1, k2 in pairs:
        v1, v2 = tgt.get(k1), tgt.get(k2)
        if filled(v1) and filled(v2):
            res["comparisons"] += 1
            if v1 != src[k1] and v2 != src[k2]:
                res["both_translated"] += 1
    for p in g.check_catalog(ref, target):
        if p["code"] != "antonym-collision":
            continue
        k1, k2 = p["key"], p["other_key"]
        res["rows"].append({"key1": k1, "key2": k2, "kind1": key_kind(k1), "kind2": key_kind(k2),
                            "en1": src[k1], "en2": src[k2], "value": tgt[k1].strip(),
                            "classes": flip_classes(g, src[k1], src[k2])})
    return res


def rate(warnings, comparisons):
    """Warnings per 1,000 comparisons (0.0 when nothing was compared)."""
    return 1000.0 * warnings / comparisons if comparisons else 0.0


def wilson(k, n, z=Z):
    """95% Wilson score interval for k successes in n trials; (0, 1) when n is 0."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def intervals_overlap(a, b):
    return a[0] <= b[1] and b[0] <= a[1]


def group_totals(locales):
    """{group: {locales, comparisons, warnings, per_1000, per_1000_interval}}."""
    out = {}
    for name in GROUPS:
        rows = [loc for loc in locales if loc["group"] == name]
        comparisons = sum(loc["comparisons"] for loc in rows)
        warnings = sum(loc["warnings"] for loc in rows)
        low, high = wilson(warnings, comparisons)
        out[name] = {"locales": len(rows), "comparisons": comparisons, "warnings": warnings,
                     "per_1000": round(rate(warnings, comparisons), 3),
                     "per_1000_interval": [round(1000.0 * low, 3), round(1000.0 * high, 3)]}
    return out


def q1_check(groups):
    """(held or None, text): the agent locales carry at least MIN_AGENT_SHARE of comparisons."""
    agent, total = groups["agent"]["comparisons"], sum(groups[n]["comparisons"] for n in GROUPS)
    if total == 0:
        return None, "no comparisons"
    share = agent / total
    return share >= MIN_AGENT_SHARE, "agent locales %d of %d comparisons (%.1f%%)" % (agent, total, 100.0 * share)


def q2_check(groups):
    """(held or None, text): the two groups' 95% Wilson intervals overlap."""
    a, c = groups["agent"], groups["crowdin"]
    warnings = a["warnings"] + c["warnings"]
    text = "agent %d/%d, crowdin %d/%d warnings/comparisons" % (a["warnings"], a["comparisons"],
                                                                c["warnings"], c["comparisons"])
    if min(a["comparisons"], c["comparisons"]) < MIN_GROUP_COMPARISONS or warnings < MIN_WARNINGS_FOR_Q2:
        return None, text + " (too few to test)"
    wa, wc = wilson(a["warnings"], a["comparisons"]), wilson(c["warnings"], c["comparisons"])
    text += "; per 1,000: agent %.2f (%.2f-%.2f), crowdin %.2f (%.2f-%.2f)" % (
        rate(a["warnings"], a["comparisons"]), 1000 * wa[0], 1000 * wa[1],
        rate(c["warnings"], c["comparisons"]), 1000 * wc[0], 1000 * wc[1])
    return intervals_overlap(wa, wc), text


def verdict(held):
    return "NOT TESTED" if held is None else "HELD" if held else "FAILED"


def write_csv(path, rows, fields):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--guard-dir", default="/out/guard")
    parser.add_argument("--out-dir", default="/out/oc-locales")
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

    url = CODELOAD % (REPO, REF)
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=900) as r:
        files, agents, commit = read_tarball(r)
    print("%s @%s: %d locale files, agent workflows for %s" % (REPO, commit[:8] or "?", len(files),
                                                              sorted(agents) or "none"))
    ref = parse(files.get(REFERENCE, b""))
    if ref is None:
        print("lang/en.json missing or unparsed; stopping")
        return 1
    src = g.flatten(unwrap(g, ref))
    pairs = g.antonym_pairs(src)
    print("%d source keys, %d antonym pairs" % (len(src), len(pairs)))

    locales, rows, unparsed = [], [], []
    for lang in sorted(files):
        if skipped(lang):
            continue
        target = parse(files[lang])
        if target is None:
            unparsed.append(lang)
            continue
        s = scan_locale(g, ref, src, pairs, target)
        group = group_of(lang, agents)
        for row in s["rows"]:
            row["locale"], row["group"] = lang, group
            rows.append(row)
        locales.append({"locale": lang, "group": group, "keys": s["keys"], "translated": s["translated"],
                        "pairs_both_translated": s["both_translated"], "comparisons": s["comparisons"],
                        "warnings": len(s["rows"]), "per_1000": round(rate(len(s["rows"]), s["comparisons"]), 3)})
        print("%s (%s): %d keys, %d translated, %d comparisons (%d both translated), %d warnings, %.2f per 1,000"
              % (lang, group, s["keys"], s["translated"], s["comparisons"], s["both_translated"],
                 len(s["rows"]), rate(len(s["rows"]), s["comparisons"])))
        for row in s["rows"]:
            print("  %s [%s] %s/%s: %r / %r = %r" % (lang, row["classes"], row["kind1"], row["kind2"],
                                                   row["key1"], row["key2"], row["value"]))
    if unparsed:
        print("unparsed: %s" % unparsed)

    groups = group_totals(locales)
    q0 = len(locales) >= MIN_LOCALES and set(agents) == set(EXPECTED_AGENT)
    q1, q1_text = q1_check(groups)
    q2, q2_text = q2_check(groups)
    checks = [
        ("Q0", "en.json parses, >= %d locale files parse, agent group is exactly %s"
               % (MIN_LOCALES, ", ".join(EXPECTED_AGENT)), q0,
         "%d locale files parsed, agents %s" % (len(locales), sorted(agents))),
        ("Q1", "agent locales carry >= %d%% of comparisons" % int(100 * MIN_AGENT_SHARE), q1, q1_text),
        ("Q2", "the two groups' 95%% Wilson intervals overlap (>= %d comparisons each, >= %d warnings)"
               % (MIN_GROUP_COMPARISONS, MIN_WARNINGS_FOR_Q2), q2, q2_text),
    ]
    for name, text, held, value in checks:
        print("%s %s: %s (%s)" % (name, verdict(held), text, value))
    by_kind = {}
    for r in rows:
        k = "+".join(sorted((r["kind1"], r["kind2"])))
        by_kind[k] = by_kind.get(k, 0) + 1
    print("groups: %s" % json.dumps(groups, sort_keys=True))
    print("warnings by key kind: %s" % json.dumps(by_kind, sort_keys=True))
    print("Q3 and Q4 are graded by hand from warnings.csv (every row, none sampled)")

    write_csv(os.path.join(args.out_dir, "locales.csv"), locales, LOCALE_FIELDS)
    write_csv(os.path.join(args.out_dir, "warnings.csv"), sorted(rows, key=lambda r: (r["locale"], r["key1"], r["key2"])),
              FIELDS + ["verdict", "note"])
    summary = {"guard": g.__version__, "repo": REPO, "ref": REF, "commit": commit, "agents": sorted(agents),
               "source_keys": len(src), "pairs": len(pairs), "unparsed": unparsed, "groups": groups,
               "by_kind": by_kind, "locales": locales,
               "predictions": [{"id": n, "text": t, "held": h, "value": v} for n, t, h, v in checks]}
    with open(os.path.join(args.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
