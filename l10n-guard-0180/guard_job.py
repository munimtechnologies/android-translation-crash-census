# Builds l10n-guard 0.18.0 in a sealed job: applies the folder-script / locale-code block,
# runs every test module before and after, and tries the new check on every translation
# folder of one Thunderbird for Android module. Nothing is published from here.
# Made with AI agents by MV2 of Munim, Inc. Apache-2.0.
import contextlib
import difflib
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

sys.dont_write_bytecode = True
REPO = os.path.abspath(sys.argv[1])
OUT = os.path.abspath(sys.argv[2])
HERE = os.path.dirname(os.path.abspath(__file__))
OLD, NEW = "0.17.0", "0.18.0"
NEW_NAMES = ("check_folder_script", "android_locale", "FOLDER_SCRIPTS", "LOCALE_CODE_FIXES",
             "FOLDER_SCRIPT_MIN", "_fs_", "_FS_")
VERSION_RES = [re.compile(r"(?<=@v)0\.17\.0\b"), re.compile(r"(?<=rev: v)0\.17\.0\b"),
               re.compile(r"(?<===)0\.17\.0\b"), re.compile(r'(?<=version = ")0\.17\.0(?=")')]
REPORT = []
SUMMARY = {}


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
    write(os.path.join(OUT, "summary.json"), json.dumps(SUMMARY, indent=1, ensure_ascii=True))
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
    anchor = eol + "def _script_maps(kind, source_path, target_path):"
    if text.count(anchor) != 1:
        fail("_script_maps anchor count %d" % text.count(anchor))
    block = block.rstrip("\n").replace("\n", eol)
    text = text.replace(anchor, eol + block + eol + eol + anchor, 1)
    lines = text.split(eol)
    hits = [i for i, l in enumerate(lines)
            if "if args.kind in _SCRIPT_KINDS and traditional_chinese(" in l]
    if len(hits) != 1:
        fail("_SCRIPT_KINDS hook anchor count %d" % len(hits))
    i = hits[0]
    indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
    j = next((k for k in range(i + 1, min(i + 8, len(lines)))
              if "problems.extend(check_script(" in lines[k]), None)
    if j is None:
        fail("check_script extend line not found after the hook anchor")
    depth, k = 0, j
    while True:
        depth += lines[k].count("(") - lines[k].count(")")
        if depth <= 0:
            break
        k += 1
    after = lines[k + 1] if k + 1 < len(lines) else ""
    if after.strip() and len(after) - len(after.lstrip()) > len(indent):
        fail("the _SCRIPT_KINDS block continues after check_script: %r" % after)
    hook = [indent + 'if args.kind == "android":',
            indent + "    problems.extend(check_folder_script(_read(args.source), _read(args.target),",
            indent + "                                        args.locale or args.target))"]
    lines[k + 1:k + 1] = hook
    say("hook inserted after line %d with indent %d" % (k + 1, len(indent)))
    text = eol.join(lines)
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


def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "l10n-guard-0.18-check (MV2, Munim, Inc.; mv2@munimtech.com)"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def thunderbird(guard):
    tb = "thunderbird/thunderbird-android"
    mod = "feature/mail/message/list/internal/src/main/res"
    commit = json.loads(fetch("https://api.github.com/repos/%s/commits/main" % tb))["sha"]
    listing = json.loads(fetch("https://api.github.com/repos/%s/contents/%s?ref=%s"
                               % (tb, mod, commit)))
    folders = sorted(e["name"] for e in listing
                     if e.get("type") == "dir" and e["name"].startswith("values"))
    raw = "https://raw.githubusercontent.com/%s/%s/%s/%%s/strings.xml" % (tb, commit, mod)
    source = fetch(raw % "values").decode("utf-8")
    rows = []
    for folder in folders:
        if folder == "values":
            continue
        try:
            target = fetch(raw % folder).decode("utf-8")
        except urllib.error.HTTPError as exc:
            rows.append((folder, "", "fetch-%s" % exc.code, ""))
            continue
        try:
            n = len(guard._fs_units(target))
            problems = guard.check_folder_script(source, target, "res/%s/strings.xml" % folder)
        except Exception as exc:  # report, never hide
            rows.append((folder, "", "crash", repr(exc)))
            continue
        if not problems:
            rows.append((folder, n, "-", ""))
        for p in problems:
            rows.append((folder, n, p["code"], p["message"]))
    lines = ["# thunderbird/thunderbird-android %s %s" % (commit, mod),
             "folder\tstrings\tcode\tmessage"]
    lines += ["%s\t%s\t%s\t%s" % r for r in rows]
    write(os.path.join(OUT, "thunderbird.tsv"), "\n".join(lines) + "\n")
    flagged = sorted({r[0] for r in rows if r[2] == "folder-script"})
    known = ["values-am", "values-ar", "values-be", "values-bg", "values-bn"]
    SUMMARY["thunderbird"] = {
        "commit": commit, "folders": len(rows), "flagged": flagged,
        "known_flagged": [f for f in known if f in flagged],
        "other_flagged": [f for f in flagged if f not in known],
        "crashes": [r[0] for r in rows if r[2] == "crash"]}
    say("thunderbird %s: %d folders, folder-script on %s" % (commit[:12], len(rows), flagged))
    # The command line on one real pair, as a user would run it.
    with tempfile.TemporaryDirectory() as tmp:
        paths = {}
        for folder in ("values", "values-ar"):
            path = os.path.join(tmp, folder, "strings.xml")
            os.makedirs(os.path.dirname(path))
            with open(path, "wb") as fh:
                fh.write(fetch(raw % folder))
            paths[folder] = path
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = guard.run(["android", paths["values"], paths["values-ar"]])
        write(os.path.join(OUT, "cli-thunderbird-ar.txt"), "exit %s\n%s" % (code, out.getvalue()))


def main():
    os.makedirs(OUT, exist_ok=True)
    files = repo_files()
    originals = {rel: read(os.path.join(REPO, rel)) for rel in files
                 if not rel.endswith((".png", ".jpg", ".gif", ".ico"))}
    write(os.path.join(OUT, "files-before.txt"), "\n".join(
        "%s %s" % (hashlib.sha256(originals[r].encode("utf-8", "surrogateescape")).hexdigest(), r)
        for r in sorted(originals)) + "\n")
    for rel in ("l10n_guard.py", "README.md", "pyproject.toml", "test_packaging.py",
                "test_0170.py", "action.yml", ".pre-commit-hooks.yaml"):
        if rel in originals:
            write(os.path.join(OUT, "orig", rel.lstrip(".") + ".txt"), originals[rel])
    say("repo files: %d" % len(files))
    SUMMARY["baseline"] = run_tests("before")

    patched = dict(originals)
    patched["l10n_guard.py"] = patch_code(originals["l10n_guard.py"],
                                          read(os.path.join(HERE, "folder_script_block.txt")))
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
    write(os.path.join(OUT, "still-0170.txt"), "\n".join(left) + "\n")
    say("lines still mentioning %s: %d (see still-0170.txt)" % (OLD, len(left)))
    patched["test_0180.py"] = read(os.path.join(HERE, "test_0180.py"))

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
    SUMMARY["new_tests_pass"] = SUMMARY["after"].get("test_0180", {}).get("exit") == 0
    say("regressions: %s; test_0180 pass: %s" % (regressions, SUMMARY["new_tests_pass"]))

    sys.path.insert(0, REPO)
    try:
        import l10n_guard as guard
        say("imported l10n_guard %s" % guard.__version__)
        thunderbird(guard)
    except Exception as exc:  # the build result above still stands
        say("thunderbird check failed: %r" % (exc,))
        SUMMARY["thunderbird"] = "failed: %r" % (exc,)
    finish(0)


if __name__ == "__main__":
    main()
