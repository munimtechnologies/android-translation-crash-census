#!/usr/bin/env python3
# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Why Android apps ship translations their per-app language list hides (pre-registered).

Android Lint has warned since AGP 7.4 (check UnusedTranslation) when a language with translated
resources is missing from the app's android:localeConfig list. Yet the locale-config census in
this repository found 74 F-Droid apps whose hand-written list leaves out translations they ship
("orphans"). This job asks why, for those 74 apps and for the apps whose list matches
("clean"), at the commit the census read:

  - is the Android Gradle Plugin new enough to have the check (7.4 or later)?
  - does any CI configuration run an Android Lint task?
  - is the check made fatal (warningsAsErrors, or UnusedTranslation raised to error/fatal)?
  - is it switched off, ignored, or listed in a lint baseline?

The groups come from locale-config/lists.csv at a pinned census commit. For every repository
the job makes a shallow, blob-less clone, moves to the census commit when it can (falling back
to the default branch head), lists the files, and sparse-checks-out only CI files, Gradle files,
version catalogs, lint XML files, manifests and res/xml files. See PREREG.md for the
predictions and how they are graded.

Made with AI agents by MV2 of Munim, Inc. Standard library only. Needs git.
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

VERSION = "0.1.0"
CENSUS = "https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/"
LISTS_COMMIT = "e3da4889b27e1e2a9682b3f9c95af475dc7f8f4a"
LISTS_URL = CENSUS + LISTS_COMMIT + "/locale-config/lists.csv"
PREREG_URL = CENSUS + "main/lint-gate/PREREG.md"
PREREG_MARK = "lint-gate PREREG v1"
MAX_BYTES = 2000000

# Pre-registered thresholds (PREREG.md).
GATE_O_READ = 60
GATE_C_READ = 150
L1_MIN_PARSED = 40
L1_SHARE = 75      # percent of orphan repos with a parsed AGP version that are on 7.4 or later
L2_MAX = 4         # orphan repos where UnusedTranslation is fatal
L3_SHARE = 30      # percent of orphan repos whose CI runs an Android Lint task (upper bound)
L4_BAND = 10       # percentage points: |clean rate - orphan rate| for CI lint
L5_MAX = 5         # orphan repos that suppress or baseline UnusedTranslation
SAMPLE_PER_STRATUM = 6

SPARSE = ["/.github/workflows/*", "/.forgejo/workflows/*", "/.gitea/workflows/*",
          "/.gitlab-ci.yml", "/.gitlab/**", "/.gitlab-ci/**", "/.travis.yml", "/bitrise.yml",
          "/Jenkinsfile", "/azure-pipelines.yml", "/.cirrus.yml", "/codemagic.yaml",
          "/appveyor.yml", "/.woodpecker.yml", "/.woodpecker.yaml", "/.woodpecker/**",
          "/.builds/**", "/.circleci/**", "**/Fastfile", "**/*.gradle", "**/*.gradle.kts",
          "**/gradle.properties", "**/*.toml", "**/buildSrc/**/*.kt", "**/build-logic/**/*.kt",
          "**/*lint*.xml", "**/*baseline*.xml", "**/AndroidManifest.xml", "**/res/xml/*.xml"]

CI_NAMES = frozenset({".gitlab-ci.yml", ".travis.yml", "bitrise.yml", "jenkinsfile",
                      "azure-pipelines.yml", ".cirrus.yml", "codemagic.yaml", "appveyor.yml",
                      ".woodpecker.yml", ".woodpecker.yaml", ".circleci/config.yml"})
_CI_WORKFLOW = re.compile(r"^\.(?:github|forgejo|gitea)/workflows/[^/]+\.ya?ml$")
_CI_DIR = re.compile(r"^\.(?:woodpecker|builds|gitlab-ci|gitlab)/(?:[^/]+/)*[^/]+\.ya?ml$")


# ---------------------------------------------------------------- file roles

def is_ci(path):
    low = path.lower()
    if low in CI_NAMES or _CI_WORKFLOW.match(low) or _CI_DIR.match(low):
        return True
    return low.rsplit("/", 1)[-1] == "fastfile"


def is_gradle_script(path):
    low = path.lower()
    name = low.rsplit("/", 1)[-1]
    if name.endswith(".gradle") or name.endswith(".gradle.kts"):
        return True
    padded = "/" + low
    return name.endswith(".kt") and ("/buildsrc/" in padded or "/build-logic/" in padded)


def is_catalog(path):
    low = path.lower()
    return low.endswith(".toml") and ("/gradle/" in "/" + low or low.endswith("libs.versions.toml"))


def is_properties(path):
    return path.lower().rsplit("/", 1)[-1] == "gradle.properties"


def is_lint_xml(path):
    name = path.lower().rsplit("/", 1)[-1]
    return name.endswith(".xml") and ("lint" in name or "baseline" in name)


def is_res_xml(path):
    low = path.lower()
    return low.rsplit("/", 1)[-1] == "androidmanifest.xml" or "/res/xml/" in "/" + low


def role(path):
    return (is_ci(path) or is_gradle_script(path) or is_catalog(path) or is_properties(path)
            or is_lint_xml(path) or is_res_xml(path))


# ---------------------------------------------------------------- Gradle text

def strip_comments(text):
    """Remove // and /* */ comments outside string literals (Groovy and Kotlin).

    Newlines inside block comments are kept. A one-quote string also ends at a newline, so a
    stray apostrophe cannot swallow the rest of the file."""
    out, i, n, quote = [], 0, len(text), None
    while i < n:
        c = text[i]
        if quote:
            if text.startswith(quote, i):
                out.append(quote)
                i += len(quote)
                quote = None
            elif c == "\\" and len(quote) == 1 and i + 1 < n:
                out.append(text[i:i + 2])
                i += 2
            else:
                if c == "\n" and len(quote) == 1:
                    quote = None
                out.append(c)
                i += 1
            continue
        if text.startswith('"""', i):
            quote = '"""'
            out.append(quote)
            i += 3
        elif c == '"' or c == "'":
            quote = c
            out.append(c)
            i += 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            end = n if j < 0 else j + 2
            out.append("\n" * text.count("\n", i, end))
            i = end
        else:
            out.append(c)
            i += 1
    return "".join(out)


def ver_tuple(v):
    m = re.match(r"\s*(\d+)\.(\d+)", v or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


AGP_COORD = re.compile(r"com\.android\.tools\.build:gradle:([^\s'\"\)]+)")
AGP_PLUGIN = re.compile(r"""\bid\s*\(?\s*["']com\.android\.(?:application|library|test|"""
                        r"""dynamic-feature)["']\s*\)?\s*version\s*\(?\s*["']([^"']+)["']""")


def toml_agp(text):
    """AGP versions named in a Gradle version catalog."""
    versions, section, found = {}, "", []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        m = re.match(r"^\[([^\]]+)\]$", line)
        if m:
            section = m.group(1).strip()
            continue
        if section == "versions":
            m = re.match(r'^([A-Za-z0-9_.\-]+)\s*=\s*"([^"]*)"', line)
            if m:
                versions[m.group(1)] = m.group(2)
        if ("com.android.tools.build:gradle" in line
                or re.search(r'\bid\s*=\s*"com\.android\.(?:application|library)"', line)):
            m = re.search(r'version\.ref\s*=\s*"([^"]+)"', line)
            if m:
                found.append(("ref", m.group(1)))
                continue
            m = re.search(r'\bversion\s*=\s*"([^"]+)"', line)
            if m:
                found.append(("v", m.group(1)))
                continue
            m = re.search(r'com\.android\.tools\.build:gradle:([^"]+)"', line)
            if m:
                found.append(("v", m.group(1)))
    out = []
    for kind, v in found:
        if kind == "ref":
            v = versions.get(v, "")
        if v:
            out.append(v)
    return out


def resolve_var(value, gradle_texts, props):
    """'$agp_version' or '${rootProject.ext.agpVersion}' -> the literal it is set to, or ''."""
    m = re.search(r"([A-Za-z_]\w*)\}?$", value)
    if not m:
        return ""
    name = m.group(1)
    rx = re.compile(r"\b%s\s*(?:=|:)\s*['\"]([0-9][^'\"]*)['\"]" % re.escape(name))
    for text in gradle_texts:
        hit = rx.search(text)
        if hit:
            return hit.group(1)
    for text in props:
        for line in text.splitlines():
            k, sep, v = line.partition("=")
            if sep and k.strip() == name and ver_tuple(v.strip()):
                return v.strip()
    return ""


def agp_versions(gradle, catalogs, props):
    """All AGP version strings found; gradle and catalogs are lists of texts."""
    out = []
    for text in gradle:
        for rx in (AGP_COORD, AGP_PLUGIN):
            for m in rx.finditer(text):
                v = m.group(1)
                if not ver_tuple(v) and v.startswith("$"):
                    v = resolve_var(v, gradle, props)
                if ver_tuple(v):
                    out.append(v)
    for text in catalogs:
        out += [v for v in toml_agp(text) if ver_tuple(v)]
    return out


# ---------------------------------------------------------------- CI

def ci_tasks(text):
    """Gradle tasks a CI file runs, as (task, line) pairs."""
    lines, buf = [], ""
    for raw in text.splitlines():
        s = raw.rstrip()
        if s.lstrip().startswith("#"):
            continue
        if s.endswith("\\"):
            buf += s[:-1] + " "
            continue
        lines.append(buf + s)
        buf = ""
    if buf:
        lines.append(buf)
    found = []
    for line in lines:
        args = None
        m = re.search(r"gradlew(?:\.bat)?\b(.*)$", line)
        if m:
            args = m.group(1)
        else:
            m = re.search(r"(?:^|[\s;&|(\"'`])gradle\s+(.*)$", line)
            if m:
                args = m.group(1)
            else:
                m = re.match(r"^\s*-?\s*arguments\s*:\s*(.*)$", line)
                if m:
                    args = m.group(1)
                else:
                    m = re.search(r"\bgradle\(\s*task\s*:\s*[\"']([^\"']+)[\"']", line)
                    if m:
                        args = m.group(1)
        if args is None:
            continue
        for tok in re.split(r"[\s,]+", args):
            tok = tok.strip("\"'`;()[]")
            if not tok or tok.startswith("-") or tok.startswith("$"):
                continue
            found.append((tok.split(":")[-1], line.strip()[:300]))
    return found


def task_class(task):
    if re.fullmatch(r"lintVital[A-Za-z0-9]*", task):
        return "vital"
    if re.fullmatch(r"lintKotlin[A-Za-z0-9]*", task):
        return None
    if re.fullmatch(r"lint(?:[A-Z][A-Za-z0-9]*)?", task):
        return "lint"
    if task in ("check", "build"):
        return "implicit"
    return None


# ---------------------------------------------------------------- lint settings

WAE = re.compile(r"\b(?:warningsAsErrors|isWarningsAsErrors)\s*(?:=\s*|\(\s*)?true\b")
ABORT_FALSE = re.compile(r"\b(?:abortOnError|isAbortOnError)\s*(?:=\s*|\(\s*)?false\b")
CHECK_RELEASE_FALSE = re.compile(
    r"\b(?:checkReleaseBuilds|isCheckReleaseBuilds)\s*(?:=\s*|\(\s*)?false\b")
FILTERS = re.compile(r"\b(?:resConfigs?|resourceConfigurations|localeFilters)\b")
LINT_BLOCK = re.compile(r"\b(?:lint|lintOptions)\s*\{")
ISSUE = re.compile(r"<issue\b([^>]*)>", re.S)
ATTR = re.compile(r'([\w:.\-]+)\s*=\s*"([^"]*)"')
XML_COMMENT = re.compile(r"<!--.*?-->", re.S)
TOOLS_IGNORE = re.compile(r'tools:ignore\s*=\s*"[^"]*\bUnusedTranslation\b')


def gradle_rule(line):
    if re.search(r"\b(?:error|fatal)\b", line):
        return "fatal"
    if re.search(r"\b(?:disable|ignore|informational)\b", line):
        return "suppressed"
    return "other"


def lint_xml_rules(text):
    """(fatal, suppressed) reasons from a lint.xml configuration file."""
    text = XML_COMMENT.sub("", text)
    fatal, suppressed = [], []
    if "<lint" not in text:
        return fatal, suppressed
    for m in ISSUE.finditer(text):
        a = dict(ATTR.findall(m.group(1)))
        ids = [x.strip() for x in a.get("id", "").split(",")]
        sev = a.get("severity", "").strip().lower()
        for i in ids:
            if i not in ("UnusedTranslation", "all"):
                continue
            if sev in ("error", "fatal"):
                fatal.append("lint.xml %s=%s" % (i, sev))
            elif sev in ("ignore", "informational"):
                suppressed.append("lint.xml %s=%s" % (i, sev))
    return fatal, suppressed


def analyse(files):
    """files: {path: text}. Returns the per-repository measures."""
    gradle = {p: strip_comments(t) for p, t in files.items() if is_gradle_script(p)}
    catalogs = [t for p, t in files.items() if is_catalog(p)]
    props = [t for p, t in files.items() if is_properties(p)]
    versions = agp_versions(list(gradle.values()), catalogs, props)
    best = max((ver_tuple(v) for v in versions), default=None)
    res = {"agp": "%d.%d" % best if best else "",
           "agp_ge_74": (best >= (7, 4)) if best else None,
           "agp_found": sorted(set(versions))[:10]}

    ci_files = sorted(p for p in files if is_ci(p))
    classes, lines = set(), []
    for p in ci_files:
        for task, line in ci_tasks(files[p]):
            c = task_class(task)
            if c:
                classes.add(c)
                if len(lines) < 12:
                    lines.append("%s [%s] %s" % (p, task, line))
    res.update(has_ci=bool(ci_files), ci_files=ci_files[:20], ci_lint="lint" in classes,
               ci_vital="vital" in classes, ci_implicit="implicit" in classes, ci_lines=lines)

    fatal, suppressed, other, baseline = [], [], [], []
    abort_false = check_release_false = filters = lint_block = False
    for p in sorted(gradle):
        text = gradle[p]
        if WAE.search(text):
            fatal.append("%s warningsAsErrors" % p)
        abort_false = abort_false or bool(ABORT_FALSE.search(text))
        check_release_false = check_release_false or bool(CHECK_RELEASE_FALSE.search(text))
        filters = filters or bool(FILTERS.search(text))
        lint_block = lint_block or bool(LINT_BLOCK.search(text))
        for line in text.splitlines():
            if "UnusedTranslation" in line:
                kind = gradle_rule(line)
                {"fatal": fatal, "suppressed": suppressed, "other": other}[kind].append(
                    "%s: %s" % (p, line.strip()[:200]))
    for p in sorted(files):
        text = files[p]
        if is_lint_xml(p):
            f, s = lint_xml_rules(text)
            fatal += ["%s %s" % (p, x) for x in f]
            suppressed += ["%s %s" % (p, x) for x in s]
            if "<issues" in text and 'id="UnusedTranslation"' in XML_COMMENT.sub("", text):
                baseline.append(p)
        if is_res_xml(p) and TOOLS_IGNORE.search(XML_COMMENT.sub("", text)):
            suppressed.append("%s tools:ignore" % p)
    res.update(fatal=bool(fatal), fatal_why=fatal[:10], suppressed=bool(suppressed),
               suppressed_why=suppressed[:10], other_rules=other[:10],
               baselined=bool(baseline), baseline_files=baseline[:10],
               abort_false=abort_false, check_release_false=check_release_false,
               filters=filters, lint_block=lint_block)
    return res


# ---------------------------------------------------------------- groups and grading

def groups(rows):
    """(orphan repos, clean repos, census head per repo) from locale-config lists.csv rows."""
    by = collections.defaultdict(list)
    for r in rows:
        by[r["repo"]].append(r)
    orphan, clean, heads = [], [], {}
    for repo in sorted(by):
        rs = by[repo]
        heads[repo] = rs[0]["head"]
        ev = [r for r in rs if r["evaluable"] == "yes"]
        if not ev:
            continue
        if any(r["orphan"].strip() for r in ev):
            orphan.append(repo)
        elif all(r["drift"] == "no" for r in ev):
            clean.append(repo)
    return orphan, clean, heads


def grade(o, c):
    """o, c: lists of result dicts with status 'ok' (orphan and clean repositories read)."""
    v = {}
    if len(o) < GATE_O_READ:
        for k in ("L1", "L2", "L3", "L4", "L5"):
            v[k] = "NOT TESTABLE (%d orphan repositories read, gate %d)" % (len(o), GATE_O_READ)
        return v
    parsed = [r for r in o if r["agp_ge_74"] is not None]
    ge = sum(1 for r in parsed if r["agp_ge_74"])
    if len(parsed) < L1_MIN_PARSED:
        v["L1"] = "NOT TESTABLE (%d with a parsed AGP version)" % len(parsed)
    else:
        v["L1"] = "HELD" if 100 * ge >= L1_SHARE * len(parsed) else "FAILED"
    v["L2"] = "HELD" if sum(1 for r in o if r["fatal"]) <= L2_MAX else "FAILED"
    o_n = sum(1 for r in o if r["ci_lint"])
    v["L3"] = "HELD" if 100 * o_n < L3_SHARE * len(o) else "FAILED"
    if len(c) < GATE_C_READ:
        v["L4"] = "NOT TESTABLE (%d clean repositories read, gate %d)" % (len(c), GATE_C_READ)
    else:
        c_n = sum(1 for r in c if r["ci_lint"])
        gap = 100 * (c_n * len(o) - o_n * len(c))
        v["L4"] = "HELD" if abs(gap) < L4_BAND * len(o) * len(c) else "FAILED"
    v["L5"] = ("HELD" if sum(1 for r in o if r["suppressed"] or r["baselined"]) <= L5_MAX
               else "FAILED")
    return v


def counts(rs):
    n = len(rs)

    def k(f):
        return sum(1 for r in rs if f(r))
    return {
        "read": n,
        "agp_parsed": k(lambda r: r["agp_ge_74"] is not None),
        "agp_ge_74": k(lambda r: r["agp_ge_74"] is True),
        "agp_lt_74": k(lambda r: r["agp_ge_74"] is False),
        "has_ci": k(lambda r: r["has_ci"]),
        "ci_lint": k(lambda r: r["ci_lint"]),
        "ci_vital_only": k(lambda r: r["ci_vital"] and not r["ci_lint"]),
        "ci_implicit_only": k(lambda r: r["ci_implicit"] and not r["ci_lint"]),
        "ci_lint_or_implicit": k(lambda r: r["ci_lint"] or r["ci_implicit"]),
        "fatal": k(lambda r: r["fatal"]),
        "suppressed": k(lambda r: r["suppressed"]),
        "baselined": k(lambda r: r["baselined"]),
        "suppressed_or_baselined": k(lambda r: r["suppressed"] or r["baselined"]),
        "abort_on_error_false": k(lambda r: r["abort_false"]),
        "check_release_builds_false": k(lambda r: r["check_release_false"]),
        "lint_block": k(lambda r: r["lint_block"]),
        "filters": k(lambda r: r["filters"]),
        "warns_unseen": k(lambda r: r["agp_ge_74"] is True and (r["ci_lint"] or r["ci_implicit"])
                          and not r["fatal"] and not r["suppressed"] and not r["baselined"]),
        "at_census_head": k(lambda r: r.get("at") == "census-head"),
    }


def sample_key(repo):
    return hashlib.sha256(("lint-gate v1|%s" % repo).encode("utf-8")).hexdigest()


def draw_sample(results):
    """6 repositories whose CI runs a lint task and 6 with CI but no lint task, by hash."""
    ok = sorted((r for r in results if r["status"] == "ok"), key=lambda r: sample_key(r["repo"]))
    s1 = [r for r in ok if r["ci_lint"]][:SAMPLE_PER_STRATUM]
    s2 = [r for r in ok if r["has_ci"] and not r["ci_lint"]][:SAMPLE_PER_STRATUM]
    return [("ci-lint", r) for r in s1] + [("ci-no-lint", r) for r in s2]


# ---------------------------------------------------------------- running

def git(args, timeout=240):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_LFS_SKIP_SMUDGE="1", GIT_ASKPASS="true")
    return subprocess.run(["git"] + args, env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def last_line(text):
    return (text.strip().splitlines() or [""])[-1][:200]


def process_repo(url, head, tmp_root):
    d = tempfile.mkdtemp(dir=tmp_root)
    res = {"repo": url, "census_head": head, "status": "ok"}
    t0 = time.time()
    try:
        s = os.path.join(d, "s")
        r = git(["clone", "--quiet", "--depth", "1", "--filter=blob:none", "--no-checkout",
                 "--single-branch", url, s])
        if r.returncode != 0:
            res.update(status="clone-failed", error=last_line(r.stderr))
            return res
        tip = git(["-C", s, "rev-parse", "HEAD"]).stdout.strip()
        commit, at = tip, "default-head"
        if head and tip == head:
            at = "census-head"
        elif head:
            f = git(["-C", s, "fetch", "--quiet", "--depth", "1", "--filter=blob:none",
                     "origin", head])
            if f.returncode == 0:
                commit, at = head, "census-head"
        res.update(commit=commit, at=at)
        lt = git(["-C", s, "ls-tree", "-r", "-z", "--name-only", commit])
        if lt.returncode != 0:
            res.update(status="error", error="ls-tree: " + last_line(lt.stderr))
            return res
        paths = [p for p in lt.stdout.split("\0") if p]
        chosen = [p for p in paths if role(p)]
        files = {}
        if chosen:
            git(["-C", s, "sparse-checkout", "set", "--no-cone"] + SPARSE)
            git(["-C", s, "checkout", "--quiet", "--detach", commit])
            if not any(os.path.isfile(os.path.join(s, *p.split("/"))) for p in chosen):
                git(["-C", s, "read-tree", "-mu", commit])
            for p in chosen:
                fp = os.path.join(s, *p.split("/"))
                try:
                    if os.path.isfile(fp) and os.path.getsize(fp) <= MAX_BYTES:
                        with open(fp, "rb") as fh:
                            files[p] = fh.read().decode("utf-8", "replace")
                except OSError:
                    pass
        res.update(paths_total=len(paths), files_wanted=len(chosen), files_read=len(files))
        res.update(analyse(files))
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


CONTROL_FILES = {
    ".github/workflows/ci.yml": "jobs:\n  b:\n    steps:\n      - run: ./gradlew \\\n"
                                "          :app:lintFdroidDebug assembleDebug\n",
    "build.gradle": "buildscript { dependencies { classpath 'com.android.tools.build:gradle:$agp' } }\n"
                    "ext.agp = '8.1.2'\n",
    "app/build.gradle.kts": "android {\n  lint {\n    // warningsAsErrors = true\n"
                            "    disable += \"UnusedTranslation\"\n  }\n}\n",
    "app/lint.xml": "<lint>\n  <!-- <issue id=\"UnusedTranslation\" severity=\"error\"/> -->\n"
                    "  <issue id=\"MissingTranslation\" severity=\"error\"/>\n</lint>\n",
}


def control():
    r = analyse(CONTROL_FILES)
    return (r["agp"] == "8.1" and r["agp_ge_74"] is True and r["ci_lint"] and not r["fatal"]
            and r["suppressed"] and not r["baselined"])


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


ROW_COLS = ["repo", "group", "status", "at", "commit", "agp", "agp_ge_74", "has_ci", "ci_lint",
            "ci_vital", "ci_implicit", "fatal", "suppressed", "baselined", "abort_false",
            "check_release_false", "lint_block", "filters", "ci_files", "ci_lines", "fatal_why",
            "suppressed_why", "other_rules", "baseline_files", "error"]
SAMPLE_COLS = ["sample", "stratum", "repo", "group", "commit", "ci_lint", "ci_files", "ci_lines",
               "label", "note"]


def clean(text):
    return str(text).encode("utf-8", "replace").decode("utf-8")


def flat(v):
    if isinstance(v, list):
        return clean(" | ".join(str(x) for x in v))[:2000]
    if v is None:
        return ""
    return clean(v)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--lists", help="local lists.csv instead of downloading")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--budget-minutes", type=float, default=150)
    ap.add_argument("--prereg-wait-minutes", type=float, default=300)
    ap.add_argument("--skip-prereg-check", action="store_true")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    started = time.time()
    with open(os.path.abspath(__file__), "rb") as f:
        own_sha = hashlib.sha256(f.read()).hexdigest()
    print("lint_gate %s" % VERSION, flush=True)
    if not control():
        print("positive control failed; stopping", file=sys.stderr)
        return 6
    prereg_sha = None
    if not a.skip_prereg_check:
        prereg_sha = wait_for_prereg(a.prereg_wait_minutes)
        if not prereg_sha:
            print("PREREG.md not public; stopping before reading any repository", file=sys.stderr)
            return 4
    if a.lists:
        with open(a.lists, "rb") as f:
            raw = f.read()
    else:
        with urllib.request.urlopen(LISTS_URL, timeout=120) as resp:
            raw = resp.read()
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
    orphan, clean_repos, heads = groups(rows)
    print("lists.csv rows %d; orphan repos %d; clean repos %d"
          % (len(rows), len(orphan), len(clean_repos)), flush=True)
    group_of = dict([(u, "orphan") for u in orphan] + [(u, "clean") for u in clean_repos])
    todo = orphan + clean_repos

    tmp_root = tempfile.mkdtemp(prefix="lint-gate-")
    deadline = time.time() + a.budget_minutes * 60

    def work(u):
        if time.time() > deadline:
            return {"repo": u, "status": "not-started"}
        return process_repo(u, heads.get(u, ""), tmp_root)

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for n, r in enumerate(ex.map(work, todo), 1):
            r["group"] = group_of[r["repo"]]
            results.append(r)
            if n % 50 == 0:
                print("%d/%d done, %.0f min" % (n, len(todo), (time.time() - started) / 60),
                      flush=True)
    shutil.rmtree(tmp_root, ignore_errors=True)

    with open(os.path.join(a.out_dir, "repos.jsonl"), "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=True, sort_keys=True) + "\n")
    with open(os.path.join(a.out_dir, "table.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ROW_COLS)
        w.writeheader()
        for r in results:
            w.writerow({k: flat(r.get(k)) for k in ROW_COLS})
    sample = draw_sample(results)
    with open(os.path.join(a.out_dir, "sample.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SAMPLE_COLS)
        w.writeheader()
        for i, (stratum, r) in enumerate(sample, 1):
            w.writerow({"sample": i, "stratum": stratum, "repo": r["repo"], "group": r["group"],
                        "commit": r.get("commit", ""), "ci_lint": r["ci_lint"],
                        "ci_files": flat(r["ci_files"]), "ci_lines": flat(r["ci_lines"]),
                        "label": "", "note": ""})

    o = [r for r in results if r["group"] == "orphan" and r["status"] == "ok"]
    c = [r for r in results if r["group"] == "clean" and r["status"] == "ok"]
    verdicts = grade(o, c)
    verdicts["H1"] = "PENDING HAND CHECK (sample of %d)" % len(sample)
    summary = {
        "verdicts": verdicts, "version": VERSION, "script_sha256": own_sha,
        "prereg_sha256": prereg_sha, "lists_url": LISTS_URL,
        "lists_sha256": hashlib.sha256(raw).hexdigest(), "lists_rows": len(rows),
        "orphan_repos": len(orphan), "clean_repos": len(clean_repos),
        "status_counts": {g: dict(collections.Counter(r["status"] for r in results
                                                      if r["group"] == g))
                          for g in ("orphan", "clean")},
        "orphan": counts(o), "clean": counts(c),
        "orphan_fatal": [[r["repo"], r["fatal_why"]] for r in o if r["fatal"]],
        "orphan_suppressed_or_baselined": [[r["repo"], r["suppressed_why"], r["baseline_files"]]
                                           for r in o if r["suppressed"] or r["baselined"]],
        "orphan_agp_lt_74": [[r["repo"], r["agp"]] for r in o if r["agp_ge_74"] is False],
        "sample_size": len(sample), "positive_control": True,
        "minutes": round((time.time() - started) / 60, 1),
    }
    with open(os.path.join(a.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=True, indent=1, sort_keys=True)
    print(json.dumps(verdicts), flush=True)
    print(json.dumps({"orphan": summary["orphan"], "clean": summary["clean"]}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
