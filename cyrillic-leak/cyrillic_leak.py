#!/usr/bin/env python3
# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Letters from another alphabet in Cyrillic Android translations (pre-registered).

For every repository in hidden-chars/repos.txt (the F-Droid source repositories of the census),
reads the Android string resources at HEAD and, for each Ukrainian, Belarusian, Russian,
Bulgarian, Serbian (Cyrillic) and Macedonian translation, counts the translated strings that
contain a letter the language's alphabet doesn't have (Russian ы, э, ё, ъ in Ukrainian; и, щ, ъ
in Belarusian; Ukrainian і, ї, є, ґ in Russian; ...). Each such string is compared with the same
string in the app's other Cyrillic translations, to see whether it is a copy of, say, the Russian
one. See PREREG.md for the predictions and how they are graded.

Same corpus, clone method and locale rules as zwsp_langs.py 0.1.0 and lint_ci.py 0.1.0, whose
helpers are copied here so the script stands alone. Needs git.

Made with AI agents by MV2 of Munim, Inc. Standard library only.
"""
import argparse
import collections
import concurrent.futures
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET

VERSION = "0.1.0"
BASE = "https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/main/"
REPOS_URL = BASE + "hidden-chars/repos.txt"
PREREG_URL = BASE + "cyrillic-leak/PREREG.md"
PREREG_MARK = "cyrillic-leak PREREG v1"
SPARSE = ["**/res/values*/*.xml"]

# Lower-case letters each language's alphabet doesn't have (PREREG.md, "Foreign letters").
FOREIGN = {
    "uk": "ёыэъ",
    "be": "ищъєї",
    "ru": "іїєґў",
    "bg": "ыэёіїєґў",
    "sr": "йщъыьэюяёіїєґў",
    "mk": "йщъыьэюяёіїєґўђћ",
}
# Letters of the language that Russian doesn't have (exploratory: a flagged string that also has
# one of these was at least partly written in the language).
NATIVE = {"uk": "іїєґ", "be": "іў", "ru": "", "bg": "", "sr": "ђјљњћџ", "mk": "ѓќѕјљњџ"}
LANGS = tuple(FOREIGN)
CYR = re.compile("[%s-%s]" % (chr(0x0400), chr(0x04FF)))  # the Cyrillic block

# Pre-registered thresholds (PREREG.md).
GATE_UNITS = 10000
GATE_REPOS = 30
P1_MIN_REPOS = 20
P2_MIN_UNITS = 30

# From zwsp_langs.py 0.1.0 (unchanged).
_U_ESC = re.compile(r"(?<!\\)\\u([0-9A-Fa-f]{4})")
_LOCALE_DIR = re.compile(
    r"^values-(?:([a-z]{2,3})(?:-r([A-Z]{2}|[0-9]{3}))?|b\+([a-zA-Z]{2,3})(?:\+[A-Za-z0-9]+)*)$")
_NOT_LOCALES = {"car"}
_PSEUDO = {("en", "XA"), ("ar", "XB")}


def decode_android(text):
    return _U_ESC.sub(lambda m: chr(int(m.group(1), 16)), text)


def locale_of(dirname):
    m = _LOCALE_DIR.match(dirname)
    if not m:
        return None
    if m.group(3):
        return m.group(3).lower()
    lang, region = m.group(1), m.group(2)
    if lang in _NOT_LOCALES or (lang, region) in _PSEUDO:
        return None
    return lang


def cyrillic_lang(dirname):
    """The language of a values-* folder if it is one of LANGS written in Cyrillic, else None."""
    lang = locale_of(dirname)
    if lang not in FOREIGN or "Latn" in dirname:
        return None
    return lang


def parse_values(path):
    return parse_root(ET.parse(path).getroot())


def parse_values_text(text):
    return parse_root(ET.fromstring(text))


def parse_root(root):
    out = {}
    if root.tag != "resources":
        return out
    for el in root:
        name = el.get("name")
        if not name or not isinstance(el.tag, str):
            continue
        if el.tag == "string":
            key, texts = "string:" + name, ["".join(el.itertext())]
        elif el.tag == "plurals":
            key, texts = "plurals:" + name, ["".join(i.itertext()) for i in el if i.tag == "item"]
        elif el.tag in ("string-array", "array"):
            key, texts = "array:" + name, ["".join(i.itertext()) for i in el if i.tag == "item"]
        else:
            continue
        if el.get("translatable") == "false":
            out[key] = None
        else:
            out[key] = [decode_android(t) for t in texts]
    return out


def norm(text):
    return unicodedata.normalize("NFC", text).lower()


def foreign_letters(lang, text, source_text):
    """Letters of `text` that `lang`'s alphabet lacks and the source string doesn't have."""
    low, src = norm(text), norm(source_text)
    return sorted({c for c in FOREIGN[lang] if c in low and c not in src})


def has_native(lang, text):
    low = norm(text)
    return any(c in low for c in NATIVE[lang])


def units(source, target):
    """(key, index, text, source text) of each translated item that has a Cyrillic letter."""
    for key in sorted(target, key=str):
        tlist, slist = target[key], source.get(key)
        if not tlist or not slist:
            continue
        src = " ".join(slist)
        for i, t in enumerate(tlist):
            if t.strip() and CYR.search(t):
                yield key, i, t, src


def item(values, key, i):
    """Item i of `key` in a parsed file, if it is a Cyrillic translation; else None."""
    if not values:
        return None
    texts = values.get(key)
    if not texts or i >= len(texts) or not CYR.search(texts[i]):
        return None
    return texts[i]


def scan_res_dir(dirpath, dirnames):
    """Counts and flagged rows for one res/ folder whose subfolders are `dirnames`."""
    out = {"units": collections.Counter(), "flagged": collections.Counter(),
           "source_cyrillic": collections.Counter(), "parse_failed": 0, "rows": []}
    by_lang = {}
    for d in sorted(dirnames):
        lang = cyrillic_lang(d)
        if lang:
            by_lang.setdefault(lang, []).append(d)
    if not by_lang:
        return out
    # The folder other translations are compared with: values-<lang> if present.
    primary = {lang: ("values-" + lang if "values-" + lang in ds else ds[0])
               for lang, ds in by_lang.items()}
    cache = {}

    def load(d, fn):
        if (d, fn) not in cache:
            p = os.path.join(dirpath, d, fn)
            try:
                cache[(d, fn)] = parse_values(p) if os.path.isfile(p) else None
            except (ET.ParseError, ValueError, OSError):
                cache[(d, fn)] = None
                out["parse_failed"] += 1
        return cache[(d, fn)]

    for lang in sorted(by_lang):
        for d in by_lang[lang]:
            for fn in sorted(os.listdir(os.path.join(dirpath, d))):
                if not fn.endswith(".xml") or not os.path.isfile(os.path.join(dirpath, "values", fn)):
                    continue
                source, target = load("values", fn), load(d, fn)
                if not source or not target:
                    continue
                for key, i, t, src in units(source, target):
                    out["units"][lang] += 1
                    if CYR.search(src):
                        out["source_cyrillic"][lang] += 1
                    letters = foreign_letters(lang, t, src)
                    if not letters:
                        continue
                    out["flagged"][lang] += 1
                    same_as, ru_available = [], False
                    for other in sorted(primary):
                        if other == lang:
                            continue
                        o = item(load(primary[other], fn), key, i)
                        if other == "ru" and o is not None:
                            ru_available = True
                        if o is not None and o.strip() == t.strip():
                            same_as.append(other)
                    out["rows"].append({
                        "lang": lang, "locale_dir": d, "file": fn, "key": key, "index": i,
                        "letters": "".join(letters), "ru_available": ru_available,
                        "ru_identical": "ru" in same_as, "same_as": " ".join(same_as),
                        "native": has_native(lang, t), "text": t.strip()[:200]})
    return out


def scan_strings(root):
    total = {"units": collections.Counter(), "flagged": collections.Counter(),
             "source_cyrillic": collections.Counter(), "parse_failed": 0, "rows": []}
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        if os.path.basename(dirpath) != "res" or "values" not in dirnames:
            continue
        r = scan_res_dir(dirpath, dirnames)
        rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
        for k in ("units", "flagged", "source_cyrillic"):
            total[k].update(r[k])
        total["parse_failed"] += r["parse_failed"]
        total["rows"] += [dict(row, res_dir=rel) for row in r["rows"]]
    return total


def git(args, timeout=240):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_LFS_SKIP_SMUDGE="1", GIT_ASKPASS="true")
    return subprocess.run(["git"] + args, env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def has_values(root):
    for dirpath, dirnames, _ in os.walk(root):
        if os.path.basename(dirpath) == "res" and "values" in dirnames:
            return True
        dirnames[:] = [d for d in dirnames if d != ".git"]
    return False


def process_repo(url, tmp_root):
    d = tempfile.mkdtemp(dir=tmp_root)
    res = {"repo": url, "status": "ok"}
    t0 = time.time()
    try:
        s = os.path.join(d, "s")
        r = git(["clone", "--quiet", "--depth", "1", "--filter=blob:none", "--no-checkout",
                 "--single-branch", url, s])
        if r.returncode != 0:
            res.update(status="clone-failed", error=(r.stderr.strip().splitlines() or [""])[-1][:200])
            return res
        git(["-C", s, "sparse-checkout", "set", "--no-cone"] + SPARSE)
        branch = git(["-C", s, "symbolic-ref", "--short", "HEAD"]).stdout.strip()
        git(["-C", s, "checkout", "--quiet"] + ([branch] if branch else []))
        if not has_values(s):
            git(["-C", s, "read-tree", "-mu", "HEAD"])
        res["head"] = git(["-C", s, "rev-parse", "HEAD"]).stdout.strip()
        res.update(scan_strings(s))
        if not sum(res["units"].values()):
            res["status"] = "no-cyrillic"
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


def per_lang(results):
    """Per-language totals from the repositories that were read."""
    table = {}
    for lang in LANGS:
        with_units = [r for r in results if r.get("units", {}).get(lang)]
        rows = [x for r in results for x in r.get("rows", []) if x["lang"] == lang]
        table[lang] = {
            "repos": len(with_units),
            "units": sum(r["units"][lang] for r in with_units),
            "flagged": sum(r["flagged"].get(lang, 0) for r in with_units),
            "repos_flagged": sum(1 for r in with_units if r["flagged"].get(lang)),
            "source_cyrillic_units": sum(r["source_cyrillic"].get(lang, 0) for r in with_units),
            "ru_available": sum(1 for x in rows if x["ru_available"]),
            "ru_identical": sum(1 for x in rows if x["ru_identical"]),
            "native": sum(1 for x in rows if x["native"]),
        }
    return table


def gated(t):
    return t["units"] >= GATE_UNITS and t["repos"] >= GATE_REPOS


def grade(table):
    """Pre-registered verdicts (PREREG.md). Integer comparisons only."""
    uk, be, ru = table["uk"], table["be"], table["ru"]
    v = {}
    if not gated(uk):
        return {p: "NOT TESTABLE (gate)" for p in ("P1", "P2", "P3", "P4")}
    v["P1"] = "HELD" if uk["repos_flagged"] >= P1_MIN_REPOS else "FAILED"
    d, s = uk["ru_available"], uk["ru_identical"]
    v["P2"] = "NOT TESTABLE" if d < P2_MIN_UNITS else ("HELD" if 2 * s >= d else "FAILED")
    # flagged_be / units_be > flagged_uk / units_uk
    if not gated(be):
        v["P3"] = "NOT TESTABLE (gate)"
    else:
        v["P3"] = "HELD" if be["flagged"] * uk["units"] > uk["flagged"] * be["units"] else "FAILED"
    # flagged_ru / units_ru < flagged_uk / units_uk
    if not gated(ru):
        v["P4"] = "NOT TESTABLE (gate)"
    else:
        v["P4"] = "HELD" if ru["flagged"] * uk["units"] < uk["flagged"] * ru["units"] else "FAILED"
    return v


def wait_for_prereg(minutes):
    """The pre-registration must be public before any repository is read."""
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


def control():
    """The detector must fire on known cases and stay quiet on clean ones (positive control)."""
    cases = [
        ("uk", "Налаштування", "Settings", []),
        ("uk", "Настройки", "Settings", []),  # Russian, but none of the four letters: missed
        ("uk", "Выберите файл", "Choose a file", ["ы"]),
        ("uk", "Ёмкость", "Capacity", ["ё"]),
        ("be", "Налады захаваны", "Settings saved", []),
        ("be", "Настройки сохранены", "Settings saved", ["и"]),
        ("be", "Мо" + "и" + chr(0x0306) + " файл", "My file", []),  # decomposed й is not и
        ("ru", "Привіт", "Hello", ["і"]),
        ("ru", "Настройки", "Settings", []),
        ("sr", "Подешавања", "Settings", []),
        ("sr", "Настройки", "Settings", ["й"]),
        ("uk", "Привіт, Э", "Hello, Э", []),  # the source has it too
    ]
    return all(foreign_letters(lang, t, s) == want for lang, t, s, want in cases)


ROW_COLS = ["repo", "head", "lang", "res_dir", "locale_dir", "file", "key", "index", "letters",
            "ru_available", "ru_identical", "same_as", "native", "text"]


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
    if not control():
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
    print("cyrillic_leak %s: %d repositories" % (VERSION, len(repos)), flush=True)

    tmp_root = tempfile.mkdtemp(prefix="cyrleak-")
    selftest = {}
    for u in ("https://github.com/TeamNewPipe/NewPipe", "https://gitlab.com/fdroid/fdroidclient"):
        r = process_repo(u, tmp_root)
        selftest[u] = {"status": r["status"], "units": dict(r.get("units", {}))}
    print("selftest", json.dumps(selftest), flush=True)
    if not any(v["units"].get("uk") and v["units"].get("ru") for v in selftest.values()):
        print("selftest found no Ukrainian and Russian strings; clone method broken, stopping",
              file=sys.stderr)
        return 3

    deadline = time.time() + a.budget_minutes * 60
    results, skipped = [], []
    jl = open(os.path.join(a.out_dir, "repos.jsonl"), "w", encoding="utf-8")
    lf = open(os.path.join(a.out_dir, "flagged.csv"), "w", encoding="utf-8", newline="")
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
            jl.write(json.dumps({
                "repo": r["repo"], "status": r["status"], "head": r.get("head"),
                "error": r.get("error"), "seconds": r.get("seconds"),
                "units": dict(r.get("units", {})), "flagged": dict(r.get("flagged", {})),
                "source_cyrillic": dict(r.get("source_cyrillic", {})),
                "parse_failed": r.get("parse_failed", 0)}, ensure_ascii=False, sort_keys=True) + "\n")
            for row in r.get("rows", []):
                lw.writerow(dict(row, repo=r["repo"], head=r.get("head", "")))
            if n % 100 == 0:
                jl.flush()
                lf.flush()
                print("%d/%d done, %.0f min" % (n, len(repos), (time.time() - started) / 60), flush=True)
    jl.close()
    lf.close()
    shutil.rmtree(tmp_root, ignore_errors=True)

    ok = [r for r in results if r.get("status") in ("ok", "no-cyrillic")]
    table = per_lang(ok)
    summary = {
        "verdicts": grade(table), "languages": table,
        "version": VERSION, "repos_url": REPOS_URL, "repos_sha256": hashlib.sha256(raw).hexdigest(),
        "prereg_sha256": prereg_sha, "repos_listed": len(repos), "repos_not_started": len(skipped),
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
