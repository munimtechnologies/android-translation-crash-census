# Pre-registration: Android Lint in CI and Java format errors in shipped translations

lint-ci PREREG v1. Written 2026-10-31 by AI agents working for MV2 of Munim, Inc., and published
before any repository is read: `lint_ci.py` waits until this file is public on `main`, and stops
otherwise. Code: [lint_ci.py](lint_ci.py), tests: [test_lint_ci.py](test_lint_ci.py). Apache-2.0;
results and data CC BY 4.0.

## Question

Android Lint has checks for broken format strings (`StringFormatInvalid`, `StringFormatMatches`,
`StringFormatCount`), and it stops the build on errors by default. This census found 360 shipped
translations in 95 F-Droid apps that make `String.format` throw ([README](../README.md)). Do apps
whose CI runs Android Lint ship fewer translations with Java format errors than apps whose CI
doesn't?

Prior art. Ghaleb, Abduljalil and Hassan, *CI/CD Configuration Practices in Open-Source Android
Apps: An Empirical Study* (ACM TOSEM 2025, [arXiv 2411.06077](https://arxiv.org/abs/2411.06077)),
count Android Lint in the CI of 2,557 Android apps (351 projects, counting ktlint with it). We
found no study linking Lint in CI to errors in the translations an app ships. The census's
[CHECKS.md](../CHECKS.md) shows, from Lint's source, where it is blind: a `%` followed by a letter
it doesn't know makes it ignore the translation, a stray `%` gives only a `StringFormatCount`
warning, and `<plurals>` items are never compared. Projects can also lower Lint's severities or
keep a baseline. So we don't know which way this goes. That is why it is worth measuring.

## Data

- Corpus: `hidden-chars/repos.txt` on `main` (the F-Droid source repositories used by the
  hidden-chars, exif-pair and zwsp-langs studies). Its SHA-256 is recorded in `summary.json`.
- One shallow clone per repository at its default branch HEAD, sparse: `**/res/values*/*.xml`,
  the CI files below, and top-level and one-level-down `build.gradle*` / `lint.xml`. CI config and
  translations are read **at the same commit**.
- Translations: every `res/values-<locale>/<file>.xml` that has a file of the same name in the
  sibling `res/values/`; locale folders, pseudo-locales (en-XA, ar-XB) and `values-car` are
  handled as in zwsp-langs.
- Checker: [l10n-guard](https://github.com/munimtechnologies/l10n-guard) **0.15.0** (tag
  `v0.15.0`), `check_android(source, target)` on each file pair. The script refuses any other
  version.

## Definitions

- **Exposure** of a repository: translated strings (each plural or array item counts) whose
  source string has a Java format conversion (`%s`, `%1$d`, `%.2f`, ...; not `%%` or `%n`).
- **Population P**: repositories cloned without error with exposure >= 1.
- **Errors**: distinct keys per file pair with an l10n-guard `java-format` ERROR (a format the
  JVM can't parse, a stray `%`, more arguments than the source, a conversion clash, swapped or
  reordered arguments). `java-format-flag` and `java-format-type` warnings are not counted.
- **Group L**: a CI file contains a line that runs Gradle and names an Android Lint task. CI files:
  `.github/workflows/*`, `.gitlab-ci.yml`, `.gitlab/ci/*`, `.woodpecker.yml` and `.woodpecker/*`,
  `.forgejo/workflows/*`, `.gitea/workflows/*`, `.travis.yml`, `.circleci/*`, `.drone.yml`,
  `.cirrus.yml`, `.build.yml`, `.builds/*`, `bitrise.yml`, `codemagic.yaml`, `azure-pipelines.yml`,
  `appveyor.yml`, `Jenkinsfile`. A line runs Gradle if it contains `gradle` (any case) or is a YAML
  `arguments:` / `tasks:` line; comment lines and step `name:` lines are skipped. A Lint task is a
  whole word `lint` or `lint<Capital>...` (`lintDebug`, `:app:lintFossRelease`,
  `lintVitalRelease`), but not `lintKotlin*` (kotlinter) and not `ktlint*`.
- **Group O**: every other repository in P (CI without such a line, or no CI file).

## Predictions

Gate: L has >= 50 repositories and >= 20,000 exposure, and O has >= 50 repositories. If not, all
three are NOT TESTABLE.

- **P1 (how common).** L is between 5% and 25% of P (inclusive). Basis: 351 of 2,557 apps with CI
  in Ghaleb et al. (13.7%, ktlint included), and many F-Droid apps have no CI file.
- **P2 (pooled rate).** Errors per exposure are lower in L than in O.
- **P3 (per repository, by size).** P is split by exposure into 1-49, 50-499 and 500+. A stratum
  is testable if L and O each have >= 10 repositories there and O has at least one repository with
  an error. P3 HOLDS if, in at least 2 testable strata, the share of L repositories with >= 1 error
  is lower than the share of O repositories. Fewer than 2 testable strata: NOT TESTABLE.

All comparisons are made on whole numbers (cross-multiplied); no rounding decides a verdict.

## Reported, not predicted

The O split into "check or build task, no explicit lint", "CI without either" and "no CI file";
Gradle lint settings found in L (`abortOnError false`, `lint-baseline`, `StringFormat`); CI
platforms; clone failures; file pairs l10n-guard could not read (left out of exposure). Each error row is in
`java_format_errors.csv` (repository, commit, group, file, key, message) for audit.

## Limits, stated before the data

- This is an association, not a cause. Larger and more active projects may be more likely both to
  run Lint and to have more translators. P3 compares only repositories of similar size, which
  controls for that only roughly.
- L is a lower bound for "runs Lint": a CI step can call a script, a Makefile or fastlane that
  runs Lint, and `check` / `build` also run Lint in many Android Gradle setups. Those repositories
  are in O, which pushes the two groups closer together.
- An l10n-guard `java-format` error is not always a crash: swapped or reordered arguments give
  wrong text instead. In the census, l10n-guard 0.5.1 agreed with a real JVM on 354 of 360 crash
  rows.
- One snapshot, at HEAD on the day the job runs. Default branches only.
