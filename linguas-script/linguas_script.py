# Census: gettext catalogs named with a script subtag (zh_Hans, zh_Hant, sr_Latn ...) in the
# po/LINGUAS files of the source repositories of the apps on Flathub.
#
# glibc's gettext and Python's gettext module find a catalog from the user's locale name, which
# has the form language[_territory][.codeset][@modifier]. They try that name and shorter forms of
# it (zh_CN.UTF-8, zh_CN, zh.UTF-8, zh), never a script. A catalog that Meson or autotools installs
# as share/locale/zh_Hans/LC_MESSAGES is therefore found only when the user sets LANGUAGE=zh_Hans
# by hand. Stage M checks this claim with the real tools before any repository is read; the census
# then counts how often apps list such names. Pre-registered in linguas-script/PREREG.md.
# Standard library, git and GNU gettext only. Made with AI agents by MV2 of Munim, Inc.
# Licence: Apache-2.0.
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
              "main/linguas-script/PREREG.md")
PREREG_MARK = "linguas-script census PREREG v1"
KEY = "linguas-script census v1"
UA = "linguas-script-census (MV2, Munim, Inc.; mv2@munimtech.com)"
CONTROL_REPOS = ("https://github.com/flattool/warehouse", "https://github.com/marhkb/pods")

TWO_PART_HOSTS = frozenset(["github.com", "codeberg.org", "bitbucket.org", "git.sr.ht"])
GITLAB_HOSTS = frozenset(["gitlab.com", "gitlab.gnome.org", "invent.kde.org", "framagit.org",
                          "gitlab.freedesktop.org", "salsa.debian.org", "gitlab.xfce.org"])
GITLAB_STOP = frozenset(["tree", "blob", "issues", "merge_requests", "wikis", "commits",
                         "releases", "tags"])
GROUP_ORDER = ("gnome", "weblate", "crowdin", "transifex", "other", "none")
VENDOR = frozenset(["subprojects", "vendor", "vendors", "third_party", "thirdparty", "third-party",
                    "3rdparty", "external", "externals", "deps", "node_modules", "submodules"])
GOVERNED = ("meson", "autotools")

GETTEXT_CALL = re.compile(r"\bgettext\s*\(")
LANG_KW = re.compile(r"\blanguages\s*:")
AC_MACROS = re.compile(r"\b(?:AM_GNU_GETTEXT|IT_PROG_INTLTOOL|AC_PROG_INTLTOOL|AM_GLIB_GNU_GETTEXT)")

MAX_BYTES = 5000000
MAX_DIRS = 20
MAX_READ = 10

# Pre-registered numbers (PREREG.md).
GATE_READ = 1000
GATE_GOVERNED = 150
MIN_TESTABLE = 4
P3_MIN_GROUP = 20
SAMPLE_REPOS = 12

# ISO 15924 script codes that appear in locale names (lower case).
SCRIPTS = frozenset("""adlm arab armn beng bopo brai cans cher cyrl deva dsrt ethi geor grek gujr
guru hang hani hans hant hebr hira jpan kana khmr knda kore laoo latn mlym mong mtei mymr nkoo olck
orya rohg shaw sinh syrc taml telu tfng thaa thai tibt vaii yiii""".split())

# Usual POSIX names for some script-coded names (exploratory column only).
SUGGEST = {"zh_Hans": "zh_CN", "zh_Hant": "zh_TW", "sr_Latn": "sr@latin", "sr_Cyrl": "sr",
           "uz_Latn": "uz", "uz_Cyrl": "uz@cyrillic", "az_Latn": "az", "bs_Latn": "bs"}


def key(*parts):
    return hashlib.sha256("|".join((KEY,) + parts).encode("utf-8")).hexdigest()


def decode(data):
    return data.decode("utf-8-sig", "replace")


# ------------------------------------------------------------------ codes

def split_code(code):
    """(language, [parts after the language], modifier) of a gettext-style code; the codeset
    (.UTF-8) is dropped. zh_Hant_HK -> ("zh", ["Hant", "HK"], "")."""
    base, _, mod = code.partition("@")
    base = base.partition(".")[0]
    parts = base.split("_")
    return parts[0], parts[1:], mod


def classify(code):
    """'hyphen' for a BCP-style name with '-' (pt-BR, zh-Hans), 'script' for a name with an
    ISO 15924 script code after '_' (zh_Hans, sr_Latn, zh_Hant_HK; any case), else 'posix'.
    Four-letter parts that are not script codes (de_FORM) stay 'posix'."""
    if "-" in code:
        return "hyphen"
    _, rest, _ = split_code(code)
    if any(p.lower() in SCRIPTS for p in rest):
        return "script"
    return "posix"


def reachable_siblings(code, tokens):
    """Listed POSIX-style codes of the same language as code (other than code itself)."""
    lang = split_code(code)[0].lower()
    return sorted(t for t in set(tokens) if t != code and classify(t) == "posix"
                  and split_code(t)[0].lower() == lang)


def dir_findings(tokens):
    """For the words of one LINGUAS file: script (listed script-coded codes), hyphen (listed codes
    with '-'), lost (script codes with no listed POSIX-style code of the same language, so no
    default locale reaches any catalog of that language) and siblings {script code: [...]}."""
    toks = []
    for t in tokens:
        if t not in toks:
            toks.append(t)
    script = [t for t in toks if classify(t) == "script"]
    hyphen = [t for t in toks if classify(t) == "hyphen"]
    sib = {t: reachable_siblings(t, toks) for t in script}
    lost = [t for t in script if not sib[t]]
    return {"script": script, "hyphen": hyphen, "lost": lost, "siblings": sib}


# ------------------------------------------------------------------ stage M: the mechanism

MECH_SCRIPT = ("zh_Hans", "zh_Hant", "sr_Latn")
MECH_POSIX = (("zh_CN", "zh_CN.UTF-8"), ("zh_TW", "zh_TW.UTF-8"),
              ("sr@latin", "sr_RS.UTF-8@latin"), ("pt_BR", "pt_BR.UTF-8"))
MECH_LOCALES = ("zh_CN.UTF-8", "zh_TW.UTF-8", "zh_HK.UTF-8", "zh_SG.UTF-8", "sr_RS.UTF-8@latin",
                "pt_BR.UTF-8")
MECH_LANGUAGE_LANG = (("zh_Hans", "zh_CN.UTF-8"), ("zh_Hant", "zh_TW.UTF-8"),
                      ("sr_Latn", "sr_RS.UTF-8@latin"))
LOCALEDEF = (("zh_CN", "zh_CN.UTF-8"), ("zh_TW", "zh_TW.UTF-8"), ("zh_HK", "zh_HK.UTF-8"),
             ("zh_SG", "zh_SG.UTF-8"), ("sr_RS@latin", "sr_RS.UTF-8@latin"),
             ("pt_BR", "pt_BR.UTF-8"))
PY_LOOKUP = ("import gettext, sys\n"
             "t = gettext.translation('m', sys.argv[1], fallback=True)\n"
             "sys.stdout.write(t.gettext('Hello'))\n")


def locale_key(name):
    """locale -a spells zh_CN.UTF-8 as zh_CN.utf8; compare without case and '-'."""
    return name.lower().replace("utf-8", "utf8")


def build_locales():
    """Generates the test locales with localedef. Returns ({name: available}, notes)."""
    notes = []
    for src, name in LOCALEDEF:
        try:
            r = subprocess.run(["localedef", "-i", src, "-f", "UTF-8", name], capture_output=True,
                               text=True, timeout=300)
            notes.append("%s exit %d %s" % (name, r.returncode, r.stderr.strip()[-160:]))
        except Exception as exc:  # recorded; availability is checked below
            notes.append("%s %r" % (name, exc))
    try:
        avail = {locale_key(x.strip()) for x in subprocess.run(
            ["locale", "-a"], capture_output=True, text=True, timeout=60).stdout.splitlines()}
    except Exception as exc:
        notes.append("locale -a %r" % (exc,))
        avail = set()
    return {name: locale_key(name) in avail for _, name in LOCALEDEF}, notes


def make_catalog(root, code, work):
    """Compiles a one-message catalog (Hello -> X-<code>) to root/<code>/LC_MESSAGES/m.mo."""
    d = os.path.join(root, code, "LC_MESSAGES")
    os.makedirs(d)
    po = os.path.join(work, "m-%s.po" % code.replace("@", "-"))
    with open(po, "w", encoding="utf-8", newline="\n") as fh:
        fh.write('msgid ""\nmsgstr ""\n"Content-Type: text/plain; charset=UTF-8\\n"\n\n'
                 'msgid "Hello"\nmsgstr "X-%s"\n' % code)
    r = subprocess.run(["msgfmt", "-o", os.path.join(d, "m.mo"), po], capture_output=True,
                       text=True, timeout=60)
    return "" if r.returncode == 0 else "msgfmt %s: %s" % (code, r.stderr.strip()[-200:])


def _env(root, lang, language):
    env = {"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"), "LANG": lang,
           "TEXTDOMAINDIR": root}
    if language:
        env["LANGUAGE"] = language
    return env


def lookup_c(root, lang, language=None):
    """What glibc gettext (the gettext program) prints for Hello with only LANG (and LANGUAGE)."""
    r = subprocess.run(["gettext", "-d", "m", "Hello"], env=_env(root, lang, language),
                       capture_output=True, text=True, timeout=60)
    return r.stdout.strip()


def lookup_py(root, lang, language=None):
    """What Python's gettext module returns for Hello with only LANG (and LANGUAGE) set."""
    r = subprocess.run([sys.executable, "-I", "-c", PY_LOOKUP, root],
                       env=_env(root, lang, language), capture_output=True, text=True, timeout=60)
    return r.stdout.strip()


def run_mechanism(tmp_root):
    """Each catalog sits alone in its own directory tree; for each locale, records which
    catalogs each lookup reaches, and whether LANGUAGE=<script code> reaches the script ones."""
    locales, notes = build_locales()
    codes = list(MECH_SCRIPT) + [c for c, _ in MECH_POSIX]
    out = {"locales": locales, "localedef": notes, "errors": [], "c": {}, "py": {},
           "c_language": {}, "py_language": {}}
    roots = {}
    work = tempfile.mkdtemp(dir=tmp_root)
    for code in codes:
        roots[code] = tempfile.mkdtemp(dir=tmp_root)
        try:
            err = make_catalog(roots[code], code, work)
        except Exception as exc:
            err = "%s %r" % (code, exc)
        if err:
            out["errors"].append(err)
    if out["errors"]:
        return out
    for loc in MECH_LOCALES:
        out["c"][loc] = sorted(c for c in codes if lookup_c(roots[c], loc) == "X-" + c)
        out["py"][loc] = sorted(c for c in codes if lookup_py(roots[c], loc) == "X-" + c)
    for code, loc in MECH_LANGUAGE_LANG:
        out["c_language"][code] = lookup_c(roots[code], loc, code) == "X-" + code
        out["py_language"][code] = lookup_py(roots[code], loc, code) == "X-" + code
    return out


def grade_mechanism(m):
    """M1 (glibc) and M2 (Python): HELD when (a) no script-coded catalog is reached from any test
    locale, (b) each POSIX control catalog is reached from its own locale and (c) LANGUAGE set to
    the script code reaches each script-coded catalog."""
    v = {}
    if m.get("errors"):
        msg = "NOT TESTABLE (catalog build failed)"
        return {"M1": msg, "M2": msg}
    for name, mk, lk, need in (("M1", "c", "c_language", True),
                               ("M2", "py", "py_language", False)):
        missing = sorted(n for n, ok in m["locales"].items() if not ok)
        if need and missing:
            v[name] = "NOT TESTABLE (locales missing: %s)" % " ".join(missing)
            continue
        mat = m[mk]
        a = not any(c in MECH_SCRIPT for loc in mat for c in mat[loc])
        b = all(code in mat.get(loc, []) for code, loc in MECH_POSIX)
        c = all(m[lk].get(code) for code in MECH_SCRIPT)
        v[name] = ("HELD" if a and b and c else
                   "FAILED (no script catalog reached: %s; controls reached: %s; LANGUAGE "
                   "reaches script catalogs: %s)" % (a, b, c))
    return v


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
    urls = app_urls(meta)
    r = repo_url(urls.get("vcs_browser"))
    if r:
        return r, "vcs_browser"
    r = repo_url(urls.get("homepage"))
    if r:
        return r, "homepage"
    return None, ""


def translate_group(meta):
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
    repos = {}
    stats = {"apps_listed": len(apps), "apps_fetched": 0, "apps_with_repo": 0}
    for app_id in sorted(apps):
        meta = apps[app_id]
        if not isinstance(meta, dict):
            continue
        stats["apps_fetched"] += 1
        url, source = app_repo(meta)
        if not url:
            continue
        stats["apps_with_repo"] += 1
        r = repos.setdefault(url.lower(), {"repo": url, "apps": [], "groups": set(),
                                           "source": source})
        r["apps"].append(app_id)
        r["groups"].add(translate_group(meta))
    out = []
    for k in sorted(repos):
        r = repos[k]
        out.append({"repo": r["repo"], "apps": r["apps"], "source": r["source"],
                    "group": next(g for g in GROUP_ORDER if g in r["groups"])})
    return out, stats


# ------------------------------------------------------------------ files

def is_vendored(path):
    return any(part.lower() in VENDOR for part in path.split("/") if part)


def po_dirs(paths):
    """{dir: {stem: path}} for each own (not vendored) directory holding LINGUAS and .po files."""
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
    """Languages as Meson reads LINGUAS: lines starting with '#' are skipped."""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.extend(line.split())
    return out


def configure_paths(d, paths_set):
    parent = d.rpartition("/")[0] if "/" in d else ""
    out = []
    for base in (parent, ""):
        for n in ("configure.ac", "configure.in"):
            p = base + "/" + n if base else n
            if p in paths_set and p not in out:
                out.append(p)
    return out


def build_kind(meson_text, configure_texts):
    if meson_text and GETTEXT_CALL.search(meson_text):
        return "meson-explicit" if LANG_KW.search(meson_text) else "meson"
    if any(t and AC_MACROS.search(t) for t in configure_texts):
        return "autotools"
    return "other"


def _unquote(s):
    i, j = s.find('"'), s.rfind('"')
    return s[i + 1:j] if i != -1 and j > i else ""


def po_stats(data):
    """{"entries", "translated", "fuzzy"} for a .po file (bytes); header and #~ entries skipped."""
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
    r = git(["-C", s, "cat-file", "-p", "%s:%s" % (commit, path)], binary=True)
    if r.returncode != 0 or len(r.stdout) > MAX_BYTES:
        return None
    return r.stdout


def analyse(entry, tmp_root):
    res = {"repo": entry["repo"], "group": entry.get("group", ""), "apps": entry.get("apps", []),
           "status": "ok", "commit": "", "n_paths": 0, "dirs": []}
    t0 = time.time()
    d = tempfile.mkdtemp(dir=tmp_root)
    try:
        s, res["commit"], paths = clone(entry["repo"], d)
        res["n_paths"] = len(paths)
        pset = set(paths)
        dirs = po_dirs(paths)
        cache = {}

        def read(p):
            if p not in cache:
                cache[p] = read_blob(s, res["commit"], p) if p in pset else None
            return cache[p]

        for dname in sorted(dirs)[:MAX_DIRS]:
            po = dirs[dname]
            prefix = dname + "/" if dname else ""
            lin = read(prefix + "LINGUAS")
            mb = read(prefix + "meson.build")
            conf = [decode(x) for x in (read(p) for p in configure_paths(dname, pset))
                    if x is not None]
            build = build_kind(decode(mb) if mb is not None else None, conf)
            rec = {"dir": dname, "build": build, "n_po": len(po), "linguas_read": lin is not None,
                   "n_listed": 0, "script": [], "hyphen": [], "lost": [], "siblings": {},
                   "remap": [], "files": []}
            if lin is not None:
                tokens = (meson_linguas(decode(lin)) if build.startswith("meson")
                          else gnu_linguas(decode(lin)))
                rec["n_listed"] = len(tokens)
                rec.update(dir_findings(tokens))
                if build in GOVERNED and rec["script"]:
                    root_mb = read("meson.build")
                    hint = "\n".join(decode(x) for x in (mb, root_mb) if x is not None)
                    rec["remap"] = sorted(t for t in rec["script"] if t in hint)
                    for t in rec["lost"][:MAX_READ]:
                        f = {"code": t, "path": po.get(t, ""), "entries": None,
                             "translated": None, "fuzzy": None, "substantive": "no file"}
                        if t in po:
                            data = read(po[t])
                            st = po_stats(data) if data is not None else None
                            f["substantive"] = substantive(st)
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
    """Pre-registered verdicts G and P1-P5 (PREREG.md) and the counts behind them."""
    read = [r for r in results if r["status"] == "ok"]
    gov = [r for r in read if governed_dirs(r)]
    flagged = [r for r in gov if any(x["script"] for x in governed_dirs(r))]
    lost_repos = [r for r in flagged if any(x["lost"] for x in governed_dirs(r))]
    fl = {id(r) for r in flagged}
    n, k = len(gov), len(flagged)
    tokens = [t for r in flagged for x in governed_dirs(r) for t in x["script"]]
    zh = [t for t in tokens if split_code(t)[0].lower() == "zh"]
    files = [f for r in flagged for x in governed_dirs(r) for f in x["files"]]
    known = [f for f in files if f["substantive"] in ("yes", "no")]
    yes = [f for f in known if f["substantive"] == "yes"]
    wn = [r for r in gov if r["group"] == "weblate"]
    on = [r for r in gov if r["group"] != "weblate"]
    wk = sum(1 for r in wn if id(r) in fl)
    ok = sum(1 for r in on if id(r) in fl)
    v = {}
    gate = len(read) >= GATE_READ and n >= GATE_GOVERNED
    v["G"] = ("PASSED" if gate else "FAILED (%d read, %d with a governed LINGUAS directory)"
              % (len(read), n))
    if not gate:
        for p in ("P1", "P2", "P3", "P4", "P5"):
            v[p] = "NOT TESTABLE (gate)"
    else:
        v["P1"] = "HELD" if (100 * k >= 2 * n and 100 * k <= 15 * n) else "FAILED"
        v["P2"] = ("NOT TESTABLE (%d flagged repositories)" % k if k < MIN_TESTABLE
                   else "HELD" if 2 * len(lost_repos) >= k else "FAILED")
        if len(wn) < P3_MIN_GROUP or len(on) < P3_MIN_GROUP or k < MIN_TESTABLE:
            v["P3"] = "NOT TESTABLE (%d weblate, %d other, %d flagged)" % (len(wn), len(on), k)
        else:
            v["P3"] = "HELD" if wk * len(on) > ok * len(wn) else "FAILED"
        v["P4"] = ("NOT TESTABLE (%d script-coded codes)" % len(tokens)
                   if len(tokens) < MIN_TESTABLE
                   else "HELD" if 4 * len(zh) >= 3 * len(tokens) else "FAILED")
        v["P5"] = ("NOT TESTABLE (%d lost catalogs with known content)" % len(known)
                   if len(known) < MIN_TESTABLE
                   else "HELD" if 4 * len(yes) >= 3 * len(known) else "FAILED")
    codes = {}
    for t in tokens:
        codes[t] = codes.get(t, 0) + 1
    hyphen = {}
    for r in gov:
        for x in governed_dirs(r):
            for t in x["hyphen"]:
                hyphen[t] = hyphen.get(t, 0) + 1
    counts = {
        "read": len(read), "governed_repos": n, "flagged_repos": k,
        "flagged_share_pct": round(100.0 * k / n, 2) if n else None,
        "lost_repos": len(lost_repos), "script_codes": len(tokens), "zh_script_codes": len(zh),
        "lost_files_read": len(files), "content_known": len(known), "content_substantive": len(yes),
        "lost_translated_messages": sum(f["translated"] or 0 for f in files),
        "weblate_governed": len(wn), "weblate_flagged": wk, "other_governed": len(on),
        "other_flagged": ok, "codes": dict(sorted(codes.items(), key=lambda kv: (-kv[1], kv[0]))),
        "hyphen_codes_exploratory": dict(sorted(hyphen.items(),
                                                key=lambda kv: (-kv[1], kv[0]))[:40]),
        "remap_hint_repos": sum(1 for r in flagged if any(x["remap"] for x in governed_dirs(r))),
    }
    return v, counts, flagged


def sample_rows(flagged):
    """One lost catalog with a .po file from each of the first SAMPLE_REPOS repositories (hash
    order) that have one."""
    rows = []
    cand_repos = [r for r in flagged
                  if any(f["path"] for x in governed_dirs(r) for f in x["files"])]
    for r in sorted(cand_repos, key=lambda r: key(r["repo"]))[:SAMPLE_REPOS]:
        cands = [(x, f) for x in governed_dirs(r) for f in x["files"] if f["path"]]
        x, f = sorted(cands, key=lambda xf: key(r["repo"], xf[1]["path"]))[0]
        rows.append({"sample": len(rows) + 1, "repo": r["repo"], "commit": r["commit"],
                     "group": r["group"], "dir": x["dir"], "build": x["build"],
                     "po_file": f["path"], "code": f["code"], "entries": f["entries"],
                     "translated": f["translated"], "remap_hint": "yes" if x["remap"] else "no",
                     "label": "", "note": ""})
    return rows


def write_csv(path, cols, rows):
    with open(path, "w", encoding="utf-8", errors="replace", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for row in rows:
            w.writerow({c: ("" if row.get(c) is None else str(row.get(c))) for c in cols})


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
    """The pipeline must find a script-coded, lost code in the Meson po/LINGUAS of at least one
    control repository (both listed zh_Hans when this was written). Returns "" when it passes."""
    errs = []
    for url in CONTROL_REPOS:
        r = analyse({"repo": url, "group": "control"}, tmp_root)
        x = [d for d in r["dirs"] if d["dir"] == "po"]
        if r["status"] != "ok" or not x:
            errs.append("%s: %s, po dir %s" % (url, r["status"], bool(x)))
            continue
        x = x[0]
        if x["build"] == "meson" and "zh_Hans" in x["script"] and "zh_Hans" in x["lost"]:
            return ""
        errs.append("%s: build %s script %s lost %s" % (url, x["build"], x["script"], x["lost"]))
    return "; ".join(errs)


CAT_COLS = ["repo", "commit", "group", "dir", "build", "code", "lost", "siblings", "suggest",
            "remap_hint"]
FILE_COLS = ["repo", "commit", "group", "dir", "code", "path", "entries", "translated", "fuzzy",
             "substantive"]
SAMPLE_COLS = ["sample", "repo", "commit", "group", "dir", "build", "po_file", "code", "entries",
               "translated", "remap_hint", "label", "note"]


def main(out, say, workers=8, prereg_wait_minutes=360):
    started = time.time()
    tmp_root = tempfile.mkdtemp(prefix="lscript-")
    mech = run_mechanism(tmp_root)
    mech_v = grade_mechanism(mech)
    with open(os.path.join(out, "mechanism.json"), "w", encoding="utf-8") as fh:
        json.dump({"verdicts": mech_v, "detail": mech}, fh, ensure_ascii=False, indent=1,
                  sort_keys=True)
    say("mechanism %s" % json.dumps(mech_v))
    err = control(tmp_root)
    if err:
        say("control failed: " + err)
        return 3
    say("control passed")
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
    ids = [x for x in json.loads(raw.decode("utf-8")) if isinstance(x, str)]
    say("flathub lists %d apps" % len(ids))
    apps = fetch_apps(ids)
    repos, pop_stats = population(apps)
    say("%d apps fetched, %d repositories" % (pop_stats["apps_fetched"], len(repos)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(lambda e: analyse(e, tmp_root), repos))
    shutil.rmtree(tmp_root, ignore_errors=True)

    with open(os.path.join(out, "results.jsonl"), "w", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    write_csv(os.path.join(out, "catalogs.csv"), CAT_COLS,
              [{"repo": r["repo"], "commit": r["commit"], "group": r["group"], "dir": x["dir"],
                "build": x["build"], "code": t, "lost": "yes" if t in x["lost"] else "no",
                "siblings": " ".join(x["siblings"].get(t, [])), "suggest": SUGGEST.get(t, ""),
                "remap_hint": "yes" if t in x["remap"] else "no"}
               for r in results if r["status"] == "ok" for x in governed_dirs(r)
               for t in x["script"]])
    write_csv(os.path.join(out, "lost_files.csv"), FILE_COLS,
              [dict(f, repo=r["repo"], commit=r["commit"], group=r["group"], dir=x["dir"])
               for r in results if r["status"] == "ok" for x in governed_dirs(r)
               for f in x["files"]])
    verdicts, counts, flagged = grade(results)
    rows = sample_rows(flagged) if verdicts["G"] == "PASSED" else []
    write_csv(os.path.join(out, "sample.csv"), SAMPLE_COLS, rows)
    verdicts["H"] = ("PENDING HAND CHECK (%d catalogs)" % len(rows) if len(rows) >= 4
                     else "NOT TESTABLE (sample of %d)" % len(rows))
    verdicts.update(mech_v)
    status = {}
    for r in results:
        st = r["status"] if r["status"] in ("ok", "timeout") else r["status"].split(":")[0]
        status[st] = status.get(st, 0) + 1
    summary = {"verdicts": verdicts, "counts": counts, "prereg_sha256": prereg_sha,
               "flathub_list_sha256": hashlib.sha256(raw).hexdigest(),
               "flathub_list_apps": len(ids), "population": pop_stats,
               "repositories": len(repos), "status": dict(sorted(status.items())),
               "minutes": round((time.time() - started) / 60, 1)}
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1, sort_keys=True)
    say(json.dumps(verdicts))
    return 0


if __name__ == "__main__":
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "out"
    os.makedirs(out_dir, exist_ok=True)

    def say(msg):
        print(time.strftime("%H:%M:%S"), msg, flush=True)

    sys.exit(main(out_dir, say))
