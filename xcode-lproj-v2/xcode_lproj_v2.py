# Census v2: translated .lproj string tables that the app's own Xcode project never references.
# Xcode copies a localized .strings file into the app only when the project's variant group
# (PBXVariantGroup) lists that language's file, so a <lang>.lproj/<Table>.strings left on disk
# beside listed siblings never ships, and nothing warns. v1 (xcode-lproj/) found the structural
# rule right but counted files with no translation in them; v2 counts a file only when its content
# is confirmed as a translation, reads every candidate file, and runs on a new population: the
# open-source macOS apps list (serhii-londar/open-source-mac-os-apps at a fixed commit) minus every
# repository of the v1 population. Pre-registered in xcode-lproj-v2/PREREG.md of the census
# repository before any population repository is read.
# Standard library and git only. Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.
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

CENSUS = ("https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/"
          "main/")
PREREG_URL = CENSUS + "xcode-lproj-v2/PREREG.md"
PREREG_MARK = "xcode-lproj census PREREG v2"
APPS_COMMIT = "23b6184ebcee27318c28e4d40661f4435a697a3d"
APPS_URL = ("https://raw.githubusercontent.com/serhii-londar/open-source-mac-os-apps/"
            + APPS_COMMIT + "/applications.json")
OLD_POP_URL = CENSUS + "ios-lproj/v2/repos.csv"
KEY = "xcode-lproj census v2"
UA = "xcode-lproj-census (MV2, Munim, Inc.; mv2@munimtech.com)"
ACTIVE_SINCE = "2024-11-10"

VENDOR = frozenset(["pods", "carthage", "node_modules", "vendor", "vendors", "third_party",
                    "thirdparty", "third-party", "3rdparty", "external", "externals",
                    "submodules", "deps", "build", "deriveddata", ".build", "sourcepackages",
                    "checkouts"])
BUNDLE_SUFFIXES = (".framework", ".xcframework", ".bundle", ".app", ".appex")
XCODEGEN_NAMES = frozenset(["project.yml", "project.yaml"])
TUIST_NAMES = frozenset(["Project.swift", "Workspace.swift"])
PLATFORM_NAMES = frozenset(["crowdin.yml", "crowdin.yaml", ".crowdin.yml", ".crowdin.yaml",
                            ".phrase.yml", ".phraseapp.yml", "lokalise.yml", ".lokalise.yml",
                            "transifex.yml", ".transifex.yml", ".transifex.yaml"])
REFERENCE_ORDER = ("en", "Base", "en-US", "en-GB", "English")
LPROJ_RE = re.compile(r"^(?:(.*)/)?([^/]+)\.lproj/([^/]+\.strings)$")
STR_RE = re.compile(r'"((?:[^"\\]|\\.)*)"\s*=\s*"((?:[^"\\]|\\.)*)"\s*;', re.S)
GH_RE = re.compile(r"^\s*https?://(?:www\.)?github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", re.I)
GH_NOT_OWNER = frozenset(["orgs", "sponsors", "topics", "features", "marketplace", "apps",
                          "settings", "about"])
TEMPLATE_RE = re.compile(chr(0xAB) + r"[A-Z_]+" + chr(0xBB) + r"|__[A-Za-z]+__")
VAR_RE = re.compile(r"\$\([^)]*\)|\$\{[^}]*\}")
FORMAT_RE = re.compile(r"%(?:\d+\$)?[-+ #0]*\d*(?:\.\d+)?(?:hh|ll|h|l|q|z|t|j)?"
                       r"[@dDiuUxXoOfFeEgGcCsSpaA%]")
LETTER_RE = re.compile(r"[^\W\d_]")
_UNQUOTED = re.compile(r"[A-Za-z0-9_$+/:.\-]+")
_SPACE = " \t\r\n" + chr(0xFEFF)

MAX_BYTES = 5000000
MAX_PROJECTS = 30
MAX_READ = 50
MAX_LISTED = 50

# Pre-registered numbers (PREREG.md).
GATE_READ = 120
GATE_GOVERNED = 80
PARSE_ERR_MAX_PCT = 5
P1_LOW_PCT, P1_HIGH_PCT = 2, 15
P2_MIN_FLAGGED = 10
P2_LOW_PCT, P2_HIGH_PCT = 30, 80
MIN_TESTABLE = 4
P3_MIN_GROUP = 10
SAMPLE_REPOS = 12
H1_MIN_SAMPLE = 6


def key(*parts):
    return hashlib.sha256("|".join((KEY,) + parts).encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ property lists

class _P(object):
    """Reader for the old-style (OpenStep) property lists used by project.pbxproj and .strings."""

    def __init__(self, text):
        self.t, self.i, self.n = text, 0, len(text)

    def ws(self):
        t, n = self.t, self.n
        while self.i < n:
            c = t[self.i]
            if c in _SPACE:
                self.i += 1
            elif t.startswith("/*", self.i):
                j = t.find("*/", self.i + 2)
                if j < 0:
                    raise ValueError("unterminated comment")
                self.i = j + 2
            elif t.startswith("//", self.i):
                j = t.find("\n", self.i)
                self.i = n if j < 0 else j + 1
            else:
                break

    def expect(self, ch):
        self.ws()
        if self.i >= self.n or self.t[self.i] != ch:
            raise ValueError("expected %r at %d" % (ch, self.i))
        self.i += 1

    def quoted(self):
        t = self.t
        self.i += 1
        out = []
        while True:
            j = self.i
            while j < self.n and t[j] not in '"\\':
                j += 1
            out.append(t[self.i:j])
            if j >= self.n:
                raise ValueError("unterminated string")
            if t[j] == '"':
                self.i = j + 1
                return "".join(out)
            if j + 1 >= self.n:
                raise ValueError("unterminated escape")
            e = t[j + 1]
            if e == "U" and re.match(r"[0-9A-Fa-f]{4}$", t[j + 2:j + 6]):
                out.append(chr(int(t[j + 2:j + 6], 16)))
                self.i = j + 6
            else:
                out.append({"n": "\n", "t": "\t", "r": "\r"}.get(e, e))
                self.i = j + 2

    def value(self):
        self.ws()
        if self.i >= self.n:
            raise ValueError("unexpected end")
        c = self.t[self.i]
        if c == "{":
            self.i += 1
            d = {}
            while True:
                self.ws()
                if self.i < self.n and self.t[self.i] == "}":
                    self.i += 1
                    return d
                k = self.value()
                if not isinstance(k, str):
                    raise ValueError("bad key at %d" % self.i)
                self.expect("=")
                d[k] = self.value()
                self.expect(";")
        if c == "(":
            self.i += 1
            a = []
            while True:
                self.ws()
                if self.i < self.n and self.t[self.i] == ")":
                    self.i += 1
                    return a
                a.append(self.value())
                self.ws()
                if self.i < self.n and self.t[self.i] == ",":
                    self.i += 1
                elif not (self.i < self.n and self.t[self.i] == ")"):
                    raise ValueError("expected , or ) at %d" % self.i)
        if c == '"':
            return self.quoted()
        if c == "<":
            j = self.t.find(">", self.i)
            if j < 0:
                raise ValueError("unterminated data")
            s = self.t[self.i:j + 1]
            self.i = j + 1
            return s
        m = _UNQUOTED.match(self.t, self.i)
        if not m:
            raise ValueError("unexpected %r at %d" % (c, self.i))
        self.i = m.end()
        return m.group(0)


def parse_plist(text):
    return _P(text).value()


def norm(path):
    """Repository path with '.' and '..' resolved, or None if it leaves the repository."""
    out = []
    for part in path.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not out:
                return None
            out.pop()
        else:
            out.append(part)
    return "/".join(out)


def project_refs(proj_path, data):
    """(refs, known_regions) for one project.pbxproj. refs: repository paths of every file
    reference and file-system-synchronized folder the project holds. proj_path is the
    repository path of the project.pbxproj file."""
    objs = data.get("objects") if isinstance(data, dict) else None
    if not isinstance(objs, dict):
        raise ValueError("no objects")
    root = objs.get(data.get("rootObject"))
    if not isinstance(root, dict):
        raise ValueError("no root object")
    src_root = proj_path.rpartition("/")[0].rpartition("/")[0]
    pdp = root.get("projectDirPath")
    if isinstance(pdp, str) and pdp:
        src_root = norm(src_root + "/" + pdp)
    parent = {}
    for oid in sorted(objs):
        o = objs[oid]
        if isinstance(o, dict) and isinstance(o.get("children"), list):
            for c in o["children"]:
                if isinstance(c, str):
                    parent.setdefault(c, oid)
    memo = {}

    def path_of(oid, depth=0):
        if oid in memo:
            return memo[oid]
        memo[oid] = None
        o = objs.get(oid)
        result = None
        if isinstance(o, dict) and depth < 64 and src_root is not None:
            st = o.get("sourceTree", "<group>")
            p = o.get("path") if isinstance(o.get("path"), str) else ""
            if p.startswith("/"):
                base = None
            elif st == "SOURCE_ROOT":
                base = src_root
            elif st == "<group>":
                par = parent.get(oid)
                base = src_root if par is None else path_of(par, depth + 1)
            else:
                base = None
            if base is not None:
                result = norm(base + "/" + p)
        memo[oid] = result
        return result

    refs = set()
    for oid in sorted(objs):
        o = objs[oid]
        if isinstance(o, dict) and o.get("isa") in ("PBXFileReference",
                                                    "PBXFileSystemSynchronizedRootGroup"):
            p = path_of(oid)
            if p is not None:
                refs.add(p)
    regions = root.get("knownRegions")
    regions = [x for x in regions if isinstance(x, str)] if isinstance(regions, list) else []
    return refs, regions


def covered(path, refs):
    """True if the path, or a folder above it, is referenced."""
    parts = path.split("/")
    for i in range(len(parts) + 1):
        if "/".join(parts[:i]) in refs:
            return True
    return False


# ------------------------------------------------------------------ .strings files

def decode_strings(data):
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", "replace")
    if len(data) >= 4 and data[1:2] == b"\x00" and data[3:4] == b"\x00":
        return data.decode("utf-16-le", "replace")
    return data.decode("utf-8-sig", "replace")


def strings_table(text):
    """{key: value} of a .strings file (old-style property list without braces)."""
    try:
        v = parse_plist("{" + text + "\n}")
        if isinstance(v, dict):
            return dict((k, x) for k, x in v.items() if isinstance(x, str))
    except (ValueError, RecursionError, IndexError, TypeError):
        pass
    return dict(STR_RE.findall(text))


def is_translated(k, v, reference):
    """True when the value reads as a translation: not empty, not equal to its key, not an
    Xcode template placeholder, not only build variables, format specifiers, numbers or
    symbols, and (when the reference language has the key) not equal to the reference text."""
    s = v.strip()
    if not s or s == k.strip():
        return False
    if TEMPLATE_RE.search(s):
        return False
    if not LETTER_RE.search(FORMAT_RE.sub("", VAR_RE.sub("", s))):
        return False
    if reference and k in reference and reference[k].strip() == s:
        return False
    return True


def content_stats(target, reference):
    """entries: keys in the file; compared: keys also in the reference file; differs: compared
    keys whose text differs from the reference; translated: entries that read as translations."""
    st = {"entries": len(target), "compared": 0, "differs": 0, "translated": 0}
    for k, v in target.items():
        if reference and k in reference:
            st["compared"] += 1
            if v != reference[k]:
                st["differs"] += 1
        if is_translated(k, v, reference):
            st["translated"] += 1
    return st


def confirmed(st):
    """yes: at least one translated entry and, when keys could be compared, at least half of
    them differ from the reference; no otherwise; unread: the file was not read."""
    if st is None:
        return "unread"
    if st["translated"] < 1:
        return "no"
    if st["compared"] and 2 * st["differs"] < st["compared"]:
        return "no"
    return "yes"


# ------------------------------------------------------------------ one repository

def is_vendored(path):
    for part in path.split("/"):
        low = part.lower()
        if low in VENDOR or low.endswith(BUNDLE_SUFFIXES):
            return True
    return False


def under(d, dirs):
    return any(q == "" or d == q or d.startswith(q + "/") for q in dirs)


def basename(p):
    return p.rpartition("/")[2]


def english(lang):
    low = lang.lower()
    return low in ("base", "english", "en") or low.startswith(("en-", "en_"))


def generators(paths):
    """Project-generator files: XcodeGen specs anywhere, Tuist manifests only when the
    repository shows other Tuist files (a Tuist folder, Tuist.swift or .tuist-version)."""
    live = [p for p in paths if not is_vendored(p)]
    tuist = any(basename(p) in ("Tuist.swift", ".tuist-version") or "Tuist" in p.split("/")[:-1]
                for p in live)
    out = [p for p in live if basename(p) in XCODEGEN_NAMES
           or (tuist and basename(p) in TUIST_NAMES)]
    return sorted(out)[:10]


def analyse_paths(paths, reader):
    """The census measurement for one repository. paths: every file path at the commit;
    reader(path) -> bytes or None."""
    res = {"projects": [], "generated": generators(paths), "platform": [], "translated": False,
           "tables": 0, "managed_tables": 0, "excluded_package": 0, "unreferenced": [],
           "n_unreferenced": 0, "n_confirmed": 0}
    res["platform"] = sorted(p for p in paths if (basename(p).lower() in PLATFORM_NAMES
                                                  or p == ".tx/config"
                                                  or p.endswith("/.tx/config")))[:10]
    projects = sorted(p for p in paths
                      if p.endswith(".xcodeproj/project.pbxproj") and not is_vendored(p))
    refs, regions = set(), set()
    for p in projects[:MAX_PROJECTS]:
        rec = {"path": p, "status": "ok", "refs": 0}
        data = reader(p)
        if data is None:
            rec["status"] = "unread"
        else:
            try:
                r, kr = project_refs(p, parse_plist(data.decode("utf-8-sig", "replace")))
                refs |= r
                regions |= set(kr)
                rec["refs"] = len(r)
            except (ValueError, RecursionError, IndexError, TypeError, AttributeError) as exc:
                rec["status"] = ("parse error: %s" % (exc,))[:160]
        res["projects"].append(rec)
    pkg = set(p.rpartition("/")[0] for p in paths
              if basename(p) == "Package.swift" or basename(p).endswith(".podspec"))
    tables = {}
    for p in paths:
        m = LPROJ_RE.match(p)
        if not m or is_vendored(p):
            continue
        if not english(m.group(2)):
            res["translated"] = True
        d = m.group(1) or ""
        if under(d, pkg):
            res["excluded_package"] += 1
            continue
        tables.setdefault((d, m.group(3)), {})[m.group(2)] = p
    res["tables"] = len(tables)
    found = []
    for (d, name) in sorted(tables):
        langs = tables[(d, name)]
        direct = sorted(lang for lang in langs if langs[lang] in refs)
        if not direct:
            continue
        res["managed_tables"] += 1
        for lang in sorted(langs):
            if not covered(langs[lang], refs):
                found.append({"dir": d, "table": name, "lang": lang, "path": langs[lang],
                              "listed": len(direct), "in_known_regions": lang in regions,
                              "_langs": langs})
    res["n_unreferenced"] = len(found)
    for i, f in enumerate(found):
        langs = f.pop("_langs")
        f.update(entries=None, compared=None, differs=None, translated=None, reference="",
                 confirmed="unread")
        if i >= MAX_READ:
            continue
        data = reader(f["path"])
        if data is None:
            continue
        target = strings_table(decode_strings(data))
        ref_lang = next((x for x in REFERENCE_ORDER if x in langs and x != f["lang"]), None)
        reference = None
        if ref_lang:
            rd = reader(langs[ref_lang])
            reference = strings_table(decode_strings(rd)) if rd is not None else None
            f["reference"] = ref_lang if reference is not None else ""
        st = content_stats(target, reference)
        f.update(st)
        f["confirmed"] = confirmed(st)
    res["n_confirmed"] = sum(1 for f in found if f["confirmed"] == "yes")
    res["unreferenced"] = found[:MAX_LISTED]
    res["known_regions"] = sorted(regions)
    return res


# ------------------------------------------------------------------ git

def git(args, timeout=300, binary=False):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_LFS_SKIP_SMUDGE="1", GIT_ASKPASS="true")
    if binary:
        return subprocess.run(["git"] + args, env=env, capture_output=True, timeout=timeout)
    return subprocess.run(["git"] + args, env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def fetch_head(url, d):
    """Blobless fetch of the default branch's head. Returns (dir, commit, committed, paths)."""
    s = os.path.join(d, "s")
    steps = [["init", "--quiet", s],
             ["-C", s, "remote", "add", "origin", url],
             ["-C", s, "config", "core.repositoryformatversion", "1"],
             ["-C", s, "config", "extensions.partialClone", "origin"],
             ["-C", s, "config", "remote.origin.promisor", "true"],
             ["-C", s, "config", "remote.origin.partialclonefilter", "blob:none"],
             ["-C", s, "fetch", "--quiet", "--depth", "1", "--filter=blob:none", "origin",
              "HEAD"]]
    for args in steps:
        r = git(args, timeout=600)
        if r.returncode != 0:
            raise RuntimeError("git %s failed: %s" % (args[2] if args[0] == "-C" else args[0],
                                                      r.stderr.strip()[-200:]))
    rp = git(["-C", s, "rev-parse", "FETCH_HEAD"])
    commit = rp.stdout.strip()
    if rp.returncode != 0 or not re.match(r"^[0-9a-f]{40}$", commit):
        raise RuntimeError("rev-parse failed: " + rp.stderr.strip()[:200])
    lg = git(["-C", s, "log", "-1", "--format=%cI", commit])
    committed = lg.stdout.strip() if lg.returncode == 0 else ""
    lt = git(["-C", s, "ls-tree", "-r", "-z", "--name-only", commit])
    if lt.returncode != 0:
        raise RuntimeError("ls-tree failed: " + lt.stderr.strip()[:200])
    return s, commit, committed, [p for p in lt.stdout.split("\0") if p]


def read_blob(s, commit, path):
    r = git(["-C", s, "cat-file", "-p", "%s:%s" % (commit, path)], binary=True)
    if r.returncode != 0 or len(r.stdout) > MAX_BYTES:
        return None
    return r.stdout


def analyse(url, tmp_root):
    res = {"repo": url, "commit": "", "committed": "", "status": "ok", "n_paths": 0}
    t0 = time.time()
    d = tempfile.mkdtemp(dir=tmp_root)
    try:
        s, commit, committed, paths = fetch_head(url, d)
        res.update(commit=commit, committed=committed, n_paths=len(paths))
        cache = {}

        def reader(p):
            if p not in cache:
                cache[p] = read_blob(s, commit, p)
            return cache[p]

        res.update(analyse_paths(paths, reader))
    except subprocess.TimeoutExpired:
        res["status"] = "timeout"
    except Exception as exc:  # record, keep going
        res["status"] = ("error: %r" % (exc,))[:240]
    finally:
        res["seconds"] = round(time.time() - t0, 1)
        shutil.rmtree(d, ignore_errors=True)
    return res


# ------------------------------------------------------------------ grading

def governed(r):
    return (r.get("status") == "ok" and r.get("translated") and not r.get("generated")
            and r.get("managed_tables", 0) > 0)


def active(r):
    return (r.get("committed") or "")[:10] >= ACTIVE_SINCE


def grade(results):
    """Pre-registered verdicts G, P1-P3 (PREREG.md) and the counts behind them."""
    ok = [r for r in results if r["status"] == "ok"]
    read = [r for r in ok if r.get("translated")]
    projects = [p for r in read for p in r.get("projects", [])]
    perr = sum(1 for p in projects if p["status"].startswith("parse error"))
    gov = [r for r in read if governed(r)]
    anyf = [r for r in gov if r["n_unreferenced"] > 0]
    flagged = [r for r in gov if r.get("n_confirmed", 0) > 0]
    n, k = len(gov), len(flagged)
    pg = [r for r in gov if r.get("platform")]
    og = [r for r in gov if not r.get("platform")]
    pk = sum(1 for r in pg if r.get("n_confirmed", 0) > 0)
    okk = sum(1 for r in og if r.get("n_confirmed", 0) > 0)
    v = {}
    gate = (len(read) >= GATE_READ and n >= GATE_GOVERNED
            and 100 * perr <= PARSE_ERR_MAX_PCT * len(projects))
    v["G"] = ("PASSED" if gate else "FAILED (%d read, %d governed, %d of %d projects unparsed)"
              % (len(read), n, perr, len(projects)))
    if not gate:
        for p in ("P1", "P2", "P3"):
            v[p] = "NOT TESTABLE (gate)"
    else:
        v["P1"] = ("HELD" if (100 * k >= P1_LOW_PCT * n and 100 * k <= P1_HIGH_PCT * n)
                   else "FAILED") + " (%d of %d)" % (k, n)
        if len(anyf) < P2_MIN_FLAGGED:
            v["P2"] = "NOT TESTABLE (%d repositories with any unreferenced file)" % len(anyf)
        else:
            v["P2"] = ("HELD" if (100 * k >= P2_LOW_PCT * len(anyf)
                                  and 100 * k <= P2_HIGH_PCT * len(anyf)) else "FAILED") + (
                " (%d of %d)" % (k, len(anyf)))
        if len(pg) < P3_MIN_GROUP or len(og) < P3_MIN_GROUP or pk + okk < MIN_TESTABLE:
            v["P3"] = "NOT TESTABLE (%d platform, %d other, %d flagged)" % (len(pg), len(og),
                                                                           pk + okk)
        else:
            v["P3"] = ("HELD" if pk * len(og) > okk * len(pg) else "FAILED") + (
                " (%d of %d vs %d of %d)" % (pk, len(pg), okk, len(og)))
    files = [f for r in flagged for f in r["unreferenced"] if f["confirmed"] == "yes"]
    allfiles = [f for r in anyf for f in r["unreferenced"]]
    by_table, by_lang = {}, {}
    for f in files:
        by_table[f["table"]] = by_table.get(f["table"], 0) + 1
        by_lang[f["lang"]] = by_lang.get(f["lang"], 0) + 1
    ag = [r for r in gov if active(r)]
    counts = {"population_ok": len(ok), "read": len(read), "projects": len(projects),
              "projects_unparsed": perr, "governed": n, "flagged": k,
              "flagged_share_pct": round(100.0 * k / n, 2) if n else None,
              "any_unreferenced": len(anyf),
              "generated_excluded": sum(1 for r in read if r.get("generated")),
              "unreferenced_files": sum(r["n_unreferenced"] for r in anyf),
              "files_listed": len(allfiles),
              "files_unread": sum(1 for f in allfiles if f["confirmed"] == "unread"),
              "files_confirmed": sum(r.get("n_confirmed", 0) for r in flagged),
              "in_known_regions": sum(1 for f in files if f["in_known_regions"]),
              "platform_governed": len(pg), "platform_flagged": pk,
              "other_governed": len(og), "other_flagged": okk,
              "active_governed": len(ag),
              "active_flagged": sum(1 for r in ag if r.get("n_confirmed", 0) > 0),
              "by_table": dict(sorted(by_table.items(), key=lambda kv: (-kv[1], kv[0]))[:30]),
              "by_language": dict(sorted(by_lang.items(), key=lambda kv: (-kv[1], kv[0]))[:40])}
    return v, counts, flagged


def sample_rows(flagged):
    rows = []
    for i, r in enumerate(sorted(flagged, key=lambda r: key(r["repo"]))[:SAMPLE_REPOS], 1):
        f = sorted((f for f in r["unreferenced"] if f["confirmed"] == "yes"),
                   key=lambda f: key(r["repo"], f["path"]))[0]
        rows.append({"sample": i, "repo": r["repo"], "commit": r["commit"],
                     "committed": r.get("committed", ""), "path": f["path"],
                     "lang": f["lang"], "table": f["table"], "listed": f["listed"],
                     "entries": f["entries"], "compared": f["compared"],
                     "differs": f["differs"], "translated": f["translated"],
                     "projects": " ".join(p["path"] for p in r["projects"]),
                     "label": "", "note": ""})
    return rows


def write_csv(path, cols, rows):
    with open(path, "w", encoding="utf-8", errors="replace", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(dict((c, "" if row.get(c) is None else str(row.get(c))) for c in cols))


# ------------------------------------------------------------------ population

def gh_repo(url):
    """https://github.com/<owner>/<repo> for a GitHub repository link, else None."""
    m = GH_RE.match(url or "")
    if not m:
        return None
    owner, name = m.group(1), m.group(2)
    if name.lower().endswith(".git"):
        name = name[:-4]
    if not name or owner.lower() in GH_NOT_OWNER:
        return None
    return "https://github.com/%s/%s" % (owner, name)


def population(apps_raw, old_raw):
    """(repository URLs, number of list entries): GitHub repositories of the macOS list, minus
    every repository of the v1 population, deduplicated without regard to case."""
    data = json.loads(apps_raw.decode("utf-8-sig"))
    apps = data.get("applications", []) if isinstance(data, dict) else []
    old = set()
    for r in csv.DictReader(io.StringIO(old_raw.decode("utf-8-sig"))):
        u = gh_repo(r.get("repo") or "")
        if u:
            old.add(u.lower())
    out = {}
    for a in apps:
        if isinstance(a, dict):
            u = gh_repo(str(a.get("repo_url") or ""))
            if u and u.lower() not in old:
                out.setdefault(u.lower(), u)
    return [out[k] for k in sorted(out)], len(apps)


# ------------------------------------------------------------------ network and main

def fetch(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read()
        except Exception as exc:  # retry, then give up
            last = exc
            time.sleep(5 * (i + 1))
    raise RuntimeError("could not read %s: %r" % (url, last))


def wait_for_prereg(minutes, say):
    end = time.time() + minutes * 60
    while True:
        try:
            data = fetch("%s?nocache=%d" % (PREREG_URL, int(time.time())), tries=1)
            if PREREG_MARK.encode("utf-8") in data:
                return hashlib.sha256(data).hexdigest()
        except Exception:
            pass
        if time.time() > end:
            return None
        say("waiting for PREREG.md")
        time.sleep(300)


UNREF_COLS = ["repo", "commit", "committed", "path", "dir", "table", "lang", "listed",
              "in_known_regions", "entries", "compared", "differs", "translated", "reference",
              "confirmed"]
SAMPLE_COLS = ["sample", "repo", "commit", "committed", "path", "lang", "table", "listed",
               "entries", "compared", "differs", "translated", "projects", "label", "note"]
REPO_COLS = ["repo", "commit", "committed", "status", "seconds", "n_paths", "translated",
             "projects", "generated", "platform", "tables", "managed_tables", "excluded_package",
             "governed", "n_unreferenced", "n_confirmed"]


def main(out, say, workers=8, prereg_wait_minutes=480):
    started = time.time()
    prereg_sha = wait_for_prereg(prereg_wait_minutes, say)
    if not prereg_sha:
        say("PREREG.md not public; stopping before reading any repository")
        return 4
    say("prereg sha256 %s" % prereg_sha)
    apps_raw = fetch(APPS_URL)
    old_raw = fetch(OLD_POP_URL)
    repos, n_apps = population(apps_raw, old_raw)
    say("population: %d GitHub repositories from %d list entries" % (len(repos), n_apps))
    tmp_root = tempfile.mkdtemp(prefix="xcl2-")
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(lambda u: analyse(u, tmp_root), repos))
    shutil.rmtree(tmp_root, ignore_errors=True)
    with open(os.path.join(out, "results.jsonl"), "w", encoding="utf-8", errors="replace") as fh:
        for r in results:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    write_csv(os.path.join(out, "repos.csv"), REPO_COLS,
              [dict(r, projects=len(r.get("projects", [])), generated=" ".join(r.get(
                  "generated", [])), platform=" ".join(r.get("platform", [])),
                    translated="yes" if r.get("translated") else "no",
                    governed="yes" if governed(r) else "no") for r in results])
    write_csv(os.path.join(out, "unreferenced.csv"), UNREF_COLS,
              [dict(f, repo=r["repo"], commit=r["commit"], committed=r.get("committed", ""))
               for r in results if governed(r) for f in r.get("unreferenced", [])])
    verdicts, counts, flagged = grade(results)
    rows = sample_rows(flagged) if verdicts["G"] == "PASSED" else []
    write_csv(os.path.join(out, "sample.csv"), SAMPLE_COLS, rows)
    verdicts["H1"] = ("PENDING HAND CHECK (%d repositories)" % len(rows)
                      if len(rows) >= H1_MIN_SAMPLE else "NOT TESTABLE (sample of %d)" % len(rows))
    status = {}
    for r in results:
        st = r["status"] if r["status"] in ("ok", "timeout") else r["status"].split(":")[0]
        status[st] = status.get(st, 0) + 1
    summary = {"verdicts": verdicts, "counts": counts, "prereg_sha256": prereg_sha,
               "apps_sha256": hashlib.sha256(apps_raw).hexdigest(),
               "old_population_sha256": hashlib.sha256(old_raw).hexdigest(),
               "list_entries": n_apps, "repositories": len(repos),
               "status": dict(sorted(status.items())),
               "minutes": round((time.time() - started) / 60, 1)}
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8", errors="replace") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1, sort_keys=True)
    say(json.dumps(verdicts))
    return 0


if __name__ == "__main__":
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "out"
    os.makedirs(out_dir, exist_ok=True)

    def say(msg):
        print(time.strftime("%H:%M:%S"), msg, flush=True)

    sys.exit(main(out_dir, say))
