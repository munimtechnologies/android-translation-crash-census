#!/usr/bin/env python3
"""Translation-crash census of open-source Android apps.

For every app in the F-Droid index whose source is in a public git repo,
fetches only the res/values*/ XML files (depth 1, blobless, sparse), pairs
each translated string with its source string, and for every string the app
would pass to String.format checks the translation two ways: l10n-guard's
static java-format check, and the real java.util.Formatter (FormatCheck.java).
A translation that throws while its source formats fine crashes the app for
everyone using that language.

  python census/census.py --data-dir /data --out-dir /out
  python census/census.py --local path/to/app --out-dir out   # one tree, no git

Writes apps.jsonl, findings.csv, summary.json and report.md to --out-dir.

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import base64
import collections
import concurrent.futures
import csv
import datetime
import glob
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

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ship", "l10n-guard"))
import l10n_guard as g  # noqa: E402

__version__ = "0.2.0"

INDEX_URLS = ["https://f-droid.org/repo/index-v2.json", "https://f-droid.org/repo/index-v1.json"]
USER_AGENT = "mv2-translation-crash-census/%s (Munim, Inc.; munimversion2@gmail.com)" % __version__
SPARSE_PATTERN = "**/res/values*/*.xml"
# values-fr, values-pt-rBR, values-b+sr+Latn. "car" is a UI mode, not a language.
LOCALE_DIR_RE = re.compile(r"^values-([a-z]{2,3}(?:-r[A-Z]{2})?|b\+[A-Za-z]{2,3}(?:\+[A-Za-z0-9]+)*)$")
NOT_LOCALES = {"car"}
JVM_TYPES = {"any": "S", "int": "I", "float": "D", "char": "C", "date": "L"}
GIT_ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_ASKPASS="", SSH_ASKPASS="",
               GIT_LFS_SKIP_SMUDGE="1")
FINDING_FIELDS = ["verdict", "exception", "use", "static", "static_detail", "locale", "key",
                  "source_key", "source", "translation", "file", "link", "repo", "commit",
                  "packages", "app"]
PLURAL_RULE = ("getQuantityString passes every quantity the same arguments, so each translated "
               "plural form is checked against the source form that reads the most of them")
# Code is fetched only for repositories with a flagged translation.
CODE_PATTERNS = ["**/*.kt", "**/*.java"]
# Calls that format the string when given arguments beyond the id (plurals:
# beyond the id and the count).
FORMAT_CALLS = {"getString", "stringResource", "getQuantityString", "pluralStringResource"}
USES = ("formatted", "referenced", "unreferenced", "unknown")
_CALL_NAME_RE = re.compile(r"([A-Za-z_]\w*)\s*$")
# String.format(getString(id), n), String.format(Locale.US, ctx.getString(id), n)
_FORMAT_WRAP_RE = re.compile(r"format\s*\(\s*(?:[\w.]*Locale[\w.()]*\s*,\s*)?[\w.?!]*$")
# Known answers the JVM must give before its verdicts are trusted.
SELF_CHECK = [("I", "%1$d%% done", "%1$d % terminé", "crash"),
              ("S", "Hello %s", "Hallo %d", "crash-if-text"),
              ("I", "%d files", "%d fichiers", "ok"),
              ("S,S", "%1$s of %2$s", "%1$s de %3$s", "crash"),
              ("S", "Saved to %s", "Téléchargé à 50% dans %s", "crash")]


def log(message):
    print("[%s] %s" % (datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S"),
                       message), flush=True)


# ------------------------------------------------------------------- F-Droid

def _text(value):
    """A localized F-Droid field ({"en-US": "..."}) or a plain string as text."""
    if isinstance(value, dict):
        if not value:
            return ""
        return str(value.get("en-US") or next(iter(value.values())) or "")
    return str(value or "")


def parse_index(data):
    """Apps from an F-Droid index-v1 ("apps" list) or index-v2 ("packages"
    object): package, name, source (the sourceCode link), updated (ms)."""
    apps = []
    if isinstance(data.get("apps"), list):
        for app in data["apps"]:
            localized = (app.get("localized") or {}).get("en-US") or {}
            apps.append({"package": app.get("packageName") or "",
                         "name": _text(app.get("name") or localized.get("name")),
                         "source": app.get("sourceCode") or "",
                         "updated": app.get("lastUpdated") or 0})
    else:
        for package, entry in sorted((data.get("packages") or {}).items()):
            meta = (entry or {}).get("metadata") or {}
            apps.append({"package": package, "name": _text(meta.get("name")),
                         "source": meta.get("sourceCode") or "",
                         "updated": meta.get("lastUpdated") or 0})
    return apps


def load_index(data_dir):
    """F-Droid's index, downloaded once into data_dir. Returns (apps, url)."""
    for url in INDEX_URLS:
        path = os.path.join(data_dir, os.path.basename(url))
        if not os.path.isfile(path):
            try:
                log("GET %s" % url)
                request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(request, timeout=600) as r, open(path + ".part", "wb") as f:
                    shutil.copyfileobj(r, f)
                os.replace(path + ".part", path)
            except Exception as exc:
                log("index download failed: %s" % exc)
                continue
        try:
            with open(path, encoding="utf-8") as f:
                return parse_index(json.load(f)), url
        except ValueError as exc:
            log("bad index %s: %s" % (path, exc))
            os.remove(path)
    raise SystemExit("could not load an F-Droid index")


def repo_of(source):
    """(clone URL, web URL, host) for an app's sourceCode link, or None."""
    m = re.match(r"^https?://([^/\s]+)/([^?#\s]+)", (source or "").strip())
    if not m:
        return None
    host = m.group(1).lower()
    if host.startswith("www."):
        host = host[4:]
    path = re.split(r"/-/|/tree/|/blob/|/src/|/commits?/|/releases?(?:/|$)|/wiki(?:/|$)",
                    m.group(2).strip("/"))[0].strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = path.split("/")
    if host in ("github.com", "codeberg.org"):
        if len(parts) < 2:
            return None
        path = "/".join(parts[:2])
    if not path:
        return None
    web = "https://%s/%s" % (host, path)
    return web + ".git", web, host


def blob_url(web, host, sha, path):
    """A link to one file at one commit, for the hosts whose URL scheme is known."""
    if not sha:
        return ""
    if host == "github.com":
        return "%s/blob/%s/%s" % (web, sha, path)
    if host == "codeberg.org":
        return "%s/src/commit/%s/%s" % (web, sha, path)
    if "gitlab" in host or host == "framagit.org":
        return "%s/-/blob/%s/%s" % (web, sha, path)
    return ""


# ---------------------------------------------------------------------- git

def git(args, cwd=None, timeout=120):
    return subprocess.run(["git"] + args, cwd=cwd, timeout=timeout, capture_output=True,
                          text=True, env=GIT_ENV)


def fetch(clone, dest, timeout):
    """Clones only the latest commit's tree, then checks out just the values
    folders. Returns the commit sha."""
    start = time.time()
    r = git(["clone", "--quiet", "--depth", "1", "--filter=blob:none", "--no-checkout",
             "--single-branch", clone, dest], timeout=timeout)
    if r.returncode:
        raise RuntimeError("clone failed: %s" % r.stderr.strip()[-300:])
    left = max(15, timeout - (time.time() - start))
    git(["config", "core.sparseCheckout", "true"], cwd=dest, timeout=30)
    info = os.path.join(dest, ".git", "info")
    os.makedirs(info, exist_ok=True)
    with open(os.path.join(info, "sparse-checkout"), "w") as f:
        f.write(SPARSE_PATTERN + "\n")
    r = git(["read-tree", "-mu", "HEAD"], cwd=dest, timeout=left)
    if r.returncode:
        raise RuntimeError("checkout failed: %s" % r.stderr.strip()[-300:])
    return git(["rev-parse", "HEAD"], cwd=dest, timeout=30).stdout.strip()


def fetch_code(dest, timeout):
    """Adds the repository's Kotlin and Java files to the sparse checkout."""
    with open(os.path.join(dest, ".git", "info", "sparse-checkout"), "a") as f:
        f.write("".join(p + "\n" for p in CODE_PATTERNS))
    r = git(["read-tree", "-mu", "HEAD"], cwd=dest, timeout=timeout)
    if r.returncode:
        raise RuntimeError("code checkout failed: %s" % r.stderr.strip()[-300:])


# --------------------------------------------------------------------- code

def _enclosing_call(text, start, end):
    """(name, name start, close paren, commas after the match) of the call
    whose argument list holds text[start:end], or None."""
    depth, i = 0, start - 1
    while i >= 0 and start - i < 400:
        c = text[i]
        if c in ")]}":
            depth += 1
        elif c in "([{":
            if depth == 0:
                break
            depth -= 1
        i -= 1
    else:
        return None
    if text[i] != "(":
        return None
    name = _CALL_NAME_RE.search(text, max(0, i - 80), i)
    depth, commas, j = 0, 0, end
    while j < len(text) and j - end < 400:
        c = text[j]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            if depth == 0:
                break
            depth -= 1
        elif c == "," and depth == 0:
            commas += 1
        j += 1
    else:
        return None
    if not name:
        return "", i, j, commas
    return name.group(1), name.start(1), j, commas


def _formats(text, start, end, kind):
    """True if the reference at text[start:end] is formatted with arguments."""
    call = _enclosing_call(text, start, end)
    if not call:
        return False
    name, name_at, close, commas = call
    if name in FORMAT_CALLS and commas >= (2 if kind == "plurals" else 1):
        return True
    if name in ("getString", "stringResource") and not commas:
        if re.match(r"\s*\.format\s*\(", text[close + 1:close + 40]):
            return True
        return bool(_FORMAT_WRAP_RE.search(text, max(0, name_at - 120), name_at))
    return False


def code_uses(root, names):
    """For each (kind, name), kind "string" or "plurals": "formatted" if some
    Kotlin or Java call passes it format arguments, "referenced" if the code
    names it only in other ways (setText, Toast, getText...), "unreferenced"
    if no .kt or .java file names it."""
    uses = {n: "unreferenced" for n in names}
    if not names:
        return uses
    # aapt turns name="a.b" into R.string.a_b.
    fields = {(kind, n.replace(".", "_")): (kind, n) for kind, n in names}
    pattern = re.compile(r"\b(?:\w*R|Res)\.(string|plurals)\.(%s)\b"
                         % "|".join(sorted(re.escape(n) for _, n in fields)))
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in files:
            if not name.endswith((".kt", ".java")):
                continue
            try:
                with open(os.path.join(dirpath, name), encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            for m in pattern.finditer(text):
                key = fields.get((m.group(1), m.group(2)))
                if uses.get(key, "formatted") == "formatted":
                    continue
                uses[key] = "formatted" if _formats(text, m.start(), m.end(), key[0]) else "referenced"
    return uses


def _resource(key):
    """("plurals", name) for name[quantity], else ("string", key)."""
    q = g._QUANTITY_KEY_RE.match(key)
    return ("plurals", q.group(1)) if q else ("string", key)


# --------------------------------------------------------------------- scan

def read_resources(folder):
    """{key: (raw text, file name)} merged over a values folder's XML files,
    the names marked formatted="false", and the count of unreadable files."""
    strings, unformatted, bad = {}, set(), 0
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if not name.endswith(".xml") or not os.path.isfile(path):
            continue
        try:
            text = g._read(path)
            found = g.parse_android(text)
            unformatted |= g.android_unformatted(text)
        except (ValueError, ET.ParseError, OSError):
            bad += 1
            continue
        for key, value in found.items():
            strings[key] = (value, name)
    return strings, unformatted, bad


def jvm_types(specs):
    """FormatCheck's argument letters for a source's java_format specs."""
    kinds = {}
    for n, kind in specs:
        if kinds.get(n, "any") == "any":
            kinds[n] = kind
    return ",".join(JVM_TYPES[kinds.get(i, "any")] for i in range(1, max(kinds) + 1))


def scan_tree(root):
    """Every translation, under every res/ folder in root, of a string the
    app formats. Returns (pairs, stats)."""
    pairs = []
    stats = collections.Counter()
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        if os.path.basename(dirpath) != "res" or "values" not in dirnames:
            continue
        src, unformatted, bad = read_resources(os.path.join(dirpath, "values"))
        stats["bad_xml"] += bad
        if not src:
            continue
        stats["res_dirs"] += 1
        src_text = {k: v[0] for k, v in src.items()}
        res = os.path.relpath(dirpath, root).replace(os.sep, "/")
        for sub in dirnames:
            m = LOCALE_DIR_RE.match(sub)
            if not m or m.group(1) in NOT_LOCALES:
                continue
            tgt, _, bad = read_resources(os.path.join(dirpath, sub))
            stats["bad_xml"] += bad
            if tgt:
                stats["locales"] += 1
            for key in sorted(tgt):
                if g._ARRAY_KEY_RE.search(key):
                    continue
                q = g._QUANTITY_KEY_RE.match(key)
                base = q.group(1) if q else key
                if key not in src and not (q and base + "[other]" in src):
                    continue
                if base in unformatted:
                    continue
                if q:
                    raw = g._plural_format_source(src_text, base)
                    source_key = [k for k in ("%s[%s]" % (base, x) for x in g._QUANTITIES)
                                  if src_text.get(k) == raw][0]
                else:
                    raw, source_key = src_text[key], key
                source = g._android_text(raw)
                specs = g.java_formatted(source)
                if not specs:
                    continue
                target = g._android_text(tgt[key][0])
                if not target.strip():
                    continue
                stats["pairs"] += 1
                static, detail = "ok", ""
                for p in g.check_java_format(source, target):
                    static, detail = ("crash" if p["level"] == g.ERROR else "maybe"), p["message"]
                    if static == "crash":
                        break
                pairs.append({"res": res, "locale": m.group(1), "key": key,
                              "source_key": source_key,
                              "file": "%s/%s" % (sub, tgt[key][1]), "source": source,
                              "target": target, "types": jvm_types(specs),
                              "static": static, "detail": detail})
    return pairs, stats


# ---------------------------------------------------------------------- JVM

def find_tool(name, data_dir):
    found = shutil.which(name)
    if found:
        return found
    hits = sorted(glob.glob(os.path.join(data_dir, "jdk", "*", "bin", name)))
    return hits[-1] if hits else None


def _b64(text):
    # A lone surrogate can't be UTF-8; "?" doesn't change how Formatter parses.
    return base64.b64encode(text.encode("utf-8", "replace")).decode("ascii")


class Jvm:
    """A running FormatCheck: real java.util.Formatter verdicts, line by line."""

    def __init__(self, java, classdir):
        self.proc = subprocess.Popen([java, "-cp", classdir, "FormatCheck"],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     text=True, encoding="utf-8")
        version = subprocess.run([java, "-version"], capture_output=True, text=True)
        self.version = (version.stderr or version.stdout).strip().splitlines()[0]

    @classmethod
    def start(cls, data_dir, tmp):
        javac = find_tool("javac", data_dir)
        if not javac:
            log("no javac: static check only")
            return None
        java = os.path.join(os.path.dirname(javac), "java")
        if not os.path.isfile(java):
            java = shutil.which("java")
        classdir = os.path.join(tmp, "classes")
        os.makedirs(classdir, exist_ok=True)
        r = subprocess.run([javac, "-d", classdir, os.path.join(HERE, "FormatCheck.java")],
                           capture_output=True, text=True)
        if r.returncode:
            log("javac failed: %s" % r.stderr.strip()[-500:])
            return None
        return cls(java, classdir)

    def check(self, rows):
        """rows: (types, source, target). Returns [sourceA, targetA, sourceB, targetB] each."""
        results = []
        for start in range(0, len(rows), 200):
            chunk = rows[start:start + 200]
            self.proc.stdin.write("".join("%d\t%s\t%s\t%s\n" % (i, types, _b64(s), _b64(t))
                                          for i, (types, s, t) in enumerate(chunk)))
            self.proc.stdin.flush()
            for i in range(len(chunk)):
                parts = self.proc.stdout.readline().rstrip("\n").split("\t")
                if len(parts) != 5 or parts[0] != str(i):
                    raise RuntimeError("FormatCheck stopped or fell out of step")
                results.append(parts[1:])
        return results

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=30)
        except Exception:
            self.proc.kill()


def verdict(result):
    """(verdict, exception) from FormatCheck's four answers. crash: the
    translation throws whatever the app passes for %s; crash-if-text: only
    when it passes text; source-fails: the source itself throws, so the pair
    tells nothing."""
    if result is None:
        return "no-jvm", ""
    src_a, tgt_a, src_b, tgt_b = result
    if src_a != "OK" or src_b != "OK":
        return "source-fails", src_a if src_a != "OK" else src_b
    if tgt_a != "OK" and tgt_b != "OK":
        return "crash", tgt_a
    if tgt_a != "OK":
        return "crash-if-text", tgt_a
    return "ok", ""


# --------------------------------------------------------------------- main

def process_repo(repo, timeout, tmp_root):
    record = {"packages": repo["packages"], "names": repo["names"], "repo": repo["web"],
              "updated": repo["updated"], "status": "ok", "sha": ""}
    start = time.time()
    pairs = []
    dest = None
    try:
        if repo.get("local"):
            root = repo["local"]
        else:
            dest = tempfile.mkdtemp(prefix="repo-", dir=tmp_root)
            root = os.path.join(dest, "git")
            record["sha"] = fetch(repo["clone"], root, timeout)
        pairs, stats = scan_tree(root)
        record.update(stats)
        if not stats.get("res_dirs"):
            record["status"] = "no-android-strings"
        flagged = {_resource(p["key"]) for p in pairs if p["static"] != "ok"}
        uses = {}
        if flagged:
            try:
                if dest:
                    fetch_code(root, timeout)
                uses = code_uses(root, flagged)
            except Exception as exc:  # keep the string verdicts; use stays unknown
                record["code_error"] = str(exc)[-300:]
        for p in pairs:
            p["use"] = uses.get(_resource(p["key"]), "unknown")
    except subprocess.TimeoutExpired:
        record["status"] = "timeout"
    except Exception as exc:
        record["status"] = "error"
        record["error"] = str(exc)[-300:]
    finally:
        if dest:
            shutil.rmtree(dest, ignore_errors=True)
    record["seconds"] = round(time.time() - start, 1)
    return record, pairs


class Census:
    def __init__(self, out_dir):
        self.out_dir = out_dir
        self.apps = open(os.path.join(out_dir, "apps.jsonl"), "w", encoding="utf-8")
        self.findings = []
        self.status = collections.Counter()
        self.verdicts = collections.Counter()
        self.agreement = collections.Counter()
        self.exceptions = collections.Counter()
        self.locales = collections.Counter()
        self.repos_with = collections.Counter()
        self.crash_repos = []
        self.crash_uses = collections.Counter()
        self.pairs = 0

    def add(self, repo, record, pairs, jvm):
        results = [None] * len(pairs)
        if pairs and jvm is not None:
            results = jvm.check([(p["types"], p["source"], p["target"]) for p in pairs])
        counts = collections.Counter()
        for p, result in zip(pairs, results):
            jv, exception = verdict(result)
            counts[jv] += 1
            self.verdicts[jv] += 1
            self.agreement["%s/%s" % (p["static"], jv)] += 1
            if jv == "crash":
                self.exceptions[exception] += 1
                self.locales[p["locale"]] += 1
                self.crash_uses[p["use"]] += 1
                if p["use"] == "formatted":
                    counts["crash-formatted"] += 1
            if jv in ("crash", "crash-if-text") or (jv == "no-jvm" and p["static"] != "ok"):
                path = "%s/%s" % (p["res"], p["file"]) if p["res"] != "." else p["file"]
                self.findings.append({
                    "verdict": jv, "exception": exception, "use": p["use"], "static": p["static"],
                    "static_detail": p["detail"], "locale": p["locale"], "key": p["key"],
                    "source_key": p["source_key"], "source": p["source"],
                    "translation": p["target"], "file": path,
                    "link": blob_url(repo["web"], repo["host"], record["sha"], path),
                    "repo": repo["web"], "commit": record["sha"],
                    "packages": " ".join(repo["packages"]), "app": "; ".join(repo["names"])})
        record["verdicts"] = dict(counts)
        self.pairs += len(pairs)
        self.status[record["status"]] += 1
        if record.get("res_dirs"):
            self.repos_with["android_strings"] += 1
        if pairs:
            self.repos_with["formatted_translations"] += 1
        if counts["crash"]:
            self.crash_repos.append((counts["crash"], repo["web"], "; ".join(repo["names"]),
                                     repo["updated"], counts["crash-formatted"]))
        self.apps.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.apps.flush()

    def write(self, meta):
        with open(os.path.join(self.out_dir, "findings.csv"), "w", encoding="utf-8",
                  errors="replace", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FINDING_FIELDS)
            writer.writeheader()
            for row in sorted(self.findings, key=lambda r: (r["repo"], r["locale"], r["key"])):
                writer.writerow(row)
        a = self.agreement
        static_crash = sum(v for k, v in a.items() if k.startswith("crash/")
                           and not k.endswith(("/source-fails", "/no-jvm")))
        jvm_crash = sum(v for k, v in a.items() if k.endswith("/crash"))
        year_ago = (time.time() - 365 * 86400) * 1000
        summary = dict(meta)
        summary.update({
            "repos_by_status": dict(self.status),
            "repos_with_android_strings": self.repos_with["android_strings"],
            "repos_with_formatted_translations": self.repos_with["formatted_translations"],
            "formatted_translation_pairs": self.pairs,
            "verdicts": dict(self.verdicts),
            "repos_with_crash": len(self.crash_repos),
            "repos_with_crash_updated_within_365_days":
                sum(1 for c in self.crash_repos if (c[3] or 0) >= year_ago),
            "crash_by_code_use": {u: self.crash_uses[u] for u in USES},
            "repos_with_formatted_crash": sum(1 for c in self.crash_repos if c[4]),
            "crash_exceptions": dict(self.exceptions.most_common()),
            "crash_locales_top": dict(self.locales.most_common(25)),
            "static_vs_jvm": dict(sorted(a.items())),
            "static_crash_precision": round(a["crash/crash"] / static_crash, 4) if static_crash else None,
            "static_crash_recall": round(a["crash/crash"] / jvm_crash, 4) if jvm_crash else None,
            "top_repos_by_crashes": [{"crashes": c[0], "formatted": c[4], "repo": c[1], "app": c[2]}
                                     for c in sorted(self.crash_repos,
                                                     key=lambda c: (c[4], c[0]), reverse=True)[:40]],
        })
        with open(os.path.join(self.out_dir, "summary.json"), "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=1)
        with open(os.path.join(self.out_dir, "report.md"), "w", encoding="utf-8") as f:
            f.write(report(summary))
        return summary


def report(s):
    v = s.get("verdicts", {})
    lines = [
        "# Translation-crash census of open-source Android apps",
        "",
        "Generated %s by census.py %s (MV2 of Munim, Inc., made with AI agents)." % (
            s.get("generated_at"), __version__),
        "",
        "- Index: %s, %s apps, %s distinct repositories, %s scanned (%s not reached in the time budget)."
        % (s.get("index_url"), s.get("apps_in_index"), s.get("repos"), s.get("repos_attempted"),
           s.get("repos_not_reached")),
        "- Repositories with Android string resources: %s; with translated strings the app formats: %s."
        % (s.get("repos_with_android_strings"), s.get("repos_with_formatted_translations")),
        "- Translations of formatted strings checked: %s, with %s."
        % (s.get("formatted_translation_pairs"), s.get("jvm") or "no JVM (static check only)"),
        "- Real java.util.Formatter verdicts: %s crash whatever the app passes, %s crash if the app "
        "passes text for a %%s argument, %s fine, %s skipped because the source string itself fails."
        % (v.get("crash", 0), v.get("crash-if-text", 0), v.get("ok", 0), v.get("source-fails", 0)),
        "- Repositories with at least one crashing translation: %s (%s of them updated in the last year)."
        % (s.get("repos_with_crash"), s.get("repos_with_crash_updated_within_365_days")),
        "- How the app's Kotlin/Java code uses the strings behind the crashing translations: "
        "%(formatted)s formatted with arguments (the crash is reachable), %(referenced)s used only "
        "in other ways, %(unreferenced)s never named in the code, %(unknown)s unknown."
        % (s.get("crash_by_code_use") or {u: 0 for u in USES}),
        "- Repositories with a crashing translation of a string the code formats: %s."
        % s.get("repos_with_formatted_crash"),
        "- l10n-guard's static java-format check against the JVM: precision %s, recall %s."
        % (s.get("static_crash_precision"), s.get("static_crash_recall")),
        "",
        "## Exceptions",
        "",
    ]
    for name, count in (s.get("crash_exceptions") or {}).items():
        lines.append("- %s: %s" % (name, count))
    lines += ["", "## Languages with the most crashing translations", ""]
    for locale, count in (s.get("crash_locales_top") or {}).items():
        lines.append("- %s: %s" % (locale, count))
    lines += ["", "## Repositories with the most crashing translations", "",
              "| crashes | in formatted strings | app | repository |", "|---:|---:|---|---|"]
    for row in s.get("top_repos_by_crashes") or []:
        lines.append("| %s | %s | %s | %s |" % (row["crashes"], row.get("formatted", ""),
                                                row["app"].replace("|", "/"), row["repo"]))
    lines += ["", "## Limits", "",
              "- A string counts as formatted when its default (values/) text has a printf "
              "specifier that isn't prose. An app that never passes arguments for it would not "
              "crash; one that passes more arguments than the source uses could escape a "
              "MissingFormatArgumentException.",
              "- Plurals: %s." % PLURAL_RULE,
              "- Code use is found by matching R.string.name / R.plurals.name (and Res.string) in "
              "the .kt and .java files, fetched only for repositories with a flagged translation. "
              "'formatted' means a getString/stringResource/getQuantityString/"
              "pluralStringResource call passes arguments, or the string is wrapped in "
              "String.format or .format(). Strings looked up by name at runtime, or formatted "
              "in ways these patterns miss, count as 'referenced' or 'unreferenced'.",
              "- Verdicts come from the JDK in the container. Android's java.util.Formatter is "
              "the same OpenJDK code for these cases, but edge cases can differ by API level.",
              "- Only the latest commit of each repository's default branch is read; a "
              "translation may already be fixed on a translation platform but not merged yet.",
              ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--data-dir", default="/data")
    parser.add_argument("--out-dir", default="/out")
    parser.add_argument("--local", help="scan one local tree instead of F-Droid")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--budget-minutes", type=float, default=140)
    parser.add_argument("--timeout", type=int, default=150, help="seconds per repository")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args(argv)
    started = time.time()
    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs(args.data_dir, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="census-")
    meta = {"census_version": __version__, "l10n_guard_version": g.__version__,
            "plural_rule": PLURAL_RULE}

    if args.local:
        apps, index_url = [], "local"
        repos = [{"local": args.local, "clone": "", "web": os.path.abspath(args.local),
                  "host": "", "packages": [], "names": [os.path.basename(args.local)],
                  "updated": 0}]
        no_source = 0
    else:
        if not shutil.which("git"):
            raise SystemExit("git is not installed")
        apps, index_url = load_index(args.data_dir)
        groups = collections.OrderedDict()
        no_source = 0
        for app in sorted(apps, key=lambda a: -(a["updated"] or 0)):
            found = repo_of(app["source"])
            if not found:
                no_source += 1
                continue
            clone, web, host = found
            repo = groups.setdefault(clone.lower(), {"clone": clone, "web": web, "host": host,
                                                     "packages": [], "names": [],
                                                     "updated": app["updated"]})
            repo["packages"].append(app["package"])
            repo["names"].append(app["name"])
        repos = list(groups.values())
        if args.limit:
            repos = repos[:args.limit]
    log("%d apps, %d repositories to scan" % (len(apps), len(repos)))

    jvm = Jvm.start(args.data_dir, tmp)
    selfcheck = []
    if jvm is not None:
        got = [verdict(r)[0] for r in jvm.check([(t, s, x) for t, s, x, _ in SELF_CHECK])]
        selfcheck = [{"source": s, "translation": x, "expected": want, "got": have}
                     for (_, s, x, want), have in zip(SELF_CHECK, got)]
        if any(c["expected"] != c["got"] for c in selfcheck):
            log("JVM self-check failed: %s" % selfcheck)
        log("JVM: %s" % jvm.version)
    meta.update({"index_url": index_url, "apps_in_index": len(apps),
                 "apps_without_git_source": no_source, "repos": len(repos),
                 "jvm": jvm.version if jvm else None, "jvm_selfcheck": selfcheck})

    census = Census(args.out_dir)
    queue = collections.deque(repos)
    pending = {}
    attempted = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        while queue or pending:
            while queue and len(pending) < args.workers * 2:
                if time.time() - started > args.budget_minutes * 60:
                    break
                repo = queue.popleft()
                pending[pool.submit(process_repo, repo, args.timeout, tmp)] = repo
                attempted += 1
            if not pending:
                break
            done, _ = concurrent.futures.wait(pending, return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                repo = pending.pop(future)
                record, pairs = future.result()
                try:
                    census.add(repo, record, pairs, jvm)
                except (RuntimeError, OSError) as exc:
                    log("JVM lost (%s); static check only from here" % exc)
                    if jvm is not None:
                        jvm.close()
                    jvm = None
                    census.add(repo, record, pairs, None)
                except ValueError as exc:
                    # Raised before anything reaches the JVM, so it stays in step.
                    log("%s: %s; static check only for this repository" % (repo["web"], exc))
                    census.add(repo, record, pairs, None)
                count = sum(census.status.values())
                if count % 100 == 0:
                    log("%d done, %d pairs, %d crashes, %d crash repos" % (
                        count, census.pairs, census.verdicts["crash"], len(census.crash_repos)))
                if count % 500 == 0:
                    census.write(dict(meta, generated_at=_now(), repos_attempted=attempted,
                                      repos_not_reached=len(queue), partial=True))
    if jvm is not None:
        jvm.close()
    summary = census.write(dict(meta, generated_at=_now(), repos_attempted=attempted,
                                repos_not_reached=len(queue), partial=False,
                                elapsed_minutes=round((time.time() - started) / 60, 1)))
    census.apps.close()
    shutil.rmtree(tmp, ignore_errors=True)
    log("done: %s" % json.dumps({k: summary[k] for k in (
        "repos_attempted", "formatted_translation_pairs", "verdicts", "repos_with_crash")}))
    return 0


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    sys.exit(main())
