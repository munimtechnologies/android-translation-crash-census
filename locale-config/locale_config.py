#!/usr/bin/env python3
# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Android per-app language lists that don't match the app's translations (pre-registered).

Since Android 13 a user can pick a language for one app in the system settings. Settings offers
only the languages in the app's locale config: either a hand-written res/xml file named by
android:localeConfig in the manifest, or one the Android Gradle Plugin generates from the resource
folders (androidResources { generateLocaleConfig = true }). A hand-written list can drift from the
translations the app really ships:

  phantom   a listed language with no translation folder anywhere in the repository (Settings
            offers it; the user gets the default language);
  orphan    a language with a translation folder in the declaring module, at least half
            translated, that the list leaves out (Settings never offers it).

For every repository in hidden-chars/repos.txt (the census's F-Droid source repositories) this
reads the file list at HEAD (git ls-tree on a shallow, blob-less clone), then a sparse checkout of
the manifests, build.gradle(.kts) files, res/xml files, resources.properties and values*/ XML.
See PREREG.md for the predictions and how they are graded.

Made with AI agents by MV2 of Munim, Inc. Standard library only. Needs git.
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
import urllib.request
import xml.etree.ElementTree as ET

VERSION = "0.1.0"
BASE = "https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/main/"
REPOS_URL = BASE + "hidden-chars/repos.txt"
PREREG_URL = BASE + "locale-config/PREREG.md"
PREREG_MARK = "locale-config PREREG v1"
SELFTEST_REPOS = ("https://github.com/TeamNewPipe/NewPipe", "https://gitlab.com/fdroid/fdroidclient")
SPARSE = ["**/AndroidManifest.xml", "**/build.gradle", "**/build.gradle.kts", "**/res/xml/*.xml",
          "**/resources.properties", "**/res/values*/*.xml"]
ANDROID_NS = "{http://schemas.android.com/apk/res/android}"
MAX_BYTES = 2000000

# Pre-registered thresholds (PREREG.md).
GATE_REPOS_READ = 4000
C1_MIN_REPOS = 100
C2C3_MIN_EVALUABLE = 20
SAMPLE_SIZE = 16
C4_MIN_SAMPLE = 8
SUBSTANTIAL = 0.5  # an orphan counts if at least half of the module's strings are translated

ISO639_1 = frozenset("""
aa ab ae af ak am an ar as av ay az ba be bg bi bm bn bo br bs ca ce ch co cr cs cu cv cy da de dv
dz ee el en eo es et eu fa ff fi fj fo fr fy ga gd gl gn gu gv ha he hi ho hr ht hu hy hz ia id ie
ig ii ik io is it iu ja jv ka kg ki kj kk kl km kn ko kr ks ku kv kw ky la lb lg li ln lo lt lu lv
mg mh mi mk ml mn mr ms mt my na nb nd ne ng nl nn no nr nv ny oc oj om or os pa pi pl ps pt qu rm
rn ro ru rw sa sc sd se sg si sk sl sm sn so sq sr ss st su sv sw ta te tg th ti tk tl tn to tr ts
tt tw ty ug uk ur uz ve vi vo wa wo xh yi yo za zh zu
""".split())
LEGACY = frozenset({"in", "iw", "ji", "mo", "sh", "bh"})
ALIAS = {"iw": "he", "in": "id", "ji": "yi"}
SKIP_SEGMENTS = frozenset({"test", "androidTest", "testFixtures", "sharedTest"})

# Same folder-name rule as locale_mismatch.py 0.1.0 in this census.
_DIR = re.compile(
    r"^values-(?:([a-z]{2,3})(?:-r([A-Z]{2}|[0-9]{3}))?|b\+([a-zA-Z]{2,3})((?:\+[A-Za-z0-9]+)*))$")
NOT_LOCALES = {"car"}
PSEUDO = {("en", "XA"), ("ar", "XB")}


def git(args, timeout=240):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_LFS_SKIP_SMUDGE="1", GIT_ASKPASS="true")
    return subprocess.run(["git"] + args, env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


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


def norm_lang(lang):
    lang = lang.lower()
    return ALIAS.get(lang, lang)


def not_a_language(lang):
    return len(lang) == 2 and lang not in ISO639_1 and lang not in LEGACY


def tag_lang(tag):
    """Language of a locale-config name ('en-US', 'zh-Hans-CN', 'pt_BR', 'b+sr+Latn', 'iw')."""
    t = (tag or "").strip()
    if t.startswith("b+"):
        t = t[2:]
    first = re.split(r"[-_+]", t, maxsplit=1)[0]
    return norm_lang(first) if first else ""


def module_of(path):
    """Module root of a res folder or manifest path: the part before the last 'src' folder, else
    the parent folder ('' for the repository root)."""
    parts = path.split("/")
    head = parts[:-1]
    if "src" in head:
        i = len(head) - 1 - head[::-1].index("src")
        return "/".join(parts[:i])
    return "/".join(head)


def skipped(path):
    return any(p in SKIP_SEGMENTS for p in path.split("/"))


def values_files(paths):
    """{(res_dir, values dir): {file names}} for .xml files in res/values*/ (not under tests)."""
    files = collections.defaultdict(set)
    for p in paths:
        parts = p.split("/")
        if len(parts) < 3 or parts[-3] != "res" or not parts[-1].endswith(".xml"):
            continue
        if parts[-2] != "values" and not parts[-2].startswith("values-"):
            continue
        res_dir = "/".join(parts[:-2])
        if skipped(res_dir):
            continue
        files[(res_dir, parts[-2])].add(parts[-1])
    return files


def candidate_folders(paths):
    """{res_dir: {locale_dir: lang}}: values-<locale> folders next to a values folder that hold an
    .xml file also present in values."""
    files = values_files(paths)
    out = collections.defaultdict(dict)
    for (res_dir, d), names in files.items():
        if d == "values":
            continue
        pd = parse_dir(d)
        default = files.get((res_dir, "values"))
        if not pd or not default or not (names & default):
            continue
        out[res_dir][d] = norm_lang(pd[0])
    return {k: dict(sorted(v.items())) for k, v in sorted(out.items())}


def keys_of(data, default=False):
    """Names of the string, plurals and string-array items of a values XML file (bytes). In the
    default folder items marked translatable="false" are left out; in a translation, empty items
    are left out. None if the file doesn't parse."""
    try:
        root = ET.fromstring(data)
    except (ET.ParseError, ValueError):
        return None
    if root.tag != "resources":
        return set()
    out = set()
    for e in root:
        if e.tag not in ("string", "plurals", "string-array"):
            continue
        name = e.get("name")
        if not name:
            continue
        if default and e.get("translatable") == "false":
            continue
        if not default and not "".join(e.itertext()).strip():
            continue
        out.add(name)
    return out


def coverage(paths, read):
    """Translated item counts. Returns (folders, parse_failed) where folders is
    {res_dir: {"default": n, "locales": {locale_dir: (lang, translated)}}} for folders with at
    least one translated item."""
    cands = candidate_folders(paths)
    files = values_files(paths)
    failed = 0
    cache = {}

    def keys(res_dir, d, fn, default):
        nonlocal failed
        k = (res_dir, d, fn)
        if k not in cache:
            data = read("%s/%s/%s" % (res_dir, d, fn) if res_dir else "%s/%s" % (d, fn))
            ks = keys_of(data, default) if data is not None else None
            if data is not None and ks is None:
                failed += 1
            cache[k] = ks or set()
        return cache[k]

    out = {}
    for res_dir, locs in cands.items():
        dfiles = sorted(files.get((res_dir, "values"), ()))
        n_default = sum(len(keys(res_dir, "values", fn, True)) for fn in dfiles)
        got = {}
        for d, lang in locs.items():
            n = 0
            for fn in sorted(files[(res_dir, d)]):
                if fn in dfiles:
                    n += len(keys(res_dir, d, fn, False) & keys(res_dir, "values", fn, True))
            if n:
                got[d] = (lang, n)
        if got:
            out[res_dir] = {"default": n_default, "locales": got}
    return out, failed


_GEN = re.compile(r"\bgenerateLocaleConfig\s*(?:=\s*)?true\b")
_LC = re.compile(r'android:localeConfig\s*=\s*"@xml/([A-Za-z0-9_.]+)"')
_UNQ = re.compile(r"^\s*unqualifiedResLocale\s*=\s*([A-Za-z0-9_+\-]+)", re.M)


def gradle_generates(text):
    """Whether a build.gradle(.kts) turns on generateLocaleConfig (line comments ignored)."""
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("//") or s.startswith("*") or s.startswith("/*"):
            continue
        if _GEN.search(line.split("//")[0]):
            return True
    return False


def manifest_locale_config(text):
    """The @xml/<name> of android:localeConfig in a manifest (XML comments ignored), or None."""
    m = _LC.search(re.sub(r"<!--.*?-->", "", text, flags=re.S))
    return m.group(1) if m else None


def parse_locale_config(data):
    """Locale names of a res/xml locale-config file (bytes), or None if it doesn't parse or its
    root isn't <locale-config>."""
    try:
        root = ET.fromstring(data)
    except (ET.ParseError, ValueError):
        return None
    if root.tag != "locale-config":
        return None
    return [e.get(ANDROID_NS + "name", "").strip() for e in root.iter("locale")]


def default_language(props_text):
    """unqualifiedResLocale of a resources.properties text, else 'en'."""
    m = _UNQ.search(props_text or "")
    return tag_lang(m.group(1)) if m else "en"


def _decode(b):
    return b.decode("utf-8", "replace") if b is not None else None


def evaluate(manifest, name, folders, paths, read, gradle_text):
    """One android:localeConfig declaration against the repository's translations."""
    mod = module_of(manifest)
    row = {"manifest": manifest, "module": mod, "xml": "", "status": "", "default": "en",
           "regenerated": any(name in t for t in gradle_text.values()), "listed": [],
           "phantom": [], "orphan": [], "weak_orphan": [], "module_langs": 0}
    cands = sorted(p for p in paths if p.endswith("/res/xml/%s.xml" % name)
                   or p == "res/xml/%s.xml" % name)
    cands = [p for p in cands if not skipped(p)]
    same = [p for p in cands if module_of(p.rsplit("/", 2)[0]) == mod]
    pick = same or cands
    if not pick:
        row["status"] = "missing"
        return row
    row["xml"] = pick[0]
    data = read(pick[0])
    listed = parse_locale_config(data) if data is not None else None
    if listed is None:
        row["status"] = "parse-failed"
        return row
    props = sorted(p for p in paths if p.split("/")[-1] == "resources.properties"
                   and not skipped(p) and module_of(p.rsplit("/", 1)[0]) == mod)
    default = default_language(_decode(read(props[0])) if props else None)
    all_langs = {lang for v in folders.values() for lang, _ in v["locales"].values()}
    den = 0
    best = collections.Counter()
    per_dir = collections.Counter()
    langs_of_dir = {}
    for rd, v in folders.items():
        if module_of(rd) != mod:
            continue
        den += v["default"]
        for d, (lang, n) in v["locales"].items():
            per_dir[d] += n
            langs_of_dir[d] = lang
    for d, n in per_dir.items():
        lang = langs_of_dir[d]
        best[lang] = max(best[lang], n)
    listed_langs = {tag_lang(t) for t in listed if tag_lang(t)}
    orphan, weak = [], []
    for lang in sorted(set(best) - listed_langs - {default}):
        pct = int(100 * best[lang] / den) if den else 0
        (orphan if den and best[lang] >= SUBSTANTIAL * den else weak).append("%s:%d" % (lang, pct))
    row.update(status="ok" if listed else "empty", default=default, listed=listed,
               phantom=sorted(listed_langs - all_langs - {default}), orphan=orphan,
               weak_orphan=weak, module_langs=len(best))
    return row


def evaluable(row):
    return row["status"] in ("ok", "empty") and not row["regenerated"]


def drift(row):
    return evaluable(row) and bool(row["phantom"] or row["orphan"])


def analyse(paths, read):
    """paths: every file path at HEAD (posix); read(path) -> bytes or None."""
    folders, failed = coverage(paths, read)
    langs = sorted({lang for v in folders.values() for lang, _ in v["locales"].values()})
    rec = {"folders": sum(len(v["locales"]) for v in folders.values()), "langs": langs,
           "parse_failed": failed, "generated": [], "lists": [],
           "bad_codes": [x for x in langs if not_a_language(x)]}
    gradle_text = {}
    for p in sorted(paths):
        if p.split("/")[-1] in ("build.gradle", "build.gradle.kts") and not skipped(p):
            t = _decode(read(p))
            if t is None:
                continue
            gradle_text[p] = t
            if gradle_generates(t):
                rec["generated"].append(p)
    for p in sorted(paths):
        if p.split("/")[-1] != "AndroidManifest.xml" or skipped(p):
            continue
        t = _decode(read(p))
        name = manifest_locale_config(t) if t is not None else None
        if name:
            rec["lists"].append(evaluate(p, name, folders, paths, read, gradle_text))
    return rec


def _strings(pairs, extra=""):
    body = "".join('  <string name="%s"%s>%s</string>\n' % (k, a, v) for k, v, a in pairs)
    return ('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n%s%s</resources>\n'
            % (body, extra)).encode("utf-8")


def control_files():
    """A synthetic repository: one hand-written list with one phantom (fr), one substantial orphan
    (uk), one weak orphan (ko); a commented-out and a real generateLocaleConfig; a bad code (ua)."""
    four = [("a", "A", ""), ("b", "B", ""), ("c", "C", ""), ("d", "D", "")]
    tr = lambda keys: _strings([(k, k.upper() + "x", "") for k in keys])
    app = "app/src/main/res/"
    return {
        "app/src/main/AndroidManifest.xml":
            b'<manifest xmlns:android="http://schemas.android.com/apk/res/android">\n'
            b'<application android:label="x" android:localeConfig="@xml/locales_config"/>\n'
            b'</manifest>\n',
        app + "xml/locales_config.xml":
            b'<?xml version="1.0" encoding="utf-8"?>\n<locale-config '
            b'xmlns:android="http://schemas.android.com/apk/res/android">\n'
            b'<locale android:name="en-US"/><locale android:name="de"/><locale android:name="fr"/>'
            b'<locale android:name="zh-Hans-CN"/><locale android:name="he"/>\n</locale-config>\n',
        app + "values/strings.xml": _strings(four + [("e", "E", ' translatable="false"')]),
        app + "values/colors.xml": b'<resources><color name="c">#fff</color></resources>',
        app + "values-de/strings.xml": tr("abcd"),
        app + "values-zh-rCN/strings.xml": tr("abc"),
        app + "values-iw/strings.xml": tr("abcd"),
        app + "values-uk/strings.xml": tr("abc"),
        app + "values-ko/strings.xml": tr("a"),
        app + "values-el/strings.xml": _strings([("a", "", "")]),
        app + "values-v21/styles.xml": b"<resources/>",
        app + "values-night/colors.xml": b"<resources/>",
        app + "values-pt/arrays.xml": b"<resources/>",
        "app/build.gradle": b"android { }\n",
        "app/src/test/res/values/strings.xml": tr("a"),
        "app/src/test/res/values-it/strings.xml": tr("a"),
        "lib/build.gradle.kts":
            b"android {\n  androidResources {\n    // generateLocaleConfig = true\n  }\n}\n",
        "lib/src/main/res/values/strings.xml": _strings([("a", "A", "")]),
        "lib/src/main/res/values-es/strings.xml": tr("a"),
        "other/build.gradle": b"android { androidResources { generateLocaleConfig true } }\n",
        "other/src/main/AndroidManifest.xml": b"<manifest/>",
        "other/src/main/res/values/strings.xml": _strings([("a", "A", "")]),
        "other/src/main/res/values-ua/strings.xml": tr("a"),
    }


CONTROL_WANT = {
    "folders": 7, "langs": ["de", "es", "he", "ko", "ua", "uk", "zh"], "bad_codes": ["ua"],
    "generated": ["other/build.gradle"], "parse_failed": 0,
    "list": {"manifest": "app/src/main/AndroidManifest.xml", "module": "app",
             "xml": "app/src/main/res/xml/locales_config.xml", "status": "ok", "default": "en",
             "regenerated": False, "phantom": ["fr"], "orphan": ["uk:75"],
             "weak_orphan": ["ko:25"], "module_langs": 5},
}


def control():
    files = control_files()
    rec = analyse(sorted(files), files.get)
    if len(rec["lists"]) != 1:
        return False
    got = {k: rec[k] for k in ("folders", "langs", "bad_codes", "generated", "parse_failed")}
    lst = {k: rec["lists"][0][k] for k in CONTROL_WANT["list"]}
    want = dict(CONTROL_WANT)
    want_list = want.pop("list")
    return got == want and lst == want_list and drift(rec["lists"][0])


def wanted(p):
    name = p.split("/")[-1]
    return (name in ("AndroidManifest.xml", "build.gradle", "build.gradle.kts",
                     "resources.properties") or "/res/xml/" in "/" + p)


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
            return res
        res["head"] = git(["-C", s, "rev-parse", "HEAD"]).stdout.strip()
        lt = git(["-C", s, "ls-tree", "-r", "-z", "--name-only", "HEAD"])
        if lt.returncode != 0:
            res.update(status="error", error=("ls-tree: " + lt.stderr.strip())[:200])
            return res
        paths = [p for p in lt.stdout.split("\0") if p]
        if not candidate_folders(paths):
            res["status"] = "no-translations"
            return res
        git(["-C", s, "sparse-checkout", "set", "--no-cone"] + SPARSE)
        branch = git(["-C", s, "symbolic-ref", "--short", "HEAD"]).stdout.strip()
        git(["-C", s, "checkout", "--quiet"] + ([branch] if branch else []))
        if not any(os.path.isfile(os.path.join(s, *p.split("/"))) for p in paths if wanted(p)):
            git(["-C", s, "read-tree", "-mu", "HEAD"])

        def read(p):
            fp = os.path.join(s, *p.split("/"))
            try:
                if not os.path.isfile(fp) or os.path.getsize(fp) > MAX_BYTES:
                    return None
                with open(fp, "rb") as f:
                    return f.read()
            except OSError:
                return None

        res.update(analyse(paths, read))
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


LIST_COLS = ["repo", "head", "manifest", "module", "xml", "status", "default", "regenerated",
             "listed", "module_langs", "phantom", "orphan", "weak_orphan", "evaluable", "drift"]
SAMPLE_COLS = ["sample"] + LIST_COLS + ["label", "note"]


def clean(text):
    return str(text).encode("utf-8", "replace").decode("utf-8")


def list_row(repo, head, x):
    return {"repo": repo, "head": head, "manifest": x["manifest"], "module": x["module"],
            "xml": x["xml"], "status": x["status"], "default": x["default"],
            "regenerated": "yes" if x["regenerated"] else "no",
            "listed": clean(" ".join(x["listed"]))[:500], "module_langs": x["module_langs"],
            "phantom": " ".join(x["phantom"]), "orphan": " ".join(x["orphan"]),
            "weak_orphan": " ".join(x["weak_orphan"]),
            "evaluable": "yes" if evaluable(x) else "no", "drift": "yes" if drift(x) else "no"}


def sample_key(repo, manifest):
    return hashlib.sha256(("locale-config v1|%s|%s" % (repo, manifest)).encode("utf-8")).hexdigest()


def draw_sample(rows):
    """Per repository the drifting list with the lowest key; then the first 16 by key."""
    by_repo = collections.defaultdict(list)
    for x in rows:
        if x["drift"] == "yes":
            by_repo[x["repo"]].append(x)
    kept = [min(rs, key=lambda x: sample_key(x["repo"], x["manifest"]))
            for _, rs in sorted(by_repo.items())]
    kept.sort(key=lambda x: sample_key(x["repo"], x["manifest"]))
    return kept[:SAMPLE_SIZE]


def repo_counts(rows):
    """Repository-level counts over the list rows (graded numbers, PREREG.md)."""
    present = {x["repo"] for x in rows if x["status"] != "missing"}
    ev = {x["repo"] for x in rows if x["evaluable"] == "yes"}
    dr = {x["repo"] for x in rows if x["drift"] == "yes"}
    orph = {x["repo"] for x in rows if x["evaluable"] == "yes" and x["orphan"]}
    phan = {x["repo"] for x in rows if x["evaluable"] == "yes" and x["phantom"]}
    return {"c1_repos_with_list": len(present), "evaluable_repos": len(ev), "drift_repos": len(dr),
            "orphan_repos": len(orph), "phantom_repos": len(phan)}


def grade(n_read, c, sample_n):
    """Pre-registered verdicts (PREREG.md). Integers only."""
    if n_read < GATE_REPOS_READ:
        return {p: "NOT TESTABLE (gate: %d repositories read)" % n_read
                for p in ("C1", "C2", "C3", "C4")}
    v = {"C1": "HELD" if c["c1_repos_with_list"] >= C1_MIN_REPOS else "FAILED"}
    if c["evaluable_repos"] < C2C3_MIN_EVALUABLE:
        v["C2"] = v["C3"] = "NOT TESTABLE (%d evaluable repositories)" % c["evaluable_repos"]
    else:
        v["C2"] = "HELD" if c["drift_repos"] * 4 >= c["evaluable_repos"] else "FAILED"
        v["C3"] = "HELD" if c["orphan_repos"] > c["phantom_repos"] else "FAILED"
    v["C4"] = ("PENDING HAND CHECK (sample of %d)" % sample_n if sample_n >= C4_MIN_SAMPLE
               else "NOT TESTABLE (sample of %d)" % sample_n)
    return v


def grade_c4(labels):
    """labels: the hand labels of the sample rows, in order."""
    n = len(labels)
    if n < C4_MIN_SAMPLE:
        return "NOT TESTABLE"
    real = sum(1 for x in labels if x == "real")
    return "HELD" if real * 4 >= n * 3 else "FAILED"


def exploratory(ok, rows):
    """Not graded."""
    with_tr = [r for r in ok if r["status"] == "ok"]
    gen = [r for r in with_tr if r.get("generated")]
    declared = {x["repo"] for x in rows}
    both = [r["repo"] for r in gen if r["repo"] in declared]
    no_list = [r for r in with_tr if len(r.get("langs", [])) >= 3 and not r.get("generated")
               and r["repo"] not in declared]
    phantom, orphan, weak = collections.Counter(), collections.Counter(), collections.Counter()
    for x in rows:
        if x["evaluable"] != "yes":
            continue
        phantom.update(x["phantom"].split())
        orphan.update(o.split(":")[0] for o in x["orphan"].split())
        weak.update(o.split(":")[0] for o in x["weak_orphan"].split())
    return {
        "repos_with_translations": len(with_tr),
        "generated_repos": len(gen),
        "generated_and_declared_repos": sorted(both),
        "generated_with_bad_codes": {r["repo"]: r["bad_codes"] for r in gen if r.get("bad_codes")},
        "no_list_repos_3plus_langs": len(no_list),
        "repos_3plus_langs": sum(1 for r in with_tr if len(r.get("langs", [])) >= 3),
        "list_status": dict(collections.Counter(x["status"] for x in rows)),
        "regenerated_lists": sum(1 for x in rows if x["regenerated"] == "yes"),
        "lists": len(rows),
        "phantom_langs": dict(phantom.most_common(40)),
        "orphan_langs": dict(orphan.most_common(40)),
        "weak_orphan_langs": dict(weak.most_common(40)),
        "repos_with_weak_orphan_only": len({x["repo"] for x in rows if x["evaluable"] == "yes"
                                            and x["weak_orphan"] and not x["orphan"]
                                            and not x["phantom"]}),
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
    with open(os.path.abspath(__file__), "rb") as f:
        own_sha = hashlib.sha256(f.read()).hexdigest()
    print("locale_config %s" % VERSION, flush=True)
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

    tmp_root = tempfile.mkdtemp(prefix="locale-config-")
    selftest = {}
    for u in SELFTEST_REPOS:
        r = process_repo(u, tmp_root)
        selftest[u] = {"status": r["status"], "folders": r.get("folders", 0)}
    print("selftest", json.dumps(selftest), flush=True)
    if not any(v["folders"] >= 10 for v in selftest.values()):
        print("selftest found no translation folders; clone method broken, stopping",
              file=sys.stderr)
        return 3

    deadline = time.time() + a.budget_minutes * 60
    results, skipped_repos, rows = [], [], []
    jl = open(os.path.join(a.out_dir, "repos.jsonl"), "w", encoding="utf-8", errors="replace")

    def work(u):
        if time.time() > deadline:
            return {"repo": u, "status": "not-started"}
        return process_repo(u, tmp_root)

    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for n, r in enumerate(ex.map(work, repos), 1):
            if r["status"] == "not-started":
                skipped_repos.append(r["repo"])
                continue
            lists = r.pop("lists", [])
            r["lists"] = len(lists)
            rows += [list_row(r["repo"], r.get("head", ""), x) for x in lists]
            results.append(r)
            jl.write(json.dumps({k: r.get(k) for k in ("repo", "status", "head", "error",
                                                       "seconds", "folders", "langs",
                                                       "parse_failed", "generated", "lists",
                                                       "bad_codes")},
                                ensure_ascii=False, sort_keys=True) + "\n")
            if n % 200 == 0:
                jl.flush()
                print("%d/%d done, %.0f min" % (n, len(repos), (time.time() - started) / 60),
                      flush=True)
    jl.close()
    shutil.rmtree(tmp_root, ignore_errors=True)

    rows.sort(key=lambda x: (x["repo"], x["manifest"]))
    with open(os.path.join(a.out_dir, "lists.csv"), "w", encoding="utf-8", errors="replace",
              newline="") as f:
        w = csv.DictWriter(f, fieldnames=LIST_COLS)
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
    counts = repo_counts(rows)
    verdicts = grade(len(ok), counts, len(sample))
    summary = {
        "verdicts": verdicts, "version": VERSION, "script_sha256": own_sha,
        "repos_url": REPOS_URL, "repos_sha256": hashlib.sha256(raw).hexdigest(),
        "prereg_sha256": prereg_sha, "repos_listed": len(repos), "repos_read": len(ok),
        "repos_not_started": len(skipped_repos),
        "status_counts": dict(collections.Counter(r["status"] for r in results)),
        "parse_failed_files": sum(r.get("parse_failed", 0) for r in results),
        "counts": counts, "sample_size": len(sample),
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
