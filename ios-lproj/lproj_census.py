# Census: country codes used as language codes in Apple .lproj folders of open-source iOS
# apps (the GitHub repositories listed in dkhamsing/open-source-ios-apps). Pre-registered in
# ios-lproj/PREREG.md before any repository is read. Standard library and git only.
# Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.
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

LIST_REPO = "https://github.com/dkhamsing/open-source-ios-apps"
LIST_RAW = "https://raw.githubusercontent.com/dkhamsing/open-source-ios-apps/%s/contents.json"
PREREG_URL = ("https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/"
              "main/ios-lproj/PREREG.md")
PREREG_MARK = "ios-lproj census PREREG v1"
KEY = "ios-lproj census v1"
UA = "ios-lproj-census (MV2, Munim, Inc.; mv2@munimtech.com)"

# Two-letter codes that are not ISO 639-1 languages but are often used as if they were
# (mostly country codes), with the language code meant. Same list as l10n-guard 0.19.0.
FIXES = {
    "cn": "zh", "cz": "cs", "ua": "uk", "jp": "ja", "by": "be", "dk": "da", "gr": "el",
    "sp": "es", "du": "nl", "vn": "vi", "al": "sq", "ir": "fa", "il": "he", "hk": "zh",
    "us": "en", "gb": "en", "pk": "ur", "ge": "ka", "mx": "es", "rs": "sr", "kz": "kk",
}
# Real ISO 639-1 codes that are also country codes, so a folder may be meant for another
# language (kr is Kanuri, not Korean). Exploratory only.
SUSPECT = {"kr": "ko", "se": "sv", "ch": "zh", "si": "sl", "ee": "et", "br": "pt"}
LEGACY = {"english": "en", "french": "fr", "german": "de", "japanese": "ja", "spanish": "es",
          "italian": "it", "dutch": "nl"}
EXPECTED_SCRIPT = {
    "cn": {"Han"}, "hk": {"Han"}, "jp": {"Han", "Kana"}, "ua": {"Cyrillic"},
    "by": {"Cyrillic"}, "kz": {"Cyrillic"}, "gr": {"Greek"}, "il": {"Hebrew"},
    "ir": {"Arabic"}, "pk": {"Arabic"}, "ge": {"Georgian"}, "kr": {"Hangul"}, "ch": {"Han"},
}
VENDOR = frozenset(["pods", "carthage", "vendor", "vendors", "node_modules", "thirdparty",
                    "third_party", "third-party", "3rdparty", ".build", "sourcepackages",
                    "external", "externals", "deps", "submodules"])
REF_NAMES = ("en", "Base", "English", "en-US", "en_US", "en-GB")
CODE_EXT = (".swift", ".m", ".mm", ".h")
SPARSE_FULL = ["*.strings", "*.xcstrings", "*.pbxproj", "*.swift", "*.m", "*.mm", "*.h"]
SPARSE_XC = ["*.xcstrings"]
MAX_BYTES = 2000000
MAX_STRINGS_FILES = 5
MAX_CODE_FILES = 20000
MAX_XCSTRINGS = 20

# Pre-registered numbers (PREREG.md).
GATE_READ = 1000
GATE_TRANSLATED = 300
P3_SET = frozenset(["cn", "cz", "ua", "jp"])
MIN_TESTABLE = 4
SAMPLE_REPOS = 12

TAG_RE = re.compile(r"^([A-Za-z]{2,3})(?:[-_][A-Za-z0-9]+)*$")
GH_RE = re.compile(r"^https?://(?:www\.)?github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", re.I)
TOKEN_RE = re.compile(r'/\*.*?\*/|//[^\n]*|"((?:[^"\\]|\\.)*)"\s*=\s*"((?:[^"\\]|\\.)*)"\s*;',
                      re.S)
KNOWN_RE = re.compile(r"knownRegions\s*=\s*\(([^)]*)\)", re.S)
SCRIPT_WORDS = frozenset([
    "LATIN", "CYRILLIC", "GREEK", "ARMENIAN", "HEBREW", "ARABIC", "DEVANAGARI", "BENGALI",
    "GUJARATI", "ORIYA", "TAMIL", "TELUGU", "KANNADA", "MALAYALAM", "SINHALA", "THAI", "LAO",
    "TIBETAN", "MYANMAR", "GEORGIAN", "HANGUL", "ETHIOPIC", "KHMER"])


def key(*parts):
    return hashlib.sha256("|".join((KEY,) + parts).encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ folder names

def lproj_primary(name):
    """Language part of an .lproj folder name without the suffix ("pt-BR" -> "pt",
    "zh_CN" -> "zh", "English" -> "en", "Base" -> "base"); None if not a language name."""
    low = name.lower()
    if low == "base":
        return "base"
    if low in LEGACY:
        return LEGACY[low]
    m = TAG_RE.match(name)
    return m.group(1).lower() if m else None


def is_vendored(path):
    for part in path.split("/"):
        low = part.lower()
        if low in VENDOR or low.endswith(".framework") or low.endswith(".xcframework"):
            return True
    return False


def lproj_folders(paths):
    """{folder path: [file paths]} for the outermost .lproj folder on each file path."""
    folders = {}
    for p in paths:
        parts = p.split("/")
        for i, part in enumerate(parts[:-1]):
            if part.lower().endswith(".lproj"):
                folders.setdefault("/".join(parts[:i + 1]), []).append(p)
                break
    return folders


def classify(paths):
    """One record per .lproj folder. kind: "country" (name is a code in FIXES), "suspect"
    (a code in SUSPECT) or ""."""
    out = []
    for folder, files in sorted(lproj_folders(paths).items()):
        base = folder.rsplit("/", 1)[-1]
        name = base[:-len(".lproj")]
        primary = lproj_primary(name)
        kind = "country" if primary in FIXES else "suspect" if primary in SUSPECT else ""
        out.append({"folder": folder, "parent": folder.rsplit("/", 1)[0] if "/" in folder else "",
                    "name": name, "primary": primary, "kind": kind,
                    "vendored": is_vendored(folder), "files": sorted(files)})
    return out


def summarize(folders):
    """Returns (languages, flagged). languages: sorted primaries of the repository's own
    (not vendored) folders, without base. flagged: own folders of kind "country". Sets
    "fix" and "correct_present" on own country and suspect folders."""
    own = [f for f in folders if not f["vendored"]]
    langs = sorted({f["primary"] for f in own if f["primary"] and f["primary"] != "base"})
    for f in own:
        if f["kind"]:
            want = FIXES.get(f["primary"]) or SUSPECT.get(f["primary"])
            accepted = ("he", "iw") if want == "he" else (want,)
            f["fix"] = want
            f["correct_present"] = any(g["primary"] in accepted for g in own)
    flagged = [f for f in own if f["kind"] == "country"]
    return langs, flagged


def translated(languages):
    """A repository has translations when one of its own folders is for a language other
    than English (Base does not count)."""
    return any(lang not in ("base", "en") for lang in languages)


# ------------------------------------------------------------------ file contents

def decode(data):
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16", "replace")
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    if len(data) >= 4 and data[1:2] == b"\x00" and data[3:4] == b"\x00":
        return data.decode("utf-16-le", "replace")
    return data.decode("utf-8", "replace")


def parse_strings(data):
    """{key: value} from an Apple .strings file (bytes); comments skipped, escapes kept as
    written, anything unreadable ignored."""
    out = {}
    for m in TOKEN_RE.finditer(decode(data)):
        if m.group(1) is not None:
            out[m.group(1)] = m.group(2)
    return out


def letter_script(c):
    if not unicodedata.category(c).startswith("L"):
        return None
    words = unicodedata.name(c, "").split()
    if len(words) > 1 and words[0] in ("FULLWIDTH", "HALFWIDTH"):
        words = words[1:]
    if not words:
        return None
    head = words[0]
    if head == "CJK":
        return "Han"
    if head == "HIRAGANA" or head.startswith("KATAKANA"):
        return "Kana"
    if head in SCRIPT_WORDS:
        return head.title()
    return None


def scripts_of(text):
    return {s for s in map(letter_script, text) if s}


def folder_content(f, read, all_folders):
    """Translation evidence for one folder. read(path) returns bytes or None. Compares each
    .strings file with the same file in a sibling English or Base folder; without five
    shared keys, falls back to the script the language is written in."""
    names = [p for p in f["files"] if p.endswith(".strings")][:MAX_STRINGS_FILES]
    folders = {g["folder"] for g in all_folders}
    ref_folder = ""
    for r in REF_NAMES:
        cand = (f["parent"] + "/" if f["parent"] else "") + r + ".lproj"
        if cand in folders and cand != f["folder"]:
            ref_folder = cand
            break
    want = EXPECTED_SCRIPT.get(f["primary"])
    values = shared = differ = with_letters = expected = 0
    for p in names:
        data = read(p)
        if data is None:
            continue
        vals = parse_strings(data)
        values += len(vals)
        for v in vals.values():
            sc = scripts_of(v)
            if sc:
                with_letters += 1
                if want and sc & want:
                    expected += 1
        if ref_folder:
            rdata = read(ref_folder + p[len(f["folder"]):])
            if rdata is not None:
                ref = parse_strings(rdata)
                for k, v in vals.items():
                    if k in ref:
                        shared += 1
                        if v != ref[k]:
                            differ += 1
    if shared >= 5:
        holds = "yes" if 2 * differ >= shared else "no"
    elif want and with_letters >= 5:
        holds = "yes" if 2 * expected >= with_letters else "no"
    else:
        holds = "unknown"
    return {"strings_files": len(names), "values": values, "ref_folder": ref_folder,
            "shared_keys": shared, "differing": differ, "with_letters": with_letters,
            "expected_script": expected, "holds_translation": holds}


def pbx_info(name, pbx_texts):
    """(in_pbxproj, known_region) for an .lproj name: whether any own Xcode project file
    names "<name>.lproj", and whether <name> is in a knownRegions list."""
    if not pbx_texts:
        return "no pbxproj", "no pbxproj"
    in_proj = any((name + ".lproj") in t for t in pbx_texts)
    known = False
    for t in pbx_texts:
        for m in KNOWN_RE.finditer(t):
            toks = [x.strip().strip('"') for x in re.split(r"[,\s]+", m.group(1))]
            if name in toks:
                known = True
    return ("yes" if in_proj else "no"), ("yes" if known else "no")


def code_mentions(name, code_texts):
    """Up to three own source files that quote the folder name ("cz", 'cz') or name
    cz.lproj: a sign that an in-app language picker may load the folder by that code."""
    pat = re.compile(r"[\"']%s[\"']|\b%s\.lproj" % (re.escape(name), re.escape(name)))
    hits = []
    for p, text in code_texts:
        if pat.search(text):
            hits.append(p)
            if len(hits) >= 3:
                break
    return hits


def xcstrings_languages(data):
    """Sorted language keys used in an Xcode String Catalog, or None if it is not one."""
    try:
        obj = json.loads(decode(data))
    except Exception:
        return None
    strings = obj.get("strings") if isinstance(obj, dict) else None
    if not isinstance(strings, dict):
        return None
    langs = set()
    for v in strings.values():
        loc = v.get("localizations") if isinstance(v, dict) else None
        if isinstance(loc, dict):
            langs.update(str(k) for k in loc)
    return sorted(langs)


# ------------------------------------------------------------------ population and git

def population(doc):
    """Unique GitHub repositories (https://github.com/<owner>/<repo>) named as "source" in
    the list's projects, sorted case-insensitively."""
    seen = {}
    for p in doc.get("projects", []):
        src = (p.get("source") or "").strip() if isinstance(p, dict) else ""
        m = GH_RE.match(src)
        if not m:
            continue
        owner, name = m.group(1), m.group(2)
        if name.lower().endswith(".git"):
            name = name[:-4]
        if not name or name in (".", ".."):
            continue
        url = "https://github.com/%s/%s" % (owner, name)
        seen.setdefault(url.lower(), url)
    return [seen[k] for k in sorted(seen)]


def git(args, timeout=300):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_LFS_SKIP_SMUDGE="1", GIT_ASKPASS="true")
    return subprocess.run(["git"] + args, env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def fetch_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def fetch_tree(url, tmp_root):
    """Blobless fetch of HEAD. Returns (dir, commit, paths) or raises RuntimeError."""
    d = tempfile.mkdtemp(dir=tmp_root)
    s = os.path.join(d, "s")
    git(["init", "--quiet", s])
    git(["-C", s, "remote", "add", "origin", url])
    r = git(["-C", s, "fetch", "--quiet", "--depth", "1", "--filter=blob:none", "origin", "HEAD"])
    if r.returncode != 0:
        raise RuntimeError("fetch failed: " + ((r.stderr.strip().splitlines() or [""])[-1])[:200])
    commit = git(["-C", s, "rev-parse", "FETCH_HEAD"]).stdout.strip()
    lt = git(["-C", s, "ls-tree", "-r", "-z", "--name-only", commit])
    if lt.returncode != 0:
        raise RuntimeError("ls-tree failed: " + lt.stderr.strip()[:200])
    return s, commit, [p for p in lt.stdout.split("\0") if p]


def sparse_checkout(s, commit, patterns):
    git(["-C", s, "config", "core.sparseCheckout", "true"])
    git(["-C", s, "config", "core.sparseCheckoutCone", "false"])
    with open(os.path.join(s, ".git", "info", "sparse-checkout"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(patterns) + "\n")
    co = git(["-C", s, "checkout", "--quiet", commit], timeout=900)
    if co.returncode != 0:
        raise RuntimeError("checkout failed: " + co.stderr.strip()[:200])


def analyse(url, tmp_root):
    res = {"repo": url, "status": "ok", "commit": "", "n_paths": 0, "n_lproj": 0,
           "languages": [], "names": [], "folders": [], "xcstrings": []}
    t0 = time.time()
    s = None
    try:
        s, res["commit"], paths = fetch_tree(url, tmp_root)
        res["n_paths"] = len(paths)
        folders = classify(paths)
        res["n_lproj"] = len(folders)
        res["names"] = sorted({f["name"] for f in folders if not f["vendored"]})
        res["languages"], flagged = summarize(folders)
        suspects = [f for f in folders if f["kind"] == "suspect" and not f["vendored"]]
        xc = [p for p in paths if p.endswith(".xcstrings") and not is_vendored(p)]
        patterns = SPARSE_FULL if (flagged or suspects) else SPARSE_XC if xc else None
        if patterns:
            sparse_checkout(s, res["commit"], patterns)

            def read(p):
                fp = os.path.join(s, *p.split("/"))
                try:
                    if not os.path.isfile(fp) or os.path.getsize(fp) > MAX_BYTES:
                        return None
                    with open(fp, "rb") as fh:
                        return fh.read()
                except OSError:
                    return None

            for p in xc[:MAX_XCSTRINGS]:
                data = read(p)
                res["xcstrings"].append({"file": p, "languages": (
                    xcstrings_languages(data) if data is not None else None)})
            if flagged or suspects:
                pbx = [decode(d) for d in (read(p) for p in paths
                                           if p.endswith(".pbxproj") and not is_vendored(p)) if d]
                code_paths = [p for p in paths if p.endswith(CODE_EXT) and not is_vendored(p)]
                code = []
                for p in code_paths[:MAX_CODE_FILES]:
                    d = read(p)
                    if d:
                        code.append((p, decode(d)))
                for f in flagged + suspects:
                    f.update(folder_content(f, read, folders))
                    f["in_pbxproj"], f["known_region"] = pbx_info(f["name"], pbx)
                    f["code_mentions"] = code_mentions(f["name"], code)
        kept = []
        for f in folders:
            if f["kind"]:
                f = dict(f)
                f["n_files"] = len(f.pop("files"))
                kept.append(f)
        res["folders"] = kept
    except subprocess.TimeoutExpired:
        res["status"] = "timeout"
    except Exception as exc:  # record, keep going
        res["status"] = ("error: %r" % (exc,))[:240]
    finally:
        res["seconds"] = round(time.time() - t0, 1)
        if s:
            shutil.rmtree(os.path.dirname(s), ignore_errors=True)
    return res


# ------------------------------------------------------------------ grading

def own_country(r):
    return [f for f in r["folders"] if f["kind"] == "country" and not f["vendored"]]


def grade(results):
    """Pre-registered verdicts G, P1-P4 (PREREG.md) and the counts behind them."""
    read = [r for r in results if r["status"] == "ok"]
    trans = [r for r in read if translated(r["languages"])]
    flagged = [r for r in trans if own_country(r)]
    n, k = len(trans), len(flagged)
    unreach = [r for r in flagged if any(not f.get("correct_present") for f in own_country(r))]
    folders = [f for r in flagged for f in own_country(r)]
    by_code = {}
    for f in folders:
        by_code[f["primary"]] = by_code.get(f["primary"], 0) + 1
    known = [f for f in folders if f.get("holds_translation") in ("yes", "no")]
    yes = [f for f in known if f["holds_translation"] == "yes"]
    v = {}
    gate = len(read) >= GATE_READ and n >= GATE_TRANSLATED
    v["G"] = ("PASSED" if gate else "FAILED (%d read, %d with translations)" % (len(read), n))
    if not gate:
        for p in ("P1", "P2", "P3", "P4"):
            v[p] = "NOT TESTABLE (gate)"
    else:
        v["P1"] = "HELD" if (1000 * k >= 3 * n and 20 * k <= n) else "FAILED"
        v["P2"] = ("NOT TESTABLE (%d flagged repositories)" % k if k < MIN_TESTABLE
                   else "HELD" if 2 * len(unreach) >= k else "FAILED")
        if len(folders) < MIN_TESTABLE:
            v["P3"] = "NOT TESTABLE (%d folders)" % len(folders)
        else:
            top = max(by_code.values())
            tops = {c for c, x in by_code.items() if x == top}
            v["P3"] = "HELD" if tops <= P3_SET else "FAILED"
        v["P4"] = ("NOT TESTABLE (%d folders with known content)" % len(known)
                   if len(known) < MIN_TESTABLE
                   else "HELD" if 4 * len(yes) >= 3 * len(known) else "FAILED")
    counts = {"read": len(read), "translated": n, "flagged_repos": k,
              "flagged_share_pct": round(100.0 * k / n, 2) if n else None,
              "unreachable_repos": len(unreach), "flagged_folders": len(folders),
              "folders_by_code": dict(sorted(by_code.items(), key=lambda kv: (-kv[1], kv[0]))),
              "content_known": len(known), "content_translation": len(yes)}
    return v, counts, flagged


def sample_rows(flagged):
    rows = []
    for i, r in enumerate(sorted(flagged, key=lambda r: key(r["repo"]))[:SAMPLE_REPOS], 1):
        f = sorted(own_country(r), key=lambda f: key(r["repo"], f["folder"]))[0]
        rows.append({"sample": i, "repo": r["repo"], "commit": r["commit"],
                     "folder": f["folder"], "name": f["name"], "fix": f.get("fix", ""),
                     "correct_present": f.get("correct_present", ""),
                     "holds_translation": f.get("holds_translation", ""),
                     "in_pbxproj": f.get("in_pbxproj", ""),
                     "known_region": f.get("known_region", ""),
                     "code_mentions": " ".join(f.get("code_mentions", [])),
                     "label": "", "note": ""})
    return rows


def write_csv(path, cols, rows):
    with open(path, "w", encoding="utf-8", errors="replace", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for row in rows:
            w.writerow({c: str(row.get(c, "")).encode("utf-8", "replace").decode("utf-8")
                        for c in cols})


FOLDER_COLS = ["repo", "commit", "folder", "name", "kind", "vendored", "fix", "correct_present",
               "n_files", "strings_files", "values", "ref_folder", "shared_keys", "differing",
               "with_letters", "expected_script", "holds_translation", "in_pbxproj",
               "known_region", "code_mentions"]


def exploratory(results):
    read = [r for r in results if r["status"] == "ok"]
    vend = [(r["repo"], f) for r in read for f in r["folders"]
            if f["kind"] == "country" and f["vendored"]]
    sus = [f for r in read for f in r["folders"] if f["kind"] == "suspect" and not f["vendored"]]
    sus_by = {}
    for f in sus:
        d = sus_by.setdefault(f["primary"], {"folders": 0, "correct_present": 0,
                                             "expected_script_majority": 0})
        d["folders"] += 1
        d["correct_present"] += 1 if f.get("correct_present") else 0
        if f.get("with_letters", 0) >= 5 and 2 * f.get("expected_script", 0) >= f["with_letters"]:
            d["expected_script_majority"] += 1
    xc_repos = [r for r in read if r["xcstrings"]]
    xc_flag = {}
    for r in xc_repos:
        for x in r["xcstrings"]:
            for lang in x["languages"] or []:
                prim = lproj_primary(lang)
                if prim in FIXES:
                    xc_flag.setdefault(r["repo"], set()).add(lang)
    names = {}
    for r in read:
        for nme in r["names"]:
            names[nme] = names.get(nme, 0) + 1
    region_uk = sorted({"%s:%s" % (r["repo"], nme) for r in read for nme in r["names"]
                        if re.match(r"^[A-Za-z]{2,3}[-_]UK$", nme)})
    return {
        "vendored_country_folders": len(vend),
        "vendored_country_repos": len({u for u, _ in vend}),
        "vendored_codes": dict(sorted({f["primary"]: sum(1 for _, g in vend
                                                         if g["primary"] == f["primary"])
                                       for _, f in vend}.items())),
        "suspect_codes": dict(sorted(sus_by.items())),
        "xcstrings_repos": len(xc_repos),
        "xcstrings_country_codes": {u: sorted(c) for u, c in sorted(xc_flag.items())},
        "region_uk_names": region_uk,
        "top_lproj_names": dict(sorted(names.items(), key=lambda kv: (-kv[1], kv[0]))[:60]),
    }


def wait_for_prereg(minutes, say):
    end = time.time() + minutes * 60
    while True:
        try:
            text = fetch_text(PREREG_URL).decode("utf-8")
            if PREREG_MARK in text:
                return hashlib.sha256(text.encode("utf-8")).hexdigest()
        except OSError:
            pass
        if time.time() > end:
            return None
        say("waiting for PREREG.md")
        time.sleep(120)


def list_commit():
    r = git(["ls-remote", LIST_REPO, "HEAD"], timeout=120)
    sha = r.stdout.split()[0] if r.returncode == 0 and r.stdout.split() else ""
    if not re.match(r"^[0-9a-f]{40}$", sha):
        raise RuntimeError("could not read the list's HEAD: " + r.stderr.strip()[:200])
    return sha


def main(out, say, workers=8, prereg_wait_minutes=360):
    started = time.time()
    prereg_sha = wait_for_prereg(prereg_wait_minutes, say)
    if not prereg_sha:
        say("PREREG.md not public; stopping before reading any repository")
        return 4
    say("prereg sha256 %s" % prereg_sha)
    sha = list_commit()
    doc = json.loads(fetch_text(LIST_RAW % sha).decode("utf-8"))
    repos = population(doc)
    say("list commit %s: %d projects, %d GitHub repositories" % (
        sha, len(doc.get("projects", [])), len(repos)))
    tmp_root = tempfile.mkdtemp(prefix="lproj-")
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(lambda u: analyse(u, tmp_root), repos))
    shutil.rmtree(tmp_root, ignore_errors=True)

    with open(os.path.join(out, "results.jsonl"), "w", encoding="utf-8", errors="replace") as fh:
        for r in results:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    write_csv(os.path.join(out, "repos.csv"),
              ["repo", "commit", "status", "seconds", "n_paths", "n_lproj", "languages",
               "translated", "country_folders", "xcstrings"],
              [dict(r, languages=" ".join(r["languages"]),
                    translated="yes" if translated(r["languages"]) else "no",
                    country_folders=" ".join(f["name"] for f in own_country(r)),
                    xcstrings=len(r["xcstrings"])) for r in results])
    write_csv(os.path.join(out, "folders.csv"), FOLDER_COLS,
              [dict(f, repo=r["repo"], commit=r["commit"],
                    code_mentions=" ".join(f.get("code_mentions", [])))
               for r in results for f in r["folders"]])
    verdicts, counts, flagged = grade(results)
    rows = sample_rows(flagged) if verdicts["G"] == "PASSED" else []
    write_csv(os.path.join(out, "sample.csv"),
              ["sample", "repo", "commit", "folder", "name", "fix", "correct_present",
               "holds_translation", "in_pbxproj", "known_region", "code_mentions", "label",
               "note"], rows)
    verdicts["H1"] = ("PENDING HAND CHECK (%d repositories)" % len(rows) if len(rows) >= 6
                      else "NOT TESTABLE (sample of %d)" % len(rows))
    status = {}
    for r in results:
        st = r["status"] if r["status"] in ("ok", "timeout") else r["status"].split(":")[0]
        status[st] = status.get(st, 0) + 1
    summary = {"verdicts": verdicts, "counts": counts, "prereg_sha256": prereg_sha,
               "list_commit": sha, "list_projects": len(doc.get("projects", [])),
               "population": len(repos), "status": dict(sorted(status.items())),
               "exploratory": exploratory(results),
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
