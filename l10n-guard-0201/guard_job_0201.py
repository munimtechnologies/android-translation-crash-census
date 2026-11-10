# Builds l10n-guard 0.20.1 in a sealed job: the unreleased 0.20.0 changes (guard_job.py and
# block_0200.txt, downloaded unchanged from the census repository) plus the 0.20.1 change
# (block_0201.txt and the replacements below), applied to the released 0.19.0 code. Runs every
# test module before and after, then (once PREREG.md is public) the pre-registered tests in
# holdout_0200.py with the new and the 0.19.0 code. Nothing is published from here.
# Made with AI agents by MV2 of Munim, Inc. Apache-2.0.
import os
import sys

sys.dont_write_bytecode = True
import guard_job as gj  # noqa: E402  (reads sys.argv: repo folder, out folder)

HERE = os.path.dirname(os.path.abspath(__file__))
CENSUS = ("https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/"
          "main/")
gj.NEW = "0.20.1"
gj.NEW_NAMES = gj.NEW_NAMES + ("_lc_dnt",)

# l10n_guard.py, applied after the six 0.20.0 replacements (each old text must occur once).
gj.REPLACEMENTS = gj.REPLACEMENTS + [
    ("donottranslate files out of the module count",
     'for fn in sorted(default_names)), "locales": {},',
     'for fn in sorted(default_names)\n'
     '                                               if not _lc_dnt(fn)), "locales": {},'),
    ("donottranslate files out of each translation's count",
     '        shared = sorted(names & default_names)\n',
     '        shared = sorted(fn for fn in names & default_names if not _lc_dnt(fn))\n'),
]

# Other files (each old text must occur once; checked after the version bump).
DOC_REPLACEMENTS = [
    ("README.md", "known limits",
     "  Known limits from that test: **ignore phantom warnings in apps whose text isn't in `res/`**\n"
     "  (Flutter `.arb`, React Native, web-view apps), and know that a folder's size counts every string\n"
     "  it holds, so a folder of untranslated English copies can still be reported as an orphan.\n",
     "  Since 0.20.1 the check closes the two gaps that test found. A string counts as translated\n"
     "  only when it differs from the default text or keeps a one-word or wordless default (`OK`,\n"
     "  `%1$s`), so a folder of untranslated English copies is no longer an orphan; and phantom\n"
     "  checks are skipped in Flutter and JavaScript apps (React Native, Expo, Capacitor, Cordova)\n"
     "  and for languages with a catalog outside `res/`. Files named `donottranslate*.xml` are left\n"
     "  out of the counts, as Android Lint treats them\n"
     "  ([0.20.1 check](https://github.com/munimtechnologies/android-translation-crash-census/blob/main/l10n-guard-0201/RESULTS.md)).\n"),
    ("skills/l10n-guard/SKILL.md", "skill version",
     'version: "0.19.0"',
     'version: "0.20.1"'),
    ("skills/l10n-guard/SKILL.md", "skill limits",
     "- `locale-config` sizes a translation by the strings a folder holds, untranslated copies\n"
     "  included, and reads only Android `res/` folders. In its pre-registered test 31 of 36 sampled\n"
     "  findings were real; the misses were phantoms in apps whose text isn't in `res/` and one folder\n"
     "  of English copies\n",
     "- `locale-config` reads only Android `res/` folders. Since 0.20.1 it counts a string as\n"
     "  translated only when it differs from the default (or keeps a one-word default such as `OK`),\n"
     "  skips phantom checks in Flutter and JavaScript apps, and leaves `donottranslate*.xml` out, as\n"
     "  Android Lint does. In the 0.19.0 test 31 of 36 sampled findings were real; the misses were\n"
     "  phantoms in apps whose text isn't in `res/` and one folder of English copies\n"),
]


def replace_once(rel, text, what, old, new):
    eol = "\r\n" if "\r\n" in text else "\n"
    old, new = old.replace("\n", eol), new.replace("\n", eol)
    if text.count(old) != 1:
        gj.fail("%s %s: old text count %d" % (rel, what, text.count(old)))
    gj.say("replaced: %s %s" % (rel, what))
    return text.replace(old, new)


def fix_packaging_test(text):
    """test_pip_line_names_this_version wants exactly one versioned pip line, but the README
    has two (install section and the locale-config CI example), so it fails on the released
    0.19.0 already. It now checks that every versioned pip line names this version, as
    test_action_examples_name_this_version does for the Action lines."""
    eol = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(eol)
    at = [i for i, x in enumerate(lines) if "def test_pip_line_names_this_version" in x]
    if len(at) != 1:
        gj.fail("test_packaging: test_pip_line_names_this_version found %d times" % len(at))
    j = at[0] + 1
    line = lines[j]
    if "re.findall(" not in line or "[g.__version__])" not in line or "assertEqual(" not in line:
        gj.fail("test_packaging: unexpected line %r" % line)
    pad = line[:len(line) - len(line.lstrip())]
    expr = line[line.index("re.findall("):line.rindex(", [g.__version__])")]
    lines[j:j + 1] = [pad + "found = " + expr,
                      pad + "self.assertTrue(found)",
                      pad + "self.assertEqual(set(found), {g.__version__})"]
    gj.say("replaced: test_packaging pip-line test")
    return eol.join(lines)


def main():
    OUT, REPO, OLD, NEW = gj.OUT, gj.REPO, gj.OLD, gj.NEW
    os.makedirs(OUT, exist_ok=True)
    files = gj.repo_files()
    originals = {rel: gj.read(os.path.join(REPO, rel)) for rel in files
                 if not rel.endswith((".png", ".jpg", ".gif", ".ico"))}
    gj.say("repo files: %d" % len(files))
    if '__version__ = "%s"' % OLD not in originals.get("l10n_guard.py", ""):
        gj.fail("l10n_guard.py on main is not %s" % OLD)
    gj.write(os.path.join(OUT, "old", "l10n_guard_0190.py"), originals["l10n_guard.py"])
    gj.SUMMARY["baseline"] = gj.run_tests("before")

    block = (gj.read(os.path.join(HERE, "block_0200.txt")).rstrip("\n") + "\n\n\n"
             + gj.read(os.path.join(HERE, "block_0201.txt")))
    patched = dict(originals)
    patched["l10n_guard.py"] = gj.patch_code(originals["l10n_guard.py"], block)
    changes = []
    for rel in sorted(originals):
        if rel.endswith(".py"):
            continue
        new, ch = gj.bump_versions(rel, originals[rel])
        patched[rel] = new
        changes += ch
    for rel, what, old, new in DOC_REPLACEMENTS:
        patched[rel] = replace_once(rel, patched[rel], what, old, new)
    patched["test_packaging.py"] = fix_packaging_test(patched["test_packaging.py"])
    for c in changes:
        gj.say("version: " + c)
    left = ["%s:%d: %s" % (rel, n + 1, line.strip())
            for rel in sorted(patched) for n, line in enumerate(patched[rel].split("\n"))
            if OLD in line]
    gj.write(os.path.join(OUT, "still-0190.txt"), "\n".join(left) + "\n")
    gj.say("lines still mentioning %s: %d (see still-0190.txt)" % (OLD, len(left)))
    for name in ("test_0200.py", "test_0201.py"):
        patched[name] = gj.read(os.path.join(HERE, name))

    import difflib
    diff = []
    for rel in sorted(patched):
        if patched[rel] != originals.get(rel):
            gj.write(os.path.join(REPO, rel), patched[rel])
            gj.write(os.path.join(OUT, "pkg", rel), patched[rel])
            diff += difflib.unified_diff(originals.get(rel, "").splitlines(True),
                                         patched[rel].splitlines(True), "a/" + rel, "b/" + rel)
    gj.write(os.path.join(OUT, "patch.diff"), "".join(diff))
    gj.SUMMARY["changed"] = sorted(r for r in patched if patched[r] != originals.get(r))
    gj.SUMMARY["version_changes"] = changes
    gj.SUMMARY["patch"] = "ok"
    after = gj.run_tests("after")
    gj.SUMMARY["after"] = after
    failing = sorted(m for m, r in after.items() if r["exit"] != 0)
    gj.SUMMARY["failing_after"] = failing
    gj.SUMMARY["T"] = ("HELD" if not failing and "test_0201" in after and "test_0200" in after
                       else "FAILED")
    gj.say("T: %s; failing after: %s" % (gj.SUMMARY["T"], failing))
    if gj.SUMMARY["T"] != "HELD":
        gj.say("T failed: the pre-registered tests are not run (graded NOT TESTABLE)")
        gj.finish(0)

    sys.path.insert(0, HERE)
    new = gj.load("l10n_guard_0201", os.path.join(REPO, "l10n_guard.py"))
    old = gj.load("l10n_guard_0190", os.path.join(OUT, "old", "l10n_guard_0190.py"))
    import holdout_0200 as ho
    ho.PREREG_URL = CENSUS + "l10n-guard-0201/PREREG.md"
    ho.PREREG_MARK = "l10n-guard 0.20.1 PREREG v1"
    ho.KEY = "l10n-guard 0.20.1 fresh v1"
    # Repositories hand-checked for 0.20.0 go to the end of the draw order (PREREG.md).
    prev = {r["repo"] for r in ho.csv_rows(CENSUS + "l10n-guard-0200/v1/sample.csv")}
    gj.SUMMARY["excluded_from_draw"] = sorted(prev)
    draw_key = ho.key

    def key(*parts):
        k = draw_key(*parts)
        return ("~" + k) if len(parts) == 1 and parts[0] in prev else k

    ho.key = key
    gj.say("loaded new %s, old %s; %d repositories from the 0.20.0 sample moved last"
           % (new.__version__, old.__version__, len(prev)))
    if (new.__version__, old.__version__) != (NEW, OLD):
        gj.fail("loaded versions %s / %s" % (new.__version__, old.__version__))
    gj.SUMMARY["holdout_exit"] = ho.main(new, old, OUT, gj.say)
    gj.SUMMARY["R6"] = grade_r6(os.path.join(OUT, "sample0190.csv"))
    gj.say("R6: %s" % gj.SUMMARY["R6"])
    gj.finish(0)


R6_CASES = [("https://github.com/BlackyHawky/Clock", "th"),
            ("https://github.com/BlackyHawky/Clock", "ca"),
            ("https://github.com/RapidAppCoder/mighty-alarm-clock", "ja")]


def grade_r6(path):
    """R6: the three orphans 0.20.0 lost are reported again by 0.20.1 (sample0190.csv:
    the column reported_0200 holds the new build's result)."""
    import csv
    if not os.path.isfile(path):
        return "NOT TESTABLE (no sample0190.csv)"
    with open(path, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    got = []
    for repo, lang in R6_CASES:
        hit = [r for r in rows if r["repo"] == repo and r["language"] == lang
               and r["code"] == "locale-config-orphan"]
        if not hit or hit[0]["status"] != "ok":
            return "NOT TESTABLE (%s %s not read)" % (repo.rsplit("/", 1)[-1], lang)
        got.append(hit[0]["reported_0200"] == "yes")
    return "HELD" if all(got) else "FAILED (%d of 3 reported)" % sum(got)


if __name__ == "__main__":
    main()
