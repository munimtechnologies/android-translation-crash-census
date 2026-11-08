# Builds l10n-guard 0.19.0 in a sealed job: applies the locale-config block to the released
# 0.18.0 code, runs every test module before and after, then (once PREREG.md is public) runs
# the pre-registered regression and held-out tests in holdout_0190.py. Nothing is published
# from here. Made with AI agents by MV2 of Munim, Inc. Apache-2.0.
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True
REPO = os.path.abspath(sys.argv[1])
OUT = os.path.abspath(sys.argv[2])
HERE = os.path.dirname(os.path.abspath(__file__))
OLD, NEW = "0.18.0", "0.19.0"
NEW_NAMES = ("check_locale_config", "locale_config_lists", "LOCALE_CONFIG_SUBSTANTIAL", "_lc_",
             "_LC_")
VERSION_RES = [re.compile(r"(?<=@v)0\.18\.0\b"), re.compile(r"(?<=rev: v)0\.18\.0\b"),
               re.compile(r"(?<===)0\.18\.0\b"), re.compile(r'(?<=version = ")0\.18\.0(?=")')]
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


def one_line(lines, pred, what):
    hits = [i for i, l in enumerate(lines) if pred(l)]
    if len(hits) != 1:
        fail("%s anchor count %d" % (what, len(hits)))
    return hits[0]


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
    # Usage line in the module docstring.
    i = one_line(lines, lambda l: l.startswith("  python3 l10n_guard.py text "), "docstring")
    lines.insert(i + 1, "  python3 l10n_guard.py locale-config  path/to/android/project")
    # Subcommand, before args = parser.parse_args(argv).
    i = one_line(lines, lambda l: l.strip() == "args = parser.parse_args(argv)", "parse_args")
    indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
    lines[i:i] = [indent + 'p = sub.add_parser("locale-config")',
                  indent + 'p.add_argument("dir")']
    # Dispatch, before the xliff branch.
    i = one_line(lines, lambda l: l.strip() == 'elif args.kind == "xliff":', "xliff branch")
    indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
    lines[i:i] = [indent + 'elif args.kind == "locale-config":',
                  indent + "    problems, stats = check_locale_config_dir(args.dir)"]
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
    SUMMARY["baseline"] = run_tests("before")

    patched = dict(originals)
    patched["l10n_guard.py"] = patch_code(originals["l10n_guard.py"],
                                          read(os.path.join(HERE, "locale_config_block.txt")))
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
    write(os.path.join(OUT, "still-0180.txt"), "\n".join(left) + "\n")
    say("lines still mentioning %s: %d (see still-0180.txt)" % (OLD, len(left)))
    patched["test_0190.py"] = read(os.path.join(HERE, "test_0190.py"))

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
    SUMMARY["new_tests_pass"] = SUMMARY["after"].get("test_0190", {}).get("exit") == 0
    say("regressions: %s; test_0190 pass: %s" % (regressions, SUMMARY["new_tests_pass"]))
    if regressions or not SUMMARY["new_tests_pass"]:
        say("tests failed: the pre-registered tests are not run (graded NOT TESTABLE)")
        finish(0)

    sys.path.insert(0, REPO)
    sys.path.insert(0, HERE)
    import l10n_guard as guard
    import holdout_0190
    say("imported l10n_guard %s" % guard.__version__)
    code = holdout_0190.main(guard, OUT, say)
    SUMMARY["holdout_exit"] = code
    finish(0)


if __name__ == "__main__":
    main()
