#!/usr/bin/env python3
"""shape: which English string shapes do Android app translators reorder?

For each English source with exactly two numbered arguments (%1$s, %2$d),
the text between the two placeholders gives the string a shape: no words
(": ", "/"), "of", a preposition ("to", "from"), "and"/"or", or anything
else. Reorder rates are then counted per shape and word-order group, over
the same F-Droid repositories and strings as placeholder-order 0.1.0, whose
code (and the census code it uses) fetch_code.py downloads from the public
repository.

The predictions in PREDICTIONS.md were published before this ran. The job
refuses to run until they are on main.

  python shape.py --data-dir /data --out-dir /out

Writes shape.md, shape.json, by_language.csv and top_sources.csv.

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import collections
import concurrent.futures
import csv
import datetime
import json
import os
import re
import shutil
import sys
import tempfile
import time
import urllib.request

import placeholder_order as po

__version__ = "0.1.0"

REPO_RAW = "https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/main/"
PREDICTIONS_URL = REPO_RAW + "placeholder-order/shape/PREDICTIONS.md"
PREDICTIONS_MARK = "shape 0.1.0 predictions"

SHAPES = ["no_words", "of", "adposition", "and_or", "other"]
ADPOSITIONS = set("to from in on at by for with into onto via than over under per as about through "
                  "within after before across toward towards against without near between inside "
                  "outside behind beyond since until during".split())
ARTICLES = {"the", "a", "an"}
MIN_VALID = 200     # translations behind a rate
MIN_REORDERS = 20   # SOV reorders behind S6
MIN_LANG = 300      # translations for a language row in the report
WORD_RE = re.compile(r"[A-Za-z]+")
LETTER_RE = re.compile(r"[^\W\d_]")
# Shape checks: if any fails, no prediction is scored.
KNOWN = [("Page %1$d of %2$d", "of"), ("%1$s: %2$s", "no_words"), ("Move %1$s to %2$s", "adposition"),
         ("%1$s and %2$s", "and_or"), ("%1$s sent you %2$s", "other"), ("%1$d%% of %2$d", "of")]


def arg_spans(text):
    """[(start, end)] of the argument placeholders in text, in text order
    (%% and %n take no argument)."""
    return [m.span() for m in po.SPEC_RE.finditer(text)
            if m.group(5) or m.group(6) not in "%n"]


def between(text):
    """The text between the first two argument placeholders, or None."""
    spans = arg_spans(text)
    if len(spans) < 2:
        return None
    return text[spans[0][1]:spans[1][0]]


def shape(gap):
    """One of SHAPES for the text between two placeholders."""
    if not LETTER_RE.search(gap):
        return "no_words"
    if LETTER_RE.search(WORD_RE.sub("", gap)):
        return "other"  # letters outside A-Z: not English
    words = [w.lower() for w in WORD_RE.findall(gap)]
    if words in (["of"], ["out", "of"], ["of", "the"]):
        return "of"
    if words[0] in ADPOSITIONS and (len(words) == 1 or (len(words) == 2 and words[1] in ARTICLES)):
        return "adposition"
    if words in (["and"], ["or"]):
        return "and_or"
    return "other"


class Tally:
    """Counts by (scope, shape): scope is "all", "group:G" or "lang:xx"."""

    def __init__(self):
        self.counts = collections.defaultdict(collections.Counter)
        self.repo_counts = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
        self.unique = collections.defaultdict(dict)
        self.sov_sources = collections.defaultdict(lambda: {"translations": 0, "reordered": 0,
                                                            "repos": set()})
        self.skipped = collections.Counter()

    def add(self, row):
        """row: a placeholder_order scan row (with source and target text)."""
        if row["kind"] != "numbered":
            return
        spans = arg_spans(row["source"])
        if len(spans) != 2:
            self.skipped["three_or_more_arguments"] += 1
            return
        if row["category"] not in po.VALID:
            self.skipped["not_valid"] += 1
            return
        s = shape(between(row["source"]))
        group = po.WORD_ORDER.get(row["lang"], "unassigned")
        for scope in ("all", "group:" + group, "lang:" + row["lang"]):
            self.counts[(scope, s)][row["category"]] += 1
            self.repo_counts[(scope, s)][row["repo"]][row["category"]] += 1
            self.unique[(scope, s)][(row["lang"], row["source"], row["target"])] = row["category"]
        if group == "SOV":
            src = self.sov_sources[(row["source"], s)]
            src["translations"] += 1
            src["reordered"] += row["category"] in ("numbered_reordered", "unnumbered_reordered")
            src["repos"].add(row["repo"])

    def merged(self, scope, shapes):
        c = collections.Counter()
        for s in shapes:
            c.update(self.counts.get((scope, s), collections.Counter()))
        return c

    def row(self, scope, shapes):
        """Rates for scope over one or more shapes."""
        out = po.rates(self.merged(scope, shapes))
        per_repo = collections.defaultdict(collections.Counter)
        unique = {}
        for s in shapes:
            for repo, c in self.repo_counts.get((scope, s), {}).items():
                per_repo[repo].update(c)
            unique.update(self.unique.get((scope, s), {}))
        repos = [(r["reordered"], r["valid"]) for r in map(po.rates, per_repo.values()) if r["valid"]]
        out["repos"] = len(repos)
        out["repo_mean_rate"] = sum(m / v for m, v in repos) / len(repos) if repos else None
        out["ci_low"], out["ci_high"] = po.cluster_ci(repos)
        u = po.rates(collections.Counter(unique.values()))
        out["unique_valid"], out["unique_reorder_rate"] = u["valid"], u["reorder_rate"]
        return out


def rate(t, scope, shapes):
    """Pooled reorder rate, or None with fewer than MIN_VALID translations."""
    r = t.row(scope, shapes)
    return r["reorder_rate"] if r["valid"] >= MIN_VALID else None


def predictions(t):
    """[(id, text, held True/False/None, detail)]."""
    out = []
    a, b = rate(t, "group:SOV", ["of"]), rate(t, "group:SOV", ["no_words"])
    out.append(("S1", "in SOV languages, of sources are reordered at least 3x as often as no_words sources",
                None if a is None or b is None else a >= 3 * b, {"of": a, "no_words": b}))
    a, b = rate(t, "group:SOV", ["adposition"]), rate(t, "group:SOV", ["other"])
    out.append(("S2", "in SOV languages, adposition sources are reordered more often than other sources",
                None if a is None or b is None else a > b, {"adposition": a, "other": b}))
    a = rate(t, "group:SVO", ["of"])
    out.append(("S3", "in SVO languages, of sources are reordered less than 3% of the time",
                None if a is None else a < 0.03, {"of": a}))
    ratios = {}
    for name, shapes in (("ratio of+adposition", ["of", "adposition"]), ("ratio other", ["other"])):
        sov, svo = rate(t, "group:SOV", shapes), rate(t, "group:SVO", shapes)
        ratios[name] = sov / svo if sov is not None and svo else None
    out.append(("S4", "the SOV/SVO reorder-rate ratio is higher for of+adposition sources than for other "
                      "sources",
                None if None in ratios.values() else ratios["ratio of+adposition"] > ratios["ratio other"],
                ratios))
    a = rate(t, "group:SOV", ["no_words"])
    out.append(("S5", "in SOV languages, no_words sources are reordered less than 3% of the time",
                None if a is None else a < 0.03, {"no_words": a}))
    total = t.row("group:SOV", SHAPES)["reordered"]
    part = t.row("group:SOV", ["of", "adposition"])["reordered"]
    share = part / total if total else None
    out.append(("S6", "of and adposition sources account for more than half of SOV reorders",
                None if total < MIN_REORDERS else share > 0.5,
                {"reorders": total, "of+adposition": part, "share": share}))
    return out


def verdict(held):
    return "NOT TESTABLE" if held is None else "HELD" if held else "FAILED"


def fmt_pct(x):
    return "n/a" if x is None else "%.1f%%" % (100 * x)


def fmt(x, digits=2):
    return "n/a" if x is None else "%.*f" % (digits, x)


def detail_text(d):
    """"of 12.0%, no_words 1.0%" for a prediction's detail: counts as they
    are, ratios with an x, rates as percentages."""
    parts = []
    for k, v in d.items():
        if isinstance(v, int):
            parts.append("%s %d" % (k, v))
        elif k.startswith("ratio "):
            parts.append("%s %s" % (k, "n/a" if v is None else fmt(v) + "x"))
        else:
            parts.append("%s %s" % (k, fmt_pct(v)))
    return ", ".join(parts)


def fetch(url, tries=4):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "mv2-shape/" + __version__})
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read().decode("utf-8-sig")
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(5 * (attempt + 1))


def write(out_dir, t, meta, checks_ok, checks):
    os.makedirs(out_dir, exist_ok=True)
    preds = predictions(t) if checks_ok else []
    groups = ["SOV", "SVO", "VSO", "no dominant order", "unassigned"]
    table = {}
    for g in ["all"] + ["group:" + x for x in groups]:
        table[g] = {s: t.row(g, [s]) for s in SHAPES}
        table[g]["total"] = t.row(g, SHAPES)
    langs = sorted({s[5:] for s, _ in t.counts if s.startswith("lang:")})
    lang_rows = []
    for lang in langs:
        total = t.row("lang:" + lang, SHAPES)
        line = {"lang": lang, "group": po.WORD_ORDER.get(lang, "unassigned"), "valid": total["valid"],
                "reordered": total["reordered"], "rate": total["reorder_rate"]}
        for s in SHAPES:
            r = po.rates(t.counts.get(("lang:" + lang, s), collections.Counter()))
            line[s + "_valid"], line[s + "_reordered"] = r["valid"], r["reordered"]
        lang_rows.append(line)
    with open(os.path.join(out_dir, "by_language.csv"), "w", newline="", encoding="utf-8") as f:
        fields = ["lang", "group", "valid", "reordered", "rate"] + [
            s + x for s in SHAPES for x in ("_valid", "_reordered")]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(lang_rows)
    top = sorted(t.sov_sources.items(), key=lambda kv: (-kv[1]["reordered"], -kv[1]["translations"], kv[0]))
    with open(os.path.join(out_dir, "top_sources.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source", "shape", "sov_translations", "sov_reordered", "repos"])
        for (source, s), v in top[:300]:
            w.writerow([source, s, v["translations"], v["reordered"], len(v["repos"])])
    result = dict(meta, version=__version__, shape_checks=checks, shape_checks_ok=checks_ok,
                  skipped=dict(t.skipped), table=table,
                  predictions=[{"id": i, "text": x, "result": verdict(h), "detail": d}
                               for i, x, h, d in preds])
    with open(os.path.join(out_dir, "shape.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1, ensure_ascii=False)

    md = ["# shape %s: which English string shapes do translators reorder?" % __version__, "",
          "MV2 of Munim, Inc., made with AI agents. Data: %s, read %s; %d repositories scanned."
          % (meta.get("index_url", ""), meta.get("finished", ""), meta.get("repos_scanned", 0)), "",
          "- Shape checks: %s" % ("all passed" if checks_ok else "FAILED, so no prediction is scored: "
                                  + "; ".join("%r want %s got %s" % (c["text"], c["want"], c["got"])
                                              for c in checks if c["want"] != c["got"])),
          "- Left out: %s" % (", ".join("%s %d" % kv for kv in sorted(t.skipped.items())) or "none"),
          "", "## Predictions", ""]
    for i, x, h, d in preds:
        md.append("- %s %s: %s. %s" % (i, verdict(h), x, detail_text(d)))
    md += ["", "## Reorder rate by shape (numbered two-argument sources)", "",
           "| group | shape | valid | reordered | rate | 95% CI (repos) | repo mean | unique-pair rate | repos |",
           "|---|---|---:|---:|---:|---|---:|---:|---:|"]
    for g, shapes in table.items():
        for s, r in shapes.items():
            md.append("| %s | %s | %d | %d | %s | %s-%s | %s | %s | %d |" % (
                g.replace("group:", ""), s, r["valid"], r["reordered"], fmt_pct(r["reorder_rate"]),
                fmt_pct(r["ci_low"]), fmt_pct(r["ci_high"]), fmt_pct(r["repo_mean_rate"]),
                fmt_pct(r["unique_reorder_rate"]), r["repos"]))
    md += ["", "## Languages (%d+ translations): reorder rate by shape (valid in brackets)" % MIN_LANG, "",
           "| lang | group | all | " + " | ".join(SHAPES) + " |", "|---|---|---|" + "---|" * len(SHAPES)]
    for line in sorted((x for x in lang_rows if x["valid"] >= MIN_LANG), key=lambda x: -(x["rate"] or 0)):
        cells = []
        for s in SHAPES:
            v = line[s + "_valid"]
            cells.append("%s (%d)" % (fmt_pct(line[s + "_reordered"] / v) if v else "n/a", v))
        md.append("| %s | %s | %s (%d) | %s |" % (line["lang"], line["group"], fmt_pct(line["rate"]),
                                                  line["valid"], " | ".join(cells)))
    md += ["", "## Most often reordered sources in SOV languages", "",
           "| source | shape | SOV translations | reordered | repos |", "|---|---|---:|---:|---:|"]
    for (source, s), v in top[:30]:
        md.append("| `%s` | %s | %d | %d | %d |" % (source.replace("|", "\\|").replace("`", "'")
                                                    .replace("\n", " ")[:120], s, v["translations"],
                                                    v["reordered"], len(v["repos"])))
    with open(os.path.join(out_dir, "shape.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    return preds


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--data-dir", default="/data")
    parser.add_argument("--out-dir", default="/out")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--budget-minutes", type=float, default=100)
    parser.add_argument("--timeout", type=int, default=150)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--no-gate", action="store_true", help="skip the PREDICTIONS.md check")
    args = parser.parse_args(argv)

    if not args.no_gate:
        try:
            pred = fetch(PREDICTIONS_URL)
        except Exception as exc:
            pred = ""
            print("gate: could not read PREDICTIONS.md on main: %s" % exc)
        if PREDICTIONS_MARK not in pred:
            print("gate: predictions not on main; refusing to run")
            return 3

    checks = [{"text": x, "want": want, "got": shape(between(x))} for x, want in KNOWN]
    checks_ok = all(c["want"] == c["got"] for c in checks)

    import census
    import census_fixes
    census_fixes.apply()
    census.USER_AGENT = "mv2-shape/%s (Munim, Inc.; mv2@munimtech.com)" % __version__
    if not shutil.which("git"):
        raise SystemExit("git is not installed")
    started = time.time()
    meta = {"started": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "census_version": census.__version__, "placeholder_order_version": po.__version__}
    repos, meta["index_url"], meta["apps_in_index"] = po.load_repos(census, args.data_dir, args.limit)
    print("%d repositories" % len(repos), flush=True)
    tmp = tempfile.mkdtemp(prefix="shape-")
    deadline = started + args.budget_minutes * 60
    t, status = Tally(), collections.Counter()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(po.scan_repo, census, r, args.timeout, tmp, deadline) for r in repos]
            for i, fut in enumerate(concurrent.futures.as_completed(futures), 1):
                record, got = fut.result()
                status[record["status"]] += 1
                for r in got:
                    t.add(r)
                if i % 250 == 0:
                    print("%d/%d repositories" % (i, len(repos)), flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    meta["finished"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    meta["repos_scanned"] = sum(status.values())
    meta["repo_status"] = dict(status)
    preds = write(args.out_dir, t, meta, checks_ok, checks)
    total = t.row("all", SHAPES)
    print("shape: %d translations of numbered two-argument sources in %d repositories; shape checks %s"
          % (total["valid"], meta["repos_scanned"], "ok" if checks_ok else "FAILED"), flush=True)
    for i, x, h, _ in preds:
        print("%s %s: %s" % (i, verdict(h), x), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
