# mkdocs-i18n mechanism check v1: what a real MkDocs build with the mkdocs-static-i18n plugin
# does with files whose last dotted suffix, or top-level folder, merely looks like a language
# code (node.js.md, socket.io.md, widget.es.js, docs/js/), and with translations of a language
# that is not configured.
#
# Builds three tiny sites with the pinned versions installed by the job (mkdocs 1.6.1,
# mkdocs-static-i18n 1.3.1) and records which output files carry each unique marker text.
# Predictions are fixed in PREREG.md (marker "mkdocs-i18n mech PREREG v1"); the script waits
# until that file is public. Always exits 0; errors are recorded in mech.json.
# Usage: python3 -B mech_mkdocs.py <out folder>
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
              "main/mkdocs-i18n/mech-v1/PREREG.md")
PREREG_MARK = "mkdocs-i18n mech PREREG v1"
UA = {"User-Agent": "mkdocs-i18n-mech (MV2, Munim, Inc.; mv2@munimtech.com)"}
WAIT_SECONDS = 8 * 3600
PINNED = {"mkdocs": "1.6.1", "mkdocs-static-i18n": "1.3.1"}


def page(title, body):
    return "# %s\n\n%s\n" % (title, body)


I18N_SUFFIX = (
    "plugins:\n"
    "  - i18n:\n"
    "      docs_structure: suffix\n"
    "      languages:\n"
    "        - locale: en\n"
    "          default: true\n"
    "          name: English\n"
    "          build: true\n"
    "        - locale: fr\n"
    "          name: Francais\n"
    "          build: true\n")

# Suffix structure (the plugin's default). en (default) and fr are configured; de and pt-BR
# are not. node.js.md, socket.io.md and widget.es.js are ordinary English files whose last
# dotted suffix looks like a language code.
SUFFIX_DOCS = {
    "docs/index.md": page("Home", "MARKSEN"),
    "docs/index.fr.md": page("Accueil", "MARKSFR"),
    "docs/guide.md": page("Guide", "MARKGUIDE\n\nSee [the Socket.IO page](socket.io.md)."),
    "docs/node.js.md": page("Node.js", "MARKNODEJS"),
    "docs/socket.io.md": page("Socket.IO", "MARKSOCKETIO"),
    "docs/node.jsx.md": page("JSX", "MARKJSX"),
    "docs/release_17.1.md": page("Release 17.1", "MARKREL"),
    "docs/guide.de.md": page("Anleitung", "MARKDE"),
    "docs/guide.pt-BR.md": page("Guia", "MARKPTDASH"),
    "docs/guide.pt_br.md": page("Guia", "MARKPTUNDER"),
    "docs/assets/widget.es.js": "// MARKESJS\n",
}
SITE_S = dict(SUFFIX_DOCS)
SITE_S["mkdocs.yml"] = ("site_name: mech s\n"
                        "theme:\n  name: mkdocs\n"
                        "extra_javascript:\n  - assets/widget.es.js\n" + I18N_SUFFIX)
# Same files, no plugin: the control that shows what MkDocs alone builds.
SITE_N = dict(SUFFIX_DOCS)
SITE_N["mkdocs.yml"] = ("site_name: mech n\n"
                        "theme:\n  name: mkdocs\n"
                        "extra_javascript:\n  - assets/widget.es.js\n"
                        "plugins: []\n")

# Folder structure: docs/en and docs/fr; js/ and javascripts/ are shared top-level folders.
SITE_F = {
    "mkdocs.yml": ("site_name: mech f\n"
                   "theme:\n  name: mkdocs\n"
                   "extra_javascript:\n  - js/custom.js\n  - javascripts/extra.js\n"
                   "plugins:\n"
                   "  - i18n:\n"
                   "      docs_structure: folder\n"
                   "      languages:\n"
                   "        - locale: en\n"
                   "          default: true\n"
                   "          name: English\n"
                   "          build: true\n"
                   "        - locale: fr\n"
                   "          name: Francais\n"
                   "          build: true\n"),
    "docs/en/index.md": page("Home", "MARKFEN"),
    "docs/fr/index.md": page("Accueil", "MARKFFR"),
    "docs/js/custom.js": "// MARKFJS\n",
    "docs/javascripts/extra.js": "// MARKFXTRA\n",
}

MARKERS_S = ["MARKSEN", "MARKSFR", "MARKGUIDE", "MARKNODEJS", "MARKSOCKETIO", "MARKJSX",
             "MARKREL", "MARKDE", "MARKPTDASH", "MARKPTUNDER", "MARKESJS"]
MARKERS_F = ["MARKFEN", "MARKFFR", "MARKFJS", "MARKFXTRA"]


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


def installed_versions():
    from importlib import metadata
    got = {}
    for name in PINNED:
        try:
            got[name] = metadata.version(name)
        except Exception:
            got[name] = ""
    return got


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


def build(files, markers, tmp, name):
    root = os.path.join(tmp, name)
    out = os.path.join(tmp, name + "-site")
    write_site(root, files)
    r = subprocess.run([sys.executable, "-m", "mkdocs", "build", "-f",
                        os.path.join(root, "mkdocs.yml"), "-d", out],
                       cwd=root, capture_output=True, text=True, encoding="utf-8",
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


def log_lines(site):
    return site["log"].splitlines() if site else []


def verdicts(s, n, f):
    v = {}
    v["K"] = ("HELD" if ok(s) and has(s, "MARKSEN", "index.html")
              and has(s, "MARKSFR", "fr/index.html") else "FAILED")
    v["KX"] = ("HELD" if ok(s) and any(p.endswith(".html") for p in s["hits"]["MARKJSX"])
               and any(p.endswith(".html") for p in s["hits"]["MARKREL"]) else "FAILED")
    v["K0"] = ("HELD" if ok(n) and has(n, "MARKNODEJS") and has(n, "MARKSOCKETIO")
               and has(n, "MARKESJS") and has(n, "MARKDE") else "FAILED")
    if v["K"] == "HELD" and v["K0"] == "HELD":
        v["D1"] = "HELD" if none_of(s, "MARKNODEJS") else "FAILED"
        v["D2"] = "HELD" if none_of(s, "MARKSOCKETIO") else "FAILED"
        v["A1"] = "HELD" if none_of(s, "MARKESJS") else "FAILED"
        v["D3"] = "HELD" if none_of(s, "MARKDE") else "FAILED"
        v["D4"] = "HELD" if none_of(s, "MARKPTDASH") else "FAILED"
        pu = s["hits"].get("MARKPTUNDER", [])
        v["L1"] = ("HELD" if any(p.startswith("guide.pt_br/") and p.endswith(".html") for p in pu)
                   else "FAILED")
        lines = log_lines(s)
        v["W"] = ("HELD" if any("WARNING" in ln and "socket.io.md" in ln for ln in lines)
                  else "FAILED")
        v["S"] = "HELD" if not any("node.js" in ln for ln in lines) else "FAILED"
    else:
        for k in ("D1", "D2", "A1", "D3", "D4", "L1", "W", "S"):
            v[k] = "NOT TESTABLE (suffix controls failed)"
    v["KF"] = ("HELD" if ok(f) and has(f, "MARKFEN", "index.html")
               and has(f, "MARKFFR", "fr/index.html") and has(f, "MARKFXTRA") else "FAILED")
    if v["KF"] == "HELD":
        v["F1"] = "HELD" if none_of(f, "MARKFJS") else "FAILED"
        v["F2"] = "HELD" if "js/custom.js" in open_text(f, "index.html") else "FAILED"
    else:
        v["F1"] = "NOT TESTABLE (folder controls failed)"
        v["F2"] = "NOT TESTABLE (folder controls failed)"
    return v


def open_text(site, rel):
    """Text of one output file, as recorded at build time (empty if missing)."""
    return site.get("texts", {}).get(rel, "")


def keep_texts(site, site_dir, rels):
    site["texts"] = {}
    for rel in rels:
        p = os.path.join(site_dir, *rel.split("/"))
        if os.path.isfile(p):
            with open(p, "rb") as fh:
                site["texts"][rel] = fh.read().decode("utf-8", "replace")


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/out"
    os.makedirs(out, exist_ok=True)
    res = {"pinned": PINNED, "log": [], "verdicts": {}}
    try:
        res["prereg_sha256"] = wait_for_prereg(res["log"])
        res["installed"] = installed_versions()
        if res["installed"] != PINNED:
            raise RuntimeError("installed versions differ from pinned: %r" % res["installed"])
        tmp = tempfile.mkdtemp(prefix="mkdocs-mech-")
        s = build(SITE_S, MARKERS_S, tmp, "site-s")
        n = build(SITE_N, MARKERS_S, tmp, "site-n")
        f = build(SITE_F, MARKERS_F, tmp, "site-f")
        keep_texts(f, os.path.join(tmp, "site-f-site"), ["index.html", "fr/index.html"])
        res["site_s"] = s
        res["site_n"] = n
        res["site_f"] = f
        res["verdicts"] = verdicts(s, n, f)
    except Exception:
        res["error"] = traceback.format_exc()[-3000:]
        res["verdicts"] = res["verdicts"] or {"ALL": "NOT TESTABLE (mech error)"}
    with open(os.path.join(out, "mech.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(res, indent=1, sort_keys=True) + "\n")
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps({"verdicts": res["verdicts"], "error": res.get("error", "")},
                            indent=1, sort_keys=True) + "\n")
    print(json.dumps(res["verdicts"], indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    main()
    sys.exit(0)
