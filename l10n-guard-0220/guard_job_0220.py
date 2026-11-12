# Builds l10n-guard 0.22.0 in a sealed job from the released 0.21.1 code on main: exact line
# replacements, version bump, test_0220.py; runs every test module before and after; then,
# once PREREG.md is public, tests the lookup mechanism (glibc and Python gettext with catalogs
# installed as zh_cn / zh_CN, pt-BR / pt_BR, nb_no / nb_NO) and runs 0.21.1 and 0.22.0
# check_linguas on 20 po folders at recorded commits, grading T, M1, M2, S and R.
# Nothing is published from here.
# Usage: python -B guard_job_0220.py <out folder>
# Made with AI agents by MV2 of Munim, Inc. Apache-2.0.
import csv
import difflib
import hashlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else "/out"
REPO = os.path.join(HERE, "repo")
OLD, NEW = "0.21.1", "0.22.0"
GUARD_RAW = "https://raw.githubusercontent.com/munimtechnologies/l10n-guard/main/l10n_guard.py"
TARBALL = "https://codeload.github.com/munimtechnologies/l10n-guard/tar.gz/refs/heads/main"
CENSUS = ("https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/"
          "main/")
PREREG_URL = CENSUS + "l10n-guard-0220/PREREG.md"
PREREG_MARK = "l10n-guard 0.22.0 PREREG v1"
WAIT_SECONDS = 8 * 3600
UA = {"User-Agent": "mv2-l10n-guard-check (mv2@munimtech.com)"}
SUMMARY = {"verdicts": {}}
LOG = []

# The 18 po folders of the 0.21.1 check, plus the two case folders: (set, repository, commit,
# po folder).
TARGETS = [
    ("held-out", "https://gitlab.gnome.org/GNOME/NetworkManager-openconnect",
     "27aecc326d989e9304f444cfe46d33e10c9906a5", "po"),
    ("held-out", "https://gitlab.gnome.org/GNOME/gnome-terminal",
     "e633d6ebacde093938db0790d83552ea738ce924", "po"),
    ("held-out", "https://gitlab.gnome.org/World/ShellExtensions/desktop-icons",
     "53a7a0c2c6501a55517b54e317e248534c958fc1", "po"),
    ("held-out", "https://gitlab.gnome.org/GNOME/Incubator/resources",
     "4fff534044062fee3d24caed0bb10e89f6f1abf6", "po"),
    ("held-out", "https://github.com/elementary/flatpak-platform",
     "15e1da2ec709f1cf0faba1064bdbb9c336823485", "platform-data/po"),
    ("held-out", "https://gitlab.gnome.org/World/tootle",
     "b4046da9a7806e11cb77e85b4531c98ff4a33ca5", "po"),
    ("regression", "https://github.com/Jeffser/Pigment",
     "cb725a903cd22f60fe1f17ff03dafa48567cf76b", "po"),
    ("regression", "https://github.com/yeKcim/warmux",
     "b7935f3d6662af821e372e913ddbbe8e2f2b064b", "old/wormux-0.8.1/po"),
    ("regression", "https://github.com/Nokse22/mini-text",
     "abd06bfdeaf4e8ad628dc12540ee51ecebe8a663", "po"),
    ("regression", "https://github.com/sheep-farm/merkato",
     "7eb5ec3bafd99246a48a4ed76bbd0793d0303a5c", "po"),
    ("regression", "https://github.com/tobagin/tempo",
     "bcacc5ca0035a6dbff8d432832db722cec714a96", "po"),
    ("regression", "https://github.com/dubstar-04/Design",
     "d19dedd7c186b72bce17d5eb74745bc3543163a5", "po"),
    ("regression", "https://github.com/tobagin/Draughts",
     "972b8dbf71c55825255d6cb20cfe9f1e31375e0c", "po"),
    ("regression", "https://github.com/phase1geo/minder",
     "fa7c1a71d8ff7fce484265b90727c8f03290bb2a", "po"),
    ("regression", "https://github.com/mijorus/whisper",
     "d454feeea973433a8f2dcebf2d4e69286619ab87", "po"),
    ("regression", "https://github.com/marhkb/pods",
     "349be73c8bc2a3340e2b6187df1c0c676b63be82", "po"),
    ("regression", "https://github.com/donadigo/appeditor",
     "8612fc8f8f812bc50002d4086afa304228a72cae", "po"),
    ("regression", "https://github.com/amit9838/mousam",
     "2a2c53c730319cdbac61c63bb45d78f6dd29348e", "po"),
    ("case", "https://github.com/DeimosHall/Metamorphosis",
     "813da906814951dff27b9638de9c0999a0f9eecf", "po"),
    ("case", "https://gitlab.com/adhami3310/Switcheroo",
     "8f773bb7dc4f6d855dc9725463c6c68d0beed922", "po"),
]

HELPERS = [
    "# --- 0.22.0: gettext spellings ---------------------------------------------------------",
    "# glibc and Python's gettext look a catalog up under the user's locale name (zh_CN, pt_BR,",
    "# nb_NO): '_' before the territory and the territory in capitals, compared exactly on a",
    "# case-sensitive file system. A catalog installed as zh_cn or pt-BR is never looked up.",
    "# Script codes (sr-Latn, zh_Hant) are left to a later check.",
    "",
    "",
    "def _lg_gettext_name(stem):",
    '    """The name gettext looks up for a .po file name: \'_\' between the parts and a two-letter',
    "    territory in capitals (zh_cn -> zh_CN, nb-no -> nb_NO). Script parts, UN M.49 numbers and",
    '    an @modifier are kept as written (sr-Latn -> sr_Latn, es_419, sr@latin)."""',
    '    base, at, mod = stem.partition("@")',
    '    parts = re.split(r"[_-]", base)',
    "    out = [parts[0]]",
    "    for p in parts[1:]:",
    "        out.append(p.upper() if len(p) == 2 and p.isalpha() else p)",
    '    return "_".join(out) + at + mod',
    "",
    "",
    "def _lg_has_script(stem):",
    '    """True when a .po file name has a four-letter script part (zh_Hant, sr-Latn)."""',
    '    parts = re.split(r"[_-]", stem.partition("@")[0])[1:]',
    "    return any(len(p) == 4 and p.isalpha() for p in parts)",
    "",
    "",
    "def _lg_why(stem, gt):",
    '    """Why a .po file name is not the name gettext looks up (gt)."""',
    "    parts = []",
    '    if "-" in stem:',
    "        parts.append(\"use '_'\")",
    '    if gt != stem.replace("-", "_"):',
    '        parts.append("write the territory in capitals")',
    '    return "gettext locale names " + " and ".join(parts)',
    "",
    "",
    "def check_linguas(paths, read):",
]

# Code replacements in l10n_guard.py: (what, old lines compared stripped, new lines relative to
# the indentation of the first old line). Each old run must occur exactly once.
CODE = [
    ("version", ['__version__ = "0.21.1"'], ['__version__ = "0.22.0"']),
    ("helpers", ["def check_linguas(paths, read):"], HELPERS),
    ("docstring",
     ["linguas-unlisted (a <lang>.po file with translated messages that LINGUAS leaves out, so",
      "it is never compiled or installed) and linguas-missing (a listed language with no .po",
      "file beside LINGUAS). paths: every file of a project, relative and '/'-separated;"],
     ["linguas-unlisted (a <lang>.po file with translated messages that LINGUAS leaves out, so",
      "it is never compiled or installed), linguas-missing (a listed language with no .po",
      "file beside LINGUAS) and linguas-spelling (a listed language installed under a name",
      "gettext never looks up, such as zh_cn or pt-BR). paths: every file of a project,",
      "relative and '/'-separated;"]),
    ("unlisted advice",
     ['elif "-" in stem:',
      'gt = stem.replace("-", "_")',
      'fix = ("gettext locale names use \'_\', so a catalog installed as \'%s\' is never "',
      '"looked up; rename %s%s to %s%s.po and add \'%s\' to %s if the "',
      '"translation is ready" % (stem, prefix, po[stem], prefix, gt, gt, rel))'],
     ['elif _lg_gettext_name(stem) != stem:',
      '    gt = _lg_gettext_name(stem)',
      '    fix = ("%s, so a catalog installed as \'%s\' is never looked up; rename %s%s to "',
      '           "%s%s.po and add \'%s\' to %s if the translation is ready"',
      '           % (_lg_why(stem, gt), stem, prefix, po[stem], prefix, gt, gt, rel))']),
    ("spelling check",
     ["for lang in sorted(listed_set):",
      "if lang not in po:",
      "problems.append(issue(",
      'WARNING, "linguas-missing",',
      '"%s lists \'%s\', but there is no %s%s.po beside it" % (rel, lang, prefix, lang),',
      "lang))"],
     ["for lang in sorted(listed_set):",
      "    if lang not in po:",
      "        problems.append(issue(",
      '            WARNING, "linguas-missing",',
      '            "%s lists \'%s\', but there is no %s%s.po beside it" % (rel, lang, prefix, lang),',
      "            lang))",
      "        continue",
      "    gt = _lg_gettext_name(lang)",
      "    if (_lg_language(lang) is None or _lg_has_script(lang) or gt == lang",
      "            or gt in listed_set):",
      "        continue",
      "    problems.append(issue(",
      '        WARNING, "linguas-spelling",',
      '        "%s lists \'%s\', so %s%s is installed as \'%s\', but %s, so it is never looked up "',
      '        "for a \'%s\' locale; rename %s%s to %s%s.po and list \'%s\' instead"',
      "        % (rel, lang, prefix, po[lang], lang, _lg_why(lang, gt), gt, prefix, po[lang],",
      "           prefix, gt, gt), lang))"]),
]

README = [
    ("spelling bullet",
     ["- **Apple `.strings` and String Catalogs**: `.strings` files in UTF-8 or UTF-16, with "
      "`/* */`"],
     ["- **gettext spellings** (0.22.0, code `linguas-spelling`): glibc and Python's `gettext`",
      "  look a catalog up under the user's locale name, such as `zh_CN` or `pt_BR`, and compare",
      "  it exactly, so a language listed in `LINGUAS` as `zh_cn` or `pt-BR` is compiled and",
      "  installed under that name but never loaded on Linux. `linguas-spelling` names the file",
      "  to rename and the entry to list, and `linguas-unlisted` now gives the same spelling in",
      "  its advice (rename `po/zh_cn.po` to `po/zh_CN.po`, rather than add `zh_cn`). Script",
      "  codes (`sr-Latn`, `zh_Hant`) are left to a later check. On macOS and Windows file",
      "  systems, which ignore case, a `zh_cn` folder may still be found.",
      "  ([0.22.0 check](https://github.com/munimtechnologies/android-translation-crash-census/tree/main/l10n-guard-0220))",
      "- **Apple `.strings` and String Catalogs**: `.strings` files in UTF-8 or UTF-16, with "
      "`/* */`"]),
]

SKILL = [
    ("spelling advice",
     ["- `antonym-collision`, `reading-leak`, `java-format-type`, `qt-arg-renumbered`,"],
     ["- `linguas-spelling` (a listed `zh_cn` or `pt-BR`, installed under a name gettext never",
      "  looks up): rename the `.po` file to the spelling it names and change the `LINGUAS` line",
      "  to match; on Weblate or Crowdin projects ask first, because the platform may recreate",
      "  the old file name.",
      "- `antonym-collision`, `reading-leak`, `java-format-type`, `qt-arg-renumbered`,"]),
]

BUMPS = {
    "README.md": [("@v0.21.1", "@v0.22.0"), ("rev: v0.21.1", "rev: v0.22.0")],
    "skills/l10n-guard/SKILL.md": [('version: "0.21.1"', 'version: "0.22.0"'),
                                   ("@v0.21.1", "@v0.22.0"),
                                   ("rev: v0.21.1", "rev: v0.22.0")],
}

# Stage M: catalogs installed under each spelling, looked up from each locale.
MECH_WRONG = ("zh_cn", "pt-BR", "nb_no")
MECH_RIGHT = (("zh_CN", "zh_CN.UTF-8"), ("pt_BR", "pt_BR.UTF-8"), ("nb_NO", "nb_NO.UTF-8"))
LOCALEDEF = (("zh_CN", "zh_CN.UTF-8"), ("pt_BR", "pt_BR.UTF-8"), ("nb_NO", "nb_NO.UTF-8"))
PY_LOOKUP = ("import gettext, sys\n"
             "t = gettext.translation('m', sys.argv[1], fallback=True)\n"
             "sys.stdout.write(t.gettext('Hello'))\n")


def say(msg):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    LOG.append(line)


def write(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def read_text(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def finish(code):
    write(os.path.join(OUT, "summary.json"), json.dumps(SUMMARY, indent=1, sort_keys=True) + "\n")
    write(os.path.join(OUT, "report.txt"), "\n".join(LOG) + "\n")
    sys.exit(code)


def fail(msg):
    say("FAIL: " + msg)
    SUMMARY["failure"] = msg
    finish(3)


def get(url, tries=7):
    """Bytes of url, None on 404. Waits out rate limits (403/429) for up to about an hour."""
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
            time.sleep(600 if e.code in (403, 429) else 10 * (i + 1))
        except Exception as e:  # network errors: retry
            last = repr(e)
            time.sleep(10 * (i + 1))
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
            fail("%s not live after %d s" % (what, WAIT_SECONDS))
        time.sleep(300)


def fetch_repo():
    data = get(TARBALL)
    if data is None:
        fail("tarball not found")
    SUMMARY["repo_tar_sha256"] = hashlib.sha256(data).hexdigest()
    os.makedirs(REPO, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
        for m in tf.getmembers():
            parts = m.name.split("/", 1)
            if len(parts) < 2 or not parts[1] or not (m.isfile() or m.isdir()):
                continue
            m.name = parts[1]
            tf.extract(m, REPO, filter="data")


def repo_files():
    out = []
    for base, dirs, names in os.walk(REPO):
        dirs[:] = sorted(d for d in dirs if d != ".git")
        rel = os.path.relpath(base, REPO).replace(os.sep, "/")
        rel = "" if rel == "." else rel + "/"
        out.extend(rel + n for n in sorted(names))
    return out


def run_tests(stage):
    mods = sorted(n[:-3] for n in os.listdir(REPO) if n.startswith("test_") and n.endswith(".py"))
    res = {}
    for m in mods:
        p = subprocess.run([sys.executable, "-B", "-m", "unittest", "-v", m], cwd=REPO,
                           capture_output=True, text=True, timeout=900)
        text = p.stdout + p.stderr
        write(os.path.join(OUT, "tests", "%s-%s.txt" % (stage, m)), text)
        ran = re.findall(r"^Ran (\d+) tests?", text, re.M)
        skipped = re.findall(r"skipped=(\d+)", text)
        res[m] = {"exit": p.returncode, "ran": int(ran[-1]) if ran else 0,
                  "skipped": int(skipped[-1]) if skipped else 0, "text": text}
        say("%s %s exit=%d ran=%d skipped=%d" % (stage, m, p.returncode, res[m]["ran"],
                                                 res[m]["skipped"]))
    return res


def replace_lines(rel, text, what, old, new):
    crlf = "\r\n" in text
    lines = text.split("\n")
    n = len(old)
    hits = [i for i in range(len(lines) - n + 1)
            if all(lines[i + k].strip() == old[k] for k in range(n))]
    if len(hits) != 1:
        fail("%s %s: old lines found %d times" % (rel, what, len(hits)))
    i = hits[0]
    first = lines[i]
    pad = first[:len(first) - len(first.lstrip())]
    lines[i:i + n] = [(pad + s if s else "") + ("\r" if crlf else "") for s in new]
    say("replaced: %s %s" % (rel, what))
    return "\n".join(lines)


def bump(rel, text):
    for old, new in BUMPS.get(rel, []):
        c = text.count(old)
        if not c:
            fail("%s: no %r to bump" % (rel, old))
        say("version: %s: %d x %r -> %r" % (rel, c, old, new))
        text = text.replace(old, new)
    return text


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------ stage M: the mechanism

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
    po = os.path.join(work, "m-%s.po" % code)
    with open(po, "w", encoding="utf-8", newline="\n") as fh:
        fh.write('msgid ""\nmsgstr ""\n"Content-Type: text/plain; charset=UTF-8\\n"\n\n'
                 'msgid "Hello"\nmsgstr "X-%s"\n' % code)
    r = subprocess.run(["msgfmt", "-o", os.path.join(d, "m.mo"), po], capture_output=True,
                       text=True, timeout=60)
    return "" if r.returncode == 0 else "msgfmt %s: %s" % (code, r.stderr.strip()[-200:])


def _env(root, lang):
    return {"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"), "LANG": lang,
            "TEXTDOMAINDIR": root}


def lookup_c(root, lang):
    """What glibc gettext (the gettext program) prints for Hello with only LANG set."""
    r = subprocess.run(["gettext", "-d", "m", "Hello"], env=_env(root, lang),
                       capture_output=True, text=True, timeout=60)
    return r.stdout.strip()


def lookup_py(root, lang):
    """What Python's gettext module returns for Hello with only LANG set."""
    r = subprocess.run([sys.executable, "-I", "-c", PY_LOOKUP, root], env=_env(root, lang),
                       capture_output=True, text=True, timeout=60)
    return r.stdout.strip()


def run_mechanism():
    """Each catalog sits alone in its own directory tree; for each locale, records which
    catalogs each lookup reaches."""
    locales, notes = build_locales()
    codes = list(MECH_WRONG) + [c for c, _ in MECH_RIGHT]
    out = {"locales": locales, "localedef": notes, "errors": [], "c": {}, "py": {}}
    tmp = tempfile.mkdtemp()
    work = tempfile.mkdtemp(dir=tmp)
    roots = {}
    for code in codes:
        roots[code] = tempfile.mkdtemp(dir=tmp)
        try:
            err = make_catalog(roots[code], code, work)
        except Exception as exc:
            err = "%s %r" % (code, exc)
        if err:
            out["errors"].append(err)
    if out["errors"]:
        return out
    for _, loc in LOCALEDEF:
        out["c"][loc] = sorted(c for c in codes if lookup_c(roots[c], loc) == "X-" + c)
        out["py"][loc] = sorted(c for c in codes if lookup_py(roots[c], loc) == "X-" + c)
    return out


def grade_mechanism(m):
    """M1 (glibc) and M2 (Python): HELD when (a) no wrongly spelled catalog is reached from any
    test locale and (b) each control catalog is reached from its own locale."""
    v = {}
    if m.get("errors"):
        msg = "NOT TESTABLE (catalog build failed)"
        return {"M1": msg, "M2": msg}
    for name, mk, need in (("M1", "c", True), ("M2", "py", False)):
        missing = sorted(n for n, ok in m["locales"].items() if not ok)
        if need and missing:
            v[name] = "NOT TESTABLE (locales missing: %s)" % " ".join(missing)
            continue
        mat = m[mk]
        a = not any(c in MECH_WRONG for loc in mat for c in mat[loc])
        b = all(code in mat.get(loc, []) for code, loc in MECH_RIGHT)
        v[name] = ("HELD" if a and b else
                   "FAILED (no wrongly spelled catalog reached: %s; controls reached: %s)"
                   % (a, b))
    return v


# ------------------------------------------------------------------ stages S and R

def get_json(url):
    data = get(url)
    return None if data is None else json.loads(data.decode("utf-8"))


def split_repo(url):
    u = urllib.parse.urlparse(url)
    return u.netloc, u.path.strip("/")


def list_dir(repo, sha, d):
    """File names in folder d at commit sha, or None when the folder does not exist."""
    host, proj = split_repo(repo)
    if host == "github.com":
        data = get_json("https://api.github.com/repos/%s/contents/%s?ref=%s"
                        % (proj, urllib.parse.quote(d), sha))
        if data is None:
            return None
        return [x["name"] for x in data if x.get("type") == "file"]
    enc = urllib.parse.quote(proj, safe="")
    names, page = [], 1
    while True:
        url = ("https://%s/api/v4/projects/%s/repository/tree?ref=%s&per_page=100&page=%d"
               % (host, enc, sha, page))
        if d:
            url += "&path=" + urllib.parse.quote(d, safe="")
        data = get_json(url)
        if data is None:
            return None if page == 1 else names
        names += [x["name"] for x in data if x.get("type") == "blob"]
        if len(data) < 100:
            return names
        page += 1


def raw_url(repo, sha, path):
    host, proj = split_repo(repo)
    if host == "github.com":
        return "https://raw.githubusercontent.com/%s/%s/%s" % (proj, sha, urllib.parse.quote(path))
    return ("https://%s/api/v4/projects/%s/repository/files/%s/raw?ref=%s"
            % (host, urllib.parse.quote(proj, safe=""), urllib.parse.quote(path, safe=""), sha))


def compare(old, new):
    rows = []
    for set_, repo, sha, d in TARGETS:
        base = {"set": set_, "repo": repo, "commit": sha, "folder": d}
        try:
            parent = d.rpartition("/")[0]
            paths = []
            for x in dict.fromkeys([d, parent, ""]):
                names = list_dir(repo, sha, x)
                if names is None:
                    raise RuntimeError("folder %r not found" % x)
                paths += [(x + "/" + n) if x else n for n in names]
            cache = {}

            def read(p, repo=repo, sha=sha, cache=cache):
                if p not in cache:
                    cache[p] = get(raw_url(repo, sha, p))
                return cache[p]

            po_old, _ = old.check_linguas(paths, read)
            po_new, _ = new.check_linguas(paths, read)
        except Exception as e:
            say("compare %s %s: error %r" % (repo, d, e))
            rows.append(dict(base, status="error: %r" % (e,), code="", key="", old_message="",
                             new_message=""))
            continue
        a = dict(((p["code"], p["key"]), p["message"]) for p in po_old)
        b = dict(((p["code"], p["key"]), p["message"]) for p in po_new)
        say("compare %s %s: %s %s, %s %s" % (repo, d, OLD, sorted(a), NEW, sorted(b)))
        if not a and not b:
            rows.append(dict(base, status="ok", code="", key="", old_message="", new_message=""))
        for k in sorted(set(a) | set(b)):
            rows.append(dict(base, status="ok", code=k[0], key=k[1],
                             old_message=a.get(k, ""), new_message=b.get(k, "")))
    return rows


def grade(rows, new):
    v = {}
    by_folder = {}
    for r in rows:
        by_folder.setdefault((r["set"], r["repo"], r["folder"]), []).append(r)
    ok18 = [k for k, rs in by_folder.items() if k[0] != "case" and rs[0]["status"] == "ok"]
    old_codes = ("linguas-unlisted", "linguas-missing")
    s_rows = [r for r in rows if r["set"] != "case" and r["status"] == "ok"
              and r["code"] in old_codes]
    differ = []
    for r in s_rows:
        if not r["old_message"] or not r["new_message"]:
            differ.append(r)
            continue
        case_key = new._lg_gettext_name(r["key"]) != r["key"].replace("-", "_")
        if r["old_message"] != r["new_message"] and not case_key:
            differ.append(r)
    if len(ok18) < 16:
        v["S"] = "NOT TESTABLE (%d of 18 folders read)" % len(ok18)
    elif differ:
        v["S"] = "FAILED (%d of %d findings differ; %d of 18 folders read)" % (
            len(differ), len(s_rows), len(ok18))
    else:
        v["S"] = "HELD (%d of 18 folders read; %d findings, none differ)" % (len(ok18),
                                                                           len(s_rows))
    spelling = [r for r in rows if r["status"] == "ok" and r["code"] == "linguas-spelling"]
    SUMMARY["linguas_spelling_hits"] = ["%s %s %s" % (r["repo"], r["folder"], r["key"])
                                        for r in spelling]
    rv = []
    for _, repo, _, d in [t for t in TARGETS if t[0] == "case"]:
        hit = [r for r in rows if r["repo"] == repo and r["folder"] == d
               and r["status"] == "ok" and r["code"] == "linguas-unlisted"
               and r["key"] == "zh_cn"]
        if not hit:
            rv.append("NOT TESTABLE")
            continue
        r = hit[0]
        ok = ("rename po/zh_cn.po to po/zh_CN.po and add 'zh_CN' to po/LINGUAS"
              in r["new_message"] and "add 'zh_cn' to po/LINGUAS" in r["old_message"])
        rv.append("HELD" if ok else "FAILED")
    names = [t[1].rsplit("/", 1)[-1] for t in TARGETS if t[0] == "case"]
    detail = ", ".join("%s %s" % (n, x) for n, x in zip(names, rv))
    if all(x == "HELD" for x in rv):
        v["R"] = "HELD (%s)" % detail
    elif any(x == "FAILED" for x in rv):
        v["R"] = "FAILED (%s)" % detail
    else:
        v["R"] = "NOT TESTABLE (%s)" % detail
    return v


def main():
    os.makedirs(OUT, exist_ok=True)
    wait_for(GUARD_RAW, '__version__ = "%s"' % OLD, "l10n-guard %s on main" % OLD)
    fetch_repo()
    files = repo_files()
    say("repo files: %d" % len(files))
    originals = {}
    for rel in ("l10n_guard.py", "README.md", "skills/l10n-guard/SKILL.md"):
        if rel not in files:
            fail("%s not in the repository" % rel)
        originals[rel] = read_text(os.path.join(REPO, rel))
    if '__version__ = "%s"' % OLD not in originals["l10n_guard.py"]:
        fail("l10n_guard.py in the tarball is not %s" % OLD)
    write(os.path.join(OUT, "old", "l10n_guard_0211.py"), originals["l10n_guard.py"])
    before = run_tests("before")
    SUMMARY["before"] = dict((m, {"exit": r["exit"], "ran": r["ran"], "skipped": r["skipped"]})
                             for m, r in before.items())

    patched = dict(originals)
    t = originals["l10n_guard.py"]
    for what, old, new in CODE:
        t = replace_lines("l10n_guard.py", t, what, old, new)
    patched["l10n_guard.py"] = t
    t = bump("README.md", originals["README.md"])
    for what, old, new in README:
        t = replace_lines("README.md", t, what, old, new)
    patched["README.md"] = t
    rel = "skills/l10n-guard/SKILL.md"
    t = bump(rel, originals[rel])
    for what, old, new in SKILL:
        t = replace_lines(rel, t, what, old, new)
    patched[rel] = t
    patched["test_0220.py"] = read_text(os.path.join(HERE, "test_0220.py"))
    left = ["%s:%d: %s" % (r, n + 1, line.strip()) for r in sorted(patched)
            for n, line in enumerate(patched[r].split("\n")) if OLD in line]
    write(os.path.join(OUT, "still-0211.txt"), "\n".join(left) + "\n")
    say("lines still mentioning %s: %d (see still-0211.txt)" % (OLD, len(left)))

    diff = []
    for r in sorted(patched):
        if patched[r] != originals.get(r):
            write(os.path.join(REPO, r), patched[r])
            write(os.path.join(OUT, "pkg", r), patched[r])
            diff += difflib.unified_diff(originals.get(r, "").splitlines(True),
                                         patched[r].splitlines(True), "a/" + r, "b/" + r)
    write(os.path.join(OUT, "patch.diff"), "".join(diff))
    SUMMARY["changed"] = sorted(r for r in patched if patched[r] != originals.get(r))

    after = run_tests("after")
    SUMMARY["after"] = dict((m, {"exit": r["exit"], "ran": r["ran"], "skipped": r["skipped"]})
                            for m, r in after.items())
    failing = sorted(m for m, r in after.items() if r["exit"] != 0)
    SUMMARY["failing_after"] = failing
    T = "HELD" if not failing and "test_0220" in after else "FAILED"
    SUMMARY["verdicts"]["T"] = T
    say("T: %s; failing after: %s" % (T, failing))
    if T != "HELD":
        for k in ("M1", "M2", "S", "R"):
            SUMMARY["verdicts"][k] = "NOT TESTABLE (T failed)"
        finish(0)

    prereg = wait_for(PREREG_URL, PREREG_MARK, "PREREG.md")
    SUMMARY["prereg_sha256"] = hashlib.sha256(prereg).hexdigest()
    say("prereg sha256 %s" % SUMMARY["prereg_sha256"])

    mech = run_mechanism()
    write(os.path.join(OUT, "mechanism.json"), json.dumps(mech, indent=1, sort_keys=True) + "\n")
    SUMMARY["verdicts"].update(grade_mechanism(mech))
    say("mechanism: %s" % json.dumps(mech, sort_keys=True))

    old = load("l10n_guard_0211", os.path.join(OUT, "old", "l10n_guard_0211.py"))
    new = load("l10n_guard_0220", os.path.join(REPO, "l10n_guard.py"))
    if (old.__version__, new.__version__) != (OLD, NEW):
        fail("loaded versions %s / %s" % (old.__version__, new.__version__))
    rows = compare(old, new)
    fields = ["set", "repo", "commit", "folder", "status", "code", "key", "old_message",
              "new_message"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    write(os.path.join(OUT, "compare.csv"), buf.getvalue())
    SUMMARY["verdicts"].update(grade(rows, new))
    say(json.dumps(SUMMARY["verdicts"], sort_keys=True))
    finish(0)


if __name__ == "__main__":
    main()
