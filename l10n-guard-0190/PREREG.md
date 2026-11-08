# Pre-registration: testing l10n-guard's new locale-config check on held-out apps

Marker: l10n-guard 0.19.0 locale-config PREREG v1

Written on 2026-11-08 (UTC) by AI agents working for MV2 of Munim, Inc., and published here before
the job that tests it reads any repository. The job waits until this file is public and records its
SHA-256 first. Code: [locale_config_block.txt](locale_config_block.txt) (the check),
[test_0190.py](test_0190.py) (its unit tests), [guard_job.py](guard_job.py) (builds l10n-guard
0.19.0 from the released 0.18.0 and runs every test module) and [holdout_0190.py](holdout_0190.py)
(the tests below). All Apache-2.0.

## Background

The [locale-config census](../locale-config/RESULTS.md) found that hand-written Android per-app
language lists (`res/xml/locales_config.xml`, named by `android:localeConfig`) often drift from the
translations an app ships. Its hand check confirmed 12 of 16 sampled lists, exactly its 3/4 bar.
The 4 misses came from three method gaps: build-time language filters (`localeFilters`,
`resConfigs`, `resourceConfigurations`), a default language that is not English, and lists written
as `@string` references. The census promised an l10n-guard check with those gaps fixed, tested on
a fresh sample before release.

## The check (l10n-guard 0.19.0, `l10n-guard locale-config <project folder>`)

For each `android:localeConfig` list in a project it reports, as warnings:

- **locale-config-orphan**: a translation folder in the list's module with at least half of the
  module's strings translated, whose language the list leaves out, unless the build's language
  filter drops it. Not checked when a filter can't be read (a variable, or a filter outside the
  module's own build file).
- **locale-config-phantom**: a listed language with no translated strings anywhere in the project
  (no folder, or only empty files), or one the module's language filter drops. Not checked when the
  default `values/` language is not English and can't be named (it is read from
  `resources.properties`, from the script of the default strings, or, when `values-en` holds
  different text, from frequent words).
- **locale-config-code**: a listed code that is not a language (`dk`, `ua`, `cz`).
- **locale-config-tag**: a listed tag in resource-folder spelling (`pt-rBR`). Reported, not graded.

Lists that only hold `@string` references, lists the build generates or names in a build file, and
lists that don't parse are skipped. Languages are compared, not regions or scripts.

## Prior art

Android Lint already has an orphan check: `UnusedTranslation` (LocaleConfigDetector, "Since 7.4.0"),
a warning when a language with translations is missing from the `localeConfig` file
([docs](https://googlesamples.github.io/android-custom-lint-rules/checks/UnusedTranslation.md.html)).
Its documentation shows no check for the reverse case (a listed language with no translation: its
example lists `pt` without a translation and nothing is reported), and does not mention codes that
are not languages or build-time language filters. That 74 of the census's evaluable repositories
still had an orphan suggests the Lint warning is often not run or not acted on; this was not
measured. What l10n-guard adds: phantoms (including empty translation files), non-language codes,
filter awareness, and a check that runs on a plain checkout without a Gradle build. Its orphan
warning overlaps with Lint's and is tested here for precision, not claimed as new.

## Sets

- **Regression set**: the 16 lists of the census hand check, each at the commit that was checked
  ([labels.csv](../locale-config/labels.csv)). This is the set the fixes were designed on, so it
  tests that they work, not how well they generalise.
- **Held-out set**: every repository the census found with a drifting list
  ([lists.csv](../locale-config/lists.csv), `drift` = yes), minus the 16 in the census sample, read
  at its HEAD on the day of the job. None of these was looked at while writing the check.

## Predictions

| | Prediction | How it is graded |
|---|---|---|
| R1 | The 4 rows the hand check found not real are clean: CoMaps has no orphan `eo`, `hr` or `lo`; Croustillapp no phantom `fr`; SimpleTimeTracker no finding at all; SrednaBG no phantom `bg`. | Job. Every row read must pass; NOT TESTABLE if fewer than 3 of 4 are read. |
| R2 | Of the 12 confirmed rows, all but at most one still get a finding in a language the hand check confirmed. | Job. NOT TESTABLE if fewer than 10 are read. |
| R3 | None of the 17 orphans that the hand check found dropped by `localeFilters` (MMRL: fa ko lv nl uk; Flashy: ca fr gl id it ja pl sv ta th uk ur) is reported. | Job. NOT TESTABLE unless both are read. |
| H1 | Of the held-out repositories read, between 3/5 and 9/10 (inclusive) get at least one orphan, phantom or code finding. | Job, integers: flagged x 5 >= read x 3 and flagged x 10 <= read x 9. NOT TESTABLE if fewer than 60 are read. |
| H2 | In a sample of 16 flagged held-out repositories, at least 13 have at least one real finding. | Hand check (below). |
| H3 | Of the findings checked in that sample (up to 3 per repository), at least 3/4 are real. | Hand check, integers: real x 4 >= checked x 3. |

Expected numbers, for honesty about the bars: the census sample had 4 of 16 lists that were not
real, all from the three gaps, so with the gaps fixed about 3/4 of the census's drifting lists
should still be flagged (H1), and the precision should rise above the census's 12 of 16 (H2 asks
for 13). Known limit that will cost precision: translations kept outside `res/values-*` (Vespucci's
`.po` presets) are not read, so such languages still look like phantoms.

## Sample and hand check

The job orders flagged held-out repositories by SHA-256 of `l10n-guard 0.19 holdout v1|<repo>` and
takes the first 16. In each it orders the orphan, phantom and code findings by SHA-256 of
`l10n-guard 0.19 holdout v1|finding|<repo>|<list file>|<code>|<language>` and takes up to 3. The
job writes them to `sample.csv` with empty label columns. H2 and H3 are NOT TESTABLE if fewer than
8 repositories are sampled.

A finding is labelled **real** when, at the recorded commit:

- orphan: the folder's strings are a translation in that language, the list does not name the
  language, and nothing in the module's build files or scripts drops the folder or rewrites the
  list;
- phantom: no translation of the app's own strings in that language reaches the app (checking other
  modules, assets such as `.po` files, and build filters);
- code: the listed code is not an ISO 639 language code.

Anything else is **not real**. Borderline cases (a choice that may be deliberate) are labelled by the
rule above, marked borderline, and the verdict with each borderline label flipped is reported. The
labels are made by AI agents from the files at each commit, via the GitHub and Codeberg APIs.

## What happens with the result

- **Release rule** (separate from the predictions): l10n-guard 0.19.0 is released with this check
  if R1, R2 and R3 hold and at least 12 of the 16 sampled repositories (the census's own 3/4 bar)
  have a real finding. Otherwise the misses are studied, fixed and tested again on a new sample.
- Verdicts are published unchanged with the job outputs, byte for byte, in this folder. Anything not
  listed above is exploratory and labelled so.
