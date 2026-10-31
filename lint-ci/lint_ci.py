#!/usr/bin/env python3
# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Android Lint in CI and Java format errors in shipped translations (pre-registered).

For every repository in hidden-chars/repos.txt (the F-Droid source repositories of the census),
reads at one commit both (a) the CI configuration files and (b) the Android string resources.
(a) puts the repository in group L if a Gradle line of its CI config names an Android Lint task
(lint, lintDebug, :app:lintRelease, ...), otherwise in group O. (b) runs l10n-guard 0.15.0's
check_android on every translated strings file against the source file of the same name and counts
the strings with a `java-format` error, and counts the exposure: translated strings whose source
has a Java format conversion. See PREREG.md for the predictions and how they are graded.

Same corpus, clone method and locale rules as zwsp_langs.py 0.1.0, whose helpers are copied here
so the script stands alone. Needs git and l10n_guard.py 0.15.0 next to this file (tag v0.15.0 of
munimtechnologies/l10n-guard).

Made with AI agents by MV2 of Munim, Inc. Standard library only.
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

import l10n_guard

VERSION = "0.1.0"
GUARD_VERSION = "0.15.0"
BASE = "https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/main/"
REPOS_URL = BASE + "hidden-chars/repos.txt"
PREREG_URL = BASE + "lint-ci/PREREG.md"
PREREG_MARK = "lint-ci PREREG v1"

CI_FILES = (".gitlab-ci.yml", ".gitlab-ci.yaml", ".travis.yml", ".drone.yml", ".cirrus.yml",
            ".woodpecker.yml", ".woodpecker.yaml", "bitrise.yml", "codemagic.yaml",
            "azure-pipelines.yml", "appveyor.yml", "Jenkinsfile", ".build.yml")
CI_DIRS = (".github/workflows", ".gitlab/ci", ".woodpecker", ".circleci", ".forgejo/workflows",
           ".gitea/workflows", ".builds")
GRADLE_FILES = ("build.gradle", "build.gradle.kts", "lint.xml")  # exploratory only
SPARSE = (["**/res/values*/*.xml"] + ["/" + f for f in CI_FILES] + ["/" + d + "/" for d in CI_DIRS]
          + ["/build.gradle*", "/*/build.gradle*", "/lint.xml", "/*/lint.xml"])

# A line counts as a Gradle line if it mentions gradle (./gradlew, gradle-build-action, setup-gradle)
# or is a YAML "arguments:" / "tasks:" line (gradle actions take their tasks there).
GRADLE_LINE = re.compile(r"gradle|^\s*-?\s*(?:arguments|tasks)\s*:", re.I)
SKIP_LINE = re.compile(r"^\s*(?:#|//|-?\s*name\s*:)")  # comments and step names run nothing
LINT_TASK = re.compile(r"(?<![\w$./-])(?:[\w-]+:)*(lint(?:[A-Z]\w*)?)(?![\w./-])")
NOT_ANDROID_LINT = re.compile(r"^lintKotlin")  # kotlinter's task, not Android Lint
CHECK_TASK = re.compile(r"(?<![\w$./-])(?:[\w-]+:)*(check|build)(?![\w./-])")  # exploratory

# A Java format conversion in the source string (exposure). %% and %n are not conversions.
JAVA_SPEC = re.compile(r"%(?:\d+\$)?[-#+ 0,(]*\d*(?:\.\d+)?[bBhHsScCdoxXeEfgGaAtT]")

# Pre-registered thresholds (PREREG.md).
GATE_L_REPOS = 50
GATE_O_REPOS = 50
GATE_L_EXPOSURE = 20000
STRATA = ((1, 50), (50, 500), (500, None))
STRATUM_MIN = 10

# From zwsp_langs.py 0.1.0 (unchanged).
_U_ESC = re.compile(r"(?<!\\)\\u([0-9A-Fa-f]{4})")
_LOCALE_DIR = re.compile(
    r"^values-(?:([a-z]{2,3})(?:-r([A-Z]{2}|[0-9]{3}))?|b\+([a-zA-Z]{2,3})(?:\+[A-Za-z0-9]+)*)$")
_NOT_LOCALES = {"car"}
_PSEUDO = {("en", "XA"), ("ar", "XB")}


def decode_android(text):
    return _U_ESC.sub(lambda m: chr(int(m.group(1), 16)), text)


def locale_of(dirname):
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
    return parse_root(ET.parse(path).getroot())


def parse_values_text(text):
    return parse_root(ET.fromstring(text))


def parse_root(root):
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


def exposure(source, target):
    """Translated strings (each plural or array item counts) whose source has a Java conversion."""
    n = 0
    for key, tlist in target.items():
        slist = source.get(key)
        if not slist or not tlist or not JAVA_SPEC.search("".join(slist).replace("%%", "")):
            continue
        n += sum(1 for t in tlist if t.strip())
    return n


def lint_evidence(text):
    """(lint lines, check/build lines) of a CI file: Gradle lines naming those tasks."""
    lint, check = [], []
    for line in text.splitlines():
        if not GRADLE_LINE.search(line) or SKIP_LINE.match(line):
            continue
        if any(not NOT_ANDROID_LINT.match(m.group(1)) for m in LINT_TASK.finditer(line)):
            lint.append(line.strip()[:200])
        if CHECK_TASK.search(line):
            check.append(line.strip()[:200])
    return lint, check


def read_text(path):
    with open(path, "rb") as f:
        return f.read().decode("utf-8", "replace")


def ci_files(root):
    found = [f for f in CI_FILES if os.path.isfile(os.path.join(root, f))]
    for d in CI_DIRS:
        top = os.path.join(root, d)
        for dirpath, _, filenames in os.walk(top):
            for fn in sorted(filenames):
                found.append(os.path.relpath(os.path.join(dirpath, fn), root).replace(os.sep, "/"))
    return found


def scan_ci(root):
    files = ci_files(root)
    out = {"ci_files": files, "lint_lines": [], "check_lines": []}
    for rel in files:
        lint, check = lint_evidence(read_text(os.path.join(root, rel)))
        out["lint_lines"] += [rel + ": " + x for x in lint]
        out["check_lines"] += [rel + ": " + x for x in check]
    out["lint"] = bool(out["lint_lines"])
    out["check_build"] = bool(out["check_lines"])
    # Exploratory: lint switched off or softened in Gradle files.
    soft = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for fn in filenames:
            if fn in GRADLE_FILES:
                t = read_text(os.path.join(dirpath, fn))
                for pat in ("abortOnError false", "abortOnError = false", "isAbortOnError = false",
                            "lint-baseline", "StringFormat"):
                    if pat in t:
                        soft.append(pat)
    out["gradle_lint_settings"] = sorted(set(soft))
    return out


def java_format_rows(source_text, target_text):
    """Distinct (key, message) of l10n-guard `java-format` errors for one file pair."""
    seen = {}
    for p in l10n_guard.check_android(source_text, target_text):
        if p.get("code") == "java-format" and p.get("level") == l10n_guard.ERROR:
            seen.setdefault(p.get("key"), p.get("message", ""))
    return seen


def scan_strings(root):
    out = {"exposure": 0, "errors": 0, "pairs": 0, "guard_failed": 0, "rows": []}
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        if os.path.basename(dirpath) != "res" or "values" not in dirnames:
            continue
        src_dir = os.path.join(dirpath, "values")
        rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
        for d in dirnames:
            if not locale_of(d):
                continue
            tgt_dir = os.path.join(dirpath, d)
            for fn in sorted(os.listdir(tgt_dir)):
                sp, tp = os.path.join(src_dir, fn), os.path.join(tgt_dir, fn)
                if not fn.endswith(".xml") or not os.path.isfile(sp) or not os.path.isfile(tp):
                    continue
                try:
                    exp = exposure({k: v for k, v in parse_values(sp).items() if v},
                                   {k: v for k, v in parse_values(tp).items() if v})
                except (ET.ParseError, ValueError, OSError):
                    continue
                if not exp:
                    continue
                try:
                    found = java_format_rows(read_text(sp), read_text(tp))
                except Exception:  # a pair l10n-guard cannot read; counted, left out of exposure
                    out["guard_failed"] += 1
                    continue
                out["pairs"] += 1
                out["exposure"] += exp
                out["errors"] += len(found)
                for key, msg in sorted(found.items(), key=lambda kv: str(kv[0])):
                    out["rows"].append({"res_dir": rel, "locale_dir": d, "file": fn, "key": key,
                                        "message": str(msg)[:300]})
    return out


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
            return res
        git(["-C", s, "sparse-checkout", "set", "--no-cone"] + SPARSE)
        branch = git(["-C", s, "symbolic-ref", "--short", "HEAD"]).stdout.strip()
        git(["-C", s, "checkout", "--quiet"] + ([branch] if branch else []))
        if not has_values(s):
            git(["-C", s, "read-tree", "-mu", "HEAD"])
        res["head"] = git(["-C", s, "rev-parse", "HEAD"]).stdout.strip()
        res.update(scan_ci(s))
        res.update(scan_strings(s))
        if not res["exposure"]:
            res["status"] = "no-exposure"
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


def stratum(e):
    for i, (lo, hi) in enumerate(STRATA):
        if e >= lo and (hi is None or e < hi):
            return i
    return None


def grade(rows):
    """Pre-registered verdicts (PREREG.md) from per-repository rows. Integer comparisons only.

    rows: dicts with lint (bool), exposure (int >= 1) and errors (int)."""
    L = [r for r in rows if r["lint"]]
    O = [r for r in rows if not r["lint"]]
    eL, eO = sum(r["exposure"] for r in L), sum(r["exposure"] for r in O)
    dL, dO = sum(r["errors"] for r in L), sum(r["errors"] for r in O)
    if len(L) < GATE_L_REPOS or len(O) < GATE_O_REPOS or eL < GATE_L_EXPOSURE:
        return {p: "NOT TESTABLE (gate)" for p in ("P1", "P2", "P3")}, []
    n = len(rows)
    v = {"P1": "HELD" if 20 * len(L) >= n and 4 * len(L) <= n else "FAILED"}
    # dL/eL < dO/eO
    v["P2"] = "NOT TESTABLE" if dO == 0 else ("HELD" if dL * eO < dO * eL else "FAILED")
    strata = []
    for i in range(len(STRATA)):
        sl = [r for r in L if stratum(r["exposure"]) == i]
        so = [r for r in O if stratum(r["exposure"]) == i]
        kl = sum(1 for r in sl if r["errors"])
        ko = sum(1 for r in so if r["errors"])
        testable = len(sl) >= STRATUM_MIN and len(so) >= STRATUM_MIN and ko > 0
        # kl/len(sl) < ko/len(so)
        lower = testable and kl * len(so) < ko * len(sl)
        strata.append({"stratum": list(STRATA[i]), "L_repos": len(sl), "L_with_error": kl,
                       "O_repos": len(so), "O_with_error": ko, "testable": testable, "L_lower": lower})
    t = [s for s in strata if s["testable"]]
    if len(t) < 2:
        v["P3"] = "NOT TESTABLE"
    else:
        v["P3"] = "HELD" if sum(1 for s in t if s["L_lower"]) >= 2 else "FAILED"
    return v, strata


def aggregate(results):
    ok = [r for r in results if r.get("status") == "ok"]
    rows = [{"lint": r["lint"], "exposure": r["exposure"], "errors": r["errors"]} for r in ok]
    verdicts, strata = grade(rows)

    def block(rs):
        e = sum(r["exposure"] for r in rs)
        d = sum(r["errors"] for r in rs)
        return {"repos": len(rs), "exposure": e, "errors": d,
                "repos_with_error": sum(1 for r in rs if r["errors"]),
                "errors_per_10k": round(10000 * d / e, 3) if e else None}

    L = [r for r in ok if r["lint"]]
    O = [r for r in ok if not r["lint"]]
    return {
        "verdicts": verdicts,
        "population": block(ok), "L": block(L), "O": block(O), "strata": strata,
        "exploratory_O_split": {
            "check_or_build_no_lint": block([r for r in O if r["check_build"]]),
            "ci_without_either": block([r for r in O if r["ci_files"] and not r["check_build"]]),
            "no_ci_files": block([r for r in O if not r["ci_files"]]),
        },
        "exploratory_L_gradle_settings": dict(collections.Counter(
            s for r in L for s in r["gradle_lint_settings"])),
        "exploratory_ci_platforms": dict(collections.Counter(
            p for r in ok for p in sorted({platform(f) for f in r["ci_files"]}))),
    }


def platform(rel):
    """The CI file or folder a path came from (.github/workflows, .gitlab-ci.yml, ...)."""
    for d in CI_DIRS:
        if rel.startswith(d + "/"):
            return d
    return rel


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


ERROR_COLS = ["repo", "head", "lint", "res_dir", "locale_dir", "file", "key", "message"]


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
    if l10n_guard.__version__ != GUARD_VERSION:
        print("l10n_guard.py is %s, not %s; stopping" % (l10n_guard.__version__, GUARD_VERSION),
              file=sys.stderr)
        return 5
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
    print("lint_ci %s (l10n-guard %s): %d repositories" % (VERSION, l10n_guard.__version__, len(repos)),
          flush=True)

    tmp_root = tempfile.mkdtemp(prefix="lintci-")
    selftest = {}
    for u in ("https://gitlab.com/fdroid/fdroidclient", "https://github.com/TeamNewPipe/NewPipe"):
        r = process_repo(u, tmp_root)
        selftest[u] = {"status": r["status"], "exposure": r.get("exposure", 0),
                       "ci_files": len(r.get("ci_files", [])), "lint": r.get("lint")}
    print("selftest", json.dumps(selftest), flush=True)
    if not any(v["exposure"] for v in selftest.values()) or not any(v["ci_files"] for v in selftest.values()):
        print("selftest found no exposure or no CI files; clone method broken, stopping", file=sys.stderr)
        return 3

    deadline = time.time() + a.budget_minutes * 60
    results, skipped = [], []
    jl = open(os.path.join(a.out_dir, "repos.jsonl"), "w", encoding="utf-8")
    ef = open(os.path.join(a.out_dir, "java_format_errors.csv"), "w", encoding="utf-8", newline="")
    ew = csv.DictWriter(ef, fieldnames=ERROR_COLS)
    ew.writeheader()

    def work(u):
        if time.time() > deadline:
            return {"repo": u, "status": "not-started"}
        return process_repo(u, tmp_root)

    keep = ("repo", "status", "head", "error", "seconds", "lint", "check_build", "ci_files", "lint_lines",
            "check_lines", "gradle_lint_settings", "exposure", "errors", "pairs", "guard_failed")
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for n, r in enumerate(ex.map(work, repos), 1):
            if r["status"] == "not-started":
                skipped.append(r["repo"])
                continue
            results.append(r)
            jl.write(json.dumps({k: r.get(k) for k in keep}, ensure_ascii=False, sort_keys=True) + "\n")
            for row in r.get("rows", []):
                ew.writerow(dict(row, repo=r["repo"], head=r.get("head", ""), lint=int(bool(r.get("lint")))))
            if n % 100 == 0:
                jl.flush()
                ef.flush()
                print("%d/%d done, %.0f min" % (n, len(repos), (time.time() - started) / 60), flush=True)
    jl.close()
    ef.close()
    shutil.rmtree(tmp_root, ignore_errors=True)

    summary = aggregate(results)
    summary.update({
        "version": VERSION, "l10n_guard": l10n_guard.__version__, "repos_url": REPOS_URL,
        "repos_sha256": hashlib.sha256(raw).hexdigest(), "prereg_sha256": prereg_sha,
        "repos_listed": len(repos), "repos_not_started": len(skipped),
        "status_counts": dict(collections.Counter(r["status"] for r in results)),
        "guard_failed_pairs": sum(r.get("guard_failed", 0) for r in results),
        "selftest": selftest, "minutes": round((time.time() - started) / 60, 1),
    })
    with open(os.path.join(a.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps(summary["verdicts"]), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
