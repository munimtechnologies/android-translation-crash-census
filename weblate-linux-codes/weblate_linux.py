# weblate-linux-codes v1: which catalog do glibc's gettext and Python's gettext module load when a
# project names its gettext files with Weblate's "Linux style" language codes?
#
# The job reads the two tables that style uses (LEGACY_CODES and LINUX_CODES in Weblate's
# weblate/formats/base.py) with ast (the file is never imported or run), installs one-message
# catalogs under the names they give, and asks glibc's gettext program and Python's gettext module
# which catalog each real locale reaches with only LANG set. It measures each locale's own script
# from its name for Monday. Pre-registered in weblate-linux-codes/PREREG.md.
# Standard library and GNU gettext only. Made with AI agents by MV2 of Munim, Inc.
# Licence: Apache-2.0.
import ast
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.request

PINNED = "e748c7be19c947d65b9936fe56be10b363e5c742"
BASE_URL = "https://raw.githubusercontent.com/WeblateOrg/weblate/%s/weblate/formats/base.py"
ALIASES_URL = "https://raw.githubusercontent.com/WeblateOrg/language-data/main/aliases.csv"
LANGUAGES_URL = "https://raw.githubusercontent.com/WeblateOrg/language-data/main/languages.csv"
PREREG_URL = ("https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/"
              "main/weblate-linux-codes/PREREG.md")
PREREG_MARK = "weblate-linux-codes PREREG v1"
UA = "weblate-linux-codes (MV2, Munim, Inc.; mv2@munimtech.com)"

TABLES = ("LEGACY_CODES", "LINUX_CODES")
FUNCS = ("get_language_posix", "get_language_legacy", "get_language_linux")

LOCALEDEF = (("sr_RS", "sr_RS.UTF-8"), ("sr_RS@latin", "sr_RS.UTF-8@latin"),
             ("sr_ME", "sr_ME.UTF-8"), ("uz_UZ", "uz_UZ.UTF-8"),
             ("uz_UZ@cyrillic", "uz_UZ.UTF-8@cyrillic"), ("be_BY", "be_BY.UTF-8"),
             ("be_BY@latin", "be_BY.UTF-8@latin"), ("zh_CN", "zh_CN.UTF-8"),
             ("zh_TW", "zh_TW.UTF-8"))
OPTIONAL_LOCALES = frozenset(["sr_ME.UTF-8"])

# Each project: (Weblate code, script its text is written in).
TREES = (("serbian", (("sr_Cyrl", "Cyrl"), ("sr_Latn", "Latn"))),
         ("uzbek", (("uz", "Cyrl"), ("uz_Latn", "Latn"))),
         ("belarusian", (("be", "Cyrl"), ("be_Latn", "Latn"))),
         ("chinese", (("zh_Hans", "Hans"), ("zh_Hant", "Hant"))))
TREE_LOCALES = {"serbian": ("sr_RS.UTF-8", "sr_RS.UTF-8@latin", "sr_ME.UTF-8"),
                "uzbek": ("uz_UZ.UTF-8", "uz_UZ.UTF-8@cyrillic"),
                "belarusian": ("be_BY.UTF-8", "be_BY.UTF-8@latin"),
                "chinese": ("zh_CN.UTF-8", "zh_TW.UTF-8")}
SCRIPT_OF_CODE = {c: s for _, members in TREES for c, s in members}
# The usual Linux names (GNOME-style), used for prediction F.
FIX = {"sr_Cyrl": "sr", "sr_Latn": "sr@latin", "uz": "uz@cyrillic", "uz_Latn": "uz",
       "be": "be", "be_Latn": "be@latin", "zh_Hans": "zh_CN", "zh_Hant": "zh_TW"}
STYLES = ("weblate", "fix")
# Pre-registered: the script each locale's Monday is written in (prediction S).
EXPECT_SCRIPT = {"sr_RS.UTF-8": "Cyrl", "sr_RS.UTF-8@latin": "Latn", "uz_UZ.UTF-8": "Latn",
                 "uz_UZ.UTF-8@cyrillic": "Cyrl", "be_BY.UTF-8": "Cyrl", "be_BY.UTF-8@latin": "Latn"}
VERDICT_KEYS = ("W1", "W2", "W3", "K", "F")

PY_LOOKUP = ("import gettext, sys\n"
             "t = gettext.translation('m', sys.argv[1], fallback=True)\n"
             "sys.stdout.write(t.gettext('Hello'))\n")
PY_DAY = ("import locale, sys\n"
          "locale.setlocale(locale.LC_ALL, '')\n"
          "sys.stdout.buffer.write(locale.nl_langinfo(locale.DAY_2).encode('utf-8'))\n")


# ------------------------------------------------------------------ pure helpers (tested)

def read_tables(source):
    """LEGACY_CODES / LINUX_CODES dict literals and the source of the get_language_* functions."""
    tree = ast.parse(source)
    out = {"tables": {}, "functions": {}}
    for node in ast.walk(tree):
        target = value = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        if isinstance(target, ast.Name) and target.id in TABLES and value is not None:
            try:
                out["tables"][target.id] = ast.literal_eval(value)
            except ValueError:
                out["tables"][target.id] = None
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in FUNCS:
            out["functions"][node.name] = ast.get_source_segment(source, node) or ""
    return out


def linux_name(code, tables):
    """Mirrors get_language_linux: LINUX_CODES, else LEGACY_CODES, else POSIX ('-' -> '_')."""
    lin = tables.get("LINUX_CODES") or {}
    leg = tables.get("LEGACY_CODES") or {}
    return lin.get(code, leg.get(code, code.replace("-", "_")))


def style_name(style, code, tables):
    return linux_name(code, tables) if style == "weblate" else FIX[code]


def script_of(text):
    """Cyrl / Latn / Hani by majority of letters; '' when there are none."""
    counts = {}
    for ch in text:
        if not ch.isalpha():
            continue
        try:
            word = unicodedata.name(ch).split()[0]
        except ValueError:
            continue
        k = {"CYRILLIC": "Cyrl", "LATIN": "Latn", "CJK": "Hani"}.get(word, "other")
        counts[k] = counts.get(k, 0) + 1
    if not counts:
        return ""
    return max(sorted(counts), key=lambda k: counts[k])


def reached(text, codes):
    """The Weblate code a lookup answered with ('X-<code>'), or '' for no translation."""
    if text.startswith("X-") and text[2:] in codes:
        return text[2:]
    return ""


def parse_back(name, aliases, codes):
    """Simplified model of Weblate reading a file name back: alias table, else exact code."""
    n = name.lower()
    if n in aliases:
        return aliases[n]
    for c in codes:
        if c.lower() == n:
            return c
    return None


def held(ok):
    return "HELD" if ok else "FAILED"


def grade(tables, scripts, locales, look):
    v = {}
    lin = (tables or {}).get("LINUX_CODES") or {}
    leg = (tables or {}).get("LEGACY_CODES") or {}
    t_ok = (lin.get("sr_Latn") == "sr" and lin.get("sr_Cyrl") == "sr@cyrillic"
            and lin.get("uz_Latn") == "uz@latin" and lin.get("be_Latn") == "be@latin"
            and leg.get("zh_Hans") == "zh_CN" and leg.get("zh_Hant") == "zh_TW")
    v["T"] = held(t_ok)
    missing = sorted(n for n, ok in locales.items() if not ok and n not in OPTIONAL_LOCALES)
    bad = sorted(loc for loc, s in EXPECT_SCRIPT.items() if scripts.get(loc) != s)
    v["S"] = "HELD" if not missing and not bad else "FAILED (%s)" % " ".join(missing + bad)
    gate = t_ok and v["S"] == "HELD" and not look.get("errors")
    for eng, suffix in (("c", ""), ("py", "py")):
        if not gate:
            for k in VERDICT_KEYS:
                v[k + suffix] = "NOT TESTABLE"
            continue
        w = look.get(eng, {})
        ser = w.get("weblate/serbian", {})
        uzb = w.get("weblate/uzbek", {})
        bel = w.get("weblate/belarusian", {})
        chi = w.get("weblate/chinese", {})
        sr_locs = [loc for loc in TREE_LOCALES["serbian"] if locales.get(loc)]
        v["W1" + suffix] = held(ser.get("sr_RS.UTF-8") == "sr_Latn")
        v["W2" + suffix] = held(bool(ser) and all(ser.get(loc) != "sr_Cyrl" for loc in sr_locs))
        v["W3" + suffix] = held(bool(uzb) and uzb.get("uz_UZ.UTF-8") == "uz"
                                and all(uzb.get(loc) != "uz_Latn"
                                        for loc in TREE_LOCALES["uzbek"]))
        v["K" + suffix] = held(bel.get("be_BY.UTF-8") == "be"
                               and bel.get("be_BY.UTF-8@latin") == "be_Latn"
                               and chi.get("zh_CN.UTF-8") == "zh_Hans"
                               and chi.get("zh_TW.UTF-8") == "zh_Hant")
        ok = True
        for tree in ("serbian", "uzbek", "belarusian"):
            got = w.get("fix/" + tree, {})
            for loc in TREE_LOCALES[tree]:
                if loc not in EXPECT_SCRIPT:
                    continue
                c = got.get(loc, "")
                if not c or SCRIPT_OF_CODE[c] != scripts.get(loc):
                    ok = False
        fz = w.get("fix/chinese", {})
        ok = ok and fz.get("zh_CN.UTF-8") == "zh_Hans" and fz.get("zh_TW.UTF-8") == "zh_Hant"
        v["F" + suffix] = held(ok)
    return v


def round_trip(tables, aliases, codes):
    rows = []
    keys = set(tables.get("LINUX_CODES") or {}) | set(tables.get("LEGACY_CODES") or {})
    for code in sorted(keys):
        name = linux_name(code, tables)
        back = parse_back(name, aliases, codes)
        rows.append({"code": code, "linux_name": name, "parsed_back": back or "",
                     "round_trip": "yes" if back == code else "no"})
    return rows


def parse_csv_map(text):
    """aliases.csv -> {alias lower: language}."""
    out = {}
    for row in csv.reader(io.StringIO(text)):
        if len(row) >= 2 and row[0]:
            out[row[0].strip().lower()] = row[1].strip()
    return out


def parse_codes(text):
    rows = list(csv.reader(io.StringIO(text)))
    return [r[0].strip() for r in rows[1:] if r and r[0].strip()]


# ------------------------------------------------------------------ tools (container only)

def locale_key(name):
    return name.lower().replace("utf-8", "utf8")


def build_locales():
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


def _env(lang, root=None):
    env = {"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"), "LANG": lang}
    if root:
        env["TEXTDOMAINDIR"] = root
    return env


def day_name(loc):
    r = subprocess.run([sys.executable, "-I", "-c", PY_DAY], env=_env(loc), capture_output=True,
                       timeout=60)
    return r.stdout.decode("utf-8", "replace")


def make_catalog(root, name, text, work):
    d = os.path.join(root, name, "LC_MESSAGES")
    os.makedirs(d)
    po = os.path.join(work, "%s-%s.po" % (os.path.basename(root), name.replace("@", "-")))
    with open(po, "w", encoding="utf-8", newline="\n") as fh:
        fh.write('msgid ""\nmsgstr ""\n"Content-Type: text/plain; charset=UTF-8\\n"\n\n'
                 'msgid "Hello"\nmsgstr "%s"\n' % text)
    r = subprocess.run(["msgfmt", "-o", os.path.join(d, "m.mo"), po], capture_output=True,
                       text=True, timeout=60)
    return "" if r.returncode == 0 else "msgfmt %s: %s" % (name, r.stderr.strip()[-200:])


def lookup_c(root, lang):
    r = subprocess.run(["gettext", "-d", "m", "Hello"], env=_env(lang, root),
                       capture_output=True, text=True, timeout=60)
    return r.stdout.strip()


def lookup_py(root, lang):
    r = subprocess.run([sys.executable, "-I", "-c", PY_LOOKUP, root], env=_env(lang, root),
                       capture_output=True, text=True, timeout=60)
    return r.stdout.strip()


def run_lookups(tmp, tables):
    work = tempfile.mkdtemp(dir=tmp)
    out = {"names": {}, "collisions": [], "errors": [], "c": {}, "py": {}}
    for style in STYLES:
        for tree, members in TREES:
            codes = [c for c, _ in members]
            names = [(c, style_name(style, c, tables)) for c in codes]
            key = "%s/%s" % (style, tree)
            out["names"][key] = dict(names)
            if len({n for _, n in names}) < len(names):
                out["collisions"].append(key)
                continue
            root = tempfile.mkdtemp(dir=tmp)
            errs = [e for e in (make_catalog(root, n, "X-" + c, work) for c, n in names) if e]
            if errs:
                out["errors"].extend(errs)
                continue
            out["c"][key] = {loc: reached(lookup_c(root, loc), codes)
                             for loc in TREE_LOCALES[tree]}
            out["py"][key] = {loc: reached(lookup_py(root, loc), codes)
                              for loc in TREE_LOCALES[tree]}
    out["sr_and_sr_Latn_names"] = {c: linux_name(c, tables) for c in ("sr", "sr_Latn")}
    return out


# ------------------------------------------------------------------ network

def fetch_once(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def fetch(url, tries=3):
    last = None
    for i in range(tries):
        try:
            return fetch_once(url)
        except OSError as exc:
            last = exc
            time.sleep(10 * (i + 1))
    raise RuntimeError("could not read %s: %r" % (url, last))


def wait_for_prereg(minutes, say):
    end = time.time() + minutes * 60
    while True:
        try:
            text = fetch_once(PREREG_URL).decode("utf-8")
            if PREREG_MARK in text:
                return hashlib.sha256(text.encode("utf-8")).hexdigest()
        except OSError:
            pass
        if time.time() > end:
            return None
        say("waiting for PREREG.md")
        time.sleep(120)


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, sort_keys=True)


def main(out, say, prereg_wait_minutes=360):
    started = time.time()
    tmp = tempfile.mkdtemp(prefix="wlc-")
    prereg_sha = wait_for_prereg(prereg_wait_minutes, say)
    if not prereg_sha:
        say("PREREG.md not public; stopping")
        return 4
    say("prereg sha256 %s" % prereg_sha)
    sources = {}
    for label, ref in (("pinned", PINNED), ("main", "main")):
        raw = fetch(BASE_URL % ref)
        info = read_tables(raw.decode("utf-8"))
        info["sha256"] = hashlib.sha256(raw).hexdigest()
        info["ref"] = ref
        sources[label] = info
    main_same = sources["main"]["tables"] == sources["pinned"]["tables"]
    say("main has the same tables: %s" % main_same)
    tables = {k: (sources["pinned"]["tables"].get(k)
                  if isinstance(sources["pinned"]["tables"].get(k), dict) else {})
              for k in TABLES}
    say("pinned tables %s" % json.dumps(tables, sort_keys=True))

    rt_rows, data_note = [], ""
    try:
        aliases_raw = fetch(ALIASES_URL)
        languages_raw = fetch(LANGUAGES_URL)
        rt_rows = round_trip(tables, parse_csv_map(aliases_raw.decode("utf-8")),
                             parse_codes(languages_raw.decode("utf-8")))
        data_note = "aliases.csv sha256 %s; languages.csv sha256 %s" % (
            hashlib.sha256(aliases_raw).hexdigest(), hashlib.sha256(languages_raw).hexdigest())
    except Exception as exc:  # exploratory only
        data_note = "language-data not read: %r" % (exc,)
    with open(os.path.join(out, "roundtrip.csv"), "w", encoding="utf-8", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=["code", "linux_name", "parsed_back", "round_trip"])
        wr.writeheader()
        for row in rt_rows:
            wr.writerow(row)

    locales, notes = build_locales()
    days = {name: day_name(name) for _, name in LOCALEDEF}
    scripts = {name: script_of(days[name]) for name in days}
    say("scripts %s" % json.dumps(scripts, sort_keys=True))
    look = run_lookups(tmp, tables)
    write_json(os.path.join(out, "lookups.json"), look)
    verdicts = grade(tables, scripts, locales, look)
    summary = {"verdicts": verdicts, "prereg_sha256": prereg_sha,
               "weblate_sources": {k: {"ref": s["ref"], "sha256": s["sha256"],
                                       "tables": s["tables"], "functions": s["functions"]}
                                   for k, s in sources.items()},
               "main_same_tables": main_same, "language_data": data_note,
               "locales": locales, "localedef": notes, "monday": days, "scripts": scripts,
               "collisions": look["collisions"], "errors": look["errors"],
               "sr_and_sr_Latn_names": look["sr_and_sr_Latn_names"],
               "minutes": round((time.time() - started) / 60, 1)}
    write_json(os.path.join(out, "summary.json"), summary)
    say(json.dumps(verdicts, sort_keys=True))
    return 0


if __name__ == "__main__":
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "out"
    os.makedirs(out_dir, exist_ok=True)

    def say(msg):
        print(time.strftime("%H:%M:%S"), msg, flush=True)

    sys.exit(main(out_dir, say))
