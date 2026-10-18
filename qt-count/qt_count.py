#!/usr/bin/env python3
"""qt-count: how often do the plural (numerus) messages of Qt translations
lose their count? A census, with l10n-guard 0.7.0's Qt plural check, of the
.ts files of the 79 open-source Qt projects read by qt-args (39) and by its
right-to-left replication (40).

QCoreApplication::translate() replaces only an ASCII %n or %Ln in a plural
message with the count (replacePercentN). A count written with a look-alike
percent sign (Arabic U+066A, fullwidth U+FF05, small U+FE6A) or with a space
("% n") is shown as written, and a translation none of whose forms has %n
never shows the number.

Each finished plural message of an English source with %n is sorted into
the first of these that applies:

  lookalike   a form writes the count with a look-alike percent sign
  spaced      a form writes it "% n"
  marker      a form writes %1 (or %2...) where the source has no place
              marker, so nothing fills it
  missing     no form has %n (l10n-guard's qt-count-missing warning)
  ok          none of these

Two predictions about the 40 replication projects, whose plural messages
nobody has read, are fixed in PREREG.md before the job runs. The 39 qt-args
projects are counted apart and not graded: some of their files were read by
hand for qt-numerus/FINDINGS.md.

  python qt_count.py --data-dir /data --out-dir /out

Writes qt_count.md, qt_count.json, rows.csv, files.csv and repos.csv.

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import collections
import csv
import datetime
import hashlib
import json
import os
import re
import shutil
import sys
import time
import xml.etree.ElementTree as ET

import l10n_guard as g     # l10n-guard 0.7.0, downloaded from its v0.7.0 tag
import qt_args as qa       # qt-args/qt_args.py 0.1.0: the 39 projects, clone(), ts_files()
import rtl_replicate as rr  # qt-args/rtl-replication/rtl_replicate.py 0.1.0: the 40 projects, fisher_greater()

__version__ = "0.1.0"

# Languages whose usual keyboards and input methods type the Arabic or the
# fullwidth percent sign: Arabic-script languages, Chinese, Japanese, Korean.
ARABIC_SCRIPT = ("ar", "fa", "ur", "ug", "ps", "ckb", "sd", "ks", "prs", "azb", "pnb")
CJK = ("zh", "ja", "ko")
KINDS = ("ok", "lookalike", "spaced", "marker", "missing")
COUNTS = ("total",) + KINDS + ("unfinished", "unfinished_bad")
# The fresh corpus first, so a time budget never cuts the graded part.
CORPORA = (("fresh", rr.REPOS), ("qt-args", qa.REPOS))

# Pre-registered thresholds (PREREG.md), for the fresh corpus only.
MIN_REPOS = 2        # P1: fresh repositories with a finished look-alike count
MIN_GROUP = 200      # finished plural messages with %n in Arabic-script/CJK languages, else P2 is not graded
MIN_OTHER = 2000     # the same in all other languages
ALPHA = 0.01         # P2: one-sided Fisher exact test
MIN_LANG = 50        # finished plural messages for a language row in the report
SAMPLE = 200         # rows listed in the report

# Look-alike counts read by hand before this census (qt-numerus/FINDINGS.md and
# MORE-PROJECTS.md): a self-check that the census finds them, not a prediction.
KNOWN = (("bitcoin/bitcoin", "ar"), ("keepassxreboot/keepassxc", "ar"), ("pbek/QOwnNotes", "ur"),
         ("pbek/QOwnNotes", "ja"))

LOOKALIKE_RE = re.compile("[%s]\\s*L?n(?![A-Za-z])" % g._QT_PERCENTS)
SPACED_RE = re.compile(r"%\s+L?n(?![A-Za-z])")


def group(lang):
    return "arabic_cjk" if lang in ARABIC_SCRIPT + CJK else "other"


def kind_of(source, forms):
    """The kind of one plural message (KINDS), or None if its source has no %n."""
    if not g._QT_COUNT_RE.search(source):
        return None
    filled = [f for f in forms if f.strip()]
    codes = {p["code"] for p in g._qt_count_issues(source, forms, "", g.ERROR)}
    if any(LOOKALIKE_RE.search(f) for f in filled):
        return "lookalike"
    if any(SPACED_RE.search(f) for f in filled):
        return "spaced"
    if "qt-count" in codes:
        return "marker"
    if "qt-count-missing" in codes:
        return "missing"
    return "ok"


class Tally:
    """Plural messages with %n, counted per .ts file, and every one that is
    not ok."""

    def __init__(self):
        self.files = collections.OrderedDict()
        self.rows = []

    def add(self, corpus, repo, commit, path, lang, msg):
        """(state, kind) for one finished or unfinished plural message, or None."""
        if not msg["numerus"] or msg["state"] not in ("finished", "unfinished"):
            return None
        kind = kind_of(msg["source"], msg["forms"])
        if kind is None:
            return None
        f = self.files.setdefault((repo, path), dict({"corpus": corpus, "repo": repo, "file": path, "lang": lang,
                                                      "group": group(lang)}, **{k: 0 for k in COUNTS}))
        if msg["state"] == "finished":
            f["total"] += 1
            f[kind] += 1
        else:
            f["unfinished"] += 1
            f["unfinished_bad"] += kind != "ok"
        if kind != "ok":
            self.rows.append({"corpus": corpus, "repo": repo, "commit": commit, "file": path, "lang": lang,
                              "group": group(lang), "state": msg["state"], "kind": kind,
                              "context": msg["context"], "source": msg["source"],
                              "forms": " || ".join(msg["forms"])})
        return msg["state"], kind


def totals(files, corpus=None):
    """{group: Counter of COUNTS} over the files of one corpus (or all)."""
    out = collections.defaultdict(collections.Counter)
    for f in files:
        if corpus is None or f["corpus"] == corpus:
            for k in COUNTS:
                out[f["group"]][k] += f[k]
    return out


def rate(c, key="lookalike"):
    return c[key] / c["total"] if c["total"] else None


def evaluate(files):
    """The two pre-registered predictions, on the fresh corpus only."""
    files = list(files)
    fresh = [f for f in files if f["corpus"] == "fresh"]
    t = totals(fresh)
    a, o = t["arabic_cjk"], t["other"]
    repos_with = sorted({f["repo"] for f in fresh if f["lookalike"]})
    enough = a["total"] >= MIN_GROUP and o["total"] >= MIN_OTHER
    p = rr.fisher_greater(a["lookalike"], a["total"], o["lookalike"], o["total"]) if a["total"] and o["total"] \
        else None
    p1 = len(repos_with) >= MIN_REPOS
    if not enough:
        p2 = None
    else:
        p2 = bool(p is not None and p < ALPHA and rate(a) > rate(o))
    return {"P1": p1, "P2": p2, "enough_data_for_P2": enough, "fresh_repos_with_lookalike": repos_with,
            "fresh": {"arabic_cjk": dict(a), "other": dict(o), "p": p},
            "known": known_found(files)}


def known_found(files):
    """Finished and unfinished look-alike or other bad counts in the files of KNOWN."""
    out = {}
    for repo, lang in KNOWN:
        c = collections.Counter()
        for f in files:
            if f["repo"] == repo and f["lang"] == lang:
                c["lookalike"] += f["lookalike"]
                c["unfinished_bad"] += f["unfinished_bad"]
                c["total"] += f["total"]
        out["%s %s" % (repo, lang)] = dict(c)
    return out


def scan(corpus, repo, root, commit, tally, record):
    for path in qa.ts_files(root):
        if qa.QT_OWN_RE.match(os.path.basename(path)):
            record["qt_own_skipped"] += 1
            continue
        parsed = qa.parse_ts(path)
        if parsed is None:
            record["not_qt_ts"] += 1
            continue
        lang, source_lang, _ = parsed
        if not lang or lang == "en" or source_lang != "en":
            record["not_counted_language"] += 1
            continue
        try:
            with open(path, "rb") as f:
                messages = g.parse_qt_ts(f.read().decode("utf-8-sig").replace("\r\n", "\n"))
        except (UnicodeDecodeError, ValueError, ET.ParseError):
            record["not_read"] += 1
            continue
        record["ts_files"] += 1
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        for msg in messages:
            got = tally.add(corpus, repo, commit, rel, lang, msg)
            if got is None:
                continue
            state, kind = got
            if state == "finished":
                record["finished"] += 1
                record["finished_" + kind] += kind != "ok"
            else:
                record["unfinished"] += 1


def fmt_rate(x):
    return "n/a" if x is None else "%.3f%%" % (100 * x)


ROW_FIELDS = ["corpus", "repo", "commit", "file", "lang", "group", "state", "kind", "context", "source", "forms"]
FILE_FIELDS = ["corpus", "repo", "file", "lang", "group"] + list(COUNTS)
RECORD_FIELDS = ["corpus", "repo", "status", "commit", "ts_files", "finished", "finished_lookalike",
                 "finished_spaced", "finished_marker", "finished_missing", "unfinished", "qt_own_skipped",
                 "not_qt_ts", "not_counted_language", "not_read"]


def write(out_dir, tally, meta, records):
    os.makedirs(out_dir, exist_ok=True)
    files = list(tally.files.values())
    result = evaluate(files)
    order = {k: i for i, k in enumerate(KINDS)}
    rows = sorted(tally.rows, key=lambda r: (r["corpus"] != "fresh", r["state"], order[r["kind"]], r["repo"],
                                             r["lang"], r["file"], r["source"]))
    with open(os.path.join(out_dir, "rows.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ROW_FIELDS)
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(out_dir, "files.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FILE_FIELDS)
        w.writeheader()
        w.writerows(files)
    with open(os.path.join(out_dir, "repos.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=RECORD_FIELDS)
        w.writeheader()
        for r in records:
            w.writerow({k: r.get(k, 0) for k in RECORD_FIELDS})
    langs = collections.defaultdict(collections.Counter)
    for f in files:
        for k in COUNTS:
            langs[(f["corpus"], f["lang"])][k] += f[k]
    out = dict(meta, version=__version__, result=result,
               totals={c: {grp: dict(v) for grp, v in totals(files, c).items()} for c, _ in CORPORA},
               languages={"%s %s" % k: dict(v) for k, v in sorted(langs.items())},
               repos=[{k: r.get(k, 0) for k in RECORD_FIELDS} for r in records])
    with open(os.path.join(out_dir, "qt_count.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    fresh = result["fresh"]
    ok = sum(r["status"] == "ok" for r in records)
    md = ["# qt-count %s: Qt plural messages that lose their count" % __version__, "",
          "MV2 of Munim, Inc., made with AI agents. Pre-registered in PREREG.md. Qt .ts files of %d of %d "
          "repositories, read with l10n-guard %s (sha256 %s), finished %s. Nothing was run in the apps."
          % (ok, len(records), g.__version__, meta.get("l10n_guard_sha256", "")[:16], meta.get("finished", "")),
          "", "## Predictions (the 40 fresh projects only)", "",
          "- P1 (finished look-alike counts in at least %d fresh repositories): **%s** (%d: %s)" % (
              MIN_REPOS, result["P1"], len(result["fresh_repos_with_lookalike"]),
              ", ".join(result["fresh_repos_with_lookalike"]) or "none"),
          "- P2 (look-alike rate higher in Arabic-script/CJK languages, one-sided Fisher p < %s, with at least "
          "%d and %d messages): **%s** (%d/%d %s against %d/%d %s, p %s)" % (
              ALPHA, MIN_GROUP, MIN_OTHER, "not graded (too little data)" if result["P2"] is None else result["P2"],
              fresh["arabic_cjk"].get("lookalike", 0), fresh["arabic_cjk"].get("total", 0),
              fmt_rate(rate(collections.Counter(fresh["arabic_cjk"]))), fresh["other"].get("lookalike", 0),
              fresh["other"].get("total", 0), fmt_rate(rate(collections.Counter(fresh["other"]))),
              rr.fmt_p(fresh["p"])),
          "", "## All kinds, by corpus and group (finished plural messages with %n)", "",
          "| corpus | group | messages | lookalike | spaced | marker | missing | unfinished | unfinished not ok |",
          "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for corpus, _ in CORPORA:
        for grp, c in sorted(totals(files, corpus).items()):
            md.append("| %s | %s | %d | %d | %d | %d | %d | %d | %d |" % (
                corpus, grp, c["total"], c["lookalike"], c["spaced"], c["marker"], c["missing"], c["unfinished"],
                c["unfinished_bad"]))
    md += ["", "Self-check, cases read by hand before this census (finished look-alike / finished messages / "
           "unfinished not ok): " + "; ".join("%s %d/%d/%d" % (k, v.get("lookalike", 0), v.get("total", 0),
                                                                 v.get("unfinished_bad", 0))
                                              for k, v in result["known"].items()),
           "", "## Languages (%d+ finished plural messages, or any look-alike)" % MIN_LANG, "",
           "| corpus | lang | group | messages | lookalike | spaced | marker | missing | lookalike rate |",
           "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for (corpus, lang), c in sorted(langs.items(), key=lambda kv: (kv[0][0] != "fresh", -kv[1]["lookalike"],
                                                                   -kv[1]["total"])):
        if c["total"] >= MIN_LANG or c["lookalike"]:
            md.append("| %s | %s | %s | %d | %d | %d | %d | %d | %s |" % (
                corpus, lang, group(lang), c["total"], c["lookalike"], c["spaced"], c["marker"], c["missing"],
                fmt_rate(rate(c))))
    md += ["", "## Repositories", "",
           "| corpus | repo | status | commit | .ts files | finished | lookalike | spaced | marker | missing |",
           "|---|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in records:
        md.append("| %s | %s | %s | %s | %d | %d | %d | %d | %d | %d |" % (
            r["corpus"], r["repo"], qa.cell(r["status"], 80), r["commit"][:10], r["ts_files"], r["finished"],
            r["finished_lookalike"], r["finished_spaced"], r["finished_marker"], r["finished_missing"]))
    shown = [r for r in rows if r["state"] == "finished" and r["kind"] != "missing"][:SAMPLE]
    md += ["", "## Finished look-alike, spaced and marker rows (first %d; all rows in rows.csv)" % SAMPLE, "",
           "| corpus | repo | lang | kind | source | forms |", "|---|---|---|---|---|---|"]
    for r in shown:
        md.append("| %s | %s | %s | %s | `%s` | `%s` |" % (r["corpus"], r["repo"], r["lang"], r["kind"],
                                                         qa.cell(r["source"]), qa.cell(r["forms"], 160)))
    with open(os.path.join(out_dir, "qt_count.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    return result


def new_record(corpus, repo):
    record = collections.defaultdict(int)
    record.update({"corpus": corpus, "repo": repo, "status": "", "commit": ""})
    return record


def sha256_of(module):
    with open(module.__file__, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--data-dir", default="/data")
    parser.add_argument("--out-dir", default="/out")
    parser.add_argument("--timeout", type=int, default=900, help="seconds per git step")
    parser.add_argument("--budget-minutes", type=float, default=120)
    args = parser.parse_args(argv)
    if not shutil.which("git"):
        raise SystemExit("git is not installed")
    if g.__version__ != "0.7.0":
        raise SystemExit("expected l10n-guard 0.7.0, got %s" % g.__version__)
    started = time.time()
    deadline = started + args.budget_minutes * 60
    meta = {"started": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "l10n_guard_version": g.__version__, "l10n_guard_sha256": sha256_of(g),
            "qt_args_sha256": sha256_of(qa), "rtl_replicate_sha256": sha256_of(rr)}
    print("l10n_guard.py %s: sha256 %s" % (g.__version__, meta["l10n_guard_sha256"][:16]), flush=True)
    tally, records = Tally(), []
    for corpus, repos in CORPORA:
        for repo in repos:
            record = new_record(corpus, repo)
            records.append(record)
            if time.time() > deadline:
                record["status"] = "not reached (time budget)"
                continue
            root, record["commit"], record["status"] = qa.clone(repo, args.data_dir, args.timeout)
            if record["status"] == "ok":
                scan(corpus, repo, root, record["commit"], tally, record)
            shutil.rmtree(root, ignore_errors=True)
            print("%s %s: %s, %d .ts files, %d finished plural messages with %%n (lookalike %d, spaced %d, "
                  "marker %d, missing %d)" % (corpus, repo, record["status"], record["ts_files"], record["finished"],
                                              record["finished_lookalike"], record["finished_spaced"],
                                              record["finished_marker"], record["finished_missing"]), flush=True)
    meta["finished"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    result = write(args.out_dir, tally, meta, records)
    print("qt-count: P1 %s (%s), P2 %s (p %s); known %s" % (
        result["P1"], ", ".join(result["fresh_repos_with_lookalike"]) or "none", result["P2"],
        rr.fmt_p(result["fresh"]["p"]), json.dumps(result["known"], sort_keys=True)), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
