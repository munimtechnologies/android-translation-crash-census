# Pre-registered tests of the l10n-guard 0.19.0 locale-config check (see PREREG.md):
# a regression set (the 16 hand-checked lists of the locale-config census, at the commits
# that were checked) and a held-out set (every other repository where the census found a
# drifting list, at today's HEAD). Made with AI agents by MV2 of Munim, Inc. Apache-2.0.
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
import urllib.request

CENSUS = ("https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/"
          "main/")
LISTS_URL = CENSUS + "locale-config/lists.csv"
SAMPLE_URL = CENSUS + "locale-config/sample.csv"
PREREG_URL = CENSUS + "l10n-guard-0190/PREREG.md"
PREREG_MARK = "l10n-guard 0.19.0 locale-config PREREG v1"
SPARSE = ["**/AndroidManifest.xml", "*.gradle", "*.gradle.kts", "**/res/xml/*.xml",
          "**/resources.properties", "**/res/values*/*.xml", "**/buildSrc/**",
          "**/build-logic/**"]
MAX_BYTES = 2000000
FLAG_CODES = ("locale-config-orphan", "locale-config-phantom", "locale-config-code")
KEY = "l10n-guard 0.19 holdout v1"

# Pre-registered numbers (PREREG.md).
GATE_HELDOUT_READ = 60
H1_LOW = (3, 5)      # flagged / read >= 3/5
H1_HIGH = (9, 10)    # flagged / read <= 9/10
SAMPLE_REPOS = 16
FINDINGS_PER_REPO = 3
HAND_MIN = 8

O, P, C = "locale-config-orphan", "locale-config-phantom", "locale-config-code"
# The census's hand check (locale-config/labels.csv): repo -> (commit, expectation).
REGRESSION = [
    ("https://codeberg.org/comaps/comaps", "3d8dd77a81897d8e9528bcdd3442dfd518613c79",
     "absent", [(O, "eo"), (O, "hr"), (O, "lo")]),
    ("https://github.com/Toum404/Croustillapp", "0778350e1a4da3460a37a90ff328e46e3ce82dbe",
     "absent", [(P, "fr")]),
    ("https://github.com/michaelWuensch/BitBanana", "a30cbd7fef2d8643fcbbcfa72484a888f4146678",
     "any", [(O, "sv")]),
    ("https://github.com/Razeeman/Android-SimpleTimeTracker",
     "60ad644f16724dcf0760a0d2019e5b53843a8d8c", "absent", "all"),
    ("https://codeberg.org/prav/prav", "1d5d291c5bf4b57ca98d0fac462dc99b72f54255",
     "any", [(P, "hi"), (O, "et")]),
    ("https://github.com/DerGoogler/MMRL", "6c2b778867f7f66ee2d208ee82887aa2cf9bb0bb",
     "any", [(O, "ta")]),
    ("https://github.com/juanro49/autu-mandu", "068457ef2064ab2c56592cf474f05adb36612535",
     "any", [(P, "uk"), (O, "zh")]),
    ("https://github.com/MuntashirAkon/AppManager", "dc4154f4c04399602895f31f9390bb66b25ea8a0",
     "any", [(O, "nl"), (O, "sv")]),
    ("https://github.com/Crazy-Marvin/Flashy", "9e0a426eb2649e97af93c3217c166b7b136ae09a",
     "any", [(O, "de"), (O, "es"), (O, "ru"), (O, "sat"), (O, "zh")]),
    ("https://github.com/urikdev/Urik", "d096280c7e0d8b86d3b31e4ca433f44681b5c024",
     "any", [(O, "bg")]),
    ("https://github.com/MarcusWolschon/osmeditor4android",
     "f018ef2e54aa4bafde49ebe16a9d2f7944fd08e5", "any", [(P, "kn"), (P, "oc")]),
    ("https://github.com/spaceapi-community/my-hackerspace",
     "861dfb6c1384ff8a59fe084fd3e47e27132c10a2", "any", [(C, "dk"), (O, "da")]),
    ("https://github.com/sky-map-team/stardroid", "dfc35a7f6f4e5acc0848f734cf2d9f0ecbe9c958",
     "any", [(O, "gl")]),
    ("https://github.com/idunnololz/summit", "3346afc4a3d7c2554df6be6cee5f4cbc3bbe48ba",
     "any", [(O, "pt"), (O, "tr")]),
    ("https://github.com/demosten-com/SrednaBG", "c5038420b10d580aaae36d07181a6f775c598eb7",
     "absent", [(P, "bg")]),
    ("https://github.com/plainhub/plain-app", "ae64c4b9339520cf445a62179d4be2e12726a87a",
     "any", [(O, "tr"), (O, "vi")]),
]
# Orphans the census reported that the build's localeFilters drop (hand check): R3.
FILTERED = [("https://github.com/DerGoogler/MMRL", lang) for lang in "fa ko lv nl uk".split()]
FILTERED += [("https://github.com/Crazy-Marvin/Flashy", lang)
             for lang in "ca fr gl id it ja pl sv ta th uk ur".split()]


def git(args, timeout=300):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_LFS_SKIP_SMUDGE="1", GIT_ASKPASS="true")
    return subprocess.run(["git"] + args, env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def fetch_text(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "l10n-guard-0.19-holdout (MV2, Munim, Inc.; mv2@munimtech.com)"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def checkout(url, ref, tmp_root):
    """Sparse checkout of one commit (ref = a sha, or None for HEAD). Returns (dir, commit,
    paths) or raises RuntimeError."""
    d = tempfile.mkdtemp(dir=tmp_root)
    s = os.path.join(d, "s")
    git(["init", "--quiet", s])
    git(["-C", s, "remote", "add", "origin", url])
    want = ref or "HEAD"
    r = git(["-C", s, "fetch", "--quiet", "--depth", "1", "--filter=blob:none", "origin", want])
    commit = None
    if r.returncode == 0:
        commit = git(["-C", s, "rev-parse", "FETCH_HEAD"]).stdout.strip()
    elif ref:
        # Some servers refuse a commit by hash; HEAD is used only if it is that same commit.
        r2 = git(["-C", s, "fetch", "--quiet", "--depth", "1", "--filter=blob:none", "origin",
                  "HEAD"])
        head = git(["-C", s, "rev-parse", "FETCH_HEAD"]).stdout.strip() if r2.returncode == 0 else ""
        if head == ref:
            commit = ref
    if not commit:
        raise RuntimeError("fetch failed: " + ((r.stderr.strip().splitlines() or [""])[-1])[:200])
    lt = git(["-C", s, "ls-tree", "-r", "-z", "--name-only", commit])
    if lt.returncode != 0:
        raise RuntimeError("ls-tree failed: " + lt.stderr.strip()[:200])
    paths = [p for p in lt.stdout.split("\0") if p]
    git(["-C", s, "config", "core.sparseCheckout", "true"])
    git(["-C", s, "config", "core.sparseCheckoutCone", "false"])
    with open(os.path.join(s, ".git", "info", "sparse-checkout"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(SPARSE) + "\n")
    co = git(["-C", s, "checkout", "--quiet", commit], timeout=900)
    if co.returncode != 0:
        raise RuntimeError("checkout failed: " + co.stderr.strip()[:200])
    return s, commit, paths


def analyse(guard, url, ref, tmp_root):
    res = {"repo": url, "status": "ok", "commit": "", "lists": []}
    t0 = time.time()
    s = None
    try:
        s, res["commit"], paths = checkout(url, ref, tmp_root)
        manifests = [p for p in paths if p.endswith("AndroidManifest.xml")]
        if manifests and not any(os.path.isfile(os.path.join(s, *p.split("/"))) for p in manifests):
            res["status"] = "sparse checkout empty"
            return res

        def read(p):
            fp = os.path.join(s, *p.split("/"))
            try:
                if not os.path.isfile(fp) or os.path.getsize(fp) > MAX_BYTES:
                    return None
                with open(fp, "rb") as fh:
                    return fh.read()
            except OSError:
                return None

        res["lists"] = guard.locale_config_lists(paths, read)
    except subprocess.TimeoutExpired:
        res["status"] = "timeout"
    except Exception as exc:  # record, keep going
        res["status"] = "error: %r" % (exc,)
        res["status"] = res["status"][:240]
    finally:
        res["seconds"] = round(time.time() - t0, 1)
        if s:
            shutil.rmtree(os.path.dirname(s), ignore_errors=True)
    return res


def findings(res):
    return [(p["code"], p.get("key", ""), r["xml"], p["message"])
            for r in res["lists"] for p in r["problems"]]


def flagged(res):
    return any(code in FLAG_CODES for code, _, _, _ in findings(res))


def key(*parts):
    return hashlib.sha256("|".join((KEY,) + parts).encode("utf-8")).hexdigest()


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


def grade_regression(results):
    by_repo = {r["repo"]: r for r in results}
    rows, r1, r2 = [], [], []
    for url, commit, kind, langs in REGRESSION:
        res = by_repo[url]
        got = {(code, lang) for code, lang, _, _ in findings(res) if code in FLAG_CODES}
        if res["status"] != "ok":
            ok = None
        elif kind == "absent":
            ok = not got if langs == "all" else not (got & set(langs))
        else:
            ok = bool(got & set(langs))
        (r1 if kind == "absent" else r2).append(ok)
        rows.append({"repo": url, "commit": res["commit"], "status": res["status"],
                     "expect": kind, "languages": "all" if langs == "all" else
                     " ".join("%s:%s" % (c.split("-")[-1], l) for c, l in langs),
                     "pass": {True: "yes", False: "no", None: "not read"}[ok],
                     "findings": " ".join(sorted("%s:%s" % (c.split("-")[-1], l)
                                                 for c, l in got))})
    filtered_hits = []
    for url, lang in FILTERED:
        got = {(c, l) for c, l, _, _ in findings(by_repo[url])}
        if (O, lang) in got:
            filtered_hits.append("%s:%s" % (url.rsplit("/", 1)[1], lang))
    r1_read = [x for x in r1 if x is not None]
    r2_read = [x for x in r2 if x is not None]
    r3_read = all(by_repo[u]["status"] == "ok" for u in {u for u, _ in FILTERED})
    v = {}
    # R1: every debunked row that could be read is clean (at least 3 of 4 read).
    v["R1"] = ("NOT TESTABLE (%d of 4 read)" % len(r1_read) if len(r1_read) < 3
               else "HELD" if all(r1_read) else "FAILED")
    # R2: of the confirmed rows that could be read (at least 10 of 12), all but one flagged.
    v["R2"] = ("NOT TESTABLE (%d of 12 read)" % len(r2_read) if len(r2_read) < 10
               else "HELD" if sum(1 for x in r2_read if not x) <= 1 else "FAILED")
    # R3: none of the filtered-out orphans reported (MMRL and Flashy both read).
    v["R3"] = ("NOT TESTABLE (MMRL or Flashy not read)" if not r3_read
               else "HELD" if not filtered_hits else "FAILED")
    counts = {"R1_pass": sum(1 for x in r1_read if x), "R1_read": len(r1_read), "R1_of": len(r1),
              "R2_pass": sum(1 for x in r2_read if x), "R2_read": len(r2_read), "R2_of": len(r2),
              "R3_filtered_reported": filtered_hits, "R3_of": len(FILTERED)}
    return rows, v, counts


def population(say):
    lists = list(csv.DictReader(io.StringIO(fetch_text(LISTS_URL).decode("utf-8"))))
    sample = list(csv.DictReader(io.StringIO(fetch_text(SAMPLE_URL).decode("utf-8"))))
    used = {r["repo"] for r in sample}
    drift = sorted({r["repo"] for r in lists if r["drift"] == "yes"})
    held = [u for u in drift if u not in used]
    say("census drift repos %d, census sample %d, held out %d" % (len(drift), len(used), len(held)))
    return held, len(drift), len(used)


def write_csv(path, cols, rows):
    with open(path, "w", encoding="utf-8", errors="replace", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for row in rows:
            w.writerow({c: str(row.get(c, "")).encode("utf-8", "replace").decode("utf-8")
                        for c in cols})


def main(guard, out, say, workers=6, prereg_wait_minutes=360):
    started = time.time()
    prereg_sha = wait_for_prereg(prereg_wait_minutes, say)
    if not prereg_sha:
        say("PREREG.md not public; stopping before reading any repository")
        return 4
    say("prereg sha256 %s" % prereg_sha)
    held, n_drift, n_used = population(say)
    tmp_root = tempfile.mkdtemp(prefix="lc0190-")
    jobs = [(u, c) for u, c, _, _ in REGRESSION] + [(u, None) for u in held]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(lambda j: analyse(guard, j[0], j[1], tmp_root), jobs))
    shutil.rmtree(tmp_root, ignore_errors=True)
    reg, held_res = results[:len(REGRESSION)], results[len(REGRESSION):]

    with open(os.path.join(out, "results.jsonl"), "w", encoding="utf-8", errors="replace") as fh:
        for set_name, rs in (("regression", reg), ("heldout", held_res)):
            for r in rs:
                fh.write(json.dumps(dict(r, set=set_name), ensure_ascii=False, sort_keys=True)
                         + "\n")

    reg_rows, verdicts, reg_counts = grade_regression(reg)
    write_csv(os.path.join(out, "regression.csv"),
              ["repo", "commit", "status", "expect", "languages", "pass", "findings"], reg_rows)

    read_ok = [r for r in held_res if r["status"] == "ok"]
    flag = [r for r in read_ok if flagged(r)]
    all_findings = []
    for r in held_res:
        for code, lang, xml, msg in findings(r):
            all_findings.append({"repo": r["repo"], "commit": r["commit"], "xml": xml,
                                 "code": code, "language": lang, "message": msg})
    write_csv(os.path.join(out, "findings.csv"),
              ["repo", "commit", "xml", "code", "language", "message"], all_findings)

    if len(read_ok) < GATE_HELDOUT_READ:
        verdicts["H1"] = verdicts["H2"] = verdicts["H3"] = (
            "NOT TESTABLE (gate: %d held-out repositories read)" % len(read_ok))
        sample_rows = []
    else:
        lo = len(flag) * H1_LOW[1] >= len(read_ok) * H1_LOW[0]
        hi = len(flag) * H1_HIGH[1] <= len(read_ok) * H1_HIGH[0]
        verdicts["H1"] = "HELD" if lo and hi else "FAILED"
        picked = sorted(flag, key=lambda r: key(r["repo"]))[:SAMPLE_REPOS]
        sample_rows = []
        for i, r in enumerate(picked, 1):
            fs = [f for f in findings(r) if f[0] in FLAG_CODES]
            fs.sort(key=lambda f: key("finding", r["repo"], f[2], f[0], f[1]))
            for code, lang, xml, msg in fs[:FINDINGS_PER_REPO]:
                sample_rows.append({"sample": i, "repo": r["repo"], "commit": r["commit"],
                                    "xml": xml, "code": code, "language": lang,
                                    "message": msg, "label": "", "note": ""})
        state = ("PENDING HAND CHECK (%d repositories)" % len(picked)
                 if len(picked) >= HAND_MIN else "NOT TESTABLE (sample of %d)" % len(picked))
        verdicts["H2"] = verdicts["H3"] = state
    write_csv(os.path.join(out, "sample.csv"),
              ["sample", "repo", "commit", "xml", "code", "language", "message", "label", "note"],
              sample_rows)

    lists = [x for r in read_ok for x in r["lists"]]
    tally = lambda field: dict(sorted(
        {v: sum(1 for x in lists if x[field] == v) for v in {x[field] for x in lists}}.items()))
    summary = {
        "verdicts": verdicts, "prereg_sha256": prereg_sha, "guard_version": guard.__version__,
        "census_drift_repos": n_drift, "census_sample_repos": n_used,
        "heldout_repos": len(held_res), "heldout_read": len(read_ok),
        "heldout_flagged": len(flag),
        "heldout_status": dict(sorted({s: sum(1 for r in held_res if r["status"] == s)
                                       for s in {r["status"] for r in held_res}}.items())),
        "regression": reg_counts,
        "exploratory": {
            "lists": len(lists),
            "list_status": tally("status"),
            "default_how": tally("default_how"),
            "orphan_check": tally("orphans"),
            "phantom_check": tally("phantoms"),
            "filters_none": sum(1 for x in lists if x["filters"] == "none"),
            "filters_unknown": sum(1 for x in lists if x["filters"] == "unknown"),
            "filters_read": sum(1 for x in lists if x["filters"] not in ("none", "unknown", "")),
            "findings_by_code": dict(sorted({c: sum(1 for f in all_findings if f["code"] == c)
                                             for c in {f["code"] for f in all_findings}}.items())),
            "heldout_repos_with_tag_only": sum(1 for r in read_ok if not flagged(r) and findings(r)),
        },
        "minutes": round((time.time() - started) / 60, 1),
    }
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8", errors="replace") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1, sort_keys=True)
    say(json.dumps(verdicts))
    return 0
