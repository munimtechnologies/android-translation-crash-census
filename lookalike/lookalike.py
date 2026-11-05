#!/usr/bin/env python3
# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Look-alike letters inside markup tags and format specifiers of Android translations.

Pre-registered (PREREG.md, mark "lookalike PREREG v1"). For every repository in
hidden-chars/repos.txt (the F-Droid source repositories of the census), reads every XML file in
the translation folders (values-xx, values-xx-rYY, values-b+...) of every res/ folder at HEAD,
and looks for two things in the raw file text:

- tag: a markup tag whose name is written with at least one letter from another alphabet that
  looks like a Latin letter, and that reads as a common tag once those letters are swapped for
  Latin ones: "</а>" with a Cyrillic а, "&lt;і&gt;" with a Ukrainian і.
- fmt: a Java format specifier whose conversion letter is such a look-alike: "%1$ѕ" with a
  Cyrillic ѕ, "%ｄ" with a fullwidth ｄ. Android's String.format throws on these at run time.

For each hit it records the string key, the look-alike letters and their alphabet, and whether
the default (source) string of the same key has the same tag or specifier in plain ASCII.

Imports the published cyrillic_leak.py 0.1.0 for the corpus, the clone method and git; the job
downloads it from main and records its SHA-256. Needs git.

Made with AI agents by MV2 of Munim, Inc. Standard library only.
"""
import argparse
import bisect
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

import cyrillic_leak as cl

VERSION = "0.1.0"
BASE = cl.BASE
REPOS_URL = cl.REPOS_URL
PREREG_URL = BASE + "lookalike/PREREG.md"
PREREG_MARK = "lookalike PREREG v1"
SALT = "lookalike v1"

# Pre-registered thresholds (PREREG.md).
GATE_REPOS = 4000
K1_MIN_REPOS = 10
K4_NUM, K4_DEN = 3, 4
K4_MIN_ROWS = 8
SAMPLE_SIZE = 40


def _table(pairs):
    return {chr(cp): ch for cp, ch in pairs}


# Letters of other alphabets that look like a Latin letter, and that letter. Fixed in PREREG.md.
CONFUSABLE = _table([
    # Cyrillic small letters
    (0x0430, "a"), (0x0435, "e"), (0x043E, "o"), (0x0440, "p"), (0x0441, "c"), (0x0443, "y"),
    (0x0445, "x"), (0x0455, "s"), (0x0456, "i"), (0x0458, "j"), (0x04BB, "h"), (0x04CF, "l"),
    (0x0501, "d"), (0x051B, "q"), (0x051D, "w"),
    # Cyrillic capital letters
    (0x0405, "S"), (0x0406, "I"), (0x0408, "J"), (0x0410, "A"), (0x0412, "B"), (0x0415, "E"),
    (0x041A, "K"), (0x041C, "M"), (0x041D, "H"), (0x041E, "O"), (0x0420, "P"), (0x0421, "C"),
    (0x0422, "T"), (0x0423, "Y"), (0x0425, "X"),
    # Greek
    (0x03B1, "a"), (0x03B9, "i"), (0x03BD, "v"), (0x03BF, "o"),
    (0x0391, "A"), (0x0392, "B"), (0x0395, "E"), (0x0396, "Z"), (0x0397, "H"), (0x0399, "I"),
    (0x039A, "K"), (0x039C, "M"), (0x039D, "N"), (0x039F, "O"), (0x03A1, "P"), (0x03A4, "T"),
    (0x03A5, "Y"), (0x03A7, "X"),
])
for _i in range(26):  # fullwidth Latin letters
    CONFUSABLE[chr(0xFF21 + _i)] = chr(0x41 + _i)
    CONFUSABLE[chr(0xFF41 + _i)] = chr(0x61 + _i)

# Tag names a look-alike tag must read as (lower case), and the Java conversions a look-alike
# conversion letter must read as.
TAGS = frozenset("a b i u p s q br em tt li ul ol big small font strong sup sub strike span div "
                 "del ins code pre h1 h2 h3 h4 h5 h6 annotation xliff:g".split())
CONVERSIONS = frozenset("sSdfxXcCoeEgGaAbBhH")

# "<" or "&lt;", an optional "/", a name, then whitespace, ">", "/" or "&gt;".
TAG = re.compile(r"(?:<|&lt;)(/?)([^\s<>/&\"'=;%]{1,12})(?=[\s>/]|&gt;)")
# "%" (not "%%"), optional "n$", flags (no space), width, precision, then one character.
FMT = re.compile(r"(?<!%)%([0-9]+\$)?([-#+0,(]*)([0-9]*)(\.[0-9]+)?(\S)")
# Start of a string resource element and its name.
ELEM = re.compile(r"<(string-array|integer-array|string|plurals|array)(?=[\s>])[^>]*?"
                  r"\bname\s*=\s*\"([^\"]*)\"")
NOT_LOCALE = frozenset(["car"])


def clean_text(value):
    """Join surrogate pairs and replace lone halves with U+FFFD, so CSV writing can't fail."""
    if not isinstance(value, str):
        return value
    return value.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def ascii_form(text):
    return "".join(CONFUSABLE.get(c, c) for c in text)


def script(c):
    cp = ord(c)
    if 0x0400 <= cp <= 0x052F:
        return "cyrillic"
    if 0x0370 <= cp <= 0x03FF:
        return "greek"
    if 0xFF00 <= cp <= 0xFFEF:
        return "fullwidth"
    return "other"


def locale_of(dirname):
    """The language part of a translation folder name ('ru' for values-ru-rRU, 'b+sr+Latn' for
    values-b+sr+Latn), or None for values/ and qualifier-only folders (values-night, values-v21)."""
    parts = dirname.split("-")
    if parts[0] != "values" or len(parts) < 2:
        return None
    p = parts[1]
    if p in NOT_LOCALE:
        return None
    if re.fullmatch("[a-z]{2,3}", p) or p.startswith("b+"):
        return p
    return None


def scan_text(text):
    """(hits, ascii counts) in the raw text of one translation file.

    A hit is a dict with kind ('tag' or 'fmt'), pos, token (the matched text), letters (its
    look-alike letters) and script (the alphabet of the first one)."""
    hits = []
    counts = collections.Counter()
    for m in TAG.finditer(text):
        name = m.group(2)
        skel = ascii_form(name)
        if not skel.isascii() or skel.lower() not in TAGS:
            continue
        if name.isascii():
            counts["ascii_tag"] += 1
            continue
        letters = "".join(c for c in name if not c.isascii())
        hits.append({"kind": "tag", "pos": m.start(), "token": text[m.start():m.end()],
                     "letters": letters, "script": script(letters[0])})
    for m in FMT.finditer(text):
        conv = m.group(5)
        positional = m.group(1) is not None
        nxt = text[m.end():m.end() + 1]
        if not positional and nxt.isalpha():
            continue  # the letter starts a word: "%" then text, not a specifier
        if conv.isascii():
            if conv in CONVERSIONS:
                counts["ascii_fmt"] += 1
            continue
        if CONFUSABLE.get(conv) not in CONVERSIONS:
            continue
        hits.append({"kind": "fmt", "pos": m.start(), "token": m.group(0), "letters": conv,
                     "script": script(conv)})
    hits.sort(key=lambda h: h["pos"])
    return hits, counts


def element_starts(text):
    """Sorted (position, 'kind:name') of every string resource element in raw XML text."""
    return [(m.start(), "%s:%s" % (m.group(1), m.group(2))) for m in ELEM.finditer(text)]


def key_at(starts, pos):
    """The key of the last element that starts before `pos`, or '' if none."""
    i = bisect.bisect_right([s for s, _ in starts], pos) - 1
    return starts[i][1] if i >= 0 else ""


def source_block(src_text, key):
    """Raw inner text of the element `key` ('kind:name') in the source file, or None."""
    if not src_text or ":" not in key:
        return None
    kind, name = key.split(":", 1)
    m = re.search(r"<%s(?=[\s>])[^>]*?\bname\s*=\s*\"%s\"[^>]*>(.*?)</%s\s*>"
                  % (re.escape(kind), re.escape(name), re.escape(kind)), src_text, re.S)
    return m.group(1) if m else None


def source_has(hit, block):
    """True if the source block has the hit's token written in plain ASCII."""
    if block is None:
        return False
    token = ascii_form(hit["token"]).replace("&lt;", "<")
    block = block.replace("&lt;", "<")
    if hit["kind"] == "tag":
        return token.lower() in block.lower()
    return token in block


def context(text, pos, width=60):
    return text[max(0, pos - width):pos + width].replace("\r", "").replace("\n", "\\n")


def read_text(path):
    with open(path, "rb") as f:
        return f.read().decode("utf-8", "replace")


def scan_res_dir(root, dirpath, dirnames):
    rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
    counts, rows, sources = collections.Counter(), [], {}
    for d in sorted(dirnames):
        if locale_of(d) is None:
            continue
        for fn in sorted(os.listdir(os.path.join(dirpath, d))):
            path = os.path.join(dirpath, d, fn)
            if not fn.endswith(".xml") or not os.path.isfile(path):
                continue
            counts["locale_files"] += 1
            text = read_text(path)
            hits, c = scan_text(text)
            counts.update(c)
            if not hits:
                continue
            if fn not in sources:
                sp = os.path.join(dirpath, "values", fn)
                sources[fn] = read_text(sp) if os.path.isfile(sp) else None
            starts = element_starts(text)
            for i, h in enumerate(hits):
                key = key_at(starts, h["pos"])
                block = source_block(sources[fn], key)
                counts["hit_" + h["kind"]] += 1
                rows.append({"res_dir": rel, "locale_dir": d, "file": fn, "key": key, "index": i,
                             "kind": h["kind"], "token": h["token"], "letters": h["letters"],
                             "codepoints": " ".join("U+%04X" % ord(c) for c in h["letters"]),
                             "script": h["script"], "source_has": source_has(h, block),
                             "context": context(text, h["pos"]),
                             "source": (block or "").strip().replace("\n", "\\n")[:200]})
    return counts, rows


def scan_repo(root):
    counts, rows = collections.Counter(), []
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        if os.path.basename(dirpath) != "res" or "values" not in dirnames:
            continue
        c, r = scan_res_dir(root, dirpath, dirnames)
        counts.update(c)
        rows += r
    return counts, rows


def process_repo(url, tmp_root):
    d = tempfile.mkdtemp(dir=tmp_root)
    res = {"repo": url, "status": "ok", "counts": collections.Counter(), "rows": []}
    t0 = time.time()
    try:
        s = os.path.join(d, "s")
        r = cl.git(["clone", "--quiet", "--depth", "1", "--filter=blob:none", "--no-checkout",
                    "--single-branch", url, s])
        if r.returncode != 0:
            res.update(status="clone-failed",
                       error=(r.stderr.strip().splitlines() or [""])[-1][:200])
            return res
        cl.git(["-C", s, "sparse-checkout", "set", "--no-cone"] + cl.SPARSE)
        branch = cl.git(["-C", s, "symbolic-ref", "--short", "HEAD"]).stdout.strip()
        cl.git(["-C", s, "checkout", "--quiet"] + ([branch] if branch else []))
        if not cl.has_values(s):
            cl.git(["-C", s, "read-tree", "-mu", "HEAD"])
        res["head"] = cl.git(["-C", s, "rev-parse", "HEAD"]).stdout.strip()
        res["counts"], res["rows"] = scan_repo(s)
        if not res["counts"].get("locale_files"):
            res["status"] = "no-locale"
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


# ---------------------------------------------------------------- tables, sample, grading

COUNT_KEYS = ("locale_files", "ascii_tag", "ascii_fmt", "hit_tag", "hit_fmt")


def tables(results):
    """Counts over repositories read (status ok or no-locale)."""
    t = {"repos_read": len(results),
         "repos_locale": sum(1 for r in results if r["counts"].get("locale_files"))}
    for k in COUNT_KEYS:
        t[k] = sum(r["counts"].get(k, 0) for r in results)
    t["repos_tag"] = sum(1 for r in results if r["counts"].get("hit_tag"))
    t["repos_fmt"] = sum(1 for r in results if r["counts"].get("hit_fmt"))
    t["repos_any"] = sum(1 for r in results if r["rows"])
    t["repos_cyrillic"] = sum(1 for r in results
                              if any(x["script"] == "cyrillic" for x in r["rows"]))
    t["hits_source_has"] = sum(1 for r in results for x in r["rows"] if x["source_has"])
    t["hits_by_script"] = dict(collections.Counter(x["script"] for r in results
                                                   for x in r["rows"]))
    t["hits_by_locale"] = dict(collections.Counter(locale_of(x["locale_dir"]) for r in results
                                                   for x in r["rows"]))
    return t


def grade(t):
    """Pre-registered verdicts K1-K3 (PREREG.md); K4 is graded by hand from sample.csv."""
    if t["repos_read"] < GATE_REPOS:
        return {k: "NOT TESTABLE (gate)" for k in ("K1", "K2", "K3", "K4")}
    v = {"K1": "HELD" if t["repos_any"] >= K1_MIN_REPOS else "FAILED"}
    if t["repos_any"] == 0:
        v["K2"] = v["K3"] = "NOT TESTABLE (no hits)"
    else:
        v["K2"] = "HELD" if 2 * t["repos_cyrillic"] > t["repos_any"] else "FAILED"
        v["K3"] = "HELD" if t["repos_tag"] > t["repos_fmt"] else "FAILED"
    v["K4"] = "PENDING (hand check of sample.csv)"
    return v


def grade_k4(labels):
    """K4 from hand labels ('defect', 'fine', 'other'), one per sampled row."""
    if len(labels) < K4_MIN_ROWS:
        return "NOT TESTABLE"
    d = sum(1 for x in labels if x == "defect")
    return "HELD" if d * K4_DEN >= len(labels) * K4_NUM else "FAILED"


def location(x):
    return "%s|%s|%s|%s|%s|%s|%s" % (SALT, x["repo"], x["res_dir"], x["locale_dir"], x["file"],
                                     x["key"], x["index"])


def draw_sample(rows, size=SAMPLE_SIZE):
    """One hit per repository (lowest hash of SALT + its location), repositories in order of the
    hash of SALT + URL, up to `size`. Fixed in PREREG.md."""
    best = {}
    for x in rows:
        h = sha(location(x))
        if x["repo"] not in best or h < best[x["repo"]][0]:
            best[x["repo"]] = (h, x)
    order = sorted(best, key=lambda r: sha(SALT + "|" + r))
    return [best[r][1] for r in order[:size]]


def control():
    """The finder must behave on fixed cases before any repository is read (PREREG.md).
    Each case: text, then the expected list of (kind, letters)."""
    a, i, s, dze = chr(0x0430), chr(0x0456), chr(0x0441), chr(0x0455)
    cases = [
        ("Список изменений <a href=\"https://x.org\">по ссылке</" + a + "> онлайн.",
         [("tag", a)]),
        ("&lt;b&gt;Привет&lt;/b&gt;", []),
        ("Введите &lt;имя&gt;", []),
        ("Файл %1$" + dze + " удалён", [("fmt", dze)]),
        ("Скидка 50% " + s + " картой", []),
        ("Готово на 100%", []),
        ("%1$s и %2$d", []),
        ("50%%" + s, []),
        ("<" + i + ">курсив</" + i + ">", [("tag", i), ("tag", i)]),
        ("Fichier %" + chr(0xFF53) + " supprimé", [("fmt", chr(0xFF53))]),
        ("&lt;/" + a + "&gt;", [("tag", a)]),
        ("100%" + s + "егодня", []),
    ]
    for text, want in cases:
        hits, _ = scan_text(text)
        if [(h["kind"], h["letters"]) for h in hits] != want:
            return False
    return True


# ---------------------------------------------------------------- the run

def wait_for(url, mark, minutes):
    """SHA-256 of the file at `url` once it contains `mark`; None if it doesn't in time."""
    end = time.time() + minutes * 60
    while True:
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                text = r.read().decode("utf-8")
            if mark in text:
                return sha(text)
        except OSError:
            pass
        if time.time() > end:
            return None
        time.sleep(60)


ROW_COLS = ["repo", "head", "res_dir", "locale_dir", "file", "key", "index", "kind", "token",
            "letters", "codepoints", "script", "source_has", "context", "source"]
SAMPLE_COLS = ["n"] + ROW_COLS


def write_row(writer, row):
    writer.writerow({k: clean_text(v) for k, v in row.items()})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--repos", help="local repos.txt instead of downloading")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--budget-minutes", type=float, default=200)
    ap.add_argument("--prereg-wait-minutes", type=float, default=300)
    ap.add_argument("--skip-prereg-check", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    started = time.time()
    if cl.VERSION != "0.1.0" or not control():
        print("positive control failed; stopping before reading any repository", file=sys.stderr)
        return 6
    prereg_sha = None
    if not a.skip_prereg_check:
        prereg_sha = wait_for(PREREG_URL, PREREG_MARK, a.prereg_wait_minutes)
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
    print("lookalike %s: %d repositories" % (VERSION, len(repos)), flush=True)

    tmp_root = tempfile.mkdtemp(prefix="lookalike-")
    selftest = {}
    for u in ("https://github.com/TeamNewPipe/NewPipe", "https://gitlab.com/fdroid/fdroidclient"):
        r = process_repo(u, tmp_root)
        selftest[u] = {"status": r["status"], "counts": dict(r["counts"])}
    print("selftest", json.dumps(selftest), flush=True)
    if not any(v["counts"].get("ascii_fmt") for v in selftest.values()):
        print("selftest found no format specifiers; clone method broken, stopping",
              file=sys.stderr)
        return 3

    deadline = time.time() + a.budget_minutes * 60
    results, skipped = [], []
    jl = open(os.path.join(a.out_dir, "repos.jsonl"), "w", encoding="utf-8")
    hf = open(os.path.join(a.out_dir, "hits.csv"), "w", encoding="utf-8", newline="")
    hw = csv.DictWriter(hf, fieldnames=ROW_COLS)
    hw.writeheader()
    all_rows = []

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
                                 "error": clean_text(r.get("error")),
                                 "seconds": r.get("seconds"), "counts": dict(r["counts"])},
                                ensure_ascii=False, sort_keys=True) + "\n")
            for row in r["rows"]:
                full = dict(row, repo=r["repo"], head=r.get("head", ""))
                write_row(hw, full)
                all_rows.append(full)
            if n % 200 == 0:
                jl.flush()
                hf.flush()
                print("%d/%d done, %.0f min" % (n, len(repos), (time.time() - started) / 60),
                      flush=True)
    jl.close()
    hf.close()
    shutil.rmtree(tmp_root, ignore_errors=True)

    ok = [r for r in results if r["status"] in ("ok", "no-locale")]
    t = tables(ok)
    ok_repos = {r["repo"] for r in ok}
    sample = draw_sample([x for x in all_rows if x["repo"] in ok_repos])
    with open(os.path.join(a.out_dir, "sample.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SAMPLE_COLS)
        w.writeheader()
        for i, x in enumerate(sample, 1):
            write_row(w, dict(x, n=i))
    summary = {
        "verdicts": grade(t), "tables": t, "version": VERSION,
        "cyrillic_leak_version": cl.VERSION, "cyrillic_leak_sha256": file_sha(cl.__file__),
        "lookalike_sha256": file_sha(os.path.abspath(__file__)),
        "repos_url": REPOS_URL, "repos_sha256": hashlib.sha256(raw).hexdigest(),
        "prereg_sha256": prereg_sha, "sample_size": len(sample),
        "repos_listed": len(repos), "repos_not_started": len(skipped),
        "status_counts": dict(collections.Counter(r["status"] for r in results)),
        "positive_control": True, "selftest": selftest,
        "minutes": round((time.time() - started) / 60, 1),
    }
    with open(os.path.join(a.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps(summary["verdicts"]), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
