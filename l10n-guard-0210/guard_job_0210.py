# Builds l10n-guard 0.21.0 (the new linguas check) in a sealed job and runs its pre-registered
# test (PREREG.md in l10n-guard-0210/ of the census repository):
#   1. waits until PREREG.md is public and l10n-guard 0.20.1 is on main;
#   2. applies block_0210.txt and the exact replacements below to 0.20.1 (each old text must
#      occur once), runs every test module before and after (T);
#   3. R1/R2 on the 12 hand-labelled files of the linguas census, at their recorded commits;
#   4. H1/P1 on a new population: GNOME GitLab (GNOME, World), Xfce GitLab and elementary's
#      GitHub projects that are not in the Flathub census, read at HEAD.
# Nothing is published from here. Made with AI agents by MV2 of Munim, Inc. Apache-2.0.
import concurrent.futures
import csv
import difflib
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import linguas_census as lc  # noqa: E402  (downloaded unchanged from the census repository)

REPO = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, "repo")
OUT = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.join(HERE, "out")
CENSUS = ("https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/"
          "main/")
PREREG_URL = CENSUS + "l10n-guard-0210/PREREG.md"
PREREG_MARK = "l10n-guard 0.21.0 PREREG v1"
KEY = "l10n-guard 0.21.0 linguas v1"
GUARD_RAW = "https://raw.githubusercontent.com/munimtechnologies/l10n-guard/main/l10n_guard.py"
GUARD_TAR = "https://codeload.github.com/munimtechnologies/l10n-guard/tar.gz/refs/heads/main"
UA = "l10n-guard-linguas-test (MV2, Munim, Inc.; mv2@munimtech.com)"
OLD, NEW = "0.20.1", "0.21.0"
NEW_NAMES = ("_LG_SKIP", "_LG_STEM_RE", "_lg_language", "_lg_build", "_lg_translated",
             "check_linguas", "check_linguas_dir")
VERSION_RES = [re.compile(r"(?<=@v)0\.20\.1\b"), re.compile(r"(?<=rev: v)0\.20\.1\b"),
               re.compile(r"(?<===)0\.20\.1\b"), re.compile(r'(?<=version = ")0\.20\.1(?=")'),
               re.compile(r'(?<=version: ")0\.20\.1(?=")')]
BLOCK_ANCHOR = "\ndef _script_maps(kind, source_path, target_path):"

GITLAB_GROUPS = [("gitlab.gnome.org", "GNOME"), ("gitlab.gnome.org", "World"),
                 ("gitlab.xfce.org", "xfce"), ("gitlab.xfce.org", "apps"),
                 ("gitlab.xfce.org", "panel-plugins"), ("gitlab.xfce.org", "thunar-plugins")]
GITHUB_ORGS = ["elementary"]
MAX_PAGES = 60

# Pre-registered numbers (PREREG.md).
R1_MIN, R1_READ_MIN = 8, 8
GATE_GOVERNED, GATE_FLAGGED = 100, 6
SAMPLE_REPOS = 12
P1_MIN_GOVERNED = 50

REPORT = []
SUMMARY = {}

# l10n_guard.py (each old text must occur once).
CODE_REPLACEMENTS = [
    ("docstring",
     "  python3 l10n_guard.py locale-config  path/to/android/project\n",
     "  python3 l10n_guard.py locale-config  path/to/android/project\n"
     "  python3 l10n_guard.py linguas        path/to/gettext/project\n"),
    ("parser",
     '    p = sub.add_parser("locale-config")\n'
     '    p.add_argument("dir")\n',
     '    p = sub.add_parser("locale-config")\n'
     '    p.add_argument("dir")\n'
     '    p = sub.add_parser("linguas")\n'
     '    p.add_argument("dir")\n'),
    ("dispatch",
     '        elif args.kind == "locale-config":\n'
     '            problems, stats = check_locale_config_dir(args.dir)\n',
     '        elif args.kind == "locale-config":\n'
     '            problems, stats = check_locale_config_dir(args.dir)\n'
     '        elif args.kind == "linguas":\n'
     '            problems, stats = check_linguas_dir(args.dir)\n'),
]

README_BULLET = (
    "- **gettext LINGUAS** (0.21.0, new `linguas` kind, codes `linguas-unlisted`,\n"
    "  `linguas-missing`): Meson's `i18n.gettext()` (without `languages:`) and gettext's autotools\n"
    "  rules build only the languages listed in the `LINGUAS` file of a po folder, so a translated\n"
    "  `<lang>.po` beside it that `LINGUAS` leaves out is never compiled or installed, and nothing\n"
    "  warns. `l10n-guard linguas <project folder>` reports such files (`linguas-unlisted`, with how\n"
    "  many messages are translated) and listed languages with no `.po` file (`linguas-missing`).\n"
    "  It reads `LINGUAS` the way each build does (Meson skips lines starting with `#`; gettext\n"
    "  treats `#` as a comment anywhere) and skips folders with an explicit `languages:` list,\n"
    "  vendored and archived folders (`subprojects/`, `old/`...), file names that are not locales\n"
    "  (`it_complete.po`, `en@quot.po`) and files with no translated message. Both are warnings;\n"
    "  use `--strict` to fail a CI step. GNOME's translation platform already warns its\n"
    "  translators about unlisted files; `linguas` brings the check to any repository and CI. In a\n"
    "  pre-registered census of Flathub apps' source repositories, 51 of 526 whose build reads\n"
    "  `LINGUAS` left translations out\n"
    "  ([census](https://github.com/munimtechnologies/android-translation-crash-census/blob/main/linguas/RESULTS.md),\n"
    "  [0.21.0 check](https://github.com/munimtechnologies/android-translation-crash-census/blob/main/l10n-guard-0210/RESULTS.md)).\n")

DOC_REPLACEMENTS = [
    ("README.md", "feature list",
     "- **Apple `.strings` and String Catalogs**: ",
     README_BULLET + "- **Apple `.strings` and String Catalogs**: "),
    ("README.md", "use section",
     "python3 l10n_guard.py locale-config  .   # an Android project folder: per-app language lists\n",
     "python3 l10n_guard.py locale-config  .   # an Android project folder: per-app language lists\n"
     "python3 l10n_guard.py linguas        .   # a gettext project: .po files po/LINGUAS leaves out\n"),
    ("README.md", "action note",
     "The Action takes a source and a target, so the `locale-config` kind runs as a plain step for now:",
     "The Action takes a source and a target, so the `locale-config` and `linguas` kinds run as a "
     "plain step for now:"),
    ("README.md", "action step",
     "    l10n-guard --strict locale-config .\n",
     "    l10n-guard --strict locale-config .\n"
     "    l10n-guard --strict linguas .\n"),
    ("skills/l10n-guard/SKILL.md", "description",
     "Android per-app language lists (locales_config.xml) that drift from the shipped translations.",
     "Android per-app language lists (locales_config.xml) that drift from the shipped translations, "
     "and gettext .po files that po/LINGUAS leaves out so Meson or autotools never builds them."),
    ("skills/l10n-guard/SKILL.md", "table row",
     "   | Android per-app language list (`android:localeConfig`) | `l10n-guard locale-config .` "
     "(a project or module folder) |\n",
     "   | Android per-app language list (`android:localeConfig`) | `l10n-guard locale-config .` "
     "(a project or module folder) |\n"
     "   | gettext built by Meson or autotools (`po/LINGUAS`) | `l10n-guard linguas .` "
     "(a project folder) |\n"),
    ("skills/l10n-guard/SKILL.md", "warning advice",
     "write the tag as `pt-BR`.\n",
     "write the tag as `pt-BR`.\n"
     "   - `linguas-unlisted` (a translated `po/xx.po` that `po/LINGUAS` leaves out, so it is never\n"
     "     built): adding the line is usually right, but first check that the file passes\n"
     "     `msgfmt --check` and that the language was not left out on purpose (a comment in\n"
     "     `LINGUAS`, an unfinished translation). `linguas-missing`: add the `.po` file or remove the\n"
     "     line.\n"),
    ("skills/l10n-guard/SKILL.md", "ci note",
     "  then `l10n-guard --strict locale-config .`.\n",
     "  then `l10n-guard --strict locale-config .` (the `linguas` kind runs the same way).\n"),
    ("skills/l10n-guard/SKILL.md", "limits",
     "- `java-format` was measured against OpenJDK 21's",
     "- `linguas` reads `LINGUAS` as Meson and gettext's autotools rules do but does not run the\n"
     "  build, and it cannot tell a translation left out on purpose from a forgotten one.\n"
     "- `java-format` was measured against OpenJDK 21's"),
]


# ------------------------------------------------------------------ small helpers

def say(line=""):
    print(time.strftime("%H:%M:%S"), line, flush=True)
    REPORT.append(str(line))


def read(path):
    with open(path, encoding="utf-8", newline="", errors="surrogateescape") as fh:
        return fh.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="", errors="surrogateescape") as fh:
        fh.write(text)


def finish(code):
    write(os.path.join(OUT, "report.txt"), "\n".join(REPORT) + "\n")
    write(os.path.join(OUT, "build-summary.json"),
          json.dumps(SUMMARY, indent=1, ensure_ascii=True, sort_keys=True))
    sys.exit(code)


def fail(msg):
    say("PATCH FAILED: " + msg)
    SUMMARY["patch"] = "failed: " + msg
    finish(3)


def key(*parts):
    return hashlib.sha256("|".join((KEY,) + parts).encode("utf-8")).hexdigest()


def fetch(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read()
        except Exception as exc:  # retry, then give up
            last = exc
            time.sleep(5 * (i + 1))
    raise RuntimeError("could not read %s: %r" % (url, last))


def wait_for(url, mark, minutes):
    """The URL's bytes once they contain mark, or None after the given minutes."""
    end = time.time() + minutes * 60
    while True:
        try:
            data = fetch("%s?nocache=%d" % (url, int(time.time())), tries=1)
            if mark.encode("utf-8") in data:
                return data
        except Exception:
            pass
        if time.time() > end:
            return None
        say("waiting for %s" % url)
        time.sleep(300)


def csv_rows(url):
    return list(csv.DictReader(io.StringIO(fetch(url).decode("utf-8-sig"))))


def write_csv(path, cols, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", errors="replace", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(dict((c, "" if row.get(c) is None else str(row.get(c))) for c in cols))


# ------------------------------------------------------------------ build

def repo_files():
    found = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for name in files:
            found.append(os.path.relpath(os.path.join(root, name), REPO).replace(os.sep, "/"))
    return sorted(found)


def run_tests(phase):
    results = {}
    mods = sorted(os.path.splitext(n)[0] for n in os.listdir(REPO)
                  if n.startswith("test_") and n.endswith(".py"))
    for mod in mods:
        try:
            proc = subprocess.run([sys.executable, "-B", "-m", "unittest", mod], cwd=REPO,
                                  capture_output=True, text=True, errors="replace", timeout=900)
            code, log = proc.returncode, proc.stdout + proc.stderr
        except subprocess.TimeoutExpired:
            code, log = "timeout", ""
        ran = re.search(r"Ran (\d+) test", log)
        results[mod] = {"exit": code, "ran": int(ran.group(1)) if ran else None,
                        "tail": log.strip().splitlines()[-4:]}
        write(os.path.join(OUT, "tests", "%s-%s.txt" % (phase, mod)), log[-60000:])
        say("%s %s exit=%s ran=%s" % (phase, mod, code, results[mod]["ran"]))
    return results


def replace_once(rel, text, what, old, new):
    eol = "\r\n" if "\r\n" in text else "\n"
    old, new = old.replace("\n", eol), new.replace("\n", eol)
    if text.count(old) != 1:
        fail("%s %s: old text count %d" % (rel, what, text.count(old)))
    say("replaced: %s %s" % (rel, what))
    return text.replace(old, new)


def patch_code(text, block):
    eol = "\r\n" if "\r\n" in text else "\n"
    for name in NEW_NAMES:
        if name in text:
            fail("name already in l10n_guard.py: " + name)
    text = replace_once("l10n_guard.py", text, "version",
                        '__version__ = "%s"' % OLD, '__version__ = "%s"' % NEW)
    for what, old, new in CODE_REPLACEMENTS:
        text = replace_once("l10n_guard.py", text, what, old, new)
    anchor = BLOCK_ANCHOR.replace("\n", eol)
    if text.count(anchor) != 1:
        fail("block anchor count %d" % text.count(anchor))
    block = block.rstrip("\n").replace("\n", eol)
    text = text.replace(anchor, eol + block + eol + eol + anchor, 1)
    compile(text, "l10n_guard.py", "exec")
    return text


def bump_versions(rel, text):
    changes, lines = [], []
    for line in text.split("\n"):
        new = line
        for rx in VERSION_RES:
            new = rx.sub(NEW, new)
        if new != line:
            changes.append("%s: %r -> %r" % (rel, line.strip(), new.strip()))
        lines.append(new)
    return "\n".join(lines), changes


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def get_repo():
    """Waits for 0.20.1 on main, then downloads and unpacks it into REPO."""
    if not wait_for(GUARD_RAW, '__version__ = "%s"' % OLD, 480):
        say("l10n-guard %s is not on main; stopping" % OLD)
        SUMMARY["patch"] = "not started: %s not on main" % OLD
        finish(4)
    data = fetch(GUARD_TAR)
    if os.path.isdir(REPO):
        shutil.rmtree(REPO)
    os.makedirs(REPO)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for m in tar.getmembers():
            parts = m.name.split("/", 1)
            if len(parts) < 2 or not parts[1] or not (m.isfile() or m.isdir()):
                continue
            if parts[1].startswith("/") or ".." in parts[1].split("/"):
                continue
            target = os.path.join(REPO, *parts[1].split("/"))
            if m.isdir():
                os.makedirs(target, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, "wb") as fh:
                    fh.write(tar.extractfile(m).read())
    SUMMARY["repo_tar_sha256"] = hashlib.sha256(data).hexdigest()


def build():
    files = repo_files()
    originals = dict((rel, read(os.path.join(REPO, rel))) for rel in files
                     if not rel.endswith((".png", ".jpg", ".gif", ".ico")))
    say("repo files: %d" % len(files))
    if '__version__ = "%s"' % OLD not in originals.get("l10n_guard.py", ""):
        fail("l10n_guard.py on main is not %s" % OLD)
    SUMMARY["baseline"] = run_tests("before")
    patched = dict(originals)
    patched["l10n_guard.py"] = patch_code(originals["l10n_guard.py"],
                                          read(os.path.join(HERE, "block_0210.txt")))
    changes = []
    for rel in sorted(originals):
        if rel.endswith(".py"):
            continue
        new, ch = bump_versions(rel, originals[rel])
        patched[rel] = new
        changes += ch
    for rel, what, old, new in DOC_REPLACEMENTS:
        patched[rel] = replace_once(rel, patched[rel], what, old, new)
    for c in changes:
        say("version: " + c)
    left = ["%s:%d: %s" % (rel, n + 1, line.strip())
            for rel in sorted(patched) for n, line in enumerate(patched[rel].split("\n"))
            if OLD in line]
    write(os.path.join(OUT, "still-0201.txt"), "\n".join(left) + "\n")
    say("lines still mentioning %s: %d (see still-0201.txt)" % (OLD, len(left)))
    patched["test_0210.py"] = read(os.path.join(HERE, "test_0210.py"))
    diff = []
    for rel in sorted(patched):
        if patched[rel] != originals.get(rel):
            write(os.path.join(REPO, rel), patched[rel])
            write(os.path.join(OUT, "pkg", rel), patched[rel])
            diff += difflib.unified_diff(originals.get(rel, "").splitlines(True),
                                         patched[rel].splitlines(True), "a/" + rel, "b/" + rel)
    write(os.path.join(OUT, "patch.diff"), "".join(diff))
    SUMMARY["changed"] = sorted(r for r in patched if patched[r] != originals.get(r))
    SUMMARY["version_changes"] = changes
    SUMMARY["patch"] = "ok"
    after = run_tests("after")
    SUMMARY["after"] = after
    failing = sorted(m for m, r in after.items() if r["exit"] != 0)
    SUMMARY["failing_after"] = failing
    SUMMARY["T"] = "HELD" if not failing and "test_0210" in after else "FAILED"
    say("T: %s; failing after: %s" % (SUMMARY["T"], failing))


# ------------------------------------------------------------------ reading repositories

def clone_at(url, commit, d):
    """Blobless fetch of one commit. Returns (dir, paths)."""
    s = os.path.join(d, "s")
    steps = [["init", "--quiet", s],
             ["-C", s, "remote", "add", "origin", url],
             ["-C", s, "config", "core.repositoryformatversion", "1"],
             ["-C", s, "config", "extensions.partialClone", "origin"],
             ["-C", s, "config", "remote.origin.promisor", "true"],
             ["-C", s, "config", "remote.origin.partialclonefilter", "blob:none"],
             ["-C", s, "fetch", "--quiet", "--depth", "1", "--filter=blob:none", "origin",
              commit]]
    for args in steps:
        r = lc.git(args, timeout=600)
        if r.returncode != 0:
            raise RuntimeError("git %s failed: %s" % (" ".join(args[2:4] if args[0] == "-C"
                                                                else args[:1]),
                                                       r.stderr.strip()[-200:]))
    lt = lc.git(["-C", s, "ls-tree", "-r", "-z", "--name-only", commit])
    if lt.returncode != 0:
        raise RuntimeError("ls-tree failed: " + lt.stderr.strip()[:200])
    return s, [p for p in lt.stdout.split("\0") if p]


def check_repo(new, url, commit=None):
    """Runs new.check_linguas on a repository (at HEAD, or at commit)."""
    res = {"repo": url, "status": "ok", "commit": commit or "", "problems": [], "stats": {}}
    t0 = time.time()
    d = tempfile.mkdtemp(prefix="lg-")
    try:
        if commit:
            s, paths = clone_at(url, commit, d)
        else:
            s, res["commit"], paths = lc.clone(url, d)
        res["n_paths"] = len(paths)
        cache = {}

        def reader(p):
            if p not in cache:
                cache[p] = lc.read_blob(s, res["commit"], p)
            return cache[p]

        res["problems"], res["stats"] = new.check_linguas(paths, reader)
    except subprocess.TimeoutExpired:
        res["status"] = "timeout"
    except Exception as exc:  # record, keep going
        res["status"] = ("error: %r" % (exc,))[:240]
    finally:
        res["seconds"] = round(time.time() - t0, 1)
        shutil.rmtree(d, ignore_errors=True)
    return res


def gitlab_projects(host, group, stats):
    out = []
    for page in range(1, MAX_PAGES + 1):
        url = ("https://%s/api/v4/groups/%s/projects?include_subgroups=true&archived=false"
               "&per_page=100&order_by=id&sort=asc&page=%d" % (host, group, page))
        try:
            items = json.loads(fetch(url).decode("utf-8"))
        except Exception as exc:
            stats["errors"].append("%s/%s page %d: %r" % (host, group, page, exc))
            break
        if not isinstance(items, list) or not items:
            break
        for p in items:
            if not isinstance(p, dict):
                continue
            if p.get("forked_from_project"):
                stats["forks"] += 1
                continue
            if p.get("empty_repo") or p.get("repository_access_level") == "disabled":
                stats["empty"] += 1
                continue
            web = p.get("web_url")
            if isinstance(web, str) and web.startswith("https://"):
                out.append((web, "%s/%s" % (host, group)))
    return out


def github_repos(org, stats):
    out = []
    for page in range(1, MAX_PAGES + 1):
        url = "https://api.github.com/orgs/%s/repos?type=sources&per_page=100&page=%d" % (org,
                                                                                        page)
        try:
            items = json.loads(fetch(url).decode("utf-8"))
        except Exception as exc:
            stats["errors"].append("github %s page %d: %r" % (org, page, exc))
            break
        if not isinstance(items, list) or not items:
            break
        for r in items:
            if not isinstance(r, dict):
                continue
            if r.get("fork") or r.get("archived"):
                stats["forks"] += 1
                continue
            web = r.get("html_url")
            if isinstance(web, str) and web.startswith("https://"):
                out.append((web, "github.com/%s" % org))
    return out


def population():
    stats = {"errors": [], "forks": 0, "empty": 0, "listed": 0, "in_flathub_census": 0}
    found = []
    for host, group in GITLAB_GROUPS:
        found += gitlab_projects(host, group, stats)
    for org in GITHUB_ORGS:
        found += github_repos(org, stats)
    stats["listed"] = len(found)
    census = set(r["repo"].lower() for r in csv_rows(CENSUS + "linguas/v1/repos.csv"))
    repos = {}
    for url, group in found:
        k = url.lower().rstrip("/")
        if k in census:
            stats["in_flathub_census"] += 1
            continue
        repos.setdefault(k, {"repo": url.rstrip("/"), "group": group})
    stats["by_group"] = {}
    for r in repos.values():
        stats["by_group"][r["group"]] = stats["by_group"].get(r["group"], 0) + 1
    return [repos[k] for k in sorted(repos)], stats


# ------------------------------------------------------------------ grading

def unlisted(res):
    return [p for p in res["problems"] if p["code"] == "linguas-unlisted"]


def governed(res):
    return res["status"] == "ok" and res["stats"].get("po folders checked", 0) > 0


def regression(new):
    """R1, R2: the 12 hand-labelled files of the linguas census, at their recorded commits."""
    labels = dict((r["sample"], r) for r in csv_rows(CENSUS + "linguas/labels.csv"))
    rows = []
    for s in csv_rows(CENSUS + "linguas/v1/sample.csv"):
        lab = labels.get(s["sample"], {})
        res = check_repo(new, s["repo"], s["commit"])
        hit = [p for p in unlisted(res) if p["message"].startswith(s["po_file"] + " has ")]
        translated = int(s["translated"]) if s.get("translated", "").isdigit() else 0
        if lab.get("label") == "real" and translated > 0:
            group = "R1"
        elif lab.get("label") == "not real" or translated == 0:
            group = "R2"
        else:
            group = ""
        rows.append({"sample": s["sample"], "repo": s["repo"], "commit": s["commit"],
                     "po_file": s["po_file"], "label": lab.get("label", ""),
                     "translated": translated, "group": group, "status": res["status"],
                     "reported": "yes" if hit else "no",
                     "message": hit[0]["message"] if hit else ""})
        say("regression %s %s %s: %s %s" % (group, s["repo"], s["po_file"], res["status"],
                                             "reported" if hit else "not reported"))
    r1 = [r for r in rows if r["group"] == "R1" and r["status"] == "ok"]
    r1_all = [r for r in rows if r["group"] == "R1"]
    r2 = [r for r in rows if r["group"] == "R2"]
    v = {}
    if len(r1) < R1_READ_MIN:
        v["R1"] = "NOT TESTABLE (%d of %d read)" % (len(r1), len(r1_all))
    else:
        got = sum(1 for r in r1 if r["reported"] == "yes")
        v["R1"] = ("HELD" if got >= R1_MIN else "FAILED") + " (%d of %d reported, %d read)" % (
            got, len(r1_all), len(r1))
    if any(r["status"] != "ok" for r in r2) or len(r2) != 3:
        v["R2"] = "NOT TESTABLE (%d rows, %d read)" % (len(r2), sum(1 for r in r2
                                                                   if r["status"] == "ok"))
    else:
        bad = [r["po_file"] for r in r2 if r["reported"] == "yes"]
        v["R2"] = "HELD" if not bad else "FAILED (reported: %s)" % ", ".join(bad)
    return v, rows


def grade(results):
    read_ok = [r for r in results if r["status"] == "ok"]
    gov = [r for r in read_ok if governed(r)]
    flagged = [r for r in results if r["status"] == "ok" and r["problems"]]
    v = {}
    gate = len(gov) >= GATE_GOVERNED and len(flagged) >= GATE_FLAGGED
    sample = []
    if gate:
        for i, r in enumerate(sorted(flagged, key=lambda r: key(r["repo"]))[:SAMPLE_REPOS], 1):
            p = sorted(r["problems"], key=lambda p: key(r["repo"], p["message"]))[0]
            sample.append({"sample": i, "repo": r["repo"], "commit": r["commit"],
                           "group": r["group"], "code": p["code"], "language": p.get("key", ""),
                           "message": p["message"], "label": "", "note": ""})
        v["H1"] = "PENDING HAND CHECK (%d repositories)" % len(sample)
    else:
        v["H1"] = "NOT TESTABLE (%d governed, %d flagged)" % (len(gov), len(flagged))
    gn = [r for r in gov if r["repo"].lower().startswith("https://gitlab.gnome.org/gnome/")]
    gk = sum(1 for r in gn if unlisted(r))
    if len(gn) < P1_MIN_GOVERNED:
        v["P1"] = "NOT TESTABLE (%d governed GNOME-group repositories)" % len(gn)
    else:
        v["P1"] = ("HELD" if 100 * gk <= 5 * len(gn) else "FAILED") + " (%d of %d)" % (
            gk, len(gn))
    groups = {}
    for r in read_ok:
        g = groups.setdefault(r["group"], {"read": 0, "governed": 0, "with_unlisted": 0,
                                           "with_missing": 0})
        g["read"] += 1
        if governed(r):
            g["governed"] += 1
            g["with_unlisted"] += 1 if unlisted(r) else 0
            g["with_missing"] += 1 if any(p["code"] == "linguas-missing"
                                          for p in r["problems"]) else 0
    counts = {"read": len(read_ok), "governed": len(gov), "flagged": len(flagged),
              "with_unlisted": sum(1 for r in gov if unlisted(r)),
              "unlisted_findings": sum(len(unlisted(r)) for r in read_ok),
              "missing_findings": sum(1 for r in read_ok for p in r["problems"]
                                      if p["code"] == "linguas-missing"),
              "gnome_group_governed": len(gn), "gnome_group_with_unlisted": gk,
              "by_group": dict(sorted(groups.items()))}
    return v, counts, sample


# ------------------------------------------------------------------ main

def main():
    os.makedirs(OUT, exist_ok=True)
    started = time.time()
    data = wait_for(PREREG_URL, PREREG_MARK, 480)
    if not data:
        say("PREREG.md not public; stopping before anything is read")
        finish(4)
    SUMMARY["prereg_sha256"] = hashlib.sha256(data).hexdigest()
    say("prereg sha256 %s" % SUMMARY["prereg_sha256"])
    get_repo()
    build()
    if SUMMARY["T"] != "HELD":
        say("T failed: the pre-registered tests are not run (graded NOT TESTABLE)")
        finish(0)
    new = load("l10n_guard_0210", os.path.join(REPO, "l10n_guard.py"))
    if new.__version__ != NEW:
        fail("loaded version %s" % new.__version__)
    verdicts = {"T": "HELD"}
    v, reg_rows = regression(new)
    verdicts.update(v)
    write_csv(os.path.join(OUT, "regression.csv"),
              ["sample", "repo", "commit", "po_file", "label", "translated", "group", "status",
               "reported", "message"], reg_rows)
    repos, pop = population()
    say("population: %d repositories (%s)" % (len(repos), json.dumps(pop["by_group"])))
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(lambda e: dict(check_repo(new, e["repo"]), group=e["group"]),
                              repos))
    with open(os.path.join(OUT, "results.jsonl"), "w", encoding="utf-8",
              errors="replace") as fh:
        for r in results:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    v, counts, sample = grade(results)
    verdicts.update(v)
    write_csv(os.path.join(OUT, "repos.csv"),
              ["repo", "group", "commit", "status", "seconds", "n_paths", "governed",
               "unlisted", "missing"],
              [dict(r, governed="yes" if governed(r) else "no", unlisted=len(unlisted(r)),
                    missing=sum(1 for p in r["problems"] if p["code"] == "linguas-missing"))
               for r in results])
    write_csv(os.path.join(OUT, "findings.csv"),
              ["repo", "group", "commit", "code", "language", "message"],
              [{"repo": r["repo"], "group": r["group"], "commit": r["commit"],
                "code": p["code"], "language": p.get("key", ""), "message": p["message"]}
               for r in results for p in r["problems"]])
    write_csv(os.path.join(OUT, "sample.csv"),
              ["sample", "repo", "commit", "group", "code", "language", "message", "label",
               "note"], sample)
    status = {}
    for r in results:
        st = r["status"] if r["status"] in ("ok", "timeout") else r["status"].split(":")[0]
        status[st] = status.get(st, 0) + 1
    summary = {"verdicts": verdicts, "counts": counts, "population": pop,
               "repositories": len(repos), "status": dict(sorted(status.items())),
               "prereg_sha256": SUMMARY["prereg_sha256"], "guard_version": new.__version__,
               "minutes": round((time.time() - started) / 60, 1)}
    with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1, sort_keys=True)
    SUMMARY["verdicts"] = verdicts
    say(json.dumps(verdicts))
    finish(0)


if __name__ == "__main__":
    main()
