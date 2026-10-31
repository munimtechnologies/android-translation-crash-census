#!/usr/bin/env python3
# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Where stray zero-width spaces in Weblate-managed Android apps came from (pre-registered).

Follow-up to the hidden-chars census. Weblate's automatic fixup RemoveZeroSpace deletes U+200B
from a translation whose source has none, but it runs inside Unit.translate (the editor, the
API, merge-type uploads). Text that reaches Weblate through the repository (git commits, the
first import, "replace" uploads) is parsed without autofixes. For every census row on a
Weblate-platform repository whose only stray character is U+200B, this finds the newest commit
that put U+200B into that string and asks whether it was a Weblate commit. See PREREG.md.

Made with AI agents by MV2 of Munim, Inc. Standard library only; needs git.
"""
import argparse
import collections
import concurrent.futures
import csv
import hashlib
import io
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
HITS_URL = BASE + "hidden-chars/hits.csv"
PREREG_URL = BASE + "hidden-chars/weblate-origin/PREREG.md"
PREREG_MARK = "weblate-origin PREREG v1"

ZWSP = chr(0x200B)
PAIR_RE = re.compile(" " + ZWSP + ZWSP + r"(?=[^\W\d_])")
WEBLATE_MSG = re.compile(r"using Weblate|Translate-URL:", re.I)
HOST_RE = re.compile(r"Translate-URL:\s*https?://([^/\s]+)", re.I)
ARRIVED = ("folder-created", "key-added")

# Pre-registered thresholds (PREREG.md).
GATE_ROWS = 60
GATE_REPOS = 15
P1_SHARE = 0.5
P2_SHARE = 0.5

# From hiddenchar.py 0.1.0 (unchanged).
_U_ESC = re.compile(r"(?<!\\)\\u([0-9A-Fa-f]{4})")


def decode_android(text):
    return _U_ESC.sub(lambda m: chr(int(m.group(1), 16)), text)


def parse_values(data):
    """key -> list of texts (None if translatable="false"), as hiddenchar.py parses a file."""
    root = ET.fromstring(data)
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


def has_zwsp(values, key, index):
    v = values.get(key) if values else None
    return bool(v) and index < len(v) and ZWSP in v[index]


def tree_xml_names(data):
    """Names of the .xml blobs in a raw git tree object (SHA-1 object ids)."""
    names, i = [], 0
    while i < len(data):
        sp = data.index(b" ", i)
        nul = data.index(b"\0", sp)
        mode, name = data[i:sp], data[sp + 1:nul].decode("utf-8", "replace")
        i = nul + 21
        if not mode.startswith(b"4") and name.endswith(".xml"):
            names.append(name)
    return sorted(names)


def is_weblate(message, author_email="", committer_email=""):
    if WEBLATE_MSG.search(message or ""):
        return True
    return any((e or "").lower().endswith("@weblate.org") for e in (author_email, committer_email))


def translate_host(message):
    m = HOST_RE.search(message or "")
    return m.group(1).lower() if m else ""


Commit = collections.namedtuple("Commit", "sha parents author_email committer_email date message")


def parse_log(text):
    out = []
    for rec in text.split("\x1e"):
        rec = rec.lstrip("\n")
        if not rec:
            continue
        f = rec.split("\x1f")
        if len(f) < 6:
            continue
        out.append(Commit(f[0], f[1].split(), f[2], f[3], f[4], "\x1f".join(f[5:])))
    return out


def attribute(commits, state, key, index):
    """Newest commit (log order) whose folder has U+200B in the string and whose parent's doesn't.

    state(sha) returns {key: [texts]} for the locale folder at sha, or None if the folder is
    absent there. Returns (commit, kind) or (None, "").
    """
    for c in commits:
        if not has_zwsp(state(c.sha), key, index):
            continue
        pv = state(c.parents[0]) if c.parents else None
        if pv is not None and has_zwsp(pv, key, index):
            continue
        if pv is None:
            kind = "folder-created"
        elif not pv.get(key) or index >= len(pv[key]):
            kind = "key-added"
        else:
            kind = "edited"
        return c, kind
    return None, ""


def select_rows(text):
    """Census rows on Weblate-platform repos whose only stray character class is U+200B."""
    rows = []
    for r in csv.DictReader(io.StringIO(text)):
        if r["platform"] == "weblate" and r["classes"] == "zwsp" and r["codepoints"] == "U+200B":
            rows.append({"repo": r["repo"], "head": r["head"], "folder": r["res_dir"] + "/" + r["locale_dir"],
                         "lang": r["lang"], "key": r["key"], "index": int(r["index"])})
    return rows


def show(text, limit=120):
    s = "".join("<U+200B>" if ch == ZWSP else ch for ch in text).replace("\n", " ")
    return s if len(s) <= limit else s[:limit] + "..."


def git(args, timeout=600):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_LFS_SKIP_SMUDGE="1", GIT_ASKPASS="true")
    return subprocess.run(["git"] + args, env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


class Store:
    """Reads objects through one `git cat-file --batch` process."""

    def __init__(self, gitdir):
        self.p = subprocess.Popen(["git", "-C", gitdir, "cat-file", "--batch"],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def read(self, spec):
        self.p.stdin.write(spec.encode("utf-8") + b"\n")
        self.p.stdin.flush()
        parts = self.p.stdout.readline().split()
        if len(parts) != 3 or parts[1] not in (b"blob", b"tree", b"commit", b"tag"):
            return None, None
        data = self.p.stdout.read(int(parts[2]))
        self.p.stdout.read(1)
        return parts[1].decode(), data

    def close(self):
        try:
            self.p.stdin.close()
            self.p.wait(timeout=30)
        except Exception:
            self.p.kill()


def folder_state(store, sha, folder, keys):
    kind, data = store.read("%s:%s" % (sha, folder))
    if kind != "tree":
        return None
    merged = {}
    for name in tree_xml_names(data):
        k, blob = store.read("%s:%s/%s" % (sha, folder, name))
        if k != "blob":
            continue
        try:
            merged.update(parse_values(blob))
        except (ET.ParseError, ValueError):
            pass
    return {k: merged[k] for k in keys if merged.get(k)}


def process_repo(url, head, rows, tmp_root, clone_timeout):
    d = tempfile.mkdtemp(dir=tmp_root)
    t0 = time.time()
    res = {"repo": url, "head": head, "status": "ok", "rows": []}

    def mark(status):
        res["rows"] = [dict(r, status=status) for r in rows]

    store = None
    try:
        g = os.path.join(d, "g")
        r = git(["clone", "--quiet", "--bare", "--single-branch", "--no-tags", url, g], timeout=clone_timeout)
        if r.returncode != 0:
            res.update(status="clone-failed", error=(r.stderr.strip().splitlines() or [""])[-1][:200])
            mark("clone-failed")
            return res
        if git(["-C", g, "cat-file", "-e", head + "^{commit}"]).returncode != 0:
            git(["-C", g, "fetch", "--quiet", "--no-tags", "origin", head], timeout=clone_timeout)
            if git(["-C", g, "cat-file", "-e", head + "^{commit}"]).returncode != 0:
                res["status"] = "head-missing"
                mark("head-missing")
                return res
        store = Store(g)
        by_folder = collections.defaultdict(list)
        for row in rows:
            by_folder[row["folder"]].append(row)
        for folder, frows in sorted(by_folder.items()):
            keys = sorted({x["key"] for x in frows})
            cache = {}

            def state(sha, folder=folder, keys=keys, cache=cache):
                if sha not in cache:
                    cache[sha] = folder_state(store, sha, folder, keys)
                return cache[sha]

            log = git(["-C", g, "log", "--no-merges",
                       "--format=%H%x1f%P%x1f%ae%x1f%ce%x1f%cI%x1f%B%x1e", head, "--", folder + "/"])
            commits = parse_log(log.stdout)
            at_head = state(head)
            for row in frows:
                out = dict(row, pair=0, status="", commit="", date="", weblate="", kind="",
                           translate_host="", subject="", commits_in_folder_history=len(commits))
                if not has_zwsp(at_head, row["key"], row["index"]):
                    out["status"] = "not-at-head"
                    res["rows"].append(out)
                    continue
                out["pair"] = int(PAIR_RE.search(at_head[row["key"]][row["index"]]) is not None)
                c, kind = attribute(commits, state, row["key"], row["index"])
                if c is None:
                    out["status"] = "unattributed"
                else:
                    out.update(status="attributed", commit=c.sha, date=c.date, kind=kind,
                               weblate=int(is_weblate(c.message, c.author_email, c.committer_email)),
                               translate_host=translate_host(c.message),
                               subject=show(c.message.strip().splitlines()[0] if c.message.strip() else ""))
                res["rows"].append(out)
        return res
    except subprocess.TimeoutExpired:
        res["status"] = "timeout"
        mark("timeout")
        return res
    except Exception as e:  # keep going; record what broke
        res.update(status="error", error=repr(e)[:200])
        mark("error")
        return res
    finally:
        if store:
            store.close()
        res["seconds"] = round(time.time() - t0, 1)
        shutil.rmtree(d, ignore_errors=True)


def share(rows):
    return sum(r["weblate"] for r in rows) / len(rows) if rows else None


def grade(rows):
    """Pre-registered verdicts (PREREG.md) from per-row results."""
    att = [r for r in rows if r.get("status") == "attributed"]
    repos = sorted({r["repo"] for r in att})
    if len(att) < GATE_ROWS or len(repos) < GATE_REPOS:
        return {p: "NOT TESTABLE (gate)" for p in ("P1", "P2", "P3")}
    v = {"P1": "HELD" if share(att) < P1_SHARE else "FAILED"}
    non = [r for r in att if not r["weblate"]]
    if not non:
        v["P2"] = "NOT TESTABLE"
    else:
        v["P2"] = "HELD" if sum(1 for r in non if r["kind"] in ARRIVED) / len(non) >= P2_SHARE else "FAILED"
    held = True
    for repo in repos:
        rest = [r for r in att if r["repo"] != repo]
        if rest and share(rest) >= P1_SHARE:
            held = False
    v["P3"] = "HELD" if held else "FAILED"
    return v


def summarize(rows):
    att = [r for r in rows if r.get("status") == "attributed"]

    def r4(x):
        return None if x is None else round(x, 4)

    def split(sub):
        return {"rows": len(sub), "weblate": sum(r["weblate"] for r in sub), "share_weblate": r4(share(sub))}

    per_repo = collections.defaultdict(lambda: [0, 0])
    for r in att:
        per_repo[r["repo"]][0] += 1
        per_repo[r["repo"]][1] += r["weblate"]
    loro = {repo: r4(share([r for r in att if r["repo"] != repo])) for repo in sorted(per_repo)}
    return {
        "verdicts": grade(rows),
        "rows_total": len(rows),
        "status_counts": dict(collections.Counter(r.get("status", "") for r in rows)),
        "attributed": split(att),
        "attributed_repos": len(per_repo),
        "kinds_non_weblate": dict(collections.Counter(r["kind"] for r in att if not r["weblate"])),
        "kinds_weblate": dict(collections.Counter(r["kind"] for r in att if r["weblate"])),
        "per_repo_rows_weblate": {k: v for k, v in sorted(per_repo.items())},
        "leave_one_repo_out_share_weblate": loro,
        "exploratory_by_pair": {"pair": split([r for r in att if r["pair"]]),
                                "other": split([r for r in att if not r["pair"]])},
        "exploratory_translate_hosts": dict(collections.Counter(r["translate_host"] for r in att if r["weblate"])),
        "exploratory_years": {"%s weblate=%d" % k: n for k, n in sorted(collections.Counter(
            (r["date"][:4], r["weblate"]) for r in att).items())},
    }


def wait_for_prereg(minutes):
    """The pre-registration must be public before any repository history is read."""
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


COLS = ["repo", "head", "folder", "lang", "key", "index", "pair", "status", "commit", "date", "weblate",
        "kind", "translate_host", "subject", "commits_in_folder_history"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--hits", help="local hits.csv instead of downloading")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--budget-minutes", type=float, default=200)
    ap.add_argument("--clone-timeout", type=float, default=1500)
    ap.add_argument("--prereg-wait-minutes", type=float, default=45)
    ap.add_argument("--skip-prereg-check", action="store_true")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    started = time.time()
    prereg_sha = None
    if not a.skip_prereg_check:
        prereg_sha = wait_for_prereg(a.prereg_wait_minutes)
        if not prereg_sha:
            print("PREREG.md not public; stopping before reading any history", file=sys.stderr)
            return 4
    if a.hits:
        with open(a.hits, "rb") as f:
            raw = f.read()
    else:
        with urllib.request.urlopen(HITS_URL, timeout=120) as resp:
            raw = resp.read()
    rows = select_rows(raw.decode("utf-8"))
    by_repo = collections.defaultdict(list)
    for r in rows:
        by_repo[(r["repo"], r["head"])].append(r)
    print("zwsp_origin %s: %d rows in %d repositories" % (VERSION, len(rows), len(by_repo)), flush=True)

    tmp_root = tempfile.mkdtemp(prefix="zwsporigin-")
    deadline = time.time() + a.budget_minutes * 60

    def work(item):
        (url, head), rs = item
        if time.time() > deadline:
            return {"repo": url, "head": head, "status": "not-started",
                    "rows": [dict(r, status="not-started") for r in rs]}
        return process_repo(url, head, rs, tmp_root, a.clone_timeout)

    results = []
    with open(os.path.join(a.out_dir, "repos.jsonl"), "w", encoding="utf-8") as jl:
        with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
            for r in ex.map(work, sorted(by_repo.items())):
                results.append(r)
                jl.write(json.dumps({k: r.get(k) for k in ("repo", "head", "status", "error", "seconds")}
                                    | {"rows": len(r["rows"])}, sort_keys=True) + "\n")
                jl.flush()
                print("%s %s %.0fs" % (r["repo"], r["status"], r.get("seconds", 0)), flush=True)
    shutil.rmtree(tmp_root, ignore_errors=True)

    out_rows = [row for r in results for row in r["rows"]]
    with open(os.path.join(a.out_dir, "rows.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        for row in out_rows:
            w.writerow({k: row.get(k, "") for k in COLS})
    summary = summarize(out_rows)
    summary.update({
        "version": VERSION, "hits_url": HITS_URL, "hits_sha256": hashlib.sha256(raw).hexdigest(),
        "prereg_sha256": prereg_sha, "rows_selected": len(rows), "repos_selected": len(by_repo),
        "repo_status_counts": dict(collections.Counter(r["status"] for r in results)),
        "minutes": round((time.time() - started) / 60, 1),
    })
    with open(os.path.join(a.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps(summary["verdicts"]), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
