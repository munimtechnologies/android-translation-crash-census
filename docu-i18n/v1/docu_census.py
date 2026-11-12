# docu-i18n census v1: Docusaurus sites whose translations are never built.
#
# Population (fixed in PREREG.md): GitHub repositories named as `source` in the Docusaurus
# showcase (website/src/data/users.tsx at a pinned commit), plus GitHub repository search
# results for topic:docusaurus and for the Docusaurus template's README sentence
# "built using Docusaurus" (non-fork, non-archived, at least 2 stars). Each repository is
# cloned at HEAD (blobless, depth 1); every docusaurus.config.{js,ts,mjs,cjs,mts} outside
# examples, templates, tests and node_modules is read without running it (docu_core), the
# folders under its i18n folder are classified, and the Markdown files of every folder that is
# not a configured locale's are compared with their English sources.
# The job waits until PREREG.md (marker "docu-i18n census PREREG v1") is public.
# Usage: python3 -B docu_census.py <out folder>
# Made with AI agents by MV2 of Munim, Inc. Apache-2.0.
import concurrent.futures
import csv
import hashlib
import io
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import docu_core as dc  # noqa: E402

CENSUS = ("https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/"
          "main/")
PREREG_URL = CENSUS + "docu-i18n/v1/PREREG.md"
PREREG_MARK = "docu-i18n census PREREG v1"
SHOWCASE = ("https://raw.githubusercontent.com/facebook/docusaurus/"
            "c4a39d6c0cfd7148b818e1ddc7454cdd646817ba/website/src/data/users.tsx")
QUERIES = [
    "topic:docusaurus fork:false archived:false stars:>=2",
    '"built using Docusaurus" in:readme fork:false archived:false stars:>=20',
    '"built using Docusaurus" in:readme fork:false archived:false stars:5..19',
    '"built using Docusaurus" in:readme fork:false archived:false stars:2..4',
]
KEY = "docu-i18n census v1"
UA = {"User-Agent": "docu-i18n-census (MV2, Munim, Inc.; mv2@munimtech.com)",
      "Accept": "application/vnd.github+json"}
WAIT_SECONDS = 8 * 3600
MAX_REPOS = 3000
MAX_SITES_PER_REPO = 3
MAX_MD_SAMPLE = 25
SUBSTANTIVE = 3
MAX_BYTES = 3000000
WORKERS = 6
GATE_SITES = 500
GATE_FOLDER_SITES = 40
SAMPLE_N = 12
SAMPLE_MISMATCH = 4
CONFIG_RE = re.compile(r"(^|/)docusaurus\.config\.(js|ts|mjs|cjs|mts)$")
NOT_SITE = frozenset(["node_modules", "example", "examples", "template", "templates", "test",
                      "tests", "__tests__", "fixtures", "__fixtures__", "e2e", "vendor",
                      "create-docusaurus", "third_party"])
SUMMARY = {"verdicts": {}}
LOG = []


def say(msg):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    LOG.append(line)


def write(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def get(url, tries=6, wait=15):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            last = "HTTP %d" % e.code
            if e.code in (403, 429):
                time.sleep(65)
                continue
        except Exception as e:  # network errors: retry
            last = repr(e)
        time.sleep(wait * (i + 1))
    raise RuntimeError("%s: %s" % (url, last))


def wait_for(url, text, what):
    start = time.time()
    while True:
        try:
            data = get(url, tries=2)
        except RuntimeError as e:
            data = None
            say("waiting for %s: %s" % (what, e))
        if data is not None and text in data.decode("utf-8", "replace"):
            say("%s is live" % what)
            return data
        if time.time() - start > WAIT_SECONDS:
            raise SystemExit("%s not live after %d s" % (what, WAIT_SECONDS))
        time.sleep(300)


def git(args, timeout=900):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_LFS_SKIP_SMUDGE="1", GIT_ASKPASS="true")
    return subprocess.run(["git"] + args, env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


# ------------------------------------------------------------------ population

def showcase_repos():
    data = get(SHOWCASE)
    if data is None:
        raise SystemExit("showcase file not found")
    SUMMARY["showcase_sha256"] = hashlib.sha256(data).hexdigest()
    out = {}
    for m in re.finditer(r"source:\s*'https://github\.com/([^/'\s]+)/([^/'\s#?]+)",
                         data.decode("utf-8", "replace")):
        name = (m.group(1) + "/" + re.sub(r"\.git$", "", m.group(2))).lower()
        out[name] = {"repo": name, "stars": -1, "src": "showcase"}
    return out


def search_repos(q):
    out, total = {}, 0
    for page in range(1, 11):
        url = ("https://api.github.com/search/repositories?q=%s&per_page=100&page=%d"
               "&sort=stars&order=desc" % (urllib.parse.quote(q), page))
        data = get(url)
        time.sleep(7)
        if data is None:
            break
        js = json.loads(data.decode("utf-8"))
        total = js.get("total_count", 0)
        items = js.get("items", [])
        for it in items:
            if it.get("fork") or it.get("archived"):
                continue
            name = it["full_name"].lower()
            out[name] = {"repo": name, "stars": it.get("stargazers_count", 0), "src": "search"}
        if len(items) < 100:
            break
    return out, total


def population():
    pop = {}
    sc = showcase_repos()
    say("showcase: %d GitHub repositories" % len(sc))
    SUMMARY["population"] = {"showcase": len(sc), "queries": {}}
    for q in QUERIES:
        got, total = search_repos(q)
        SUMMARY["population"]["queries"][q] = {"total_count": total, "kept": len(got),
                                               "truncated": total > 1000}
        say("search %r: %d of %d" % (q, len(got), total))
        for k, v in got.items():
            if k in pop:
                pop[k]["stars"] = max(pop[k]["stars"], v["stars"])
            else:
                pop[k] = dict(v)
    for k, v in sc.items():
        if k in pop:
            pop[k]["src"] = "showcase+search"
        else:
            pop[k] = v
    rows = sorted(pop.values(), key=lambda r: (-r["stars"] if r["stars"] >= 0 else 0, r["repo"]))
    showcase_first = [r for r in rows if "showcase" in r["src"]]
    rest = [r for r in rows if "showcase" not in r["src"]]
    rows = (showcase_first + rest)[:MAX_REPOS]
    SUMMARY["population"]["total"] = len(pop)
    SUMMARY["population"]["used"] = len(rows)
    say("population: %d repositories (%d used)" % (len(pop), len(rows)))
    return rows


# ------------------------------------------------------------------ one repository

def site_configs(paths):
    found = []
    for p in paths:
        if not CONFIG_RE.search(p):
            continue
        parts = p.split("/")[:-1]
        if any(x.lower() in NOT_SITE for x in parts):
            continue
        found.append(p)
    found.sort(key=lambda p: (p.count("/"), p))
    return found[:MAX_SITES_PER_REPO]


def analyse(entry, tmp_root):
    repo = entry["repo"]
    res = {"repo": repo, "src": entry["src"], "stars": entry["stars"], "status": "ok",
           "commit": "", "sites": [], "folders": []}
    t0 = time.time()
    d = tempfile.mkdtemp(dir=tmp_root)
    try:
        s = os.path.join(d, "s")
        r = git(["clone", "--quiet", "--depth", "1", "--filter=blob:none", "--no-checkout",
                 "--single-branch", "https://github.com/%s.git" % repo, s])
        if r.returncode != 0:
            raise RuntimeError("clone failed: " + ((r.stderr.strip().splitlines() or [""])[-1])
                               [:160])
        res["commit"] = git(["-C", s, "rev-parse", "HEAD"]).stdout.strip()
        lt = git(["-C", s, "ls-tree", "-r", "-z", "--name-only", "HEAD"])
        if lt.returncode != 0:
            raise RuntimeError("ls-tree failed")
        paths = [p for p in lt.stdout.split("\0") if p]
        pset = set(paths)
        configs = site_configs(paths)
        if not configs:
            res["status"] = "no-config"
            return res
        extra = [p for p in paths if p in ("package.json", "netlify.toml", "vercel.json")
                 or (p.startswith(".github/workflows/") and p.endswith((".yml", ".yaml")))]
        crowdin = any(p.rsplit("/", 1)[-1] in ("crowdin.yml", "crowdin.yaml") for p in paths)
        need = set(configs) | set(extra)
        for c in configs:
            site = c.rpartition("/")[0]
            for n in ("package.json", "netlify.toml", "vercel.json"):
                p = (site + "/" + n) if site else n
                if p in pset:
                    need.add(p)
        checkout(s, sorted(need))

        def read(p):
            fp = os.path.join(s, *p.split("/"))
            try:
                if os.path.getsize(fp) > MAX_BYTES:
                    return None
                with open(fp, "rb") as fh:
                    return fh.read().decode("utf-8", "replace")
            except OSError:
                return None

        cli_texts = [read(p) or "" for p in sorted(need) if p not in configs]
        for c in configs:
            site = c.rpartition("/")[0]
            cfg = dc.parse_config(read(c) or "")
            srow = {"repo": repo, "commit": res["commit"], "config": c, "status": cfg["status"],
                    "why": cfg["why"], "default_locale": cfg["default_locale"],
                    "locales": " ".join(cfg["locales"]), "i18n_path": cfg["i18n_path"],
                    "folders": "", "n_folders": 0, "crowdin": "yes" if crowdin else "no"}
            res["sites"].append(srow)
            if cfg["status"] == "unparsed":
                continue
            i18n_dir = (site + "/" if site else "") + cfg["i18n_path"]
            pre = i18n_dir + "/"
            folders = sorted({p[len(pre):].split("/", 1)[0] for p in paths
                              if p.startswith(pre) and "/" in p[len(pre):]})
            srow["folders"] = " ".join(folders)
            srow["n_folders"] = len(folders)
            for row in dc.classify(cfg, folders):
                f = row["folder"]
                frow = {"repo": repo, "commit": res["commit"], "config": c, "site": site,
                        "i18n_dir": i18n_dir, "folder": f, "cls": row["cls"],
                        "locale": row["locale"], "default_locale": cfg["default_locale"],
                        "listed": " ".join(cfg["locales"]), "n_files": 0, "n_md": 0,
                        "sampled_md": 0, "translated_md": 0, "english_copy_md": 0,
                        "unmatched_md": 0, "code_json": "no", "substantive": "",
                        "commented": "", "mentioned": "", "cli": "",
                        "crowdin": "yes" if crowdin else "no"}
                if f:
                    fpre = pre + f + "/"
                    files = [p for p in paths if p.startswith(fpre)]
                    frow["n_files"] = len(files)
                    md = [p for p in files if p.endswith((".md", ".mdx"))]
                    frow["n_md"] = len(md)
                    frow["code_json"] = "yes" if (fpre + "code.json") in pset else "no"
                if f and row["cls"] not in ("configured",):
                    content(s, read, pset, site, fpre, md, frow)
                    frow["commented"] = "yes" if dc.quoted_in(cfg["comments"], f) else "no"
                    frow["mentioned"] = "yes" if dc.quoted_in(cfg["code"], f) else "no"
                    frow["cli"] = "yes" if dc.cli_mentions(cli_texts, f) else "no"
                res["folders"].append(frow)
    except subprocess.TimeoutExpired:
        res["status"] = "timeout"
    except Exception as exc:  # record, keep going
        res["status"] = ("error: %r" % (exc,))[:240]
    finally:
        res["seconds"] = round(time.time() - t0, 1)
        shutil.rmtree(d, ignore_errors=True)
    return res


def checkout(s, paths):
    for i in range(0, len(paths), 100):
        r = git(["--literal-pathspecs", "-C", s, "checkout", "-q", "HEAD", "--"]
                + paths[i:i + 100], timeout=1800)
        if r.returncode != 0:
            raise RuntimeError("checkout failed: " + r.stderr.strip()[:160])


def content(s, read, pset, site, fpre, md, frow):
    pairs = []
    for p in md:
        rel = p[len(fpre):]
        eng = next((c for c in dc.english_candidates(site, rel) if c in pset), None)
        if eng is None:
            frow["unmatched_md"] += 1
        else:
            pairs.append((p, eng))
    rng = random.Random(KEY + frow["repo"] + fpre)
    if len(pairs) > MAX_MD_SAMPLE:
        pairs = sorted(rng.sample(pairs, MAX_MD_SAMPLE))
    if pairs:
        checkout(s, sorted({x for pr in pairs for x in pr}))
    for p, eng in pairs:
        a, b = read(p), read(eng)
        if a is None or b is None:
            continue
        frow["sampled_md"] += 1
        if dc.squash(a) == dc.squash(b):
            frow["english_copy_md"] += 1
        else:
            frow["translated_md"] += 1
    frow["substantive"] = "yes" if frow["translated_md"] >= SUBSTANTIVE else "no"


# ------------------------------------------------------------------ grading

SITE_COLS = ["repo", "commit", "config", "status", "why", "default_locale", "locales",
             "i18n_path", "n_folders", "folders", "crowdin"]
FOLDER_COLS = ["repo", "commit", "config", "site", "i18n_dir", "folder", "cls", "locale",
               "default_locale", "listed", "n_files", "n_md", "sampled_md", "translated_md",
               "english_copy_md", "unmatched_md", "code_json", "substantive", "commented",
               "mentioned", "cli", "crowdin"]
REPO_COLS = ["repo", "src", "stars", "commit", "status", "seconds", "n_sites"]
SAMPLE_COLS = ["sample"] + FOLDER_COLS + ["verdict", "note"]


def csv_text(cols, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def deliberate(f):
    return f["commented"] == "yes" or f["mentioned"] == "yes" or f["cli"] == "yes"


def grade(results, mech):
    v = {}
    for k in ("K", "K2", "W1", "W2", "W3"):
        v["M-" + k] = mech.get("verdicts", {}).get(k, "NOT TESTABLE (no mech.json)")
    sites = [s for r in results for s in r["sites"] if s["status"] != "unparsed"]
    folders = [f for r in results for f in r["folders"]]
    key = lambda f: (f["repo"], f["config"])  # noqa: E731
    with_folders = {key(f) for f in folders if f["folder"]
                    and f["folder"] != f["default_locale"]}
    SUMMARY["counts"] = {
        "repos": len(results),
        "repos_ok": sum(1 for r in results if r["status"] in ("ok", "no-config")),
        "repos_with_config": sum(1 for r in results if r["sites"]),
        "sites": sum(len(r["sites"]) for r in results),
        "sites_parsed": len(sites),
        "sites_unparsed": sum(1 for r in results for s in r["sites"]
                              if s["status"] == "unparsed"),
        "sites_with_folders": len(with_folders),
        "folders_by_class": {}}
    for f in folders:
        c = SUMMARY["counts"]["folders_by_class"]
        c[f["cls"]] = c.get(f["cls"], 0) + 1
    gate = len(sites) >= GATE_SITES and len(with_folders) >= GATE_FOLDER_SITES
    v["G"] = ("HELD" if gate else "FAILED") + " (%d parsed sites, %d with a non-default i18n " \
        "folder)" % (len(sites), len(with_folders))
    if not gate:
        for k in ("P1", "P2", "P3"):
            v[k] = "NOT TESTABLE (gate G failed)"
        return v
    n = len(with_folders)
    orphan_sites = {key(f) for f in folders if f["cls"] == "orphan"
                    and f["substantive"] == "yes"}
    share = len(orphan_sites) / n
    v["P1"] = ("HELD" if 0.05 <= share <= 0.40 else "FAILED") + (
        " (%d of %d sites, %.1f%%)" % (len(orphan_sites), n, 100 * share))
    mm_sub = {key(f) for f in folders if f["cls"] == "mismatch" and f["substantive"] == "yes"}
    mm_any = {key(f) for f in folders if f["cls"] == "mismatch"}
    v["P2"] = ("HELD" if len(mm_sub) >= 1 and len(mm_any) <= 0.10 * n else "FAILED") + (
        " (%d sites with a substantive mismatch folder; %d of %d with any mismatch folder)"
        % (len(mm_sub), len(mm_any), n))
    subs = [f for f in folders if f["cls"] == "orphan" and f["substantive"] == "yes"]
    if len(subs) < 5:
        v["P3"] = "NOT TESTABLE (%d substantive orphan folders)" % len(subs)
    else:
        dl = sum(1 for f in subs if deliberate(f))
        v["P3"] = ("HELD" if 2 * dl <= len(subs) else "FAILED") + (
            " (%d of %d substantive orphan folders carry a deliberate signal)" % (dl, len(subs)))
    return v


def sample(results):
    folders = [f for r in results for f in r["folders"] if f["substantive"] == "yes"
               and f["cls"] in ("orphan", "mismatch")]
    rng = random.Random(KEY)
    mm = sorted((f for f in folders if f["cls"] == "mismatch"),
                key=lambda f: (f["repo"], f["config"], f["folder"]))
    pick = rng.sample(mm, min(SAMPLE_MISMATCH, len(mm)))
    orph = sorted((f for f in folders if f["cls"] == "orphan"),
                  key=lambda f: (f["repo"], f["config"], f["folder"]))
    pick += rng.sample(orph, min(SAMPLE_N - len(pick), len(orph)))
    return [dict(f, sample=i, verdict="", note="") for i, f in enumerate(pick, 1)]


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/out"
    os.makedirs(out, exist_ok=True)
    try:
        _run(out)
    finally:
        write(os.path.join(out, "summary.json"),
              json.dumps(SUMMARY, indent=1, sort_keys=True) + "\n")
        write(os.path.join(out, "report.txt"), "\n".join(LOG) + "\n")


def _run(out):
    prereg = wait_for(PREREG_URL, PREREG_MARK, "PREREG.md")
    SUMMARY["prereg_sha256"] = hashlib.sha256(prereg).hexdigest()
    say("prereg sha256 %s" % SUMMARY["prereg_sha256"])
    mech = {}
    mp = os.path.join(out, "mech.json")
    if os.path.exists(mp):
        with open(mp, encoding="utf-8") as fh:
            mech = json.load(fh)
    tmp_root = tempfile.mkdtemp(prefix="docu-")
    entries = population()
    write(os.path.join(out, "population.csv"),
          csv_text(["repo", "src", "stars"], entries))
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = [ex.submit(analyse, e, tmp_root) for e in entries]
        for i, fut in enumerate(concurrent.futures.as_completed(futs), 1):
            results.append(fut.result())
            if i % 100 == 0 or i == len(futs):
                say("%d of %d repositories done" % (i, len(futs)))
    results.sort(key=lambda r: r["repo"])
    for r in results:
        r["n_sites"] = len(r["sites"])
    write(os.path.join(out, "repos.csv"), csv_text(REPO_COLS, results))
    write(os.path.join(out, "sites.csv"),
          csv_text(SITE_COLS, [s for r in results for s in r["sites"]]))
    write(os.path.join(out, "folders.csv"),
          csv_text(FOLDER_COLS, [f for r in results for f in r["folders"]]))
    SUMMARY["verdicts"] = grade(results, mech)
    write(os.path.join(out, "sample.csv"), csv_text(SAMPLE_COLS, sample(results)))
    say(json.dumps(SUMMARY["verdicts"], sort_keys=True))
    say(json.dumps(SUMMARY["counts"], sort_keys=True))
    shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    main()
