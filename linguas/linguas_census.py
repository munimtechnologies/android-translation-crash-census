# Census: gettext translations left out of po/LINGUAS in the source repositories of the apps on
# Flathub. Meson's i18n.gettext() and gettext's autotools rules build only the languages listed
# in LINGUAS, so a <lang>.po file that is not listed is never compiled or installed, and nothing
# warns. Pre-registered in linguas/PREREG.md before any population repository is read.
# Standard library and git only. Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.
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
import urllib.parse
import urllib.request

APPS_URL = "https://flathub.org/api/v2/appstream"
APP_URL = "https://flathub.org/api/v2/appstream/%s"
PREREG_URL = ("https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/"
              "main/linguas/PREREG.md")
PREREG_MARK = "linguas census PREREG v1"
KEY = "linguas census v1"
UA = "linguas-census (MV2, Munim, Inc.; mv2@munimtech.com)"
CONTROL_REPO = "https://gitlab.gnome.org/GNOME/gnome-calculator"

TWO_PART_HOSTS = frozenset(["github.com", "codeberg.org", "bitbucket.org", "git.sr.ht"])
GITLAB_HOSTS = frozenset(["gitlab.com", "gitlab.gnome.org", "invent.kde.org", "framagit.org",
                          "gitlab.freedesktop.org", "salsa.debian.org", "gitlab.xfce.org"])
GITLAB_STOP = frozenset(["tree", "blob", "issues", "merge_requests", "wikis", "commits",
                         "releases", "tags"])
GROUP_ORDER = ("gnome", "weblate", "crowdin", "transifex", "other", "none")
VENDOR = frozenset(["subprojects", "vendor", "vendors", "third_party", "thirdparty", "third-party",
                    "3rdparty", "external", "externals", "deps", "node_modules", "submodules"])
GOVERNED = ("meson", "autotools")

LANG_LIKE = re.compile(r"^[A-Za-z]{2,3}(?:[_-][A-Za-z0-9]{2,8})*(?:@[A-Za-z]+)?$")
GETTEXT_CALL = re.compile(r"\bgettext\s*\(")
LANG_KW = re.compile(r"\blanguages\s*:")
AC_MACROS = re.compile(r"\b(?:AM_GNU_GETTEXT|IT_PROG_INTLTOOL|AC_PROG_INTLTOOL|AM_GLIB_GNU_GETTEXT)")

MAX_BYTES = 5000000
MAX_DIRS = 20
MAX_DROPPED_READ = 10

# Pre-registered numbers (PREREG.md).
GATE_READ = 1000
GATE_GOVERNED = 150
MIN_TESTABLE = 4
P3_MIN_GROUP = 20
SAMPLE_REPOS = 12


def key(*parts):
    return hashlib.sha256("|".join((KEY,) + parts).encode("utf-8")).hexdigest()


def decode(data):
    return data.decode("utf-8-sig", "replace")


# ------------------------------------------------------------------ population

def repo_url(url):
    """Clone URL https://<host>/<path> for a forge page URL, or None for other hosts."""
    if not isinstance(url, str) or not url.strip():
        return None
    p = urllib.parse.urlsplit(url.strip())
    if p.scheme not in ("http", "https"):
        return None
    host = p.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    parts = [x for x in p.path.split("/") if x]
    if host in TWO_PART_HOSTS:
        if len(parts) < 2:
            return None
        parts = parts[:2]
    elif host in GITLAB_HOSTS:
        if "-" in parts:
            parts = parts[:parts.index("-")]
        for i, x in enumerate(parts):
            if i >= 2 and x in GITLAB_STOP:
                parts = parts[:i]
                break
        if len(parts) < 2:
            return None
    else:
        return None
    if parts[-1].lower().endswith(".git"):
        parts[-1] = parts[-1][:-4]
    if not parts[-1]:
        return None
    return "https://%s/%s" % (host, "/".join(parts))


def app_urls(meta):
    urls = meta.get("urls") if isinstance(meta, dict) else None
    return urls if isinstance(urls, dict) else {}


def app_repo(meta):
    """(clone URL, "vcs_browser" | "homepage") from Flathub app metadata, or (None, "")."""
    urls = app_urls(meta)
    r = repo_url(urls.get("vcs_browser"))
    if r:
        return r, "vcs_browser"
    r = repo_url(urls.get("homepage"))
    if r:
        return r, "homepage"
    return None, ""


def translate_group(meta):
    """Where the app says it is translated: gnome (l10n.gnome.org, which runs Damned Lies),
    weblate, crowdin, transifex, other, or none."""
    t = app_urls(meta).get("translate")
    if not isinstance(t, str) or not t.strip():
        return "none"
    host = urllib.parse.urlsplit(t.strip()).netloc.lower()
    if host == "l10n.gnome.org":
        return "gnome"
    if "weblate" in host:
        return "weblate"
    if "crowdin" in host:
        return "crowdin"
    if "transifex" in host:
        return "transifex"
    return "other"


def population(apps):
    """apps: {app id: metadata dict or None}. Returns (repositories, stats). Repositories are
    deduplicated without regard to case and sorted; each keeps its app ids, the translate group
    (gnome first, then weblate, crowdin, transifex, other, none) and where the URL came from."""
    repos = {}
    stats = {"apps_listed": len(apps), "apps_fetched": 0, "apps_with_repo": 0,
             "by_source": {}, "unrecognised_hosts": {}}
    for app_id in sorted(apps):
        meta = apps[app_id]
        if not isinstance(meta, dict):
            continue
        stats["apps_fetched"] += 1
        url, source = app_repo(meta)
        if not url:
            raw = app_urls(meta).get("vcs_browser") or app_urls(meta).get("homepage") or ""
            host = urllib.parse.urlsplit(raw).netloc.lower() if isinstance(raw, str) else ""
            host = host or "(none)"
            stats["unrecognised_hosts"][host] = stats["unrecognised_hosts"].get(host, 0) + 1
            continue
        stats["apps_with_repo"] += 1
        stats["by_source"][source] = stats["by_source"].get(source, 0) + 1
        r = repos.setdefault(url.lower(), {"repo": url, "apps": [], "groups": set(),
                                           "source": source})
        r["apps"].append(app_id)
        r["groups"].add(translate_group(meta))
    out = []
    for k in sorted(repos):
        r = repos[k]
        out.append({"repo": r["repo"], "apps": r["apps"], "source": r["source"],
                    "group": next(g for g in GROUP_ORDER if g in r["groups"])})
    top = sorted(stats["unrecognised_hosts"].items(), key=lambda kv: (-kv[1], kv[0]))[:25]
    stats["unrecognised_hosts"] = dict(top)
    return out, stats


# ------------------------------------------------------------------ paths and files

def is_vendored(path):
    return any(part.lower() in VENDOR for part in path.split("/") if part)


def language_like(stem):
    return bool(LANG_LIKE.match(stem)) and not stem.endswith(("@quot", "@boldquot"))


def po_dirs(paths):
    """{dir: {stem: path}} for each own (not vendored) directory that holds a file named LINGUAS
    and at least one .po file directly in it ("" is the repository root)."""
    by_dir = {}
    for p in paths:
        d, _, name = p.rpartition("/")
        by_dir.setdefault(d, set()).add(name)
    out = {}
    for d in sorted(by_dir):
        names = by_dir[d]
        if "LINGUAS" not in names or is_vendored(d):
            continue
        po = {n[:-3]: (d + "/" + n if d else n) for n in sorted(names)
              if n.endswith(".po") and len(n) > 3}
        if po:
            out[d] = po
    return out


def gnu_linguas(text):
    """Languages as gettext's po.m4 reads LINGUAS: '#' starts a comment anywhere on a line."""
    out = []
    for line in text.splitlines():
        out.extend(line.split("#", 1)[0].split())
    return out


def meson_linguas(text):
    """Languages as Meson's read_linguas() reads LINGUAS: lines starting with '#' are skipped,
    other lines are split on whitespace (an inline '#' is kept as a word)."""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.extend(line.split())
    return out


def configure_paths(d, paths_set):
    """configure.ac / configure.in next to the po directory's parent, then at the root."""
    parent = d.rpartition("/")[0] if "/" in d else ""
    out = []
    for base in (parent, ""):
        for n in ("configure.ac", "configure.in"):
            p = base + "/" + n if base else n
            if p in paths_set and p not in out:
                out.append(p)
    return out


def build_kind(meson_text, configure_texts):
    """meson: the directory's meson.build calls gettext() without a languages: list (so Meson
    reads LINGUAS); meson-explicit: it passes languages:; autotools: configure.ac uses gettext
    or intltool macros; other: neither."""
    if meson_text and GETTEXT_CALL.search(meson_text):
        return "meson-explicit" if LANG_KW.search(meson_text) else "meson"
    if any(t and AC_MACROS.search(t) for t in configure_texts):
        return "autotools"
    return "other"


def compare(po, tokens):
    """(dropped, phantom, variants). dropped: language-like .po stems not listed; phantom: listed
    languages with no .po file; variants: dropped stems equal to a listed language after
    lower-casing and reading '-' as '_'."""
    toks = set(tokens)
    dropped = sorted(s for s in po if language_like(s) and s not in toks)
    phantom = sorted(t for t in toks if t not in po)
    norm = {t.lower().replace("-", "_") for t in toks}
    variants = sorted(s for s in dropped if s.lower().replace("-", "_") in norm)
    return dropped, phantom, variants


def _unquote(s):
    i, j = s.find('"'), s.rfind('"')
    return s[i + 1:j] if i != -1 and j > i else ""


def po_stats(data):
    """{"entries", "translated", "fuzzy"} for a .po file (bytes). Entries are messages with a
    non-empty msgid (the header and obsolete #~ entries are skipped). Translated: not fuzzy and
    some msgstr (any plural form) non-empty, which is what msgfmt compiles by default."""
    counts = {"entries": 0, "translated": 0, "fuzzy": 0}
    e = {"has_id": False, "fuzzy": False, "msgid": "", "msgstr": [], "field": None}

    def flush():
        if e["has_id"] and e["msgid"] != "":
            counts["entries"] += 1
            if e["fuzzy"]:
                counts["fuzzy"] += 1
            elif any(s for s in e["msgstr"]):
                counts["translated"] += 1
        e.update(has_id=False, fuzzy=False, msgid="", msgstr=[], field=None)

    for raw in decode(data).splitlines():
        line = raw.strip()
        if not line:
            flush()
        elif line.startswith("#~"):
            continue
        elif line.startswith("#"):
            if e["has_id"]:
                flush()
            if line.startswith("#,") and "fuzzy" in line[2:].replace(",", " ").split():
                e["fuzzy"] = True
        elif line.startswith("msgctxt"):
            if e["has_id"]:
                flush()
            e["field"] = "ctxt"
        elif line.startswith("msgid_plural"):
            e["field"] = "plural"
        elif line.startswith("msgid"):
            if e["has_id"]:
                flush()
            e["has_id"] = True
            e["field"] = "msgid"
            e["msgid"] = _unquote(line[5:])
        elif line.startswith("msgstr"):
            e["field"] = "msgstr"
            e["msgstr"].append(_unquote(line[6:]))
        elif line.startswith('"'):
            if e["field"] == "msgid":
                e["msgid"] += _unquote(line)
            elif e["field"] == "msgstr" and e["msgstr"]:
                e["msgstr"][-1] += _unquote(line)
    flush()
    return counts


def substantive(st):
    if not st or st["entries"] == 0:
        return "unknown"
    return "yes" if 2 * st["translated"] >= st["entries"] else "no"


# ------------------------------------------------------------------ git

def git(args, timeout=300, binary=False):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_LFS_SKIP_SMUDGE="1", GIT_ASKPASS="true")
    if binary:
        return subprocess.run(["git"] + args, env=env, capture_output=True, timeout=timeout)
    return subprocess.run(["git"] + args, env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def clone(url, d):
    """Blobless depth-1 clone without checkout. Returns (dir, commit, paths)."""
    s = os.path.join(d, "s")
    r = git(["clone", "--quiet", "--depth", "1", "--filter=blob:none", "--no-checkout",
             "--single-branch", url, s], timeout=600)
    if r.returncode != 0:
        raise RuntimeError("clone failed: " + ((r.stderr.strip().splitlines() or [""])[-1])[:200])
    commit = git(["-C", s, "rev-parse", "HEAD"]).stdout.strip()
    lt = git(["-C", s, "ls-tree", "-r", "-z", "--name-only", "HEAD"])
    if lt.returncode != 0:
        raise RuntimeError("ls-tree failed: " + lt.stderr.strip()[:200])
    return s, commit, [p for p in lt.stdout.split("\0") if p]


def read_blob(s, commit, path):
    """File contents at the commit (git fetches the blob on demand), or None."""
    r = git(["-C", s, "cat-file", "-p", "%s:%s" % (commit, path)], binary=True)
    if r.returncode != 0 or len(r.stdout) > MAX_BYTES:
        return None
    return r.stdout


def analyse(entry, tmp_root):
    res = {"repo": entry["repo"], "group": entry.get("group", ""), "apps": entry.get("apps", []),
           "status": "ok", "commit": "", "n_paths": 0, "n_linguas_dirs": 0, "dirs": []}
    t0 = time.time()
    d = tempfile.mkdtemp(dir=tmp_root)
    try:
        s, res["commit"], paths = clone(entry["repo"], d)
        res["n_paths"] = len(paths)
        pset = set(paths)
        dirs = po_dirs(paths)
        res["n_linguas_dirs"] = len(dirs)
        cache = {}

        def read(p):
            if p not in cache:
                cache[p] = read_blob(s, res["commit"], p)
            return cache[p]

        for dname in sorted(dirs)[:MAX_DIRS]:
            po = dirs[dname]
            prefix = dname + "/" if dname else ""
            lin = read(prefix + "LINGUAS")
            mb = read(prefix + "meson.build") if (prefix + "meson.build") in pset else None
            conf = [decode(x) for x in (read(p) for p in configure_paths(dname, pset))
                    if x is not None]
            build = build_kind(decode(mb) if mb is not None else None, conf)
            rec = {"dir": dname, "build": build, "n_po": len(po), "linguas_read": lin is not None,
                   "n_listed": 0, "dropped": [], "phantom": [], "variants": [], "files": []}
            if lin is not None:
                text = decode(lin)
                tokens = meson_linguas(text) if build.startswith("meson") else gnu_linguas(text)
                rec["n_listed"] = len(tokens)
                rec["dropped"], rec["phantom"], rec["variants"] = compare(po, tokens)
                if build in GOVERNED:
                    for stem in rec["dropped"][:MAX_DROPPED_READ]:
                        data = read(po[stem])
                        st = po_stats(data) if data is not None else None
                        f = {"stem": stem, "path": po[stem], "entries": None, "translated": None,
                             "fuzzy": None, "substantive": substantive(st)}
                        if st:
                            f.update(st)
                        rec["files"].append(f)
            res["dirs"].append(rec)
    except subprocess.TimeoutExpired:
        res["status"] = "timeout"
    except Exception as exc:  # record, keep going
        res["status"] = ("error: %r" % (exc,))[:240]
    finally:
        res["seconds"] = round(time.time() - t0, 1)
        shutil.rmtree(d, ignore_errors=True)
    return res


# ------------------------------------------------------------------ grading

def governed_dirs(r):
    return [x for x in r["dirs"] if x["build"] in GOVERNED and x.get("linguas_read")]


def grade(results):
    """Pre-registered verdicts G, P1-P4 (PREREG.md) and the counts behind them."""
    read = [r for r in results if r["status"] == "ok"]
    gov = [r for r in read if governed_dirs(r)]
    flagged = [r for r in gov if any(x["dropped"] for x in governed_dirs(r))]
    flagged_ids = {id(r) for r in flagged}
    n, k = len(gov), len(flagged)
    files = [f for r in flagged for x in governed_dirs(r) for f in x["files"]]
    known = [f for f in files if f["substantive"] in ("yes", "no")]
    yes = [f for f in known if f["substantive"] == "yes"]
    gn = [r for r in gov if r["group"] == "gnome"]
    on = [r for r in gov if r["group"] != "gnome"]
    gk = sum(1 for r in gn if id(r) in flagged_ids)
    ok = sum(1 for r in on if id(r) in flagged_ids)

    def meson(r):
        return [x for x in governed_dirs(r) if x["build"] == "meson"]

    m_drop = [r for r in gov if any(x["dropped"] for x in meson(r))]
    m_phan = [r for r in gov if any(x["phantom"] for x in meson(r))]
    v = {}
    gate = len(read) >= GATE_READ and n >= GATE_GOVERNED
    v["G"] = ("PASSED" if gate else "FAILED (%d read, %d with a governed LINGUAS directory)"
              % (len(read), n))
    if not gate:
        for p in ("P1", "P2", "P3", "P4"):
            v[p] = "NOT TESTABLE (gate)"
    else:
        v["P1"] = "HELD" if (100 * k >= 3 * n and 4 * k <= n) else "FAILED"
        v["P2"] = ("NOT TESTABLE (%d dropped files with known content)" % len(known)
                   if len(known) < MIN_TESTABLE
                   else "HELD" if 2 * len(yes) >= len(known) else "FAILED")
        if len(gn) < P3_MIN_GROUP or len(on) < P3_MIN_GROUP or gk + ok < MIN_TESTABLE:
            v["P3"] = "NOT TESTABLE (%d gnome, %d other, %d flagged)" % (len(gn), len(on), gk + ok)
        else:
            v["P3"] = "HELD" if gk * len(on) < ok * len(gn) else "FAILED"
        v["P4"] = ("NOT TESTABLE (%d repositories)" % (len(m_drop) + len(m_phan))
                   if len(m_drop) + len(m_phan) < MIN_TESTABLE
                   else "HELD" if len(m_phan) < len(m_drop) else "FAILED")
    lang = {}
    for r in flagged:
        for x in governed_dirs(r):
            for s in x["dropped"]:
                lang[s] = lang.get(s, 0) + 1
    counts = {
        "read": len(read), "governed_repos": n, "flagged_repos": k,
        "flagged_share_pct": round(100.0 * k / n, 2) if n else None,
        "governed_by_build": {b: sum(1 for r in gov if any(x["build"] == b
                                                           for x in governed_dirs(r)))
                              for b in GOVERNED},
        "dropped_files": sum(len(x["dropped"]) for r in flagged for x in governed_dirs(r)),
        "dropped_files_read": len(files), "content_known": len(known),
        "content_substantive": len(yes),
        "dropped_translated_messages": sum(f["translated"] or 0 for f in files),
        "gnome_governed": len(gn), "gnome_flagged": gk, "other_governed": len(on),
        "other_flagged": ok, "meson_dropped_repos": len(m_drop),
        "meson_phantom_repos": len(m_phan),
        "dropped_languages": dict(sorted(lang.items(), key=lambda kv: (-kv[1], kv[0]))[:40]),
    }
    return v, counts, flagged


def exploratory(results):
    read = [r for r in results if r["status"] == "ok"]
    groups = {}
    for r in read:
        if governed_dirs(r):
            g = groups.setdefault(r["group"], {"governed": 0, "flagged": 0})
            g["governed"] += 1
            if any(x["dropped"] for x in governed_dirs(r)):
                g["flagged"] += 1
    builds = {}
    for r in read:
        for x in r["dirs"]:
            b = builds.setdefault(x["build"], {"dirs": 0, "with_dropped": 0, "with_phantom": 0})
            b["dirs"] += 1
            b["with_dropped"] += 1 if x["dropped"] else 0
            b["with_phantom"] += 1 if x["phantom"] else 0
    variants = sorted("%s:%s/%s" % (r["repo"], x["dir"], s) for r in read
                      for x in governed_dirs(r) for s in x["variants"])
    auto_phantom = sorted({r["repo"] for r in read for x in governed_dirs(r)
                           if x["build"] == "autotools" and x["phantom"]})
    return {"by_translate_group": dict(sorted(groups.items())),
            "dirs_by_build": dict(sorted(builds.items())),
            "spelling_variants": variants, "autotools_phantom_repos": auto_phantom,
            "repos_with_linguas_dir": sum(1 for r in read if r["dirs"])}


def sample_rows(flagged):
    rows = []
    for i, r in enumerate(sorted(flagged, key=lambda r: key(r["repo"]))[:SAMPLE_REPOS], 1):
        cands = [(x, f) for x in governed_dirs(r) for f in x["files"]]
        x, f = sorted(cands, key=lambda xf: key(r["repo"], xf[1]["path"]))[0]
        rows.append({"sample": i, "repo": r["repo"], "commit": r["commit"], "group": r["group"],
                     "dir": x["dir"], "build": x["build"], "po_file": f["path"],
                     "language": f["stem"], "entries": f["entries"],
                     "translated": f["translated"], "fuzzy": f["fuzzy"],
                     "n_listed": x["n_listed"], "label": "", "note": ""})
    return rows


def write_csv(path, cols, rows):
    with open(path, "w", encoding="utf-8", errors="replace", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for row in rows:
            w.writerow({c: ("" if row.get(c) is None else str(row.get(c)))
                        .encode("utf-8", "replace").decode("utf-8") for c in cols})


# ------------------------------------------------------------------ network

def fetch_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def fetch_json(url, tries=3):
    last = None
    for i in range(tries):
        try:
            return json.loads(fetch_text(url).decode("utf-8"))
        except Exception as exc:  # retry, then give up
            last = exc
            time.sleep(5 * (i + 1))
    raise RuntimeError("could not read %s: %r" % (url, last))


def fetch_apps(ids, workers=6):
    def one(app_id):
        try:
            return app_id, fetch_json(APP_URL % urllib.parse.quote(app_id, safe=""))
        except Exception:
            return app_id, None
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        return dict(ex.map(one, ids))


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


def control(tmp_root):
    """Checks the pipeline on GNOME Calculator before any population repository is read: po/
    must be a Meson LINGUAS directory listing de, and po/de.po must read as a translation.
    Returns "" when it passes, else what went wrong."""
    d = tempfile.mkdtemp(dir=tmp_root)
    try:
        s, commit, paths = clone(CONTROL_REPO, d)
        dirs = po_dirs(paths)
        if "de" not in dirs.get("po", {}):
            return "po/de.po not found next to po/LINGUAS"
        mb, lin = read_blob(s, commit, "po/meson.build"), read_blob(s, commit, "po/LINGUAS")
        if mb is None or lin is None:
            return "could not read po/meson.build or po/LINGUAS"
        if build_kind(decode(mb), []) != "meson":
            return "po/meson.build not recognised as Meson gettext"
        if "de" not in meson_linguas(decode(lin)):
            return "de not listed in po/LINGUAS"
        data = read_blob(s, commit, "po/de.po")
        st = po_stats(data) if data is not None else None
        if not st or st["entries"] < 100 or substantive(st) != "yes":
            return "po/de.po stats %r" % (st,)
        return ""
    except Exception as exc:
        return "control error: %r" % (exc,)
    finally:
        shutil.rmtree(d, ignore_errors=True)


DIR_COLS = ["repo", "commit", "group", "dir", "build", "n_po", "n_listed", "dropped", "phantom",
            "variants"]
FILE_COLS = ["repo", "commit", "group", "dir", "build", "stem", "path", "entries", "translated",
             "fuzzy", "substantive"]
SAMPLE_COLS = ["sample", "repo", "commit", "group", "dir", "build", "po_file", "language",
               "entries", "translated", "fuzzy", "n_listed", "label", "note"]


def main(out, say, workers=8, prereg_wait_minutes=360):
    started = time.time()
    tmp_root = tempfile.mkdtemp(prefix="linguas-")
    err = control(tmp_root)
    if err:
        say("control failed: " + err)
        return 3
    say("control passed (%s)" % CONTROL_REPO)
    prereg_sha = wait_for_prereg(prereg_wait_minutes, say)
    if not prereg_sha:
        say("PREREG.md not public; stopping before reading any repository")
        return 4
    say("prereg sha256 %s" % prereg_sha)
    raw = None
    for attempt in range(3):
        try:
            raw = fetch_text(APPS_URL)
            break
        except OSError as exc:
            say("flathub list attempt %d failed: %r" % (attempt + 1, exc))
            time.sleep(30)
    if raw is None:
        say("could not read the Flathub app list")
        return 5
    ids =[x for x in json.loads(raw.decode("utf-8")) if isinstance(x, str)]
    say("flathub lists %d apps" % len(ids))
    apps = fetch_apps(ids)
    repos, pop_stats = population(apps)
    say("%d apps fetched, %d repositories" % (pop_stats["apps_fetched"], len(repos)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(lambda e: analyse(e, tmp_root), repos))
    shutil.rmtree(tmp_root, ignore_errors=True)

    with open(os.path.join(out, "results.jsonl"), "w", encoding="utf-8", errors="replace") as fh:
        for r in results:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    write_csv(os.path.join(out, "apps.csv"), ["app", "fetched", "repo", "source", "group"],
              [{"app": a, "fetched": "yes" if isinstance(m, dict) else "no",
                "repo": app_repo(m)[0] if isinstance(m, dict) else "",
                "source": app_repo(m)[1] if isinstance(m, dict) else "",
                "group": translate_group(m) if isinstance(m, dict) else ""}
               for a, m in sorted(apps.items())])
    write_csv(os.path.join(out, "repos.csv"),
              ["repo", "commit", "group", "status", "seconds", "n_paths", "n_linguas_dirs",
               "governed", "dropped"],
              [dict(r, governed="yes" if governed_dirs(r) else "no",
                    dropped=sum(len(x["dropped"]) for x in governed_dirs(r))) for r in results])
    write_csv(os.path.join(out, "dirs.csv"), DIR_COLS,
              [dict(x, repo=r["repo"], commit=r["commit"], group=r["group"],
                    dropped=" ".join(x["dropped"]), phantom=" ".join(x["phantom"]),
                    variants=" ".join(x["variants"]))
               for r in results for x in r["dirs"]])
    write_csv(os.path.join(out, "dropped.csv"), FILE_COLS,
              [dict(f, repo=r["repo"], commit=r["commit"], group=r["group"], dir=x["dir"],
                    build=x["build"])
               for r in results for x in r["dirs"] for f in x["files"]])
    verdicts, counts, flagged = grade(results)
    rows = sample_rows(flagged) if verdicts["G"] == "PASSED" else []
    write_csv(os.path.join(out, "sample.csv"), SAMPLE_COLS, rows)
    verdicts["H1"] = ("PENDING HAND CHECK (%d repositories)" % len(rows) if len(rows) >= 6
                      else "NOT TESTABLE (sample of %d)" % len(rows))
    status = {}
    for r in results:
        st = r["status"] if r["status"] in ("ok", "timeout") else r["status"].split(":")[0]
        status[st] = status.get(st, 0) + 1
    summary = {"verdicts": verdicts, "counts": counts, "prereg_sha256": prereg_sha,
               "flathub_list_sha256": hashlib.sha256(raw).hexdigest(),
               "flathub_list_apps": len(ids), "population": pop_stats,
               "repositories": len(repos), "status": dict(sorted(status.items())),
               "exploratory": exploratory(results), "control": CONTROL_REPO,
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
