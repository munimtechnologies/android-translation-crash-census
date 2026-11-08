# Results: why Android apps leave shipped translations out of their language list (pre-registered)

Graded 2026-11-08. Pre-registration: [PREREG.md](PREREG.md) (marker "lint-gate PREREG v1", sha256
`c7a6a87a...2de76`, published before any repository was read). Code: [lint_gate.py](lint_gate.py)
0.1.0 (sha256 `6499741a...dec5`). Job outputs are in [v1/](v1/), byte for byte as the job wrote them;
the hand labels are kept apart in [labels.csv](labels.csv). Made by AI agents working for MV2 of
Munim, Inc.; the hand check was done by AI agents reading the repositories' CI files through GitHub,
not by the projects' maintainers.

## The question

The [locale-config census](../locale-config/RESULTS.md) found 74 F-Droid apps whose hand-written
Android 13+ per-app language list leaves out a translation the app ships ("orphans"), so Android's
per-app language setting never offers it. Android Lint has had a check for exactly this,
`UnusedTranslation`, since AGP 7.4 (January 2023). Why do the orphans survive? We read the build and
CI configuration of the 74 orphan repositories and of 282 "clean" repositories (lists with no drift),
at the same commits as the census, in 1.8 minutes of job time.

## Verdicts (as pre-registered, unchanged)

| Prediction | Bar | Result | Verdict |
|---|---|---|---|
| Gate: orphan repositories read | at least 60 | 74 of 74 | passed |
| L1: the check exists for most (AGP 7.4+) | at least 75% of orphan repos with a parsed AGP version | **74 of 74** (100%) | **HELD** |
| L2: almost nobody makes it fatal | at most 4 orphan repos | **0** | **HELD** |
| L3: most never run Lint in CI | fewer than 30% of orphan repos | **16 of 74** (21.6%) | **HELD** |
| L4: running Lint in CI does not protect | orphan and clean shares differ by under 10 points | 21.6% vs **76 of 282** (27.0%): 5.3 points | **HELD** |
| L5: few knowingly silence it | at most 5 orphan repos suppressed or baselined | **2** | **HELD** |
| H1: the CI detector is right | at least 10 of 12 hand-checked calls correct | **11 of 12** | **HELD** |

All six predictions held. The code's own tests passed before the run.

**H1 details.** The 6 "runs Lint" calls were all right: each step is active (no `if:`, not
commented out) and runs a Lint task (`lint`, `lintDebug`, `lintRelease`, `lintFdroidBenchmark`...).
Of the 6 "doesn't run Lint" calls, 5 were right, including mpv-android, where we traced the CI through
three shell scripts to `./gradlew assembleDebug assembleRelease`. The one miss is moneytoo/Player: its
CI runs `./gradlew build`, and `build` pulls in Lint through `check`. The pre-registration records such
tasks separately (`ci_implicit`), so the detector's narrow call is wrong for that repository. Borderline
cases: three "no" repositories build release variants, which runs `lintVital` (fatal-severity issues
only; `UnusedTranslation` is a warning). The pre-registration excludes `lintVital` from "runs Lint", so
these stay "no"; if they were counted as "yes", H1 would be 8 of 12 and would fail. One repository's
CI includes a template from another project that we could not read (security-scan jobs).

## What this means

- **The check is there.** Every orphan app builds with AGP 7.4 or later, so `UnusedTranslation` is
  available to all of them. Old tooling is not the explanation.
- **Lint mostly doesn't run outside the IDE.** 16 of 74 orphan apps (22%) run a Lint task in CI;
  7 more run `build` or `check`, which include Lint (23 of 74, 31%). Among orphan apps that have CI at
  all, 16 of 60 (27%) run Lint explicitly, close to the 28.7% that Ghaleb et al. (TOSEM 2025) report
  for CI-using Android apps.
- **Where it runs, it can't fail anything.** None of the 74 orphan apps makes Lint warnings fatal,
  and `UnusedTranslation` is a warning. Running Lint in CI barely differs between orphan apps (21.6%)
  and clean ones (27.0%). So the warning is produced, if at all, in a report nobody has to read.
- **Silencing is rare.** Two orphan apps suppress the check on purpose with `tools:ignore` on
  `<application>`: Clock (BlackyHawky) and a fork of it. No repository uses a lint baseline for it.

In short: the orphans are not caused by missing tooling or by deliberate choices; they survive because a
warning-level check, in projects that mostly don't run Lint in CI and never make warnings fatal,
does not stop anything. A check that runs without a Gradle build and can fail CI on just this
problem (such as `l10n-guard locale-config --strict`) addresses that gap; whether projects adopt it is
a separate question we have not measured.

## Exploratory (not pre-registered; treat as hints)

- **Fatal settings appear only in clean apps**: 14 of 282 clean repositories set Lint's
  `warningsAsErrors` (two spot-checked: Exclave sets `lint.warningsAsErrors = true` in buildSrc, and
  VES-Image-Compare sets it in `lint { }`), against 0 of 74 orphan repositories. If fatal settings were
  spread at random, the chance of none landing in the orphan group is about 3.6% (one-sided
  hypergeometric). This is one of many comparisons made after the fact, and several of those 14 apps
  don't run Lint in CI at all (Exclave also sets `checkReleaseBuilds = false`), so `warningsAsErrors`
  may mark careful maintainers rather than be the cause of clean lists.
- `abortOnError false` is more common among orphan repositories (16 of 74, 22%) than clean ones
  (26 of 282, 9%). Build-time language filters (`localeFilters`/`resConfigs`) appear in 21 of 74 and
  63 of 282.
- 3 clean repositories build with an AGP older than 7.4; none of the orphan ones do.

## Limits

One commit per repository, F-Droid apps only. We read configuration and did not run Gradle or Lint,
so we do not know whether Lint's own definition of an unused translation matches every census orphan
(the census counts a folder at least half translated; build-time filters can also remove orphans).
Settings applied by convention plugins outside `buildSrc/`/`build-logic/`, by init scripts or by
the IDE are not seen. The hand check covers 12 repositories.

## Files

- [labels.csv](labels.csv): one row per hand-checked repository, with the label and the evidence.
- [v1/summary.json](v1/summary.json), [v1/table.csv](v1/table.csv), [v1/repos.jsonl](v1/repos.jsonl),
  [v1/sample.csv](v1/sample.csv): job outputs, unchanged (the `label` column of sample.csv is empty by
  design).

Licence: text and data CC BY 4.0; code Apache-2.0.
