# Census v3: Weblate-managed Apple .strings translations that the app's own Xcode project never
# references, so they are committed but never ship. Population: every repository behind a
# Hosted Weblate component whose translations are Apple string tables (weblate-apple/v1/
# apple_components.csv, listed from Weblate's public API on 2026-11-12). Each repository is read
# at the branch Weblate commits to. Only string tables that match a Weblate component's file
# mask are counted. Rules learned in v2 (post hoc there, pre-registered here): English and Base
# tables never count, and a regional copy (ja_JP, es-ES) of a language the table already ships
# never counts. The project-file and .strings readers are v2's code, fetched unchanged
# (fetch_v2.py). Pre-registered in weblate-apple/PREREG.md of the census repository before any
# population repository is read.
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

import xcode_lproj_v2 as v2

CENSUS = ("https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/"
          "main/")
PREREG_URL = CENSUS + "weblate-apple/PREREG.md"
PREREG_MARK = "xcode-lproj census PREREG v3"
POP_URL = CENSUS + "weblate-apple/v1/apple_components.csv"
KEY = "xcode-lproj census v3"
V2_SHA256 = "982fdafd9eea92d185a7b5bb4b3f059bb4c8c81c393cc494f9614f437d6d9fa4"

MAX_PROJECTS = 30
MAX_READ = 80
MAX_LISTED = 80
REGION_RE = re.compile(r"^([A-Za-z]{2,3})[-_]([A-Za-z]{2}|[0-9]{3})$")

# Pre-registered numbers (PREREG.md).
GATE_READ = 30
GATE_GOVERNED = 10
PARSE_ERR_MAX = 2
P1_LOW_PCT, P1_HIGH_PCT = 15, 50
P2_MIN_PAIRS = 3
SAMPLE_REPOS = 12
H_MIN_SAMPLE = 3


def key(*parts):
    return hashlib.sha256("|".join((KEY,) + parts).encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ rules

def mask_regex(mask):
    """Weblate file mask -> regex; '*' stands for one path segment (the language code)."""
    return re.compile("^" + "([^/]+)".join(re.escape(p) for p in mask.split("*")) + "$")


def regional_copy(lang, shipped):
    """True for lang_REGION / lang-REGION (2 letters or 3 digits) when the plain language is
    already shipped by the same table. Script subtags (zh-Hant) are never regional copies."""
    m = REGION_RE.match(lang)
    if not m:
        return False
    base = m.group(1).lower()
    return any(s.lower() == base for s in shipped)


def read_projects(paths, reader):
    projects = sorted(p for p in paths
                      if p.endswith(".xcodeproj/project.pbxproj") and not v2.is_vendored(p))
    out, refs, regions = [], set(), set()
    for p in projects[:MAX_PROJECTS]:
        rec = {"path": p, "status": "ok", "refs": 0}
        data = reader(p)
        if data is None:
            rec["status"] = "unread"
        else:
            try:
                r, kr = v2.project_refs(p, v2.parse_plist(data.decode("utf-8-sig", "replace")))
                refs |= r
                regions |= set(kr)
                rec["refs"] = len(r)
            except (ValueError, RecursionError, IndexError, TypeError, AttributeError) as exc:
                rec["status"] = ("parse error: %s" % (exc,))[:160]
        out.append(rec)
    return out, refs, regions


def analyse_paths(paths, reader, masks):
    """The v3 measurement for one repository. paths: every file path at the commit;
    reader(path) -> bytes or None; masks: the Weblate file masks of its components."""
    res = {"projects": [], "generated": v2.generators(paths), "translated": False,
           "managed_files": 0, "tables": 0, "managed_tables": 0, "excluded_package": 0,
           "lost": [], "n_lost": 0, "n_confirmed": 0, "skipped": {}}
    regexes = [mask_regex(m) for m in masks if m]
    res["projects"], refs, regions = read_projects(paths, reader)
    pkg = set(p.rpartition("/")[0] for p in paths
              if v2.basename(p) == "Package.swift" or v2.basename(p).endswith(".podspec"))
    shipped_any = set()
    tables = {}
    for p in paths:
        m = v2.LPROJ_RE.match(p)
        if not m or v2.is_vendored(p):
            continue
        if v2.covered(p, refs):
            shipped_any.add(m.group(2))
        if not any(rx.match(p) for rx in regexes):
            continue
        res["managed_files"] += 1
        if not v2.english(m.group(2)):
            res["translated"] = True
        d = m.group(1) or ""
        if v2.under(d, pkg):
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
        shipped = set(lang for lang in langs if v2.covered(langs[lang], refs))
        for lang in sorted(langs):
            if lang in shipped:
                continue
            if v2.english(lang):
                skip = "english"
            elif regional_copy(lang, shipped):
                skip = "regional copy"
            else:
                skip = ""
            if skip:
                res["skipped"][skip] = res["skipped"].get(skip, 0) + 1
                continue
            found.append({"dir": d, "table": name, "lang": lang, "path": langs[lang],
                          "listed": len(direct), "in_known_regions": lang in regions,
                          "whole": lang not in shipped_any, "_langs": langs})
    res["n_lost"] = len(found)
    for i, f in enumerate(found):
        langs = f.pop("_langs")
        f.update(entries=None, compared=None, differs=None, translated=None, reference="",
                 confirmed="unread")
        if i >= MAX_READ:
            continue
        data = reader(f["path"])
        if data is None:
            continue
        target = v2.strings_table(v2.decode_strings(data))
        ref_lang = next((x for x in v2.REFERENCE_ORDER if x in langs and x != f["lang"]), None)
        reference = None
        if ref_lang:
            rd = reader(langs[ref_lang])
            reference = v2.strings_table(v2.decode_strings(rd)) if rd is not None else None
            f["reference"] = ref_lang if reference is not None else ""
        st = v2.content_stats(target, reference)
        f.update(st)
        f["confirmed"] = v2.confirmed(st)
    res["n_confirmed"] = sum(1 for f in found if f["confirmed"] == "yes")
    res["lost"] = found[:MAX_LISTED]
    res["known_regions"] = sorted(regions)
    return res


# ------------------------------------------------------------------ git

def fetch_ref(url, branch, d):
    """Blobless depth-1 fetch of Weblate's branch (or HEAD if that fails).
    Returns (dir, commit, committed, paths, ref used)."""
    s = os.path.join(d, "s")
    steps = [["init", "--quiet", s],
             ["-C", s, "remote", "add", "origin", url],
             ["-C", s, "config", "core.repositoryformatversion", "1"],
             ["-C", s, "config", "extensions.partialClone", "origin"],
             ["-C", s, "config", "remote.origin.promisor", "true"],
             ["-C", s, "config", "remote.origin.partialclonefilter", "blob:none"]]
    for args in steps:
        r = v2.git(args, timeout=600)
        if r.returncode != 0:
            raise RuntimeError("git setup failed: " + r.stderr.strip()[-200:])
    used, last = None, ""
    for ref in ([branch] if branch else []) + ["HEAD"]:
        r = v2.git(["-C", s, "fetch", "--quiet", "--depth", "1", "--filter=blob:none", "origin",
                    ref], timeout=900)
        if r.returncode == 0:
            used = ref
            break
        last = r.stderr.strip()[-200:]
    if used is None:
        raise RuntimeError("git fetch failed: " + last)
    rp = v2.git(["-C", s, "rev-parse", "FETCH_HEAD"])
    commit = rp.stdout.strip()
    if rp.returncode != 0 or not re.match(r"^[0-9a-f]{40}$", commit):
        raise RuntimeError("rev-parse failed: " + rp.stderr.strip()[:200])
    lg = v2.git(["-C", s, "log", "-1", "--format=%cI", commit])
    committed = lg.stdout.strip() if lg.returncode == 0 else ""
    lt = v2.git(["-C", s, "ls-tree", "-r", "-z", "--name-only", commit])
    if lt.returncode != 0:
        raise RuntimeError("ls-tree failed: " + lt.stderr.strip()[:200])
    return s, commit, committed, [p for p in lt.stdout.split("\0") if p], used


def analyse(entry, tmp_root):
    res = {"repo": entry["repo"], "branch": entry["branch"], "ref": "", "commit": "",
           "committed": "", "status": "ok", "n_paths": 0, "masks": entry["masks"],
           "components": entry["components"]}
    t0 = time.time()
    d = tempfile.mkdtemp(dir=tmp_root)
    try:
        s, commit, committed, paths, used = fetch_ref(entry["repo"], entry["branch"], d)
        res.update(commit=commit, committed=committed, n_paths=len(paths), ref=used)
        cache = {}

        def reader(p):
            if p not in cache:
                cache[p] = v2.read_blob(s, commit, p)
            return cache[p]

        res.update(analyse_paths(paths, reader, entry["masks"]))
        try:
            res["v2_rule_confirmed"] = v2.analyse_paths(paths, reader)["n_confirmed"]
        except Exception as exc:  # exploratory only
            res["v2_rule_confirmed"] = ("error: %r" % (exc,))[:120]
    except subprocess.TimeoutExpired:
        res["status"] = "timeout"
    except Exception as exc:  # record, keep going
        res["status"] = ("error: %r" % (exc,))[:240]
    finally:
        res["seconds"] = round(time.time() - t0, 1)
        shutil.rmtree(d, ignore_errors=True)
    return res


# ------------------------------------------------------------------ population

def population(csv_bytes):
    """One entry per repository (https URL, case-insensitive) behind the Apple components:
    the branch most of its components use, every file mask, every component."""
    repos = {}
    for r in csv.DictReader(io.StringIO(csv_bytes.decode("utf-8-sig"))):
        u = (r.get("repo_norm") or "").strip()
        if not u.startswith("https://") or (r.get("apple") or "") != "1":
            continue
        e = repos.setdefault(u.lower(), {"repo": u, "branches": {}, "masks": [],
                                         "components": []})
        b = (r.get("branch") or "").strip()
        if b:
            e["branches"][b] = e["branches"].get(b, 0) + 1
        m = r.get("filemask") or ""
        if m and m not in e["masks"]:
            e["masks"].append(m)
        e["components"].append("%s/%s" % (r.get("project", ""), r.get("component", "")))
    out = []
    for k in sorted(repos):
        e = repos[k]
        br = sorted(e["branches"].items(), key=lambda kv: (-kv[1], kv[0]))
        e["branch"] = br[0][0] if br else ""
        e["branch_conflict"] = len(br) > 1
        del e["branches"]
        out.append(e)
    return out


# ------------------------------------------------------------------ grading

def governed(r):
    return (r.get("status") == "ok" and r.get("translated") and not r.get("generated")
            and r.get("managed_tables", 0) > 0)


def lost_pairs(flagged):
    """{(repo, lang): whole} for every language with a confirmed lost file."""
    pairs = {}
    for r in flagged:
        for f in r["lost"]:
            if f["confirmed"] == "yes":
                pairs[(r["repo"], f["lang"])] = bool(f["whole"])
    return pairs


def grade(results):
    """Pre-registered verdicts G, P1, P2 (PREREG.md) and the counts behind them."""
    ok = [r for r in results if r["status"] == "ok"]
    projects = [p for r in ok for p in r.get("projects", [])]
    perr = sum(1 for p in projects if p["status"].startswith("parse error"))
    gov = [r for r in ok if governed(r)]
    flagged = [r for r in gov if r.get("n_confirmed", 0) > 0]
    n, k = len(gov), len(flagged)
    pairs = lost_pairs(flagged)
    whole = sum(1 for w in pairs.values() if w)
    v = {}
    gate = len(ok) >= GATE_READ and n >= GATE_GOVERNED and perr <= PARSE_ERR_MAX
    v["G"] = ("PASSED" if gate else "FAILED (%d read, %d governed, %d of %d projects unparsed)"
              % (len(ok), n, perr, len(projects)))
    if not gate:
        v["P1"] = v["P2"] = "NOT TESTABLE (gate)"
    else:
        v["P1"] = ("HELD" if (100 * k >= P1_LOW_PCT * n and 100 * k <= P1_HIGH_PCT * n)
                   else "FAILED") + " (%d of %d)" % (k, n)
        if len(pairs) < P2_MIN_PAIRS:
            v["P2"] = "NOT TESTABLE (%d lost languages)" % len(pairs)
        else:
            v["P2"] = ("HELD" if 2 * whole >= len(pairs) else "FAILED") + (
                " (%d of %d whole)" % (whole, len(pairs)))
    by_lang = {}
    for (_, lang) in pairs:
        by_lang[lang] = by_lang.get(lang, 0) + 1
    skipped = {}
    for r in gov:
        for s, c in r.get("skipped", {}).items():
            skipped[s] = skipped.get(s, 0) + c
    counts = {"population": len(results), "read": len(ok), "projects": len(projects),
              "projects_unparsed": perr, "governed": n, "flagged": k,
              "flagged_share_pct": round(100.0 * k / n, 2) if n else None,
              "lost_files": sum(r["n_lost"] for r in gov),
              "confirmed_files": sum(r["n_confirmed"] for r in gov),
              "lost_languages": len(pairs), "whole_languages": whole,
              "skipped": dict(sorted(skipped.items())),
              "generated_excluded": sum(1 for r in ok if r.get("generated")),
              "no_managed_table": sum(1 for r in ok if r.get("managed_tables", 0) == 0),
              "by_language": dict(sorted(by_lang.items(), key=lambda kv: (-kv[1], kv[0]))),
              "v2_rule_flagged": sum(1 for r in ok if isinstance(r.get("v2_rule_confirmed"), int)
                                     and r["v2_rule_confirmed"] > 0)}
    return v, counts, flagged


def sample_rows(flagged):
    rows = []
    for i, r in enumerate(sorted(flagged, key=lambda r: key(r["repo"]))[:SAMPLE_REPOS], 1):
        f = sorted((f for f in r["lost"] if f["confirmed"] == "yes"),
                   key=lambda f: key(r["repo"], f["path"]))[0]
        rows.append({"sample": i, "repo": r["repo"], "ref": r["ref"], "commit": r["commit"],
                     "path": f["path"], "lang": f["lang"], "table": f["table"],
                     "whole": f["whole"], "entries": f["entries"], "differs": f["differs"],
                     "translated": f["translated"],
                     "projects": " ".join(p["path"] for p in r["projects"]),
                     "label": "", "note": ""})
    return rows


# ------------------------------------------------------------------ main

def wait_for_prereg(minutes, say):
    end = time.time() + minutes * 60
    while True:
        try:
            data = v2.fetch("%s?nocache=%d" % (PREREG_URL, int(time.time())), tries=1)
            if PREREG_MARK.encode("utf-8") in data:
                return hashlib.sha256(data).hexdigest()
        except Exception:
            pass
        if time.time() > end:
            return None
        say("waiting for PREREG.md")
        time.sleep(300)


LOST_COLS = ["repo", "ref", "commit", "path", "dir", "table", "lang", "listed",
             "in_known_regions", "whole", "entries", "compared", "differs", "translated",
             "reference", "confirmed"]
SAMPLE_COLS = ["sample", "repo", "ref", "commit", "path", "lang", "table", "whole", "entries",
               "differs", "translated", "projects", "label", "note"]
REPO_COLS = ["repo", "branch", "ref", "commit", "committed", "status", "seconds", "n_paths",
             "projects", "generated", "managed_files", "tables", "managed_tables",
             "excluded_package", "translated", "governed", "n_lost", "n_confirmed",
             "v2_rule_confirmed"]


def main(out, say, workers=6, prereg_wait_minutes=480):
    started = time.time()
    with open(v2.__file__, "rb") as fh:
        v2_sha = hashlib.sha256(fh.read()).hexdigest()
    prereg_sha = wait_for_prereg(prereg_wait_minutes, say)
    if not prereg_sha:
        say("PREREG.md not public; stopping before reading any repository")
        return 0
    say("prereg sha256 %s" % prereg_sha)
    v2.MAX_BYTES = 20000000
    pop_raw = v2.fetch(POP_URL)
    entries = population(pop_raw)
    say("population: %d repositories" % len(entries))
    tmp_root = tempfile.mkdtemp(prefix="xcl3-")
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(lambda e: analyse(e, tmp_root), entries))
    shutil.rmtree(tmp_root, ignore_errors=True)
    with open(os.path.join(out, "results.jsonl"), "w", encoding="utf-8", errors="replace") as fh:
        for r in results:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    v2.write_csv(os.path.join(out, "repos.csv"), REPO_COLS,
                 [dict(r, projects=len(r.get("projects", [])),
                       generated=" ".join(r.get("generated", [])),
                       translated="yes" if r.get("translated") else "no",
                       governed="yes" if governed(r) else "no") for r in results])
    v2.write_csv(os.path.join(out, "lost.csv"), LOST_COLS,
                 [dict(f, repo=r["repo"], ref=r["ref"], commit=r["commit"])
                  for r in results if governed(r) for f in r.get("lost", [])])
    verdicts, counts, flagged = grade(results)
    rows = sample_rows(flagged) if verdicts["G"] == "PASSED" else []
    v2.write_csv(os.path.join(out, "sample.csv"), SAMPLE_COLS, rows)
    verdicts["H"] = ("PENDING HAND CHECK (%d repositories)" % len(rows)
                     if len(rows) >= H_MIN_SAMPLE else "NOT TESTABLE (sample of %d)" % len(rows))
    status = {}
    for r in results:
        st = r["status"] if r["status"] in ("ok", "timeout") else r["status"].split(":")[0]
        status[st] = status.get(st, 0) + 1
    summary = {"verdicts": verdicts, "counts": counts, "prereg_sha256": prereg_sha,
               "population_sha256": hashlib.sha256(pop_raw).hexdigest(),
               "v2_code_sha256": v2_sha, "v2_code_identical": v2_sha == V2_SHA256,
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
