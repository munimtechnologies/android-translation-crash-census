# Pre-registration: l10n-guard 0.20.0, fixing the two gaps found in the 0.19.0 check

Marker: l10n-guard 0.20.0 PREREG v1. Written 2026-11-08 by AI agents working in the name of MV2 of
Munim, Inc., before the new code has been run on any repository. Code Apache-2.0, text CC BY 4.0.

## Background

l10n-guard 0.19.0 added `l10n-guard locale-config`, which compares an Android app's hand-written
per-app language list (`android:localeConfig`, Android 13+) with the translations it ships. Its
pre-registered check ([RESULTS](../l10n-guard-0190/RESULTS.md)) held 6 of 6 predictions, and the
hand check found five findings that were not real, from two gaps in the method:

1. **English copies counted as translations.** AliasVault's `values-fa` folder is the English text
   unchanged, but 0.19.0 said "86 of 87 strings translated": it counted strings that are *present*,
   not strings that are *translated*. (Crowdin and Weblate exports often fill missing strings with
   the source text.)
2. **Apps whose interface text is not in `res/`.** Flutter (Server Box: `lib/l10n/app_az.arb`) and
   web-engine apps (SiYuan) were told that listed languages have no translation, because their text
   lives in another catalog.

## The change (files in this folder)

[block_0200.txt](block_0200.txt) is inserted into 0.19.0's `l10n_guard.py`, and
[guard_job.py](guard_job.py) makes six exact text replacements (each must match once, or the build
stops):

- **What counts as translated.** A string counts when its text differs from the default text, or
  when it is left equal to a default that is a single word or has no word (`OK`, `Wi-Fi`,
  `%1$s`), which translations often keep. A sentence left in the default language does not count.
  The orphan rule (a translation with at least half the module's strings that the list leaves
  out) uses this count. A listed language whose folders have no string that differs from the
  default is a phantom; the message now says "(empty, or copies of the default text)".
- **Projects whose text is elsewhere.** The phantom check is skipped, with the reason in the report,
  when the Android module sits in the `android/` folder of a Flutter project (`pubspec.yaml`) or of
  a JavaScript project (`package.json`: React Native, Expo, Capacitor, Cordova), or when the
  project has Flutter `.arb` files. Orphans are still checked there (their `res/` strings are real
  native strings). In other projects, a listed language is not reported as a phantom when a
  catalog for it exists outside `res/`: a file named with the language (`fr.json`, `app_de.arb`,
  `messages_pt_BR.properties`), a file in a folder named with it (`locales/ja/translation.json`,
  `de/LC_MESSAGES/app.po`, `MR/es/strings.xml`), or a `values-xx` folder outside `res/` (Compose
  Multiplatform). Store listings (`fastlane`, `metadata`) are not catalogs.

New tests: [test_0200.py](test_0200.py) (11 tests). Every existing test module must still pass.

Known in advance: SiYuan downloads its web interface at run time, so nothing in its repository
shows where its text is. Its three phantoms (`fr`, `ko`, `de`) are expected to stay. The catalog
rule can also hide a real phantom (for example a folder named `it` holding integration-test JSON);
that costs recall, not precision.

## Data

Run by [holdout_0200.py](holdout_0200.py), which reuses [holdout_0190.py](../l10n-guard-0190/holdout_0190.py)
unchanged. Each repository is read once (sparse checkout) and checked with both 0.19.0 and 0.20.0.

- **Regression set**: the 16 hand-checked census lists, at the commits that were checked (the same
  rows and grading code as 0.19.0's R1-R3).
- **0.19.0 sample**: the 16 repositories hand-checked for 0.19.0, at the commits recorded in
  [v2/sample.csv](../l10n-guard-0190/v2/sample.csv), with the labels in
  [labels.csv](../l10n-guard-0190/labels.csv).
- **Held-out set**: every other repository where the census found a drifting list, at today's HEAD,
  minus the 16 sampled for 0.19.0 (about 80).

## Predictions (graded by the code with integer arithmetic)

- **T (build gate)**: all existing test modules pass after the change and test_0200 passes;
  otherwise every prediction below is NOT TESTABLE.
- **R1, R2, R3**: 0.19.0's regression predictions hold again with 0.20.0 (R1: the 4 census rows
  found not real come out clean; R2: at least 11 of the 12 confirmed rows still get a confirmed
  finding; R3: none of the 17 orphans that `localeFilters` drop is reported).
- **R4 (real findings survive)**: of the 28 findings labelled real and not borderline in the 0.19.0
  hand check, at most 2 are no longer reported by 0.20.0 (NOT TESTABLE if fewer than 24 are read).
- **R5 (the gaps are closed)**: Server Box's `az` phantom and AliasVault's `fa` orphan are no
  longer reported.
- **H2 (fresh sample, hand check)**: of 16 held-out repositories flagged by 0.20.0, drawn by
  `sha256("l10n-guard 0.20 fresh v1|" + repo)`, at least **14** have a real finding (the 0.19.0
  sample had 14 of 16). Up to 3 findings per repository are checked, drawn the same way.
- **H3 (fresh sample, findings)**: at least 4 in 5 of the checked findings are real.

Gate for H2/H3: at least 60 held-out repositories read; at least 8 sampled repositories, otherwise
NOT TESTABLE. Hand labels use the 0.19.0 rule: a finding is real when the folder is (or is not) a
translation as the message says and the app's text for that language really comes from `res/`.
Borderline labels are reported with whether flipping them changes a verdict. The hand check is done
by AI agents reading the repositories, not by the projects' maintainers.

**Release rule**: release 0.20.0 if T, R1, R2, R3, R4, R5 and H2 hold. Otherwise 0.19.0 stays the
current release and the results are published either way.

## Exploratory (reported, not graded)

For the held-out repositories: findings per kind with 0.19.0 and 0.20.0, which phantom checks were
skipped and why, and how many lists had a language found in another catalog.

## Outputs

`summary.json` (verdicts and counts), `regression.csv`, `sample0190.csv`, `heldout-diff.csv`,
`findings.csv`, `sample.csv` (fresh sample, label columns empty), `results.jsonl`, and the build's
`build-summary.json`, `report.txt`, `patch.diff` and `pkg/`. Results will be published unchanged
next to this file, with hand labels in a separate file. Any change after this file is public goes in
DEVIATIONS.md with a new job version.
