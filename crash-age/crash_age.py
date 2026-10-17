#!/usr/bin/env python3
"""How old are the census's crashing translations, and how did they arrive?
(crash_age 0.1.0)

For every row of the census's callsites/findings.csv (the 2026-10-17 read)
whose verdict is "crash" or "crash-if-text", this reads the git history of
the strings.xml the row came from, on the first-parent line of the commit
the census read, and finds:

  intro     the commit from which the exact crashing text has been there
            without a break up to the census commit (the start of its last
            unbroken run), with the commit's committer time;
  age       days from that commit to the census read (2026-10-17 05:13 UTC);
  pipeline  how that commit came in: a translation platform (Weblate,
            Crowdin, Transifex, translatewiki.net, ...) by its author,
            committer, subject or, for a merge, the merged commits that
            touch the file; "other bot"; or "direct" (a commit no platform
            or bot marks);
  episodes  how many separate times the exact text has been in the file
            (2 or more: it was gone and came back);
  before    what the key held just before: nothing ("new"), another text
            ("replaced"), or unknown because the run starts at the file's
            first version at this path ("file start": the age is a lower
            bound).

Each repository is cloned once with full history but no file contents
(--filter=blob:none, bare); only the versions of the files the rows name
are downloaded, in batches. Each version is parsed with the census's own
l10n_guard.parse_android and _android_text, so "the exact text" means the
string the census flagged.

No names or email addresses are written anywhere: only commit hashes and
the pipeline each commit was classed as.

  python crash_age.py --data-dir /data --out-dir /out

Writes ages.csv, repos.csv, crash_age.json and crash_age.md. The
predictions in PREDICTIONS.md were published before this ran; the job
refuses to run until they are on main.

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import collections
import concurrent.futures
import csv
import datetime
import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET

import l10n_guard as g

__version__ = "0.1.0"

REPO_RAW = "https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/main/"
PREDICTIONS_URL = REPO_RAW + "crash-age/PREDICTIONS.md"
PREDICTIONS_MARK = "crash_age 0.1.0 predictions"
FINDINGS = "findings.csv"
READ_AT = datetime.datetime(2026, 10, 17, 5, 13, tzinfo=datetime.timezone.utc)
VERDICTS = ("crash", "crash-if-text")
MAX_VERSIONS = 3000  # newest versions kept per file; older ones are cut (left-censored)
BATCH = 500  # blobs per fetch
READ_BATCH = 100  # blobs held in memory at once
GIT_ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_ASKPASS="", SSH_ASKPASS="",
               GIT_LFS_SKIP_SMUDGE="1", GIT_LITERAL_PATHSPECS="1")
# (pipeline, lower-case markers in a commit's author, committer and subject).
PIPELINES = [
    ("weblate", ["weblate", "translate.codeberg.org", "codeberg translate", "toolate"]),
    ("crowdin", ["crowdin", "l10n_"]),  # Crowdin Bot commits; its PR branches are l10n_<branch>
    ("transifex", ["transifex"]),
    ("translatewiki", ["translatewiki", "localisation updates from"]),
    ("localazy", ["localazy"]),
    ("lokalise", ["lokalise"]),
    ("pontoon", ["pontoon"]),
    ("poeditor", ["poeditor"]),
    ("gitlocalize", ["gitlocalize"]),
]
PLATFORM_NAMES = tuple(name for name, _ in PIPELINES)
BOT_MARKERS = ["[bot]", "github-actions", "bot@", "dependabot", "renovate"]
ABSENT = object()
UNREADABLE = object()
AGE_FIELDS = ["verdict", "use", "locale", "key", "file", "repo", "commit", "platform", "status",
              "intro_commit", "intro_at", "age_days", "pipeline", "episodes", "before",
              "first_at", "versions"]

_lock = threading.Lock()


def log(message):
    print("[%s] %s" % (datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S"),
                       message), flush=True)


# --------------------------------------------------------------- pure parts

def classify(text):
    """The pipeline a commit's "author committer subject" text points to."""
    low = text.lower()
    for name, markers in PIPELINES:
        if any(m in low for m in markers):
            return name
    if any(m in low for m in BOT_MARKERS):
        return "other bot"
    return "direct"


def decode(data):
    """A file's bytes as text, the way l10n_guard._read reads a file."""
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = data.decode("utf-16")
    else:
        text = data.decode("utf-8-sig")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def values(data, keys):
    """{key: runtime text or ABSENT} for keys in one version of a
    strings.xml, or UNREADABLE if it doesn't parse."""
    try:
        found = g.parse_android(decode(data))
    except (ValueError, ET.ParseError):
        return UNREADABLE
    return {k: g._android_text(found[k]) if k in found else ABSENT for k in keys}


def parse_log(text):
    """{path: [version]} from git log --raw output made with LOG_FORMAT,
    oldest version first. A version is (time, commit, merge, ident, blob);
    blob is None where the commit deleted the file."""
    by_path = collections.defaultdict(list)
    head = None
    for line in text.split("\n"):
        if line.startswith("@@C\t"):
            parts = line.split("\t", 6)
            if len(parts) < 7:
                head = None
                continue
            _, sha, ts, parents, author, committer, subject = parts
            head = (int(ts), sha, len(parents.split()) > 1,
                    "%s %s %s" % (author, committer, subject))
        elif line.startswith(":") and head and "\t" in line:
            meta, path = line[1:].split("\t", 1)
            fields = meta.split()
            if len(fields) < 5:
                continue
            blob = None if fields[4].startswith("D") or set(fields[3]) == {"0"} else fields[3]
            by_path[path].append(head + (blob,))
    for path in by_path:
        by_path[path].reverse()
    return dict(by_path)


def parse_batch(data):
    """{oid: bytes} from git cat-file --batch output."""
    out, pos = {}, 0
    while pos < len(data):
        nl = data.find(b"\n", pos)
        if nl < 0:
            break
        parts = data[pos:nl].decode("ascii", "replace").split()
        if len(parts) == 3:
            size = int(parts[2])
            out[parts[0]] = data[nl + 1:nl + 1 + size]
            pos = nl + 1 + size + 1
        else:  # "<oid> missing"
            pos = nl + 1
    return out


def timeline(flags):
    """For a text's presence in each version, oldest first (True, False, or
    None where the version couldn't be read): (index where the last unbroken
    run of True starts, or None if the newest readable version lacks it;
    number of separate runs of True)."""
    start, runs, last = None, 0, False
    for i, flag in enumerate(flags):
        if flag is None:
            continue
        if flag and not last:
            runs += 1
            start = i
        last = flag
    return (start if last else None), runs


def before(states, start):
    """What the key held before versions[start]: "new", "replaced" or
    "file start" (no readable version before it)."""
    for state in reversed(states[:start]):
        if state is UNREADABLE:
            continue
        return "new" if state is ABSENT else "replaced"
    return "file start"


def iso(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def date_row(row, versions, states, cut, pipeline_of):
    """Fills row's dating fields from its file's versions (oldest first) and
    the key's state in each (text, ABSENT or UNREADABLE). cut: older
    versions were dropped. pipeline_of(version) classes a commit."""
    want = row["translation"]
    flags = [None if s is UNREADABLE else (s is not ABSENT and s == want) for s in states]
    start, runs = timeline(flags)
    row["versions"] = len(versions)
    if start is None:
        row["status"] = "not found"
        return row
    prev = before(states, start)
    if prev == "file start" and cut:
        prev = "cut"
    intro = versions[start]
    first = next(i for i, f in enumerate(flags) if f)
    row.update(status="dated" if prev in ("new", "replaced") else "lower bound",
               intro_commit=intro[1], intro_at=iso(intro[0]),
               age_days=round((READ_AT.timestamp() - intro[0]) / 86400.0, 1),
               pipeline=pipeline_of(intro), episodes=runs, before=prev,
               first_at=iso(versions[first][0]))
    return row


# --------------------------------------------------------------- git

LOG_FORMAT = "--format=@@C%x09%H%x09%ct%x09%P%x09%an <%ae>%x09%cn <%ce>%x09%s"


def git(args, cwd=None, timeout=300, data=None):
    r = subprocess.run(["git", "-c", "core.quotePath=false"] + args, cwd=cwd, timeout=timeout,
                       capture_output=True, input=data, env=GIT_ENV)
    return r.returncode, r.stdout, r.stderr.decode("utf-8", "replace")


def file_log(dest, commit, paths, timeout):
    base = ["log", "--first-parent", "--no-renames", "--raw", "--no-abbrev", LOG_FORMAT]
    code, out, err = git(base[:2] + ["--diff-merges=first-parent"] + base[2:] + [commit, "--"]
                         + paths, dest, timeout)
    if code:  # git before 2.31: -m with --first-parent diffs merges against the first parent
        code, out, err = git(base[:2] + ["-m"] + base[2:] + [commit, "--"] + paths, dest, timeout)
    if code:
        raise RuntimeError("git log failed: %s" % err.strip()[-300:])
    return parse_log(out.decode("utf-8", "replace"))


def fetch_blobs(dest, oids, timeout):
    """Downloads blobs in batches the way git's own lazy fetch does. Returns
    the number of batches that failed (their blobs are then fetched one at a
    time when read)."""
    failed = 0
    for i in range(0, len(oids), BATCH):
        chunk = oids[i:i + BATCH]
        code, _, err = git(["-c", "fetch.negotiationAlgorithm=noop", "fetch", "origin", "--no-tags",
                            "--no-write-fetch-head", "--recurse-submodules=no",
                            "--filter=blob:none", "--stdin"], dest, timeout,
                           "".join(o + "\n" for o in chunk).encode())
        if code:
            failed += 1
            log("blob batch failed in %s: %s" % (dest, err.strip()[-200:]))
    return failed


def read_blobs(dest, oids, timeout):
    out = {}
    for i in range(0, len(oids), READ_BATCH):
        chunk = oids[i:i + READ_BATCH]
        code, data, err = git(["cat-file", "--batch"], dest, timeout,
                              "".join(o + "\n" for o in chunk).encode())
        if code:
            raise RuntimeError("cat-file failed: %s" % err.strip()[-300:])
        out.update(parse_batch(data))
    return out


def pipeline_in(dest, version, path, timeout):
    """classify() for a version's commit; for a merge, the merged commits
    that touch the file are read too."""
    ts, sha, merge, ident, _ = version
    text = ident
    if merge:
        code, out, _ = git(["log", "-n", "50", "--format=%an <%ae> %cn <%ce> %s",
                            "%s^1..%s^2" % (sha, sha), "--", path], dest, timeout)
        if not code:
            inner = out.decode("utf-8", "replace")
            kind = classify(inner)
            if kind != "direct":
                return kind
    return classify(text)


def process_repo(repo, rows, work, timeout):
    """Dates every row of one repository. Returns (rows, record)."""
    clone_url = repo + ".git"
    commit = rows[0]["commit"]
    dest = os.path.join(work, hashlib.sha1((repo + commit).encode()).hexdigest()[:16])
    record = {"repo": repo, "rows": len(rows), "status": "ok", "versions": 0, "blobs": 0,
              "failed_batches": 0, "seconds": 0}
    start = time.time()
    shutil.rmtree(dest, ignore_errors=True)
    try:
        code, _, err = git(["clone", "--quiet", "--bare", "--filter=blob:none", "--single-branch",
                            clone_url, dest], None, timeout)
        if code:
            raise RuntimeError("clone failed: %s" % err.strip()[-300:])
        if git(["cat-file", "-e", commit + "^{commit}"], dest, 60)[0]:
            code, _, err = git(["fetch", "--quiet", "--filter=blob:none", "origin", commit], dest,
                               timeout)
            if code:
                raise RuntimeError("census commit not found: %s" % err.strip()[-200:])
        paths = sorted({r["file"] for r in rows})
        logs = file_log(dest, commit, paths, timeout)
        for path in paths:
            versions = logs.get(path, [])
            cut = len(versions) > MAX_VERSIONS
            versions = versions[-MAX_VERSIONS:]
            record["versions"] += len(versions)
            mine = [r for r in rows if r["file"] == path]
            if not versions:
                for r in mine:
                    r.update(status="not found", versions=0)
                continue
            oids = sorted({v[4] for v in versions if v[4]})
            record["blobs"] += len(oids)
            record["failed_batches"] += fetch_blobs(dest, oids, timeout)
            keys = sorted({r["key"] for r in mine})
            parsed = {}
            for i in range(0, len(oids), READ_BATCH):
                blobs = read_blobs(dest, oids[i:i + READ_BATCH], timeout)
                for oid, data in blobs.items():
                    parsed[oid] = values(data, keys)
            classes = {}

            def pipeline_of(version, path=path, classes=classes):
                if version[1] not in classes:
                    classes[version[1]] = pipeline_in(dest, version, path, timeout)
                return classes[version[1]]

            for r in mine:
                states = []
                for v in versions:
                    if v[4] is None:
                        states.append(ABSENT)
                        continue
                    got = parsed.get(v[4], UNREADABLE)
                    states.append(got if got is UNREADABLE else got[r["key"]])
                date_row(r, versions, states, cut, pipeline_of)
    except (RuntimeError, subprocess.TimeoutExpired, OSError) as exc:
        record["status"] = "failed: %s" % str(exc)[:300]
        for r in rows:
            if not r.get("status"):
                r["status"] = "repo failed"
    finally:
        shutil.rmtree(dest, ignore_errors=True)
    record["seconds"] = round(time.time() - start)
    return rows, record


# --------------------------------------------------------------- summary

def quantiles(xs):
    if not xs:
        return {}
    xs = sorted(xs)
    pick = lambda q: xs[min(len(xs) - 1, int(q * (len(xs) - 1) + 0.5))]  # noqa: E731
    return {"n": len(xs), "p25": pick(0.25), "median": statistics.median(xs), "p75": pick(0.75),
            "min": xs[0], "max": xs[-1]}


def summarize(rows):
    """Counts and age quantiles for one set of rows."""
    dated = [r for r in rows if r.get("status") in ("dated", "lower bound")]
    ages = [r["age_days"] for r in dated]
    by = lambda field: dict(collections.Counter(str(r.get(field, "")) for r in dated)  # noqa: E731
                            .most_common())
    pipe_ages = collections.defaultdict(list)
    for r in dated:
        pipe_ages[r["pipeline"]].append(r["age_days"])
    use_ages = collections.defaultdict(list)
    for r in dated:
        use_ages[r["use"]].append(r["age_days"])
    years = collections.Counter(r["intro_at"][:4] for r in dated)
    repo_medians = collections.defaultdict(list)
    for r in dated:
        repo_medians[r["repo"]].append(r["age_days"])
    return {"rows": len(rows), "status": dict(collections.Counter(r.get("status", "") for r in rows)),
            "dated": len(dated), "age_days": quantiles(ages),
            "age_days_exact_only": quantiles([r["age_days"] for r in dated
                                              if r["status"] == "dated"]),
            "repo_median_age_days": quantiles([statistics.median(v) for v in repo_medians.values()]),
            "pipeline": by("pipeline"), "before": by("before"), "episodes": by("episodes"),
            "use": by("use"), "census_platform": by("platform"),
            "age_by_pipeline": {k: quantiles(v) for k, v in sorted(pipe_ages.items())},
            "age_by_use": {k: quantiles(v) for k, v in sorted(use_ages.items())},
            "intro_year": dict(sorted(years.items())),
            "within_90_days": sum(1 for a in ages if a <= 90),
            "older_than_2_years": sum(1 for a in ages if a > 730)}


def predictions(rows):
    """PREDICTIONS.md's A1-A6, on the rows whose verdict is "crash"."""
    crash = [r for r in rows if r["verdict"] == "crash"]
    dated = [r for r in crash if r.get("status") in ("dated", "lower bound")]
    ages = [r["age_days"] for r in dated]
    pipes = collections.Counter(r["pipeline"] for r in dated)
    platform = sum(n for p, n in pipes.items() if p in PLATFORM_NAMES)
    back = sum(1 for r in dated if r["episodes"] >= 2)
    formatted = [r["age_days"] for r in dated if r["use"] == "formatted"]
    top = pipes.most_common(2)
    med = statistics.median(ages) if ages else None
    fmed = statistics.median(formatted) if formatted else None
    return [
        {"id": "A1", "text": "median age of dated crash rows is at least 365 days: %s days (%d rows)"
         % (med, len(ages)), "held": None if med is None else med >= 365},
        {"id": "A2", "text": "at least half of dated crash rows arrived through a translation "
         "platform's commit: %d of %d" % (platform, len(dated)),
         "held": bool(dated) and platform * 2 >= len(dated)},
        {"id": "A3", "text": "Weblate is the most common pipeline, ahead of direct commits and every "
         "other platform: %s" % json.dumps(dict(pipes.most_common())),
         "held": bool(top) and top[0][0] == "weblate" and (len(top) == 1 or top[0][1] > top[1][1])},
        {"id": "A4", "text": "at least 5%% of dated crash rows were gone and came back (2 or more "
         "episodes): %d of %d" % (back, len(dated)),
         "held": bool(dated) and back * 20 >= len(dated)},
        {"id": "A5", "text": "at least 80%% of crash rows are dated: %d of %d" % (len(dated), len(crash)),
         "held": bool(crash) and len(dated) * 5 >= len(crash) * 4},
        {"id": "A6", "text": "median age of dated crash rows the census calls formatted is at least "
         "180 days: %s days (%d rows)" % (fmed, len(formatted)),
         "held": None if fmed is None else fmed >= 180},
    ]


def label(held):
    return "NOT TESTABLE" if held is None else "HELD" if held else "FAILED"


def report(result):
    lines = ["# crash_age %s" % __version__, "",
             "MV2 of Munim, Inc. Made with AI agents. Generated by crash_age.py; numbers only.", ""]
    for p in result["predictions"]:
        lines.append("- %s %s: %s" % (p["id"], label(p["held"]), p["text"]))
    for name in ("crash", "crash-if-text"):
        s = result["summary"][name]
        lines += ["", "## %s rows" % name, "", "```", json.dumps(s, indent=1, ensure_ascii=False),
                  "```"]
    lines += ["", "## Repositories", "", "```",
              json.dumps(result["repos"], indent=1, ensure_ascii=False), "```", ""]
    return "\n".join(lines)


# --------------------------------------------------------------- main

def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "mv2-crash-age"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def load_rows(path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["verdict"] in VERDICTS]
    out, seen = [], set()
    for r in rows:
        k = (r["repo"], r["file"], r["key"])
        if k in seen:
            continue
        seen.add(k)
        out.append({f: r.get(f, "") for f in ("verdict", "use", "locale", "key", "file", "repo",
                                              "commit", "platform", "translation")})
    return out


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="/data")
    parser.add_argument("--out-dir", default="/out")
    parser.add_argument("--findings", default=FINDINGS)
    parser.add_argument("--timeout", type=int, default=900, help="seconds per git step")
    parser.add_argument("--budget-minutes", type=float, default=150)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--no-gate", action="store_true")
    args = parser.parse_args(argv)
    if not args.no_gate:
        try:
            pred = _fetch(PREDICTIONS_URL)
        except Exception as exc:
            pred = ""
            print("gate: could not read PREDICTIONS.md on main: %s" % exc)
        if PREDICTIONS_MARK not in pred:
            print("gate: predictions not on main; refusing to run")
            return 3
    os.makedirs(args.out_dir, exist_ok=True)
    cache = os.path.join(args.data_dir, "crash-age-cache-" + __version__)
    work = os.path.join(args.data_dir, "crash-age-work")
    os.makedirs(cache, exist_ok=True)
    os.makedirs(work, exist_ok=True)

    rows = load_rows(args.findings)
    by_repo = collections.OrderedDict()
    for r in sorted(rows, key=lambda r: r["repo"]):
        by_repo.setdefault(r["repo"], []).append(r)
    log("%d rows (%s) in %d repositories" % (len(rows), json.dumps(
        dict(collections.Counter(r["verdict"] for r in rows))), len(by_repo)))

    deadline = time.time() + args.budget_minutes * 60
    done, records = [], []

    def one(repo):
        mine = by_repo[repo]
        path = os.path.join(cache, hashlib.sha1((repo + mine[0]["commit"]).encode()).hexdigest()
                            + ".json")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                saved = json.load(f)
            return saved["rows"], saved["record"]
        if time.time() > deadline:
            for r in mine:
                r["status"] = "not reached"
            return mine, {"repo": repo, "rows": len(mine), "status": "not reached"}
        got, record = process_repo(repo, mine, work, args.timeout)
        if record["status"] == "ok":
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"rows": got, "record": record}, f, ensure_ascii=False)
        return got, record

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(one, repo): repo for repo in by_repo}
        for fut in concurrent.futures.as_completed(futures):
            repo = futures[fut]
            try:
                got, record = fut.result()
            except Exception as exc:  # keep going; the repository is reported as failed
                got = by_repo[repo]
                for r in got:
                    r["status"] = "repo failed"
                record = {"repo": repo, "rows": len(got), "status": "failed: %r" % exc}
            with _lock:
                done.extend(got)
                records.append(record)
            ages = [r["age_days"] for r in got if "age_days" in r]
            print("repo %s: %s, %d rows, %d dated, median age %s days, %s s"
                  % (repo, record["status"][:80], len(got), len(ages),
                     statistics.median(ages) if ages else "-", record.get("seconds", "-")),
                  flush=True)

    done.sort(key=lambda r: (r["repo"], r["file"], r["key"]))
    records.sort(key=lambda r: r["repo"])
    with open(os.path.join(args.out_dir, "ages.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=AGE_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(done)
    with open(os.path.join(args.out_dir, "repos.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["repo", "rows", "status", "versions", "blobs",
                                          "failed_batches", "seconds"], extrasaction="ignore")
        w.writeheader()
        w.writerows(records)
    commit = ""
    if os.path.isfile("census_commit.txt"):
        with open("census_commit.txt") as f:
            commit = f.read().strip()
    checks = predictions(done)
    result = {"version": __version__, "census_commit": commit, "l10n_guard": getattr(g, "__version__", ""),
              "read_at": READ_AT.isoformat(), "predictions": checks,
              "summary": {v: summarize([r for r in done if r["verdict"] == v]) for v in VERDICTS},
              "repos": {"total": len(records),
                        "status": dict(collections.Counter(r["status"].split(":")[0]
                                                           for r in records))}}
    with open(os.path.join(args.out_dir, "crash_age.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    with open(os.path.join(args.out_dir, "crash_age.md"), "w", encoding="utf-8") as f:
        f.write(report(result))
    s = result["summary"]["crash"]
    print("crash-age: %d crash rows, %d dated; median age %s days; pipelines %s; before %s; "
          "episodes %s" % (s["rows"], s["dated"], s["age_days"].get("median"),
                           json.dumps(s["pipeline"]), json.dumps(s["before"]),
                           json.dumps(s["episodes"])), flush=True)
    for p in checks:
        print("%s %s: %s" % (p["id"], label(p["held"]), p["text"]), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
