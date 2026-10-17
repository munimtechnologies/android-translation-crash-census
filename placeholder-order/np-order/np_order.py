#!/usr/bin/env python3
"""np-order: does the order of a language's noun phrase (WALS) predict how
often its app translators reorder numbered placeholders better than its
clause order does?

Input is placeholder-order 0.1.0's by_language.csv (published in this repo):
per language, how many translations of numbered two-or-more-argument strings
put the arguments in another order. Each language code is mapped to ISO
639-3 (SIL tables) and then to WALS (Dryer & Haspelmath 2013, CLDF, CC BY
4.0). Features: 81A (subject/object/verb), 85A (adpositions), 86A (genitive
and noun), 87A (adjective and noun), 90A (relative clause and noun), each
reduced to its two dominant orders; everything else is left out.

The predictions in PREDICTIONS.md were published before this ran. The job
refuses to run until they are on main.

  python np_order.py --out-dir /out

Writes np_order.md, np_order.json and languages.csv.

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import csv
import hashlib
import io
import json
import os
import random
import re
import statistics
import sys
import time
import urllib.request

__version__ = "0.1.0"

REPO_RAW = "https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/main/"
BY_LANGUAGE_URL = REPO_RAW + "placeholder-order/by_language.csv"
PREDICTIONS_URL = REPO_RAW + "placeholder-order/np-order/PREDICTIONS.md"
PREDICTIONS_MARK = "np-order 0.1.0 predictions"
WALS_RAW = "https://raw.githubusercontent.com/cldf-datasets/wals/master/cldf/"
SIL = "https://iso639-3.sil.org/sites/iso639-3/files/downloads/"

MIN_VALID = 300   # numbered translations per language
MIN_REPOS = 10    # repositories per language
MIN_SIDE = 3      # languages on each side of a comparison
DRAWS = 2000
SEED = 86

# Each feature: (positive orders, negative orders), by WALS code name.
FEATURES = {
    "81A": ({"SOV"}, {"SVO", "VSO", "VOS"}),
    "85A": ({"Postpositions"}, {"Prepositions"}),
    "86A": ({"Genitive-Noun"}, {"Noun-Genitive"}),
    "87A": ({"Adjective-Noun"}, {"Noun-Adjective"}),
    "90A": ({"Relative clause-Noun"}, {"Noun-Relative clause"}),
}

# Android locale language -> the ISO 639-3 variety its app text is written
# in, for macrolanguages, tried first. Fixed before looking at any WALS value.
MAIN_VARIETY = {
    "zh": "cmn", "fa": "pes", "ms": "zsm", "no": "nob", "et": "ekk", "lv": "lvs",
    "uz": "uzn", "sw": "swh", "ku": "kmr", "mn": "khk", "ne": "npi", "or": "ory",
    "ps": "pbu", "az": "azj", "fil": "tgl",
}
# Already seen before this was written (placeholder-order 0.1.0's report).
SEEN = {"zh", "yue"}
# Mapping checks: if any fails, no prediction is scored.
KNOWN = [("ja", "81A", "SOV"), ("ja", "86A", "Genitive-Noun"), ("fr", "81A", "SVO"),
         ("fr", "86A", "Noun-Genitive"), ("tr", "85A", "Postpositions"),
         ("es", "85A", "Prepositions")]


def fetch(url, tries=4):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "np-order/" + __version__})
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read().decode("utf-8-sig")
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(5 * (attempt + 1))


def read_rates(text):
    """{lang: {...}} from by_language.csv rows with scope lang:xx, kind numbered."""
    out = {}
    for row in csv.DictReader(io.StringIO(text)):
        if not row["scope"].startswith("lang:") or row["kind"] != "numbered":
            continue
        out[row["scope"][5:]] = {
            "valid": int(row["valid"]), "reordered": int(row["reordered"]),
            "rate": float(row["reorder_rate"]) if row["reorder_rate"] else None,
            "repos": int(row["repos"] or 0),
            "unique_rate": float(row["unique_reorder_rate"]) if row["unique_reorder_rate"] else None,
            "repo_mean_rate": float(row["repo_mean_rate"]) if row["repo_mean_rate"] else None,
        }
    return out


def read_sil(iso_text, macro_text):
    """(part1 -> part3, macro -> [members])."""
    part1, members = {}, {}
    for row in csv.DictReader(io.StringIO(iso_text), delimiter="\t"):
        if row.get("Part1"):
            part1[row["Part1"]] = row["Id"]
    for row in csv.DictReader(io.StringIO(macro_text), delimiter="\t"):
        if row.get("I_Status", "A") == "A":
            members.setdefault(row["M_Id"], []).append(row["I_Id"])
    return part1, members


def candidates(lang, part1, members):
    """Tiers of ISO 639-3 codes to try, best first: the main variety (for
    macrolanguages in MAIN_VARIETY), the code itself, its macro members."""
    tiers = [[MAIN_VARIETY[lang]]] if lang in MAIN_VARIETY else []
    code = part1.get(lang, lang if len(lang) == 3 else None)
    if code is None:
        return tiers
    return tiers + [[code], list(members.get(code, []))]


def read_wals(languages_text, codes_text, values_text):
    """(iso -> [wals ids], (wals id, feature) -> code name)."""
    by_iso = {}
    for row in csv.DictReader(io.StringIO(languages_text)):
        isos = set(re.findall(r"[a-z]{3}", (row.get("ISO_codes") or "")))
        if row.get("ISO639P3code"):
            isos.add(row["ISO639P3code"])
        for iso in isos:
            by_iso.setdefault(iso, []).append(row["ID"])
    names = {row["ID"]: row["Name"] for row in csv.DictReader(io.StringIO(codes_text))}
    values = {}
    for row in csv.DictReader(io.StringIO(values_text)):
        if row["Parameter_ID"] in FEATURES:
            values[(row["Language_ID"], row["Parameter_ID"])] = names.get(row["Code_ID"], "")
    return by_iso, values


def feature_value(tiers, by_iso, values, feature):
    """(value or None or "conflict", wals ids used). The first tier with any
    value wins; disagreeing WALS entries in it give "conflict"."""
    for tier in tiers:
        ids = sorted({w for iso in tier for w in by_iso.get(iso, [])})
        got = {values[(w, feature)] for w in ids if (w, feature) in values}
        if len(got) == 1:
            return got.pop(), ids
        if len(got) > 1:
            return "conflict", ids
    return None, []


def side(value, feature):
    """1, 0 or None for a WALS value of a feature."""
    pos, neg = FEATURES[feature]
    return 1 if value in pos else 0 if value in neg else None


def auc(pairs):
    """P(rate of a positive language > rate of a negative one), ties half.
    pairs is [(side, rate)]."""
    pos = [r for s, r in pairs if s == 1]
    neg = [r for s, r in pairs if s == 0]
    if not pos or not neg:
        return None
    wins = sum(1.0 if p > n else 0.5 if p == n else 0.0 for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def counts(pairs):
    return sum(1 for s, _ in pairs if s == 1), sum(1 for s, _ in pairs if s == 0)


def compare(rows, f1, f2, draws=DRAWS, seed=SEED):
    """AUC of f1 and f2 on languages with both, and a bootstrap 95% interval
    of AUC(f1) - AUC(f2), resampling languages."""
    both = [r for r in rows if r[f1] is not None and r[f2] is not None]
    a1 = auc([(r[f1], r["rate"]) for r in both])
    a2 = auc([(r[f2], r["rate"]) for r in both])
    n1, n2 = counts([(r[f1], 0) for r in both]), counts([(r[f2], 0) for r in both])
    testable = min(n1 + n2) >= MIN_SIDE
    diffs = []
    rng = random.Random(seed)
    for _ in range(draws if testable else 0):
        sample = [rng.choice(both) for _ in both]
        b1 = auc([(r[f1], r["rate"]) for r in sample])
        b2 = auc([(r[f2], r["rate"]) for r in sample])
        if b1 is not None and b2 is not None:
            diffs.append(b1 - b2)
    diffs.sort()
    ci = [diffs[int(0.025 * len(diffs))], diffs[int(0.975 * len(diffs)) - 1]] if diffs else [None, None]
    return {"features": [f1, f2], "languages": len(both), "sides": [list(n1), list(n2)],
            "auc": [a1, a2], "diff_ci95": ci, "testable": testable}


def median_split(rows, feature, keep):
    """Medians of the positive and negative sides among rows where keep(row)."""
    sub = [r for r in rows if keep(r) and r[feature] is not None]
    pos = [r["rate"] for r in sub if r[feature] == 1]
    neg = [r["rate"] for r in sub if r[feature] == 0]
    return {"positive": sorted(r["lang"] for r in sub if r[feature] == 1),
            "negative": sorted(r["lang"] for r in sub if r[feature] == 0),
            "median_positive": statistics.median(pos) if pos else None,
            "median_negative": statistics.median(neg) if neg else None}


def predictions(rows):
    """[(id, text, held True/False/None, detail)]."""
    out = []
    c = compare(rows, "86A", "81A")
    out.append(("P1", "genitive order (86A) separates reorder rates better than verb-final order (81A)",
                (c["auc"][0] > c["auc"][1]) if c["testable"] else None, c))
    c = compare(rows, "85A", "81A")
    out.append(("P2", "adposition order (85A) separates reorder rates better than verb-final order (81A)",
                (c["auc"][0] > c["auc"][1]) if c["testable"] else None, c))
    m = median_split(rows, "86A", lambda r: r["81A"] == 1)
    ok = len(m["positive"]) >= MIN_SIDE and len(m["negative"]) >= 2
    out.append(("P3", "among SOV languages, noun-genitive ones reorder less (median) than genitive-noun ones",
                (m["median_negative"] < m["median_positive"]) if ok else None, m))
    m = median_split(rows, "86A", lambda r: r["81A"] == 0 and r["lang"] not in SEEN)
    ok = len(m["positive"]) >= MIN_SIDE and len(m["negative"]) >= MIN_SIDE
    out.append(("P4", "among SVO/VSO/VOS languages other than zh and yue, genitive-noun ones reorder more "
                      "(median) than noun-genitive ones",
                (m["median_positive"] > m["median_negative"]) if ok else None, m))
    c = compare(rows, "86A", "87A")
    out.append(("P5", "genitive order (86A) separates reorder rates better than adjective order (87A)",
                (c["auc"][0] > c["auc"][1]) if c["testable"] else None, c))
    return out


def fmt(x, digits=3):
    return "n/a" if x is None else ("%.*f" % (digits, x))


def verdict(held):
    return "NOT TESTABLE" if held is None else "HELD" if held else "FAILED"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--no-gate", action="store_true", help="skip the PREDICTIONS.md check (tests only)")
    args = ap.parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)

    if not args.no_gate:
        try:
            pred = fetch(PREDICTIONS_URL)
        except Exception as exc:
            pred = ""
            print("gate: could not read PREDICTIONS.md on main: %s" % exc)
        if PREDICTIONS_MARK not in pred:
            print("gate: predictions not on main; refusing to run")
            return 3

    sources = {"by_language": BY_LANGUAGE_URL, "sil_iso": SIL + "iso-639-3.tab",
               "sil_macro": SIL + "iso-639-3-macrolanguages.tab",
               "wals_languages": WALS_RAW + "languages.csv", "wals_codes": WALS_RAW + "codes.csv",
               "wals_values": WALS_RAW + "values.csv"}
    text = {k: fetch(u) for k, u in sources.items()}
    digests = {k: hashlib.sha256(v.encode("utf-8")).hexdigest() for k, v in text.items()}

    rates = read_rates(text["by_language"])
    part1, members = read_sil(text["sil_iso"], text["sil_macro"])
    by_iso, values = read_wals(text["wals_languages"], text["wals_codes"], text["wals_values"])

    def look(lang, feature):
        return feature_value(candidates(lang, part1, members), by_iso, values, feature)

    checks = [(lang, f, want, look(lang, f)[0]) for lang, f, want in KNOWN]
    mapping_ok = all(got == want for _, _, want, got in checks)

    rows, table = [], []
    for lang in sorted(rates):
        r = rates[lang]
        if r["rate"] is None or r["valid"] < MIN_VALID or r["repos"] < MIN_REPOS:
            continue
        row = {"lang": lang, "valid": r["valid"], "reordered": r["reordered"], "rate": r["rate"],
               "repos": r["repos"], "unique_rate": r["unique_rate"], "repo_mean_rate": r["repo_mean_rate"]}
        line = dict(row)
        wals_ids = set()
        for f in FEATURES:
            value, ids = look(lang, f)
            wals_ids.update(ids)
            line[f] = value or ""
            row[f] = side(value, f)
        line["iso"] = " ".join(sum(candidates(lang, part1, members), []))[:80]
        line["wals"] = " ".join(sorted(wals_ids))
        rows.append(row)
        table.append(line)

    preds = predictions(rows) if mapping_ok else []
    held = [verdict(p[2]) for p in preds]

    fields = ["lang", "valid", "reordered", "rate", "repos", "unique_rate", "repo_mean_rate",
              "81A", "85A", "86A", "87A", "90A", "iso", "wals"]
    with open(os.path.join(args.out_dir, "languages.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for line in table:
            w.writerow({k: line.get(k, "") for k in fields})

    singles = {}
    for f in FEATURES:
        pairs = [(r[f], r["rate"]) for r in rows if r[f] is not None]
        singles[f] = {"sides": list(counts(pairs)), "auc": auc(pairs),
                      "auc_unique": auc([(r[f], r["unique_rate"]) for r in rows
                                         if r[f] is not None and r["unique_rate"] is not None]),
                      "auc_repo_mean": auc([(r[f], r["repo_mean_rate"]) for r in rows
                                            if r[f] is not None and r["repo_mean_rate"] is not None])}

    result = {"version": __version__, "sources": sources, "sha256": digests,
              "min_valid": MIN_VALID, "min_repos": MIN_REPOS, "languages": len(rows),
              "mapping_checks": [{"lang": l, "feature": f, "want": w, "got": g} for l, f, w, g in checks],
              "mapping_ok": mapping_ok, "single_feature": singles,
              "predictions": [{"id": i, "text": t, "result": verdict(h), "detail": d} for i, t, h, d in preds]}
    with open(os.path.join(args.out_dir, "np_order.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1, ensure_ascii=False)

    md = ["# np-order %s: noun-phrase order and placeholder reordering" % __version__, "",
          "MV2 of Munim, Inc., made with AI agents. WALS data: Dryer & Haspelmath (eds.) 2013, CC BY 4.0.", "",
          "- Languages with at least %d numbered translations in at least %d repositories: %d"
          % (MIN_VALID, MIN_REPOS, len(rows)),
          "- Mapping checks: %s" % ("all passed" if mapping_ok else "FAILED, so no prediction is scored: "
                                    + "; ".join("%s %s want %s got %s" % c for c in checks if c[2] != c[3])),
          "", "## Predictions", ""]
    for (i, t, h, d), v in zip(preds, held):
        if "auc" in d:
            extra = "AUC %s vs %s on %d languages (sides %s), difference 95%% CI [%s, %s]" % (
                fmt(d["auc"][0]), fmt(d["auc"][1]), d["languages"], d["sides"],
                fmt(d["diff_ci95"][0]), fmt(d["diff_ci95"][1]))
        else:
            extra = "median %s (%s) vs %s (%s)" % (
                fmt(d["median_positive"], 4), " ".join(d["positive"]),
                fmt(d["median_negative"], 4), " ".join(d["negative"]))
        md.append("- %s %s: %s. %s" % (i, v, t, extra))
    md += ["", "## Each feature alone (all languages with a value)", "",
           "| feature | positive | negative | AUC | AUC unique pairs | AUC repo mean |", "|---|---:|---:|---:|---:|---:|"]
    for f, s in singles.items():
        md.append("| %s %s | %d | %d | %s | %s | %s |" % (
            f, "/".join(sorted(FEATURES[f][0])), s["sides"][0], s["sides"][1],
            fmt(s["auc"]), fmt(s["auc_unique"]), fmt(s["auc_repo_mean"])))
    md += ["", "## Languages", "", "| lang | valid | reorder rate | 81A | 85A | 86A | 87A | 90A |",
           "|---|---:|---:|---|---|---|---|---|"]
    for line in sorted(table, key=lambda x: -x["rate"]):
        md.append("| %s | %d | %s | %s | %s | %s | %s | %s |" % (
            line["lang"], line["valid"], fmt(line["rate"], 4), line["81A"], line["85A"],
            line["86A"], line["87A"], line["90A"]))
    with open(os.path.join(args.out_dir, "np_order.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print("np-order: %d languages, mapping %s" % (len(rows), "ok" if mapping_ok else "FAILED"))
    for (i, t, _, _), v in zip(preds, held):
        print("%s %s: %s" % (i, v, t))
    return 0


if __name__ == "__main__":
    sys.exit(main())
