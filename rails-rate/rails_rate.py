#!/usr/bin/env python3
"""How often do the translations of open-source Rails applications lose a
%{name} interpolation, write it with a look-alike character (％{count}), or
add one the English doesn't pass?

Population: every application and engine pinned as a git submodule in Real
World Rails (github.com/eliotsykes/real-world-rails) at its last commit,
c5e6e6e1 (2024-07-21; the repository was archived in 2026). For each one,
the YAML files under config/locales/ at the pinned commit are loaded with
PyYAML, merged per locale as Ruby's I18n merges them, and every translated
string is compared with the English one by Ruby I18n's rules:

  - I18n fills %{name} and %<name>s only (\\w is ASCII in Ruby), and %% is
    a literal %;
  - a %{name} in a translation that the app doesn't pass raises
    I18n::MissingInterpolationArgument; Rails passes count for plurals;
  - the zero, one and two plural forms may leave a placeholder out.

The predictions were published before this ran: rails-rate/PREREG.md in
munimtechnologies/android-translation-crash-census.

  python rails_rate.py --out-dir /out/rails-rate --workers 6

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import csv
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import yaml

__version__ = "0.1.0"

RWR = "https://github.com/eliotsykes/real-world-rails"
RWR_COMMIT = "c5e6e6e1d9f74026ca3d7fad449998803dbba9af"
RWR_GITMODULES = ("https://raw.githubusercontent.com/eliotsykes/real-world-rails/%s/.gitmodules"
                  % RWR_COMMIT)
GIT_ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_ASKPASS="", SSH_ASKPASS="",
               GIT_LFS_SKIP_SMUDGE="1")
# Chinese, Japanese, Korean and Arabic-script languages: where every
# look-alike placeholder found so far, in nine formats, was written.
GROUP = ("zh", "ja", "ko", "ar", "fa", "ur", "ps", "ckb", "sd", "ug")
ENGLISH = ("en", "en-US", "en_US", "en-GB", "en_GB")
LOCALE_RE = re.compile(r"^[A-Za-z]{2,3}(?:[-_][A-Za-z0-9]{2,8})*$")
PLURAL_RE = re.compile(r"\.(zero|one|two|few|many|other)$")
# i18n's INTERPOLATION_PATTERN, without %% (removed first).
INTERP_RE = re.compile(r"%\{([\w|]+)\}|%<(\w+)>[^\d<>]*?\d*\.?\d*[bBdiouxXeEfgGcps]", re.ASCII)
LOOKALIKE_PERCENTS = "％٪﹪"
LOOKALIKE_BRACES = "｛｝"
KINDS = ("lookalike-percent", "lookalike-brace", "spaced", "ruby-hash", "no-percent",
         "other-syntax", "renamed", "dropped")
LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

REPO_FIELDS = ["path", "url", "commit", "fetched", "error", "yaml_files", "loaded", "english",
               "locales", "compared_locales", "collisions", "seconds"]
FILE_FIELDS = ["repo", "file", "loaded", "locales", "error"]
STAT_FIELDS = ["repo", "locale", "language", "group", "strings", "placeholder_strings",
               "error_strings", "lookalike_errors", "lookalike_error_strings",
               "lookalike_warnings", "missing_errors", "missing_warnings", "extra_warnings"]
ROW_FIELDS = ["repo", "commit", "locale", "key", "quantity", "level", "code", "kind", "name",
              "seen", "source", "translation"]


# ---------------------------------------------------------------- population

def git(args, cwd=None, timeout=300):
    return subprocess.run(["git"] + args, cwd=cwd, timeout=timeout, capture_output=True,
                          text=True, env=GIT_ENV)


def https_url(url):
    """git@github.com:owner/repo.git or https://github.com/owner/repo -> https form."""
    m = re.match(r"(?:git@github\.com:|https?://github\.com/)(.+?)(?:\.git)?/?$", url.strip())
    return "https://github.com/" + m.group(1) if m else url.strip()


def parse_gitmodules(text):
    """{path: https url} from a .gitmodules file."""
    out, path, url = {}, None, None
    for line in text.splitlines() + ["[submodule end]"]:
        line = line.strip()
        if line.startswith("["):
            if path and url:
                out[path] = https_url(url)
            path = url = None
        elif "=" in line:
            key, value = (s.strip() for s in line.split("=", 1))
            if key == "path":
                path = value
            elif key == "url":
                url = value
    return out


def parse_ls_tree(text):
    """{path: commit} for the submodule (gitlink) entries of git ls-tree -r."""
    out = {}
    for line in text.splitlines():
        meta, _, path = line.partition("\t")
        parts = meta.split()
        if len(parts) == 3 and parts[0] == "160000" and parts[1] == "commit":
            out[path] = parts[2]
    return out


def init_fetch(url, commit, dest, timeout):
    """A depth-1, blobless fetch of one commit into a new repository at dest."""
    os.makedirs(dest)
    for args in (["init", "-q"], ["remote", "add", "origin", url]):
        r = git(args, cwd=dest, timeout=60)
        if r.returncode:
            raise RuntimeError("git %s failed: %s" % (args[0], r.stderr.strip()[-200:]))
    r = git(["fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", commit], cwd=dest,
            timeout=timeout)
    if r.returncode:
        raise RuntimeError("fetch failed: %s" % r.stderr.strip()[-300:])


def population(work):
    """The submodules of Real World Rails at RWR_COMMIT: [{path, url, commit}]."""
    dest = os.path.join(work, "real-world-rails")
    init_fetch(RWR, RWR_COMMIT, dest, 600)
    r = git(["ls-tree", "-r", RWR_COMMIT], cwd=dest, timeout=300)
    if r.returncode:
        raise RuntimeError("ls-tree failed: %s" % r.stderr.strip()[-300:])
    pins = parse_ls_tree(r.stdout)
    req = urllib.request.Request(RWR_GITMODULES, headers={"User-Agent": "mv2-rails-rate"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        urls = parse_gitmodules(resp.read().decode("utf-8"))
    shutil.rmtree(dest, ignore_errors=True)
    subs = [{"path": p, "url": urls.get(p, ""), "commit": c} for p, c in sorted(pins.items())]
    return subs, len(urls)


def fetch_locales(url, commit, dest, timeout):
    """Checks out only config/locales/ of one pinned commit."""
    init_fetch(url, commit, dest, timeout)
    git(["config", "core.sparseCheckout", "true"], cwd=dest, timeout=30)
    info = os.path.join(dest, ".git", "info")
    os.makedirs(info, exist_ok=True)
    with open(os.path.join(info, "sparse-checkout"), "w") as f:
        f.write("/config/locales/\n")
    r = git(["read-tree", "-mu", commit], cwd=dest, timeout=timeout)
    # Older git refuses a sparse checkout that matches nothing: no config/locales/.
    if r.returncode and "leaves no entry" not in r.stderr:
        raise RuntimeError("checkout failed: %s" % r.stderr.strip()[-300:])


# ------------------------------------------------------------------- locales

def flatten(data, prefix=""):
    """Nested mappings to dotted keys; lists and scalars are values."""
    flat = {}
    if isinstance(data, dict):
        for k, v in data.items():
            flat.update(flatten(v, "%s.%s" % (prefix, k) if prefix else str(k)))
    else:
        flat[prefix] = data
    return flat


def load_locales(root, repo=""):
    """({locale: {key: value}}, file records, collisions): every YAML file
    under root/config/locales, each top-level locale key (en:, ja:) merged
    into its locale, later files over earlier ones."""
    base = os.path.join(root, "config", "locales")
    merged, files, collisions = {}, [], 0
    for dirpath, dirs, names in os.walk(base):
        dirs.sort()
        for name in sorted(names):
            if not name.endswith((".yml", ".yaml")):
                continue
            path = os.path.join(dirpath, name)
            record = {"repo": repo, "file": os.path.relpath(path, root).replace(os.sep, "/"),
                      "loaded": 0, "locales": "", "error": ""}
            files.append(record)
            try:
                with open(path, "rb") as f:
                    doc = yaml.load(f.read().decode("utf-8-sig"), Loader=LOADER)
            except Exception as exc:  # noqa: BLE001 - every failure is a result here
                record["error"] = ("%s: %s" % (type(exc).__name__, exc)).replace("\n", " ")[:300]
                continue
            record["loaded"] = 1
            roots = [k for k, v in doc.items() if isinstance(k, str) and LOCALE_RE.match(k)
                     and isinstance(v, dict)] if isinstance(doc, dict) else []
            record["locales"] = " ".join(roots)
            for locale in roots:
                bucket = merged.setdefault(locale, {})
                for key, value in flatten(doc[locale]).items():
                    if key in bucket and bucket[key] != value:
                        collisions += 1
                    bucket[key] = value
    return merged, files, collisions


def language(locale):
    return re.split(r"[-_]", locale)[0].lower()


def in_group(locale):
    return language(locale) in GROUP


# --------------------------------------------------------------------- rules

def names(text):
    """The %{name} and %<name>s placeholders Ruby's I18n fills in text."""
    return {a or b for a, b in INTERP_RE.findall(text.replace("%%", ""))}


def lookalike(name, target):
    """(what target wrote, code) when target writes %{name} with a look-alike
    percent sign or brace (％{count}, ٪ {name}, %｛name｝, ％<n>d), else None."""
    word = re.escape(name)
    for m in re.finditer("[%%%s] ?(?:[{｛] ?%s ?[}｝]|<%s>)" % (LOOKALIKE_PERCENTS, word, word),
                         target):
        seen = m.group(0)
        if seen[0] in LOOKALIKE_PERCENTS:
            return seen, "lookalike-percent"
        if any(c in LOOKALIKE_BRACES for c in seen):
            return seen, "lookalike-brace"
    return None


def kind(name, source, target):
    """(kind, what target wrote) for a placeholder missing from target."""
    found = lookalike(name, target)
    if found:
        return found[1], found[0]
    word = re.escape(name)
    tests = (("spaced", r"%(?:\s+\{\s*" + word + r"\s*\}|\{(?:\s+" + word + r"\s*|" + word
              + r"\s+)\})"),
             ("ruby-hash", r"#\{\s*" + word + r"\s*\}"),
             ("other-syntax", r"\$\{\s*" + word + r"\s*\}|%\(" + word + r"\)|%" + word + "%"),
             ("no-percent", r"(?<![%#$\w])\{\{?\s*" + word + r"\s*\}\}?"))
    for code, pattern in tests:
        m = re.search(pattern, target)
        if m:
            return code, m.group(0)
    others = sorted(set(re.findall(r"%\{([^{}]*)\}", target)) - names(source))
    if others:
        return "renamed", "%%{%s}" % others[0]
    return "dropped", ""


def check_pair(source, target, quantity=None):
    """Problems of one translated string, by Ruby I18n's rules: a missing
    placeholder is an error (a warning in a zero, one or two plural form), a
    look-alike one is an error unless the ASCII one is there too, and an
    extra one (other than count in a plural form) is a warning, because
    I18n raises MissingInterpolationArgument unless the app passes it."""
    if not target.strip():
        return []
    want, have, problems = names(source), names(target), []
    for name in sorted(want - have):
        code, seen = kind(name, source, target)
        if code.startswith("lookalike"):
            problems.append({"level": "error", "code": code, "kind": code, "name": name,
                             "seen": seen})
        else:
            problems.append({"level": "warning" if quantity in ("zero", "one", "two") else "error",
                             "code": "placeholder-missing", "kind": code, "name": name,
                             "seen": seen})
    for name in sorted(want & have):
        found = lookalike(name, target)
        if found:
            problems.append({"level": "warning", "code": found[1], "kind": found[1],
                             "name": name, "seen": found[0]})
    for name in sorted(have - want - ({"count"} if quantity else set())):
        problems.append({"level": "warning", "code": "placeholder-extra", "kind": "",
                         "name": name, "seen": "%%{%s}" % name})
    return problems


def pairs(src, tgt):
    """[(key, source, translation, plural form or None)]: every key both have
    as text, and every plural form the translation has and the source lacks
    (few, many), against the source's other form."""
    out = []
    for key in sorted(src):
        if key in tgt and isinstance(src[key], str) and isinstance(tgt[key], str):
            form = PLURAL_RE.search(key)
            out.append((key, src[key], tgt[key], form.group(1) if form else None))
    for key in sorted(set(tgt) - set(src)):
        form = PLURAL_RE.search(key)
        other = src.get(PLURAL_RE.sub("", key) + ".other") if form else None
        if isinstance(other, str) and isinstance(tgt[key], str):
            out.append((key, other, tgt[key], form.group(1)))
    return out


def locale_stats(repo, commit, locale, src, tgt):
    """(stats row, problem rows) for one locale of one repository."""
    stat = dict.fromkeys(STAT_FIELDS, 0)
    stat.update(repo=repo, locale=locale, language=language(locale), group=int(in_group(locale)))
    rows = []
    for key, source, target, quantity in pairs(src, tgt):
        stat["strings"] += 1
        if names(source):
            stat["placeholder_strings"] += 1
        problems = check_pair(source, target, quantity)
        if any(p["level"] == "error" for p in problems):
            stat["error_strings"] += 1
        looks = [p for p in problems if p["code"].startswith("lookalike") and p["level"] == "error"]
        if looks:
            stat["lookalike_error_strings"] += 1
        for p in problems:
            if p["code"].startswith("lookalike"):
                stat["lookalike_errors" if p["level"] == "error" else "lookalike_warnings"] += 1
            elif p["code"] == "placeholder-missing":
                stat["missing_errors" if p["level"] == "error" else "missing_warnings"] += 1
            else:
                stat["extra_warnings"] += 1
            rows.append(dict(p, repo=repo, commit=commit, locale=locale, key=key,
                             quantity=quantity or "", source=source[:300],
                             translation=target[:300]))
    return stat, rows


# --------------------------------------------------------------- statistics

def _log_comb(n, k):
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def fisher_greater(a, b, c, d):
    """One-sided Fisher exact p that the first row's share (a of a+b) is
    greater than the second's (c of c+d)."""
    n, k, total = a + b, a + c, a + b + c + d
    if total == 0 or k == 0:
        return 1.0
    p = 0.0
    for x in range(a, min(k, n) + 1):
        p += math.exp(_log_comb(k, x) + _log_comb(total - k, n - x) - _log_comb(total, n))
    return min(1.0, p)


# ---------------------------------------------------------------------- run

def analyse(sub, dest, timeout):
    """(repo record, file records, stats rows, problem rows) for one submodule."""
    start = time.time()
    record = dict.fromkeys(REPO_FIELDS, "")
    record.update(sub, fetched=0, yaml_files=0, loaded=0, locales=0, compared_locales=0,
                  collisions=0)
    files, stats, rows = [], [], []
    try:
        if not sub["url"]:
            raise RuntimeError("no url in .gitmodules")
        fetch_locales(sub["url"], sub["commit"], dest, timeout)
        record["fetched"] = 1
        merged, files, collisions = load_locales(dest, sub["path"])
        record.update(yaml_files=len(files), loaded=sum(f["loaded"] for f in files),
                      locales=len(merged), collisions=collisions)
        english = next((e for e in ENGLISH if e in merged), "")
        record["english"] = english
        if english:
            src = merged[english]
            for locale in sorted(merged):
                if language(locale) == "en":
                    continue
                stat, found = locale_stats(sub["path"], sub["commit"], locale, src,
                                           merged[locale])
                if stat["strings"]:
                    stats.append(stat)
                    rows.extend(found)
            record["compared_locales"] = len(stats)
    except Exception as exc:  # noqa: BLE001 - every failure is a result here
        record["error"] = ("%s: %s" % (type(exc).__name__, exc)).replace("\n", " ")[:300]
    finally:
        shutil.rmtree(dest, ignore_errors=True)
    record["seconds"] = round(time.time() - start, 1)
    return record, files, stats, rows


def predictions(repos, files, stats, rows):
    """[(id, text, held, value)] for P1-P7 of rails-rate/PREREG.md."""
    compared = [s for s in stats if s["strings"]]
    with_look = [s for s in compared if s["lookalike_errors"]]
    look_rows = [r for r in rows if r["code"].startswith("lookalike") and r["level"] == "error"]
    outside = sorted({"%s %s" % (r["repo"], r["locale"]) for r in look_rows
                      if not in_group(r["locale"])})
    g = [s for s in compared if s["group"]]
    o = [s for s in compared if not s["group"]]
    ga, gn = sum(s["lookalike_error_strings"] for s in g), sum(s["placeholder_strings"] for s in g)
    oa, on = sum(s["lookalike_error_strings"] for s in o), sum(s["placeholder_strings"] for s in o)
    p3 = fisher_greater(ga, gn - ga, oa, on - oa) if gn and on else 1.0
    look_errors = sum(s["lookalike_errors"] for s in compared)
    missing = sum(s["missing_errors"] for s in compared)
    yaml_files = len(files)
    loaded = sum(f["loaded"] for f in files)
    fetched = sum(r["fetched"] for r in repos)
    repos_compared = len({s["repo"] for s in compared})
    kinds = {k: 0 for k in KINDS}
    for r in rows:
        if r["level"] == "error" and r["kind"] in kinds:
            kinds[r["kind"]] += 1
    others = max(v for k, v in kinds.items() if k != "dropped")
    return [
        ("P1", "fewer than 2% of compared (repository, locale) pairs have a look-alike "
               "placeholder error",
         bool(compared) and len(with_look) < 0.02 * len(compared),
         "%d of %d (%.2f%%)" % (len(with_look), len(compared),
                               100.0 * len(with_look) / len(compared) if compared else 0)),
        ("P2", "every look-alike placeholder error is in a Chinese, Japanese, Korean or "
               "Arabic-script locale",
         not outside, "%d errors; outside: %s" % (len(look_rows), ", ".join(outside) or "none")),
        ("P3", "the share of placeholder strings with a look-alike error is higher in those "
               "locales than in all others",
         bool(gn) and bool(on) and ga / gn > oa / on,
         "%d of %d vs %d of %d; one-sided Fisher p %.3g" % (ga, gn, oa, on, p3)),
        ("P4", "missing-placeholder errors outnumber look-alike errors at least 10 to 1",
         missing >= 10 * max(1, look_errors), "%d vs %d" % (missing, look_errors)),
        ("P5", "at least 95% of the YAML files under config/locales load with PyYAML",
         bool(yaml_files) and loaded >= 0.95 * yaml_files,
         "%d of %d (%.1f%%)" % (loaded, yaml_files,
                               100.0 * loaded / yaml_files if yaml_files else 0)),
        ("P6", "at least 180 of the pinned commits fetch, and at least 40 repositories have a "
               "translation compared with English",
         fetched >= 180 and repos_compared >= 40,
         "%d of %d fetched; %d repositories compared" % (fetched, len(repos), repos_compared)),
        ("P7", "'dropped' is the most common kind of placeholder error",
         kinds["dropped"] > others, ", ".join("%s %d" % kv for kv in kinds.items())),
    ]


def write_csv(path, fields, items):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(items)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="/out/rails-rate")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--timeout", type=int, default=600, help="seconds per git step")
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    print("rails_rate %s, PyYAML %s (%s), git %s" % (
        __version__, yaml.__version__, LOADER.__name__,
        git(["--version"], timeout=30).stdout.strip()))
    work = tempfile.mkdtemp(prefix="rails-rate-")
    started = time.time()
    subs, gitmodules = population(work)
    print("Real World Rails %s: %d submodule commits, %d .gitmodules entries"
          % (RWR_COMMIT[:12], len(subs), gitmodules))
    write_csv(os.path.join(args.out_dir, "population.csv"), ["path", "url", "commit"], subs)

    def one(item):
        i, sub = item
        return analyse(sub, os.path.join(work, "r%03d" % i), args.timeout)

    repos, files, stats, rows = [], [], [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for record, f, s, r in pool.map(one, enumerate(subs)):
            repos.append(record)
            files.extend(f)
            stats.extend(s)
            rows.extend(r)
            print("%(path)s %(commit).10s: fetched %(fetched)s, yaml %(yaml_files)s, loaded "
                  "%(loaded)s, locales %(locales)s, compared %(compared_locales)s, english "
                  "'%(english)s', %(seconds)ss %(error)s" % record, flush=True)

    for f in files:
        if f["error"]:
            print("load error: %s %s: %s" % (f["repo"], f["file"], f["error"][:160]))
    for r in rows:
        if r["code"].startswith("lookalike"):
            print("%(level)s %(code)s %(repo)s %(locale)s [%(key)s] %(seen)s" % r)
    checks = predictions(repos, files, stats, rows)
    for name, text, held, value in checks:
        print("%s %s: %s (%s)" % (name, "HELD" if held else "FAILED", text, value))

    write_csv(os.path.join(args.out_dir, "repos.csv"), REPO_FIELDS, repos)
    write_csv(os.path.join(args.out_dir, "files.csv"), FILE_FIELDS, files)
    write_csv(os.path.join(args.out_dir, "locales.csv"), STAT_FIELDS, stats)
    write_csv(os.path.join(args.out_dir, "problems.csv"), ROW_FIELDS, rows)
    totals = {k: sum(s[k] for s in stats) for k in STAT_FIELDS[4:]}
    by_kind = {}
    for r in rows:
        by_kind.setdefault("%s %s %s" % (r["level"], r["code"], r["kind"]), 0)
        by_kind["%s %s %s" % (r["level"], r["code"], r["kind"])] += 1
    with open(os.path.join(args.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump({"version": __version__, "real_world_rails": RWR_COMMIT,
                   "submodules": len(subs), "fetched": sum(r["fetched"] for r in repos),
                   "yaml_files": len(files), "loaded": sum(x["loaded"] for x in files),
                   "repositories_compared": len({s["repo"] for s in stats}),
                   "locales_compared": len(stats), "totals": totals, "by_kind": by_kind,
                   "minutes": round((time.time() - started) / 60, 1),
                   "predictions": [{"id": n, "text": t, "held": h, "value": v}
                                   for n, t, h, v in checks]},
                  f, ensure_ascii=False, indent=1)
    print("totals: %s" % json.dumps(totals))
    print("by kind: %s" % json.dumps(by_kind, ensure_ascii=False))
    print("%.1f minutes" % ((time.time() - started) / 60))
    shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
