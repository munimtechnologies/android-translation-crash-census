#!/usr/bin/env python3
# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Simplified Chinese characters in Traditional Chinese app-store listings (pre-registered).

Held-out test of the hanzi-leak detector. For every repository in hidden-chars/repos.txt,
reads the store-listing text files at HEAD (fastlane/metadata/android, play/listings,
play/release-notes, top-level metadata) and counts the lines of Traditional Chinese listings
(zh-TW, zh-HK, zh-MO, zh-Hant) that contain a Simplified-only character, with the character
sets and detector of hanzi_leak.py (imported unchanged). Writes a deterministic hand-check
sample for the precision prediction. See PREREG.md.

Made with AI agents by MV2 of Munim, Inc. Standard library only; needs git and hanzi_leak.py
(downloaded from the census repository during setup).
"""
import argparse
import collections
import concurrent.futures
import csv
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import urllib.request

import hanzi_leak as hl

VERSION = "0.1.0"
BASE = hl.BASE
REPOS_URL = BASE + "hidden-chars/repos.txt"
PREREG_URL = BASE + "hanzi-meta/PREREG.md"
PREREG_MARK = "hanzi-meta PREREG v1"
STRINGS_URL = BASE + "hanzi-leak/repos.jsonl"
SPARSE = [
    "**/fastlane/metadata/android/*/*.txt",
    "**/fastlane/metadata/android/*/changelogs/*.txt",
    "**/play/listings/*/*.txt",
    "**/play/release-notes/*/*.txt",
    "/metadata/*/*.txt",
    "/metadata/*/changelogs/*.txt",
]
SELFTEST_REPOS = ("https://github.com/TeamNewPipe/NewPipe", "https://gitlab.com/fdroid/fdroidclient")
ROOT_SUFFIXES = ("fastlane/metadata/android", "play/listings", "play/release-notes")
SOURCE_LOCALES = ("en-us", "en-gb", "en")
HANT_REGIONS = {"tw", "hk", "mo"}
HANS_REGIONS = {"cn", "sg"}

# Pre-registered thresholds (PREREG.md).
M1_MIN_SAMPLE = 20
SAMPLE_PER_REPO = 2
SAMPLE_SIZE = 60
M2_GATE_UNITS = 2000
M2_GATE_REPOS = 50
M2_SHARE_DEN = 10          # repos_flagged * 10 >= repos
M3_MIN_GROUP = 10


def locale_group(name):
    """'hant' or 'hans' for a Chinese listing folder name, else None (plain zh -> None)."""
    parts = name.replace("_", "-").lower().split("-")
    if parts[0] != "zh" or len(parts) == 1:
        return None
    sub = parts[1:]
    if "hant" in sub:
        return "hant"
    if "hans" in sub:
        return "hans"
    if any(s in HANT_REGIONS for s in sub):
        return "hant"
    if any(s in HANS_REGIONS for s in sub):
        return "hans"
    return None


def is_root(rel):
    """True if a folder path (relative, '/'-separated) is a listing root."""
    return rel == "metadata" or any(rel == s or rel.endswith("/" + s) for s in ROOT_SUFFIXES)


def file_kind(root_rel, rel_file):
    name = rel_file.rsplit("/", 1)[-1].lower().replace("-", "_")
    if root_rel == "play/release-notes" or root_rel.endswith("/play/release-notes"):
        return "changelog"
    if rel_file.startswith("changelogs/"):
        return "changelog"
    if name == "title.txt":
        return "title"
    if name == "short_description.txt":
        return "short_description"
    if name == "full_description.txt":
        return "full_description"
    return "other"


def read_text(path):
    """(text, had_bad_bytes)."""
    with open(path, "rb") as f:
        raw = f.read()
    try:
        return raw.decode("utf-8"), False
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace"), True


def locale_files(locale_path):
    """Relative names of *.txt directly in a locale folder and in its changelogs/ folder."""
    out = []
    for fn in sorted(os.listdir(locale_path)):
        p = os.path.join(locale_path, fn)
        if os.path.isfile(p) and fn.lower().endswith(".txt"):
            out.append(fn)
    ch = os.path.join(locale_path, "changelogs")
    if os.path.isdir(ch):
        for fn in sorted(os.listdir(ch)):
            if os.path.isfile(os.path.join(ch, fn)) and fn.lower().endswith(".txt"):
                out.append("changelogs/" + fn)
    return out


def pick_locale(dirs, choices):
    """First folder (by preference list of lowercase names/predicates) present in dirs."""
    low = {d.replace("_", "-").lower(): d for d in dirs}
    for c in choices:
        if callable(c):
            hits = sorted(d for k, d in low.items() if c(k))
            if hits:
                return hits[0]
        elif c in low:
            return low[c]
    return None


def scan_root(root_path, root_rel, s_set, t_set):
    """Count units and flags in one listing root. Returns a counts dict with rows."""
    out = {"units": collections.Counter(), "flagged": collections.Counter(),
           "kind_units": collections.Counter(), "kind_flagged": collections.Counter(),
           "bad_files": 0, "rows": []}
    dirs = sorted(d for d in os.listdir(root_path) if os.path.isdir(os.path.join(root_path, d)))
    src_dir = pick_locale(dirs, SOURCE_LOCALES)
    hans_dir = pick_locale(dirs, ("zh-cn", lambda k: locale_group(k) == "hans" and "hans" in
                                  k.split("-"), "zh-sg"))
    charset = {"hant": s_set, "hans": t_set}
    cache = {}

    def load(d, rel):
        if (d, rel) not in cache:
            p = os.path.join(root_path, d, *rel.split("/")) if d else None
            if p and os.path.isfile(p):
                cache[(d, rel)] = read_text(p)
            else:
                cache[(d, rel)] = None
        return cache[(d, rel)]

    for d in dirs:
        g = locale_group(d)
        if not g:
            continue
        for rel in locale_files(os.path.join(root_path, d)):
            got = load(d, rel)
            if got is None:
                continue
            text, bad = got
            if bad:
                out["bad_files"] += 1
            src = load(src_dir, rel) if src_dir else None
            src_text = src[0] if src else ""
            kind = file_kind(root_rel, rel)
            for n, line in enumerate(text.splitlines(), 1):
                line = line.strip()
                if not line or not hl.has_han(line):
                    continue
                out["units"][g] += 1
                out["kind_units"][g + ":" + kind] += 1
                chars = hl.foreign(line, src_text, charset[g])
                if not chars:
                    continue
                out["flagged"][g] += 1
                out["kind_flagged"][g + ":" + kind] += 1
                available = identical = False
                if g == "hant" and hans_dir:
                    other = load(hans_dir, rel)
                    if other is not None:
                        available = True
                        identical = line in {x.strip() for x in other[0].splitlines()}
                out["rows"].append({
                    "group": g, "path": "/".join(x for x in (root_rel, d, rel) if x),
                    "line": n, "kind": kind, "chars": "".join(chars),
                    "other_dir": hans_dir if available else "", "available": available,
                    "identical": identical, "text": line[:300]})
    return out


def scan_listings(root):
    """Yield (absolute path, relative path) of every listing root under a checkout."""
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
        if rel != "." and is_root(rel):
            yield dirpath, rel


def scan_checkout(root, s_set, t_set):
    total = {"units": collections.Counter(), "flagged": collections.Counter(),
             "kind_units": collections.Counter(), "kind_flagged": collections.Counter(),
             "bad_files": 0, "roots": 0, "rows": []}
    for path, rel in scan_listings(root):
        r = scan_root(path, rel, s_set, t_set)
        total["roots"] += 1
        for k in ("units", "flagged", "kind_units", "kind_flagged"):
            total[k].update(r[k])
        total["bad_files"] += r["bad_files"]
        total["rows"] += r["rows"]
    return total


def process_repo(url, tmp_root, s_set, t_set):
    d = tempfile.mkdtemp(dir=tmp_root)
    res = {"repo": url, "status": "ok"}
    t0 = time.time()
    try:
        s = os.path.join(d, "s")
        r = hl.git(["clone", "--quiet", "--depth", "1", "--filter=blob:none", "--no-checkout",
                    "--single-branch", url, s])
        if r.returncode != 0:
            res.update(status="clone-failed", error=(r.stderr.strip().splitlines() or [""])[-1][:200])
            return res
        hl.git(["-C", s, "sparse-checkout", "set", "--no-cone"] + SPARSE)
        branch = hl.git(["-C", s, "symbolic-ref", "--short", "HEAD"]).stdout.strip()
        hl.git(["-C", s, "checkout", "--quiet"] + ([branch] if branch else []))
        res["head"] = hl.git(["-C", s, "rev-parse", "HEAD"]).stdout.strip()
        res.update(scan_checkout(s, s_set, t_set))
        if not sum(res["units"].values()):
            res["status"] = "no-chinese-listing"
        return res
    except Exception as e:  # keep going; record what broke
        res.update(status="error", error=repr(e)[:200])
        return res
    finally:
        res["seconds"] = round(time.time() - t0, 1)
        shutil.rmtree(d, ignore_errors=True)


def sample_key(repo, path, line):
    return hashlib.sha256(("%s|%s|%d" % (repo, path, line)).encode("utf-8")).hexdigest()


def draw_sample(rows):
    """PREREG sample: per repo first 2 by key, then first 60 of those by key."""
    by_repo = collections.defaultdict(list)
    for x in rows:
        if x["group"] == "hant":
            by_repo[x["repo"]].append(x)
    kept = []
    for repo in sorted(by_repo):
        rs = sorted(by_repo[repo], key=lambda x: sample_key(x["repo"], x["path"], x["line"]))
        kept += rs[:SAMPLE_PER_REPO]
    kept.sort(key=lambda x: sample_key(x["repo"], x["path"], x["line"]))
    return kept[:SAMPLE_SIZE]


def grade_m1(labels):
    """labels: list of label strings for the sample, in order."""
    n = len(labels)
    if n < M1_MIN_SAMPLE:
        return "NOT TESTABLE"
    defects = sum(1 for x in labels if x == "defect")
    return "HELD" if defects * 5 >= n * 4 else "FAILED"


def grade_m2(repos, units, repos_flagged):
    if units < M2_GATE_UNITS or repos < M2_GATE_REPOS:
        return "NOT TESTABLE (gate)"
    return "HELD" if repos_flagged * M2_SHARE_DEN >= repos else "FAILED"


def m3_table(listing, strings):
    """listing: {repo: (hant_units, hant_flagged)}; strings: {repo: (hant_units, hant_flagged)}."""
    t = {"strings_flagged": {"repos": 0, "listing_flagged": 0},
         "strings_clean": {"repos": 0, "listing_flagged": 0}}
    for repo, (lu, lf) in listing.items():
        if not lu or repo not in strings or not strings[repo][0]:
            continue
        g = "strings_flagged" if strings[repo][1] else "strings_clean"
        t[g]["repos"] += 1
        t[g]["listing_flagged"] += 1 if lf else 0
    return t


def grade_m3(t):
    a, b = t["strings_flagged"], t["strings_clean"]
    if a["repos"] < M3_MIN_GROUP or b["repos"] < M3_MIN_GROUP:
        return "NOT TESTABLE"
    return ("HELD" if a["listing_flagged"] * b["repos"] > b["listing_flagged"] * a["repos"]
            else "FAILED")


def control(s_set, t_set):
    """Synthetic listing: the detector must fire on 这是设置 in zh-TW and not on 這是設定."""
    d = tempfile.mkdtemp(prefix="hanzi-meta-control-")
    try:
        root = os.path.join(d, "fastlane", "metadata", "android")
        for loc, text in (("en-US", "Settings\n"), ("zh-TW", "这是设置\n這是設定\n"),
                          ("zh-CN", "这是设置\n")):
            os.makedirs(os.path.join(root, loc))
            with open(os.path.join(root, loc, "full_description.txt"), "w", encoding="utf-8") as f:
                f.write(text)
        r = scan_checkout(d, s_set, t_set)
        rows = r["rows"]
        return (r["units"]["hant"] == 2 and r["flagged"]["hant"] == 1 and len(rows) == 1
                and rows[0]["chars"] == "设这" and rows[0]["identical"] is True)
    finally:
        shutil.rmtree(d, ignore_errors=True)


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


def load_strings(path=None):
    """hanzi-leak per-repo Traditional counts: {repo: (units, flagged)} or None."""
    try:
        if path:
            with open(path, "rb") as f:
                raw = f.read()
        else:
            with urllib.request.urlopen(STRINGS_URL, timeout=120) as r:
                raw = r.read()
    except OSError:
        return None, None
    out = {}
    for line in raw.decode("utf-8").splitlines():
        if line.strip():
            x = json.loads(line)
            out[x["repo"]] = (x.get("units", {}).get("hant", 0), x.get("flagged", {}).get("hant", 0))
    return out, hashlib.sha256(raw).hexdigest()


ROW_COLS = ["repo", "head", "group", "path", "line", "kind", "chars", "other_dir", "available",
            "identical", "text"]
SAMPLE_COLS = ["sample", "repo", "head", "path", "line", "kind", "chars", "text", "label", "note"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--repos", help="local repos.txt instead of downloading")
    ap.add_argument("--dicts", help="local folder with the OpenCC files instead of downloading")
    ap.add_argument("--strings", help="local hanzi-leak repos.jsonl instead of downloading")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--budget-minutes", type=float, default=200)
    ap.add_argument("--prereg-wait-minutes", type=float, default=45)
    ap.add_argument("--skip-prereg-check", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    started = time.time()
    with open(hl.__file__, "rb") as f:
        hl_sha = hashlib.sha256(f.read()).hexdigest()
    (s_set, t_set), dict_hashes = hl.load_dicts(a.out_dir, a.dicts)
    print("hanzi_meta %s (hanzi_leak %s): S %d, T %d" % (VERSION, hl.VERSION, len(s_set),
                                                        len(t_set)), flush=True)
    if not hl.control(s_set, t_set) or not control(s_set, t_set):
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

    tmp_root = tempfile.mkdtemp(prefix="hanzi-meta-")
    selftest = {}
    for u in SELFTEST_REPOS:
        r = process_repo(u, tmp_root, s_set, t_set)
        selftest[u] = {"status": r["status"], "roots": r.get("roots", 0),
                       "units": dict(r.get("units", {}))}
    print("selftest", json.dumps(selftest), flush=True)
    if not any(v["roots"] for v in selftest.values()):
        print("selftest found no listing folder; clone method broken, stopping", file=sys.stderr)
        return 3
    deadline = time.time() + a.budget_minutes * 60
    results, skipped, rows = [], [], []
    jl = open(os.path.join(a.out_dir, "repos.jsonl"), "w", encoding="utf-8")

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
                "error": r.get("error"), "seconds": r.get("seconds"), "roots": r.get("roots", 0),
                "units": dict(r.get("units", {})), "flagged": dict(r.get("flagged", {})),
                "kind_units": dict(r.get("kind_units", {})),
                "kind_flagged": dict(r.get("kind_flagged", {})),
                "bad_files": r.get("bad_files", 0)}, ensure_ascii=False, sort_keys=True) + "\n")
            for row in r.get("rows", []):
                rows.append(dict(row, repo=r["repo"], head=r.get("head", "")))
            if n % 200 == 0:
                jl.flush()
                print("%d/%d done, %.0f min" % (n, len(repos), (time.time() - started) / 60),
                      flush=True)
    jl.close()
    shutil.rmtree(tmp_root, ignore_errors=True)

    with open(os.path.join(a.out_dir, "flagged.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ROW_COLS)
        w.writeheader()
        for row in rows:
            w.writerow({k: row[k] for k in ROW_COLS})
    sample = draw_sample(rows)
    with open(os.path.join(a.out_dir, "sample.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SAMPLE_COLS)
        w.writeheader()
        for i, x in enumerate(sample, 1):
            w.writerow({"sample": i, "repo": x["repo"], "head": x["head"], "path": x["path"],
                        "line": x["line"], "kind": x["kind"], "chars": x["chars"],
                        "text": x["text"], "label": "", "note": ""})

    ok = [r for r in results if r.get("status") in ("ok", "no-chinese-listing")]
    tables = {}
    for g in ("hant", "hans"):
        w = [r for r in ok if r.get("units", {}).get(g)]
        g_rows = [x for x in rows if x["group"] == g]
        kinds = collections.Counter()
        kflag = collections.Counter()
        for r in w:
            for k, v in r.get("kind_units", {}).items():
                if k.startswith(g + ":"):
                    kinds[k.split(":", 1)[1]] += v
            for k, v in r.get("kind_flagged", {}).items():
                if k.startswith(g + ":"):
                    kflag[k.split(":", 1)[1]] += v
        tables[g] = {"repos": len(w), "units": sum(r["units"][g] for r in w),
                     "flagged": sum(r["flagged"].get(g, 0) for r in w),
                     "repos_flagged": sum(1 for r in w if r["flagged"].get(g)),
                     "available": sum(1 for x in g_rows if x["available"]),
                     "identical": sum(1 for x in g_rows if x["identical"]),
                     "kind_units": dict(kinds), "kind_flagged": dict(kflag)}
    strings, strings_sha = load_strings(a.strings)
    listing = {r["repo"]: (r.get("units", {}).get("hant", 0), r.get("flagged", {}).get("hant", 0))
               for r in ok}
    if strings is None:
        m3 = None
        m3_verdict = "NOT TESTABLE (hanzi-leak repos.jsonl not available)"
    else:
        m3 = m3_table(listing, strings)
        m3_verdict = grade_m3(m3)
    tables["m3"] = m3
    h = tables["hant"]
    verdicts = {
        "M1": "PENDING HAND CHECK (sample of %d)" % len(sample) if len(sample) >= M1_MIN_SAMPLE
              else "NOT TESTABLE",
        "M2": grade_m2(h["repos"], h["units"], h["repos_flagged"]),
        "M3": m3_verdict,
    }
    summary = {
        "verdicts": verdicts, "tables": tables, "sample_size": len(sample),
        "version": VERSION, "hanzi_leak_version": hl.VERSION, "hanzi_leak_sha256": hl_sha,
        "repos_url": REPOS_URL, "repos_sha256": hashlib.sha256(raw).hexdigest(),
        "strings_url": STRINGS_URL, "strings_sha256": strings_sha,
        "prereg_sha256": prereg_sha, "opencc_tag": hl.OPENCC_TAG, "opencc_sha256": dict_hashes,
        "s_size": len(s_set), "t_size": len(t_set),
        "repos_listed": len(repos), "repos_not_started": len(skipped),
        "status_counts": dict(collections.Counter(r["status"] for r in results)),
        "listing_roots": sum(r.get("roots", 0) for r in results),
        "bad_files": sum(r.get("bad_files", 0) for r in results),
        "positive_control": True, "selftest": selftest, "minutes": round((time.time() - started) / 60, 1),
    }
    with open(os.path.join(a.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps(verdicts), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
