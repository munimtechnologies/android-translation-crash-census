#!/usr/bin/env python3
"""qt-args RTL replication: a pre-registered test, on Qt projects the
exploratory count never read, of the finding in qt-args/RTL.md that
right-to-left translations write the place marker %1 digit-first ("1%")
far more often than translations into other languages.

The project list, the predictions and their thresholds are fixed in
PREREG.md and in this file before any of these projects' .ts files were
read. It reuses qt_args.py 0.1.0 (parse_ts, classify, hints, clone)
unchanged, so "reversed" means exactly what it meant in RTL.md: the first
hint of a finished translation whose markers are lost or misplaced is the
marker's digit followed by %, with no digit before it.

  python rtl_replicate.py --data-dir /data --out-dir /out

Writes rtl_replication.md, rtl_replication.json, reversed_rows.csv,
files.csv and repos.csv.

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import collections
import csv
import datetime
import hashlib
import json
import math
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, os.path.join(HERE, ".."))  # qt-args/qt_args.py in the repository
import qt_args as qa  # noqa: E402

__version__ = "0.1.0"

# The right-to-left languages RTL.md counted.
RTL = ("ar", "fa", "he", "ur", "ug", "yi", "ps")
# Other languages often written right to left or in Arabic script, which
# RTL.md did not count: left out of both groups.
EXCLUDED = ("ku", "ckb", "sd", "dv", "syr", "ks", "prs", "azb", "mzn", "glk", "lrc", "bal", "arc",
            "bqi", "sdh", "pnb")

# Fixed before any of their .ts files were read (PREREG.md): open-source Qt
# code bases believed to keep .ts files in the repository, read at the
# default branch. One that has none, or fails to clone, counts as nothing
# found and is reported; none is swapped for another.
REPOS = [
    "transmission/transmission", "sqlitebrowser/sqlitebrowser", "mixxxdj/mixxx", "texstudio-org/texstudio",
    "OpenBoard-org/OpenBoard", "qelectrotech/qelectrotech-source-mirror", "Nheko-Reborn/nheko",
    "pencil2d/pencil", "Komet/MediaElch", "vkohaupt/vokoscreenNG", "webcamoid/webcamoid", "IJHack/QtPass",
    "haiwen/seafile-client", "dail8859/NotepadNext", "vnotex/vnote", "jurplel/qView", "MatsuriDayo/nekoray",
    "qt-creator/qt-creator", "rncbc/qtractor", "Martchus/syncthingtray", "MaartenBaert/ssr",
    "Maproom/qmapshack", "BelledonneCommunications/linphone-desktop", "mpc-qt/mpc-qt",
    "GoldenCheetah/GoldenCheetah", "ra3xdh/qucs_s", "YACReader/yacreader", "Faster3ck/Converseen",
    "rizinorg/cutter-translations", "psi-im/psi-l10n", "quotient-im/Quaternion", "ukui/ukui-control-center",
    "openstreetmap/merkaartor", "tomahawk-player/tomahawk", "veyon/veyon", "fooyin/fooyin",
    "trialuser02/qt6ct", "x64dbg/x64dbg", "CloudCompare/CloudCompare", "moonlight-stream/moonlight-qt",
]
# Forks and ancestors of the 39 exploratory projects: their translations overlap.
RELATED = ("owncloud/client", "goldendict/goldendict", "keepassx/keepassx", "TokTok/qTox",
           "c0re100/qBittorrent-Enhanced-Edition")

# Pre-registered thresholds (PREREG.md).
MIN_RTL = 500        # finished right-to-left translations with markers, else "too little data"
MIN_OTHER = 10000    # finished translations with markers in all other languages
RATIO = 5.0          # right-to-left reversed rate over the other languages' rate
ALPHA_MAIN = 0.001   # one-sided Fisher exact test, P1
ALPHA_LOO = 0.01     # the same with the top repository left out, P3
MIN_REPOS = 3        # repositories with a right-to-left reversed row, P2
MIN_LANG = 200       # translations for a language row in the report
SAMPLE = 40          # rows listed per group in the report
COUNTS = ("total", "broken", "reversed", "reversed_any")


def independent(repo):
    """False for one of the 39 exploratory projects, a repository of one of
    their owners, or a known fork or ancestor of one."""
    low = repo.lower()
    owners = {r.split("/")[0].lower() for r in qa.REPOS}
    return (low not in {r.lower() for r in qa.REPOS} and low.split("/")[0] not in owners
            and low not in {r.lower() for r in RELATED})


def group(lang):
    return "rtl" if lang in RTL else "excluded" if lang in EXCLUDED else "other"


def _lcomb(n, k):
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def fisher_greater(a, n1, c, n2):
    """One-sided Fisher exact p: the chance of a or more successes in the
    first group (size n1) when a + c successes fall at random over n1 + n2."""
    k, n = a + c, n1 + n2
    lo, hi = max(a, n1 - (n - k)), min(k, n1)
    p = sum(math.exp(_lcomb(k, x) + _lcomb(n - k, n1 - x) - _lcomb(n, n1)) for x in range(lo, hi + 1))
    return min(1.0, p)


class Tally:
    """Finished translations with markers, counted per .ts file, and every
    row with a reversed hint."""

    def __init__(self):
        self.files = collections.OrderedDict()
        self.rows = []

    def add(self, repo, commit, path, lang, msg):
        """(category, reversed first) for one finished message, or None if
        its source has no marker."""
        got = qa.classify(msg["source"], msg["translation"])
        if got is None:
            return None
        category = got[0]
        hs = qa.hints(msg["source"], msg["translation"]) if category != "ok" else []
        first = bool(hs) and hs[0].startswith("reversed:")
        anywhere = any(h.startswith("reversed:") for h in hs)
        f = self.files.setdefault((repo, path), {"repo": repo, "file": path, "lang": lang, "group": group(lang),
                                                 "total": 0, "broken": 0, "reversed": 0, "reversed_any": 0})
        f["total"] += 1
        f["broken"] += category != "ok"
        f["reversed"] += first
        f["reversed_any"] += anywhere
        if anywhere:
            self.rows.append({"repo": repo, "commit": commit, "file": path, "lang": lang, "group": group(lang),
                              "category": category, "reversed_first": int(first), "hints": ";".join(hs),
                              "context": msg["context"], "source": msg["source"],
                              "translation": msg["translation"]})
        return category, first


def totals(files, skip_repo=None):
    """{group: Counter of COUNTS} over files, leaving out one repository if asked."""
    out = collections.defaultdict(collections.Counter)
    for f in files:
        if f["repo"] == skip_repo:
            continue
        for k in COUNTS:
            out[f["group"]][k] += f[k]
    return out


def compare(t, key="reversed"):
    """Right-to-left against other languages for one count."""
    r, o = t["rtl"], t["other"]
    rate_r = r[key] / r["total"] if r["total"] else None
    rate_o = o[key] / o["total"] if o["total"] else None
    if rate_r is None or rate_o is None:
        ratio = None
    elif rate_o == 0:
        ratio = math.inf if rate_r > 0 else None
    else:
        ratio = rate_r / rate_o
    p = fisher_greater(r[key], r["total"], o[key], o["total"]) if r["total"] and o["total"] else None
    return {"rtl": r[key], "rtl_total": r["total"], "other": o[key], "other_total": o["total"],
            "rtl_rate": rate_r, "other_rate": rate_o, "ratio": ratio, "p": p}


def evaluate(files):
    """The three pre-registered predictions and the verdict."""
    files = list(files)
    main = compare(totals(files))
    by_repo = collections.Counter()
    for f in files:
        if f["group"] == "rtl":
            by_repo[f["repo"]] += f["reversed"]
    repos_with = sorted(r for r, n in by_repo.items() if n)
    top = max(repos_with, key=lambda r: by_repo[r]) if repos_with else None
    loo = compare(totals(files, skip_repo=top)) if top else main
    enough = main["rtl_total"] >= MIN_RTL and main["other_total"] >= MIN_OTHER
    p1 = bool(enough and main["ratio"] is not None and main["ratio"] >= RATIO and main["p"] < ALPHA_MAIN)
    p2 = len(repos_with) >= MIN_REPOS
    p3 = bool(loo["ratio"] is not None and loo["ratio"] >= RATIO and loo["p"] is not None
              and loo["p"] < ALPHA_LOO)
    if not enough:
        verdict = "too little data"
    elif not p1:
        verdict = "not replicated"
    elif p2 and p3:
        verdict = "replicated"
    else:
        verdict = "partly replicated"
    return {"verdict": verdict, "enough_data": enough, "P1": p1, "P2": p2, "P3": p3, "main": main,
            "repos_with_rtl_reversed": {r: by_repo[r] for r in repos_with}, "left_out_repo": top,
            "leave_one_repo_out": loo, "any_hint": compare(totals(files), "reversed_any")}


def by_language(files):
    out = collections.defaultdict(collections.Counter)
    for f in files:
        for k in COUNTS:
            out[f["lang"]][k] += f[k]
    return out


def scan(repo, root, commit, tally, record):
    for path in qa.ts_files(root):
        if qa.QT_OWN_RE.match(os.path.basename(path)):
            record["qt_own_skipped"] += 1
            continue
        parsed = qa.parse_ts(path)
        if parsed is None:
            record["not_qt_ts"] += 1
            continue
        lang, source_lang, messages = parsed
        if not lang or lang == "en" or source_lang != "en":
            record["not_counted_language"] += 1
            continue
        record["ts_files"] += 1
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        for msg in messages:
            if msg["state"] != "finished" or not msg["source"].strip() or not msg["translation"].strip():
                continue
            got = tally.add(repo, commit, rel, lang, msg)
            if got is not None:
                record[group(lang) + "_total"] += 1
                record[group(lang) + "_reversed"] += got[1]


def fmt_rate(x):
    return "n/a" if x is None else "%.3f%%" % (100 * x)


def fmt_ratio(x):
    return "n/a" if x is None else "inf" if math.isinf(x) else "%.1f" % x


def fmt_p(x):
    return "n/a" if x is None else "%.2g" % x


ROW_FIELDS = ["repo", "commit", "file", "lang", "group", "category", "reversed_first", "hints", "context",
              "source", "translation"]
FILE_FIELDS = ["repo", "file", "lang", "group"] + list(COUNTS)
RECORD_FIELDS = ["repo", "status", "commit", "ts_files", "rtl_total", "rtl_reversed", "other_total",
                 "other_reversed", "excluded_total", "excluded_reversed", "qt_own_skipped", "not_qt_ts",
                 "not_counted_language"]


def write(out_dir, tally, meta, records):
    os.makedirs(out_dir, exist_ok=True)
    files = list(tally.files.values())
    result = evaluate(files)
    langs = by_language(files)
    rows = sorted(tally.rows, key=lambda r: (r["group"], r["repo"], r["lang"], r["file"], r["source"],
                                             r["translation"]))
    with open(os.path.join(out_dir, "reversed_rows.csv"), "w", newline="", encoding="utf-8") as f:
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
    out = dict(meta, version=__version__, result=result,
               languages={k: dict(v) for k, v in sorted(langs.items())},
               repos=[{k: r.get(k, 0) for k in RECORD_FIELDS} for r in records])
    with open(os.path.join(out_dir, "rtl_replication.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    m, loo, anyh = result["main"], result["leave_one_repo_out"], result["any_hint"]
    ok = sum(r["status"] == "ok" for r in records)
    md = ["# qt-args RTL replication %s: verdict **%s**" % (__version__, result["verdict"]), "",
          "MV2 of Munim, Inc., made with AI agents. Pre-registered in PREREG.md. Qt .ts files of %d of %d "
          "repositories, read %s. Nothing was run on a device." % (ok, len(records), meta.get("finished", "")), "",
          "| | right-to-left reversed | right-to-left finished | rate | other reversed | other finished | rate "
          "| ratio | one-sided p |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name, c in (("all repositories (P1)", m), ("without %s (P3)" % loo_name(result), loo),
                    ("any reversed hint (not graded)", anyh)):
        md.append("| %s | %d | %d | %s | %d | %d | %s | %s | %s |" % (
            name, c["rtl"], c["rtl_total"], fmt_rate(c["rtl_rate"]), c["other"], c["other_total"],
            fmt_rate(c["other_rate"]), fmt_ratio(c["ratio"]), fmt_p(c["p"])))
    md += ["",
           "- Enough data (at least %d right-to-left and %d other finished translations with markers): %s"
           % (MIN_RTL, MIN_OTHER, result["enough_data"]),
           "- P1 (ratio >= %s and p < %s): %s" % (RATIO, ALPHA_MAIN, result["P1"]),
           "- P2 (right-to-left reversed rows in >= %d repositories): %s (%d: %s)" % (
               MIN_REPOS, result["P2"], len(result["repos_with_rtl_reversed"]),
               ", ".join("%s %d" % kv for kv in result["repos_with_rtl_reversed"].items()) or "none"),
           "- P3 (ratio >= %s and p < %s without the repository with the most right-to-left reversed rows): %s"
           % (RATIO, ALPHA_LOO, result["P3"]),
           "", "## Languages (all right-to-left ones, others with %d+ finished translations with markers)" % MIN_LANG,
           "", "| lang | group | finished with markers | lost or misplaced | reversed | rate |",
           "|---|---|---:|---:|---:|---:|"]
    for lang, c in sorted(langs.items(), key=lambda kv: (group(kv[0]) != "rtl", -kv[1]["total"])):
        if group(lang) == "rtl" or c["total"] >= MIN_LANG:
            md.append("| %s | %s | %d | %d | %d | %s |" % (lang, group(lang), c["total"], c["broken"], c["reversed"],
                                                          fmt_rate(c["reversed"] / c["total"] if c["total"] else None)))
    md += ["", "## Repositories", "",
           "| repo | status | commit | .ts files | right-to-left | reversed | other | reversed |",
           "|---|---|---|---:|---:|---:|---:|---:|"]
    for r in records:
        md.append("| %s | %s | %s | %d | %d | %d | %d | %d |" % (
            r["repo"], qa.cell(r["status"], 80), r["commit"][:10], r["ts_files"], r["rtl_total"],
            r["rtl_reversed"], r["other_total"], r["other_reversed"]))
    for name in ("rtl", "other"):
        shown = [r for r in rows if r["group"] == name and r["reversed_first"]][:SAMPLE]
        md += ["", "## First %d %s reversed rows (all in reversed_rows.csv)" % (SAMPLE, name), "",
               "| repo | lang | source | translation | hints |", "|---|---|---|---|---|"]
        for r in shown:
            md.append("| %s | %s | `%s` | `%s` | %s |" % (r["repo"], r["lang"], qa.cell(r["source"]),
                                                       qa.cell(r["translation"]), r["hints"]))
    with open(os.path.join(out_dir, "rtl_replication.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    return result


def loo_name(result):
    return result["left_out_repo"] or "no repository"


def new_record(repo):
    record = collections.defaultdict(int)
    record.update({"repo": repo, "status": "", "commit": ""})
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--data-dir", default="/data")
    parser.add_argument("--out-dir", default="/out")
    parser.add_argument("--timeout", type=int, default=900, help="seconds per git step")
    parser.add_argument("--budget-minutes", type=float, default=100)
    args = parser.parse_args(argv)
    if not shutil.which("git"):
        raise SystemExit("git is not installed")
    bad = [r for r in REPOS if not independent(r)]
    if bad:
        raise SystemExit("not independent of the exploratory projects: %s" % bad)
    with open(qa.__file__, "rb") as f:
        qa_sha = hashlib.sha256(f.read()).hexdigest()
    started = time.time()
    deadline = started + args.budget_minutes * 60
    meta = {"started": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "qt_args_version": qa.__version__, "qt_args_sha256": qa_sha}
    tally, records = Tally(), []
    for repo in REPOS:
        record = new_record(repo)
        records.append(record)
        if time.time() > deadline:
            record["status"] = "not reached (time budget)"
            continue
        root, record["commit"], record["status"] = qa.clone(repo, args.data_dir, args.timeout)
        if record["status"] == "ok":
            scan(repo, root, record["commit"], tally, record)
        shutil.rmtree(root, ignore_errors=True)
        print("%s: %s, %d .ts files, right-to-left %d (%d reversed), other %d (%d reversed)"
              % (repo, record["status"], record["ts_files"], record["rtl_total"], record["rtl_reversed"],
                 record["other_total"], record["other_reversed"]), flush=True)
    meta["finished"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    result = write(args.out_dir, tally, meta, records)
    for name, c in (("main", result["main"]), ("leave-one-repo-out", result["leave_one_repo_out"]),
                    ("any-hint", result["any_hint"])):
        print("%s: rtl %d/%d (%s), other %d/%d (%s), ratio %s, p %s" % (
            name, c["rtl"], c["rtl_total"], fmt_rate(c["rtl_rate"]), c["other"], c["other_total"],
            fmt_rate(c["other_rate"]), fmt_ratio(c["ratio"]), fmt_p(c["p"])), flush=True)
    print("rtl-replication: %s (P1 %s, P2 %s, P3 %s; left out %s)" % (
        result["verdict"], result["P1"], result["P2"], result["P3"], loo_name(result)), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
