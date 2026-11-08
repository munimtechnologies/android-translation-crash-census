# Pre-registered tests of l10n-guard 0.20.0 (see PREREG.md): the 0.19.0 regression set, the
# 0.19.0 hand-checked sample at its recorded commits, and a fresh sample of held-out
# repositories at today's HEAD. Every repository is read once and checked with both the
# released 0.19.0 code and the new 0.20.0 code. Reuses holdout_0190.py (downloaded unchanged
# from the census repository). Made with AI agents by MV2 of Munim, Inc. Apache-2.0.
import concurrent.futures
import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import time

import holdout_0190 as h

CENSUS = ("https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/"
          "main/")
PREREG_URL = CENSUS + "l10n-guard-0200/PREREG.md"
PREREG_MARK = "l10n-guard 0.20.0 PREREG v1"
SAMPLE0190_URL = CENSUS + "l10n-guard-0190/v2/sample.csv"
LABELS0190_URL = CENSUS + "l10n-guard-0190/labels.csv"
KEY = "l10n-guard 0.20 fresh v1"

# Pre-registered numbers (PREREG.md).
R4_MIN_READ = 24        # of the 28 findings labelled real (not borderline) in the 0.19.0 check
R4_MAX_MISSING = 2
R5_ABSENT = [("https://github.com/lollipopkit/flutter_server_box", "locale-config-phantom", "az"),
             ("https://github.com/aliasvault/aliasvault", "locale-config-orphan", "fa")]
GATE_HELDOUT_READ = 60
SAMPLE_REPOS = 16
FINDINGS_PER_REPO = 3
HAND_MIN = 8


def key(*parts):
    return hashlib.sha256("|".join((KEY,) + parts).encode("utf-8")).hexdigest()


def flag_set(lists):
    return {(p["code"], p.get("key", "")) for r in lists for p in r["problems"]
            if p["code"] in h.FLAG_CODES}


def analyse_both(new, old, url, ref, tmp_root):
    res = {"repo": url, "status": "ok", "commit": "", "lists": [], "old_lists": []}
    t0 = time.time()
    s = None
    try:
        s, res["commit"], paths = h.checkout(url, ref, tmp_root)
        manifests = [p for p in paths if p.endswith("AndroidManifest.xml")]
        if manifests and not any(os.path.isfile(os.path.join(s, *p.split("/"))) for p in manifests):
            res["status"] = "sparse checkout empty"
            return res

        def read(p):
            fp = os.path.join(s, *p.split("/"))
            try:
                if not os.path.isfile(fp) or os.path.getsize(fp) > h.MAX_BYTES:
                    return None
                with open(fp, "rb") as fh:
                    return fh.read()
            except OSError:
                return None

        res["lists"] = new.locale_config_lists(paths, read)
        res["old_lists"] = old.locale_config_lists(paths, read)
    except subprocess.TimeoutExpired:
        res["status"] = "timeout"
    except Exception as exc:  # record, keep going
        res["status"] = ("error: %r" % (exc,))[:240]
    finally:
        res["seconds"] = round(time.time() - t0, 1)
        if s:
            shutil.rmtree(os.path.dirname(s), ignore_errors=True)
    return res


def wait_for_prereg(minutes, say):
    end = time.time() + minutes * 60
    while True:
        try:
            text = h.fetch_text(PREREG_URL).decode("utf-8")
            if PREREG_MARK in text:
                return hashlib.sha256(text.encode("utf-8")).hexdigest()
        except OSError:
            pass
        if time.time() > end:
            return None
        say("waiting for PREREG.md")
        time.sleep(120)


def csv_rows(url):
    return list(csv.DictReader(io.StringIO(h.fetch_text(url).decode("utf-8"))))


def grade_sample0190(results, labels):
    by_repo = {r["repo"]: r for r in results}
    rows, kept, missing, read = [], 0, [], 0
    for lab in labels:
        res = by_repo.get(lab["repo"])
        ok = res is not None and res["status"] == "ok"
        now = ok and (lab["code"], lab["language"]) in flag_set(res["lists"])
        before = ok and (lab["code"], lab["language"]) in flag_set(res["old_lists"])
        rows.append({"repo": lab["repo"], "code": lab["code"], "language": lab["language"],
                     "label": lab["label"], "borderline": lab["borderline"],
                     "status": res["status"] if res else "not run",
                     "commit": res["commit"] if res else "",
                     "reported_0190": "yes" if before else "no" if ok else "",
                     "reported_0200": "yes" if now else "no" if ok else ""})
        if lab["label"] == "real" and lab["borderline"] == "no" and ok:
            read += 1
            if now:
                kept += 1
            else:
                missing.append("%s %s %s" % (lab["repo"].rsplit("/", 1)[-1], lab["code"],
                                             lab["language"]))
    if read < R4_MIN_READ:
        r4 = "NOT TESTABLE (%d real findings read)" % read
    else:
        r4 = "HELD" if len(missing) <= R4_MAX_MISSING else "FAILED"
    absent = []
    for url, code, lang in R5_ABSENT:
        res = by_repo.get(url)
        if res is None or res["status"] != "ok":
            absent.append(None)
        else:
            absent.append((code, lang) not in flag_set(res["lists"]))
    r5 = ("NOT TESTABLE (not read)" if None in absent
          else "HELD" if all(absent) else "FAILED")
    return rows, r4, r5, {"R4_read": read, "R4_kept": kept, "R4_missing": missing,
                          "R5_absent": absent}


def main(new, old, out, say, workers=6, prereg_wait_minutes=360):
    started = time.time()
    prereg_sha = wait_for_prereg(prereg_wait_minutes, say)
    if not prereg_sha:
        say("PREREG.md not public; stopping before reading any repository")
        return 4
    say("prereg sha256 %s" % prereg_sha)
    held, n_drift, n_used = h.population(say)
    sample0190 = csv_rows(SAMPLE0190_URL)
    labels = csv_rows(LABELS0190_URL)
    s_commit = {}
    for r in sample0190:
        s_commit.setdefault(r["repo"], r["commit"])
    say("0.19.0 sample repos %d, label rows %d" % (len(s_commit), len(labels)))

    jobs = ([("regression", u, c) for u, c, _, _ in h.REGRESSION]
            + [("sample0190", u, c) for u, c in sorted(s_commit.items())]
            + [("heldout", u, None) for u in held if u not in s_commit])
    tmp_root = tempfile.mkdtemp(prefix="lc0200-")
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(lambda j: dict(analyse_both(new, old, j[1], j[2], tmp_root),
                                             set=j[0]), jobs))
    shutil.rmtree(tmp_root, ignore_errors=True)
    reg = [r for r in results if r["set"] == "regression"]
    s90 = [r for r in results if r["set"] == "sample0190"]
    held_res = [r for r in results if r["set"] == "heldout"]

    with open(os.path.join(out, "results.jsonl"), "w", encoding="utf-8", errors="replace") as fh:
        for r in results:
            row = {"set": r["set"], "repo": r["repo"], "status": r["status"],
                   "commit": r["commit"], "seconds": r.get("seconds"),
                   "lists": [{k: x.get(k) for k in ("manifest", "xml", "status", "listed",
                                                    "default", "filters", "orphans", "phantoms",
                                                    "phantoms_elsewhere")}
                             for x in r["lists"]],
                   "findings_0200": sorted("%s:%s" % c for c in flag_set(r["lists"])),
                   "findings_0190": sorted("%s:%s" % c for c in flag_set(r["old_lists"]))}
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    reg_rows, verdicts, reg_counts = h.grade_regression(reg)
    h.write_csv(os.path.join(out, "regression.csv"),
                ["repo", "commit", "status", "expect", "languages", "pass", "findings"], reg_rows)

    s_rows, verdicts["R4"], verdicts["R5"], s_counts = grade_sample0190(s90, labels)
    h.write_csv(os.path.join(out, "sample0190.csv"),
                ["repo", "commit", "status", "code", "language", "label", "borderline",
                 "reported_0190", "reported_0200"], s_rows)

    # Held-out repositories: old versus new findings, and the fresh sample for the hand check.
    read_ok = [r for r in held_res if r["status"] == "ok"]
    diff_rows, all_new = [], []
    for r in read_ok:
        a, b = flag_set(r["old_lists"]), flag_set(r["lists"])
        why = {x["xml"]: x["phantoms"] for x in r["lists"]}
        for code, lang in sorted(a | b):
            diff_rows.append({"repo": r["repo"], "commit": r["commit"], "code": code,
                              "language": lang, "in_0190": "yes" if (code, lang) in a else "no",
                              "in_0200": "yes" if (code, lang) in b else "no",
                              "phantom_check_0200": " | ".join(sorted(set(why.values())))})
        for x in r["lists"]:
            for p in x["problems"]:
                if p["code"] in h.FLAG_CODES:
                    all_new.append({"repo": r["repo"], "commit": r["commit"], "xml": x["xml"],
                                    "code": p["code"], "language": p.get("key", ""),
                                    "message": p["message"]})
    h.write_csv(os.path.join(out, "heldout-diff.csv"),
                ["repo", "commit", "code", "language", "in_0190", "in_0200",
                 "phantom_check_0200"], diff_rows)
    h.write_csv(os.path.join(out, "findings.csv"),
                ["repo", "commit", "xml", "code", "language", "message"], all_new)

    flagged = [r for r in read_ok if flag_set(r["lists"])]
    sample_rows = []
    if len(read_ok) < GATE_HELDOUT_READ:
        verdicts["H2"] = verdicts["H3"] = (
            "NOT TESTABLE (gate: %d held-out repositories read)" % len(read_ok))
    else:
        picked = sorted(flagged, key=lambda r: key(r["repo"]))[:SAMPLE_REPOS]
        for i, r in enumerate(picked, 1):
            fs = [f for f in all_new if f["repo"] == r["repo"]]
            fs.sort(key=lambda f: key("finding", r["repo"], f["xml"], f["code"], f["language"]))
            for f in fs[:FINDINGS_PER_REPO]:
                sample_rows.append(dict(f, sample=i, label="", note=""))
        verdicts["H2"] = verdicts["H3"] = (
            "PENDING HAND CHECK (%d repositories)" % len(picked) if len(picked) >= HAND_MIN
            else "NOT TESTABLE (sample of %d)" % len(picked))
    h.write_csv(os.path.join(out, "sample.csv"),
                ["sample", "repo", "commit", "xml", "code", "language", "message", "label",
                 "note"], sample_rows)

    def count(rows, code, col):
        return sum(1 for d in rows if d["code"] == code and d[col] == "yes")

    lists = [x for r in read_ok for x in r["lists"]]
    phantom_status = {}
    for x in lists:
        k = x["phantoms"].split(" (")[0]
        phantom_status[k] = phantom_status.get(k, 0) + 1
    summary = {
        "verdicts": verdicts, "prereg_sha256": prereg_sha,
        "guard_versions": [new.__version__, old.__version__],
        "census_drift_repos": n_drift, "census_sample_repos": n_used,
        "sample0190_repos": len(s90), "sample0190_read": sum(1 for r in s90 if r["status"] == "ok"),
        "heldout_repos": len(held_res), "heldout_read": len(read_ok),
        "heldout_flagged_0200": len(flagged),
        "heldout_flagged_0190": sum(1 for r in read_ok if flag_set(r["old_lists"])),
        "heldout_status": dict(sorted({s: sum(1 for r in held_res if r["status"] == s)
                                       for s in {r["status"] for r in held_res}}.items())),
        "regression": reg_counts, "sample0190": s_counts,
        "exploratory": {
            "findings": {c.split("-")[-1]: {"0190": count(diff_rows, c, "in_0190"),
                                            "0200": count(diff_rows, c, "in_0200")}
                         for c in h.FLAG_CODES},
            "lists": len(lists),
            "phantom_check_0200": dict(sorted(phantom_status.items())),
            "lists_with_phantoms_elsewhere": sum(1 for x in lists if x.get("phantoms_elsewhere")),
        },
        "minutes": round((time.time() - started) / 60, 1),
    }
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8", errors="replace") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1, sort_keys=True)
    say(json.dumps(verdicts))
    return 0
