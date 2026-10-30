#!/usr/bin/env python3
# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Doubled zero-width space after "EXIF" in shipped Android translations (pre-registered).

Follow-up to the hidden-chars census. For every translated unit whose English source has an
all-capital word of 2-5 letters followed by a space and a letter ("EXIF tag", "GPS data"),
check whether the translation carries that word, a space and exactly two U+200B before a
letter (the "signature"). Compares "EXIF" with every other such word. See PREREG.md.

Same corpus (hidden-chars/repos.txt) and the same unit definition as hiddenchar.py 0.1.0,
whose parsing helpers are copied here so the script stands alone.

Made with AI agents by MV2 of Munim, Inc. Standard library only; needs git.
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
import urllib.request
import xml.etree.ElementTree as ET

VERSION = "0.1.0"
REPOS_URL = ("https://raw.githubusercontent.com/munimtechnologies/"
             "android-translation-crash-census/main/hidden-chars/repos.txt")
PREREG_URL = ("https://raw.githubusercontent.com/munimtechnologies/"
              "android-translation-crash-census/main/hidden-chars/exif-pair/PREREG.md")
PREREG_MARK = "exif-pair PREREG v1"
SPARSE = "**/res/values*/*.xml"

ZWSP = chr(0x200B)
TARGET = "EXIF"
MIXED = "Exif"  # reported, not predicted
NAMED = ("GPS", "PDF", "URL", "VPN", "QR", "API", "HTTP", "HTTPS", "USB", "SD", "PIN", "NFC",
         "SMS", "JSON", "CSV", "HTML")
CAPS_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z]{2,5})(?= [^\W\d_])")
MIXED_RE = re.compile(r"(?<![A-Za-z0-9])Exif(?= [^\W\d_])")
PAIR_RE = re.compile(" " + ZWSP + ZWSP + r"(?=[^\W\d_])")

# From hiddenchar.py 0.1.0 (unchanged).
ZWSP_LANGS = {"th", "lo", "my", "km", "bo", "dz"}
_U_ESC = re.compile(r"(?<!\\)\\u([0-9A-Fa-f]{4})")
_LOCALE_DIR = re.compile(
    r"^values-(?:([a-z]{2,3})(?:-r([A-Z]{2}|[0-9]{3}))?|b\+([a-zA-Z]{2,3})(?:\+[A-Za-z0-9]+)*)$")
_NOT_LOCALES = {"car"}
_PSEUDO = {("en", "XA"), ("ar", "XB")}

# Pre-registered thresholds (PREREG.md).
GATE_REPOS = 2000
MIN_EXIF_UNITS = 100
P1_RATE = 0.01
P2_FACTOR = 20
P3_MIN_UNITS = 200
P3_RATE = 0.002
P4_SHARE = 0.5
P5_MIN_UNITS = 30
P5_SHARE = 0.5


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


def parse_values(path):
    root = ET.parse(path).getroot()
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


def merge_dir(folder):
    merged = {}
    for fn in sorted(os.listdir(folder)):
        if not fn.endswith(".xml"):
            continue
        try:
            merged.update(parse_values(os.path.join(folder, fn)))
        except (ET.ParseError, ValueError, OSError):
            pass
    return {k: v for k, v in merged.items() if v}


def show(text, limit=300):
    s = "".join("<U+200B>" if ch == ZWSP else ch for ch in text).replace("\n", "\\n")
    return s if len(s) <= limit else s[:limit] + "..."


def units(source, target):
    """(key, index, source_text, target_text) for each translated unit, as hiddenchar counts them."""
    for key, tlist in target.items():
        slist = source.get(key)
        if not slist or not tlist:
            continue
        union = "".join(slist)
        if not union.strip():
            continue
        for i, t in enumerate(tlist):
            if not t.strip():
                continue
            yield key, i, (slist[i] if key.startswith("array:") and i < len(slist) else union), t


def words(src):
    """Distinct all-capital words (2-5 letters) followed by a space and a letter, plus 'Exif'."""
    found = set(CAPS_RE.findall(src))
    if MIXED_RE.search(src):
        found.add(MIXED)
    return found


def sig_after(word, text):
    """True if text has the word, a space, exactly two U+200B, then a letter."""
    pat = r"(?<![A-Za-z0-9])" + re.escape(word) + " " + ZWSP + ZWSP + r"(?=[^\W\d_])"
    return re.search(pat, text) is not None


def unit_record(src, tgt):
    """Per-word outcomes for one unit, or None if the source has U+200B or no word."""
    if ZWSP in src:
        return None
    toks = words(src)
    if not toks:
        return None
    return {"words": {t: sig_after(t, tgt) for t in sorted(toks)},
            "any_zwsp": ZWSP in tgt, "pair": PAIR_RE.search(tgt) is not None}


def scan_checkout(root):
    """Counts for every res/ folder under root, outside th/lo/my/km/bo/dz."""
    out = {"units": 0, "pair_units": 0, "tok": {}, "control": [0, 0], "rows": []}
    tok = collections.defaultdict(lambda: [0, 0, 0])
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        if os.path.basename(dirpath) != "res" or "values" not in dirnames:
            continue
        source = merge_dir(os.path.join(dirpath, "values"))
        if not source:
            continue
        rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
        for d in dirnames:
            lang = locale_of(d)
            if not lang or lang in ZWSP_LANGS:
                continue
            target = merge_dir(os.path.join(dirpath, d))
            for key, i, src, tgt in units(source, target):
                out["units"] += 1
                if ZWSP not in src and PAIR_RE.search(tgt):
                    out["pair_units"] += 1
                rec = unit_record(src, tgt)
                if rec is None:
                    continue
                ctrl = [t for t in rec["words"] if t not in (TARGET, MIXED)]
                if ctrl:
                    out["control"][0] += 1
                    out["control"][1] += int(any(rec["words"][t] for t in ctrl))
                for t, hit in rec["words"].items():
                    c = tok[t]
                    c[0] += 1
                    c[1] += int(hit)
                    c[2] += int(rec["any_zwsp"])
                    if t in (TARGET, MIXED):
                        out["rows"].append({
                            "word": t, "res_dir": rel, "locale_dir": d, "lang": lang, "key": key,
                            "index": i, "signature": int(hit), "any_zwsp": int(rec["any_zwsp"]),
                            "pair_anywhere": int(rec["pair"]), "source": show(src), "target": show(tgt)})
    out["tok"] = dict(tok)
    return out


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
        git(["-C", s, "sparse-checkout", "set", "--no-cone", SPARSE])
        branch = git(["-C", s, "symbolic-ref", "--short", "HEAD"]).stdout.strip()
        git(["-C", s, "checkout", "--quiet"] + ([branch] if branch else []))
        if not has_values(s):
            git(["-C", s, "read-tree", "-mu", "HEAD"])
        res["head"] = git(["-C", s, "rev-parse", "HEAD"]).stdout.strip()
        res.update(scan_checkout(s))
        if res["units"] == 0:
            res["status"] = "no-translations"
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


def rate(c):
    return c[1] / c[0] if c and c[0] else None


def grade(stats):
    """Pre-registered verdicts from pooled counts (PREREG.md)."""
    if stats["repos_with_units"] < GATE_REPOS:
        return {p: "NOT TESTABLE (gate)" for p in ("P1", "P2", "P3", "P4", "P5")}
    v = {}
    ex = stats["tok"].get(TARGET, [0, 0, 0])
    enough = ex[0] >= MIN_EXIF_UNITS
    er = rate(ex)
    v["P1"] = "NOT TESTABLE" if not enough else ("HELD" if er >= P1_RATE else "FAILED")
    cr = rate(stats["control"])
    if not enough or cr is None:
        v["P2"] = "NOT TESTABLE"
    else:
        v["P2"] = "HELD" if er > 0 and er >= P2_FACTOR * cr else "FAILED"
    named = [stats["tok"][t] for t in NAMED if t in stats["tok"] and stats["tok"][t][0] >= P3_MIN_UNITS]
    v["P3"] = ("NOT TESTABLE" if not named
               else "HELD" if all(rate(c) < P3_RATE for c in named) else "FAILED")
    affected = [c for c in stats["exif_repo"].values() if c[1] > 0]
    if not enough or not affected:
        v["P4"] = "NOT TESTABLE"
    else:
        tot = [sum(c[0] for c in affected), sum(c[1] for c in affected)]
        v["P4"] = "HELD" if rate(tot) < P4_SHARE else "FAILED"
    langs = [c for c in stats["exif_lang"].values() if c[0] >= P5_MIN_UNITS]
    if not enough or not langs:
        v["P5"] = "NOT TESTABLE"
    else:
        v["P5"] = "HELD" if sum(1 for c in langs if c[1] > 0) / len(langs) >= P5_SHARE else "FAILED"
    return v


def aggregate(results):
    ok = [r for r in results if r.get("status") == "ok"]
    tok = collections.defaultdict(lambda: [0, 0, 0])
    tok_repos = collections.Counter()
    control = [0, 0]
    exif_repo = collections.defaultdict(lambda: [0, 0])
    exif_lang = collections.defaultdict(lambda: [0, 0])
    mixed_lang = collections.defaultdict(lambda: [0, 0])
    next_word = collections.defaultdict(lambda: [0, 0])
    units_total = pair_total = 0
    for r in ok:
        units_total += r["units"]
        pair_total += r["pair_units"]
        control[0] += r["control"][0]
        control[1] += r["control"][1]
        for t, c in r["tok"].items():
            for j in range(3):
                tok[t][j] += c[j]
            tok_repos[t] += 1
        for row in r["rows"]:
            if row["word"] == TARGET:
                exif_repo[r["repo"]][0] += 1
                exif_repo[r["repo"]][1] += row["signature"]
                exif_lang[row["lang"]][0] += 1
                exif_lang[row["lang"]][1] += row["signature"]
                m = re.search(r"(?<![A-Za-z0-9])EXIF ([^\W\d_]+)", row["source"])
                w = m.group(1) if m else ""
                next_word[w][0] += 1
                next_word[w][1] += row["signature"]
            else:
                mixed_lang[row["lang"]][0] += 1
                mixed_lang[row["lang"]][1] += row["signature"]
    stats = {"repos_with_units": len(ok), "tok": dict(tok), "control": control,
             "exif_repo": dict(exif_repo), "exif_lang": dict(exif_lang)}
    verdicts = grade(stats)
    ex = tok.get(TARGET, [0, 0, 0])
    mx = tok.get(MIXED, [0, 0, 0])

    def r4(x):
        return None if x is None else round(x, 6)
    return {
        "verdicts": verdicts,
        "repos_with_units": len(ok), "units_non_zwsp_langs": units_total,
        "pair_units_anywhere": pair_total,
        "exif": {"units": ex[0], "signature": ex[1], "any_zwsp": ex[2], "rate": r4(rate(ex)),
                 "repos": tok_repos.get(TARGET, 0),
                 "repos_with_signature": sum(1 for c in exif_repo.values() if c[1]),
                 "langs": len(exif_lang), "langs_with_signature": sum(1 for c in exif_lang.values() if c[1])},
        "control": {"units": control[0], "signature": control[1], "rate": r4(rate(control))},
        "ratio_exif_over_control": r4(rate(ex) / rate(control)) if rate(ex) is not None and rate(control) else None,
        "named": {t: {"units": tok[t][0], "signature": tok[t][1], "rate": r4(rate(tok[t]))}
                  for t in NAMED if t in tok},
        "affected_repos": {k: c for k, c in sorted(exif_repo.items()) if c[1]},
        "exif_lang": {k: c for k, c in sorted(exif_lang.items())},
        "exploratory_mixed_Exif": {"units": mx[0], "signature": mx[1], "rate": r4(rate(mx)),
                                   "by_lang_with_signature": {k: c for k, c in sorted(mixed_lang.items()) if c[1]}},
        "exploratory_exif_next_word": sorted(([w, c[0], c[1]] for w, c in next_word.items()),
                                             key=lambda x: (-x[1], x[0]))[:40],
        "words_table": sorted(([t, c[0], c[1], c[2], tok_repos[t]] for t, c in tok.items()),
                               key=lambda x: (-x[1], x[0])),
    }


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
    print("exif_pair %s: %d repositories" % (VERSION, len(repos)), flush=True)

    tmp_root = tempfile.mkdtemp(prefix="exifpair-")
    selftest = {}
    for u in ("https://gitlab.com/fdroid/fdroidclient", "https://github.com/TeamNewPipe/NewPipe"):
        r = process_repo(u, tmp_root)
        selftest[u] = {"status": r["status"], "units": r.get("units", 0)}
    print("selftest", json.dumps(selftest), flush=True)
    if not any(v["units"] for v in selftest.values()):
        print("selftest found no translations; clone method broken, stopping", file=sys.stderr)
        return 3

    deadline = time.time() + a.budget_minutes * 60
    results, skipped = [], []
    jl = open(os.path.join(a.out_dir, "repos.jsonl"), "w", encoding="utf-8")
    rf = open(os.path.join(a.out_dir, "exif_units.csv"), "w", encoding="utf-8", newline="")
    cols = ["repo", "head", "word", "res_dir", "locale_dir", "lang", "key", "index",
            "signature", "any_zwsp", "pair_anywhere", "source", "target"]
    rw = csv.DictWriter(rf, fieldnames=cols)
    rw.writeheader()

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
            ex_c = r.get("tok", {}).get(TARGET, [0, 0, 0])
            jl.write(json.dumps({k: r.get(k) for k in ("repo", "status", "head", "units", "error",
                                                       "seconds")} | {"exif": ex_c}, sort_keys=True) + "\n")
            for row in r.get("rows", []):
                rw.writerow({k: row.get(k, "") for k in cols} | {"repo": r["repo"], "head": r.get("head", "")})
            if n % 100 == 0:
                jl.flush()
                rf.flush()
                print("%d/%d done, %.0f min" % (n, len(repos), (time.time() - started) / 60), flush=True)
    jl.close()
    rf.close()
    shutil.rmtree(tmp_root, ignore_errors=True)

    summary = aggregate(results)
    table = summary.pop("words_table")
    with open(os.path.join(a.out_dir, "words.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["word", "units", "signature", "any_zwsp", "repos"])
        w.writerows(table)
    summary.update({
        "version": VERSION, "repos_url": REPOS_URL, "repos_sha256": hashlib.sha256(raw).hexdigest(),
        "prereg_sha256": prereg_sha, "repos_listed": len(repos), "repos_not_started": len(skipped),
        "status_counts": dict(collections.Counter(r["status"] for r in results)),
        "selftest": selftest, "minutes": round((time.time() - started) / 60, 1),
    })
    with open(os.path.join(a.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps(summary["verdicts"]), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
