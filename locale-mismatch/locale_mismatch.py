#!/usr/bin/env python3
# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Android translation folders whose text is not in the folder's language (pre-registered).

For every repository in hidden-chars/repos.txt (the F-Droid source repositories of the census),
reads the Android string resources at HEAD and checks each translation folder (values-<locale>)
as a whole:

  not-a-language    the folder's two-letter code is not an ISO 639-1 language (values-ua,
                    values-jp, values-cz): no system language ever selects it;
  wrong-script:X    most translated strings are in script X, not the language's own
                    (Cyrillic text in values-ko);
  latin             most translated strings are Latin-only in a language with its own script;
  ja-no-kana        a Japanese folder where under 10% of the CJK strings have kana (Chinese text);
  zh-kana           a Chinese folder where at least 25% of the CJK strings have kana (Japanese);
  cyrillic-letters  a Russian, Ukrainian or Belarusian folder where more strings carry letters of
                    another of the three languages than of its own (Ukrainian in values-ru-rUA).

For repositories with a not-a-language folder it then checks whether the code is referenced
anywhere in the app's Java/Kotlin/Gradle sources, manifest, res/xml or default values XML (an
in-app language picker could select it). See PREREG.md for the predictions and how they are graded.

Same corpus and clone method as cyrillic_leak.py 0.1.0, whose git(), parse_values() and norm()
helpers are imported unchanged (downloaded from the census repository during setup). Needs git.

Made with AI agents by MV2 of Munim, Inc. Standard library only.
"""
import argparse
import collections
import concurrent.futures
import csv
import functools
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

VERSION = "0.1.0"
BASE = cl.BASE
REPOS_URL = BASE + "hidden-chars/repos.txt"
PREREG_URL = BASE + "locale-mismatch/PREREG.md"
PREREG_MARK = "locale-mismatch PREREG v1"
SELFTEST_REPOS = ("https://github.com/TeamNewPipe/NewPipe", "https://gitlab.com/fdroid/fdroidclient")
KNOWN_CASE = ("https://github.com/FreezeYou/FreezeYou", "values-ru-rUA")
SPARSE = cl.SPARSE  # ["**/res/values*/*.xml"]
SOURCE_SPARSE = ["**/*.java", "**/*.kt", "**/*.gradle", "**/*.kts", "**/AndroidManifest.xml",
                 "**/res/xml/*.xml", "**/res/values/*.xml"]
REF_EXT = (".java", ".kt", ".gradle", ".kts", ".xml")

# Pre-registered thresholds (PREREG.md).
GATE_REPOS_READ = 4000
MIN_UNITS = 10
MIN_CJK = 20
L1_MIN_REPOS = 5
L3_MIN_REPOS = 5
SAMPLE_SIZE = 40
L2_MIN_SAMPLE = 8

# ISO 639-1 (183 codes) and the legacy or deprecated codes Android still accepts.
ISO639_1 = frozenset("""
aa ab ae af ak am an ar as av ay az ba be bg bi bm bn bo br bs ca ce ch co cr cs cu cv cy da de dv
dz ee el en eo es et eu fa ff fi fj fo fr fy ga gd gl gn gu gv ha he hi ho hr ht hu hy hz ia id ie
ig ii ik io is it iu ja jv ka kg ki kj kk kl km kn ko kr ks ku kv kw ky la lb lg li ln lo lt lu lv
mg mh mi mk ml mn mr ms mt my na nb nd ne ng nl nn no nr nv ny oc oj om or os pa pi pl ps pt qu rm
rn ro ru rw sa sc sd se sg si sk sl sm sn so sq sr ss st su sv sw ta te tg th ti tk tl tn to tr ts
tt tw ty ug uk ur uz ve vi vo wa wo xh yi yo za zh zu
""".split())
LEGACY = frozenset({"in", "iw", "ji", "mo", "sh", "bh"})

# The script each checked language is written in (languages written in more than one script,
# such as sr, uz, az, pa, ku, mn, sd, are not checked).
EXPECT = {}
for _script, _langs in (
        ("Cyrillic", "ru uk be bg mk kk ky tg tt ba cv os ce kv av"),
        ("Greek", "el"), ("Armenian", "hy"), ("Hebrew", "he iw yi ji"),
        ("Arabic", "ar fa ur ps ckb ug"), ("Devanagari", "hi mr ne sa"),
        ("Bengali", "bn as"), ("Gujarati", "gu"), ("Oriya", "or"), ("Tamil", "ta"),
        ("Telugu", "te"), ("Kannada", "kn"), ("Malayalam", "ml"), ("Sinhala", "si"),
        ("Thai", "th"), ("Lao", "lo"), ("Tibetan", "bo dz"), ("Myanmar", "my"),
        ("Georgian", "ka"), ("Hangul", "ko"), ("Ethiopic", "am ti"), ("Khmer", "km"),
        ("Kana", "ja"), ("Han", "zh")):
    for _l in _langs.split():
        EXPECT[_l] = _script

# Letters of another of the three languages (a) and of the folder's own language (b).
CYR_RULES = {"ru": ("іїєґў", "ыэёъ"), "uk": ("ыэёъ", "іїєґ"), "be": ("ищ", "ў")}

_RANGES = (
    (0x0370, 0x03FF, "Greek"), (0x1F00, 0x1FFF, "Greek"), (0x0400, 0x052F, "Cyrillic"),
    (0x1C80, 0x1C8F, "Cyrillic"), (0x2DE0, 0x2DFF, "Cyrillic"), (0xA640, 0xA69F, "Cyrillic"),
    (0x0530, 0x058F, "Armenian"), (0x0590, 0x05FF, "Hebrew"), (0xFB1D, 0xFB4F, "Hebrew"),
    (0x0600, 0x06FF, "Arabic"), (0x0750, 0x077F, "Arabic"), (0x08A0, 0x08FF, "Arabic"),
    (0xFB50, 0xFDFF, "Arabic"), (0xFE70, 0xFEFF, "Arabic"), (0x0900, 0x097F, "Devanagari"),
    (0x0980, 0x09FF, "Bengali"), (0x0A00, 0x0A7F, "Gurmukhi"), (0x0A80, 0x0AFF, "Gujarati"),
    (0x0B00, 0x0B7F, "Oriya"), (0x0B80, 0x0BFF, "Tamil"), (0x0C00, 0x0C7F, "Telugu"),
    (0x0C80, 0x0CFF, "Kannada"), (0x0D00, 0x0D7F, "Malayalam"), (0x0D80, 0x0DFF, "Sinhala"),
    (0x0E00, 0x0E7F, "Thai"), (0x0E80, 0x0EFF, "Lao"), (0x0F00, 0x0FFF, "Tibetan"),
    (0x1000, 0x109F, "Myanmar"), (0x10A0, 0x10FF, "Georgian"), (0x1C90, 0x1CBF, "Georgian"),
    (0x2D00, 0x2D2F, "Georgian"), (0x1100, 0x11FF, "Hangul"), (0x3130, 0x318F, "Hangul"),
    (0xA960, 0xA97F, "Hangul"), (0xAC00, 0xD7FF, "Hangul"), (0x1200, 0x139F, "Ethiopic"),
    (0x2D80, 0x2DDF, "Ethiopic"), (0x1780, 0x17FF, "Khmer"), (0x19E0, 0x19FF, "Khmer"),
    (0x1800, 0x18AF, "Mongolian"), (0x3040, 0x309F, "Kana"), (0x30A0, 0x30FF, "Kana"),
    (0x31F0, 0x31FF, "Kana"), (0xFF66, 0xFF9F, "Kana"), (0x3400, 0x4DBF, "Han"),
    (0x4E00, 0x9FFF, "Han"), (0xF900, 0xFAFF, "Han"), (0x20000, 0x3134F, "Han"),
)


@functools.lru_cache(maxsize=None)
def script_of(ch):
    """The script of a letter (Unicode category L*), or None for anything that isn't a letter."""
    if not unicodedata.category(ch).startswith("L"):
        return None
    o = ord(ch)
    if (o < 0x0250 or 0x1E00 <= o <= 0x1EFF or 0x2C60 <= o <= 0x2C7F or 0xA720 <= o <= 0xA7FF
            or 0xFF21 <= o <= 0xFF5A):
        return "Latin"
    for lo, hi, name in _RANGES:
        if lo <= o <= hi:
            return name
    return "Other"


def scripts(text):
    out = set()
    for ch in text:
        s = script_of(ch)
        if s:
            out.add(s)
    return out


_DIR = re.compile(
    r"^values-(?:([a-z]{2,3})(?:-r([A-Z]{2}|[0-9]{3}))?|b\+([a-zA-Z]{2,3})((?:\+[A-Za-z0-9]+)*))$")
NOT_LOCALES = {"car"}
PSEUDO = {("en", "XA"), ("ar", "XB")}


def parse_dir(name):
    """(lang, region or None, script or None) of a values-* folder, or None if not a locale."""
    m = _DIR.match(name)
    if not m:
        return None
    if m.group(3):
        lang = m.group(3).lower()
        subs = [x for x in m.group(4).split("+") if x]
        script = next((x.title() for x in subs if len(x) == 4 and x.isalpha()), None)
        region = next((x.upper() for x in subs
                       if (len(x) == 2 and x.isalpha()) or (len(x) == 3 and x.isdigit())), None)
    else:
        lang, region, script = m.group(1), m.group(2), None
        if lang in NOT_LOCALES:
            return None
    if (lang, region) in PSEUDO:
        return None
    return lang, region, script


def not_a_language(lang):
    return len(lang) == 2 and lang not in ISO639_1 and lang not in LEGACY


def clean(text):
    """Lone surrogates (from \\uD83D-style escapes) become '?', so output files always encode."""
    return text.encode("utf-8", "replace").decode("utf-8")


def _add(m, bucket, text):
    ex = m["ex"].setdefault(bucket, [])
    if len(ex) < 3:
        ex.append(clean(text)[:120])


def folder_metrics(lang, pairs):
    """pairs: (text, source item or None, all source items joined), stripped. Identical copies of
    the source item are not translated strings and are skipped."""
    m = {"units": 0, "own": 0, "other": collections.Counter(), "latin": 0, "cjk": 0, "kana": 0,
         "cyr_a": 0, "cyr_b": 0, "ex": {}}
    exp = EXPECT.get(lang)
    own_set = {"ja": {"Kana", "Han"}, "zh": {"Han"}}.get(lang, {exp} if exp else set())
    not_other = {"ja": {"Kana", "Han"}, "zh": {"Han", "Kana"}}.get(lang, {exp} if exp else set())
    rule = CYR_RULES.get(lang)
    for t, s_item, s_all in pairs:
        if s_item is not None and t == s_item:
            continue
        m["units"] += 1
        _add(m, "any", t)
        ts = scripts(t)
        nonlatin = ts - {"Latin", "Other"}
        new = nonlatin - scripts(s_all)
        if ts & own_set:
            m["own"] += 1
        for sc in sorted(new - not_other):
            m["other"][sc] += 1
            _add(m, "script:" + sc, t)
        if "Latin" in ts and not nonlatin:
            m["latin"] += 1
            _add(m, "latin", t)
        if ts & {"Han", "Kana"}:
            m["cjk"] += 1
            if "Kana" in ts:
                m["kana"] += 1
                _add(m, "kana", t)
            else:
                _add(m, "hanonly", t)
        if rule:
            low, slow = cl.norm(t), cl.norm(s_all)
            if any(c in low and c not in slow for c in rule[0]):
                m["cyr_a"] += 1
                _add(m, "cyr", t)
            if any(c in low and c not in slow for c in rule[1]):
                m["cyr_b"] += 1
    return m


def top_other(m):
    """(script, units) of the most common other script; ties go to the alphabetically first."""
    return sorted(m["other"].items(), key=lambda kv: (-kv[1], kv[0]))[0]


def checked(lang, script):
    """Whether the script rules apply to a folder (a known script and no other script subtag)."""
    return lang in EXPECT and (not script or lang == "zh")


def classify(lang, script, m):
    """The pre-registered flags of one folder, in a fixed order."""
    if not_a_language(lang):
        return ["not-a-language"]
    if not checked(lang, script):
        return []
    flags = []
    if lang == "ja" and m["cjk"] >= MIN_CJK and m["kana"] * 10 < m["cjk"]:
        flags.append("ja-no-kana")
    if lang == "zh" and m["cjk"] >= MIN_CJK and m["kana"] * 4 >= m["cjk"]:
        flags.append("zh-kana")
    if m["other"]:
        top, n = top_other(m)
        if n >= MIN_UNITS and n > m["own"]:
            flags.append("wrong-script:" + top)
    if m["latin"] >= MIN_UNITS and m["latin"] > m["own"]:
        flags.append("latin")
    if lang in CYR_RULES and m["cyr_a"] >= MIN_UNITS and m["cyr_a"] > m["cyr_b"]:
        flags.append("cyrillic-letters")
    return flags


BUCKET = {"not-a-language": "any", "ja-no-kana": "hanonly", "zh-kana": "kana", "latin": "latin",
          "cyrillic-letters": "cyr"}


def examples(flags, m):
    if not flags:
        return []
    f = flags[0]
    bucket = "script:" + f.split(":", 1)[1] if f.startswith("wrong-script:") else BUCKET[f]
    return m["ex"].get(bucket, [])


def scan_res_dir(dirpath, dirnames):
    """Every translation folder of one res/ folder that has at least one translated string."""
    out = {"folders": [], "parse_failed": 0}
    cache = {}

    def load(d, fn):
        if (d, fn) not in cache:
            p = os.path.join(dirpath, d, fn)
            try:
                cache[(d, fn)] = cl.parse_values(p) if os.path.isfile(p) else None
            except (ET.ParseError, ValueError, OSError):
                cache[(d, fn)] = None
                out["parse_failed"] += 1
        return cache[(d, fn)]

    for d in sorted(dirnames):
        p = parse_dir(d)
        if not p or not os.path.isdir(os.path.join(dirpath, d)):
            continue
        lang, region, script = p
        pairs = []
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
                s_all = " ".join(x.strip() for x in sl)
                for i, t in enumerate(tl):
                    t = t.strip()
                    if t:
                        pairs.append((t, sl[i].strip() if i < len(sl) else None, s_all))
        m = folder_metrics(lang, pairs)
        if not m["units"]:
            continue
        out["folders"].append({"locale_dir": d, "lang": lang, "region": region or "",
                               "script": script or "", "flags": classify(lang, script, m),
                               "m": m})
    return out


def scan_strings(root):
    total = {"folders": [], "parse_failed": 0}
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        if os.path.basename(dirpath) != "res" or "values" not in dirnames:
            continue
        r = scan_res_dir(dirpath, dirnames)
        rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
        total["parse_failed"] += r["parse_failed"]
        total["folders"] += [dict(f, res_dir=rel) for f in r["folders"]]
    return total


def eligible(folders):
    """Folder counts each rule could have flagged (denominators, exploratory)."""
    c = collections.Counter()
    for f in folders:
        lang, script = f["lang"], f["script"] or None
        c["folders"] += 1
        if len(lang) == 2:
            c["two_letter"] += 1
        if checked(lang, script):
            c["script_checked"] += 1
            if f["region"]:
                c["script_checked_region"] += 1
            if lang in ("ja", "zh"):
                c[lang] += 1
            if lang in CYR_RULES:
                c["cyr"] += 1
    return c


def _ref_patterns(codes):
    return {c: re.compile(r"""(["'])%s(?:[-_][A-Za-z0-9]{2,4})?\1|>\s*%s(?:[-_][A-Za-z0-9]{2,4})?\s*<"""
                          % (re.escape(c), re.escape(c))) for c in codes}


def find_refs(root, codes):
    """{code: True if the code appears quoted ("ua", 'ua-UA') or as an XML item (>ua<) in a
    .java/.kt/.gradle/.kts/.xml file outside values-* folders}."""
    pats = _ref_patterns(codes)
    found = {c: False for c in codes}
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        if os.path.basename(dirpath).startswith("values-"):
            continue
        for fn in sorted(files):
            if not fn.endswith(REF_EXT):
                continue
            p = os.path.join(dirpath, fn)
            try:
                if os.path.getsize(p) > 2000000:
                    continue
                with open(p, encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            for c in codes:
                if not found[c] and pats[c].search(text):
                    found[c] = True
    return found


def _checkout(url, d, sparse):
    s = os.path.join(d, "s")
    r = cl.git(["clone", "--quiet", "--depth", "1", "--filter=blob:none", "--no-checkout",
                "--single-branch", url, s])
    if r.returncode != 0:
        return None, (r.stderr.strip().splitlines() or [""])[-1][:200]
    cl.git(["-C", s, "sparse-checkout", "set", "--no-cone"] + sparse)
    branch = cl.git(["-C", s, "symbolic-ref", "--short", "HEAD"]).stdout.strip()
    cl.git(["-C", s, "checkout", "--quiet"] + ([branch] if branch else []))
    return s, None


def code_references(url, codes, tmp_root):
    """{code: True/False}, head; or ({code: None}, None) if the sources could not be read."""
    d = tempfile.mkdtemp(dir=tmp_root)
    try:
        s, err = _checkout(url, d, SOURCE_SPARSE)
        if not s:
            return {c: None for c in codes}, None
        head = cl.git(["-C", s, "rev-parse", "HEAD"]).stdout.strip()
        return find_refs(s, codes), head
    except Exception:  # keep going; unknown counts against L4
        return {c: None for c in codes}, None
    finally:
        shutil.rmtree(d, ignore_errors=True)


def process_repo(url, tmp_root):
    d = tempfile.mkdtemp(dir=tmp_root)
    res = {"repo": url, "status": "ok"}
    t0 = time.time()
    try:
        s, err = _checkout(url, d, SPARSE)
        if not s:
            res.update(status="clone-failed", error=err)
            return res
        if not cl.has_values(s):
            cl.git(["-C", s, "read-tree", "-mu", "HEAD"])
        res["head"] = cl.git(["-C", s, "rev-parse", "HEAD"]).stdout.strip()
        res.update(scan_strings(s))
        if not res["folders"]:
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


def folder_row(repo, head, f):
    m = f["m"]
    top, top_n = top_other(m) if m["other"] else ("", 0)
    ex = examples(f["flags"], m) + ["", "", ""]
    return {"repo": repo, "head": head, "res_dir": f["res_dir"], "locale_dir": f["locale_dir"],
            "lang": f["lang"], "region": f["region"], "script": f["script"],
            "flags": " ".join(f["flags"]), "units": m["units"], "own": m["own"],
            "top_other": top, "top_other_units": top_n, "latin": m["latin"], "cjk": m["cjk"],
            "kana": m["kana"], "cyr_a": m["cyr_a"], "cyr_b": m["cyr_b"], "code_referenced": "",
            "ex1": ex[0], "ex2": ex[1], "ex3": ex[2]}


def mismatch(row):
    """Whether a flagged folder counts for L1/L2 (any flag other than not-a-language)."""
    return any(x != "not-a-language" for x in row["flags"].split())


def sample_key(repo, res_dir, locale_dir):
    return hashlib.sha256(("locale-mismatch v1|%s|%s|%s" % (repo, res_dir, locale_dir))
                          .encode("utf-8")).hexdigest()


def draw_sample(rows):
    """PREREG sample: per repository the L1 folder with the lowest key, then the first 40 by key."""
    by_repo = collections.defaultdict(list)
    for x in rows:
        if mismatch(x):
            by_repo[x["repo"]].append(x)
    kept = [min(rs, key=lambda x: sample_key(x["repo"], x["res_dir"], x["locale_dir"]))
            for _, rs in sorted(by_repo.items())]
    kept.sort(key=lambda x: sample_key(x["repo"], x["res_dir"], x["locale_dir"]))
    return kept[:SAMPLE_SIZE]


def dead_repos(rows):
    """Repositories with a not-a-language folder, and those where at least one such code was
    found unreferenced (code_referenced == 'no')."""
    l3, dead = set(), set()
    for x in rows:
        if "not-a-language" in x["flags"].split():
            l3.add(x["repo"])
            if x["code_referenced"] == "no":
                dead.add(x["repo"])
    return l3, dead


def grade(n_read, l1_repos, sample_n, l3_repos, n_dead):
    """Pre-registered verdicts (PREREG.md). Integers only."""
    if n_read < GATE_REPOS_READ:
        return {p: "NOT TESTABLE (gate: %d repositories read)" % n_read
                for p in ("L1", "L2", "L3", "L4")}
    v = {"L1": "HELD" if l1_repos >= L1_MIN_REPOS else "FAILED",
         "L2": ("PENDING HAND CHECK (sample of %d)" % sample_n if sample_n >= L2_MIN_SAMPLE
                else "NOT TESTABLE (sample of %d)" % sample_n),
         "L3": "HELD" if l3_repos >= L3_MIN_REPOS else "FAILED"}
    if l3_repos < L3_MIN_REPOS:
        v["L4"] = "NOT TESTABLE (%d repositories)" % l3_repos
    else:
        v["L4"] = "HELD" if n_dead * 2 >= l3_repos else "FAILED"
    return v


def grade_l2(labels):
    """labels: the hand labels of the sample rows, in order."""
    n = len(labels)
    if n < L2_MIN_SAMPLE:
        return "NOT TESTABLE"
    defects = sum(1 for x in labels if x == "defect")
    return "HELD" if defects * 4 >= n * 3 else "FAILED"


def _xml(pairs):
    body = "".join('  <string name="%s">%s</string>\n' % (k, v) for k, v in pairs)
    return '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n%s</resources>\n' % body


def control_tree(d):
    """A synthetic project with seven planted folders and three clean ones."""
    def write(rel, text):
        p = os.path.join(d, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)

    keys = ["s%02d" % n for n in range(20)]
    app, lib = "app/src/main/res/", "lib/src/main/res/"
    write(app + "values/strings.xml", _xml((k, "Open file %d" % n) for n, k in enumerate(keys)))
    write(lib + "values/strings.xml", _xml((k, "Open file %d" % n) for n, k in enumerate(keys)))
    ru = lambda n: "Открыть файл %d" % n
    uk = lambda n: "Відкрити файл %d" % n
    zh = lambda n: "打开文件%d" % n
    ja = lambda n: "ファイルを開く%d" % n
    plant = (
        (app + "values-el/strings.xml", 12, lambda n: "Anoigma arxeiou %d" % n),
        (app + "values-ja/strings.xml", 20, zh),
        (app + "values-ko/strings.xml", 10, ru),
        (app + "values-ru/strings.xml", 12, ru),
        (app + "values-ru-rUA/strings.xml", 12, uk),
        (app + "values-ua/strings.xml", 3, uk),
        (app + "values-uk/strings.xml", 12, uk),
        (app + "values-zh-rCN/strings.xml", 20, ja),
        (lib + "values-ja/strings.xml", 20, ja),
        (lib + "values-jp/strings.xml", 3, ja),
    )
    for rel, n, fn in plant:
        write(rel, _xml((keys[i], fn(i)) for i in range(n)))
    write("lib/src/main/java/Lang.kt", 'val l = java.util.Locale("jp")\n')


CONTROL_WANT = [
    ("app/src/main/res", "values-el", "latin"),
    ("app/src/main/res", "values-ja", "ja-no-kana"),
    ("app/src/main/res", "values-ko", "wrong-script:Cyrillic"),
    ("app/src/main/res", "values-ru", ""),
    ("app/src/main/res", "values-ru-rUA", "cyrillic-letters"),
    ("app/src/main/res", "values-ua", "not-a-language"),
    ("app/src/main/res", "values-uk", ""),
    ("app/src/main/res", "values-zh-rCN", "zh-kana"),
    ("lib/src/main/res", "values-ja", ""),
    ("lib/src/main/res", "values-jp", "not-a-language"),
]


def control():
    """The detector must flag exactly the seven planted folders and find the one reference."""
    d = tempfile.mkdtemp(prefix="locale-mismatch-control-")
    try:
        control_tree(d)
        r = scan_strings(d)
        got = [(f["res_dir"], f["locale_dir"], " ".join(f["flags"])) for f in r["folders"]]
        refs = find_refs(d, ["jp", "ua"])
        return got == CONTROL_WANT and refs == {"jp": True, "ua": False} and not r["parse_failed"]
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


ROW_COLS = ["repo", "head", "res_dir", "locale_dir", "lang", "region", "script", "flags", "units",
            "own", "top_other", "top_other_units", "latin", "cjk", "kana", "cyr_a", "cyr_b",
            "code_referenced", "ex1", "ex2", "ex3"]
SAMPLE_COLS = ["sample"] + ROW_COLS + ["label", "note"]


def exploratory(ok, rows):
    """Not graded: flag counts, languages, codes, and region-tagged shares."""
    flags, langs, codes = collections.Counter(), collections.Counter(), collections.Counter()
    region_flagged = flagged = 0
    for x in rows:
        for f in x["flags"].split():
            flags[f.split(":")[0] if f.startswith("wrong-script") else f] += 1
            if f.startswith("wrong-script:"):
                flags[f] += 1
        if "not-a-language" in x["flags"].split():
            codes[x["lang"]] += 1
        if mismatch(x):
            flagged += 1
            langs[x["lang"]] += 1
            if x["region"]:
                region_flagged += 1
    elig = collections.Counter()
    for r in ok:
        elig.update(r.get("eligible", {}))
    return {"flag_folders": dict(flags), "mismatch_langs": dict(langs),
            "not_a_language_codes": dict(codes), "mismatch_folders": flagged,
            "mismatch_folders_region_tagged": region_flagged, "eligible": dict(elig)}


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
    with open(cl.__file__, "rb") as f:
        cl_sha = hashlib.sha256(f.read()).hexdigest()
    print("locale_mismatch %s (cyrillic_leak %s)" % (VERSION, cl.VERSION), flush=True)
    if not control():
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

    tmp_root = tempfile.mkdtemp(prefix="locale-mismatch-")
    selftest = {}
    for u in SELFTEST_REPOS:
        r = process_repo(u, tmp_root)
        selftest[u] = {"status": r["status"], "folders": len(r.get("folders", []))}
    print("selftest", json.dumps(selftest), flush=True)
    if not any(v["folders"] >= 10 for v in selftest.values()):
        print("selftest found no translation folders; clone method broken, stopping",
              file=sys.stderr)
        return 3

    deadline = time.time() + a.budget_minutes * 60
    results, skipped, rows = [], [], []
    jl = open(os.path.join(a.out_dir, "repos.jsonl"), "w", encoding="utf-8", errors="replace")

    def work(u):
        if time.time() > deadline:
            return {"repo": u, "status": "not-started"}
        return process_repo(u, tmp_root)

    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for n, r in enumerate(ex.map(work, repos), 1):
            if r["status"] == "not-started":
                skipped.append(r["repo"])
                continue
            folders = r.pop("folders", [])
            r["eligible"] = dict(eligible(folders))
            flagged = [folder_row(r["repo"], r.get("head", ""), f) for f in folders if f["flags"]]
            r["flagged"] = len(flagged)
            results.append(r)
            rows += flagged
            jl.write(json.dumps({k: r.get(k) for k in ("repo", "status", "head", "error",
                                                       "seconds", "parse_failed", "eligible",
                                                       "flagged")},
                                ensure_ascii=False, sort_keys=True) + "\n")
            if n % 200 == 0:
                jl.flush()
                print("%d/%d done, %.0f min" % (n, len(repos), (time.time() - started) / 60),
                      flush=True)
    jl.close()

    # L4: are the not-a-language codes referenced in the app's sources?
    codes_by_repo = collections.defaultdict(set)
    for x in rows:
        if "not-a-language" in x["flags"].split():
            codes_by_repo[x["repo"]].add(x["lang"])
    refs = {}
    for repo in sorted(codes_by_repo):
        found, head2 = code_references(repo, sorted(codes_by_repo[repo]), tmp_root)
        refs[repo] = {"found": found, "head": head2}
    for x in rows:
        if "not-a-language" in x["flags"].split():
            v = refs[x["repo"]]["found"].get(x["lang"])
            x["code_referenced"] = "unknown" if v is None else ("yes" if v else "no")
    shutil.rmtree(tmp_root, ignore_errors=True)

    rows.sort(key=lambda x: (x["repo"], x["res_dir"], x["locale_dir"]))
    with open(os.path.join(a.out_dir, "folders.csv"), "w", encoding="utf-8", errors="replace",
              newline="") as f:
        w = csv.DictWriter(f, fieldnames=ROW_COLS)
        w.writeheader()
        for row in rows:
            w.writerow(row)
    sample = draw_sample(rows)
    with open(os.path.join(a.out_dir, "sample.csv"), "w", encoding="utf-8", errors="replace",
              newline="") as f:
        w = csv.DictWriter(f, fieldnames=SAMPLE_COLS)
        w.writeheader()
        for i, x in enumerate(sample, 1):
            w.writerow(dict(x, sample=i, label="", note=""))

    ok = [r for r in results if r.get("status") in ("ok", "no-translations")]
    l1_repos = len({x["repo"] for x in rows if mismatch(x)})
    l3, dead = dead_repos(rows)
    verdicts = grade(len(ok), l1_repos, len(sample), len(l3), len(dead))
    known = [x for x in rows if x["repo"] == KNOWN_CASE[0] and x["locale_dir"] == KNOWN_CASE[1]]
    known_read = any(r["repo"] == KNOWN_CASE[0] and r["status"] == "ok" for r in results)
    summary = {
        "verdicts": verdicts, "version": VERSION, "cyrillic_leak_sha256": cl_sha,
        "repos_url": REPOS_URL, "repos_sha256": hashlib.sha256(raw).hexdigest(),
        "prereg_sha256": prereg_sha, "repos_listed": len(repos), "repos_read": len(ok),
        "repos_with_translations": sum(1 for r in ok if r["status"] == "ok"),
        "repos_not_started": len(skipped),
        "status_counts": dict(collections.Counter(r["status"] for r in results)),
        "parse_failed_files": sum(r.get("parse_failed", 0) for r in results),
        "l1_repos": l1_repos, "sample_size": len(sample), "l3_repos": len(l3),
        "l4_dead_repos": len(dead), "references": refs,
        "known_case": {"repo": KNOWN_CASE[0], "folder": KNOWN_CASE[1], "read": known_read,
                       "flags": [x["flags"] for x in known]},
        "exploratory": exploratory(ok, rows),
        "positive_control": True, "selftest": selftest,
        "minutes": round((time.time() - started) / 60, 1),
    }
    with open(os.path.join(a.out_dir, "summary.json"), "w", encoding="utf-8",
              errors="replace") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps(verdicts), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
