#!/usr/bin/env python3
"""Placeholder order: how often Android app translators put an English
string's format arguments in a different order, per language, and how often
they do it safely (with numbered placeholders such as %2$s) or unsafely
(moving unnumbered ones, which Java still fills left to right).

It reads the same F-Droid repositories and string pairs as the
android-translation-crash-census (census.py 0.3.0 + census_fixes 0.3.1):
every translation of a string the app formats. Plural forms are left out,
because translated plural forms often drop an argument on purpose.

A source string counts when Java's Formatter finds at least two argument
placeholders in it and either none or all of them are numbered (each number
1..n once). Each translation is then:
  kept_unnumbered       unnumbered, same argument kinds in the same order
  unnumbered_reordered  unnumbered, the same kinds in a different order
  numbered_in_order     numbered, every argument once, in the source's order
  numbered_reordered    numbered, every argument once, in another order
  other                 anything else (missing or extra arguments, changed
                        kinds, relative "<" indexes, a placeholder that throws)
Moving unnumbered placeholders only shows when the source mixes kinds (%s and
%d); in "%s ... %s" it is invisible, so those sources are counted apart.

  python placeholder_order.py --data-dir /data --out-dir /out

Writes report.md, summary.json, by_language.csv, unnumbered_reordered.csv and
pairs.csv.gz (one line per counted translation, without its text).

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import collections
import concurrent.futures
import csv
import datetime
import gzip
import json
import os
import random
import re
import shutil
import sys
import tempfile
import time

__version__ = "0.1.0"

# java.util.Formatter's own pattern.
SPEC_RE = re.compile(r"%(\d+\$)?([-#+ 0,(<]*)?(\d+)?(\.\d+)?([tT])?([a-zA-Z%])")
KINDS = {"b": "b", "h": "h", "s": "s", "c": "c", "d": "d", "o": "d", "x": "d",
         "e": "f", "f": "f", "g": "f", "a": "f"}
CATEGORIES = ["kept_unnumbered", "unnumbered_reordered", "numbered_in_order",
              "numbered_reordered", "other"]
VALID = CATEGORIES[:4]
SOURCE_KINDS = ["numbered", "unnumbered_mixed", "unnumbered_same"]

# Dominant order of subject, object and verb (WALS feature 81A, main variety),
# simplified to four groups. Languages left out are "unassigned".
WORD_ORDER = {}
for _group, _langs in {
    "SOV": "ja ko tr az kk ky uz tk tt ba ug cv mn hi bn mr gu pa ne or as si ur sd ta te kn ml "
           "fa ps ku ckb hy ka eu am my bo sa",
    "SVO": "fr es it pt ro ca gl oc ru uk be pl cs sk sl hr sr bs bg mk lt lv et fi sq sw id ms vi "
           "th zh yue he eo nb nn no sv da is km lo ha yo ig zu xh rw mt",
    "VSO": "ga cy gd br tl fil",
    "no dominant order": "de nl hu",
}.items():
    for _lang in _langs.split():
        WORD_ORDER[_lang] = _group
OLD_CODES = {"iw": "he", "in": "id", "ji": "yi"}


def specs(text):
    """[(index or None, relative, kind)] for each argument Java's Formatter
    finds in text (%% and %n take none), or None if one of them throws."""
    out = []
    for m in SPEC_RE.finditer(text):
        index, flags, _, _, time_prefix, conv = m.groups()
        if time_prefix:
            kind = "t"
        elif conv in "%n":
            continue
        elif conv.lower() in KINDS and (conv.islower() or conv in "BHSCXEGA"):
            kind = KINDS[conv.lower()]
        else:
            return None
        number = int(index[:-1]) if index else None
        if number == 0:
            return None
        out.append((number, "<" in (flags or ""), kind))
    return out


def source_kind(src):
    """numbered, unnumbered_mixed, unnumbered_same, or None (not counted)."""
    if src is None or len(src) < 2 or any(rel for _, rel, _ in src):
        return None
    numbers = [n for n, _, _ in src]
    if all(n is None for n in numbers):
        return "unnumbered_mixed" if len({k for _, _, k in src}) > 1 else "unnumbered_same"
    if all(n is not None for n in numbers) and sorted(numbers) == list(range(1, len(src) + 1)):
        return "numbered"
    return None


def classify(source, target):
    """(source kind, category) for one translation, or (None, None)."""
    src = specs(source)
    kind = source_kind(src)
    if kind is None:
        return None, None
    tgt = specs(target)
    if tgt is None or len(tgt) != len(src) or any(rel for _, rel, _ in tgt):
        return kind, "other"
    if kind == "numbered":
        want = {n: k for n, _, k in src}
        order = [n for n, _, _ in src]
    else:
        want = {i + 1: k for i, (_, _, k) in enumerate(src)}
        order = list(range(1, len(src) + 1))
    numbers = [n for n, _, _ in tgt]
    got = [k for _, _, k in tgt]
    identity = list(range(1, len(src) + 1))
    if all(n is None for n in numbers):
        # Java fills unnumbered placeholders with arguments 1..n.
        if order != identity:
            return kind, "other"
        if got == [want[n] for n in identity]:
            return kind, "kept_unnumbered"
        if sorted(got) == sorted(want.values()):
            return kind, "unnumbered_reordered"
        return kind, "other"
    if any(n is None for n in numbers) or sorted(numbers) != identity:
        return kind, "other"
    if any(want[n] != k for n, k in zip(numbers, got)):
        return kind, "other"
    return kind, ("numbered_in_order" if numbers == order else "numbered_reordered")


def order_text(text):
    """The argument order of a string, e.g. "2$s 1$d" or "s d"."""
    return " ".join(("%d$" % n if n else "") + k for n, _, k in specs(text) or [])


def language(locale):
    """values-pt-rBR -> pt, b+sr+Latn -> sr, iw -> he."""
    if locale.startswith("b+"):
        lang = locale[2:].split("+")[0]
    else:
        lang = locale.split("-")[0]
    lang = lang.lower()
    return OLD_CODES.get(lang, lang)


def rates(counts):
    """Reorder rates from a Counter of categories."""
    valid = sum(counts[c] for c in VALID)
    moved = counts["numbered_reordered"] + counts["unnumbered_reordered"]
    return {"valid": valid, "reordered": moved,
            "reorder_rate": moved / valid if valid else None,
            "unsafe": counts["unnumbered_reordered"],
            "unsafe_share": counts["unnumbered_reordered"] / moved if moved else None,
            "numbered_in_order": counts["numbered_in_order"]}


def cluster_ci(per_repo, draws=1000, seed=81):
    """95% interval of the pooled reorder rate, resampling repositories.
    per_repo is a list of (reordered, valid)."""
    per_repo = [x for x in per_repo if x[1]]
    if len(per_repo) < 2:
        return None, None
    rng = random.Random(seed)
    got = []
    for _ in range(draws):
        sample = [per_repo[rng.randrange(len(per_repo))] for _ in per_repo]
        valid = sum(v for _, v in sample)
        got.append(sum(m for m, _ in sample) / valid if valid else 0.0)
    got.sort()
    return got[int(0.025 * draws)], got[int(0.975 * draws) - 1]


class Tally:
    """Counts by (scope, source kind): scope is a language, a word-order group
    or "all"."""

    def __init__(self):
        self.counts = collections.defaultdict(collections.Counter)
        self.repo_counts = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
        self.unique = collections.defaultdict(dict)
        self.rows = {}

    def add(self, repo, lang, kind, category, source, target):
        self.rows.clear()
        for scope in ("all", "lang:" + lang, "group:" + WORD_ORDER.get(lang, "unassigned")):
            self.counts[(scope, kind)][category] += 1
            self.repo_counts[(scope, kind)][repo][category] += 1
            self.unique[(scope, kind)][(lang, source, target)] = category

    def row(self, scope, kind):
        if (scope, kind) not in self.rows:
            self.rows[(scope, kind)] = self._row(scope, kind)
        return self.rows[(scope, kind)]

    def _row(self, scope, kind):
        counts = self.counts.get((scope, kind), collections.Counter())
        out = rates(counts)
        per_repo = []
        for c in self.repo_counts.get((scope, kind), {}).values():
            r = rates(c)
            per_repo.append((r["reordered"], r["valid"]))
        repos = [x for x in per_repo if x[1]]
        out["repos"] = len(repos)
        out["repos_with_reorder"] = sum(1 for m, _ in repos if m)
        out["repo_mean_rate"] = sum(m / v for m, v in repos) / len(repos) if repos else None
        out["ci_low"], out["ci_high"] = cluster_ci(repos)
        unique = collections.Counter(self.unique.get((scope, kind), {}).values())
        out["unique_valid"] = rates(unique)["valid"]
        out["unique_reorder_rate"] = rates(unique)["reorder_rate"]
        out["other"] = counts["other"]
        return out


def predictions(t):
    """The predictions written in PREDICTIONS.md before the run, checked."""
    def rate(scope, kind):
        return t.row(scope, kind)["reorder_rate"]

    out = []
    for n, kind in (("P1", "unnumbered_mixed"), ("P2", "numbered")):
        sov, svo = rate("group:SOV", kind), rate("group:SVO", kind)
        ok = sov is not None and svo is not None and sov >= 2 * svo
        out.append((n, "SOV reorder rate >= 2x SVO (%s sources): SOV %s, SVO %s"
                    % (kind, pct(sov), pct(svo)), ok))
    ranked = sorted(((t.row(s, "numbered")["reorder_rate"], s[5:]) for s, k in t.counts
                     if k == "numbered" and s.startswith("lang:")
                     and t.row(s, "numbered")["repos"] >= 20), reverse=True)
    top = [lang for _, lang in ranked[:5]]
    out.append(("P3", "ja and ko both in the top 5 languages (>= 20 repositories) by numbered "
                "reorder rate: top 5 = %s" % ", ".join(top), "ja" in top and "ko" in top))
    mixed = t.row("all", "unnumbered_mixed")
    share = mixed["unsafe_share"]
    out.append(("P4", "at least 10%% of reorders of mixed-kind unnumbered sources are unsafe: %s"
                % pct(share), share is not None and share >= 0.10))
    p5 = []
    for g in ("SOV", "SVO"):
        a, b = rate("group:" + g, "numbered"), rate("group:" + g, "unnumbered_mixed")
        p5.append(a is not None and b is not None and a > b)
    out.append(("P5", "in both SOV and SVO, numbered sources are reordered more often than "
                "mixed-kind unnumbered ones: SOV %s vs %s, SVO %s vs %s"
                % (pct(rate("group:SOV", "numbered")), pct(rate("group:SOV", "unnumbered_mixed")),
                   pct(rate("group:SVO", "numbered")), pct(rate("group:SVO", "unnumbered_mixed"))),
                all(p5)))
    c = collections.Counter()
    for kind in ("unnumbered_mixed", "unnumbered_same"):
        c.update(t.counts.get(("all", kind), collections.Counter()))
    out.append(("P6", "on unnumbered sources, translations numbered in the source order outnumber "
                "numbered reorders: %d vs %d" % (c["numbered_in_order"], c["numbered_reordered"]),
                c["numbered_in_order"] > c["numbered_reordered"]))
    return out


def pct(x):
    return "n/a" if x is None else "%.1f%%" % (100 * x)


def scan_repo(census, repo, timeout, tmp_root, deadline):
    record = {"repo": repo["web"], "status": "ok", "sha": "", "pairs": 0}
    if time.time() > deadline:
        record["status"] = "skipped (time budget)"
        return record, []
    dest = tempfile.mkdtemp(prefix="repo-", dir=tmp_root)
    rows = []
    try:
        root = os.path.join(dest, "git")
        record["sha"] = census.fetch(repo["clone"], root, timeout)
        pairs, _ = census.scan_tree(root)
        for p in pairs:
            if "[" in p["key"]:
                continue  # plural forms
            kind, category = classify(p["source"], p["target"])
            if kind is None:
                continue
            path = "%s/%s" % (p["res"], p["file"])
            rows.append({"repo": repo["web"], "res": p["res"], "locale": p["locale"],
                         "lang": language(p["locale"]), "key": p["key"], "kind": kind,
                         "category": category, "source_order": order_text(p["source"]),
                         "target_order": order_text(p["target"]),
                         "source": p["source"], "target": p["target"],
                         "link": census.blob_url(repo["web"], repo["host"], record["sha"], path)})
        record["pairs"] = len(rows)
    except Exception as exc:
        record["status"] = "error"
        record["error"] = str(exc)[-300:]
    finally:
        shutil.rmtree(dest, ignore_errors=True)
    return record, rows


def load_repos(census, data_dir, limit):
    apps, index_url = census.load_index(data_dir)
    groups = collections.OrderedDict()
    for app in sorted(apps, key=lambda a: -(a["updated"] or 0)):
        found = census.repo_of(app["source"])
        if not found:
            continue
        clone, web, host = found
        groups.setdefault(clone.lower(), {"clone": clone, "web": web, "host": host})
    repos = list(groups.values())
    return (repos[:limit] if limit else repos), index_url, len(apps)


def write(out_dir, tally, rows, records, meta):
    os.makedirs(out_dir, exist_ok=True)
    fields = ["repo", "res", "locale", "lang", "key", "kind", "category", "source_order",
              "target_order"]
    with gzip.open(os.path.join(out_dir, "pairs.csv.gz"), "wt", encoding="utf-8",
                   errors="replace", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    bad = sorted((r for r in rows if r["category"] == "unnumbered_reordered"),
                 key=lambda r: (r["repo"], r["locale"], r["key"]))
    with open(os.path.join(out_dir, "unnumbered_reordered.csv"), "w", encoding="utf-8",
              errors="replace", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields + ["source", "target", "link"])
        w.writeheader()
        w.writerows(bad)
    table = []
    scopes = sorted({s for s, _ in tally.counts})
    for scope in scopes:
        for kind in SOURCE_KINDS:
            if (scope, kind) not in tally.counts:
                continue
            r = tally.row(scope, kind)
            lang = scope[5:] if scope.startswith("lang:") else ""
            table.append(dict(scope=scope, group=WORD_ORDER.get(lang, "unassigned") if lang else "",
                              kind=kind, **r))
    with open(os.path.join(out_dir, "by_language.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(table[0].keys()) if table else ["scope"])
        w.writeheader()
        w.writerows(table)
    checks = predictions(tally)
    status = collections.Counter(r["status"] for r in records)
    summary = dict(meta, version=__version__, repos_scanned=len(records),
                   repo_status=dict(status), counted_translations=len(rows),
                   unnumbered_reordered=len(bad),
                   predictions=[{"id": n, "text": text, "held": ok} for n, text, ok in checks],
                   totals={k: tally.row("all", k) for k in SOURCE_KINDS
                           if ("all", k) in tally.counts})
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    with open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8") as f:
        f.write(report(tally, summary, checks))
    return summary


def report(tally, summary, checks):
    lines = ["# Placeholder order in Android app translations (placeholder-order %s)" % __version__,
             "", "Made by MV2 of Munim, Inc. with AI agents. Data: %s, read %s."
             % (summary.get("index_url", ""), summary.get("finished", "")),
             "", "%d repositories scanned (%s); %d translations of non-plural strings with two or "
             "more arguments counted." % (summary["repos_scanned"], ", ".join(
                 "%s %d" % kv for kv in sorted(summary["repo_status"].items())),
                 summary["counted_translations"]), ""]
    lines += ["## Overall", "", "| source | valid | reordered | rate | 95% CI (repos) | unsafe | "
              "numbered in order | other | repos |", "|---|---|---|---|---|---|---|---|---|"]
    for kind in SOURCE_KINDS:
        if ("all", kind) not in tally.counts:
            continue
        r = tally.row("all", kind)
        lines.append("| %s | %d | %d | %s | %s-%s | %d | %d | %d | %d |" % (
            kind, r["valid"], r["reordered"], pct(r["reorder_rate"]), pct(r["ci_low"]),
            pct(r["ci_high"]), r["unsafe"], r["numbered_in_order"], r["other"], r["repos"]))
    lines += ["", "## By word order", ""]
    for kind in ("numbered", "unnumbered_mixed"):
        lines += ["### %s sources" % kind, "", "| group | valid | rate | 95% CI | repo mean | "
                  "unique-pair rate | unsafe | repos |", "|---|---|---|---|---|---|---|---|"]
        for g in ("SOV", "SVO", "VSO", "no dominant order", "unassigned"):
            if ("group:" + g, kind) not in tally.counts:
                continue
            r = tally.row("group:" + g, kind)
            lines.append("| %s | %d | %s | %s-%s | %s | %s | %d | %d |" % (
                g, r["valid"], pct(r["reorder_rate"]), pct(r["ci_low"]), pct(r["ci_high"]),
                pct(r["repo_mean_rate"]), pct(r["unique_reorder_rate"]), r["unsafe"], r["repos"]))
        lines.append("")
    for kind in ("numbered", "unnumbered_mixed"):
        rows = [(s[5:], tally.row(s, k)) for s, k in tally.counts
                if k == kind and s.startswith("lang:")]
        rows = sorted((x for x in rows if x[1]["repos"] >= 10),
                      key=lambda x: -(x[1]["reorder_rate"] or 0))
        lines += ["## Languages, %s sources (10+ repositories)" % kind, "",
                  "| lang | order | valid | rate | 95% CI | repo mean | unsafe | repos |",
                  "|---|---|---|---|---|---|---|---|"]
        for lang, r in rows:
            lines.append("| %s | %s | %d | %s | %s-%s | %s | %d | %d |" % (
                lang, WORD_ORDER.get(lang, "unassigned"), r["valid"], pct(r["reorder_rate"]),
                pct(r["ci_low"]), pct(r["ci_high"]), pct(r["repo_mean_rate"]), r["unsafe"],
                r["repos"]))
        lines.append("")
    lines += ["## Predictions (written before the run)", ""]
    for n, text, ok in checks:
        lines.append("- %s %s: %s" % (n, "HELD" if ok else "FAILED", text))
    lines += ["", "## Limits", "",
              "- Word order groups are a coarse proxy. Where a placeholder lands depends more on "
              "how a language orders a noun and its modifier, a possessor, or a postposition than "
              "on clause order.",
              "- A reorder of two unnumbered placeholders of the same kind cannot be seen, so "
              "unnumbered_same rates count only numbered reorders and are a lower bound.",
              "- Strings shared by many apps (forks, copied libraries) repeat; the repo mean and "
              "unique-pair columns show how much that matters.",
              "- 'unsafe' rows are not all crashes: %s and %d swapped crash only where text "
              "reaches %d; otherwise the values just appear in the wrong places.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--data-dir", default="/data")
    parser.add_argument("--out-dir", default="/out")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--budget-minutes", type=float, default=100)
    parser.add_argument("--timeout", type=int, default=150)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args(argv)

    import census
    import census_fixes
    census_fixes.apply()
    census.USER_AGENT = "mv2-placeholder-order/%s (Munim, Inc.; mv2@munimtech.com)" % __version__
    if not shutil.which("git"):
        raise SystemExit("git is not installed")
    started = time.time()
    meta = {"started": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "census_version": census.__version__}
    repos, meta["index_url"], meta["apps_in_index"] = load_repos(census, args.data_dir, args.limit)
    print("%d repositories" % len(repos), flush=True)
    tmp = tempfile.mkdtemp(prefix="order-")
    deadline = started + args.budget_minutes * 60
    tally, rows, records = Tally(), [], []
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(scan_repo, census, r, args.timeout, tmp, deadline) for r in repos]
            for i, fut in enumerate(concurrent.futures.as_completed(futures), 1):
                record, got = fut.result()
                records.append(record)
                for r in got:
                    tally.add(r["repo"], r["lang"], r["kind"], r["category"], r["source"],
                              r["target"])
                rows.extend(got)
                if i % 250 == 0:
                    print("%d/%d repositories, %d translations" % (i, len(repos), len(rows)),
                          flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    meta["finished"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    summary = write(args.out_dir, tally, rows, records, meta)
    print("placeholder-order: %d translations counted in %d repositories; %d unnumbered reorders"
          % (summary["counted_translations"], summary["repos_scanned"],
             summary["unnumbered_reordered"]), flush=True)
    for p in summary["predictions"]:
        print("%s %s: %s" % (p["id"], "HELD" if p["held"] else "FAILED", p["text"]), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
