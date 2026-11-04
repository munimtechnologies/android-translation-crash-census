#!/usr/bin/env python3
# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""How often is zhtw-mcp's mainland-vocabulary check right on shipped Taiwan Android strings?

Pre-registered (PREREG.md, mark "zhtw-lint PREREG v1"). For every repository in
hidden-chars/repos.txt (the F-Droid source repositories of the census), reads the Android string
resources at HEAD, takes every Traditional Chinese (Taiwan) translation unit, and runs the open
zh-TW linter zhtw-mcp (github.com/sysprog21/zhtw-mcp, MIT) on it:

    zhtw-mcp lint --format json --profile base --relaxed --content-type plain -- < text

Only `cross_strait` findings (mainland vocabulary) are counted. The same units are also run
through the OpenCC Taiwan phrase rule of zh_vocab.py 0.1.0, so the two can be compared on
identical text. It also runs zhtw-mcp on the 40 strings that zh-vocab's hand check labelled
before this study existed (16 `mainland`, 24 `fine`), and draws a fresh sample of 40 zhtw-mcp
findings for a hand check.

Imports the published zh_vocab.py 0.1.0 (corpus, clone method, folder rules, parsing, units,
phrase rule); the job downloads it from main and records its SHA-256. Needs git and the zhtw-mcp
binary (the job downloads the `latest` release and checks it against the release's SHA256SUMS).

Made with AI agents by MV2 of Munim, Inc. Standard library only.
"""
import argparse
import collections
import concurrent.futures
import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import xml.etree.ElementTree as ET

import zh_vocab as z

VERSION = "0.1.0"
BASE = z.BASE
REPOS_URL = z.REPOS_URL
PREREG_URL = BASE + "zhtw-lint/PREREG.md"
PREREG_MARK = "zhtw-lint PREREG v1"
KNOWN_SAMPLE_URL = BASE + "zh-vocab/sample.csv"
KNOWN_LABELS_URL = BASE + "zh-vocab/sample_labels.csv"
RELEASE_API = "https://api.github.com/repos/sysprog21/zhtw-mcp/releases/tags/latest"
MAIN_API = "https://api.github.com/repos/sysprog21/zhtw-mcp/commits/main"
SALT = "zhtw-lint v1"
LINT_ARGS = ["lint", "--format", "json", "--profile", "base", "--relaxed",
             "--content-type", "plain", "--"]
VOCAB_TYPE = "crossstrait"
FOUND_KEYS = ("found", "matched", "match", "original", "from", "term", "text", "span")

# Pre-registered thresholds (PREREG.md).
GATE_UNITS = 20000
GATE_REPOS = 100
MAX_ERR_NUM, MAX_ERR_DEN = 1, 100
Z1_NUM, Z1_DEN = 3, 4
Z1_MIN_ROWS = 20
Z2_MIN = 12
Z3_MAX = 6
SAMPLE_SIZE = 40

# zh-vocab's hand check (zh-vocab/sample_labels.csv, published 2026-11-04): the term or terms
# judged mainland usage in each of its 16 `mainland` rows, by row number n.
MAINLAND_TERMS = {
    5: ["設備"], 6: ["點擊"], 9: ["設置"], 11: ["頁腳"], 13: ["設備"], 17: ["點擊"],
    21: ["連接"], 23: ["保存"], 24: ["文件名"], 25: ["文件"], 26: ["鏡像"],
    30: ["應用程序", "添加"], 31: ["發送"], 33: ["連接"], 34: ["設備"], 40: ["發送"],
}


def clean_text(value):
    """Join surrogate pairs and replace lone halves with U+FFFD."""
    if not isinstance(value, str):
        return value
    return value.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ---------------------------------------------------------------- reading zhtw-mcp's output

def norm_type(value):
    return "".join(c for c in value.lower() if c.isalpha())


def is_vocab(d):
    return any(isinstance(v, str) and norm_type(v) == VOCAB_TYPE for v in d.values())


def findings(obj):
    """Every issue object in zhtw-mcp's JSON whose rule type is cross_strait.

    The CLI's per-issue field names are not documented, so an issue is any JSON object that has
    a string value equal to "cross_strait" (letters only, any case), directly or in an object
    one level down. Such an object is not searched further."""
    out = []

    def walk(o):
        if isinstance(o, dict):
            if is_vocab(o) or any(isinstance(v, dict) and is_vocab(v) for v in o.values()):
                out.append(o)
                return
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(obj)
    return out


def found_text(issue):
    """The text the finding matched: the first non-empty string under FOUND_KEYS, in the issue
    or in an object one level down; "" if there is none."""
    for d in [issue] + [v for v in issue.values() if isinstance(v, dict)]:
        for k in FOUND_KEYS:
            v = d.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return ""


def lint(binary, text, timeout=60):
    """(list of matched texts of cross_strait findings, None) or (None, error)."""
    env = dict(os.environ, ZHTW_NO_NETWORK="1", NO_COLOR="1")
    try:
        p = subprocess.run([binary] + LINT_ARGS, input=text.encode("utf-8"),
                           capture_output=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except OSError as e:
        return None, "oserror: %s" % str(e)[:150]
    if p.returncode not in (0, 1):
        return None, "exit %d: %s" % (p.returncode,
                                      p.stderr.decode("utf-8", "replace").strip()[:200])
    out = p.stdout.decode("utf-8", "replace").strip()
    if not out:
        return [], None
    try:
        data = json.loads(out)
    except ValueError as e:
        return None, "json: %s" % str(e)[:150]
    return [found_text(f) for f in findings(data)], None


def lint_raw(binary, text, timeout=60):
    """Exit code, stdout and stderr, for the record (control.json)."""
    env = dict(os.environ, ZHTW_NO_NETWORK="1", NO_COLOR="1")
    try:
        p = subprocess.run([binary] + LINT_ARGS, input=text.encode("utf-8"),
                           capture_output=True, timeout=timeout, env=env)
        return {"exit": p.returncode, "stdout": p.stdout.decode("utf-8", "replace")[:4000],
                "stderr": p.stderr.decode("utf-8", "replace")[:2000]}
    except (subprocess.TimeoutExpired, OSError) as e:
        return {"error": repr(e)[:300]}


CONTROL_CASES = [
    # (text, a term some finding must match, or None for "no cross_strait finding")
    ("這個軟件很好用", "軟件"),
    ("請檢查默認設定", "默認"),
    ("這個軟體很好用", None),
]


def control(binary):
    """zhtw-mcp must report the two mainland terms (with their matched text, at most 6
    characters) and nothing on the Taiwan sentence. Returns (ok, record)."""
    record, ok = [], True
    for text, want in CONTROL_CASES:
        found, err = lint(binary, text)
        good = err is None and (
            (want is None and found == []) or
            (want is not None and any(want in f and len(f) <= 6 for f in found)))
        ok = ok and good
        record.append({"text": text, "want": want, "found": found, "error": err, "ok": good,
                       "raw": lint_raw(binary, text)})
    return ok, record


def overlaps(found, terms):
    """True if a matched text contains one of `terms` or lies inside one."""
    return any(f and (t in f or f in t) for f in found for t in terms)


# ---------------------------------------------------------------- reading the repositories

def _load(cache, path):
    if path not in cache:
        try:
            cache[path] = (z.parse_values(path) if os.path.isfile(path) else None, False)
        except (ET.ParseError, ValueError, OSError):
            cache[path] = (None, True)
    return cache[path][0]


def scan_tw(root):
    """Taiwan units under every res/ folder: (rows, number of files that failed to parse)."""
    rows, cache = [], {}
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        if os.path.basename(dirpath) != "res" or "values" not in dirnames:
            continue
        rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
        for d in [x for x in dirnames if z.zh_group(x) == "tw"]:
            for fn in sorted(os.listdir(os.path.join(dirpath, d))):
                if not fn.endswith(".xml") or not os.path.isfile(
                        os.path.join(dirpath, "values", fn)):
                    continue
                source = _load(cache, os.path.join(dirpath, "values", fn))
                target = _load(cache, os.path.join(dirpath, d, fn))
                if not source or not target:
                    continue
                for key, i, t, src in z.units(source, target):
                    rows.append({"res_dir": rel, "locale_dir": d, "file": fn, "key": key,
                                 "index": i, "text": clean_text(t).strip(),
                                 "source": clean_text(src).strip()})
    return rows, sum(1 for v in cache.values() if v[1])


def process_repo(url, tmp_root):
    d = tempfile.mkdtemp(dir=tmp_root)
    res = {"repo": url, "status": "ok", "units": [], "parse_failed": 0}
    t0 = time.time()
    try:
        s = os.path.join(d, "s")
        r = z.git(["clone", "--quiet", "--depth", "1", "--filter=blob:none", "--no-checkout",
                   "--single-branch", url, s])
        if r.returncode != 0:
            res.update(status="clone-failed",
                       error=(r.stderr.strip().splitlines() or [""])[-1][:200])
            return res
        z.git(["-C", s, "sparse-checkout", "set", "--no-cone"] + z.SPARSE)
        branch = z.git(["-C", s, "symbolic-ref", "--short", "HEAD"]).stdout.strip()
        z.git(["-C", s, "checkout", "--quiet"] + ([branch] if branch else []))
        if not z.has_values(s):
            z.git(["-C", s, "read-tree", "-mu", "HEAD"])
        res["head"] = z.git(["-C", s, "rev-parse", "HEAD"]).stdout.strip()
        res["units"], res["parse_failed"] = scan_tw(s)
        if not res["units"]:
            res["status"] = "no-tw"
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


# ---------------------------------------------------------------- known rows, sample, grading

def known_rows(sample_text, labels_text):
    """zh-vocab's 40 hand-labelled rows joined on n: dicts with n, repo, key, terms, label,
    text. Raises ValueError if the rows don't match what PREREG.md describes."""
    texts = {int(r["n"]): r for r in csv.DictReader(io.StringIO(sample_text))}
    out = []
    for r in csv.DictReader(io.StringIO(labels_text)):
        n = int(r["n"])
        s = texts[n]
        if s["repo"] != r["repo"] or s["key"] != r["key"]:
            raise ValueError("row %d differs between sample.csv and sample_labels.csv" % n)
        out.append({"n": n, "repo": r["repo"], "key": r["key"], "terms": r["terms"].split(),
                    "label": r["label"], "text": s["text"]})
    mainland = {r["n"] for r in out if r["label"] == "mainland"}
    fine = {r["n"] for r in out if r["label"] == "fine"}
    if len(out) != 40 or mainland != set(MAINLAND_TERMS) or len(fine) != 24:
        raise ValueError("known rows are not the 16 mainland + 24 fine rows of PREREG.md")
    return sorted(out, key=lambda r: r["n"])


def grade_known(rows):
    """Z2: mainland rows where a finding overlaps the row's mainland term(s).
    Z3: fine rows where a finding overlaps one of the row's (correct) table terms."""
    caught = [r["n"] for r in rows if r["label"] == "mainland" and r.get("error") is None
              and overlaps(r["found"], MAINLAND_TERMS[r["n"]])]
    repeated = [r["n"] for r in rows if r["label"] == "fine" and r.get("error") is None
                and overlaps(r["found"], r["terms"])]
    errors = [r["n"] for r in rows if r.get("error") is not None]
    if errors:
        v2 = v3 = "NOT TESTABLE (lint error on a known row)"
    else:
        v2 = "HELD" if len(caught) >= Z2_MIN else "FAILED"
        v3 = "HELD" if len(repeated) <= Z3_MAX else "FAILED"
    return {"Z2": v2, "Z3": v3}, {"z2_caught": caught, "z3_repeated": repeated,
                                  "errors": errors}


def location(x):
    return "%s|%s|%s|%s|%s|%s|%s" % (SALT, x["repo"], x["res_dir"], x["locale_dir"], x["file"],
                                     x["key"], x["index"])


def draw_sample(rows, exclude=(), size=SAMPLE_SIZE):
    """One flagged unit per repository (lowest hash of SALT + its location), repositories in
    order of the hash of SALT + URL, up to `size`. Units whose (repo, key) is in `exclude`
    (zh-vocab's 40 rows) are never drawn."""
    best = {}
    for x in rows:
        if not x.get("zhtw") or (x["repo"], x["key"]) in exclude:
            continue
        h = sha(location(x))
        if x["repo"] not in best or h < best[x["repo"]][0]:
            best[x["repo"]] = (h, x)
    order = sorted(best, key=lambda r: sha(SALT + "|" + r))
    return [best[r][1] for r in order[:size]]


def grade_z1(labels):
    """Z1 from hand labels ('mainland', 'fine', 'other'), one per sampled unit."""
    if len(labels) < Z1_MIN_ROWS:
        return "NOT TESTABLE"
    m = sum(1 for x in labels if x == "mainland")
    return "HELD" if m * Z1_DEN >= len(labels) * Z1_NUM else "FAILED"


def tables(units):
    """Counts over linted units (dicts with repo, zhtw, opencc)."""
    t = collections.Counter()
    repos = collections.defaultdict(set)
    terms_units, terms_repos = collections.Counter(), collections.defaultdict(set)
    for u in units:
        t["units"] += 1
        repos["units"].add(u["repo"])
        z_hit, o_hit = bool(u["zhtw"]), bool(u["opencc"])
        for name, hit in (("zhtw", z_hit), ("opencc", o_hit), ("both", z_hit and o_hit),
                          ("zhtw_only", z_hit and not o_hit), ("opencc_only", o_hit and not z_hit)):
            if hit:
                t[name] += 1
                repos[name].add(u["repo"])
        for f in sorted(set(u["zhtw"])):
            terms_units[f] += 1
            terms_repos[f].add(u["repo"])
    out = dict(t)
    for name, s in repos.items():
        out["repos_" + name] = len(s)
    top = [[f, n, len(terms_repos[f])] for f, n in terms_units.most_common(60)]
    return out, top


def grade_z4(t):
    return "HELD" if t.get("zhtw", 0) < t.get("opencc", 0) else "FAILED"


# ---------------------------------------------------------------- the run

def fetch(url, timeout=120):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read()


def wait_for_prereg(minutes):
    end = time.time() + minutes * 60
    while True:
        try:
            text = fetch(PREREG_URL, 60).decode("utf-8")
            if PREREG_MARK in text:
                return sha(text)
        except OSError:
            pass
        if time.time() > end:
            return None
        time.sleep(60)


def release_info():
    info = {}
    for name, url in (("release", RELEASE_API), ("main", MAIN_API)):
        try:
            d = json.loads(fetch(url, 60).decode("utf-8"))
        except (OSError, ValueError) as e:
            info[name] = {"error": repr(e)[:200]}
            continue
        if name == "release":
            info[name] = {k: d.get(k) for k in ("tag_name", "name", "target_commitish",
                                                 "published_at", "created_at")}
            info[name]["assets"] = [{k: a.get(k) for k in ("name", "size", "updated_at",
                                                            "digest")}
                                    for a in d.get("assets", [])]
        else:
            info[name] = {"sha": d.get("sha"),
                          "date": (d.get("commit") or {}).get("committer", {}).get("date")}
    return info


ROW_COLS = ["repo", "head", "res_dir", "locale_dir", "file", "key", "index", "zhtw_terms",
            "opencc_terms", "text", "source"]
SAMPLE_COLS = ["n"] + ROW_COLS


def as_row(u):
    r = {k: u.get(k, "") for k in ROW_COLS if k not in ("zhtw_terms", "opencc_terms")}
    r["zhtw_terms"] = " ".join(u["zhtw"])
    r["opencc_terms"] = " ".join(u["opencc"])
    return {k: clean_text(v) for k, v in r.items()}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--zhtw", default="./zhtw-mcp")
    ap.add_argument("--repos", help="local repos.txt instead of downloading")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--lint-workers", type=int, default=4)
    ap.add_argument("--budget-minutes", type=float, default=150)
    ap.add_argument("--lint-budget-minutes", type=float, default=150)
    ap.add_argument("--prereg-wait-minutes", type=float, default=120)
    ap.add_argument("--skip-prereg-check", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    started = time.time()
    binary = os.path.abspath(a.zhtw)

    st, s_set, phrases, opencc_hashes = z.load_dicts(a.out_dir)
    ok, record = control(binary)
    with open(os.path.join(a.out_dir, "control.json"), "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=1)
    if z.VERSION != "0.1.0" or not z.control(phrases, s_set) or not ok:
        print("positive control failed; stopping before reading any repository (control.json)",
              file=sys.stderr)
        return 6
    prereg_sha = None
    if not a.skip_prereg_check:
        prereg_sha = wait_for_prereg(a.prereg_wait_minutes)
        if not prereg_sha:
            print("PREREG.md not public; stopping before reading any repository",
                  file=sys.stderr)
            return 4

    # zh-vocab's hand-labelled rows (Z2, Z3).
    sample_raw, labels_raw = fetch(KNOWN_SAMPLE_URL), fetch(KNOWN_LABELS_URL)
    try:
        known = known_rows(sample_raw.decode("utf-8"), labels_raw.decode("utf-8"))
    except (ValueError, KeyError) as e:
        print("known rows don't match PREREG.md: %s" % e, file=sys.stderr)
        return 8
    for r in known:
        r["found"], r["error"] = lint(binary, r["text"])
        r["found"] = r["found"] or []
    known_v, known_detail = grade_known(known)
    with open(os.path.join(a.out_dir, "known_rows.csv"), "w", encoding="utf-8",
              newline="") as f:
        w = csv.DictWriter(f, fieldnames=["n", "repo", "key", "label", "terms",
                                          "mainland_terms", "zhtw_terms", "error", "counted",
                                          "text"])
        w.writeheader()
        for r in known:
            counted = (r["n"] in known_detail["z2_caught"] or
                       r["n"] in known_detail["z3_repeated"])
            w.writerow({k: clean_text(v) for k, v in {
                "n": r["n"], "repo": r["repo"], "key": r["key"], "label": r["label"],
                "terms": " ".join(r["terms"]),
                "mainland_terms": " ".join(MAINLAND_TERMS.get(r["n"], [])),
                "zhtw_terms": " ".join(r["found"]), "error": r["error"] or "",
                "counted": counted, "text": r["text"]}.items()})
    print("known rows", json.dumps(known_v), flush=True)

    raw = open(a.repos, "rb").read() if a.repos else fetch(REPOS_URL)
    repos = [u.strip() for u in raw.decode("utf-8").splitlines() if u.strip()]
    if a.limit:
        repos = repos[:a.limit]
    print("zhtw_lint %s: %d repositories" % (VERSION, len(repos)), flush=True)

    tmp_root = tempfile.mkdtemp(prefix="zhtw-")
    selftest = {}
    for u in ("https://github.com/TeamNewPipe/NewPipe", "https://gitlab.com/fdroid/fdroidclient"):
        r = process_repo(u, tmp_root)
        selftest[u] = {"status": r["status"], "units": len(r["units"])}
    print("selftest", json.dumps(selftest), flush=True)
    if not any(v["units"] for v in selftest.values()):
        print("selftest found no Taiwan units; clone method broken, stopping", file=sys.stderr)
        return 3

    deadline = time.time() + a.budget_minutes * 60
    results, skipped = [], []
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
            jl.write(json.dumps({"repo": r["repo"], "status": r["status"], "head": r.get("head"),
                                 "error": clean_text(r.get("error")), "units": len(r["units"]),
                                 "parse_failed": r["parse_failed"], "seconds": r.get("seconds")},
                                ensure_ascii=False, sort_keys=True) + "\n")
            if n % 200 == 0:
                jl.flush()
                print("%d/%d read, %.0f min" % (n, len(repos), (time.time() - started) / 60),
                      flush=True)
    jl.close()
    shutil.rmtree(tmp_root, ignore_errors=True)

    ok_results = [r for r in results if r["status"] in ("ok", "no-tw")]
    units, source_han = [], 0
    for r in ok_results:
        for x in r["units"]:
            if z.has_han(x["source"]):
                source_han += 1
                continue
            units.append(dict(x, repo=r["repo"], head=r.get("head", "")))
    distinct = sorted({u["text"] for u in units})
    print("%d Taiwan units, %d distinct texts to lint" % (len(units), len(distinct)), flush=True)

    memo, lint_deadline = {}, time.time() + a.lint_budget_minutes * 60

    def lint_one(text):
        if time.time() > lint_deadline:
            return text, (None, "not-linted")
        return text, lint(binary, text)

    with concurrent.futures.ThreadPoolExecutor(max_workers=a.lint_workers) as ex:
        for n, (text, res) in enumerate(ex.map(lint_one, distinct), 1):
            memo[text] = res
            if n % 10000 == 0:
                print("%d/%d linted, %.0f min" % (n, len(distinct),
                                                  (time.time() - started) / 60), flush=True)
    errors = collections.Counter(err.split(":")[0] for _, err in memo.values() if err)
    error_texts = sum(errors.values())
    not_linted = errors.get("not-linted", 0)

    linted = []
    for u in units:
        found, err = memo[u["text"]]
        if err:
            continue
        u["zhtw"] = sorted(set(found))
        u["opencc"] = phrases.terms(u["text"], u["source"])
        linted.append(u)
    t, top = tables(linted)
    gate = (len(linted) >= GATE_UNITS and t.get("repos_units", 0) >= GATE_REPOS
            and not_linted == 0 and error_texts * MAX_ERR_DEN <= len(distinct) * MAX_ERR_NUM)
    verdicts = dict(known_v)
    if gate:
        verdicts["Z4"] = grade_z4(t)
        verdicts["Z1"] = "PENDING (hand check of sample.csv)"
    else:
        verdicts["Z4"] = verdicts["Z1"] = "NOT TESTABLE (gate)"

    flagged = [u for u in linted if u["zhtw"]]
    with open(os.path.join(a.out_dir, "flagged.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ROW_COLS)
        w.writeheader()
        for u in flagged:
            w.writerow(as_row(u))
    exclude = {(r["repo"], r["key"]) for r in known}
    sample = draw_sample(flagged, exclude)
    with open(os.path.join(a.out_dir, "sample.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SAMPLE_COLS)
        w.writeheader()
        for i, u in enumerate(sample, 1):
            w.writerow(dict(as_row(u), n=i))

    summary = {
        "version": VERSION, "zh_vocab_version": z.VERSION,
        "zh_vocab_sha256": file_sha(z.__file__),
        "zhtw_lint_sha256": file_sha(os.path.abspath(__file__)),
        "zhtw_mcp_sha256": file_sha(binary), "zhtw_mcp_release": release_info(),
        "lint_args": LINT_ARGS, "opencc_sha256": opencc_hashes,
        "prereg_sha256": prereg_sha, "repos_url": REPOS_URL,
        "repos_sha256": hashlib.sha256(raw).hexdigest(),
        "known_sha256": {"sample.csv": hashlib.sha256(sample_raw).hexdigest(),
                         "sample_labels.csv": hashlib.sha256(labels_raw).hexdigest()},
        "verdicts": verdicts, "known": known_detail, "tables": t, "top_zhtw_terms": top,
        "units_source_han": source_han, "distinct_texts": len(distinct),
        "lint_errors": dict(errors), "gate_passed": gate, "sample_size": len(sample),
        "repos_listed": len(repos), "repos_not_started": len(skipped),
        "status_counts": dict(collections.Counter(r["status"] for r in results)),
        "parse_failed_files": sum(r["parse_failed"] for r in results),
        "selftest": selftest, "minutes": round((time.time() - started) / 60, 1),
    }
    with open(os.path.join(a.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps(verdicts), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
