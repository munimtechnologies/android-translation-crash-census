#!/usr/bin/env python3
"""qt-args: what do Qt translations whose %N place markers differ from the
source actually show? A census of the .ts files of open-source Qt projects.

Code that formats a translated Qt string calls QString::arg() once per
argument (or once with several). Each call fills the LOWEST-numbered place
marker still in the text (qtbase src/corelib/text/qstring.cpp,
findArgEscapes / parseMultiArgFormatString), so the i-th argument lands in
the i-th smallest marker number of the TRANSLATION, whatever the translator
meant. A marker is % then an optional L then one or two digits; %0 counts.
Since Qt 6.6, only ASCII digits make a marker unless the environment
variable QT_USE_UNICODE_DIGIT_VALUES_IN_STRING_ARG is set (older Qt also
accepted digits such as Bengali U+09E7 in single-argument calls).

For each finished, non-plural translation of an English source with at
least one marker, this simulates that rule and sorts the translation into:

  ok           every marker shows the value it shows in the source, and
               markers the source lacks (Turkish "%50" percentages above
               the source's markers) stay as text
  dropped      nothing is misplaced, but at least one argument is never
               shown (Qt logs "QString::arg: Argument missing")
  wrong_value  some marker shows another marker's value, a marker the
               source lacks takes an argument, or a source marker is left
               as text

It assumes the code passes as many arguments as the source has distinct
markers, which is how .arg() is normally used; rows are candidates to read
in the project's code, not confirmed bugs. Unfinished translations (which
lrelease can still ship unless -nounfinished is given) are counted apart.

This is a counting pass with no predictions: its numbers fix the sample
sizes of any later pre-registered test.

  python qt_args.py --data-dir /data --out-dir /out

Writes qt_args.md, qt_args.json, rows.csv, by_language.csv and repos.csv.

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import collections
import csv
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

__version__ = "0.1.0"

# The same 39 projects as qt-shape 0.1.0: open-source Qt code bases that keep
# their .ts files in the repository, one per code base, read at the default
# branch.
REPOS = [
    "qbittorrent/qBittorrent", "keepassxreboot/keepassxc", "nextcloud/desktop", "musescore/MuseScore",
    "mumble-voip/mumble", "flameshot-org/flameshot", "hluk/CopyQ", "Mudlet/Mudlet", "mltframework/shotcut",
    "PCSX2/pcsx2", "stenzek/duckstation", "mapeditor/tiled", "LibreCAD/LibreCAD", "bitcoin/bitcoin",
    "monero-project/monero-gui", "Sigil-Ebook/Sigil", "LMMS/lmms", "Cockatrice/Cockatrice",
    "lxqt/lxqt-panel", "lxqt/pcmanfm-qt", "lxqt/qterminal", "wireshark/wireshark",
    "scribusproject/scribus", "AntiMicroX/antimicrox", "Qalculate/qalculate-qt", "qTox/qTox",
    "tsujan/FeatherPad", "ksnip/ksnip", "nomacs/nomacs", "hydrogen-music/hydrogen", "smplayer-dev/smplayer",
    "pbek/QOwnNotes", "xiaoyifang/goldendict-ng", "fritzing/fritzing-app", "subsurface/subsurface",
    "tumic0/GPXSee", "savoirfairelinux/jami-client-qt", "linuxdeepin/dde-file-manager",
    "FreeCAD/FreeCAD",
]

OLD_CODES = {"iw": "he", "in": "id", "ji": "yi", "jw": "jv"}
CATEGORIES = ("ok", "dropped", "wrong_value")
STATES = ("finished", "unfinished")
MIN_LANG = 200      # translations for a language row in the report
SAMPLE = 60         # wrong_value rows listed in the report
ASCII_RE = re.compile(r"%L?([0-9]{1,2})")
UNICODE_RE = re.compile(r"%L?(\d{1,2})")
# Copies of Qt's own translations (qt_fa.ts, qtbase_ja.ts) that projects ship.
QT_OWN_RE = re.compile(r"^(?:qt|qtbase|qtdeclarative|qtmultimedia|qtscript|qtxmlpatterns|qtconnectivity|"
                       r"qtlocation|qtquickcontrols2?|qtserialport|qtwebengine|qtwebsockets|qt_help|"
                       r"assistant|designer|linguist|qtconfig)_[A-Za-z]{2,3}(?:[_@-][^.]*)?\.ts$")
PERCENT_LIKE = "٪％﹪"  # Arabic percent, fullwidth percent, small percent


def lang_code(code):
    """zh_CN -> zh, sr@latin -> sr, pt-BR -> pt, iw -> he."""
    lang = re.split(r"[_@.\-]", (code or "").strip())[0].lower()
    return OLD_CODES.get(lang, lang)


def file_lang(name):
    """The language in a .ts file name (keepassxc_zh_CN.ts -> zh), or ""."""
    stem = name[:-3] if name.endswith(".ts") else name
    for part in stem.split("_")[1:]:
        if re.fullmatch(r"[a-z]{2,3}(?:@\w+)?", part):
            return lang_code(part)
    return ""


def parse_ts(path):
    """(language, source language, [message dict]) for a Qt .ts file, or None
    if the file is not one (TypeScript, broken XML). Each message dict has
    source, translation, state (finished/unfinished/numerus/obsolete),
    context, location and line."""
    try:
        with open(path, "rb") as f:
            head = f.read(4096)
        if b"<TS" not in head:
            return None
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return None
    if root.tag != "TS":
        return None
    lang = lang_code(root.get("language")) or file_lang(os.path.basename(path))
    messages = []
    for ctx in root.iter("context"):
        name = ctx.findtext("name") or ""
        for msg in ctx.iter("message"):
            s, t = msg.find("source"), msg.find("translation")
            if s is None or t is None:
                continue
            kind = t.get("type") or ""
            if kind in ("obsolete", "vanished"):
                state = "obsolete"
            elif msg.get("numerus") == "yes":
                state = "numerus"
            elif kind == "unfinished":
                state = "unfinished"
            else:
                state = "finished"
            loc = msg.find("location")
            messages.append({"source": "".join(s.itertext()), "translation": "".join(t.itertext()),
                             "state": state, "context": name,
                             "location": loc.get("filename", "") if loc is not None else "",
                             "line": loc.get("line", "") if loc is not None else ""})
    return lang, lang_code(root.get("sourcelanguage") or "en"), messages


def markers(text, unicode_digits=False):
    """Sorted distinct place-marker numbers QString::arg() sees in text."""
    rx = UNICODE_RE if unicode_digits else ASCII_RE
    return sorted({int(m.group(1)) for m in rx.finditer(text)})


def classify(source, target, unicode_digits=False):
    """(category, source markers, translation markers, wrong, missing) or
    None if the source has no marker. wrong lists (marker, meant, shown):
    meant/shown are 1-based argument numbers, None for "left as text";
    missing lists the arguments the translation never shows."""
    src = markers(source)
    if not src:
        return None
    tgt = markers(target, unicode_digits)
    meant = {n: i + 1 for i, n in enumerate(src)}
    shown = {n: (i + 1 if i < len(src) else None) for i, n in enumerate(tgt)}
    wrong = [(n, meant.get(n), shown[n]) for n in tgt if meant.get(n) != shown[n]]
    used = set(v for v in shown.values() if v)
    missing = [i for i in range(1, len(src) + 1) if i not in used]
    category = "wrong_value" if wrong else "dropped" if missing else "ok"
    return category, src, tgt, wrong, missing


def wrong_kinds(wrong):
    """The kinds of misplacement in a wrong list."""
    out = set()
    for _, meant, shown in wrong:
        out.add("text_marker_takes_value" if meant is None else "marker_left_as_text" if shown is None
                else "value_moved")
    return sorted(out)


def hints(source, target):
    """What the translator may have written instead of each source marker the
    translation lacks: 1% (reversed), % 1 (spaced), Arabic/fullwidth percent,
    a non-ASCII digit, or a printf %s/%d."""
    src, tgt = markers(source), markers(target)
    out = []
    for n in src:
        if n in tgt:
            continue
        d = str(n)
        if re.search(r"(?<![0-9])%s%%" % d, target) and not re.search(r"(?<![0-9])%s%%" % d, source):
            out.append("reversed:%s%%" % d)
        if re.search(r"%%\s+%s(?![0-9])" % d, target):
            out.append("spaced:%% %s" % d)
        if re.search(r"[%s]L?%s(?![0-9])" % (PERCENT_LIKE, d), target):
            out.append("percent_sign:%s" % d)
        if any(int(m.group(1)) == n and not m.group(1).isascii() for m in UNICODE_RE.finditer(target)):
            out.append("non_ascii_digit:%s" % d)
    if re.search(r"%[sd]", target) and not re.search(r"%[sd]", source):
        out.append("printf")
    return out


class Tally:
    """Counts by (state, scope, category), raw and per repository, and the
    rows worth reading."""

    def __init__(self):
        self.counts = collections.Counter()
        self.repo_counts = collections.defaultdict(collections.Counter)
        self.kinds = collections.Counter()
        self.unique = collections.defaultdict(dict)
        self.rows = []
        self.legacy_differs = collections.Counter()

    def add(self, repo, commit, path, lang, msg):
        got = classify(msg["source"], msg["translation"])
        if got is None:
            return None
        category, src, tgt, wrong, missing = got
        legacy = classify(msg["source"], msg["translation"], unicode_digits=True)[0]
        state = msg["state"]
        for scope in ("all", "lang:" + lang):
            self.counts[(state, scope, category)] += 1
        self.repo_counts[(state, repo)][category] += 1
        self.unique[state][(lang, msg["source"], msg["translation"])] = category
        if legacy != category:
            self.legacy_differs[(state, category, legacy)] += 1
        if category == "wrong_value":
            for k in wrong_kinds(wrong):
                self.kinds[(state, k)] += 1
        if category != "ok" or legacy != category:
            self.rows.append({
                "repo": repo, "commit": commit, "file": path, "lang": lang, "state": state,
                "category": category, "category_before_qt66": legacy, "kinds": ";".join(wrong_kinds(wrong)),
                "source_markers": " ".join(map(str, src)), "translation_markers": " ".join(map(str, tgt)),
                "wrong": ";".join("%%%d:%s->%s" % (n, m or "text", s or "text") for n, m, s in wrong),
                "missing": " ".join(map(str, missing)), "hints": ";".join(hints(msg["source"], msg["translation"])),
                "context": msg["context"], "location": msg["location"], "line": msg["line"],
                "source": msg["source"], "translation": msg["translation"]})
        return category

    def row(self, state, scope):
        out = {c: self.counts[(state, scope, c)] for c in CATEGORIES}
        out["total"] = sum(out.values())
        for c in ("dropped", "wrong_value"):
            out[c + "_rate"] = out[c] / out["total"] if out["total"] else None
        return out

    def repo_rates(self, state, category):
        """Per-repository rates of category (repositories with any counted
        translation)."""
        rates = []
        for (st, _), c in self.repo_counts.items():
            total = sum(c[x] for x in CATEGORIES)
            if st == state and total:
                rates.append(c[category] / total)
        return sorted(rates)


def median(xs):
    if not xs:
        return None
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2


def pct(x):
    return "n/a" if x is None else "%.2f%%" % (100 * x)


def git(args, timeout):
    return subprocess.run(["git"] + args, capture_output=True, text=True, timeout=timeout)


def clone(repo, data_dir, timeout):
    """(folder, commit, status): a shallow, blob-filtered clone holding only
    the repository's *.ts files."""
    dest = os.path.join(data_dir, "qt-ts", repo.replace("/", "__"))
    shutil.rmtree(dest, ignore_errors=True)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    try:
        r = git(["clone", "--quiet", "--depth", "1", "--filter=blob:none", "--sparse",
                 "https://github.com/%s.git" % repo, dest], timeout)
        if r.returncode:
            return dest, "", "clone failed: " + r.stderr.strip()[-200:]
        r = git(["-C", dest, "sparse-checkout", "set", "--no-cone", "*.ts"], timeout)
        if r.returncode:
            return dest, "", "sparse-checkout failed: " + r.stderr.strip()[-200:]
        commit = git(["-C", dest, "rev-parse", "HEAD"], 60).stdout.strip()
    except subprocess.TimeoutExpired:
        return dest, "", "timed out"
    return dest, commit, "ok"


def ts_files(root):
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        for name in sorted(files):
            if name.endswith(".ts"):
                yield os.path.join(dirpath, name)


def scan(repo, root, commit, t, record):
    for path in ts_files(root):
        name = os.path.basename(path)
        if QT_OWN_RE.match(name):
            record["qt_own_skipped"] += 1
            continue
        parsed = parse_ts(path)
        if parsed is None:
            record["not_qt_ts"] += 1
            continue
        lang, source_lang, messages = parsed
        if not lang or lang == "en" or source_lang != "en":
            record["not_counted_language"] += 1
            continue
        record["ts_files"] += 1
        record["languages"].add(lang)
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        for msg in messages:
            if not msg["source"].strip() or not msg["translation"].strip():
                continue
            if msg["state"] not in STATES:
                record[msg["state"] + "_skipped"] += 1
                continue
            category = t.add(repo, commit, rel, lang, msg)
            if category is not None:
                record[msg["state"] + "_with_markers"] += 1
                if category != "ok":
                    record[msg["state"] + "_" + category] += 1


RECORD_FIELDS = ["repo", "status", "commit", "ts_files", "languages", "finished_with_markers", "finished_dropped",
                 "finished_wrong_value", "unfinished_with_markers", "unfinished_dropped", "unfinished_wrong_value",
                 "numerus_skipped", "obsolete_skipped", "qt_own_skipped", "not_qt_ts", "not_counted_language"]
ROW_FIELDS = ["repo", "commit", "file", "lang", "state", "category", "category_before_qt66", "kinds",
              "source_markers", "translation_markers", "wrong", "missing", "hints", "context", "location", "line",
              "source", "translation"]


def cell(text, width=90):
    return (text.replace("|", "\\|").replace("`", "'").replace("\n", " ").replace("\r", " ")[:width])


def write(out_dir, t, meta, records):
    os.makedirs(out_dir, exist_ok=True)
    order = {c: i for i, c in enumerate(("wrong_value", "dropped", "ok"))}
    rows = sorted(t.rows, key=lambda r: (r["state"], order[r["category"]], r["repo"], r["lang"], r["file"],
                                         r["source"], r["translation"]))
    with open(os.path.join(out_dir, "rows.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ROW_FIELDS)
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(out_dir, "repos.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=RECORD_FIELDS)
        w.writeheader()
        for r in records:
            w.writerow({k: (len(r[k]) if k == "languages" else r.get(k, 0)) for k in RECORD_FIELDS})
    langs = sorted({scope[5:] for (_, scope, _) in t.counts if scope.startswith("lang:")})
    lang_rows = []
    for lang in langs:
        line = {"lang": lang}
        for state in STATES:
            r = t.row(state, "lang:" + lang)
            for c in CATEGORIES:
                line["%s_%s" % (state, c)] = r[c]
        lang_rows.append(line)
    with open(os.path.join(out_dir, "by_language.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["lang"] + ["%s_%s" % (s, c) for s in STATES for c in CATEGORIES])
        w.writeheader()
        w.writerows(lang_rows)

    summary = {}
    for state in STATES:
        r = t.row(state, "all")
        u = t.unique[state]
        summary[state] = dict(r, unique=len(u), unique_dropped=sum(v == "dropped" for v in u.values()),
                              unique_wrong_value=sum(v == "wrong_value" for v in u.values()),
                              repos_with_wrong_value=sum(1 for (st, _), c in t.repo_counts.items()
                                                         if st == state and c["wrong_value"]),
                              repo_median_wrong_value_rate=median(t.repo_rates(state, "wrong_value")),
                              repo_median_dropped_rate=median(t.repo_rates(state, "dropped")),
                              wrong_kinds={k: n for (st, k), n in t.kinds.items() if st == state},
                              before_qt66_differs={"%s->%s" % (a, b): n for (st, a, b), n in t.legacy_differs.items()
                                                   if st == state})
    result = dict(meta, version=__version__, summary=summary,
                  repos=[dict(r, languages=sorted(r["languages"])) for r in records])
    with open(os.path.join(out_dir, "qt_args.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1, ensure_ascii=False)

    ok = sum(r["status"] == "ok" for r in records)
    md = ["# qt-args %s: what Qt translations with mismatched %%N place markers show" % __version__, "",
          "MV2 of Munim, Inc., made with AI agents. Qt .ts files of %d of %d repositories, read %s. A counting "
          "pass: rows are candidates to read in each project's code, not confirmed bugs."
          % (ok, len(records), meta.get("finished", "")), "",
          "| state | with markers | dropped | wrong value | dropped rate | wrong-value rate | unique wrong value "
          "| repos with wrong value | repo median wrong-value rate |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for state in STATES:
        s = summary[state]
        md.append("| %s | %d | %d | %d | %s | %s | %d | %d | %s |" % (
            state, s["total"], s["dropped"], s["wrong_value"], pct(s["dropped_rate"]), pct(s["wrong_value_rate"]),
            s["unique_wrong_value"], s["repos_with_wrong_value"], pct(s["repo_median_wrong_value_rate"])))
    for state in STATES:
        md += ["", "- %s wrong-value kinds: %s" % (state, ", ".join(
            "%s %d" % kv for kv in sorted(summary[state]["wrong_kinds"].items())) or "none"),
               "- %s rows whose category differs before Qt 6.6 (non-ASCII digits accepted): %s" % (state, ", ".join(
                   "%s %d" % kv for kv in sorted(summary[state]["before_qt66_differs"].items())) or "none")]
    md += ["", "## Languages (%d+ finished translations with markers)" % MIN_LANG, "",
           "| lang | finished | dropped | wrong value | wrong-value rate |", "|---|---:|---:|---:|---:|"]
    lines = []
    for line in lang_rows:
        total = sum(line["finished_" + c] for c in CATEGORIES)
        if total >= MIN_LANG:
            lines.append((line["finished_wrong_value"] / total, line["lang"], total, line["finished_dropped"],
                          line["finished_wrong_value"]))
    for rate, lang, total, dropped, wrong in sorted(lines, reverse=True):
        md.append("| %s | %d | %d | %d | %s |" % (lang, total, dropped, wrong, pct(rate)))
    md += ["", "## Repositories", "",
           "| repo | status | commit | .ts files | languages | finished with markers | dropped | wrong value |",
           "|---|---|---|---:|---:|---:|---:|---:|"]
    for r in records:
        md.append("| %s | %s | %s | %d | %d | %d | %d | %d |" % (
            r["repo"], cell(r["status"], 80), r["commit"][:10], r["ts_files"], len(r["languages"]),
            r["finished_with_markers"], r["finished_dropped"], r["finished_wrong_value"]))
    md += ["", "## First %d finished wrong-value rows (all rows in rows.csv)" % SAMPLE, "",
           "| repo | lang | source | translation | wrong | hints |", "|---|---|---|---|---|---|"]
    shown = [r for r in rows if r["state"] == "finished" and r["category"] == "wrong_value"][:SAMPLE]
    for r in shown:
        md.append("| %s | %s | `%s` | `%s` | %s | %s |" % (r["repo"], r["lang"], cell(r["source"]),
                                                          cell(r["translation"]), r["wrong"], r["hints"]))
    with open(os.path.join(out_dir, "qt_args.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    return summary


def new_record(repo):
    record = collections.defaultdict(int)
    record.update({"repo": repo, "status": "", "commit": "", "languages": set()})
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--data-dir", default="/data")
    parser.add_argument("--out-dir", default="/out")
    parser.add_argument("--timeout", type=int, default=1200, help="seconds per git step")
    parser.add_argument("--budget-minutes", type=float, default=110)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args(argv)
    if not shutil.which("git"):
        raise SystemExit("git is not installed")

    started = time.time()
    deadline = started + args.budget_minutes * 60
    meta = {"started": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    t, records = Tally(), []
    for repo in REPOS[:args.limit or None]:
        record = new_record(repo)
        records.append(record)
        if time.time() > deadline:
            record["status"] = "not reached (time budget)"
            continue
        root, record["commit"], record["status"] = clone(repo, args.data_dir, args.timeout)
        if record["status"] == "ok":
            scan(repo, root, record["commit"], t, record)
        shutil.rmtree(root, ignore_errors=True)
        print("%s: %s, %d .ts files, %d languages, %d finished with markers, %d dropped, %d wrong value"
              % (repo, record["status"], record["ts_files"], len(record["languages"]),
                 record["finished_with_markers"], record["finished_dropped"], record["finished_wrong_value"]),
              flush=True)
    meta["finished"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    summary = write(args.out_dir, t, meta, records)
    for state in STATES:
        s = summary[state]
        print("qt-args %s: %d translations with markers in %d repositories; dropped %d (%s), wrong value %d (%s); "
              "kinds %s" % (state, s["total"], sum(r["status"] == "ok" for r in records), s["dropped"],
                            pct(s["dropped_rate"]), s["wrong_value"], pct(s["wrong_value_rate"]),
                            json.dumps(s["wrong_kinds"], sort_keys=True)), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
