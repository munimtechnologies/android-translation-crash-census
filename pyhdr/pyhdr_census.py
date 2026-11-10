# pyhdr census v1: gettext catalogs that CPython's gettext module cannot load.
#
# For every .po file in the po folders whose Meson or autotools build reads LINGUAS (the 526
# Flathub app repositories of the linguas census and the 291 GNOME, GNOME World, elementary and
# Xfce repositories of the l10n-guard 0.21.0 check, each cloned again at HEAD), this job
#   1. compiles the file with GNU msgfmt (plain, as Meson and gettext's autotools rules do),
#   2. loads the compiled catalog with CPython's gettext.GNUTranslations (ground truth: does a
#      Python program, or itstool, crash when it opens this language?),
#   3. runs `msgfmt --check` on it (does the usual gettext check catch it?), and
#   4. runs py_load_problem(), a pure-Python reading of the .po file that mirrors
#      GNUTranslations._parse (CPython 3.12), to test whether a linter can predict step 2.
# Nothing is published from here. Predictions: PREREG.md in the same folder.
# Usage: python -B pyhdr_census.py <out folder>
# Made with AI agents by MV2 of Munim, Inc. Apache-2.0.
import codecs
import concurrent.futures
import csv
import gettext
import hashlib
import importlib.util
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
import urllib.request

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
CENSUS = ("https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/"
          "main/")
FLATHUB_DIRS = CENSUS + "linguas/v1/dirs.csv"
PLATFORM_REPOS = CENSUS + "l10n-guard-0210/repos.csv"
GUARD_URL = "https://raw.githubusercontent.com/munimtechnologies/l10n-guard/v0.21.0/l10n_guard.py"
PREREG_URL = CENSUS + "pyhdr/PREREG.md"
PREREG_MARK = "pyhdr census PREREG v1"
KEY = "pyhdr census v1"
UA = {"User-Agent": "pyhdr-census (MV2, Munim, Inc.; mv2@munimtech.com)"}
WAIT_SECONDS = 8 * 3600
MAX_BYTES = 5000000
GATE_REPOS = 600
GATE_FILES = 10000
SAMPLE_REPOS = 12
WORKERS = 6
GOVERNED = ("meson", "autotools")
# First path parts that hold build helpers, tests or docs rather than the app's own code.
NOT_APP = frozenset(["po", "build-aux", "help", "doc", "docs", "test", "tests", "subprojects",
                     "tools", "scripts", "data", "examples", "build", "vendor", "third_party",
                     "flatpak", "packaging", "ci", ".ci", ".github", ".gitlab"])

SUMMARY = {"verdicts": {}}
LOG = []


# ------------------------------------------------------------------ the rule (pure)

_ESC = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "a": "\a", "b": "\b",
        "f": "\f", "v": "\v"}


def _unq(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1]
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            out.append(_ESC.get(s[i + 1], s[i + 1]))
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def parse_po(text):
    """Entries of a .po file. Pass the bytes decoded as latin-1 so every byte survives.
    Each entry: ctxt, id, id_plural (str or None), strs (dict form -> str; form 0 for a
    singular msgstr), fuzzy, obsolete."""
    entries, cur, field, flags = [], None, None, set()
    for raw in text.splitlines():
        line = raw.strip()
        obsolete = False
        if line.startswith("#~"):
            obsolete = True
            line = line[2:].strip()
            if line.startswith("|"):
                continue
        elif line.startswith("#,"):
            flags |= set(f.strip() for f in line[2:].split(","))
            continue
        elif not line or line.startswith("#"):
            continue
        if line.startswith('"'):
            if cur is not None and field is not None:
                if field[0] == "str":
                    cur["strs"][field[1]] += _unq(line)
                else:
                    cur[field[0]] += _unq(line)
            continue
        kw, _, rest = line.partition(" ")
        if cur is None or (kw in ("msgctxt", "msgid") and cur["id"] is not None):
            if cur is not None:
                entries.append(cur)
            cur = {"ctxt": None, "id": None, "id_plural": None, "strs": {},
                   "fuzzy": "fuzzy" in flags, "obsolete": False}
            flags = set()
        cur["obsolete"] = cur["obsolete"] or obsolete
        m = re.match(r"msgstr\[(\d+)\]$", kw)
        if m:
            field = ("str", int(m.group(1)))
            cur["strs"][field[1]] = _unq(rest)
        elif kw == "msgstr":
            field = ("str", 0)
            cur["strs"][0] = _unq(rest)
        elif kw in ("msgctxt", "msgid", "msgid_plural"):
            name = {"msgctxt": "ctxt", "msgid": "id", "msgid_plural": "id_plural"}[kw]
            field = (name,)
            cur[name] = _unq(rest)
        else:
            field = None
    if cur is not None and cur["id"] is not None:
        entries.append(cur)
    return entries


def _is_header(e):
    return e["id"] == "" and e["ctxt"] is None


def py_load_problem(data):
    """(code, detail) when CPython's gettext.GNUTranslations would raise on the catalog that
    msgfmt builds from this .po file (data: its bytes), else None. Mirrors
    GNUTranslations._parse in CPython 3.12: msgfmt keeps only translated entries and drops
    fuzzy ones except the header; Python decodes each header line as UTF-8, takes the charset
    with v.split('charset=')[1] and the plural rule with v.split(';')[1].split('plural=')[1],
    compiles it with gettext.c2py, then decodes every kept message in that charset."""
    entries = [e for e in parse_po(data.decode("latin-1")) if not e["obsolete"]
               and e["id"] is not None]
    kept = [e for e in entries if e["strs"].get(0, "") != ""
            and (not e["fuzzy"] or _is_header(e))]
    header = None
    for e in kept:
        if _is_header(e):
            header = e
            break
    charset = None
    if header is not None:
        lastk = None
        for b_item in header["strs"][0].encode("latin-1").split(b"\n"):
            try:
                item = b_item.decode().strip()
            except UnicodeDecodeError:
                return ("header-not-utf8", "header line is not UTF-8: %r" % (b_item[:60],))
            if not item:
                continue
            if item.startswith("#-#-#-#-#") and item.endswith("#-#-#-#-#"):
                continue
            k = v = None
            if ":" in item:
                k, v = item.split(":", 1)
                k = k.strip().lower()
                v = v.strip()
                lastk = k
            elif lastk:
                pass
            if k == "content-type":
                parts = v.split("charset=")
                if len(parts) < 2:
                    return ("content-type-no-charset", "Content-Type: %s" % v[:80])
                charset = parts[1]
            elif k == "plural-forms":
                parts = v.split(";")
                seg = parts[1].split("plural=") if len(parts) >= 2 else []
                if len(seg) < 2:
                    return ("plural-forms-syntax", "Plural-Forms: %s" % v[:80])
                try:
                    gettext.c2py(seg[1])
                except Exception as exc:  # c2py raises ValueError
                    return ("plural-forms-expression", "%s: %r" % (exc, seg[1][:80]))
    cs = charset or "ascii"
    try:
        codecs.lookup(cs)
    except LookupError:
        return ("unknown-charset", "charset %r" % (cs[:40],))
    for e in kept:
        texts = [e["ctxt"] or "", e["id"]] + [e["strs"][k] for k in sorted(e["strs"])]
        for t in texts:
            try:
                t.encode("latin-1").decode(cs)
            except UnicodeDecodeError:
                return ("text-not-in-charset",
                        "text is not valid %s near msgid %r" % (cs, e["id"][:40]))
    return None


# ------------------------------------------------------------------ ground truth

def _first_line(text, pattern=None):
    lines = [x.strip() for x in (text or "").splitlines() if x.strip()]
    if pattern:
        hit = [x for x in lines if re.search(pattern, x, re.I)]
        if hit:
            return hit[0][:240]
    return lines[0][:240] if lines else ""


def ground_truth(po_path, mo_path):
    """msgfmt the file, load the result with gettext.GNUTranslations, and run msgfmt --check."""
    res = {"msgfmt": "", "msgfmt_err": "", "load": "", "check": "", "check_err": ""}
    if os.path.exists(mo_path):
        os.remove(mo_path)
    p = subprocess.run(["msgfmt", "-o", mo_path, po_path], capture_output=True, text=True,
                       errors="replace", timeout=180)
    if p.returncode != 0 or not os.path.exists(mo_path):
        res["msgfmt"] = "fail"
        res["msgfmt_err"] = _first_line(p.stderr, r"error|fatal")
    else:
        res["msgfmt"] = "ok"
        try:
            with open(mo_path, "rb") as fh:
                gettext.GNUTranslations(fh)
            res["load"] = "ok"
        except Exception as exc:
            res["load"] = ("%s: %s" % (type(exc).__name__, exc))[:240]
    c = subprocess.run(["msgfmt", "--check", "-o", os.devnull, po_path], capture_output=True,
                       text=True, errors="replace", timeout=180)
    res["check"] = "pass" if c.returncode == 0 else "fail"
    if c.returncode != 0:
        res["check_err"] = _first_line(c.stderr, r"plural|charset|header")
    return res


# ------------------------------------------------------------------ plumbing

def say(msg):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    LOG.append(line)


def write(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def get(url, tries=6):
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
        except Exception as e:  # network errors: retry
            last = repr(e)
        time.sleep(15 * (i + 1))
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


def git(args, timeout=600):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_LFS_SKIP_SMUDGE="1", GIT_ASKPASS="true")
    return subprocess.run(["git"] + args, env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def clone(url, d):
    """Blobless depth-1 clone without checkout. Returns (dir, commit, paths)."""
    s = os.path.join(d, "s")
    r = git(["clone", "--quiet", "--depth", "1", "--filter=blob:none", "--no-checkout",
             "--single-branch", url, s])
    if r.returncode != 0:
        raise RuntimeError("clone failed: " + ((r.stderr.strip().splitlines() or [""])[-1])[:200])
    commit = git(["-C", s, "rev-parse", "HEAD"]).stdout.strip()
    lt = git(["-C", s, "ls-tree", "-r", "-z", "--name-only", "HEAD"])
    if lt.returncode != 0:
        raise RuntimeError("ls-tree failed: " + lt.stderr.strip()[:200])
    return s, commit, [p for p in lt.stdout.split("\0") if p]


def checkout(s, paths):
    for i in range(0, len(paths), 100):
        r = git(["--literal-pathspecs", "-C", s, "checkout", "-q", "HEAD", "--"]
                + paths[i:i + 100], timeout=1800)
        if r.returncode != 0:
            raise RuntimeError("checkout failed: " + r.stderr.strip()[:200])


def load_guard(tmp):
    data = get(GUARD_URL)
    if data is None or b'__version__ = "0.21.0"' not in data:
        raise SystemExit("l10n-guard v0.21.0 not found")
    SUMMARY["guard_sha256"] = hashlib.sha256(data).hexdigest()
    path = os.path.join(tmp, "l10n_guard_0210.py")
    with open(path, "wb") as fh:
        fh.write(data)
    spec = importlib.util.spec_from_file_location("l10n_guard_0210", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def population():
    flathub = {}
    for r in csv.DictReader(io.StringIO(get(FLATHUB_DIRS).decode("utf-8"))):
        if r["build"] in GOVERNED:
            flathub.setdefault(r["repo"], r["group"])
    platform = {}
    for r in csv.DictReader(io.StringIO(get(PLATFORM_REPOS).decode("utf-8"))):
        if r["governed"] == "yes" and r["repo"] not in flathub:
            platform.setdefault(r["repo"], r["group"])
    SUMMARY["population"] = {"flathub": len(flathub), "platform": len(platform)}
    say("population: %d Flathub repositories, %d platform repositories"
        % (len(flathub), len(platform)))
    return ([("flathub", u, g) for u, g in sorted(flathub.items())]
            + [("platform", u, g) for u, g in sorted(platform.items())])


def py_files(g, paths):
    n = 0
    for p in paths:
        if not p.endswith(".py") or "/" not in p:
            continue
        if p.split("/")[0].lower() in NOT_APP or g._lg_skipped(p.rpartition("/")[0]):
            continue
        n += 1
    return n


def analyse(g, entry, tmp_root):
    src, repo, group = entry
    res = {"repo": repo, "src": src, "group": group, "status": "ok", "commit": "",
           "n_paths": 0, "py_files": 0, "dirs": 0, "files": []}
    t0 = time.time()
    d = tempfile.mkdtemp(dir=tmp_root)
    try:
        s, res["commit"], paths = clone(repo, d)
        res["n_paths"] = len(paths)
        res["py_files"] = py_files(g, paths)
        pset = set(paths)
        by_dir = {}
        for p in paths:
            dn, _, name = p.rpartition("/")
            by_dir.setdefault(dn, set()).add(name)
        plans = []
        for dn in sorted(by_dir):
            names = by_dir[dn]
            if "LINGUAS" not in names or g._lg_skipped(dn):
                continue
            po = sorted(n for n in names if n.endswith(".po") and len(n) > 3)
            if not po:
                continue
            prefix = dn + "/" if dn else ""
            confs = []
            for base in (dn.rpartition("/")[0], ""):
                for n in ("configure.ac", "configure.in"):
                    p = base + "/" + n if base else n
                    if p in pset and p not in confs:
                        confs.append(p)
            meson = prefix + "meson.build" if (prefix + "meson.build") in pset else None
            plans.append((dn, prefix, po, meson, confs))
        need = set()
        for dn, prefix, po, meson, confs in plans:
            need.add(prefix + "LINGUAS")
            need.update(prefix + n for n in po)
            need.update(confs)
            if meson:
                need.add(meson)
        if need:
            checkout(s, sorted(need))

        def local(p):
            return os.path.join(s, *p.split("/"))

        def read(p):
            fp = local(p)
            try:
                if os.path.getsize(fp) > MAX_BYTES:
                    return None
                with open(fp, "rb") as fh:
                    return fh.read()
            except OSError:
                return None

        mo = os.path.join(d, "check.mo")
        for dn, prefix, po, meson, confs in plans:
            mt = read(meson) if meson else None
            conf_texts = [x.decode("utf-8", "replace") for x in (read(p) for p in confs)
                          if x is not None]
            build = g._lg_build(None if mt is None else mt.decode("utf-8", "replace"),
                                conf_texts)
            lin = read(prefix + "LINGUAS")
            if build not in GOVERNED or lin is None:
                continue
            res["dirs"] += 1
            text = lin.decode("utf-8-sig", "replace")
            listed = set(g._lg_meson_linguas(text) if build == "meson"
                         else g._lg_gnu_linguas(text))
            for n in po:
                stem = n[:-3]
                if g._lg_language(stem) is None:
                    continue
                row = {"repo": repo, "src": src, "commit": res["commit"], "dir": dn,
                       "build": build, "stem": stem, "listed": "yes" if stem in listed else "no",
                       "translated": "", "total": "", "rule_code": "", "rule_detail": "",
                       "msgfmt": "unread", "msgfmt_err": "", "load": "", "check": "",
                       "check_err": ""}
                data = read(prefix + n)
                if data is not None:
                    row["translated"], row["total"] = g._lg_translated(data)
                    try:
                        rule = py_load_problem(data)
                    except Exception as exc:  # record, keep going
                        rule = ("rule-error", repr(exc)[:200])
                    if rule:
                        row["rule_code"], row["rule_detail"] = rule
                    row.update(ground_truth(local(prefix + n), mo))
                res["files"].append(row)
    except subprocess.TimeoutExpired:
        res["status"] = "timeout"
    except Exception as exc:  # record, keep going
        res["status"] = ("error: %r" % (exc,))[:240]
    finally:
        res["seconds"] = round(time.time() - t0, 1)
        shutil.rmtree(d, ignore_errors=True)
    return res


FILE_COLS = ["repo", "src", "commit", "dir", "build", "stem", "listed", "translated", "total",
             "rule_code", "rule_detail", "msgfmt", "msgfmt_err", "load", "check", "check_err"]
REPO_COLS = ["repo", "src", "group", "commit", "status", "seconds", "n_paths", "py_files", "dirs",
             "files", "listed_crash", "unlisted_crash", "listed_msgfmt_fail"]
SAMPLE_COLS = ["sample", "repo", "src", "commit", "dir", "po_file", "rule_code", "load", "check",
               "py_files"]


def csv_text(cols, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def crashes(f):
    return f["msgfmt"] == "ok" and f["load"] != "ok"


def grade(results):
    v = {}
    ok = [r for r in results if r["status"] == "ok"]
    files = [f for r in ok for f in r["files"]]
    compiled = [f for f in files if f["msgfmt"] == "ok"]
    SUMMARY["counts"] = {"repos": len(results), "repos_ok": len(ok),
                         "repos_with_governed_dir": sum(1 for r in ok if r["dirs"]),
                         "po_files": len(files), "compiled": len(compiled),
                         "msgfmt_fail": sum(1 for f in files if f["msgfmt"] == "fail"),
                         "unread": sum(1 for f in files if f["msgfmt"] == "unread")}
    gate = len(ok) >= GATE_REPOS and len(compiled) >= GATE_FILES
    v["G"] = ("HELD (%d repositories, %d compiled files)" % (len(ok), len(compiled)) if gate
              else "FAILED (%d repositories, %d compiled files)" % (len(ok), len(compiled)))
    flagged = [f for f in compiled if f["rule_code"]]
    crash = [f for f in compiled if crashes(f)]
    tp = [f for f in flagged if crashes(f)]
    SUMMARY["agreement"] = {"flagged": len(flagged), "crash": len(crash), "both": len(tp)}
    if not gate:
        for k in ("A1", "A2", "P1"):
            v[k] = "NOT TESTABLE (gate G failed)"
        return v
    if len(flagged) < 5:
        v["A1"] = "NOT TESTABLE (%d flagged)" % len(flagged)
    else:
        v["A1"] = ("HELD" if 20 * len(tp) >= 19 * len(flagged) else "FAILED") + (
            " (%d of %d flagged files crash)" % (len(tp), len(flagged)))
    if len(crash) < 5:
        v["A2"] = "NOT TESTABLE (%d crashing files)" % len(crash)
    else:
        v["A2"] = ("HELD" if 20 * len(tp) >= 19 * len(crash) else "FAILED") + (
            " (%d of %d crashing files flagged)" % (len(tp), len(crash)))
    k = [r for r in ok if any(f["listed"] == "yes" and crashes(f) for f in r["files"])]
    v["P1"] = ("HELD" if len(k) >= 1 and 20 * len(k) <= len(ok) else "FAILED") + (
        " (%d of %d repositories ship a crashing catalog)" % (len(k), len(ok)))
    return v


def exploratory(results):
    ok = [r for r in results if r["status"] == "ok"]
    files = [f for r in ok for f in r["files"]]
    crash = [f for f in files if crashes(f)]
    by_type, by_code = {}, {}
    for f in crash:
        t = f["load"].split(":", 1)[0]
        by_type[t] = by_type.get(t, 0) + 1
        c = f["rule_code"] or "(not flagged)"
        by_code[c] = by_code.get(c, 0) + 1
    ex = {"crash_by_exception": by_type, "crash_by_rule_code": by_code,
          "crash_listed": sum(1 for f in crash if f["listed"] == "yes"),
          "crash_unlisted": sum(1 for f in crash if f["listed"] == "no"),
          "crash_passing_msgfmt_check": sum(1 for f in crash if f["check"] == "pass"),
          "listed_msgfmt_fail": sum(1 for f in files if f["listed"] == "yes"
                                    and f["msgfmt"] == "fail")}
    for src in ("flathub", "platform"):
        rs = [r for r in ok if r["src"] == src]
        ex["repos_shipping_crash_" + src] = "%d of %d" % (
            sum(1 for r in rs if any(f["listed"] == "yes" and crashes(f) for f in r["files"])),
            len(rs))
    ex["repos_shipping_crash_with_py_files"] = sum(
        1 for r in ok if r["py_files"] and any(f["listed"] == "yes" and crashes(f)
                                               for f in r["files"]))
    return ex


def sample(results):
    cands = sorted((r for r in results if r["status"] == "ok" and r["py_files"]
                    and any(f["listed"] == "yes" and crashes(f) for f in r["files"])),
                   key=lambda r: r["repo"])
    rng = random.Random(KEY)
    pick = sorted(rng.sample(cands, min(SAMPLE_REPOS, len(cands))), key=lambda r: r["repo"])
    rows = []
    for i, r in enumerate(pick, 1):
        f = sorted((f for f in r["files"] if f["listed"] == "yes" and crashes(f)),
                   key=lambda f: (f["dir"], f["stem"]))[0]
        rows.append({"sample": i, "repo": r["repo"], "src": r["src"], "commit": r["commit"],
                     "dir": f["dir"], "po_file": (f["dir"] + "/" if f["dir"] else "")
                     + f["stem"] + ".po", "rule_code": f["rule_code"], "load": f["load"],
                     "check": f["check"], "py_files": r["py_files"]})
    return rows


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
    SUMMARY["python"] = sys.version.split()[0]
    p = subprocess.run(["msgfmt", "--version"], capture_output=True, text=True)
    SUMMARY["msgfmt"] = _first_line(p.stdout)
    say("python %s, %s" % (SUMMARY["python"], SUMMARY["msgfmt"]))
    prereg = wait_for(PREREG_URL, PREREG_MARK, "PREREG.md")
    SUMMARY["prereg_sha256"] = hashlib.sha256(prereg).hexdigest()
    say("prereg sha256 %s" % SUMMARY["prereg_sha256"])
    tmp_root = tempfile.mkdtemp(prefix="pyhdr-")
    g = load_guard(tmp_root)
    entries = population()
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = [ex.submit(analyse, g, e, tmp_root) for e in entries]
        for i, fut in enumerate(concurrent.futures.as_completed(futs), 1):
            r = fut.result()
            results.append(r)
            if i % 25 == 0 or i == len(futs):
                say("%d of %d repositories done" % (i, len(futs)))
    results.sort(key=lambda r: (r["src"], r["repo"]))
    files = [f for r in results for f in r["files"]]
    write(os.path.join(out, "files.csv"), csv_text(FILE_COLS, files))
    write(os.path.join(out, "flagged.csv"), csv_text(
        FILE_COLS, [f for f in files if f["rule_code"] or f["msgfmt"] == "fail"
                    or (f["load"] and f["load"] != "ok")]))
    for r in results:
        r["files_n"] = len(r["files"])
        r["listed_crash"] = sum(1 for f in r["files"] if f["listed"] == "yes" and crashes(f))
        r["unlisted_crash"] = sum(1 for f in r["files"] if f["listed"] == "no" and crashes(f))
        r["listed_msgfmt_fail"] = sum(1 for f in r["files"] if f["listed"] == "yes"
                                      and f["msgfmt"] == "fail")
    rows = [dict(r, files=r["files_n"]) for r in results]
    write(os.path.join(out, "repos.csv"), csv_text(REPO_COLS, rows))
    SUMMARY["verdicts"] = grade(results)
    SUMMARY["exploratory"] = exploratory(results)
    write(os.path.join(out, "sample.csv"), csv_text(SAMPLE_COLS, sample(results)))
    say(json.dumps(SUMMARY["verdicts"], sort_keys=True))
    say(json.dumps(SUMMARY["exploratory"], sort_keys=True))
    shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    main()
