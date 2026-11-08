# Builds l10n-guard 0.20.0 in a sealed job: applies the pre-registered changes to the released
# 0.19.0 code (exact text replacements, each of which must match once), runs every test module
# before and after, then (once PREREG.md is public) runs the pre-registered tests in
# holdout_0200.py with both the old and the new code. Nothing is published from here.
# Made with AI agents by MV2 of Munim, Inc. Apache-2.0.
import difflib
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True
REPO = os.path.abspath(sys.argv[1])
OUT = os.path.abspath(sys.argv[2])
HERE = os.path.dirname(os.path.abspath(__file__))
OLD, NEW = "0.19.0", "0.20.0"
NEW_NAMES = ("_lc_count", "_lc_other_ui", "_lc_catalog_langs", "_LC_CATALOG", "_LC_LETTERS2_RE",
             "phantoms_elsewhere")
VERSION_RES = [re.compile(r"(?<=@v)0\.19\.0\b"), re.compile(r"(?<=rev: v)0\.19\.0\b"),
               re.compile(r"(?<===)0\.19\.0\b"), re.compile(r'(?<=version = ")0\.19\.0(?=")')]
REPORT = []
SUMMARY = {}

BLOCK_ANCHOR = "\ndef _lc_coverage(paths, read):"

# (what, old text, new text): each old text must occur exactly once in 0.19.0.
REPLACEMENTS = [
    ("coverage dict",
     'for fn in sorted(default_names)), "locales": {}}',
     'for fn in sorted(default_names)), "locales": {},\n'
     '                               "differ": {}}'),
    ("coverage count",
     '        n = sum(len(set(strings(res_dir, d, fn, False)) & set(strings(res_dir, "values", fn, True)))\n'
     '                for fn in shared)\n'
     '        folders[res_dir]["locales"][d] = (lang, n)\n',
     '        counts = [_lc_count(strings(res_dir, d, fn, False), strings(res_dir, "values", fn, True))\n'
     '                  for fn in shared]\n'
     '        n = sum(c[0] for c in counts)\n'
     '        folders[res_dir]["locales"][d] = (lang, n)\n'
     '        folders[res_dir]["differ"][d] = sum(c[1] for c in counts)\n'),
    ("phantom start",
     '    if not default:\n'
     '        rep["phantoms"] = "skipped: default language not English and not identified"\n'
     '    else:\n'
     '        for lang in sorted(listed_langs - bad - default):\n'
     '            kept = translated.get(lang, set())\n'
     '            if kept and (not isinstance(filt, frozenset) or lang in filt):\n'
     '                continue\n',
     '    other_ui = _lc_other_ui(mod, paths)\n'
     '    if other_ui:\n'
     '        rep["phantoms"] = "skipped: " + other_ui\n'
     '    elif not default:\n'
     '        rep["phantoms"] = "skipped: default language not English and not identified"\n'
     '    else:\n'
     '        elsewhere = _lc_catalog_langs(paths)\n'
     '        for lang in sorted(listed_langs - bad - default):\n'
     '            kept = translated.get(lang, set())\n'
     '            if kept and (not isinstance(filt, frozenset) or lang in filt):\n'
     '                continue\n'
     '            if not kept and lang in elsewhere:\n'
     '                rep.setdefault("phantoms_elsewhere", []).append(\n'
     '                    "%s (%s)" % (lang, elsewhere[lang]))\n'
     '                continue\n'),
    ("phantom message",
     '"its %s strings files have no translated strings"',
     '"its %s strings files have no translated strings "\n'
     '                       "(empty, or copies of the default text)"'),
    ("orphan message",
     '"%s has %d of this module\'s %d strings translated, but %s does not list \'%s\', so "',
     '"%s has %d of this module\'s %d strings translated (untranslated copies of default "\n'
     '            "sentences not counted), but %s does not list \'%s\', so "'),
    ("translated set",
     '            if n:\n'
     '                translated.setdefault(lang, set()).add(d)\n',
     '            if folders[res_dir]["differ"][d]:\n'
     '                translated.setdefault(lang, set()).add(d)\n'),
]


def say(line=""):
    print(line, flush=True)
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
    write(os.path.join(OUT, "build-summary.json"), json.dumps(SUMMARY, indent=1, ensure_ascii=True))
    sys.exit(code)


def fail(msg):
    say("PATCH FAILED: " + msg)
    SUMMARY["patch"] = "failed: " + msg
    finish(3)


def repo_files():
    found = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d != ".git" and d != "__pycache__"]
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


def patch_code(text, block):
    eol = "\r\n" if "\r\n" in text else "\n"
    for name in NEW_NAMES:
        if name in text:
            fail("name already in l10n_guard.py: " + name)
    line = '__version__ = "%s"' % OLD
    if text.count(line) != 1:
        fail("__version__ line count %d" % text.count(line))
    text = text.replace(line, '__version__ = "%s"' % NEW)
    for what, old, new in REPLACEMENTS:
        old, new = old.replace("\n", eol), new.replace("\n", eol)
        if text.count(old) != 1:
            fail("%s: old text count %d" % (what, text.count(old)))
        text = text.replace(old, new)
        say("replaced: " + what)
    anchor = BLOCK_ANCHOR.replace("\n", eol)
    if text.count(anchor) != 1:
        fail("_lc_coverage anchor count %d" % text.count(anchor))
    block = block.rstrip("\n").replace("\n", eol)
    text = text.replace(anchor, eol + block + eol + eol + anchor, 1)
    compile(text, "l10n_guard.py", "exec")
    return text


def bump_versions(rel, text):
    changes = []
    new_lines = []
    for line in text.split("\n"):
        new = line
        for rx in VERSION_RES:
            new = rx.sub(NEW, new)
        if new != line:
            changes.append("%s: %r -> %r" % (rel, line.strip(), new.strip()))
        new_lines.append(new)
    return "\n".join(new_lines), changes


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    os.makedirs(OUT, exist_ok=True)
    files = repo_files()
    originals = {rel: read(os.path.join(REPO, rel)) for rel in files
                 if not rel.endswith((".png", ".jpg", ".gif", ".ico"))}
    write(os.path.join(OUT, "files-before.txt"), "\n".join(
        "%s %s" % (hashlib.sha256(originals[r].encode("utf-8", "surrogateescape")).hexdigest(), r)
        for r in sorted(originals)) + "\n")
    say("repo files: %d" % len(files))
    if '__version__ = "%s"' % OLD not in originals.get("l10n_guard.py", ""):
        fail("l10n_guard.py on main is not %s" % OLD)
    # Keep the released code for the old-versus-new comparison.
    write(os.path.join(OUT, "old", "l10n_guard_0190.py"), originals["l10n_guard.py"])
    SUMMARY["baseline"] = run_tests("before")

    patched = dict(originals)
    patched["l10n_guard.py"] = patch_code(originals["l10n_guard.py"],
                                          read(os.path.join(HERE, "block_0200.txt")))
    changes = []
    for rel in sorted(originals):
        if rel.endswith(".py"):
            continue
        new, ch = bump_versions(rel, originals[rel])
        patched[rel] = new
        changes += ch
    for c in changes:
        say("version: " + c)
    left = ["%s:%d: %s" % (rel, n + 1, line.strip())
            for rel in sorted(patched) for n, line in enumerate(patched[rel].split("\n"))
            if OLD in line]
    write(os.path.join(OUT, "still-0190.txt"), "\n".join(left) + "\n")
    say("lines still mentioning %s: %d (see still-0190.txt)" % (OLD, len(left)))
    patched["test_0200.py"] = read(os.path.join(HERE, "test_0200.py"))

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
    SUMMARY["after"] = run_tests("after")
    regressions = [m for m, r in SUMMARY["after"].items()
                   if r["exit"] != 0 and SUMMARY["baseline"].get(m, {}).get("exit") == 0]
    SUMMARY["regressions"] = regressions
    SUMMARY["new_tests_pass"] = SUMMARY["after"].get("test_0200", {}).get("exit") == 0
    say("regressions: %s; test_0200 pass: %s" % (regressions, SUMMARY["new_tests_pass"]))
    if regressions or not SUMMARY["new_tests_pass"]:
        say("tests failed: the pre-registered tests are not run (graded NOT TESTABLE)")
        finish(0)

    sys.path.insert(0, HERE)
    new = load("l10n_guard_0200", os.path.join(REPO, "l10n_guard.py"))
    old = load("l10n_guard_0190", os.path.join(OUT, "old", "l10n_guard_0190.py"))
    import holdout_0200
    say("loaded new %s, old %s" % (new.__version__, old.__version__))
    if (new.__version__, old.__version__) != (NEW, OLD):
        fail("loaded versions %s / %s" % (new.__version__, old.__version__))
    SUMMARY["holdout_exit"] = holdout_0200.main(new, old, OUT, say)
    finish(0)


if __name__ == "__main__":
    main()
