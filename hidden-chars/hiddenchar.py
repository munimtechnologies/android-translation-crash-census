#!/usr/bin/env python3
# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Invisible-character census of shipped Android translations (F-Droid corpus).

For every F-Droid app's source repository, read res/values*/*.xml at the
default branch's latest commit and count translated strings that contain an
invisible character (zero-width space, soft hyphen, bidi controls, other
Unicode format characters) that their English source does not contain.
Repositories are labelled by translation platform from their commit history
(Weblate / Crowdin / Transifex / other), to test whether Weblate's automatic
zero-width-space removal shows up in shipped catalogs. See PREREG.md.

Made with AI agents by MV2 of Munim, Inc. Standard library only; needs git.
"""
import argparse
import collections
import concurrent.futures
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET

VERSION = "0.1.0"
INDEX_URL = "https://f-droid.org/repo/index-v2.json"
SPARSE = "**/res/values*/*.xml"

# Scripts that use U+200B as a word separator (Weblate exempts Khmer).
ZWSP_LANGS = {"th", "lo", "my", "km", "bo", "dz"}
# Right-to-left languages, where LRM/RLM/ALM are expected.
RTL_LANGS = {"ar", "fa", "he", "iw", "ur", "ps", "ckb", "ug", "yi", "ji", "dv",
             "sd", "ks", "pnb", "syr", "nqo", "mzn", "glk", "lrc", "azb", "bal",
             "sdh", "arc"}
# Format characters that are part of normal text, not invisible artifacts.
_ARABIC_SIGNS = set(range(0x0600, 0x0606)) | {0x06DD, 0x070F, 0x0890, 0x0891, 0x08E2}
_TAGS = set(range(0xE0020, 0xE0080))  # emoji tag sequences (subdivision flags)

CLASSES = ("zwsp", "shy", "joiner", "mark", "bidi", "wj-bom", "other-cf")
CONTROL = ("shy", "bidi", "wj-bom", "other-cf")  # never auto-removed by Weblate

_CF = sorted(cp for cp in range(0x110000) if unicodedata.category(chr(cp)) == "Cf")
_INVISIBLE_RE = re.compile("[" + "".join(re.escape(chr(cp)) for cp in _CF) + "]")
_U_ESC = re.compile(r"(?<!\\)\\u([0-9A-Fa-f]{4})")
_LOCALE_DIR = re.compile(
    r"^values-(?:([a-z]{2,3})(?:-r([A-Z]{2}|[0-9]{3}))?|b\+([a-zA-Z]{2,3})(?:\+[A-Za-z0-9]+)*)$")
_NOT_LOCALES = {"car"}  # UI-mode qualifier, not a language
_PSEUDO = {("en", "XA"), ("ar", "XB")}


def char_class(cp):
    """Class of one code point, or None if it is not an invisible character we count."""
    if cp == 0x200B:
        return "zwsp"
    if cp == 0x00AD:
        return "shy"
    if cp in (0x200C, 0x200D):
        return "joiner"
    if cp in (0x200E, 0x200F, 0x061C):
        return "mark"
    if 0x202A <= cp <= 0x202E or 0x2066 <= cp <= 0x2069:
        return "bidi"
    if cp in (0x2060, 0xFEFF):
        return "wj-bom"
    if cp < 0xA0 or cp in _ARABIC_SIGNS or cp in _TAGS:
        return None
    if unicodedata.category(chr(cp)) == "Cf":
        return "other-cf"
    return None


def decode_android(text):
    """Apply Android's \\uXXXX escapes (aapt decodes them at build time)."""
    return _U_ESC.sub(lambda m: chr(int(m.group(1), 16)), text)


def locale_of(dirname):
    """Base language of a values-* directory, or None if it is not a plain locale folder."""
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
    """{key: [texts]} for <string>, <plurals> and <string-array> in one values file.

    Keys marked translatable="false" map to None so they can be dropped from the source.
    """
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


def merge_dir(folder, errors):
    merged = {}
    for fn in sorted(os.listdir(folder)):
        if not fn.endswith(".xml"):
            continue
        try:
            merged.update(parse_values(os.path.join(folder, fn)))
        except (ET.ParseError, ValueError, OSError):
            errors.append(os.path.join(folder, fn))
    return merged


def extra_chars(source_text, target_text):
    """{class: sorted code points} present in the target but not in the source."""
    src = set(map(ord, source_text))
    extra = {}
    for ch in _INVISIBLE_RE.findall(target_text):
        cp = ord(ch)
        cls = char_class(cp)
        if cls and cp not in src:
            extra.setdefault(cls, set()).add(cp)
    return {k: sorted(v) for k, v in extra.items()}


def is_primary(classes, lang):
    """True if any extra class is unexpected for this language."""
    for cls in classes:
        if cls == "zwsp" and lang not in ZWSP_LANGS:
            return True
        if cls == "mark" and lang not in RTL_LANGS:
            return True
        if cls in CONTROL:
            return True
    return False


def is_control(classes, lang):
    return any(c in CONTROL or (c == "mark" and lang not in RTL_LANGS) for c in classes)


def show(text, limit=200):
    """Text with invisible characters made visible as <U+XXXX>."""
    out = []
    for ch in text:
        cp = ord(ch)
        if char_class(cp) or (unicodedata.category(ch) in ("Cf", "Cc") and ch not in "\n\t"):
            out.append("<U+%04X>" % cp)
        else:
            out.append(ch)
    s = "".join(out).replace("\n", "\\n")
    return s if len(s) <= limit else s[:limit] + "..."


def compare(source, target, lang):
    """Per-locale stats and hits for one target catalog against its source."""
    stats = {"lang": lang, "units": 0, "extra": collections.Counter(), "primary": 0, "control": 0}
    hits = []
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
            src = slist[i] if key.startswith("array:") and i < len(slist) else union
            stats["units"] += 1
            extra = extra_chars(src, t)
            if not extra:
                continue
            for cls in extra:
                stats["extra"][cls] += 1
            if is_control(extra, lang):
                stats["control"] += 1
            if is_primary(extra, lang):
                stats["primary"] += 1
                hits.append({"key": key, "index": i, "classes": ";".join(sorted(extra)),
                             "codepoints": " ".join("U+%04X" % cp for v in extra.values() for cp in v),
                             "source": show(src), "target": show(t)})
    stats["extra"] = dict(stats["extra"])
    return stats, hits


def scan_checkout(root):
    """Scan every res/ folder under root. Returns ({locale_key: stats}, hits, parse_errors)."""
    locales, hits, errors = {}, [], []
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        if os.path.basename(dirpath) != "res" or "values" not in dirnames:
            continue
        source = {k: v for k, v in merge_dir(os.path.join(dirpath, "values"), errors).items() if v}
        if not source:
            continue
        rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
        for d in dirnames:
            lang = locale_of(d)
            if not lang:
                continue
            target = {k: v for k, v in merge_dir(os.path.join(dirpath, d), errors).items() if v}
            stats, h = compare(source, target, lang)
            if stats["units"] == 0:
                continue
            lk = rel + "/" + d
            locales[lk] = stats
            for row in h:
                row.update({"res_dir": rel, "locale_dir": d, "lang": lang})
                hits.append(row)
    return locales, hits, [os.path.relpath(e, root).replace(os.sep, "/") for e in errors]


def detect_platform(log):
    """Translation platform from `git log --format=%ce%x1f%cn%x1f%ae%x1f%an%x1f%s` output."""
    w = c = t = False
    for line in log.splitlines():
        f = [x.lower() for x in line.split("\x1f")]
        if len(f) < 5:
            continue
        ce, cn, ae, an, subj = f[:5]
        if "weblate" in ce or "weblate" in cn or "weblate" in ae or "weblate" in an or "using weblate" in subj:
            w = True
        if ("crowdin" in ce or "crowdin" in cn or "crowdin" in ae or "crowdin" in an
                or re.match(r"new translations? .+\(.+\)", subj)):
            c = True
        if "transifex" in ae or "transifex" in an or "transifex" in subj:
            t = True
    return "weblate" if w else "crowdin" if c else "transifex" if t else "other"


def clone_url(src):
    """Normalised https clone URL for an F-Droid sourceCode link, or None."""
    if not isinstance(src, str):
        return None
    s = src.strip().split("#")[0].split("?")[0]
    m = re.match(r"^https?://([^/]+)(/.*)?$", s)
    if not m:
        return None
    host = m.group(1).lower()
    if host.startswith("www."):
        host = host[4:]
    parts = [p for p in (m.group(2) or "").split("/") if p]
    for i, p in enumerate(parts):
        if i >= 2 and p in ("-", "tree", "blob", "src", "commits", "issues", "wiki", "releases"):
            parts = parts[:i]
            break
    if host in ("github.com", "codeberg.org", "bitbucket.org", "notabug.org"):
        parts = parts[:2]
    if len(parts) < 2:
        return None
    if parts[-1].endswith(".git"):
        parts[-1] = parts[-1][:-4]
    return "https://%s/%s" % (host, "/".join(parts))


def load_sources(index):
    urls = {}
    for _, entry in sorted(index.get("packages", {}).items()):
        u = clone_url((entry.get("metadata") or {}).get("sourceCode"))
        if u:
            urls.setdefault(u.lower(), u)
    return [urls[k] for k in sorted(urls)]


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
            return res, []
        git(["-C", s, "sparse-checkout", "set", "--no-cone", SPARSE])
        branch = git(["-C", s, "symbolic-ref", "--short", "HEAD"]).stdout.strip()
        git(["-C", s, "checkout", "--quiet"] + ([branch] if branch else []))
        if not has_values(s):
            git(["-C", s, "read-tree", "-mu", "HEAD"])
        res["head"] = git(["-C", s, "rev-parse", "HEAD"]).stdout.strip()
        locales, hits, errors = scan_checkout(s)
        res["locales"] = locales
        res["parse_errors"] = len(errors)
        res["units"] = sum(v["units"] for v in locales.values())
        if res["units"] == 0:
            res["status"] = "no-translations"
            return res, []
        h = os.path.join(d, "h")
        r = git(["clone", "--quiet", "--bare", "--filter=tree:0", "--single-branch", url, h])
        if r.returncode == 0:
            log = git(["-C", h, "log", "-n", "200000",
                       "--format=%ce%x1f%cn%x1f%ae%x1f%an%x1f%s"]).stdout
            res["commits"] = log.count("\n")
            res["platform"] = detect_platform(log)
        else:
            res["platform"] = "unknown"
        for row in hits[:500]:
            row.update({"repo": url, "head": res["head"], "platform": res["platform"]})
        res["hits"] = len(hits)
        return res, hits[:500]
    except subprocess.TimeoutExpired:
        res["status"] = "timeout"
        return res, []
    except Exception as e:  # keep the census going; record what broke
        res.update(status="error", error=repr(e)[:200])
        return res, []
    finally:
        res["seconds"] = round(time.time() - t0, 1)
        shutil.rmtree(d, ignore_errors=True)


def ratio(a, b):
    return a / b if b else None


def aggregate(results):
    """Pooled rates per group and the pre-registered verdicts (PREREG.md)."""
    ok = [r for r in results if r.get("status") == "ok"]
    groups = {"weblate": collections.Counter(), "non-weblate": collections.Counter()}
    by_platform = collections.Counter(r.get("platform", "unknown") for r in ok)
    by_lang = collections.defaultdict(collections.Counter)
    class_hits = collections.Counter()
    mark_rtl = mark_all = 0
    repos_primary = 0
    for r in ok:
        g = None
        if r.get("platform") == "weblate":
            g = groups["weblate"]
        elif r.get("platform") in ("crowdin", "transifex", "other"):
            g = groups["non-weblate"]
        prim = 0
        for st in r["locales"].values():
            lang, ex = st["lang"], st["extra"]
            prim += st["primary"]
            bl = by_lang[lang]
            bl["units"] += st["units"]
            bl["primary"] += st["primary"]
            for cls, n in ex.items():
                bl[cls] += n
            if lang not in ZWSP_LANGS:
                class_hits["zwsp"] += ex.get("zwsp", 0)
            for cls in CONTROL:
                class_hits[cls] += ex.get(cls, 0)
            if lang not in RTL_LANGS:
                class_hits["mark"] += ex.get("mark", 0)
            mark_all += ex.get("mark", 0)
            if lang in RTL_LANGS:
                mark_rtl += ex.get("mark", 0)
            if g is not None:
                if lang not in ZWSP_LANGS:
                    g["zwsp_units"] += st["units"]
                    g["zwsp_hits"] += ex.get("zwsp", 0)
                g["units"] += st["units"]
                g["control_hits"] += st["control"]
        if g is not None:
            g["repos"] += 1
            g["repos_zwsp"] += int(any(st["extra"].get("zwsp", 0) and st["lang"] not in ZWSP_LANGS
                                       for st in r["locales"].values()))
        repos_primary += int(prim > 0)

    def rates(g):
        return {"repos": g["repos"], "units": g["units"], "zwsp_units": g["zwsp_units"],
                "zwsp_hits": g["zwsp_hits"], "control_hits": g["control_hits"],
                "zwsp_rate": ratio(g["zwsp_hits"], g["zwsp_units"]),
                "control_rate": ratio(g["control_hits"], g["units"]),
                "repos_with_zwsp": g["repos_zwsp"],
                "repo_share_zwsp": ratio(g["repos_zwsp"], g["repos"])}

    W, N = rates(groups["weblate"]), rates(groups["non-weblate"])
    verdicts = {}
    share = ratio(repos_primary, len(ok))
    verdicts["P1"] = "NOT TESTABLE" if share is None else ("HELD" if share >= 0.03 else "FAILED")
    rz = ratio(W["zwsp_rate"], N["zwsp_rate"]) if W["zwsp_rate"] is not None and N["zwsp_rate"] else None
    rc = ratio(W["control_rate"], N["control_rate"]) if W["control_rate"] is not None and N["control_rate"] else None
    if rz is None or rc is None:
        verdicts["P2"] = "NOT TESTABLE"
    else:
        verdicts["P2"] = "HELD" if rz < 0.5 and rz < rc else "FAILED"
    verdicts["P3"] = ("NOT TESTABLE" if not mark_all
                      else "HELD" if mark_rtl / mark_all >= 0.8 else "FAILED")
    others = [class_hits[c] for c in CONTROL + ("mark",)]
    verdicts["P4"] = ("NOT TESTABLE" if not class_hits["zwsp"] and not any(others)
                      else "HELD" if class_hits["zwsp"] > max(others) else "FAILED")
    return {
        "repos_ok": len(ok), "repos_with_primary": repos_primary, "repo_share_primary": share,
        "by_platform": dict(by_platform), "weblate": W, "non_weblate": N,
        "zwsp_rate_ratio_W_over_N": rz, "control_rate_ratio_W_over_N": rc,
        "primary_class_hits": dict(class_hits), "mark_units_rtl": mark_rtl, "mark_units_all": mark_all,
        "by_lang": {k: dict(v) for k, v in sorted(by_lang.items())},
        "verdicts": verdicts,
    }


def without_top(results, platform_group):
    """Results with the single repo contributing most zero-width-space hits in a group removed."""
    def in_group(r):
        p = r.get("platform")
        return p == "weblate" if platform_group == "weblate" else p in ("crowdin", "transifex", "other")

    def zw(r):
        return sum(st["extra"].get("zwsp", 0) for st in r.get("locales", {}).values()
                   if st["lang"] not in ZWSP_LANGS)
    cands = [r for r in results if r.get("status") == "ok" and in_group(r)]
    if not cands:
        return results
    top = max(cands, key=zw)
    return [r for r in results if r is not top]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--index", help="local index-v2.json instead of downloading")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--budget-minutes", type=float, default=270)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    started = time.time()
    if a.index:
        with open(a.index, encoding="utf-8") as f:
            index = json.load(f)
    else:
        with urllib.request.urlopen(INDEX_URL, timeout=300) as resp:
            index = json.loads(resp.read().decode("utf-8"))
    index_ts = (index.get("repo") or {}).get("timestamp")
    repos = load_sources(index)
    del index
    if a.limit:
        repos = repos[:a.limit]
    with open(os.path.join(a.out_dir, "repos.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(repos) + "\n")
    print("hiddenchar %s: %d repositories" % (VERSION, len(repos)), flush=True)

    tmp_root = tempfile.mkdtemp(prefix="hiddenchar-")
    # Self-test: the clone method must find translations in two well-known apps.
    selftest = {}
    for u in ("https://gitlab.com/fdroid/fdroidclient", "https://github.com/TeamNewPipe/NewPipe"):
        r, _ = process_repo(u, tmp_root)
        selftest[u] = {"status": r["status"], "units": r.get("units", 0), "platform": r.get("platform")}
    print("selftest", json.dumps(selftest), flush=True)
    if not any(v["units"] for v in selftest.values()):
        print("selftest found no translations; clone method broken, stopping", file=sys.stderr)
        with open(os.path.join(a.out_dir, "selftest.json"), "w", encoding="utf-8") as f:
            json.dump(selftest, f, indent=1)
        return 3

    deadline = started + a.budget_minutes * 60
    results, lock = [], threading.Lock()
    jl = open(os.path.join(a.out_dir, "repos.jsonl"), "w", encoding="utf-8")
    hf = open(os.path.join(a.out_dir, "hits.csv"), "w", encoding="utf-8", newline="")
    cols = ["repo", "head", "platform", "res_dir", "locale_dir", "lang", "key", "index",
            "classes", "codepoints", "source", "target"]
    hw = csv.DictWriter(hf, fieldnames=cols)
    hw.writeheader()
    skipped = []

    def work(u):
        if time.time() > deadline:
            return {"repo": u, "status": "not-started"}, []
        return process_repo(u, tmp_root)

    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for n, (r, hits) in enumerate(ex.map(work, repos), 1):
            with lock:
                if r["status"] == "not-started":
                    skipped.append(r["repo"])
                    continue
                results.append(r)
                jl.write(json.dumps(r, sort_keys=True) + "\n")
                for row in hits:
                    hw.writerow({k: row.get(k, "") for k in cols})
                if n % 100 == 0:
                    jl.flush()
                    hf.flush()
                    print("%d/%d done, %.0f min" % (n, len(repos), (time.time() - started) / 60), flush=True)
    jl.close()
    hf.close()
    shutil.rmtree(tmp_root, ignore_errors=True)

    summary = aggregate(results)
    summary["sensitivity_without_top_zwsp_repo"] = {
        g: aggregate(without_top(results, g))["zwsp_rate_ratio_W_over_N"] for g in ("weblate", "non-weblate")}
    summary.update({
        "version": VERSION, "index_url": INDEX_URL, "index_timestamp": index_ts,
        "repos_listed": len(repos), "repos_not_started": len(skipped),
        "status_counts": dict(collections.Counter(r["status"] for r in results)),
        "selftest": selftest, "minutes": round((time.time() - started) / 60, 1),
    })
    with open(os.path.join(a.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1, sort_keys=True)
    with open(os.path.join(a.out_dir, "by_lang.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["lang", "units", "primary"] + list(CLASSES))
        for lang, c in summary["by_lang"].items():
            w.writerow([lang, c.get("units", 0), c.get("primary", 0)] + [c.get(k, 0) for k in CLASSES])
    print(json.dumps(summary["verdicts"]), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
