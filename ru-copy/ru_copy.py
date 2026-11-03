#!/usr/bin/env python3
# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Russian copies in Ukrainian and Belarusian Android translations (pre-registered).

For every repository in hidden-chars/repos.txt (the F-Droid source repositories of the census),
reads the Android string resources at HEAD and, for each Ukrainian and Belarusian translation,
finds the strings that are exactly the same as the app's Russian string for the same key. It then
asks how many of those copies the letter rule of cyrillic-leak (Russian-only letters ы, э, ё, ъ
in Ukrainian; и, щ, ъ in Belarusian) would have caught. See PREREG.md for the predictions and how
they are graded.

Imports the published cyrillic_leak.py 0.1.0 (same corpus, clone method, folder rules, parsing and
letter rule); the job downloads it from main and records its SHA-256. Needs git.

Made with AI agents by MV2 of Munim, Inc. Standard library only.
"""
import argparse
import collections
import concurrent.futures
import csv
import fractions
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import xml.etree.ElementTree as ET

import cyrillic_leak as cl

VERSION = "0.1.0"
BASE = cl.BASE
REPOS_URL = cl.REPOS_URL
PREREG_URL = BASE + "ru-copy/PREREG.md"
PREREG_MARK = "ru-copy PREREG v1"
LANGS = ("uk", "be")
# Letters Russian doesn't have. A copy holding one is not Russian text (it is Ukrainian or
# Belarusian sitting in the Russian file, as in MultiVNC), so it is counted apart.
NOT_RUSSIAN = "іїєґў"
# A word: two or more characters of the Cyrillic block in a row.
WORD = re.compile("[%s-%s]{2,}" % (chr(0x0400), chr(0x04FF)))

# Pre-registered thresholds (PREREG.md).
GATE_PAIRS = 50000
GATE_REPOS = 100
R1_MIN_REPOS = 20
MEAN_MIN_REPOS = 10
BE_GATE_PAIRS = 5000
BE_GATE_REPOS = 20
R4_NUM, R4_DEN = 3, 4
SAMPLE_SIZE = 40
COUNT_KEYS = ("units", "source_cyrillic", "pairs", "copies", "multi", "cand", "cand_flagged",
              "not_russian")


def clean_text(value):
    """Join surrogate pairs and replace lone halves with U+FFFD, so CSV writing can't fail."""
    if not isinstance(value, str):
        return value
    return value.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")


def words(text):
    return WORD.findall(text)


def copy_kind(lang, text, ru_text, source_text):
    """None if `text` is not the Russian string; else what kind of copy it is."""
    if ru_text is None or text.strip() != ru_text.strip():
        return None
    low = cl.norm(text)
    return {"words": len(words(text)), "multi": len(words(text)) >= 2,
            "not_russian": any(c in low for c in NOT_RUSSIAN),
            "letters": "".join(cl.foreign_letters(lang, text, source_text))}


def ru_folder(dirnames):
    """The Russian folder copies are compared with: values-ru if present, else the first."""
    ds = sorted(d for d in dirnames if cl.cyrillic_lang(d) == "ru")
    if not ds:
        return None
    return "values-ru" if "values-ru" in ds else ds[0]


def new_counts():
    out = {k: collections.Counter() for k in COUNT_KEYS}
    out["parse_failed"] = 0
    out["rows"] = []
    return out


def scan_res_dir(dirpath, dirnames):
    out = new_counts()
    targets = [(d, cl.cyrillic_lang(d)) for d in sorted(dirnames)]
    targets = [(d, lang) for d, lang in targets if lang in LANGS]
    if not targets:
        return out
    ru_dir = ru_folder(dirnames)
    cache = {}

    def load(d, fn):
        if (d, fn) not in cache:
            p = os.path.join(dirpath, d, fn)
            try:
                cache[(d, fn)] = cl.parse_values(p) if os.path.isfile(p) else None
            except (ET.ParseError, ValueError, OSError):
                cache[(d, fn)] = None
                out["parse_failed"] += 1
        return cache[(d, fn)]

    for d, lang in targets:
        for fn in sorted(os.listdir(os.path.join(dirpath, d))):
            if not fn.endswith(".xml") or not os.path.isfile(os.path.join(dirpath, "values", fn)):
                continue
            source, target = load("values", fn), load(d, fn)
            if not source or not target:
                continue
            ru = load(ru_dir, fn) if ru_dir else None
            for key, i, t, src in cl.units(source, target):
                out["units"][lang] += 1
                if cl.CYR.search(src):
                    out["source_cyrillic"][lang] += 1
                    continue
                o = cl.item(ru, key, i)
                if o is None:
                    continue
                out["pairs"][lang] += 1
                k = copy_kind(lang, t, o, src)
                if k is None:
                    continue
                out["copies"][lang] += 1
                if k["multi"]:
                    out["multi"][lang] += 1
                    if k["not_russian"]:
                        out["not_russian"][lang] += 1
                    else:
                        out["cand"][lang] += 1
                        if k["letters"]:
                            out["cand_flagged"][lang] += 1
                out["rows"].append({
                    "lang": lang, "locale_dir": d, "ru_dir": ru_dir, "file": fn, "key": key,
                    "index": i, "words": k["words"], "multi": k["multi"],
                    "not_russian": k["not_russian"], "letters": k["letters"],
                    "cand": k["multi"] and not k["not_russian"],
                    "text": t.strip()[:200], "source": src.strip()[:200]})
    return out


def scan_strings(root):
    total = new_counts()
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        if os.path.basename(dirpath) != "res" or "values" not in dirnames:
            continue
        r = scan_res_dir(dirpath, dirnames)
        rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
        for k in COUNT_KEYS:
            total[k].update(r[k])
        total["parse_failed"] += r["parse_failed"]
        total["rows"] += [dict(row, res_dir=rel) for row in r["rows"]]
    return total


def process_repo(url, tmp_root):
    d = tempfile.mkdtemp(dir=tmp_root)
    res = {"repo": url, "status": "ok"}
    t0 = time.time()
    try:
        s = os.path.join(d, "s")
        r = cl.git(["clone", "--quiet", "--depth", "1", "--filter=blob:none", "--no-checkout",
                    "--single-branch", url, s])
        if r.returncode != 0:
            res.update(status="clone-failed", error=(r.stderr.strip().splitlines() or [""])[-1][:200])
            return res
        cl.git(["-C", s, "sparse-checkout", "set", "--no-cone"] + cl.SPARSE)
        branch = cl.git(["-C", s, "symbolic-ref", "--short", "HEAD"]).stdout.strip()
        cl.git(["-C", s, "checkout", "--quiet"] + ([branch] if branch else []))
        if not cl.has_values(s):
            cl.git(["-C", s, "read-tree", "-mu", "HEAD"])
        res["head"] = cl.git(["-C", s, "rev-parse", "HEAD"]).stdout.strip()
        res.update(scan_strings(s))
        if not sum(res["units"].values()):
            res["status"] = "no-uk-be"
        return res
    except subprocess.TimeoutExpired:
        res["status"] = "timeout"
        return res
    except Exception as e:  # keep going; record what broke
        res.update(status="error", error=repr(e)[:200])
        return res
    finally:
        res["seconds"] = round(time.time() - t0, 1)
        shutil.rmtree(d, ignore_errors=True)


def recall_sum(results, lang):
    """(sum over repositories with a candidate of cand_flagged/cand, number of such repositories)."""
    shares = [fractions.Fraction(r["cand_flagged"].get(lang, 0), r["cand"][lang])
              for r in results if r.get("cand", {}).get(lang)]
    return sum(shares, fractions.Fraction(0)), len(shares)


def tables(results):
    t = {}
    for lang in LANGS:
        x = {}
        for k in COUNT_KEYS:
            x[k] = sum(r.get(k, {}).get(lang, 0) for r in results)
            x["repos_" + k] = sum(1 for r in results if r.get(k, {}).get(lang))
        s, n = recall_sum(results, lang)
        x["recall_sum"] = "%d/%d" % (s.numerator, s.denominator)
        x["recall_repos"] = n
        x["recall_mean"] = round(float(s / n), 4) if n else None
        t[lang] = x
    return t


def grade(t, sums):
    """Pre-registered verdicts R1-R3 (PREREG.md); R4 is graded by hand from sample.csv.
    `sums` maps lang -> (Fraction sum of per-repository shares, number of repositories)."""
    uk, be = t["uk"], t["be"]
    if not (uk["pairs"] >= GATE_PAIRS and uk["repos_pairs"] >= GATE_REPOS):
        return {p: "NOT TESTABLE (gate)" for p in ("R1", "R2", "R3", "R4")}
    v = {"R1": "HELD" if uk["repos_cand"] >= R1_MIN_REPOS else "FAILED"}
    s_uk, n_uk = sums["uk"]
    if n_uk < MEAN_MIN_REPOS:
        v["R2"] = "NOT TESTABLE"
    else:
        v["R2"] = "HELD" if 2 * s_uk < n_uk else "FAILED"
    s_be, n_be = sums["be"]
    if (be["pairs"] < BE_GATE_PAIRS or be["repos_pairs"] < BE_GATE_REPOS
            or n_be < MEAN_MIN_REPOS or n_uk < MEAN_MIN_REPOS):
        v["R3"] = "NOT TESTABLE"
    else:
        v["R3"] = "HELD" if s_be * n_uk > s_uk * n_be else "FAILED"
    v["R4"] = "PENDING (hand check of sample.csv)"
    return v


def grade_r4(labels):
    """R4 from hand labels ('russian', 'both', 'ukrainian', 'other'), one per sampled row."""
    if len(labels) < 4:
        return "NOT TESTABLE"
    m = sum(1 for x in labels if x == "russian")
    return "HELD" if m * R4_DEN >= len(labels) * R4_NUM else "FAILED"


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def draw_sample(rows, size=SAMPLE_SIZE):
    """One Ukrainian candidate per repository (lowest hash of its location), repositories taken in
    order of the hash of their URL, up to `size`. Fixed in PREREG.md."""
    best = {}
    for x in rows:
        if x["lang"] != "uk" or not x["cand"]:
            continue
        h = sha("%s|%s|%s|%s|%s|%s" % (x["repo"], x["res_dir"], x["locale_dir"], x["file"],
                                        x["key"], x["index"]))
        if x["repo"] not in best or h < best[x["repo"]][0]:
            best[x["repo"]] = (h, x)
    order = sorted(best, key=sha)
    return [best[r][1] for r in order[:size]]


def control():
    """The copy finder must behave on known cases (positive control)."""
    cases = [
        ("uk", "Выберите файл", "Выберите файл", "Choose a file",
         {"words": 2, "multi": True, "not_russian": False, "letters": "ы"}),
        ("uk", "Настройки сохранены", "Настройки сохранены", "Settings saved",
         {"words": 2, "multi": True, "not_russian": False, "letters": ""}),
        ("uk", "Налаштування", "Настройки", "Settings", None),
        ("uk", "Ключ імпорту", "Ключ імпорту", "Import key",
         {"words": 2, "multi": True, "not_russian": True, "letters": ""}),
        ("uk", "Сервер", "Сервер", "Server",
         {"words": 1, "multi": False, "not_russian": False, "letters": ""}),
        ("uk", " Выход ", "Выход", "Exit",
         {"words": 1, "multi": False, "not_russian": False, "letters": "ы"}),
        ("be", "Настройки сохранены", "Настройки сохранены", "Settings saved",
         {"words": 2, "multi": True, "not_russian": False, "letters": "и"}),
        ("uk", "Файл SSH", "Файл SSH", "SSH file",
         {"words": 1, "multi": False, "not_russian": False, "letters": ""}),
        ("uk", "Текст", None, "Text", None),
    ]
    return all(copy_kind(lang, t, ru, src) == want for lang, t, ru, src, want in cases)


def wait_for_prereg(minutes):
    end = time.time() + minutes * 60
    while True:
        try:
            with urllib.request.urlopen(PREREG_URL, timeout=60) as r:
                text = r.read().decode("utf-8")
            if PREREG_MARK in text:
                return hashlib.sha256(text.encode("utf-8")).hexdigest()
        except OSError:
            pass
        if time.time() > end:
            return None
        time.sleep(60)


def file_sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


ROW_COLS = ["repo", "head", "lang", "res_dir", "locale_dir", "ru_dir", "file", "key", "index",
            "words", "multi", "not_russian", "cand", "letters", "text", "source"]
SAMPLE_COLS = ["n", "repo", "head", "res_dir", "locale_dir", "file", "key", "index", "letters",
               "text", "source"]


def write_row(writer, row):
    writer.writerow({k: clean_text(v) for k, v in row.items()})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--repos", help="local repos.txt instead of downloading")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--budget-minutes", type=float, default=200)
    ap.add_argument("--prereg-wait-minutes", type=float, default=45)
    ap.add_argument("--skip-prereg-check", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    started = time.time()
    if cl.VERSION != "0.1.0" or not cl.control() or not control():
        print("positive control failed; stopping", file=sys.stderr)
        return 6
    prereg_sha = None
    if not a.skip_prereg_check:
        prereg_sha = wait_for_prereg(a.prereg_wait_minutes)
        if not prereg_sha:
            print("PREREG.md not public; stopping before reading any repository", file=sys.stderr)
            return 4
    if a.repos:
        with open(a.repos, "rb") as f:
            raw = f.read()
    else:
        with urllib.request.urlopen(REPOS_URL, timeout=120) as resp:
            raw = resp.read()
    repos = [u.strip() for u in raw.decode("utf-8").splitlines() if u.strip()]
    if a.limit:
        repos = repos[:a.limit]
    print("ru_copy %s: %d repositories" % (VERSION, len(repos)), flush=True)

    tmp_root = tempfile.mkdtemp(prefix="rucopy-")
    selftest = {}
    for u in ("https://github.com/TeamNewPipe/NewPipe", "https://gitlab.com/fdroid/fdroidclient"):
        r = process_repo(u, tmp_root)
        selftest[u] = {"status": r["status"], "pairs": dict(r.get("pairs", {})),
                       "copies": dict(r.get("copies", {}))}
    print("selftest", json.dumps(selftest), flush=True)
    if not any(v["pairs"].get("uk") for v in selftest.values()):
        print("selftest found no Ukrainian-Russian pairs; clone method broken, stopping",
              file=sys.stderr)
        return 3

    deadline = time.time() + a.budget_minutes * 60
    results, skipped, all_rows = [], [], []
    jl = open(os.path.join(a.out_dir, "repos.jsonl"), "w", encoding="utf-8")
    lf = open(os.path.join(a.out_dir, "copies.csv"), "w", encoding="utf-8", newline="")
    lw = csv.DictWriter(lf, fieldnames=ROW_COLS)
    lw.writeheader()

    def work(u):
        if time.time() > deadline:
            return {"repo": u, "status": "not-started"}
        return process_repo(u, tmp_root)

    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for n, r in enumerate(ex.map(work, repos), 1):
            if r["status"] == "not-started":
                skipped.append(r["repo"])
                continue
            results.append(r)
            rec = {"repo": r["repo"], "status": r["status"], "head": r.get("head"),
                   "error": clean_text(r.get("error")), "seconds": r.get("seconds"),
                   "parse_failed": r.get("parse_failed", 0)}
            for k in COUNT_KEYS:
                rec[k] = dict(r.get(k, {}))
            jl.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
            for row in r.get("rows", []):
                full = dict(row, repo=r["repo"], head=r.get("head", ""))
                write_row(lw, full)
                all_rows.append(full)
            if n % 100 == 0:
                jl.flush()
                lf.flush()
                print("%d/%d done, %.0f min" % (n, len(repos), (time.time() - started) / 60), flush=True)
    jl.close()
    lf.close()
    shutil.rmtree(tmp_root, ignore_errors=True)

    ok = [r for r in results if r.get("status") in ("ok", "no-uk-be")]
    t = tables(ok)
    sums = {lang: recall_sum(ok, lang) for lang in LANGS}
    ok_repos = {r["repo"] for r in ok}
    sample = draw_sample([x for x in all_rows if x["repo"] in ok_repos])
    with open(os.path.join(a.out_dir, "sample.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SAMPLE_COLS, extrasaction="ignore")
        w.writeheader()
        for i, x in enumerate(sample, 1):
            write_row(w, dict(x, n=i))
    summary = {
        "verdicts": grade(t, sums), "tables": t,
        "version": VERSION, "cyrillic_leak_version": cl.VERSION,
        "cyrillic_leak_sha256": file_sha(cl.__file__),
        "repos_url": REPOS_URL, "repos_sha256": hashlib.sha256(raw).hexdigest(),
        "prereg_sha256": prereg_sha, "sample_size": len(sample),
        "repos_listed": len(repos), "repos_not_started": len(skipped),
        "status_counts": dict(collections.Counter(r["status"] for r in results)),
        "parse_failed_files": sum(r.get("parse_failed", 0) for r in results),
        "positive_control": True, "selftest": selftest,
        "minutes": round((time.time() - started) / 60, 1),
    }
    with open(os.path.join(a.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps(summary["verdicts"]), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
