#!/usr/bin/env python3
"""qt-shape: does genitive order decide which "X of Y" strings translators
reorder? An out-of-sample test on Qt .ts translation files.

shape 0.1.0 found, in Android apps on F-Droid, that translators into verb-final
(SOV) languages reorder "%1$d of %2$d" strings about half the time. Read by
hand afterwards, the per-language table suggested that the "of" reorders follow
the language's genitive order (WALS 86A) rather than its clause order: Persian
(SOV, noun before genitive) almost never reordered them, Chinese (SVO, genitive
before noun) often did. That reading was made after the fact, so this tests it
on data it was not drawn from: the Qt Linguist .ts files of other open-source
projects (REPOS), whose %1 and %2 placeholders translators may move freely.

For each English source with exactly the arguments %1 and %2 (each once), the
text between them gives the same shapes as shape 0.1.0 (its shape() is reused,
with HTML tags removed first). Plural (numerus) messages, unfinished, obsolete
and vanished translations, and copies of Qt's own translation files are left
out.

The predictions in PREDICTIONS.md were published before this ran. The job
refuses to run until they are on main.

  python qt_shape.py --data-dir /data --out-dir /out

Writes qt_shape.md, qt_shape.json, by_language.csv, top_sources.csv and
repos.csv.

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
import urllib.request
import xml.etree.ElementTree as ET

import placeholder_order as po
import shape as sh

__version__ = "0.1.0"

REPO_RAW = "https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/main/"
PREDICTIONS_URL = REPO_RAW + "placeholder-order/qt-shape/PREDICTIONS.md"
PREDICTIONS_MARK = "qt-shape 0.1.0 predictions"
WALS_CSV = "languages.csv"  # np-order 0.1.0's per-language WALS table, fetched by fetch_code.py

# Open-source Qt projects that keep their .ts files in the repository, one
# per code base (no forks). Each is read at its default branch.
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

NON_SOV = ("SVO", "VSO", "no dominant order")
CHINESE = {"zh", "yue", "lzh"}
GEN_SHORT = {"Genitive-Noun": "GenN", "Noun-Genitive": "NGen"}
MIN_VALID = 100     # translations behind a pooled rate
MIN_LANG_OF = 30    # Persian "of" translations behind Q5
MIN_LANG = 100      # translations for a language row in the report
QT_ARG_RE = re.compile(r"%L?(\d+)")
TAG_RE = re.compile(r"<[^>]*>")
# Copies of Qt's own translations (qt_fa.ts, qtbase_ja.ts) that projects ship.
QT_OWN_RE = re.compile(r"^(?:qt|qtbase|qtdeclarative|qtmultimedia|qtscript|qtxmlpatterns|qtconnectivity|"
                       r"qtlocation|qtquickcontrols2?|qtserialport|qtwebengine|qtwebsockets|qt_help|"
                       r"assistant|designer|linguist|qtconfig)_[A-Za-z]{2,3}(?:[_@-][^.]*)?\.ts$")
# Shape checks: if any fails, no prediction is scored.
KNOWN = [("Page %1 of %2", "of"), ("%1: %2", "no_words"), ("Move %1 to %2", "adposition"),
         ("<b>%1</b> of <b>%2</b>", "of"), ("%1 and %2", "and_or"), ("%1 sent you %2", "other")]


def lang_code(code):
    """zh_CN -> zh, sr@latin -> sr, pt-BR -> pt, iw -> he."""
    lang = re.split(r"[_@.\-]", (code or "").strip())[0].lower()
    return po.OLD_CODES.get(lang, lang)


def file_lang(name):
    """The language in a .ts file name (keepassxc_zh_CN.ts -> zh), or ""."""
    stem = name[:-3] if name.endswith(".ts") else name
    for part in stem.split("_")[1:]:
        if re.fullmatch(r"[a-z]{2,3}(?:@\w+)?", part):
            return lang_code(part)
    return ""


def parse_ts(path):
    """(language, source language, [(source, translation)]) for a Qt .ts
    file, or None if the file is not one (TypeScript, broken XML)."""
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
    pairs = []
    for msg in root.iter("message"):
        if msg.get("numerus") == "yes":
            continue
        s, t = msg.find("source"), msg.find("translation")
        if s is None or t is None or t.get("type") in ("unfinished", "obsolete", "vanished"):
            continue
        source, target = "".join(s.itertext()), "".join(t.itertext())
        if source.strip() and target.strip():
            pairs.append((source, target))
    return lang, lang_code(root.get("sourcelanguage") or "en"), pairs


def qt_args(text):
    """[(number, (start, end))] for each %N or %LN in text, in text order."""
    return [(int(m.group(1)), m.span()) for m in QT_ARG_RE.finditer(text)]


def classify(source, target):
    """(shape, reordered) for a translation of a source whose arguments are
    exactly %1 and %2 (each once), or None if either side doesn't have them."""
    src = qt_args(source)
    if sorted(n for n, _ in src) != [1, 2]:
        return None
    tgt = qt_args(target)
    if sorted(n for n, _ in tgt) != [1, 2]:
        return None
    gap = TAG_RE.sub(" ", source[src[0][1][1]:src[1][1][0]])
    return sh.shape(gap), [n for n, _ in tgt] != [n for n, _ in src]


def load_genitive(path):
    """{lang: "Genitive-Noun" | "Noun-Genitive"} from np-order's languages.csv."""
    out = {}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("86A") in GEN_SHORT:
                out[row["lang"]] = row["86A"]
    return out


def scopes(lang, genitive):
    """The scopes a translation into lang counts in."""
    group = po.WORD_ORDER.get(lang, "unassigned")
    out = ["all", "group:" + group, "lang:" + lang]
    gen = GEN_SHORT.get(genitive.get(lang, ""))
    clause = "SOV" if group == "SOV" else "nonSOV" if group in NON_SOV else None
    if gen and clause:
        out.append("pool:%s:%s" % (clause, gen))
        if lang not in CHINESE:
            out.append("pool:%s:%s:nozh" % (clause, gen))
    return out


class Tally:
    """[valid, reordered] by (scope, shape), per repository and per unique
    (language, source, translation)."""

    def __init__(self):
        self.counts = collections.defaultdict(lambda: [0, 0])
        self.repo_counts = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
        self.unique = collections.defaultdict(dict)
        self.sources = collections.defaultdict(lambda: {"translations": 0, "reordered": 0, "repos": set()})

    def add(self, repo, lang, shape, reordered, source, target, genitive):
        for scope in scopes(lang, genitive):
            c = self.counts[(scope, shape)]
            c[0] += 1
            c[1] += bool(reordered)
            r = self.repo_counts[(scope, shape)][repo]
            r[0] += 1
            r[1] += bool(reordered)
            self.unique[(scope, shape)][(lang, source, target)] = bool(reordered)
        group = po.WORD_ORDER.get(lang, "unassigned")
        for where in ([group] if group == "SOV" else []) + ([lang] if lang in ("fa", "zh") else []):
            s = self.sources[(where, source, shape)]
            s["translations"] += 1
            s["reordered"] += bool(reordered)
            s["repos"].add(repo)

    def row(self, scope, shapes):
        valid = moved = 0
        per_repo = collections.defaultdict(lambda: [0, 0])
        unique = {}
        for s in shapes:
            v, m = self.counts.get((scope, s), (0, 0))
            valid += v
            moved += m
            for repo, (rv, rm) in self.repo_counts.get((scope, s), {}).items():
                per_repo[repo][0] += rv
                per_repo[repo][1] += rm
            unique.update(self.unique.get((scope, s), {}))
        repos = [(m, v) for v, m in per_repo.values() if v]
        low, high = po.cluster_ci(repos)
        return {"valid": valid, "reordered": moved, "rate": moved / valid if valid else None,
                "repos": len(repos), "ci_low": low, "ci_high": high,
                "repo_mean_rate": sum(m / v for m, v in repos) / len(repos) if repos else None,
                "unique_valid": len(unique),
                "unique_rate": sum(unique.values()) / len(unique) if unique else None}


def rate(t, scope, shape, minimum):
    r = t.row(scope, [shape])
    return r["rate"] if r["valid"] >= minimum else None


def predictions(t, minimum=MIN_VALID, lang_minimum=MIN_LANG_OF):
    """[(id, text, held True/False/None, detail)]."""
    out = []
    a, b = rate(t, "group:SOV", "of", minimum), rate(t, "group:SOV", "no_words", minimum)
    out.append(("Q1", "in SOV languages, of sources are reordered at least 3x as often as no_words sources",
                None if a is None or b is None else a >= 3 * b, {"of": a, "no_words": b}))
    out.append(("Q2", "in SOV languages, no_words sources are reordered less than 3% of the time",
                None if b is None else b < 0.03, {"no_words": b}))
    g, n = rate(t, "pool:nonSOV:GenN", "of", minimum), rate(t, "pool:nonSOV:NGen", "of", minimum)
    out.append(("Q3", "in languages that are not SOV, of sources are reordered at least 3x as often in "
                      "Genitive-Noun languages as in Noun-Genitive languages",
                None if g is None or n is None else g > 0 and g >= 3 * n, {"GenN": g, "NGen": n}))
    g2, n2 = rate(t, "pool:nonSOV:GenN:nozh", "of", minimum), rate(t, "pool:nonSOV:NGen:nozh", "of", minimum)
    out.append(("Q4", "Q3 holds with Chinese left out",
                None if g2 is None or n2 is None else g2 > 0 and g2 >= 3 * n2, {"GenN": g2, "NGen": n2}))
    fa, sg = rate(t, "lang:fa", "of", lang_minimum), rate(t, "pool:SOV:GenN", "of", minimum)
    out.append(("Q5", "Persian reorders of sources less than 5% of the time, while SOV Genitive-Noun "
                      "languages reorder them more than 25% of the time",
                None if fa is None or sg is None else fa < 0.05 and sg > 0.25, {"fa": fa, "SOV GenN": sg}))
    out.append(("Q6", "SOV Genitive-Noun languages reorder of sources more often than Genitive-Noun "
                      "languages that are not SOV",
                None if sg is None or g is None else sg > g, {"SOV GenN": sg, "non-SOV GenN": g}))
    return out


def verdict(held):
    return "NOT TESTABLE" if held is None else "HELD" if held else "FAILED"


def pct(x):
    return "n/a" if x is None else "%.1f%%" % (100 * x)


def fetch(url, tries=4):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "mv2-qt-shape/" + __version__})
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read().decode("utf-8-sig")
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(5 * (attempt + 1))


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
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in sorted(files):
            if name.endswith(".ts"):
                yield os.path.join(dirpath, name)


def scan(repo, root, t, genitive, record):
    for path in ts_files(root):
        name = os.path.basename(path)
        if QT_OWN_RE.match(name):
            record["qt_own_skipped"] += 1
            continue
        parsed = parse_ts(path)
        if parsed is None:
            record["not_qt_ts"] += 1
            continue
        lang, source_lang, pairs = parsed
        if not lang or lang == "en" or source_lang != "en":
            record["not_counted_language"] += 1
            continue
        record["ts_files"] += 1
        record["languages"].add(lang)
        record["translations"] += len(pairs)
        for source, target in pairs:
            got = classify(source, target)
            if got is None:
                continue
            record["two_argument_valid"] += 1
            t.add(repo, lang, got[0], got[1], source, target, genitive)


def write(out_dir, t, meta, checks_ok, checks, records, genitive):
    os.makedirs(out_dir, exist_ok=True)
    preds = predictions(t) if checks_ok else []
    pools = ["all", "group:SOV", "group:SVO", "group:VSO", "group:no dominant order", "group:unassigned",
             "pool:SOV:GenN", "pool:SOV:NGen", "pool:nonSOV:GenN", "pool:nonSOV:NGen",
             "pool:nonSOV:GenN:nozh", "pool:nonSOV:NGen:nozh"]
    table = {p: {s: t.row(p, [s]) for s in sh.SHAPES} for p in pools}
    for p in pools:
        table[p]["total"] = t.row(p, sh.SHAPES)
    langs = sorted({s[5:] for s, _ in t.counts if s.startswith("lang:")})
    lang_rows = []
    for lang in langs:
        total = t.row("lang:" + lang, sh.SHAPES)
        line = {"lang": lang, "group": po.WORD_ORDER.get(lang, "unassigned"), "wals_86A": genitive.get(lang, ""),
                "valid": total["valid"], "reordered": total["reordered"], "rate": total["rate"]}
        for s in sh.SHAPES:
            v, m = t.counts.get(("lang:" + lang, s), (0, 0))
            line[s + "_valid"], line[s + "_reordered"] = v, m
        lang_rows.append(line)
    with open(os.path.join(out_dir, "by_language.csv"), "w", newline="", encoding="utf-8") as f:
        fields = ["lang", "group", "wals_86A", "valid", "reordered", "rate"] + [
            s + x for s in sh.SHAPES for x in ("_valid", "_reordered")]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(lang_rows)
    top = sorted(t.sources.items(), key=lambda kv: (kv[0][0], -kv[1]["reordered"], -kv[1]["translations"],
                                                     kv[0][1]))
    with open(os.path.join(out_dir, "top_sources.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["where", "source", "shape", "translations", "reordered", "repos"])
        shown = collections.Counter()
        for (where, source, s), v in top:
            if shown[where] < 300:
                shown[where] += 1
                w.writerow([where, source, s, v["translations"], v["reordered"], len(v["repos"])])
    with open(os.path.join(out_dir, "repos.csv"), "w", newline="", encoding="utf-8") as f:
        fields = ["repo", "status", "commit", "ts_files", "languages", "translations", "two_argument_valid",
                  "qt_own_skipped", "not_qt_ts", "not_counted_language"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in records:
            w.writerow(dict(r, languages=len(r["languages"])))
    result = dict(meta, version=__version__, shape_checks=checks, shape_checks_ok=checks_ok, table=table,
                  repos=[dict(r, languages=sorted(r["languages"])) for r in records],
                  predictions=[{"id": i, "text": x, "result": verdict(h), "detail": d} for i, x, h, d in preds])
    with open(os.path.join(out_dir, "qt_shape.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1, ensure_ascii=False)

    ok = sum(r["status"] == "ok" for r in records)
    md = ["# qt-shape %s: does genitive order decide which \"X of Y\" strings translators reorder?" % __version__,
          "", "MV2 of Munim, Inc., made with AI agents. Qt .ts files of %d of %d repositories, read %s."
          % (ok, len(records), meta.get("finished", "")), "",
          "- Shape checks: %s" % ("all passed" if checks_ok else "FAILED, so no prediction is scored: "
                                  + "; ".join("%r want %s got %s" % (c["text"], c["want"], c["got"])
                                              for c in checks if c["want"] != c["got"])),
          "", "## Predictions", ""]
    for i, x, h, d in preds:
        md.append("- %s %s: %s. %s" % (i, verdict(h), x, ", ".join("%s %s" % (k, pct(v)) for k, v in d.items())))
    md += ["", "## Reorder rate by shape (sources with exactly %1 and %2)", "",
           "| scope | shape | valid | reordered | rate | 95% CI (repos) | repo mean | unique-pair rate | repos |",
           "|---|---|---:|---:|---:|---|---:|---:|---:|"]
    for p, shapes in table.items():
        for s, r in shapes.items():
            md.append("| %s | %s | %d | %d | %s | %s-%s | %s | %s | %d |" % (
                p.replace("group:", ""), s, r["valid"], r["reordered"], pct(r["rate"]), pct(r["ci_low"]),
                pct(r["ci_high"]), pct(r["repo_mean_rate"]), pct(r["unique_rate"]), r["repos"]))
    md += ["", "## Languages (%d+ translations): reorder rate by shape (valid in brackets)" % MIN_LANG, "",
           "| lang | group | WALS 86A | all | " + " | ".join(sh.SHAPES) + " |",
           "|---|---|---|---|" + "---|" * len(sh.SHAPES)]
    for line in sorted((x for x in lang_rows if x["valid"] >= MIN_LANG), key=lambda x: -(x["rate"] or 0)):
        cells = []
        for s in sh.SHAPES:
            v = line[s + "_valid"]
            cells.append("%s (%d)" % (pct(line[s + "_reordered"] / v) if v else "n/a", v))
        md.append("| %s | %s | %s | %s (%d) | %s |" % (line["lang"], line["group"], line["wals_86A"] or "-",
                                                       pct(line["rate"]), line["valid"], " | ".join(cells)))
    for where in ("SOV", "fa", "zh"):
        md += ["", "## Most often reordered sources: %s" % where, "",
               "| source | shape | translations | reordered | repos |", "|---|---|---:|---:|---:|"]
        rows = [(k, v) for k, v in top if k[0] == where][:25]
        for (_, source, s), v in rows:
            md.append("| `%s` | %s | %d | %d | %d |" % (source.replace("|", "\\|").replace("`", "'")
                                                        .replace("\n", " ")[:120], s, v["translations"],
                                                        v["reordered"], len(v["repos"])))
    md += ["", "## Repositories", "", "| repo | status | commit | .ts files | languages | two-argument valid |",
           "|---|---|---|---:|---:|---:|"]
    for r in records:
        md.append("| %s | %s | %s | %d | %d | %d |" % (r["repo"], r["status"].replace("|", "/")[:80],
                                                       r["commit"][:10], r["ts_files"], len(r["languages"]),
                                                       r["two_argument_valid"]))
    with open(os.path.join(out_dir, "qt_shape.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    return preds


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--data-dir", default="/data")
    parser.add_argument("--out-dir", default="/out")
    parser.add_argument("--timeout", type=int, default=1200, help="seconds per git step")
    parser.add_argument("--budget-minutes", type=float, default=110)
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
    if not shutil.which("git"):
        raise SystemExit("git is not installed")

    checks = [{"text": x, "want": want, "got": classify(x, x)[0]} for x, want in KNOWN]
    checks_ok = all(c["want"] == c["got"] for c in checks)
    genitive = load_genitive(os.path.join(os.path.dirname(os.path.abspath(__file__)), WALS_CSV))
    started = time.time()
    deadline = started + args.budget_minutes * 60
    meta = {"started": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "shape_version": sh.__version__, "placeholder_order_version": po.__version__,
            "wals_languages": len(genitive)}
    t, records = Tally(), []
    for repo in REPOS[:args.limit or None]:
        record = {"repo": repo, "status": "", "commit": "", "ts_files": 0, "languages": set(),
                  "translations": 0, "two_argument_valid": 0, "qt_own_skipped": 0, "not_qt_ts": 0,
                  "not_counted_language": 0}
        records.append(record)
        if time.time() > deadline:
            record["status"] = "not reached (time budget)"
            continue
        root, record["commit"], record["status"] = clone(repo, args.data_dir, args.timeout)
        if record["status"] == "ok":
            scan(repo, root, t, genitive, record)
        shutil.rmtree(root, ignore_errors=True)
        print("%s: %s, %d .ts files, %d languages, %d two-argument translations"
              % (repo, record["status"], record["ts_files"], len(record["languages"]),
                 record["two_argument_valid"]), flush=True)
    meta["finished"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    preds = write(args.out_dir, t, meta, checks_ok, checks, records, genitive)
    total = t.row("all", sh.SHAPES)
    print("qt-shape: %d translations of two-argument sources in %d repositories; shape checks %s"
          % (total["valid"], sum(r["status"] == "ok" for r in records), "ok" if checks_ok else "FAILED"),
          flush=True)
    for i, x, h, _ in preds:
        print("%s %s: %s" % (i, verdict(h), x), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
