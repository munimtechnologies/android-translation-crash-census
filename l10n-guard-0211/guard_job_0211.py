# Builds l10n-guard 0.21.1 in a sealed job from the released 0.21.0 code on main: exact line
# replacements, version bump, test_0211.py; runs every test module before and after; then,
# once PREREG.md is public, runs 0.21.0 and 0.21.1 check_linguas on 18 po folders at their
# recorded commits and grades T, A, S, M1, M2 and M3. Nothing is published from here.
# Usage: python -B guard_job_0211.py <out folder>
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
import time
import urllib.error
import urllib.parse
import urllib.request

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else "/out"
REPO = os.path.join(HERE, "repo")
OLD, NEW = "0.21.0", "0.21.1"
GUARD_RAW = "https://raw.githubusercontent.com/munimtechnologies/l10n-guard/main/l10n_guard.py"
TARBALL = "https://codeload.github.com/munimtechnologies/l10n-guard/tar.gz/refs/heads/main"
CENSUS = ("https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/"
          "main/")
PREREG_URL = CENSUS + "l10n-guard-0211/PREREG.md"
PREREG_MARK = "l10n-guard 0.21.1 PREREG v1"
WAIT_SECONDS = 8 * 3600
UA = {"User-Agent": "mv2-l10n-guard-check (mv2@munimtech.com)"}
SUMMARY = {"verdicts": {}}
LOG = []

# The 18 po folders of the 0.21.0 check: (set, repository, commit, po folder).
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
]

# Code replacements in l10n_guard.py: (what, old lines compared stripped, new lines relative to
# the indentation of the first old line). Each old run must occur exactly once.
CODE = [
    ("version", ['__version__ = "0.21.0"'], ['__version__ = "0.21.1"']),
    ("autotools wording",
     ['tool = "Meson" if build == "meson" else "gettext\'s build rules"'],
     ['tool = ("Meson never compiles or installs it" if build == "meson"',
      '        else "gettext\'s build rules never compile or install it")']),
    ("hyphen advice",
     ['else:',
      'fix = "add \'%s\' to %s if the translation is ready" % (stem, rel)'],
     ['elif "-" in stem:',
      '    gt = stem.replace("-", "_")',
      '    fix = ("gettext locale names use \'_\', so a catalog installed as \'%s\' is never "',
      '           "looked up; rename %s%s to %s%s.po and add \'%s\' to %s if the "',
      '           "translation is ready" % (stem, prefix, po[stem], prefix, gt, gt, rel))',
      'else:',
      '    fix = "add \'%s\' to %s if the translation is ready" % (stem, rel)']),
    ("message",
     ['"%s%s has %d of %d messages translated, but %s does not list \'%s\', so %s never "',
      '"compiles or installs it; %s" % (prefix, po[stem], done, total, rel, stem, tool,',
      'fix), stem))'],
     ['"%s%s has %d of %d messages translated, but %s does not list \'%s\', so %s; %s"',
      '% (prefix, po[stem], done, total, rel, stem, tool, fix), stem))']),
]

ACTION = [
    ("case line", True, ['po|xliff|xcstrings|qt)'],
     ['po|xliff|xcstrings|qt|locale-config|linguas)']),
    ("kind description", False,
     ['description: "html, md, json, properties, arb, android, strings, resx, laravel, rails, '
      'symfony, dir (a whole locale folder against its source folder), or a single-file format: '
      'po, xliff, xcstrings, qt"'],
     ['description: "html, md, json, properties, arb, android, strings, resx, laravel, rails, '
      'symfony, dir (a whole locale folder against its source folder), a single-file format: '
      'po, xliff, xcstrings, qt, or a project folder: locale-config, linguas"']),
    ("source description", False,
     ['description: "Source-language file or folder (not used for po, xliff, xcstrings, qt)"'],
     ['description: "Source-language file or folder (not used for po, xliff, xcstrings, qt, '
      'locale-config, linguas)"']),
    ("target description", False,
     ['description: "Translated file or folder"'],
     ['description: "Translated file or folder (the project folder for locale-config and '
      'linguas)"']),
]

README = [
    ("action folder kinds",
     ['The Action takes a source and a target, so the `locale-config` and `linguas` kinds run '
      'as a plain step for now:'],
     ['Project-folder kinds (`locale-config`, `linguas`) take only `target` (since 0.21.1):',
      '',
      '```yaml',
      '- uses: actions/checkout@v4',
      '- uses: munimtechnologies/l10n-guard@v0.21.1',
      '  with:',
      '    kind: linguas',
      '    target: .',
      '    strict: "true"',
      '```',
      '',
      'Or run them as a plain step:']),
]

SKILL = [
    ("ci note",
     ['(single-file kinds `po`, `xliff`, `xcstrings`, `qt` take only `target`). For '
      '`locale-config`,',
      'use a plain step instead: `pip install '
      '"git+https://github.com/munimtechnologies/l10n-guard@v0.21.1"`'],
     ['(single-file kinds `po`, `xliff`, `xcstrings`, `qt` and the project-folder kinds',
      '`locale-config` and `linguas` take only `target`). Or use a plain step:',
      '`pip install "git+https://github.com/munimtechnologies/l10n-guard@v0.21.1"`']),
]

BUMPS = {
    "README.md": [("@v0.21.0", "@v0.21.1"), ("rev: v0.21.0", "rev: v0.21.1")],
    "skills/l10n-guard/SKILL.md": [('version: "0.21.0"', 'version: "0.21.1"'),
                                   ("@v0.21.0", "@v0.21.1"),
                                   ("rev: v0.21.0", "rev: v0.21.1")],
}


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


def replace_lines(rel, text, what, old, new, required=True):
    crlf = "\r\n" in text
    lines = text.split("\n")
    n = len(old)
    hits = [i for i in range(len(lines) - n + 1)
            if all(lines[i + k].strip() == old[k] for k in range(n))]
    if len(hits) != 1:
        if required:
            fail("%s %s: old lines found %d times" % (rel, what, len(hits)))
        say("optional replacement skipped: %s %s (found %d times)" % (rel, what, len(hits)))
        SUMMARY.setdefault("skipped_optional", []).append("%s %s" % (rel, what))
        return text
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

            po_old, st_old = old.check_linguas(paths, read)
            po_new, st_new = new.check_linguas(paths, read)
        except Exception as e:
            say("compare %s %s: error %r" % (repo, d, e))
            rows.append(dict(base, status="error: %r" % (e,), code="", key="", old_message="",
                             new_message=""))
            continue
        a = dict(((p["code"], p["key"]), p["message"]) for p in po_old)
        b = dict(((p["code"], p["key"]), p["message"]) for p in po_new)
        say("compare %s %s: 0.21.0 %s, 0.21.1 %s" % (repo, d, sorted(a), sorted(b)))
        if not a and not b:
            rows.append(dict(base, status="ok", code="", key="", old_message="", new_message=""))
        for k in sorted(set(a) | set(b)):
            rows.append(dict(base, status="ok", code=k[0], key=k[1],
                             old_message=a.get(k, ""), new_message=b.get(k, "")))
    return rows


def grade(rows):
    v = {}
    by_folder = {}
    for r in rows:
        by_folder.setdefault((r["repo"], r["folder"]), []).append(r)
    ok = [k for k, rs in by_folder.items() if rs[0]["status"] == "ok"]
    diffs = [r for r in rows if r["status"] == "ok" and r["code"]
             and (not r["old_message"] or not r["new_message"])]
    if len(ok) < 16:
        v["S"] = "NOT TESTABLE (%d of 18 folders read)" % len(ok)
    elif diffs:
        v["S"] = "FAILED (%d findings differ; %d of 18 folders read)" % (len(diffs), len(ok))
    else:
        v["S"] = "HELD (%d of 18 folders read, same findings)" % len(ok)

    def find(repo_end, key):
        hit = [r for r in rows if r["repo"].endswith(repo_end) and r["key"] == key
               and r["status"] == "ok"]
        return hit[0] if hit else None

    r = find("/World/tootle", "nb-NO")
    if r is None:
        v["M1"] = "NOT TESTABLE (Tootle nb-NO not read)"
    else:
        v["M1"] = ("HELD" if "rename po/nb-NO.po to po/nb_NO.po" in r["new_message"]
                   else "FAILED")
    r = find("/GNOME/NetworkManager-openconnect", "en_US")
    if r is None:
        v["M2"] = "NOT TESTABLE (NetworkManager-openconnect en_US not read)"
    else:
        v["M2"] = ("HELD" if "gettext's build rules never compile or install it"
                   in r["new_message"] else "FAILED")
    m3 = [r for r in rows if r["status"] == "ok" and r["code"] and "-" not in r["key"]
          and "so Meson never compiles" in r["old_message"]]
    bad = [r for r in m3 if r["old_message"] != r["new_message"]]
    if not m3:
        v["M3"] = "NOT TESTABLE (no Meson finding read)"
    else:
        v["M3"] = ("HELD (%d of %d identical)" % (len(m3), len(m3)) if not bad
                   else "FAILED (%d of %d differ)" % (len(bad), len(m3)))
    return v


def main():
    os.makedirs(OUT, exist_ok=True)
    wait_for(GUARD_RAW, '__version__ = "%s"' % OLD, "l10n-guard %s on main" % OLD)
    fetch_repo()
    files = repo_files()
    say("repo files: %d" % len(files))
    originals = {}
    for rel in ("l10n_guard.py", "action.yml", "README.md", "skills/l10n-guard/SKILL.md"):
        if rel not in files:
            fail("%s not in the repository" % rel)
        originals[rel] = read_text(os.path.join(REPO, rel))
    if '__version__ = "%s"' % OLD not in originals.get("l10n_guard.py", ""):
        fail("l10n_guard.py in the tarball is not %s" % OLD)
    write(os.path.join(OUT, "old", "l10n_guard_0210.py"), originals["l10n_guard.py"])
    before = run_tests("before")
    SUMMARY["before"] = dict((m, {"exit": r["exit"], "ran": r["ran"], "skipped": r["skipped"]})
                             for m, r in before.items())

    patched = dict(originals)
    t = originals["l10n_guard.py"]
    for what, old, new in CODE:
        t = replace_lines("l10n_guard.py", t, what, old, new)
    patched["l10n_guard.py"] = t
    t = originals["action.yml"]
    for what, required, old, new in ACTION:
        t = replace_lines("action.yml", t, what, old, new, required)
    patched["action.yml"] = t
    t = bump("README.md", originals["README.md"])
    for what, old, new in README:
        t = replace_lines("README.md", t, what, old, new)
    patched["README.md"] = t
    rel = "skills/l10n-guard/SKILL.md"
    t = bump(rel, originals[rel])
    for what, old, new in SKILL:
        t = replace_lines(rel, t, what, old, new)
    patched[rel] = t
    patched["test_0211.py"] = read_text(os.path.join(HERE, "test_0211.py"))
    left = ["%s:%d: %s" % (r, n + 1, line.strip()) for r in sorted(patched)
            for n, line in enumerate(patched[r].split("\n")) if OLD in line]
    write(os.path.join(OUT, "still-0210.txt"), "\n".join(left) + "\n")
    say("lines still mentioning %s: %d (see still-0210.txt)" % (OLD, len(left)))

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
    T = "HELD" if not failing and "test_0211" in after else "FAILED"
    SUMMARY["verdicts"]["T"] = T
    say("T: %s; failing after: %s" % (T, failing))
    if T != "HELD":
        for k in ("A", "S", "M1", "M2", "M3"):
            SUMMARY["verdicts"][k] = "NOT TESTABLE (T failed)"
        finish(0)
    text = after["test_0211"]["text"]
    a_ok = all(re.search(r"%s \(.*\) \.\.\. ok" % name, text)
               for name in ("test_linguas_takes_only_target",
                            "test_locale_config_takes_only_target"))
    SUMMARY["verdicts"]["A"] = "HELD" if a_ok else "FAILED (Action tests skipped or failed)"
    say("A: %s" % SUMMARY["verdicts"]["A"])

    prereg = wait_for(PREREG_URL, PREREG_MARK, "PREREG.md")
    SUMMARY["prereg_sha256"] = hashlib.sha256(prereg).hexdigest()
    say("prereg sha256 %s" % SUMMARY["prereg_sha256"])
    old = load("l10n_guard_0210", os.path.join(OUT, "old", "l10n_guard_0210.py"))
    new = load("l10n_guard_0211", os.path.join(REPO, "l10n_guard.py"))
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
    SUMMARY["verdicts"].update(grade(rows))
    say(json.dumps(SUMMARY["verdicts"], sort_keys=True))
    finish(0)


if __name__ == "__main__":
    main()
