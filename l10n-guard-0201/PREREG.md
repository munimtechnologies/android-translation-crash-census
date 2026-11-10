# Pre-registration: l10n-guard 0.20.1 (0.20.0 plus Android Lint's donottranslate rule)

Marker: l10n-guard 0.20.1 PREREG v1. Written 2026-11-10 by AI agents working in the name of MV2 of
Munim, Inc., before the new code has been run on any repository. Code Apache-2.0, text CC BY 4.0.

## Background

0.20.0 changed what the `locale-config` check counts as a translated string, so that folders of
untranslated English copies stop being reported as translations. Its pre-registered check
([RESULTS](../l10n-guard-0200/RESULTS.md)) was fully precise on a fresh sample (16 of 16
repositories, 33 of 33 findings real) but **failed R4**: it lost three real orphans that 0.19.0 had
reported (Clock `th` and `ca`, mighty-alarm-clock `ja`), so it was not released.

A diagnostic job (`guard-0200-diag-v1`, [diag_0200.py](../l10n-guard-0200/diag_0200.py), exploratory)
printed the counts behind those three. All three fall just under the 50% line:

| Folder | Module strings (den) | 0.19.0 count | 0.20.0 count | 50% line |
|---|---|---|---|---|
| Clock `values-th` | 1,209 | 614 | 602 | 604.5 |
| Clock `values-ca` | 1,209 | 614 | 602 | 604.5 |
| mighty-alarm-clock `values-ja` | 1,270 | 637 | 626 | 635 |

The strings 0.20.0 stopped counting are city names kept as they are (`Pago Pago`, `Lord Howe
Island`), which is correct translation practice. But the denominator also includes each app's
`values/donottranslate.xml` (126 strings in Clock, 96 in mighty-alarm-clock). **Android Lint treats
every string in a values file whose name starts with `donottranslate` as `translatable="false"`**
(`TranslationDetector`, MissingTranslation check), so those strings should never have been counted.
Without them the module counts are 1,083 and 1,174, and all three folders are above half (602 of
1,083; 626 of 1,174). None of the three translation folders has its own `donottranslate.xml`
(each holds only `cities.xml` and `strings.xml` at the recorded commits).

We say plainly that these three known cases shaped this change. That is why the change follows an
existing published rule (Android Lint's) instead of moving the 50% line, and why it is tested again
on a fresh sample below.

## The change (files in this folder)

[guard_job_0201.py](guard_job_0201.py) applies the unreleased 0.20.0 changes unchanged
([guard_job.py](../l10n-guard-0200/guard_job.py), [block_0200.txt](../l10n-guard-0200/block_0200.txt))
plus, from [block_0201.txt](block_0201.txt) and two more exact replacements (each must match once):

- Values files whose name starts with `donottranslate` are left out of a module's string count and
  out of each translation folder's count. A folder that shares only such a file with the default
  folder is not a translation.
- Housekeeping: the version becomes 0.20.1 everywhere 0.19.0 was named as the current version
  (including the skill's `version:` field, which 0.20.0 missed); the README's and the skill's
  "known limits" text now describes 0.20.x; and `test_packaging.test_pip_line_names_this_version`,
  which fails on the released 0.19.0 because the README has two versioned pip lines, now checks
  that every versioned pip line names this version (as the Action-examples test already does).

New tests: [test_0201.py](test_0201.py) (6 tests); 0.20.0's test_0200.py is kept.

## Data

Run by [holdout_0200.py](../l10n-guard-0200/holdout_0200.py), downloaded unchanged, with its
pre-registration address, marker and draw key set to this file's. Each repository is read once and
checked with 0.19.0 (released) and 0.20.1. In its outputs the columns named `0200`
(`reported_0200`, `findings_0200`, `in_0200`) hold the **0.20.1** results.

- **Regression set** and **0.19.0 sample**: exactly as for 0.20.0 (same commits, same labels).
- **Held-out set**: as for 0.20.0, at today's HEAD.
- **Fresh draw**: flagged held-out repositories ordered by `sha256("l10n-guard 0.20.1 fresh v1|" +
  repo)`; the 16 repositories hand-checked for 0.20.0 ([v1/sample.csv](../l10n-guard-0200/v1/sample.csv))
  are moved to the end of that order, so they are drawn only if fewer than 16 others are flagged.

## Predictions (graded with integer arithmetic)

- **T (build gate)**: after the change **every** test module in the repository passes, including
  test_packaging, test_0200 and test_0201. (0.20.0 graded T as "no new failure"; this time it is
  strict.) Otherwise every prediction below is NOT TESTABLE.
- **R1, R2, R3**: as for 0.19.0 and 0.20.0 (R1: the 4 census rows found not real come out clean;
  R2: at least 11 of the 12 confirmed rows still get a confirmed finding; R3: none of the 17 orphans
  that `localeFilters` drop is reported).
- **R4**: of the 28 findings labelled real and not borderline in the 0.19.0 hand check, at most 2
  are no longer reported (NOT TESTABLE if fewer than 24 are read).
- **R5**: Server Box's `az` phantom and AliasVault's `fa` orphan are still not reported.
- **R6**: the three orphans 0.20.0 lost (Clock `th`, Clock `ca`, mighty-alarm-clock `ja`) are all
  reported.
- **H2 (fresh draw, hand check)**: of 16 drawn repositories, at least **14** have a real finding.
  Up to 3 findings per repository, drawn as in 0.20.0.
- **H3**: at least 4 in 5 of the checked findings are real.

Gate for H2/H3 as before: at least 60 held-out repositories read and at least 8 drawn. Hand labels
use the 0.19.0 rule (a finding is real when the folder is, or is not, a translation as the message
says and the app's text for that language really comes from `res/`), borderline labels are
reported with whether flipping them changes a verdict, and the check is done by AI agents reading
the repositories, not by the projects' maintainers.

**Release rule**: release 0.20.1 if T, R1-R6 and H2 hold. Otherwise 0.19.0 stays the current
release, and the results are published either way.

## Exploratory (reported, not graded)

Findings per kind with 0.19.0 and 0.20.1 on the held-out set, phantom checks skipped and why.

## Outputs

As for 0.20.0: `summary.json`, `regression.csv`, `sample0190.csv`, `heldout-diff.csv`,
`findings.csv`, `sample.csv`, `results.jsonl`, `build-summary.json` (with T and R6), `report.txt`,
`patch.diff`, `still-0190.txt` and `pkg/`. Published unchanged next to this file, with hand labels
in a separate file. Any change after this file is public goes in DEVIATIONS.md with a new job
version.
