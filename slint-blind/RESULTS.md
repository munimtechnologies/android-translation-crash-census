# slint-blind 0.1.0: results

Made by MV2 of Munim, Inc. with AI agents. Code Apache-2.0; data and text CC BY 4.0.

[i18n-security-lint](https://github.com/ecogetaway/oss-language-inclusion) (Apache-2.0, PyPI 0.2.1) is a
fourth free check run over the census's 366 crashing Android translations, next to Weblate, pofilter and
Android Lint ([../data/checks-blind.md](../data/checks-blind.md)). Predictions were published before the
run: [PREDICTIONS.md](PREDICTIONS.md).

- Run: sealed container job `slint-blind-v1`, 2026-10-17 02:02-02:06Z, i18n-security-lint 0.2.1 installed
  from PyPI, rows from `data/checks-blind-rows.csv` at `50cd0ac`. Tests passed.
- Files: [slint_blind.md](slint_blind.md) (tables and every unflagged row), [slint_blind.json](slint_blind.json),
  [slint_blind_rows.csv](slint_blind_rows.csv) (one row per translation, with each tool's verdict).

## Predictions

- P1, an Android `res/` tree and a `values-es/strings.xml` give no findings and `--strict` exits 0: **HELD**.
  The tool's extractor does not read Android string XML.
- P2, the 366 pairs as one XLIFF file give 0 drift findings: **HELD**. Its extractor pairs source with
  target only in .po files.
- P3, of the 12 rows no other check sees, it flags 0: **HELD**.
- P4, through its Python API it flags fewer than pofilter's 322: **FAILED**. It flags 323.
- P5, the CLI on one-entry .po files agrees with the API on at least 360 of 366 rows: **HELD** (366 of 366,
  0 errors).

## What P4's miss means

| | rows | i18n-security-lint | pofilter |
|---|---:|---:|---:|
| all crashing translations | 366 | 323 | 322 |
| in strings the code formats | 237 | 206 | 215 |

The two tools agree on 305 rows. pofilter alone flags 17. i18n-security-lint alone flags 18, and all 18
are one string: Tella's `Vault_Encryting_SheetText` (`%1$d%% complete`) in 18 languages, where the
translation reads `%d% ...` or `%d % ...`. It flags these because `%1$d` became `%d`, and it compares
placeholder text exactly. That rewrite is harmless in Java on its own; the crash comes from the lone `%`
after it, which neither tool reports. So it flags the right rows for the wrong reason, and the string is
one the census found no code formatting. In strings the code does format, it flags 9 fewer than pofilter.

Read by hand: 6 flagged rows (Briar oc, monocles mail ga, Bimba uk, Who Has My Stuff? da, Metronome ru,
Automation de) and 9 unflagged rows (Flashy gl, Mastodon in, Cryptomator nl, Exodus tr, Element X ja,
Stepsy ar, HeartBeat bn, Material Files eu, FeinstaubWidget de). Each verdict matches what its pattern
`%(?:\(\w+\)|\d+\$)?[sdiufxX]` predicts: it does not see flags, width or precision (`%,d`, `%.1f`,
`%1$,d`), a lone `%` that leaves the matched tokens unchanged, or unnumbered arguments moved into a
different order.

## What this adds

- With four free checks, the union is still 354 of 366: i18n-security-lint finds no crashing row the other
  three miss. The 12 rows no check sees are listed in [../data/checks-blind.md](../data/checks-blind.md).
- Per its source, the exact-text comparison would also flag safe rewrites such as `%1$d` to `%d` in
  single-argument strings. This run only measured crashing rows, so its false-positive rate is not measured.
- The tool was built for security review of locale files in .json, .po, .xliff and .ftl, not for Android,
  so these results say how well it fits Android string files, not whether it meets its own goals.

## Limits

- The rows are the census's extracted text, written as .po entries; the tool was not run on raw Android XML
  except for P1.
- Only crashing rows were tested. Nothing was run on a device.
