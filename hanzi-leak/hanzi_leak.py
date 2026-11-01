#!/usr/bin/env python3
# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Simplified Chinese characters in Traditional Chinese Android translations (pre-registered).

For every repository in hidden-chars/repos.txt (the F-Droid source repositories of the census),
reads the Android string resources at HEAD and, for each Traditional Chinese translation
(values-zh-rTW, -rHK, -rMO, values-b+zh+Hant...), counts the translated strings that contain a
character used only in Simplified Chinese (这, 设, 发 ...), and, the other way round, Simplified
translations (values-zh-rCN, -rSG, values-b+zh+Hans...) holding a Traditional-only character.
Each flagged Traditional string is compared with the same string in the app's Simplified file,
to see whether it is a copy of it. See PREREG.md for the predictions and how they are graded.

The character sets come from OpenCC's dictionaries (Apache-2.0) at a pinned tag. Same corpus,
clone method and file rules as cyrillic_leak.py 0.1.0, whose helpers are copied here so the
script stands alone. Needs git.

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
PREREG_URL = BASE + "hanzi-leak/PREREG.md"
PREREG_MARK = "hanzi-leak PREREG v1"
OPENCC_TAG = "ver.1.4.2"
OPENCC_URL = "https://raw.githubusercontent.com/BYVoid/OpenCC/%s/data/dictionary/" % OPENCC_TAG
DICTS = ("STCharacters.txt", "TSCharacters.txt", "TWVariants.txt", "HKVariants.txt")
SPARSE = ["**/res/values*/*.xml"]

# Pre-registered thresholds (PREREG.md).
GATE_UNITS = 20000
GATE_REPOS = 100
P1_SHARE_DEN = 10          # P1: repos_flagged * 10 >= repos
P2_MIN_REPOS = 10
P4_GATE_UNITS = 2000
P4_GATE_REPOS = 20

# Android \uXXXX escapes (built without a literal escape sequence in this file).
_U_ESC = re.compile(r"(?<!\\)\\" + "u" + r"([0-9A-Fa-f]{4})")
_ZH_REGION = re.compile(r"^values-zh(?:-r([A-Z]{2}))?$")
_ZH_BCP = re.compile(r"^values-b\+zh((?:\+[A-Za-z0-9]+)*)$")
HANT_REGIONS = {"tw", "hk", "mo"}
HANS_REGIONS = {"cn", "sg"}


def decode_android(text):
    return _U_ESC.sub(lambda m: chr(int(m.group(1), 16)), text)


def zh_group(dirname):
    """'hant', 'hans' or 'plain' for a Chinese values-* folder, else None."""
    m = _ZH_REGION.match(dirname)
    if m:
        region = m.group(1)
        if region is None:
            return "plain"
        region = region.lower()
        if region in HANT_REGIONS:
            return "hant"
        if region in HANS_REGIONS:
            return "hans"
        return None
    m = _ZH_BCP.match(dirname)
    if m:
        subtags = [s.lower() for s in m.group(1).split("+") if s]
        if "hant" in subtags:
            return "hant"
        if "hans" in subtags:
            return "hans"
        if any(s in HANT_REGIONS for s in subtags):
            return "hant"
        if any(s in HANS_REGIONS for s in subtags):
            return "hans"
        return "plain"
    return None


def primary_rank(dirname, want):
    """Sort key choosing the folder a flagged string is compared with (lower is preferred)."""
    g = zh_group(dirname)
    if want == "hans":
        if dirname == "values-zh-rCN":
            return (0, dirname)
        if g == "hans" and dirname != "values-zh-rSG":
            return (1, dirname)
        if dirname == "values-zh-rSG":
            return (2, dirname)
        if g == "plain":
            return (3, dirname)
        return None
    if dirname == "values-zh-rTW":
        return (0, dirname)
    if dirname == "values-zh-rHK":
        return (1, dirname)
    if g == "hant":
        return (2, dirname)
    return None


def is_han(c):
    o = ord(c)
    return (0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF or 0xF900 <= o <= 0xFAFF
            or 0x20000 <= o <= 0x3134F)


def has_han(text):
    return any(is_han(c) for c in text)


def parse_dict(text):
    """OpenCC dictionary text -> {key: [values]}; single-character keys only."""
    out = {}
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        key = parts[0].strip()
        vals = [v for v in parts[1].strip().split(" ") if v]
        if len(key) == 1 and vals:
            out[key] = vals
    return out


def build_sets(st, ts, tw, hk):
    """(S, T): Simplified-only and Traditional-only characters (PREREG.md, "Character sets")."""
    st_vals = {v for vs in st.values() for v in vs}
    ts_vals = {v for vs in ts.values() for v in vs}
    regional = {v for d in (tw, hk) for vs in d.values() for v in vs}
    s = {k for k in st if k not in st_vals and k not in ts and k not in regional}
    t = {k for k in ts if k not in ts_vals and k not in st}
    return s, t


def foreign(text, source_text, charset):
    """Characters of `text` in `charset` that the source string doesn't contain."""
    return sorted({c for c in text if c in charset and c not in source_text})


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
            "source_han": collections.Counter(), "plain": collections.Counter(),
            "parse_failed": 0, "simplified_dirs": 0, "rows": []}


def scan_res_dir(dirpath, dirnames, s_set, t_set):
    out = new_counts()
    groups = {}
    for d in sorted(dirnames):
        g = zh_group(d)
        if g:
            groups.setdefault(g, []).append(d)
    if not groups:
        return out
    out["simplified_dirs"] = len(groups.get("hans", [])) + len(groups.get("plain", []))
    prim = {}
    for want in ("hans", "hant"):
        ranked = sorted(r for r in (primary_rank(d, want) for d in dirnames) if r)
        prim[want] = ranked[0][1] if ranked else None
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

    charset = {"hant": s_set, "hans": t_set}
    other = {"hant": "hans", "hans": "hant"}
    for g in ("hant", "hans", "plain"):
        for d in groups.get(g, []):
            for fn in sorted(os.listdir(os.path.join(dirpath, d))):
                if not fn.endswith(".xml") or not os.path.isfile(os.path.join(dirpath, "values", fn)):
                    continue
                source, target = load("values", fn), load(d, fn)
                if not source or not target:
                    continue
                for key, i, t, src in units(source, target):
                    if g == "plain":
                        out["plain"]["units"] += 1
                        if foreign(t, src, s_set):
                            out["plain"]["with_s"] += 1
                        if foreign(t, src, t_set):
                            out["plain"]["with_t"] += 1
                        continue
                    out["units"][g] += 1
                    if has_han(src):
                        out["source_han"][g] += 1
                    chars = foreign(t, src, charset[g])
                    if not chars:
                        continue
                    out["flagged"][g] += 1
                    od = prim[other[g]]
                    o = item(load(od, fn), key, i) if od else None
                    out["rows"].append({
                        "group": g, "locale_dir": d, "file": fn, "key": key, "index": i,
                        "chars": "".join(chars), "other_dir": od if o is not None else "",
                        "other_available": o is not None,
                        "other_identical": o is not None and o.strip() == t.strip(),
                        "has_own": bool(foreign(t, src, charset[other[g]])),
                        "text": t.strip()[:200]})
    return out


def scan_strings(root, s_set, t_set):
    total = new_counts()
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        if os.path.basename(dirpath) != "res" or "values" not in dirnames:
            continue
        r = scan_res_dir(dirpath, dirnames, s_set, t_set)
        rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
        for k in ("units", "flagged", "source_han", "plain"):
            total[k].update(r[k])
        total["parse_failed"] += r["parse_failed"]
        total["simplified_dirs"] += r["simplified_dirs"]
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


def process_repo(url, tmp_root, s_set, t_set):
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
        res.update(scan_strings(s, s_set, t_set))
        if not sum(res["units"].values()) and not res["plain"].get("units"):
            res["status"] = "no-chinese"
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


def p2_counts(rows):
    """(available, identical) over flagged Traditional rows of one repository."""
    a = sum(1 for x in rows if x["group"] == "hant" and x["other_available"])
    i = sum(1 for x in rows if x["group"] == "hant" and x["other_identical"])
    return a, i


def group_totals(results, g, pick=None):
    w = [r for r in results if r.get("units", {}).get(g) and (pick is None or pick(r))]
    return {"repos": len(w), "units": sum(r["units"][g] for r in w),
            "flagged": sum(r["flagged"].get(g, 0) for r in w),
            "repos_flagged": sum(1 for r in w if r["flagged"].get(g))}


def tables(results):
    t = {}
    for g in ("hant", "hans"):
        t[g] = group_totals(results, g)
        rows = [x for r in results for x in r.get("rows", []) if x["group"] == g]
        t[g]["source_han_units"] = sum(r.get("source_han", {}).get(g, 0) for r in results
                                       if r.get("units", {}).get(g))
        t[g]["other_available"] = sum(1 for x in rows if x["other_available"])
        t[g]["other_identical"] = sum(1 for x in rows if x["other_identical"])
        t[g]["has_own"] = sum(1 for x in rows if x["has_own"])
    t["hant_only"] = group_totals(results, "hant", lambda r: not r.get("simplified_dirs"))
    t["hant_with_simplified"] = group_totals(results, "hant", lambda r: r.get("simplified_dirs"))
    shares = []
    for r in results:
        a, i = p2_counts(r.get("rows", []))
        if a:
            shares.append(fractions.Fraction(i, a))
    total = sum(shares, fractions.Fraction(0))
    t["p2"] = {"repos": len(shares), "sum_of_shares": "%d/%d" % (total.numerator, total.denominator),
               "mean_share": round(float(total / len(shares)), 4) if shares else None}
    plain = collections.Counter()
    for r in results:
        plain.update(r.get("plain", {}))
    t["plain_zh"] = {"repos": sum(1 for r in results if r.get("plain", {}).get("units")),
                     "units": plain["units"], "with_s": plain["with_s"], "with_t": plain["with_t"]}
    return t, total, len(shares)


def gated(x, units=GATE_UNITS, repos=GATE_REPOS):
    return x["units"] >= units and x["repos"] >= repos


def grade(t, p2_sum, p2_n):
    """Pre-registered verdicts (PREREG.md). Whole numbers and exact fractions only."""
    hant, hans = t["hant"], t["hans"]
    if not gated(hant):
        return {p: "NOT TESTABLE (gate)" for p in ("P1", "P2", "P3", "P4")}
    v = {}
    v["P1"] = "HELD" if hant["repos_flagged"] * P1_SHARE_DEN >= hant["repos"] else "FAILED"
    if p2_n < P2_MIN_REPOS:
        v["P2"] = "NOT TESTABLE"
    else:
        v["P2"] = "HELD" if 2 * p2_sum >= p2_n else "FAILED"
    if not gated(hans):
        v["P3"] = "NOT TESTABLE (gate)"
    else:
        v["P3"] = ("HELD" if hans["flagged"] * hant["units"] < hant["flagged"] * hans["units"]
                   else "FAILED")
    only, both = t["hant_only"], t["hant_with_simplified"]
    if not gated(only, P4_GATE_UNITS, P4_GATE_REPOS) or not both["units"]:
        v["P4"] = "NOT TESTABLE (gate)"
    else:
        v["P4"] = ("HELD" if only["flagged"] * both["units"] < both["flagged"] * only["units"]
                   else "FAILED")
    return v


def control(s_set, t_set):
    """The detector must fire on known cases and stay quiet on clean ones (positive control)."""
    must_s = "这设发说"
    must_t = "這設發說"
    never_s = "台只干床才吃峰後這"
    never_t = "这台只"
    if not all(c in s_set for c in must_s) or not all(c in t_set for c in must_t):
        return False
    if any(c in s_set for c in never_s) or any(c in t_set for c in never_t):
        return False
    cases = [
        ("這是設定", "Settings", s_set, []),
        ("这是设置", "Settings", s_set, ["设", "这"]),
        ("臺灣的床", "Bed", s_set, []),
        ("这是设置", "Settings", t_set, []),
        ("這是設定", "Settings", t_set, ["設", "這"]),
        ("这", "这", s_set, []),  # the source has it too
    ]
    return all(foreign(text, src, cs) == sorted(want) for text, src, cs, want in cases)


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
    """Download (or read) the four OpenCC dictionaries; copy them and their hashes to out_dir."""
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
    st, ts, tw, hk = (parse_dict(texts[n]) for n in DICTS)
    return build_sets(st, ts, tw, hk), hashes


ROW_COLS = ["repo", "head", "group", "res_dir", "locale_dir", "file", "key", "index", "chars",
            "other_dir", "other_available", "other_identical", "has_own", "text"]


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
    (s_set, t_set), dict_hashes = load_dicts(a.out_dir, a.dicts)
    print("hanzi_leak %s: S %d characters, T %d characters" % (VERSION, len(s_set), len(t_set)),
          flush=True)
    if not control(s_set, t_set):
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

    tmp_root = tempfile.mkdtemp(prefix="hanzi-")
    selftest = {}
    for u in ("https://github.com/TeamNewPipe/NewPipe", "https://gitlab.com/fdroid/fdroidclient"):
        r = process_repo(u, tmp_root, s_set, t_set)
        selftest[u] = {"status": r["status"], "units": dict(r.get("units", {}))}
    print("selftest", json.dumps(selftest), flush=True)
    if not any(v["units"].get("hant") and v["units"].get("hans") for v in selftest.values()):
        print("selftest found no Traditional and Simplified strings; clone method broken, stopping",
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
        return process_repo(u, tmp_root, s_set, t_set)

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
                "source_han": dict(r.get("source_han", {})), "plain": dict(r.get("plain", {})),
                "simplified_dirs": r.get("simplified_dirs", 0),
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

    ok = [r for r in results if r.get("status") in ("ok", "no-chinese")]
    t, p2_sum, p2_n = tables(ok)
    summary = {
        "verdicts": grade(t, p2_sum, p2_n), "tables": t,
        "version": VERSION, "repos_url": REPOS_URL, "repos_sha256": hashlib.sha256(raw).hexdigest(),
        "prereg_sha256": prereg_sha, "opencc_tag": OPENCC_TAG, "opencc_sha256": dict_hashes,
        "s_size": len(s_set), "t_size": len(t_set),
        "repos_listed": len(repos), "repos_not_started": len(skipped),
        "status_counts": dict(collections.Counter(r["status"] for r in results)),
        "parse_failed_files": sum(r.get("parse_failed", 0) for r in results),
        "positive_control": True, "selftest": selftest,
        "minutes": round((time.time() - started) / 60, 1),
    }
    with open(os.path.join(a.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1, sort_keys=True)
    with open(os.path.join(a.out_dir, "s_set.txt"), "w", encoding="utf-8") as f:
        f.write("".join(sorted(s_set)) + "\n")
    with open(os.path.join(a.out_dir, "t_set.txt"), "w", encoding="utf-8") as f:
        f.write("".join(sorted(t_set)) + "\n")
    print(json.dumps(summary["verdicts"]), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
