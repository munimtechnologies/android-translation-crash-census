# mkdocs-i18n mechanism check v2: real MkDocs builds with the released mkdocs-static-i18n
# (1.3.1, environment A) and with open pull request #348's head (environment B), side by side,
# on files whose last dotted part or top-level folder is a three-letter word (jquery.min.js,
# app.esm.js, theme.min.css, setup.mac.md, docs/img/, docs/css/).
#
# Predictions are fixed in PREREG.md (marker "mkdocs-i18n mech PREREG v2"); the script waits
# until that file is public. Always exits 0; errors are recorded in mech.json.
# Usage: python3 -B mech_mkdocs2.py <out folder> <python of env A> <python of env B>
# Made with AI agents by MV2 of Munim, Inc. Apache-2.0.
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.request

PREREG_URL = ("https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/"
              "main/mkdocs-i18n/mech-v2/PREREG.md")
PREREG_MARK = "mkdocs-i18n mech PREREG v2"
UA = {"User-Agent": "mkdocs-i18n-mech (MV2, Munim, Inc.; mv2@munimtech.com)"}
WAIT_SECONDS = 8 * 3600
PINNED_A = {"mkdocs": "1.6.1", "mkdocs-static-i18n": "1.3.1"}
PINNED_B_MKDOCS = "1.6.1"


def page(title, body):
    return "# %s\n\n%s\n" % (title, body)


def i18n(structure):
    return ("plugins:\n"
            "  - i18n:\n"
            "      docs_structure: %s\n"
            "      languages:\n"
            "        - locale: en\n"
            "          default: true\n"
            "          name: English\n"
            "          build: true\n"
            "        - locale: fr\n"
            "          name: Francais\n"
            "          build: true\n" % structure)


SUFFIX_DOCS = {
    "docs/index.md": page("Home", "MARKSEN"),
    "docs/index.fr.md": page("Accueil", "MARKSFR"),
    "docs/guide.md": page("Guide", "MARKGUIDE"),
    "docs/setup.mac.md": page("Setup on macOS", "MARKMAC"),
    "docs/node.js.md": page("Node.js", "MARKNODEJS"),
    "docs/assets/jquery.min.js": "// MARKMINJS\n",
    "docs/assets/app.esm.js": "// MARKESM\n",
    "docs/assets/theme.min.css": "/* MARKMINCSS */\n",
}
SUFFIX_HEAD = ("theme:\n  name: mkdocs\n"
               "extra_javascript:\n  - assets/jquery.min.js\n  - assets/app.esm.js\n"
               "extra_css:\n  - assets/theme.min.css\n")
SITE_S = dict(SUFFIX_DOCS)
SITE_S["mkdocs.yml"] = "site_name: mech2 s\n" + SUFFIX_HEAD + i18n("suffix")
SITE_N = dict(SUFFIX_DOCS)
SITE_N["mkdocs.yml"] = "site_name: mech2 n\n" + SUFFIX_HEAD + "plugins: []\n"

SITE_F = {
    "mkdocs.yml": ("site_name: mech2 f\n"
                   "theme:\n  name: mkdocs\n"
                   "extra_javascript:\n  - js/custom.js\n  - javascripts/extra.js\n"
                   "extra_css:\n  - css/extra.css\n" + i18n("folder")),
    "docs/en/index.md": page("Home", "MARKFEN\n\n![diagram](../img/diagram.svg)"),
    "docs/fr/index.md": page("Accueil", "MARKFFR"),
    "docs/img/diagram.svg": ("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"1\" height=\"1\">"
                             "<!-- MARKIMG --></svg>\n"),
    "docs/css/extra.css": "/* MARKFCSS */\n",
    "docs/js/custom.js": "// MARKFJS\n",
    "docs/javascripts/extra.js": "// MARKFXTRA\n",
    "docs/api/index.md": page("API", "MARKAPI"),
}

MARKERS_S = ["MARKSEN", "MARKSFR", "MARKGUIDE", "MARKMAC", "MARKNODEJS", "MARKMINJS", "MARKESM",
             "MARKMINCSS"]
MARKERS_F = ["MARKFEN", "MARKFFR", "MARKIMG", "MARKFCSS", "MARKFJS", "MARKFXTRA", "MARKAPI"]
QUIET_NAMES = ["setup.mac", "jquery.min", "app.esm", "theme.min"]


def get(url, tries=4):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            last = "HTTP %d" % e.code
        except Exception as e:  # network errors: retry
            last = repr(e)
        time.sleep(15 * (i + 1))
    raise RuntimeError("%s: %s" % (url, last))


def wait_for_prereg(log):
    start = time.time()
    while True:
        try:
            data = get(PREREG_URL, tries=2)
        except RuntimeError as e:
            data = None
            log.append("waiting for PREREG.md: %s" % e)
        if data is not None and PREREG_MARK in data.decode("utf-8", "replace"):
            log.append("PREREG.md is live")
            return hashlib.sha256(data).hexdigest()
        if time.time() - start > WAIT_SECONDS:
            raise RuntimeError("PREREG.md not live after %d s" % WAIT_SECONDS)
        time.sleep(300)


PROBE = ("import importlib.metadata as m, json\n"
         "from mkdocs_static_i18n.config import RE_LOCALE\n"
         "print(json.dumps({'mkdocs': m.version('mkdocs'),"
         " 'mkdocs-static-i18n': m.version('mkdocs-static-i18n'),"
         " 'ast': bool(RE_LOCALE.match('ast')), 'min': bool(RE_LOCALE.match('min')),"
         " 'js': bool(RE_LOCALE.match('js'))}))\n")


def probe(py):
    r = subprocess.run([py, "-c", PROBE], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300)
    if r.returncode != 0:
        raise RuntimeError("probe failed for %s: %s" % (py, r.stderr[-1500:]))
    return json.loads(r.stdout.strip().splitlines()[-1])


def write_site(root, files):
    for rel, text in files.items():
        p = os.path.join(root, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)


def scan(site_dir, markers):
    """Return ({marker: [relpath, ...]} over every output file, sorted list of all files)."""
    hits = {m: [] for m in markers}
    allf = []
    for dirpath, _dirs, files in os.walk(site_dir):
        for name in files:
            fp = os.path.join(dirpath, name)
            rel = os.path.relpath(fp, site_dir).replace(os.sep, "/")
            allf.append(rel)
            with open(fp, "rb") as fh:
                text = fh.read().decode("utf-8", "replace")
            for m in markers:
                if m in text:
                    hits[m].append(rel)
    for m in markers:
        hits[m].sort()
    allf.sort()
    return hits, allf


def build(py, files, markers, tmp, name):
    root = os.path.join(tmp, name)
    out = os.path.join(tmp, name + "-site")
    write_site(root, files)
    r = subprocess.run([py, "-m", "mkdocs", "build", "-f", os.path.join(root, "mkdocs.yml"),
                        "-d", out], cwd=root, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=900)
    hits, allf = scan(out, markers) if os.path.isdir(out) else ({m: [] for m in markers}, [])
    return {"exit": r.returncode, "log": (r.stdout + "\n" + r.stderr).strip(),
            "hits": hits, "files": allf}


def ok(site):
    return bool(site) and site.get("exit") == 0


def has(site, marker, path=None):
    paths = site["hits"].get(marker, []) if site else []
    if path is None:
        return bool(paths)
    return path in paths


def none_of(site, marker):
    return ok(site) and not site["hits"].get(marker, [])


def suffix_ok(s):
    return (ok(s) and has(s, "MARKSEN", "index.html") and has(s, "MARKSFR", "fr/index.html")
            and has(s, "MARKGUIDE"))


def folder_ok(f):
    return (ok(f) and has(f, "MARKFEN", "index.html") and has(f, "MARKFFR", "fr/index.html")
            and has(f, "MARKFXTRA"))


def hv(cond):
    return "HELD" if cond else "FAILED"


def verdicts(pa, pb, sa, sb, n, fa, fb):
    v = {}
    v["KP"] = hv(bool(pb.get("ast")) and not pa.get("ast"))
    v["KA"] = hv(suffix_ok(sa))
    v["KB"] = hv(suffix_ok(sb))
    v["K0"] = hv(ok(n) and all(has(n, m) for m in
                               ("MARKMAC", "MARKNODEJS", "MARKMINJS", "MARKESM", "MARKMINCSS")))
    v["KFA"] = hv(folder_ok(fa))
    v["KFB"] = hv(folder_ok(fb))
    held = lambda *ks: all(v[k] == "HELD" for k in ks)  # noqa: E731
    nt = "NOT TESTABLE (controls failed)"
    v["B1"] = (hv(all(has(sa, m) for m in ("MARKMAC", "MARKMINJS", "MARKESM", "MARKMINCSS")))
               if held("KA", "K0") else nt)
    v["B2"] = hv(has(fa, "MARKIMG") and has(fa, "MARKFCSS")) if held("KFA") else nt
    v["C1"] = (hv(none_of(sa, "MARKNODEJS") and none_of(sb, "MARKNODEJS"))
               if held("KA", "KB", "K0") else nt)
    v["C2"] = hv(none_of(fa, "MARKFJS") and none_of(fb, "MARKFJS")) if held("KFA", "KFB") else nt
    rs = held("KP", "KB", "K0")
    v["R1"] = hv(none_of(sb, "MARKMINJS")) if rs else nt
    v["R2"] = hv(none_of(sb, "MARKESM")) if rs else nt
    v["R3"] = hv(none_of(sb, "MARKMINCSS")) if rs else nt
    v["R4"] = hv(none_of(sb, "MARKMAC")) if rs else nt
    rf = held("KP", "KFB")
    v["R5"] = hv(none_of(fb, "MARKIMG")) if rf else nt
    v["R6"] = hv(none_of(fb, "MARKFCSS")) if rf else nt
    lines = sb["log"].splitlines() if sb else []
    v["S2"] = (hv(not any(q in ln for ln in lines for q in QUIET_NAMES)) if rs else nt)
    return v


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/out"
    py_a = sys.argv[2] if len(sys.argv) > 2 else "/opt/envA/bin/python"
    py_b = sys.argv[3] if len(sys.argv) > 3 else "/opt/envB/bin/python"
    os.makedirs(out, exist_ok=True)
    res = {"log": [], "verdicts": {}}
    try:
        res["prereg_sha256"] = wait_for_prereg(res["log"])
        pa = probe(py_a)
        pb = probe(py_b)
        res["probe_a"] = pa
        res["probe_b"] = pb
        got_a = {"mkdocs": pa.get("mkdocs"), "mkdocs-static-i18n": pa.get("mkdocs-static-i18n")}
        if got_a != PINNED_A or pb.get("mkdocs") != PINNED_B_MKDOCS:
            raise RuntimeError("installed versions differ from pinned: %r %r" % (pa, pb))
        tmp = tempfile.mkdtemp(prefix="mkdocs-mech2-")
        sa = build(py_a, SITE_S, MARKERS_S, os.path.join(tmp, "a"), "site-s")
        sb = build(py_b, SITE_S, MARKERS_S, os.path.join(tmp, "b"), "site-s")
        n = build(py_a, SITE_N, MARKERS_S, os.path.join(tmp, "a"), "site-n")
        fa = build(py_a, SITE_F, MARKERS_F, os.path.join(tmp, "a"), "site-f")
        fb = build(py_b, SITE_F, MARKERS_F, os.path.join(tmp, "b"), "site-f")
        res.update({"site_s_a": sa, "site_s_b": sb, "site_n": n, "site_f_a": fa,
                    "site_f_b": fb})
        res["verdicts"] = verdicts(pa, pb, sa, sb, n, fa, fb)
        res["reported_api_page"] = {"A": fa["hits"].get("MARKAPI", []),
                                    "B": fb["hits"].get("MARKAPI", [])}
    except Exception:
        res["error"] = traceback.format_exc()[-3000:]
        res["verdicts"] = res["verdicts"] or {"ALL": "NOT TESTABLE (mech error)"}
    with open(os.path.join(out, "mech.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(res, indent=1, sort_keys=True) + "\n")
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps({"verdicts": res["verdicts"], "error": res.get("error", ""),
                             "api_page": res.get("reported_api_page", {})},
                            indent=1, sort_keys=True) + "\n")
    print(json.dumps(res["verdicts"], indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
    sys.exit(0)
