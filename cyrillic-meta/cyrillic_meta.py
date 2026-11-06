#!/usr/bin/env python3
# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Letters from another alphabet in Cyrillic app-store listings (pre-registered).

Held-out test of the cyrillic-leak detector. For every repository in hidden-chars/repos.txt,
reads the store-listing text files at HEAD (fastlane/metadata/android, play/listings,
play/release-notes, top-level metadata) and, for each Ukrainian, Belarusian, Russian, Bulgarian,
Serbian (Cyrillic) and Macedonian listing, counts the lines that contain a letter the language's
alphabet doesn't have (Russian ы, э, ё, ъ in Ukrainian; и, щ, ъ in Belarusian; ...). The letter
table and the detector are cyrillic_leak.py 0.1.0's, imported unchanged; the listing walker is
hanzi_meta.py 0.1.0's, imported unchanged. Writes a deterministic hand-check sample. See PREREG.md.

Made with AI agents by MV2 of Munim, Inc. Standard library only; needs git, cyrillic_leak.py,
hanzi_meta.py and hanzi_leak.py (downloaded from the census repository during setup).
"""
import argparse
import collections
import concurrent.futures
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

import cyrillic_leak as cl
import hanzi_meta as hm

VERSION = "0.1.0"
BASE = cl.BASE
REPOS_URL = BASE + "hidden-chars/repos.txt"
PREREG_URL = BASE + "cyrillic-meta/PREREG.md"
PREREG_MARK = "cyrillic-meta PREREG v1"
STRINGS_URL = BASE + "cyrillic-leak/repos.jsonl"
SELFTEST_REPOS = ("https://github.com/TeamNewPipe/NewPipe", "https://gitlab.com/fdroid/fdroidclient")
LANGS = tuple(cl.FOREIGN)  # uk be ru bg sr mk
PAIR = ("uk", "be")         # the languages C3 pools

# Pre-registered thresholds (PREREG.md).
GATE_REPOS_READ = 4000
SAMPLE_SIZE = 40
C1_MIN_SAMPLE = 15
C2_GATE_UNITS = 2000
C2_GATE_REPOS = 50
C2_MIN_REPOS = 10
C3_MIN_GROUP = 10
C4_GATE_UNITS = 300
C4_GATE_REPOS = 10


def listing_lang(name):
    """The language of a listing folder ('uk', 'uk-UA', 'be_BY', 'sr-Cyrl') if Cyrillic, else None."""
    parts = name.replace("_", "-").lower().split("-")
    if parts[0] not in cl.FOREIGN or "latn" in parts[1:]:
        return None
    return parts[0]


def scan_root(root_path, root_rel):
    """Count units and flags in one listing root. Returns a counts dict with rows."""
    out = {"units": collections.Counter(), "flagged": collections.Counter(),
           "kind_units": collections.Counter(), "kind_flagged": collections.Counter(),
           "bad_files": 0, "rows": []}
    dirs = sorted(d for d in os.listdir(root_path) if os.path.isdir(os.path.join(root_path, d)))
    src_dir = hm.pick_locale(dirs, hm.SOURCE_LOCALES)
    src_cache = {}

    def source_text(rel):
        if not src_dir:
            return ""
        if rel not in src_cache:
            p = os.path.join(root_path, src_dir, *rel.split("/"))
            src_cache[rel] = hm.read_text(p)[0] if os.path.isfile(p) else ""
        return src_cache[rel]

    for d in dirs:
        lang = listing_lang(d)
        if not lang:
            continue
        for rel in hm.locale_files(os.path.join(root_path, d)):
            text, bad = hm.read_text(os.path.join(root_path, d, *rel.split("/")))
            if bad:
                out["bad_files"] += 1
            kind = hm.file_kind(root_rel, rel)
            for n, line in enumerate(text.splitlines(), 1):
                line = line.strip()
                if not line or not cl.CYR.search(line):
                    continue
                out["units"][lang] += 1
                out["kind_units"][lang + ":" + kind] += 1
                letters = cl.foreign_letters(lang, line, source_text(rel))
                if not letters:
                    continue
                out["flagged"][lang] += 1
                out["kind_flagged"][lang + ":" + kind] += 1
                out["rows"].append({
                    "lang": lang, "path": "/".join(x for x in (root_rel, d, rel) if x),
                    "line": n, "kind": kind, "letters": "".join(letters),
                    "native": cl.has_native(lang, line), "text": line[:300]})
    return out


def scan_checkout(root):
    total = {"units": collections.Counter(), "flagged": collections.Counter(),
             "kind_units": collections.Counter(), "kind_flagged": collections.Counter(),
             "bad_files": 0, "roots": 0, "rows": []}
    for path, rel in hm.scan_listings(root):
        r = scan_root(path, rel)
        total["roots"] += 1
        for k in ("units", "flagged", "kind_units", "kind_flagged"):
            total[k].update(r[k])
        total["bad_files"] += r["bad_files"]
        total["rows"] += r["rows"]
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
        cl.git(["-C", s, "sparse-checkout", "set", "--no-cone"] + hm.SPARSE)
        branch = cl.git(["-C", s, "symbolic-ref", "--short", "HEAD"]).stdout.strip()
        cl.git(["-C", s, "checkout", "--quiet"] + ([branch] if branch else []))
        res["head"] = cl.git(["-C", s, "rev-parse", "HEAD"]).stdout.strip()
        res.update(scan_checkout(s))
        if not sum(res["units"].values()):
            res["status"] = "no-cyrillic-listing"
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


def sample_key(repo, path, line):
    return hashlib.sha256(("cyrillic-meta v1|%s|%s|%d" % (repo, path, line)).encode("utf-8")).hexdigest()


def draw_sample(rows):
    """PREREG sample: per repository the flagged line with the lowest key, then the first 40 by key."""
    by_repo = collections.defaultdict(list)
    for x in rows:
        by_repo[x["repo"]].append(x)
    kept = [min(rs, key=lambda x: sample_key(x["repo"], x["path"], x["line"]))
            for _, rs in sorted(by_repo.items())]
    kept.sort(key=lambda x: sample_key(x["repo"], x["path"], x["line"]))
    return kept[:SAMPLE_SIZE]


def grade_c1(labels):
    """labels: the hand labels of the sample rows, in order."""
    n = len(labels)
    if n < C1_MIN_SAMPLE:
        return "NOT TESTABLE"
    defects = sum(1 for x in labels if x == "defect")
    return "HELD" if defects * 4 >= n * 3 else "FAILED"


def uk_gated(uk):
    return uk["units"] >= C2_GATE_UNITS and uk["repos"] >= C2_GATE_REPOS


def grade_c2(uk):
    if not uk_gated(uk):
        return "NOT TESTABLE (gate)"
    return "HELD" if uk["repos_flagged"] >= C2_MIN_REPOS else "FAILED"


def c3_table(listing, strings):
    """listing, strings: {repo: (units, flagged)} for uk and be pooled."""
    t = {"strings_flagged": {"repos": 0, "listing_flagged": 0},
         "strings_clean": {"repos": 0, "listing_flagged": 0}}
    for repo in sorted(listing):
        lu, lf = listing[repo]
        if not lu or repo not in strings or not strings[repo][0]:
            continue
        g = "strings_flagged" if strings[repo][1] else "strings_clean"
        t[g]["repos"] += 1
        t[g]["listing_flagged"] += 1 if lf else 0
    return t


def grade_c3(t):
    a, b = t["strings_flagged"], t["strings_clean"]
    if a["repos"] < C3_MIN_GROUP or b["repos"] < C3_MIN_GROUP:
        return "NOT TESTABLE"
    return ("HELD" if a["listing_flagged"] * b["repos"] > b["listing_flagged"] * a["repos"]
            else "FAILED")


def grade_c4(uk, be):
    if not uk_gated(uk) or be["units"] < C4_GATE_UNITS or be["repos"] < C4_GATE_REPOS:
        return "NOT TESTABLE (gate)"
    return "HELD" if be["flagged"] * uk["units"] > uk["flagged"] * be["units"] else "FAILED"


CONTROL_FILES = (
    ("en-US", "full_description.txt", "Settings\n"),
    ("en-US", "short_description.txt", "Keyboard: ы э\n"),
    ("uk", "full_description.txt",
     "Налаштування\n"
     "Выберите файл\n"
     "Plain English line\n"),
    ("uk", "short_description.txt", "Клавіатура: ы э\n"),  # the source has them too
    ("be-BY", "full_description.txt",
     "Настройки "
     "сохранены\n"),
    ("ru-RU", "title.txt", "Привіт\n"),
    ("sr-Latn", "full_description.txt", "Podešavanja ы\n"),
)


def control():
    """Synthetic listing: the detector must flag exactly the three planted lines."""
    d = tempfile.mkdtemp(prefix="cyrillic-meta-control-")
    try:
        root = os.path.join(d, "fastlane", "metadata", "android")
        for loc, fn, text in CONTROL_FILES:
            os.makedirs(os.path.join(root, loc), exist_ok=True)
            with open(os.path.join(root, loc, fn), "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
        r = scan_checkout(d)
        got = [(x["lang"], x["path"], x["line"], x["kind"], x["letters"]) for x in r["rows"]]
        want = [
            ("be", "fastlane/metadata/android/be-BY/full_description.txt", 1, "full_description",
             "и"),
            ("ru", "fastlane/metadata/android/ru-RU/title.txt", 1, "title", "і"),
            ("uk", "fastlane/metadata/android/uk/full_description.txt", 2, "full_description",
             "ы"),
        ]
        return (r["roots"] == 1 and dict(r["units"]) == {"uk": 3, "be": 1, "ru": 1}
                and dict(r["flagged"]) == {"uk": 1, "be": 1, "ru": 1} and got == want)
    finally:
        shutil.rmtree(d, ignore_errors=True)


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


def load_strings(path=None):
    """cyrillic-leak per-repo uk+be string counts: ({repo: (units, flagged)}, sha256) or (None, None)."""
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
            u, f = x.get("units") or {}, x.get("flagged") or {}
            out[x["repo"]] = (sum(u.get(k, 0) for k in PAIR), sum(f.get(k, 0) for k in PAIR))
    return out, hashlib.sha256(raw).hexdigest()


def lang_tables(ok, rows):
    tables = {}
    for g in LANGS:
        w = [r for r in ok if r.get("units", {}).get(g)]
        kinds, kflag = collections.Counter(), collections.Counter()
        for r in w:
            for k, v in r.get("kind_units", {}).items():
                if k.startswith(g + ":"):
                    kinds[k.split(":", 1)[1]] += v
            for k, v in r.get("kind_flagged", {}).items():
                if k.startswith(g + ":"):
                    kflag[k.split(":", 1)[1]] += v
        g_rows = [x for x in rows if x["lang"] == g]
        tables[g] = {"repos": len(w), "units": sum(r["units"][g] for r in w),
                     "flagged": sum(r["flagged"].get(g, 0) for r in w),
                     "repos_flagged": sum(1 for r in w if r["flagged"].get(g)),
                     "native": sum(1 for x in g_rows if x["native"]),
                     "kind_units": dict(kinds), "kind_flagged": dict(kflag)}
    return tables


ROW_COLS = ["repo", "head", "lang", "path", "line", "kind", "letters", "native", "text"]
SAMPLE_COLS = ["sample", "repo", "head", "lang", "path", "line", "kind", "letters", "text",
               "label", "note"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--repos", help="local repos.txt instead of downloading")
    ap.add_argument("--strings", help="local cyrillic-leak repos.jsonl instead of downloading")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--budget-minutes", type=float, default=200)
    ap.add_argument("--prereg-wait-minutes", type=float, default=45)
    ap.add_argument("--skip-prereg-check", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    started = time.time()
    hashes = {}
    for mod in (cl, hm, hm.hl):
        with open(mod.__file__, "rb") as f:
            hashes[os.path.basename(mod.__file__)] = hashlib.sha256(f.read()).hexdigest()
    print("cyrillic_meta %s (cyrillic_leak %s, hanzi_meta %s)" % (VERSION, cl.VERSION, hm.VERSION),
          flush=True)
    if not cl.control() or not control():
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

    tmp_root = tempfile.mkdtemp(prefix="cyrillic-meta-")
    selftest = {}
    for u in SELFTEST_REPOS:
        r = process_repo(u, tmp_root)
        selftest[u] = {"status": r["status"], "roots": r.get("roots", 0),
                       "units": dict(r.get("units", {}))}
    print("selftest", json.dumps(selftest, ensure_ascii=False), flush=True)
    if not any(v["roots"] for v in selftest.values()):
        print("selftest found no listing folder; clone method broken, stopping", file=sys.stderr)
        return 3
    deadline = time.time() + a.budget_minutes * 60
    results, skipped, rows = [], [], []
    jl = open(os.path.join(a.out_dir, "repos.jsonl"), "w", encoding="utf-8")

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
            w.writerow({"sample": i, "repo": x["repo"], "head": x["head"], "lang": x["lang"],
                        "path": x["path"], "line": x["line"], "kind": x["kind"],
                        "letters": x["letters"], "text": x["text"], "label": "", "note": ""})

    ok = [r for r in results if r.get("status") in ("ok", "no-cyrillic-listing")]
    tables = lang_tables(ok, rows)
    strings, strings_sha = load_strings(a.strings)
    listing = {r["repo"]: (sum(r.get("units", {}).get(k, 0) for k in PAIR),
                           sum(r.get("flagged", {}).get(k, 0) for k in PAIR)) for r in ok}
    if strings is None:
        c3, c3_verdict = None, "NOT TESTABLE (cyrillic-leak repos.jsonl not available)"
    else:
        c3 = c3_table(listing, strings)
        c3_verdict = grade_c3(c3)
    tables["c3"] = c3
    if len(ok) < GATE_REPOS_READ:
        verdicts = {p: "NOT TESTABLE (gate: %d repositories read)" % len(ok)
                    for p in ("C1", "C2", "C3", "C4")}
    else:
        verdicts = {
            "C1": ("PENDING HAND CHECK (sample of %d)" % len(sample)
                   if len(sample) >= C1_MIN_SAMPLE else "NOT TESTABLE"),
            "C2": grade_c2(tables["uk"]),
            "C3": c3_verdict,
            "C4": grade_c4(tables["uk"], tables["be"]),
        }
    summary = {
        "verdicts": verdicts, "tables": tables, "sample_size": len(sample),
        "version": VERSION, "module_sha256": hashes,
        "repos_url": REPOS_URL, "repos_sha256": hashlib.sha256(raw).hexdigest(),
        "strings_url": STRINGS_URL, "strings_sha256": strings_sha, "prereg_sha256": prereg_sha,
        "repos_listed": len(repos), "repos_read": len(ok), "repos_not_started": len(skipped),
        "status_counts": dict(collections.Counter(r["status"] for r in results)),
        "listing_roots": sum(r.get("roots", 0) for r in results),
        "bad_files": sum(r.get("bad_files", 0) for r in results),
        "positive_control": True, "selftest": selftest,
        "minutes": round((time.time() - started) / 60, 1),
    }
    with open(os.path.join(a.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps(verdicts), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
