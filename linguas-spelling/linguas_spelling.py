# Census: languages that po/LINGUAS lists and the build compiles, but under a name gettext never
# looks up (zh_cn, pt-BR, nb-no), so the catalog is installed and never loaded. Population: the
# 526 repositories of linguas census v1 whose build reads po/LINGUAS, read again at today's HEAD.
# Pre-registered in linguas-spelling/PREREG.md before any population repository is read.
# Reuses linguas census v1 (linguas/linguas_census.py, fetched unchanged by fetch_lc.py).
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

import linguas_census as lc

BASE = "https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/main/"
PREREG_URL = BASE + "linguas-spelling/PREREG.md"
PREREG_MARK = "linguas-spelling census PREREG v1"
REPOS_URL = BASE + "linguas/v1/repos.csv"
KEY = "linguas-spelling v1"

# A name glibc and Python gettext can look up: lang[_TERRITORY][@modifier].
OK = re.compile(r"^[a-z]{2,3}(?:_(?:[A-Z]{2}|[0-9]{3}))?(?:@[A-Za-z]+)?$")
# Same shape with any case and '-' or '_' as the separator.
LOOSE = re.compile(r"^([A-Za-z]{2,3})(?:[_-]([A-Za-z]{2}|[0-9]{3}))?(@[A-Za-z]+)?$")
# A script subtag (Hans, Latn, Cyrl): left to the linguas-script census.
SCRIPT = re.compile(r"[_-][A-Z][a-z]{3}(?=$|[_@-])")

# Pre-registered numbers (PREREG.md).
GATE_READ = 480
GATE_GOVERNED = 450
MIN_TESTABLE = 4
P3_MIN_GROUP = 20
SAMPLE_REPOS = 12


def key(*parts):
    return hashlib.sha256("|".join((KEY,) + parts).encode("utf-8")).hexdigest()


def classify(tok):
    """(class, proposed). class: ok, script, misspelled or other. proposed is the spelling gettext
    looks up, for a misspelled entry only (else "")."""
    if OK.match(tok):
        return "ok", ""
    if SCRIPT.search(tok):
        return "script", ""
    m = LOOSE.match(tok)
    if not m:
        return "other", ""
    lang, terr, mod = m.group(1), m.group(2), m.group(3)
    prop = lang.lower() + ("_" + terr.upper() if terr else "") + (mod or "")
    return "misspelled", prop


def check_dir(po, tokens):
    """Non-ok entries among the listed languages that have a .po file (so the build compiles
    them). Each: token, class, proposed, shadowed (the proposed spelling is also listed) and
    proposed_po (a .po file with the proposed spelling exists too)."""
    toks = list(dict.fromkeys(tokens))
    tset = set(toks)
    out = []
    for t in toks:
        if t not in po:
            continue
        c, prop = classify(t)
        if c == "ok":
            continue
        out.append({"token": t, "class": c, "proposed": prop,
                    "shadowed": bool(prop) and prop in tset,
                    "proposed_po": bool(prop) and prop in po})
    return out


def is_flag(e):
    return e["class"] == "misspelled" and not e["shadowed"]


def population(data):
    """The v1 repositories with a governed LINGUAS directory that were read ok, sorted."""
    out, seen = [], set()
    for row in csv.DictReader(io.StringIO(lc.decode(data))):
        if row.get("governed") != "yes" or row.get("status") != "ok":
            continue
        k = row["repo"].lower()
        if k in seen:
            continue
        seen.add(k)
        out.append({"repo": row["repo"], "group": row.get("group", ""),
                    "v1_commit": row.get("commit", "")})
    return sorted(out, key=lambda e: e["repo"].lower())


def analyse(entry, tmp_root):
    res = {"repo": entry["repo"], "group": entry.get("group", ""),
           "v1_commit": entry.get("v1_commit", ""), "status": "ok", "commit": "", "dirs": []}
    t0 = time.time()
    d = tempfile.mkdtemp(dir=tmp_root)
    try:
        s, res["commit"], paths = lc.clone(entry["repo"], d)
        pset = set(paths)
        dirs = lc.po_dirs(paths)
        for dname in sorted(dirs)[:lc.MAX_DIRS]:
            po = dirs[dname]
            prefix = dname + "/" if dname else ""
            lin = lc.read_blob(s, res["commit"], prefix + "LINGUAS")
            mb = (lc.read_blob(s, res["commit"], prefix + "meson.build")
                  if (prefix + "meson.build") in pset else None)
            conf = [lc.decode(x) for x in (lc.read_blob(s, res["commit"], p)
                                           for p in lc.configure_paths(dname, pset))
                    if x is not None]
            build = lc.build_kind(lc.decode(mb) if mb is not None else None, conf)
            rec = {"dir": dname, "build": build, "linguas_read": lin is not None,
                   "n_po": len(po), "n_listed": 0, "entries": []}
            if lin is not None:
                text = lc.decode(lin)
                tokens = (lc.meson_linguas(text) if build.startswith("meson")
                          else lc.gnu_linguas(text))
                rec["n_listed"] = len(tokens)
                rec["entries"] = [dict(e, dir=dname) for e in check_dir(po, tokens)]
            res["dirs"].append(rec)
    except subprocess.TimeoutExpired:
        res["status"] = "timeout"
    except Exception as exc:  # record, keep going
        res["status"] = ("error: %r" % (exc,))[:240]
    finally:
        res["seconds"] = round(time.time() - t0, 1)
        shutil.rmtree(d, ignore_errors=True)
    return res


def governed(r):
    return [x for x in r["dirs"] if x["build"] in lc.GOVERNED and x["linguas_read"]]


def entries(r):
    return [e for x in governed(r) for e in x["entries"]]


def flags(r):
    return [e for e in entries(r) if is_flag(e)]


def lang_of(name):
    return name.split("@", 1)[0].split("_", 1)[0]


def grade(results, gate_read=GATE_READ, gate_governed=GATE_GOVERNED):
    """Pre-registered verdicts G, P1-P3 (PREREG.md) and the counts behind them."""
    read = [r for r in results if r["status"] == "ok"]
    gov = [r for r in read if governed(r)]
    flagged = [r for r in gov if flags(r)]
    n, k = len(gov), len(flagged)
    fl = [e for r in flagged for e in flags(r)]
    zp = [e for e in fl if lang_of(e["proposed"]) in ("zh", "pt")]
    gn = [r for r in gov if r["group"] == "gnome"]
    gk = sum(1 for r in gn if flags(r))
    v = {}
    gate = len(read) >= gate_read and n >= gate_governed
    v["G"] = ("PASSED" if gate else "FAILED (%d read, %d with a governed LINGUAS directory)"
              % (len(read), n))
    if not gate:
        for p in ("P1", "P2", "P3"):
            v[p] = "NOT TESTABLE (gate)"
    else:
        v["P1"] = "HELD" if (200 * k >= n and 20 * k <= n) else "FAILED"
        v["P2"] = ("NOT TESTABLE (%d flagged entries)" % len(fl) if len(fl) < MIN_TESTABLE
                   else "HELD" if 2 * len(zp) >= len(fl) else "FAILED")
        v["P3"] = ("NOT TESTABLE (%d gnome repositories)" % len(gn) if len(gn) < P3_MIN_GROUP
                   else "HELD" if gk == 0 else "FAILED")
    allent = [e for r in gov for e in entries(r)]
    by_class = {}
    for e in allent:
        c = e["class"] + (" (shadowed)" if e["class"] == "misspelled" and e["shadowed"] else "")
        by_class[c] = by_class.get(c, 0) + 1
    tokens = {}
    for e in fl:
        tokens[e["token"]] = tokens.get(e["token"], 0) + 1
    counts = {
        "read": len(read), "governed_repos": n, "flagged_repos": k,
        "flagged_share_pct": round(100.0 * k / n, 2) if n else None,
        "flagged_entries": len(fl), "flagged_zh_pt": len(zp),
        "flagged_hyphen": sum(1 for e in fl if "-" in e["token"]),
        "flagged_with_proposed_po": sum(1 for e in fl if e["proposed_po"]),
        "gnome_governed": len(gn), "gnome_flagged": gk,
        "non_ok_entries_by_class": dict(sorted(by_class.items())),
        "flagged_tokens": dict(sorted(tokens.items(), key=lambda kv: (-kv[1], kv[0]))),
    }
    return v, counts, flagged


def sample_rows(flagged):
    rows = []
    for i, r in enumerate(sorted(flagged, key=lambda r: key(r["repo"]))[:SAMPLE_REPOS], 1):
        e = sorted(flags(r), key=lambda e: key(r["repo"], e["dir"], e["token"]))[0]
        rows.append({"sample": i, "repo": r["repo"], "commit": r["commit"], "group": r["group"],
                     "dir": e["dir"], "token": e["token"], "proposed": e["proposed"],
                     "label": "", "note": ""})
    return rows


def control(tmp_root):
    """GNOME Calculator's po/LINGUAS (Damned Lies spells its languages as gettext looks them
    up) must list >= 30 languages and none may be flagged. Returns "" when it passes."""
    d = tempfile.mkdtemp(dir=tmp_root)
    try:
        s, commit, paths = lc.clone(lc.CONTROL_REPO, d)
        po = lc.po_dirs(paths).get("po", {})
        lin = lc.read_blob(s, commit, "po/LINGUAS")
        if not po or lin is None:
            return "po/LINGUAS or po/*.po not found"
        tokens = lc.meson_linguas(lc.decode(lin))
        found = check_dir(po, tokens)
        if len(tokens) < 30:
            return "only %d languages listed" % len(tokens)
        if any(is_flag(e) for e in found):
            return "control flagged %r" % ([e["token"] for e in found if is_flag(e)],)
        return ""
    except Exception as exc:
        return "control error: %r" % (exc,)
    finally:
        shutil.rmtree(d, ignore_errors=True)


ENTRY_COLS = ["repo", "commit", "group", "dir", "build", "token", "class", "proposed",
              "shadowed", "proposed_po"]
SAMPLE_COLS = ["sample", "repo", "commit", "group", "dir", "token", "proposed", "label", "note"]


def main(out, say, workers=8, prereg_wait_minutes=360):
    started = time.time()
    tmp_root = tempfile.mkdtemp(prefix="lspell-")
    err = control(tmp_root)
    if err:
        say("control failed: " + err)
        return 3
    say("control passed (%s)" % lc.CONTROL_REPO)
    lc.PREREG_URL, lc.PREREG_MARK = PREREG_URL, PREREG_MARK
    prereg_sha = lc.wait_for_prereg(prereg_wait_minutes, say)
    if not prereg_sha:
        say("PREREG.md not public; stopping before reading any repository")
        return 4
    say("prereg sha256 %s" % prereg_sha)
    raw = None
    for attempt in range(3):
        try:
            raw = lc.fetch_text(REPOS_URL)
            break
        except OSError as exc:
            say("repos.csv attempt %d failed: %r" % (attempt + 1, exc))
            time.sleep(30)
    if raw is None:
        say("could not read linguas/v1/repos.csv")
        return 5
    pop = population(raw)
    say("%d repositories in the population" % len(pop))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(lambda e: analyse(e, tmp_root), pop))
    shutil.rmtree(tmp_root, ignore_errors=True)

    with open(os.path.join(out, "results.jsonl"), "w", encoding="utf-8", errors="replace") as fh:
        for r in results:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    lc.write_csv(os.path.join(out, "repos.csv"),
                 ["repo", "v1_commit", "commit", "group", "status", "seconds", "governed",
                  "flagged"],
                 [dict(r, governed="yes" if governed(r) else "no", flagged=len(flags(r)))
                  for r in results])
    lc.write_csv(os.path.join(out, "entries.csv"), ENTRY_COLS,
                 [dict(e, repo=r["repo"], commit=r["commit"], group=r["group"], build=x["build"])
                  for r in results for x in governed(r) for e in x["entries"]])
    verdicts, counts, flagged = grade(results)
    rows = sample_rows(flagged) if verdicts["G"] == "PASSED" else []
    lc.write_csv(os.path.join(out, "sample.csv"), SAMPLE_COLS, rows)
    verdicts["H"] = ("PENDING HAND CHECK (%d repositories)" % len(rows)
                     if len(rows) >= MIN_TESTABLE else "NOT TESTABLE (sample of %d)" % len(rows))
    status = {}
    for r in results:
        st = r["status"] if r["status"] in ("ok", "timeout") else r["status"].split(":")[0]
        status[st] = status.get(st, 0) + 1
    summary = {"verdicts": verdicts, "counts": counts, "prereg_sha256": prereg_sha,
               "repos_csv_sha256": hashlib.sha256(raw).hexdigest(), "population": len(pop),
               "status": dict(sorted(status.items())), "control": lc.CONTROL_REPO,
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
