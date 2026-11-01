# Results: Android Lint in CI and Java format errors in shipped translations

Graded 2026-11-01 by AI agents working for MV2 of Munim, Inc., against the pre-registration
[PREREG.md](PREREG.md) (lint-ci PREREG v1, SHA-256 `d4cffb941d2b4c748a10ead364f9ff9ca8204d7395ac3bddfaa6259c9b986c50`,
recorded by the job). The job ran on 2026-11-01 from 06:28 to 06:57 UTC with
[lint_ci.py](lint_ci.py) 0.1.0 and [l10n-guard](https://github.com/munimtechnologies/l10n-guard)
0.15.0; its unit tests passed first. Verdicts are copied unchanged from
[summary.json](summary.json). Every error is in [java_format_errors.csv](java_format_errors.csv).
Apache-2.0 code; results and data CC BY 4.0.

## Headline

One in five F-Droid apps whose translations are formatted with `String.format` runs Android
Lint in CI. Those apps ship slightly fewer broken format strings per translated string
(2.2 vs 2.7 per 10,000). But apps of similar size do no better: in 2 of 3 size bands, the
share of apps shipping at least one broken translation is a little *higher* among the apps that
run Lint. Running Lint in CI is not, on this evidence, a guard against translations that crash
`String.format`.

## Verdicts

| | Prediction | Numbers | Verdict |
|---|---|---|---|
| Gate | L >= 50 repos and >= 20,000 exposure; O >= 50 repos | L 371 repos, 437,006 exposure; O 1,434 repos | passed |
| P1 | L is 5%-25% of P | 371 of 1,805 (20.6%) | **HELD** |
| P2 | errors per exposure lower in L than in O | L 95 / 437,006 (2.17 per 10,000); O 236 / 869,993 (2.71 per 10,000) | **HELD** |
| P3 | share of repos with an error lower in L in >= 2 of the testable size strata | lower in 1 of 3 | **FAILED** |

P3 by stratum (exposure = translated strings whose source has a Java format conversion):

| Exposure | L repos with error | O repos with error | L lower? |
|---|---|---|---|
| 1-49 | 2 of 110 (1.8%) | 11 of 650 (1.7%) | no |
| 50-499 | 7 of 129 (5.4%) | 25 of 508 (4.9%) | no |
| 500+ | 18 of 132 (13.6%) | 39 of 276 (14.1%) | yes |

All three strata were testable. The differences are small in every stratum: the honest reading
is "no visible difference", not "Lint makes it worse".

4,693 repositories were listed: 1,805 had exposure >= 1 (population P), 2,797 had none, 91
failed to clone. Both self-test repositories (NewPipe, F-Droid client) were read and classed as
L. l10n-guard read every file pair.

## Exploratory (not pre-registered)

**The O group split.** Apps whose CI runs `check` or `build` but names no Lint task (183 repos)
had the highest rate, 4.1 per 10,000 (19 errors in 46,316); CI without either (654 repos) 2.8;
apps with no CI file at all (597 repos) 2.1, about the same as L. So the pooled P2 difference
comes from the CI groups inside O, not from apps without CI.

**What the errors in Lint-running apps look like.** Of the 95 errors in L:
- 65 are a stray or misplaced `%` that Java reads as a bad placeholder
  (`UnknownFormatConversionException` or `FormatFlagsConversionMismatchException`, as in `% ms`,
  `% MB`, `dîtina % s`);
- 29 are a missing argument, a type clash or reordered unnumbered placeholders; 1 is other;
- 35 sit in `<plurals>` items (O: 74 of 236).
The census's [CHECKS.md](../CHECKS.md), read from Lint's source, says Lint never compares
`<plurals>` items and skips a translation when a `%` is followed by a letter it doesn't know.
We did not run Lint on these apps, so we can't say which of the 95 each blind spot let through.

**Lint settings in L.** Counted per repository and form in top-level and one-level-down Gradle
files: `abortOnError false` (24), `abortOnError = false` (29), `isAbortOnError = false` (1),
a lint baseline (40), a `StringFormat` mention (17). So a sizeable part of L runs Lint without
letting it fail the build, or with old findings suppressed.

**CI platforms seen** (repositories per CI file form, as counted by the job): GitHub Actions 1,005,
GitLab CI 117, Travis 78, Forgejo 23, Woodpecker 19 + 12 + 1 (three file forms, which may
overlap), CircleCI 13, others fewer.

## Prior art and what is new

Ghaleb, Abduljalil and Hassan (ACM TOSEM 2025, [arXiv 2411.06077](https://arxiv.org/abs/2411.06077))
count Android Lint in the CI of open-source Android apps. We found no study that links Lint in CI
to the format errors an app ships in its translations. This is a first measurement of that link,
on 1,805 F-Droid apps, with the comparison fixed before any repository was read.

## Limits

- An association, not a cause; the size strata control for project size only roughly.
- L is a lower bound for "runs Lint": `check`/`build` tasks, scripts and fastlane can run Lint
  too, and those apps are in O.
- l10n-guard errors are not all crashes (reordered placeholders give wrong text instead); in the
  census, l10n-guard 0.5.1 agreed with a real JVM on 354 of 360 crash rows.
- One snapshot of default branches on 2026-11-01.
