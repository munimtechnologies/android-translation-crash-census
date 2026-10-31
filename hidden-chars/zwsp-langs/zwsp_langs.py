#!/usr/bin/env python3
# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""The doubled zero-width space in th/lo/my/km/bo/dz translations (pre-registered).

Follow-up to the hidden-chars census, which skips these six languages when it counts stray U+200B
because their scripts can use U+200B as a word-break hint. A word-break hint is one U+200B
between letters; this counts the other shape, "space + exactly two U+200B + letter", in those
languages (group Z) and in every other language (group N), in one scan. See PREREG.md.

Same corpus (hidden-chars/repos.txt), clone method and unit definition as exif_pair.py 0.1.0,
whose helpers are copied here so the script stands alone.

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
BASE = "https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/main/"
REPOS_URL = BASE + "hidden-chars/repos.txt"
PREREG_URL = BASE + "hidden-chars/zwsp-langs/PREREG.md"
PREREG_MARK = "zwsp-langs PREREG v1"
SPARSE = "**/res/values*/*.xml"

ZWSP = chr(0x200B)
PAIR_RE = re.compile(" " + ZWSP + ZWSP + r"(?=[^\W\d_])")
SINGLE_RE = re.compile(" " + ZWSP + r"(?=[^\W\d_])")  # reported, not predicted

# Pre-registered thresholds (PREREG.md).
GATE_UNITS = 10000
GATE_REPOS = 50
P1_UNITS = 5
P1_REPOS = 3

# From hiddenchar.py 0.1.0 (unchanged).
ZWSP_LANGS = {"th", "lo", "my", "km", "bo", "dz"}
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


def pair_context(text):
    """(latin_before, word_before) at the first pair, or None if the text has no pair."""
    m = PAIR_RE.search(text)
    if not m:
        return None
    head = text[:m.start()]
    prev = head[-1:] if head else ""
    w = re.search(r"(\S+)$", head)
    return prev.isascii() and prev.isalnum(), (w.group(1) if w else "")


def new_counts():
    # units, pair units, single-U+200B-after-space units, units with any U+200B
    return [0, 0, 0, 0]


def count_unit(c, tgt):
    c[0] += 1
    c[1] += int(PAIR_RE.search(tgt) is not None)
    c[2] += int(SINGLE_RE.search(tgt) is not None)
    c[3] += int(ZWSP in tgt)


def scan_checkout(root):
    """Group Z / N counts for every res/ folder under root, and the group-Z pair units."""
    out = {"Z": new_counts(), "N": new_counts(), "langs": {}, "rows": []}
    langs = collections.defaultdict(new_counts)
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
            if not lang:
                continue
            z = lang in ZWSP_LANGS
            target = merge_dir(os.path.join(dirpath, d))
            for key, i, src, tgt in units(source, target):
                if ZWSP in src:
                    continue
                count_unit(out["Z" if z else "N"], tgt)
                if not z:
                    continue
                count_unit(langs[lang], tgt)
                ctx = pair_context(tgt)
                if ctx:
                    out["rows"].append({"res_dir": rel, "locale_dir": d, "lang": lang, "key": key, "index": i,
                                        "latin_before": int(ctx[0]), "word_before": show(ctx[1], 60),
                                        "source": show(src), "target": show(tgt)})
    out["langs"] = dict(langs)
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
        if res["Z"][0] + res["N"][0] == 0:
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
    """Pre-registered verdicts from pooled counts (PREREG.md). Integer comparisons only."""
    Z, N = stats["Z"], stats["N"]
    if Z[0] < GATE_UNITS or stats["z_repos"] < GATE_REPOS:
        return {p: "NOT TESTABLE (gate)" for p in ("P1", "P2", "P3")}
    v = {"P1": "HELD" if Z[1] >= P1_UNITS and stats["z_pair_repos"] >= P1_REPOS else "FAILED"}
    if N[0] == 0 or N[1] == 0:
        v["P2"] = "NOT TESTABLE"
    else:
        # Z[1]/Z[0] >= 0.5 * N[1]/N[0]
        v["P2"] = "HELD" if 2 * Z[1] * N[0] >= N[1] * Z[0] else "FAILED"
    pairs, latin = stats["z_latin"]
    v["P3"] = "NOT TESTABLE" if pairs == 0 else ("HELD" if 2 * latin >= pairs else "FAILED")
    return v


def aggregate(results):
    ok = [r for r in results if r.get("status") == "ok"]
    Z, N = new_counts(), new_counts()
    langs = collections.defaultdict(new_counts)
    z_repo = {}
    words = collections.Counter()
    latin = 0
    npairs = 0
    for r in ok:
        for j in range(4):
            Z[j] += r["Z"][j]
            N[j] += r["N"][j]
        for lang, c in r["langs"].items():
            for j in range(4):
                langs[lang][j] += c[j]
        if r["Z"][0]:
            z_repo[r["repo"]] = [r["Z"][0], r["Z"][1]]
        for row in r["rows"]:
            npairs += 1
            latin += row["latin_before"]
            words[row["word_before"]] += 1
    stats = {"Z": Z, "N": N, "z_repos": len(z_repo),
             "z_pair_repos": sum(1 for c in z_repo.values() if c[1]), "z_latin": [npairs, latin]}

    def r8(x):
        return None if x is None else round(x, 8)

    def block(c):
        return {"units": c[0], "pair": c[1], "single_after_space": c[2], "any_zwsp": c[3],
                "pair_rate": r8(rate(c)), "any_zwsp_rate": r8(c[3] / c[0] if c[0] else None)}

    rz, rn = rate(Z), rate(N)
    return {
        "verdicts": grade(stats),
        "repos_ok": len(ok),
        "Z": block(Z), "N": block(N),
        "ratio_Z_over_N": r8(rz / rn) if rz is not None and rn else None,
        "z_repos": stats["z_repos"], "z_pair_repos": stats["z_pair_repos"],
        "z_pairs_latin_before": latin,
        "exploratory_langs": {k: block(c) for k, c in sorted(langs.items())},
        "exploratory_pair_repos": {k: c for k, c in sorted(z_repo.items()) if c[1]},
        "exploratory_word_before": sorted(([w, n] for w, n in words.items()), key=lambda x: (-x[1], x[0]))[:40],
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


COLS = ["repo", "head", "res_dir", "locale_dir", "lang", "key", "index", "latin_before", "word_before",
        "source", "target"]


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
    print("zwsp_langs %s: %d repositories" % (VERSION, len(repos)), flush=True)

    tmp_root = tempfile.mkdtemp(prefix="zwsplangs-")
    selftest = {}
    for u in ("https://gitlab.com/fdroid/fdroidclient", "https://github.com/TeamNewPipe/NewPipe"):
        r = process_repo(u, tmp_root)
        selftest[u] = {"status": r["status"], "units": r.get("Z", [0])[0] + r.get("N", [0])[0]}
    print("selftest", json.dumps(selftest), flush=True)
    if not any(v["units"] for v in selftest.values()):
        print("selftest found no translations; clone method broken, stopping", file=sys.stderr)
        return 3

    deadline = time.time() + a.budget_minutes * 60
    results, skipped = [], []
    jl = open(os.path.join(a.out_dir, "repos.jsonl"), "w", encoding="utf-8")
    rf = open(os.path.join(a.out_dir, "zwsp_lang_units.csv"), "w", encoding="utf-8", newline="")
    rw = csv.DictWriter(rf, fieldnames=COLS)
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
            jl.write(json.dumps({k: r.get(k) for k in ("repo", "status", "head", "error", "seconds", "Z", "N")},
                                sort_keys=True) + "\n")
            for row in r.get("rows", []):
                rw.writerow({k: row.get(k, "") for k in COLS} | {"repo": r["repo"], "head": r.get("head", "")})
            if n % 100 == 0:
                jl.flush()
                rf.flush()
                print("%d/%d done, %.0f min" % (n, len(repos), (time.time() - started) / 60), flush=True)
    jl.close()
    rf.close()
    shutil.rmtree(tmp_root, ignore_errors=True)

    summary = aggregate(results)
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
