#!/usr/bin/env python3
# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Mainland vocabulary in Taiwan Chinese Android translations (pre-registered).

For every repository in hidden-chars/repos.txt (the F-Droid source repositories of the census),
reads the Android string resources at HEAD and, for each Taiwan translation (values-zh-rTW,
values-b+zh+Hant+TW ...) and each Hong Kong or Macau translation (values-zh-rHK, -rMO ...),
finds mainland terms written in Traditional characters (軟件 for 軟體, 默認 for 預設) with
OpenCC's Taiwan phrase table, read by forward maximum matching as OpenCC does. Each flagged
Taiwan string is compared with the same string in the app's Simplified file, to see whether it
is a character-by-character conversion of it. A fixed sample is written for a hand check. See
PREREG.md for the predictions and how they are graded.

The dictionaries come from OpenCC (Apache-2.0) at a pinned tag. Same corpus, clone method and
file rules as hanzi_leak.py 0.1.0, whose helpers are copied here so the script stands alone.
Needs git.

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

VERSION = "0.1.0"
BASE = "https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/main/"
REPOS_URL = BASE + "hidden-chars/repos.txt"
PREREG_URL = BASE + "zh-vocab/PREREG.md"
PREREG_MARK = "zh-vocab PREREG v1"
OPENCC_TAG = "ver.1.4.2"
OPENCC_URL = "https://raw.githubusercontent.com/BYVoid/OpenCC/%s/data/dictionary/" % OPENCC_TAG
DICTS = ("STCharacters.txt", "TSCharacters.txt", "TWVariants.txt", "HKVariants.txt",
         "TWPhrases.txt")
SPARSE = ["**/res/values*/*.xml"]

# Pre-registered thresholds (PREREG.md).
GATE_UNITS = 20000
GATE_REPOS = 100
V1_NUM, V1_DEN = 1, 3       # V1: repos_flagged * 3 >= repos * 1
V2_GATE_UNITS = 2000
V2_GATE_REPOS = 20
V3_MIN_REPOS = 10
V4_NUM, V4_DEN = 3, 4       # V4: mainland * 4 >= sample * 3
SAMPLE_SIZE = 40

# Android \uXXXX escapes (built without a literal escape sequence in this file).
_U_ESC = re.compile(r"(?<!\\)\\" + "u" + r"([0-9A-Fa-f]{4})")
_ZH_REGION = re.compile(r"^values-zh(?:-r([A-Z]{2}))?$")
_ZH_BCP = re.compile(r"^values-b\+zh((?:\+[A-Za-z0-9]+)*)$")
HANS_REGIONS = {"cn", "sg"}


def decode_android(text):
    return _U_ESC.sub(lambda m: chr(int(m.group(1), 16)), text)


def zh_group(dirname):
    """'tw', 'hk', 'hant' (Traditional, no region), 'hans', 'plain' or None for a values-* folder."""
    m = _ZH_REGION.match(dirname)
    if m:
        region = m.group(1)
        if region is None:
            return "plain"
        region = region.lower()
        if region == "tw":
            return "tw"
        if region in ("hk", "mo"):
            return "hk"
        if region in HANS_REGIONS:
            return "hans"
        return None
    m = _ZH_BCP.match(dirname)
    if m:
        subtags = [s.lower() for s in m.group(1).split("+") if s]
        if "hans" in subtags:
            return "hans"
        if "tw" in subtags:
            return "tw"
        if "hk" in subtags or "mo" in subtags:
            return "hk"
        if "hant" in subtags:
            return "hant"
        if any(s in HANS_REGIONS for s in subtags):
            return "hans"
        return "plain"
    return None


def hans_rank(dirname):
    """Sort key choosing the Simplified folder a flagged string is compared with."""
    g = zh_group(dirname)
    if dirname == "values-zh-rCN":
        return (0, dirname)
    if g == "hans" and dirname != "values-zh-rSG":
        return (1, dirname)
    if dirname == "values-zh-rSG":
        return (2, dirname)
    if g == "plain":
        return (3, dirname)
    return None


def is_han(c):
    o = ord(c)
    return (0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF or 0xF900 <= o <= 0xFAFF
            or 0x20000 <= o <= 0x3134F)


def has_han(text):
    return any(is_han(c) for c in text)


def parse_dict(text, single=True):
    """OpenCC dictionary text -> {key: [values]}; single-character keys only if `single`."""
    out = {}
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        key = parts[0].strip()
        vals = [v for v in parts[1].strip().split(" ") if v]
        if key and vals and (len(key) == 1 or not single):
            out[key] = vals
    return out


def build_s_set(st, ts, tw, hk):
    """Simplified-only characters, exactly as hanzi_leak.py 0.1.0 builds S."""
    st_vals = {v for vs in st.values() for v in vs}
    regional = {v for d in (tw, hk) for vs in d.values() for v in vs}
    return {k for k in st if k not in st_vals and k not in ts and k not in regional}


class Phrases:
    """OpenCC's Taiwan phrase table, matched the way OpenCC segments text."""

    def __init__(self, table):
        self.table = table
        self.maxlen = max((len(k) for k in table), default=0)

    def flagged_key(self, key):
        """A key is a mainland term if Taiwan usage (its values) doesn't include the key itself."""
        return key not in self.table[key]

    def matches(self, text):
        """Forward maximum matching: [(start, key)] of every table key matched in `text`."""
        out, i, n = [], 0, len(text)
        while i < n:
            hit = None
            for size in range(min(self.maxlen, n - i), 0, -1):
                if text[i:i + size] in self.table:
                    hit = text[i:i + size]
                    break
            if hit:
                out.append((i, hit))
                i += len(hit)
            else:
                i += 1
        return out

    def terms(self, text, source_text):
        """Mainland terms in `text` that the source string doesn't contain, in order, no repeats."""
        seen = []
        for _, key in self.matches(text):
            if self.flagged_key(key) and key not in source_text and key not in seen:
                seen.append(key)
        return seen


def char_equivalent(simplified, traditional, st):
    """True if `traditional` is `simplified` converted character by character (OpenCC STCharacters)."""
    if len(simplified) != len(traditional):
        return False
    return all(a == b or b in st.get(a, ()) for a, b in zip(simplified, traditional))


def parse_values(path):
    return parse_root(ET.parse(path).getroot())


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


def units(source, target):
    """(key, index, text, source text) of each translated item that has a Han character."""
    for key in sorted(target, key=str):
        tlist, slist = target[key], source.get(key)
        if not tlist or not slist:
            continue
        src = " ".join(slist)
        for i, t in enumerate(tlist):
            if t.strip() and has_han(t):
                yield key, i, t, src


def item(values, key, i):
    if not values:
        return None
    texts = values.get(key)
    if not texts or i >= len(texts) or not has_han(texts[i]):
        return None
    return texts[i]


def new_counts():
    return {"units": collections.Counter(), "flagged": collections.Counter(),
            "terms": collections.Counter(), "source_han": collections.Counter(),
            "parse_failed": 0, "rows": []}


def scan_res_dir(dirpath, dirnames, phrases, st, s_set):
    out = new_counts()
    groups = {}
    for d in sorted(dirnames):
        g = zh_group(d)
        if g:
            groups.setdefault(g, []).append(d)
    if not any(g in groups for g in ("tw", "hk", "hant")):
        return out
    ranked = sorted(r for r in (hans_rank(d) for d in dirnames) if r)
    hans_dir = ranked[0][1] if ranked else None
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

    for g in ("tw", "hk", "hant"):
        for d in groups.get(g, []):
            for fn in sorted(os.listdir(os.path.join(dirpath, d))):
                if not fn.endswith(".xml") or not os.path.isfile(os.path.join(dirpath, "values", fn)):
                    continue
                source, target = load("values", fn), load(d, fn)
                if not source or not target:
                    continue
                for key, i, t, src in units(source, target):
                    out["units"][g] += 1
                    if has_han(src):
                        out["source_han"][g] += 1
                    terms = phrases.terms(t, src)
                    if not terms:
                        continue
                    out["flagged"][g] += 1
                    for term in terms:
                        out["terms"][g + "\t" + term] += 1
                    o = item(load(hans_dir, fn), key, i) if hans_dir else None
                    out["rows"].append({
                        "group": g, "locale_dir": d, "file": fn, "key": key, "index": i,
                        "terms": " ".join(terms),
                        "taiwan": " | ".join("/".join(phrases.table[x]) for x in terms),
                        "hans_dir": hans_dir if o is not None else "",
                        "hans_available": o is not None,
                        "hans_identical": o is not None and o.strip() == t.strip(),
                        "char_equivalent": o is not None and char_equivalent(o.strip(), t.strip(), st),
                        "has_s": any(c in s_set and c not in src for c in t),
                        "text": t.strip()[:200], "source": src.strip()[:200],
                        "hans_text": (o or "").strip()[:200]})
    return out


def scan_strings(root, phrases, st, s_set):
    total = new_counts()
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        if os.path.basename(dirpath) != "res" or "values" not in dirnames:
            continue
        r = scan_res_dir(dirpath, dirnames, phrases, st, s_set)
        rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
        for k in ("units", "flagged", "terms", "source_han"):
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


def process_repo(url, tmp_root, phrases, st, s_set):
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
        res.update(scan_strings(s, phrases, st, s_set))
        if not sum(res["units"].values()):
            res["status"] = "no-traditional"
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


def group_totals(results, g):
    w = [r for r in results if r.get("units", {}).get(g)]
    return {"repos": len(w), "units": sum(r["units"][g] for r in w),
            "flagged": sum(r["flagged"].get(g, 0) for r in w),
            "repos_flagged": sum(1 for r in w if r["flagged"].get(g)),
            "source_han_units": sum(r.get("source_han", {}).get(g, 0) for r in w)}


def v3_counts(rows):
    """(available, char_equivalent) over flagged Taiwan rows of one repository."""
    a = sum(1 for x in rows if x["group"] == "tw" and x["hans_available"])
    e = sum(1 for x in rows if x["group"] == "tw" and x["char_equivalent"])
    return a, e


def tables(results):
    t = {}
    for g in ("tw", "hk", "hant"):
        t[g] = group_totals(results, g)
        rows = [x for r in results for x in r.get("rows", []) if x["group"] == g]
        t[g]["hans_available"] = sum(1 for x in rows if x["hans_available"])
        t[g]["hans_identical"] = sum(1 for x in rows if x["hans_identical"])
        t[g]["char_equivalent"] = sum(1 for x in rows if x["char_equivalent"])
        t[g]["has_s"] = sum(1 for x in rows if x["has_s"])
        terms = collections.Counter()
        repos_per_term = collections.Counter()
        for r in results:
            mine = {k.split("\t", 1)[1]: v for k, v in r.get("terms", {}).items()
                    if k.split("\t", 1)[0] == g}
            terms.update(mine)
            repos_per_term.update(mine.keys())
        t[g]["top_terms"] = [[k, v, repos_per_term[k]] for k, v in
                             sorted(terms.items(), key=lambda kv: (-kv[1], kv[0]))[:40]]
        t[g]["distinct_terms"] = len(terms)
    shares = []
    for r in results:
        a, e = v3_counts(r.get("rows", []))
        if a:
            shares.append(fractions.Fraction(e, a))
    total = sum(shares, fractions.Fraction(0))
    t["v3"] = {"repos": len(shares), "sum_of_shares": "%d/%d" % (total.numerator, total.denominator),
               "mean_share": round(float(total / len(shares)), 4) if shares else None}
    return t, total, len(shares)


def gated(x, units=GATE_UNITS, repos=GATE_REPOS):
    return x["units"] >= units and x["repos"] >= repos


def grade(t, v3_sum, v3_n):
    """Pre-registered verdicts V1-V3 (PREREG.md). V4 is graded by hand from sample.csv."""
    tw, hk = t["tw"], t["hk"]
    if not gated(tw):
        return {p: "NOT TESTABLE (gate)" for p in ("V1", "V2", "V3", "V4")}
    v = {}
    v["V1"] = "HELD" if tw["repos_flagged"] * V1_DEN >= tw["repos"] * V1_NUM else "FAILED"
    if not gated(hk, V2_GATE_UNITS, V2_GATE_REPOS):
        v["V2"] = "NOT TESTABLE (gate)"
    else:
        v["V2"] = "HELD" if hk["flagged"] * tw["units"] > tw["flagged"] * hk["units"] else "FAILED"
    if v3_n < V3_MIN_REPOS:
        v["V3"] = "NOT TESTABLE"
    else:
        v["V3"] = "HELD" if 2 * v3_sum >= v3_n else "FAILED"
    v["V4"] = "PENDING (hand check of sample.csv)"
    return v


def grade_v4(labels):
    """V4 from hand labels ('mainland', 'fine', 'other'), one per sampled row."""
    if len(labels) < 4:
        return "NOT TESTABLE"
    m = sum(1 for x in labels if x == "mainland")
    return "HELD" if m * V4_DEN >= len(labels) * V4_NUM else "FAILED"


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def draw_sample(rows, size=SAMPLE_SIZE):
    """One flagged Taiwan row per repository (lowest hash of its location), repositories taken
    in order of the hash of their URL, up to `size`. Fixed in PREREG.md."""
    best = {}
    for x in rows:
        if x["group"] != "tw":
            continue
        h = sha("%s|%s|%s|%s|%s|%s" % (x["repo"], x["res_dir"], x["locale_dir"], x["file"],
                                        x["key"], x["index"]))
        if x["repo"] not in best or h < best[x["repo"]][0]:
            best[x["repo"]] = (h, x)
    order = sorted(best, key=sha)
    return [best[r][1] for r in order[:size]]


def control(phrases, s_set):
    """The detector must fire on known cases and stay quiet on clean ones (positive control)."""
    for k in ("軟件", "默認", "用戶", "信息", "內存"):
        if k not in phrases.table or not phrases.flagged_key(k):
            return False
    cases = [
        ("默認", "Default", ["默認"]),
        ("預設", "Default", []),
        ("軟體", "Software", []),
        ("軟件，用戶", "Software, user", ["軟件", "用戶"]),
        ("軟件", "軟件", []),  # the source has it too
    ]
    if not all(phrases.terms(text, src) == want for text, src, want in cases):
        return False
    return "这" in s_set and "這" not in s_set


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


def load_dicts(out_dir, local_dir=None):
    """Download (or read) the OpenCC dictionaries; copy them and their hashes to out_dir."""
    texts, hashes = {}, {}
    os.makedirs(os.path.join(out_dir, "opencc"), exist_ok=True)
    for name in DICTS:
        if local_dir:
            with open(os.path.join(local_dir, name), "rb") as f:
                raw = f.read()
        else:
            with urllib.request.urlopen(OPENCC_URL + name, timeout=120) as r:
                raw = r.read()
        hashes[name] = hashlib.sha256(raw).hexdigest()
        with open(os.path.join(out_dir, "opencc", name), "wb") as f:
            f.write(raw)
        texts[name] = raw.decode("utf-8")
    st, ts, tw, hk = (parse_dict(texts[n]) for n in DICTS[:4])
    phrases = Phrases(parse_dict(texts["TWPhrases.txt"], single=False))
    return st, build_s_set(st, ts, tw, hk), phrases, hashes


ROW_COLS = ["repo", "head", "group", "res_dir", "locale_dir", "file", "key", "index", "terms",
            "taiwan", "hans_dir", "hans_available", "hans_identical", "char_equivalent", "has_s",
            "text", "source", "hans_text"]
SAMPLE_COLS = ["n", "repo", "head", "res_dir", "locale_dir", "file", "key", "index", "terms",
               "taiwan", "text", "source"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--repos", help="local repos.txt instead of downloading")
    ap.add_argument("--dicts", help="local folder with the OpenCC files instead of downloading")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--budget-minutes", type=float, default=200)
    ap.add_argument("--prereg-wait-minutes", type=float, default=45)
    ap.add_argument("--skip-prereg-check", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    started = time.time()
    st, s_set, phrases, dict_hashes = load_dicts(a.out_dir, a.dicts)
    n_flag = sum(1 for k in phrases.table if phrases.flagged_key(k))
    print("zh_vocab %s: %d phrase keys, %d mainland terms, S %d characters"
          % (VERSION, len(phrases.table), n_flag, len(s_set)), flush=True)
    if not control(phrases, s_set):
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
    print("%d repositories" % len(repos), flush=True)

    tmp_root = tempfile.mkdtemp(prefix="zhvocab-")
    selftest = {}
    for u in ("https://github.com/TeamNewPipe/NewPipe", "https://gitlab.com/fdroid/fdroidclient"):
        r = process_repo(u, tmp_root, phrases, st, s_set)
        selftest[u] = {"status": r["status"], "units": dict(r.get("units", {}))}
    print("selftest", json.dumps(selftest), flush=True)
    if not any(v["units"].get("tw") for v in selftest.values()):
        print("selftest found no Taiwan strings; clone method broken, stopping", file=sys.stderr)
        return 3

    deadline = time.time() + a.budget_minutes * 60
    results, skipped, all_rows = [], [], []
    jl = open(os.path.join(a.out_dir, "repos.jsonl"), "w", encoding="utf-8")
    lf = open(os.path.join(a.out_dir, "flagged.csv"), "w", encoding="utf-8", newline="")
    lw = csv.DictWriter(lf, fieldnames=ROW_COLS)
    lw.writeheader()

    def work(u):
        if time.time() > deadline:
            return {"repo": u, "status": "not-started"}
        return process_repo(u, tmp_root, phrases, st, s_set)

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
                "source_han": dict(r.get("source_han", {})),
                "parse_failed": r.get("parse_failed", 0)}, ensure_ascii=False, sort_keys=True) + "\n")
            for row in r.get("rows", []):
                full = dict(row, repo=r["repo"], head=r.get("head", ""))
                lw.writerow(full)
                all_rows.append(full)
            r["rows"] = [dict(x, repo=r["repo"]) for x in r.get("rows", [])]
            if n % 100 == 0:
                jl.flush()
                lf.flush()
                print("%d/%d done, %.0f min" % (n, len(repos), (time.time() - started) / 60), flush=True)
    jl.close()
    lf.close()
    shutil.rmtree(tmp_root, ignore_errors=True)

    ok = [r for r in results if r.get("status") in ("ok", "no-traditional")]
    t, v3_sum, v3_n = tables(ok)
    ok_repos = {r["repo"] for r in ok}
    sample = draw_sample([x for x in all_rows if x["repo"] in ok_repos])
    with open(os.path.join(a.out_dir, "sample.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SAMPLE_COLS, extrasaction="ignore")
        w.writeheader()
        for i, x in enumerate(sample, 1):
            w.writerow(dict(x, n=i))
    summary = {
        "verdicts": grade(t, v3_sum, v3_n), "tables": t,
        "version": VERSION, "repos_url": REPOS_URL, "repos_sha256": hashlib.sha256(raw).hexdigest(),
        "prereg_sha256": prereg_sha, "opencc_tag": OPENCC_TAG, "opencc_sha256": dict_hashes,
        "phrase_keys": len(phrases.table), "mainland_terms": n_flag, "s_size": len(s_set),
        "sample_size": len(sample),
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
