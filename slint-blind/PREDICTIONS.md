# Predictions: i18n-security-lint 0.2.1 over the census's crashing translations

MV2 of Munim, Inc. Made with AI agents. Written 2026-10-17, before slint_blind.py was first run.
Licence: this text CC BY 4.0; slint_blind.py and its tests Apache-2.0.

## What is tested

[i18n-security-lint](https://github.com/ecogetaway/oss-language-inclusion) (Apache-2.0, PyPI 0.2.1,
2026-08-26) is a free CI scanner for translated strings. One of its checks is "format-specifier
tampering": a translator adding, dropping or retyping a placeholder. The census already measured
three free checks (Weblate's Java format check, translate-toolkit's pofilter `printf` test and
Android Lint) against its 366 crashing Android translations (data/checks-blind.md: pofilter flags
322, Weblate 300, Lint 239, and 12 rows in 9 repositories are seen by none of them).
slint_blind.py adds this fourth tool, installed from PyPI and called, never copied, on the same
rows (data/checks-blind-rows.csv at commit 50cd0ac).

## What reading its source (commit b5dd40f) leads us to expect

The placeholder check finds `%(?:\(\w+\)|\d+\$)?[sdiufxX]` and `{0}` / `{name}` / `{{name}}` /
`$name` tokens in source and translation, sorts each list, and reports drift when the lists differ.
So it cannot see flags, width or precision (`%,d`, `%2.1f`, `%1$,d`), conversions outside
s/d/i/u/f/x/X (`%e`, `%c`, `%b`, `%n`), a stray `%` that leaves the matched tokens unchanged, or a
reordering. Its extractor reads .json, .po, .xliff/.xlf and .ftl files only, and pairs a
translation with its source only in .po files.

- P1. An Android `res/` tree, and a `values-es/strings.xml` named directly, give no findings, and
  `--strict` exits 0, although each of the three Spanish strings throws in java.util.Formatter.
- P2. The 366 pairs written as one XLIFF file with `<source>` and `<target>` give 0 drift findings.
- P3. Of the 12 rows no other check sees, it flags 0.
- P4. Through its Python API it flags fewer of the 366 rows than pofilter's 322.
- P5. Writing each row as a one-entry .po file and running the tool's CLI gives the same verdict
  as the API on at least 360 of the 366 rows.

## Limits

The rows are the census's extracted text, not raw XML, so this measures the check as if a project
kept these strings in a .po file. P1 and P2 describe the tool as shipped. The tool was built for
security review of locale files, not for Android, so "it does not see these" is a statement about
fit, not a criticism of its own goals.
