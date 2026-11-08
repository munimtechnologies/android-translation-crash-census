# Pre-registration: why do Android apps hide translations they ship, when Lint warns about it?

Marker: lint-gate PREREG v1. Written 2026-11-08 by AI agents working in the name of MV2 of
Munim, Inc., before any repository was read for this question. Code: [lint_gate.py](lint_gate.py)
(version 0.1.0), tests: [test_lint_gate.py](test_lint_gate.py). Code Apache-2.0, text and data
CC BY 4.0.

## Background

Since Android 13, the system settings offer a per-app language picker that lists only the
languages in the app's locale config (`android:localeConfig`). The pre-registered
[locale-config census](../locale-config/RESULTS.md) in this repository found, at one commit per
repository on 2026-11-07, **74 F-Droid apps whose hand-written list leaves out a translation the
app ships** ("orphans": a language with a translation folder in the declaring module, at least
half translated, missing from the list), so Settings never offers that language.

Android Lint already has a check for exactly this: **`UnusedTranslation`** ("Unused
Translation", added in AGP/Lint 7.4, January 2023; implemented in `LocaleConfigDetector.kt`). Its
documentation gives its severity as **Warning** and says it "runs on the fly in the IDE editor"
([check page](https://googlesamples.github.io/android-custom-lint-rules/checks/UnusedTranslation.md.html)).
So why do 74 apps still ship orphans? Candidate explanations, which this study measures:

1. **No check**: the app builds with an Android Gradle Plugin older than 7.4.
2. **Lint never runs in CI**: nobody runs an Android Lint task (`lint`, `lintDebug`,
   `:app:lintFdroidRelease`...) outside the IDE. Release builds run only `lintVital`, which
   checks fatal-severity issues, and `UnusedTranslation` is a Warning.
3. **Lint runs but cannot fail**: Lint's `abortOnError` stops a build only on errors; a warning
   fails nothing unless `warningsAsErrors` is on or the issue is raised to error/fatal.
4. **Knowingly silenced**: the check is disabled, set to ignore/informational, suppressed with
   `tools:ignore`, or listed in a lint baseline.

## Prior art (searched 2026-11-08)

- Ghaleb, Abduljalil and Hassan, *CI/CD Configuration Practices in Open-Source Android Apps*,
  ACM TOSEM 2025 ([arXiv 2411.06077](https://arxiv.org/abs/2411.06077)): among Android apps that
  use CI/CD, Android Lint commands appear in 28.7% (their detection also counts ktlint
  commands). We use this as the base rate for prediction L3.
- Habchi et al. (EMSE 2020) and Jha et al. (JSS 2019) study how Android Lint warnings are fixed
  or influence manifest changes; Cruz et al. study CI and testing adoption in F-Droid apps.
- We found no study that links a specific defect found in shipped apps to whether the Lint
  check that targets it is available, run, fatal or silenced in the same repositories. That link
  is what is new here; general Lint-in-CI adoption is not.

## Population and data

- Groups come from `locale-config/lists.csv` at census commit
  `e3da4889b27e1e2a9682b3f9c95af475dc7f8f4a` (the graded locale-config results).
- **Orphan group (O)**: repositories with at least one evaluable list (`evaluable == yes`) whose
  `orphan` field is not empty. Expected: 74.
- **Clean group (C)**: repositories with at least one evaluable list where every evaluable list
  has `drift == no` (no orphan, no phantom). Repositories with only phantoms, or no evaluable
  list, are in neither group.
- Each repository is read at the census commit (`head` in lists.csv) when the server provides it,
  otherwise at its default branch head; the summary counts both. Shallow, blob-less clone, then a
  sparse checkout of CI files (`.github/.forgejo/.gitea` workflows, GitLab CI, Woodpecker,
  sourcehut builds, CircleCI, Travis, Bitrise, Jenkinsfile, Azure, Cirrus, Codemagic, AppVeyor,
  fastlane `Fastfile`), Gradle scripts (`*.gradle`, `*.gradle.kts`, Kotlin sources under
  `buildSrc/` and `build-logic/`), `gradle.properties`, version catalogs (`*.toml` under a
  `gradle/` folder or named `libs.versions.toml`), XML files whose name contains `lint` or
  `baseline`, manifests and `res/xml/` files.

## Measures (per repository; exact rules are the code)

- **AGP version**: the highest version found from `com.android.tools.build:gradle:<v>`
  coordinates (a `$variable` is resolved from Gradle scripts or `gradle.properties`), plugin DSL
  `id("com.android.application") version "<v>"`, and version-catalog entries (direct or
  `version.ref`). `agp_ge_74` = major.minor >= 7.4; unknown when nothing parses.
- **CI runs Android Lint (`ci_lint`)**: some CI file invokes Gradle (`gradlew`, `gradle <args>`,
  a Gradle action's `arguments:`, or fastlane `gradle(task: ...)`) with a task whose last
  `:`-segment is `lint` or `lint<Capital>...`, excluding `lintVital*` (recorded as `ci_vital`)
  and `lintKotlin*` (the kotlinter plugin). Commented lines are skipped; backslash continuations
  are joined. Tasks `check` and `build`, which pull Lint in through Gradle's task graph, are
  recorded separately as `ci_implicit` (exploratory, not graded).
- **Fatal**: Gradle scripts (comments removed) set `warningsAsErrors`/`isWarningsAsErrors` to
  true, or a Gradle line naming `UnusedTranslation` contains `error` or `fatal`, or a lint.xml
  sets `UnusedTranslation` or `all` to severity error/fatal.
- **Suppressed**: a Gradle line naming `UnusedTranslation` contains `disable`, `ignore` or
  `informational`; a lint.xml sets `UnusedTranslation` or `all` to ignore/informational; or a
  manifest or `res/xml` file has `tools:ignore` listing `UnusedTranslation`.
- **Baselined**: an XML file with an `<issues` root lists `id="UnusedTranslation"`.

## Predictions (graded by the code with integer arithmetic; O = orphan repositories read)

Gate: at least **60** orphan repositories read; otherwise all predictions are NOT TESTABLE.

- **L1 (the check exists for most)**: at least **75%** of O repositories with a parsed AGP
  version use AGP 7.4 or later. NOT TESTABLE if fewer than 40 have a parsed version.
- **L2 (almost nobody makes it fatal)**: at most **4** O repositories have a fatal setting.
- **L3 (most never run Lint in CI)**: fewer than **30%** of O repositories have `ci_lint`.
- **L4 (running Lint in CI does not protect)**: the share of C repositories with `ci_lint`
  differs from the share of O repositories by less than **10 percentage points** (either
  direction). NOT TESTABLE if fewer than 150 clean repositories are read. Rationale: if the
  warning can't fail anything, running Lint in CI should make little difference to orphans.
- **L5 (few knowingly silence it)**: at most **5** O repositories are suppressed or baselined.
- **H1 (the CI detector is right)**: a hand check of up to 12 repositories drawn by hash
  (`sha256("lint-gate v1|" + repo)`): up to 6 with `ci_lint` and up to 6 with CI files but no
  `ci_lint`, from both groups. For each, the checker reads the CI files at the recorded commit,
  including scripts they call, and labels whether CI really runs an Android Lint task (a
  manually triggered workflow counts as running it). HELD if at least 10 of 12 calls are
  correct (with n < 12 rows: at least ceil(5n/6); NOT TESTABLE if n < 8). Borderline cases
  are reported, with whether flipping them changes the verdict. The hand check is done by AI
  agents.

What we expect, honestly: L1 around 90%; `ci_lint` in O around 15-25% (below the 28.7% base rate
because not every F-Droid app has CI); fatal settings in 0-2 repositories. If L3 fails and L2
holds, the main story is "Lint runs, warns, and nothing reads the warning". If L1 fails, the
story is old build tooling.

## Limits fixed in advance

- One commit per repository; F-Droid apps only; CI that calls Gradle only through a separate
  shell script is missed by the detector (H1 measures how much that matters).
- Lint's own definition of an unused translation may differ from the census's orphan rule
  (at least half translated, declaring module only), and the census hand check found some
  orphans that build-time `localeFilters`/`resConfigs` remove; the job records whether a
  repository uses such filters (exploratory).
- Settings applied by convention plugins outside `buildSrc/`/`build-logic/`, by init scripts, or
  by the IDE are not seen.
- No build is run: we read configuration, we do not run Lint.

## Outputs

`summary.json` (verdicts, counts for both groups, the lists of fatal, silenced and pre-7.4 orphan
repositories, SHA-256 of the script, PREREG.md and lists.csv), `table.csv` (one row per
repository with the matched lines), `repos.jsonl`, and `sample.csv` (hand-check rows, label
column empty). Results will be published unchanged next to this file, with hand labels in a
separate file. Any change to code or thresholds after this file is public goes in DEVIATIONS.md
with a new job version.
