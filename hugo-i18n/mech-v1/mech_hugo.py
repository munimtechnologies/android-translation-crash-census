# hugo-i18n mechanism check v1: what a real Hugo build does with translations whose
# language is not configured (file-name suffix and content-directory setups).
#
# Downloads the official Hugo release tarball (version pinned below, sha256 checked against
# the release's checksums file), builds two tiny sites, and records which output page carries
# each translated text and under which language. Predictions are fixed in PREREG.md (marker
# "hugo-i18n mech PREREG v1"); the script waits until that file is public.
# Always exits 0; errors are recorded in mech.json.
# Usage: python3 -B mech_hugo.py <out folder>
# Made with AI agents by MV2 of Munim, Inc. Apache-2.0.
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import time
import traceback
import urllib.error
import urllib.request

VERSION = "0.169.0"
BASE = "https://github.com/gohugoio/hugo/releases/download/v%s/" % VERSION
TARBALL = "hugo_%s_linux-amd64.tar.gz" % VERSION
SUMS = "hugo_%s_checksums.txt" % VERSION
PREREG_URL = ("https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/"
              "main/hugo-i18n/mech-v1/PREREG.md")
PREREG_MARK = "hugo-i18n mech PREREG v1"
UA = {"User-Agent": "hugo-i18n-mech (MV2, Munim, Inc.; mv2@munimtech.com)"}
WAIT_SECONDS = 8 * 3600

SINGLE = ('<!doctype html>\n<html><body>\n<p class="lang">LANG={{ .Language.Name }}</p>\n'
          '<h1>{{ .Title }}</h1>\n{{ .Content }}\n</body></html>\n')
LIST = ('<!doctype html>\n<html><body>\n<p class="lang">LANG={{ .Language.Name }}</p>\n'
        '<ul>{{ range .Pages }}<li>{{ .Title }}</li>{{ end }}</ul>\n</body></html>\n')
LAYOUTS = {"layouts/single.html": SINGLE, "layouts/list.html": LIST, "layouts/home.html": LIST}


def page(title, body):
    return "---\ntitle: %s\n---\n\n%s\n" % (title, body)


# Site A: translation by file name. en, fr, pt-BR configured; es configured but disabled;
# de not configured at all.
SITE_A = dict(LAYOUTS)
SITE_A.update({
    "hugo.toml": (
        'baseURL = "https://example.org/"\n'
        'title = "mech a"\n'
        'defaultContentLanguage = "en"\n'
        'disableLanguages = ["es"]\n'
        "\n"
        "[languages]\n"
        "  [languages.en]\n"
        "    weight = 1\n"
        "  [languages.fr]\n"
        "    weight = 2\n"
        "  [languages.pt-BR]\n"
        "    weight = 3\n"
        "  [languages.es]\n"
        "    weight = 4\n"),
    "content/posts/hello.md": page("TITLEAEN", "MARKAEN"),
    "content/posts/hello.fr.md": page("TITLEAFR", "MARKAFR"),
    "content/posts/hello.de.md": page("TITLEADE", "MARKADE"),
    "content/posts/hello.pt-BR.md": page("TITLEAPTDASH", "MARKAPTDASH"),
    "content/posts/hello.pt_br.md": page("TITLEAPTUNDER", "MARKAPTUNDER"),
    "content/posts/hello.es.md": page("TITLEAES", "MARKAES"),
    "content/notes/hello/index.md": page("TITLECEN", "MARKCEN"),
    "content/notes/hello/index.fr.md": page("TITLECFR", "MARKCFR"),
    "content/notes/hello/index.de.md": page("TITLECDE", "MARKCDE"),
})

# Site B: translation by content directory. en and fr each have a contentDir; content/de has
# a translated page but no language points at it.
SITE_B = dict(LAYOUTS)
SITE_B.update({
    "hugo.toml": (
        'baseURL = "https://example.org/"\n'
        'title = "mech b"\n'
        'defaultContentLanguage = "en"\n'
        "\n"
        "[languages]\n"
        "  [languages.en]\n"
        '    contentDir = "content/en"\n'
        "    weight = 1\n"
        "  [languages.fr]\n"
        '    contentDir = "content/fr"\n'
        "    weight = 2\n"),
    "content/en/posts/hello.md": page("TITLEBEN", "MARKBEN"),
    "content/fr/posts/hello.md": page("TITLEBFR", "MARKBFR"),
    "content/de/posts/hello.md": page("TITLEBDE", "MARKBDE"),
})

MARKERS_A = ["MARKAEN", "MARKAFR", "MARKADE", "MARKAPTDASH", "MARKAPTUNDER", "MARKAES",
             "MARKCEN", "MARKCFR", "MARKCDE", "TITLEADE", "TITLEAPTUNDER"]
MARKERS_B = ["MARKBEN", "MARKBFR", "MARKBDE", "TITLEBDE"]
LANG_RE = re.compile(r"LANG=([A-Za-z0-9_-]*)")
TOKEN_DE = re.compile(r"(?<![a-z0-9_])de(?![a-z0-9_])")


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


def expected_sha(sums_text, name):
    for line in sums_text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*") == name:
            return parts[0].lower()
    return None


def install_hugo(bindir):
    sums = get(BASE + SUMS)
    if sums is None:
        raise RuntimeError("checksums file not found")
    want = expected_sha(sums.decode("utf-8", "replace"), TARBALL)
    if not want:
        raise RuntimeError("tarball not listed in checksums file")
    tb = get(BASE + TARBALL)
    if tb is None:
        raise RuntimeError("tarball not found")
    got = hashlib.sha256(tb).hexdigest()
    if got != want:
        raise RuntimeError("sha256 mismatch: %s != %s" % (got, want))
    with tarfile.open(fileobj=io.BytesIO(tb), mode="r:gz") as tf:
        member = tf.getmember("hugo")
        data = tf.extractfile(member).read()
    path = os.path.join(bindir, "hugo")
    with open(path, "wb") as fh:
        fh.write(data)
    os.chmod(path, 0o755)
    return path, got


def write_site(root, files):
    for rel, text in files.items():
        p = os.path.join(root, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)


def lang_of(html):
    m = LANG_RE.search(html)
    return m.group(1) if m else ""


def scan(pub, markers):
    """Return ({marker: [[relpath, lang], ...]} over .html files,
    {marker: [relpath, ...]} over all files, sorted top-level names)."""
    html_hits = {m: [] for m in markers}
    any_hits = {m: [] for m in markers}
    top = sorted(os.listdir(pub)) if os.path.isdir(pub) else []
    for dirpath, _dirs, files in os.walk(pub):
        for name in sorted(files):
            fp = os.path.join(dirpath, name)
            rel = os.path.relpath(fp, pub).replace(os.sep, "/")
            with open(fp, "rb") as fh:
                text = fh.read().decode("utf-8", "replace")
            lang = lang_of(text) if name.endswith(".html") else ""
            for m in markers:
                if m in text:
                    any_hits[m].append(rel)
                    if name.endswith(".html"):
                        html_hits[m].append([rel, lang])
    for m in markers:
        html_hits[m].sort()
        any_hits[m].sort()
    return html_hits, any_hits, top


def build(hugo, files, markers, tmp, name):
    site = os.path.join(tmp, name)
    pub = os.path.join(tmp, name + "-public")
    write_site(site, files)
    env = dict(os.environ, HUGO_CACHEDIR=os.path.join(tmp, "cache"))
    r = subprocess.run([hugo, "--source", site, "--destination", pub], env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=600)
    html_hits, any_hits, top = scan(pub, markers)
    return {"exit": r.returncode, "log": (r.stdout + "\n" + r.stderr).strip(),
            "html_hits": html_hits, "any_hits": any_hits, "top": top}


def silent_about_de(log):
    for line in log.splitlines():
        low = line.lower()
        if "hello.de" in low or "index.de" in low:
            return False
        if "lang" in low and TOKEN_DE.search(low):
            return False
    return True


def has_lang(hits, lang):
    return any(l == lang for _p, l in hits)


def verdicts(a, b):
    v = {}
    ah = a["html_hits"] if a else {}
    ok_a = bool(a) and a["exit"] == 0
    v["K"] = "HELD" if ok_a and has_lang(ah.get("MARKAFR", []), "fr") else "FAILED"
    v["K3"] = "HELD" if ok_a and has_lang(ah.get("MARKAEN", []), "en") else "FAILED"
    v["KC"] = "HELD" if ok_a and has_lang(ah.get("MARKCFR", []), "fr") else "FAILED"
    controls_a = v["K"] == v["K3"] == v["KC"] == "HELD"
    if controls_a:
        es_any = a["any_hits"].get("MARKAES", [])
        v["D"] = "HELD" if not es_any and "es" not in a["top"] else "FAILED"
        de = ah.get("MARKADE", [])
        v["L1"] = ("HELD" if de and all(l == "en" for _p, l in de) and "de" not in a["top"]
                   else "FAILED")
        pu = ah.get("MARKAPTUNDER", [])
        v["L2"] = "HELD" if pu and all(l == "en" for _p, l in pu) else "FAILED"
        v["C1"] = "HELD" if has_lang(ah.get("MARKAPTDASH", []), "pt-br") else "FAILED"
        v["L3"] = "HELD" if not ah.get("MARKCDE", []) else "FAILED"
        v["S"] = "HELD" if silent_about_de(a["log"]) else "FAILED"
    else:
        for k in ("D", "L1", "L2", "C1", "L3", "S"):
            v[k] = "NOT TESTABLE (site A controls failed)"
    bh = b["html_hits"] if b else {}
    ok_b = bool(b) and b["exit"] == 0
    v["KB"] = "HELD" if ok_b and has_lang(bh.get("MARKBFR", []), "fr") else "FAILED"
    if v["KB"] == "HELD":
        v["O1"] = ("HELD" if not b["any_hits"].get("MARKBDE", []) and "de" not in b["top"]
                   else "FAILED")
    else:
        v["O1"] = "NOT TESTABLE (site B control failed)"
    return v


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/out"
    os.makedirs(out, exist_ok=True)
    res = {"hugo_version": VERSION, "tarball": TARBALL, "log": [], "verdicts": {}}
    try:
        res["prereg_sha256"] = wait_for_prereg(res["log"])
        tmp = tempfile.mkdtemp(prefix="hugo-mech-")
        bindir = os.path.join(tmp, "bin")
        os.makedirs(bindir)
        hugo, sha = install_hugo(bindir)
        res["tarball_sha256"] = sha
        vr = subprocess.run([hugo, "version"], capture_output=True, text=True)
        res["hugo_version_output"] = (vr.stdout + vr.stderr).strip()
        a = build(hugo, SITE_A, MARKERS_A, tmp, "site-a")
        b = build(hugo, SITE_B, MARKERS_B, tmp, "site-b")
        res["site_a"] = a
        res["site_b"] = b
        res["verdicts"] = verdicts(a, b)
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
