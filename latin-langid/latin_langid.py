#!/usr/bin/env python3
# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Android translation folders that hold another language written in the same alphabet
(pre-registered in latin-langid/PREREG.md before any repository is read).

The earlier locale-mismatch census (same corpus) checked each folder's SCRIPT, so it could not
see Hungarian in values-ast or Italian in values-az: both are Latin script. This census builds
a character n-gram profile (1- to 3-grams, Cavnar & Trenkle 1994 "out-of-place" ranking) for
every language from the corpus itself, then flags a Latin-script folder whose text is much
closer to another, non-related language's profile than to its own.

Same corpus and clone method as locale_mismatch.py 0.1.0 and cyrillic_leak.py 0.1.0, whose
helpers (parse_dir, not_a_language, script_of, clean, _checkout, git, parse_values,
has_values) are imported unchanged (both downloaded from the census repository during setup).
Needs git. Standard library only. Made with AI agents by MV2 of Munim, Inc.
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

import cyrillic_leak as cl
import locale_mismatch as lm

VERSION = "0.1.0"
BASE = cl.BASE
REPOS_URL = BASE + "hidden-chars/repos.txt"
PREREG_URL = BASE + "latin-langid/PREREG.md"
PREREG_MARK = "latin-langid census PREREG v1"
KEY = "latin-langid v1"
SELFTEST_REPOS = lm.SELFTEST_REPOS
THUNDERBIRD = "https://github.com/thunderbird/thunderbird-android"
TB_RES = "feature/mail/message/list/internal/src/main/res"
# Known same-script cases from the thunderbird-android issue #11893 (found by hand, 2026-11-06).
KNOWN = ((TB_RES, "values-ast", "hu"), (TB_RES, "values-az", "it"), (TB_RES, "values-br", "tr"))

# Pre-registered numbers (PREREG.md).
MIN_UNITS = 10
MIN_LETTERS = 100
MAX_LETTERS = 40000
NMAX = 3
DOC_SIZE = 300
PROFILE_SIZE = 400
MIN_PROFILE_REPOS = 30
MARGIN = (9, 10)        # d(holds) * 10 <= d(own group) * 9
CONF = (9, 10)          # dn(holds) <= the 90th percentile of the holds language's own folders
GATE_REPOS_READ = 4000
GATE_PROFILES = 20
S0_PCT = 95
S1_MIN_REPOS = 5
MIN_TESTABLE = 4
SAMPLE_SIZE = 24
H1_MIN = 8

LEGACY_MAP = {"in": "id", "iw": "he", "ji": "yi", "no": "nb", "mo": "ro"}
# Closely related languages: a folder is never flagged for looking like a language in its own
# group (Danish text in values-nb is not counted). Groups are not merged with each other.
CLOSE_GROUPS = ("nb nn da", "sr hr bs sh cnr", "hr sl", "id ms", "cs sk", "es gl ast an",
                "gl pt", "ca oc", "nl af fy li", "de lb gsw", "fil tl", "ga gd", "tr az",
                "it co sc", "pl szl csb", "fr wa", "lv ltg", "en sco")
CLOSE = collections.defaultdict(set)
for _g in CLOSE_GROUPS:
    _s = _g.split()
    for _a in _s:
        CLOSE[_a].update(_s)

_PH = re.compile(r"%(?:\d+\$)?[-#+0,(]*\d*(?:\.\d+)?[a-zA-Z]|\{[^{}]*\}|<[^<>]*>"
                 r"|&[A-Za-z#0-9]+;|https?://\S+|\\[nrtu'\"@?]")


def lang_key(lang, script):
    """'in' -> 'id', ('sr', 'Latn') -> 'sr-Latn'; regions are dropped."""
    lang = LEGACY_MAP.get(lang, lang)
    return lang + "-" + script if script else lang


def base(key):
    return key.split("-")[0]


def close(a, b):
    a, b = base(a), base(b)
    return a == b or b in CLOSE.get(a, ())


def words(text):
    """Lowercased words (runs of letters, with any combining marks) after placeholders, markup,
    entities, URLs and backslash escapes are replaced by spaces."""
    t = unicodedata.normalize("NFC", _PH.sub(" ", text)).lower()
    out, cur = [], []
    for ch in t:
        cat = unicodedata.category(ch)
        if cat.startswith("L") or (cat.startswith("M") and cur):
            cur.append(ch)
        elif cur:
            out.append("".join(cur))
            cur = []
    if cur:
        out.append("".join(cur))
    return out


def ngrams(word, nmax=NMAX):
    p = "_" + word + "_"
    for n in range(1, nmax + 1):
        for i in range(len(p) - n + 1):
            g = p[i:i + n]
            if g != "_":
                yield g


def doc_stats(units, max_letters=MAX_LETTERS):
    """(n-gram Counter, letters, Latin letters) of a list of strings; stops after max_letters."""
    counts = collections.Counter()
    letters = latin = 0
    for u in units:
        for w in words(u):
            for ch in w:
                s = lm.script_of(ch)
                if s:
                    letters += 1
                    if s == "Latin":
                        latin += 1
            counts.update(ngrams(w))
        if letters >= max_letters:
            break
    return counts, letters, latin


def ranked(counts, size):
    return [g for g, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:size]]


def distance(doc, prof_rank, size=PROFILE_SIZE):
    """Cavnar-Trenkle out-of-place distance of a ranked n-gram list from a profile
    ({gram: rank}); a gram missing from the profile costs `size`."""
    d = 0
    for i, g in enumerate(doc):
        r = prof_rank.get(g)
        d += size if r is None else abs(i - r)
    return d


def repo_contrib(by_key):
    """{key: [Counter, ...]} of one repository -> {key: {gram: weight}}: each folder's
    relative frequencies, averaged over the repository's folders of that key (weight 1)."""
    out = {}
    for key, counters in by_key.items():
        acc = {}
        n = len(counters)
        for c in counters:
            total = float(sum(c.values()))
            if not total:
                continue
            for g, v in c.items():
                acc[g] = acc.get(g, 0.0) + v / total / n
        out[key] = acc
    return out


def merge_contrib(glob, contrib):
    for key in sorted(contrib):
        g = glob.setdefault(key, {"repos": 0, "freq": {}})
        g["repos"] += 1
        gf = g["freq"]
        for gram, v in contrib[key].items():
            gf[gram] = gf.get(gram, 0.0) + v


def build_profiles(glob, min_repos=MIN_PROFILE_REPOS, size=PROFILE_SIZE):
    """{key: {gram: rank}} for every key with at least min_repos contributing repositories."""
    out = {}
    for key in sorted(glob):
        d = glob[key]
        if d["repos"] < min_repos:
            continue
        top = sorted(d["freq"].items(), key=lambda kv: (-kv[1], kv[0]))[:size]
        out[key] = {g: i for i, (g, _) in enumerate(top)}
    return out


# ------------------------------------------------------------------ reading a repository

def scan_res_dir(dirpath, dirnames):
    """(folders, source units, parse failures) of one res/ folder. folders: every translation
    folder with at least one translated string (identical copies of the source are skipped)."""
    cache = {}
    failed = [0]

    def load(d, fn):
        if (d, fn) not in cache:
            p = os.path.join(dirpath, d, fn)
            try:
                cache[(d, fn)] = cl.parse_values(p) if os.path.isfile(p) else None
            except (ET.ParseError, ValueError, OSError):
                cache[(d, fn)] = None
                failed[0] += 1
        return cache[(d, fn)]

    folders, src_units = [], set()
    for d in sorted(dirnames):
        p = lm.parse_dir(d)
        if not p or not os.path.isdir(os.path.join(dirpath, d)):
            continue
        lang, region, script = p
        units = []
        for fn in sorted(os.listdir(os.path.join(dirpath, d))):
            if not fn.endswith(".xml") or not os.path.isfile(os.path.join(dirpath, "values", fn)):
                continue
            src, tgt = load("values", fn), load(d, fn)
            if not src or not tgt:
                continue
            for key in sorted(tgt, key=str):
                tl, sl = tgt[key], src.get(key)
                if not tl or not sl:
                    continue
                for i, t in enumerate(tl):
                    t = t.strip()
                    s_item = sl[i].strip() if i < len(sl) and sl[i] else None
                    if not t or (s_item is not None and t == s_item):
                        continue
                    units.append(t)
                    if s_item:
                        src_units.add(s_item)
        if units:
            folders.append({"locale_dir": d, "lang": lang, "region": region or "",
                            "script": script or "", "units": units})
    return folders, sorted(src_units), failed[0]


def scan_tree(root):
    out, failed = [], 0
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        if os.path.basename(dirpath) != "res" or "values" not in dirnames:
            continue
        folders, src, pf = scan_res_dir(dirpath, dirnames)
        failed += pf
        out.append((os.path.relpath(dirpath, root).replace(os.sep, "/"), folders, src))
    return out, failed


def build_records(repo, head, res_folders, min_units=MIN_UNITS, min_letters=MIN_LETTERS):
    """(records, profile contribution, eligibility counts) of one repository. A folder is
    checked when it has min_units translated strings, min_letters letters and at least half of
    its letters are Latin; its code must be a language (values-ua is left to locale-mismatch).
    The repository's source strings (values/) form one extra 'source' record for English."""
    records, by_key, elig, src_all = [], collections.defaultdict(list), collections.Counter(), []
    for rel, folders, src in res_folders:
        sib = sorted({lang_key(f["lang"], f["script"]) for f in folders})
        for f in folders:
            elig["folders"] += 1
            if lm.not_a_language(f["lang"]):
                elig["not_a_language"] += 1
                continue
            key = lang_key(f["lang"], f["script"])
            if base(key) in lm.EXPECT:
                elig["non_latin_language"] += 1   # its script was checked by locale-mismatch
                continue
            counts, letters, latin = doc_stats(f["units"])
            if len(f["units"]) < min_units or letters < min_letters:
                elig["too_small"] += 1
                continue
            if 2 * latin < letters:
                elig["not_latin"] += 1
                continue
            elig["checked"] += 1
            by_key[key].append(counts)
            records.append({"repo": repo, "head": head, "res_dir": rel,
                            "locale_dir": f["locale_dir"], "key": key, "units": len(f["units"]),
                            "letters": letters, "latin": latin, "doc": ranked(counts, DOC_SIZE),
                            "siblings": sib, "ex": [lm.clean(u)[:120] for u in f["units"][:3]]})
        src_all.extend(src)
    src_units = sorted(set(src_all))
    if src_units:
        counts, letters, latin = doc_stats(src_units)
        if len(src_units) >= min_units and letters >= min_letters and 2 * latin >= letters:
            elig["source_checked"] += 1
            by_key["en"].append(counts)
            records.append({"repo": repo, "head": head, "res_dir": "", "locale_dir": "values",
                            "key": "en", "source": True, "units": len(src_units),
                            "letters": letters, "latin": latin, "doc": ranked(counts, DOC_SIZE),
                            "siblings": [], "ex": []})
    return records, repo_contrib(by_key), elig


def process_repo(url, tmp_root):
    d = tempfile.mkdtemp(dir=tmp_root)
    res = {"repo": url, "status": "ok", "records": [], "contrib": {}, "eligible": {}}
    t0 = time.time()
    try:
        s, err = lm._checkout(url, d, cl.SPARSE)
        if not s:
            res.update(status="clone-failed", error=err)
            return res
        if not cl.has_values(s):
            cl.git(["-C", s, "read-tree", "-mu", "HEAD"])
        res["head"] = cl.git(["-C", s, "rev-parse", "HEAD"]).stdout.strip()
        tree, res["parse_failed"] = scan_tree(s)
        recs, contrib, elig = build_records(url, res["head"], tree)
        res.update(records=recs, contrib=contrib, eligible=dict(elig))
        if not elig.get("folders"):
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


# ------------------------------------------------------------------ classifying and grading

def classify_rows(records, profiles, size=PROFILE_SIZE):
    """rows (one per checked, non-source record, in input order) and the 90th-percentile
    thresholds. 'holds' is the closest profile not related to the folder's own language."""
    keys = sorted(profiles)
    dists_by_key = collections.defaultdict(list)
    rows = []
    for rec in records:
        doc = rec["doc"]
        k = len(doc)
        if not k or not keys:
            continue
        dist = {K: distance(doc, profiles[K], size) for K in keys}
        if rec.get("source"):
            if "en" in profiles:
                dists_by_key["en"].append(dist["en"] / float(k * size))
            continue
        own = rec["key"]
        if own in profiles:
            dists_by_key[own].append(dist[own] / float(k * size))
        best = min(keys, key=lambda K: (dist[K], K))
        far = [K for K in keys if not close(K, own)]
        near = [dist[K] for K in keys if close(K, own)]
        m = min(far, key=lambda K: (dist[K], K)) if far else ""
        row = {c: rec[c] for c in ("repo", "head", "res_dir", "locale_dir", "key", "units",
                                   "letters", "latin", "siblings", "ex")}
        row.update(k=k, best=best, holds=m, d_holds=dist[m] if m else None,
                   dn_holds=dist[m] / float(k * size) if m else None,
                   d_own=min(near) if near else None, own_profile=own in profiles)
        rows.append(row)
    q = {K: sorted(v)[(len(v) * CONF[0]) // CONF[1]] for K, v in dists_by_key.items() if v}
    for row in rows:
        m = row["holds"]
        ok = (bool(m) and m in q and row["dn_holds"] <= q[m]
              and (row["d_own"] is None or row["d_holds"] * MARGIN[1] <= row["d_own"] * MARGIN[0]))
        row["q_holds"] = q.get(m)
        row["flagged"] = ok
        row["category"] = ("english" if base(m) == "en" else "other-language") if ok else ""
        row["consistent"] = close(row["best"], row["key"]) if row["own_profile"] else None
    return rows, q


def known_cases(rows):
    out = []
    for res_dir, loc, want in KNOWN:
        hit = [r for r in rows if r["repo"].lower() == THUNDERBIRD.lower()
               and r["res_dir"] == res_dir and r["locale_dir"] == loc]
        r = hit[0] if hit else None
        out.append({"res_dir": res_dir, "locale_dir": loc, "expected": want,
                    "checked": bool(r), "holds": r["holds"] if r else "",
                    "category": r["category"] if r else "",
                    "right": bool(r) and r["category"] == "other-language"
                    and base(r["holds"]) == want})
    return out


def has_sibling(row):
    return any(base(s) == base(row["holds"]) for s in row["siblings"])


def grade(n_read, n_profiles, rows, known):
    """Pre-registered verdicts S0-S4 and H1 (PREREG.md). Integers only."""
    names = ("S0", "S1", "S2", "S3", "S4")
    if n_read < GATE_REPOS_READ or n_profiles < GATE_PROFILES:
        why = "NOT TESTABLE (gate: %d repositories read, %d profiles)" % (n_read, n_profiles)
        return {p: why for p in names}
    v = {}
    prof = [r for r in rows if r["own_profile"]]
    cons = sum(1 for r in prof if r["consistent"])
    v["S0"] = ("NOT TESTABLE (no folders)" if not prof
               else "HELD" if 100 * cons >= S0_PCT * len(prof) else "FAILED")
    other = [r for r in rows if r["category"] == "other-language"]
    v["S1"] = "HELD" if len({r["repo"] for r in other}) >= S1_MIN_REPOS else "FAILED"
    v["S2"] = ("NOT TESTABLE (no folders)" if not rows
               else "HELD" if 100 * len(other) < len(rows) else "FAILED")
    kc = [x for x in known if x["checked"]]
    v["S3"] = ("NOT TESTABLE (%d known folders checked)" % len(kc) if len(kc) < 2
               else "HELD" if sum(1 for x in kc if x["right"]) >= 2 else "FAILED")
    if len(other) < MIN_TESTABLE:
        v["S4"] = "NOT TESTABLE (%d flagged folders)" % len(other)
    else:
        sib = sum(1 for r in other if has_sibling(r))
        v["S4"] = "HELD" if 2 * sib >= len(other) else "FAILED"
    return v


def sample_key(repo, res_dir, locale_dir):
    return hashlib.sha256(("%s|%s|%s|%s" % (KEY, repo, res_dir, locale_dir))
                          .encode("utf-8")).hexdigest()


def draw_sample(rows, size=SAMPLE_SIZE):
    """Per repository the other-language folder with the lowest key, then the first `size`."""
    by_repo = collections.defaultdict(list)
    for r in rows:
        if r["category"] == "other-language":
            by_repo[r["repo"]].append(r)
    kept = [min(rs, key=lambda r: sample_key(r["repo"], r["res_dir"], r["locale_dir"]))
            for _, rs in sorted(by_repo.items())]
    kept.sort(key=lambda r: sample_key(r["repo"], r["res_dir"], r["locale_dir"]))
    return kept[:size]


def grade_h1(labels):
    """labels: hand labels of the sample rows ('real' or anything else)."""
    if len(labels) < H1_MIN:
        return "NOT TESTABLE"
    real = sum(1 for x in labels if x == "real")
    return "HELD" if real * 4 >= 3 * len(labels) else "FAILED"


ROW_COLS = ["repo", "head", "res_dir", "locale_dir", "key", "units", "letters", "latin",
            "category", "holds", "best", "dn_holds", "q_holds", "margin", "holds_folder_present",
            "siblings", "ex1", "ex2", "ex3"]
SAMPLE_COLS = ["sample"] + ROW_COLS + ["label", "note"]


def out_row(r):
    ex = list(r["ex"]) + ["", "", ""]
    margin = (round(r["d_holds"] / float(r["d_own"]), 4)
              if r["d_own"] and r["d_holds"] is not None else "")
    return {"repo": r["repo"], "head": r["head"], "res_dir": r["res_dir"],
            "locale_dir": r["locale_dir"], "key": r["key"], "units": r["units"],
            "letters": r["letters"], "latin": r["latin"], "category": r["category"],
            "holds": r["holds"], "best": r["best"],
            "dn_holds": "" if r["dn_holds"] is None else round(r["dn_holds"], 4),
            "q_holds": "" if r["q_holds"] is None else round(r["q_holds"], 4),
            "margin": margin, "holds_folder_present": "yes" if has_sibling(r) else "no",
            "siblings": " ".join(r["siblings"]), "ex1": ex[0], "ex2": ex[1], "ex3": ex[2]}


def exploratory(rows, glob, profiles, q):
    pairs = collections.Counter()
    for r in rows:
        if r["flagged"]:
            pairs["%s>%s (%s)" % (r["key"], r["holds"], r["category"])] += 1
    confusion = collections.Counter("%s>%s" % (r["key"], r["best"]) for r in rows
                                    if r["own_profile"] and not r["consistent"])
    per_key = collections.Counter(r["key"] for r in rows)
    eng = [r for r in rows if r["category"] == "english"]
    return {
        "flagged_pairs": dict(pairs.most_common(60)),
        "inconsistent_top": dict(confusion.most_common(40)),
        "english_folders": len(eng), "english_repos": len({r["repo"] for r in eng}),
        "flagged_without_own_profile": sum(1 for r in rows if r["flagged"]
                                           and not r["own_profile"]),
        "checked_by_key": dict(per_key.most_common()),
        "repos_by_key": {k: glob[k]["repos"] for k in sorted(glob)},
        "profile_keys": sorted(profiles),
        "q90": {k: round(v, 4) for k, v in sorted(q.items())},
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


def iter_jsonl(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--repos", help="local repos.txt instead of downloading")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--budget-minutes", type=float, default=240)
    ap.add_argument("--prereg-wait-minutes", type=float, default=360)
    ap.add_argument("--skip-prereg-check", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    started = time.time()
    shas = {}
    for mod in (cl, lm):
        with open(mod.__file__, "rb") as f:
            shas[mod.__name__] = hashlib.sha256(f.read()).hexdigest()
    print("latin_langid %s (locale_mismatch %s, cyrillic_leak %s)"
          % (VERSION, lm.VERSION, cl.VERSION), flush=True)
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

    tmp_root = tempfile.mkdtemp(prefix="latin-langid-")
    selftest = {}
    for u in SELFTEST_REPOS:
        r = process_repo(u, tmp_root)
        selftest[u] = {"status": r["status"], "checked": len(r["records"])}
    print("selftest", json.dumps(selftest), flush=True)
    if not any(v["checked"] >= 10 for v in selftest.values()):
        print("selftest found no checked folders; clone or parse broken, stopping",
              file=sys.stderr)
        return 3

    deadline = time.time() + a.budget_minutes * 60
    glob, results, skipped = {}, [], []
    rec_path = os.path.join(tmp_root, "records.jsonl")
    rec_f = open(rec_path, "w", encoding="utf-8", errors="replace")
    jl = open(os.path.join(a.out_dir, "repos.jsonl"), "w", encoding="utf-8", errors="replace")

    def work(u):
        if time.time() > deadline:
            return {"repo": u, "status": "not-started", "records": [], "contrib": {}}
        return process_repo(u, tmp_root)

    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for n, r in enumerate(ex.map(work, repos), 1):
            recs, contrib = r.pop("records", []), r.pop("contrib", {})
            if r["status"] == "not-started":
                skipped.append(r["repo"])
                continue
            for rec in recs:
                rec_f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
            merge_contrib(glob, contrib)
            r["records"] = len(recs)
            results.append(r)
            jl.write(json.dumps({k: r.get(k) for k in ("repo", "status", "head", "error",
                                                       "seconds", "parse_failed", "eligible",
                                                       "records")},
                                ensure_ascii=False, sort_keys=True) + "\n")
            if n % 200 == 0:
                jl.flush()
                print("%d/%d done, %.0f min" % (n, len(repos), (time.time() - started) / 60),
                      flush=True)
    rec_f.close()
    jl.close()

    profiles = build_profiles(glob)
    print("%d profiles: %s" % (len(profiles), " ".join(sorted(profiles))), flush=True)
    rows, q = classify_rows(iter_jsonl(rec_path), profiles)
    shutil.rmtree(tmp_root, ignore_errors=True)

    flagged = [r for r in rows if r["flagged"]]
    flagged.sort(key=lambda r: (r["repo"], r["res_dir"], r["locale_dir"]))
    with open(os.path.join(a.out_dir, "folders.csv"), "w", encoding="utf-8", errors="replace",
              newline="") as f:
        w = csv.DictWriter(f, fieldnames=ROW_COLS)
        w.writeheader()
        for r in flagged:
            w.writerow(out_row(r))
    sample = draw_sample(rows)
    with open(os.path.join(a.out_dir, "sample.csv"), "w", encoding="utf-8", errors="replace",
              newline="") as f:
        w = csv.DictWriter(f, fieldnames=SAMPLE_COLS)
        w.writeheader()
        for i, r in enumerate(sample, 1):
            w.writerow(dict(out_row(r), sample=i, label="", note=""))
    with open(os.path.join(a.out_dir, "profiles.json"), "w", encoding="utf-8") as f:
        json.dump({k: {"repos": glob[k]["repos"],
                       "top": [g for g, _ in sorted(profiles[k].items(), key=lambda kv: kv[1])]}
                   for k in sorted(profiles)}, f, ensure_ascii=False, indent=0, sort_keys=True)

    ok = [r for r in results if r.get("status") in ("ok", "no-translations")]
    known = known_cases(rows)
    verdicts = grade(len(ok), len(profiles), rows, known)
    gate_open = not verdicts["S0"].startswith("NOT TESTABLE (gate")
    verdicts["H1"] = (("PENDING HAND CHECK (sample of %d)" % len(sample)
                       if len(sample) >= H1_MIN else "NOT TESTABLE (sample of %d)" % len(sample))
                      if gate_open else verdicts["S0"])
    prof = [r for r in rows if r["own_profile"]]
    other = [r for r in rows if r["category"] == "other-language"]
    elig = collections.Counter()
    for r in ok:
        elig.update(r.get("eligible") or {})
    summary = {
        "verdicts": verdicts, "version": VERSION, "module_sha256": shas,
        "repos_url": REPOS_URL, "repos_sha256": hashlib.sha256(raw).hexdigest(),
        "prereg_sha256": prereg_sha, "repos_listed": len(repos), "repos_read": len(ok),
        "repos_not_started": len(skipped),
        "status_counts": dict(collections.Counter(r["status"] for r in results)),
        "parse_failed_files": sum(r.get("parse_failed") or 0 for r in results),
        "eligible": dict(elig), "profiles": len(profiles), "checked_folders": len(rows),
        "with_own_profile": len(prof),
        "consistent": sum(1 for r in prof if r["consistent"]),
        "other_language_folders": len(other),
        "other_language_repos": len({r["repo"] for r in other}),
        "other_language_with_holds_folder": sum(1 for r in other if has_sibling(r)),
        "english_folders": sum(1 for r in rows if r["category"] == "english"),
        "sample_size": len(sample), "known_cases": known,
        "exploratory": exploratory(rows, glob, profiles, q), "selftest": selftest,
        "minutes": round((time.time() - started) / 60, 1),
    }
    with open(os.path.join(a.out_dir, "summary.json"), "w", encoding="utf-8",
              errors="replace") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps(verdicts), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
