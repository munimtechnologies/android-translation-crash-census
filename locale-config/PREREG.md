# Pre-registration: Android per-app language lists that don't match the app's translations

Marker: locale-config PREREG v1

Written and published on 2026-11-07, before any repository is read for this study. Made with AI
agents by MV2 of Munim, Inc. Code: [locale_config.py](locale_config.py) (Apache-2.0), tests:
[test_locale_config.py](test_locale_config.py). The job waits until this file is public at the
census repository's `main` branch and records its SHA-256 before it reads any repository.

## Question

Since Android 13, a user can choose a language for a single app in the system settings. Settings
offers only the languages in the app's **locale config**: either a hand-written file in `res/xml/`
that the manifest names with `android:localeConfig`, or one the Android Gradle Plugin writes from
the app's resource folders (`androidResources { generateLocaleConfig = true }`). A hand-written
list is a second copy of the app's language list, and nothing checks that it keeps up with the
translations:

- **Orphan:** the app ships a translation that the list leaves out, so Settings never offers it.
  (A phone whose system language is that language still gets it.)
- **Phantom:** the list names a language the app has no translation for, so Settings offers it
  and the user gets the app's default language.

How often does a hand-written list disagree with the translations shipped next to it in open-source
Android apps?

## What is already known (disclosed before reading)

- This census's [locale-mismatch](../locale-mismatch/RESULTS.md) study (2026-11-06) found
  translation folders named with country codes (`values-ua`, `values-cz`). Its correction of
  2026-11-07 notes that one of them, Exodus, generates its locale config, so `cn` may appear in
  its per-app list. That correction is what led to this study. Nothing in this census has counted
  locale configs before (checked: no mention of `localeConfig` or `locales_config` in the census
  README).
- A search on 2026-11-07 found no published count of locale-config drift and no lint check that
  compares a hand-written list with the resource folders. Android's own answer to drift is
  `generateLocaleConfig`. Projects do fix drift by hand (for example Organic Maps PR #13882,
  "Regenerate locales_config.xml and add missing languages"), and some apps have translations but
  no list at all (Shuttle2 issue #997).
- We have not looked at any repository's locale config for this study, apart from the four apps
  in the locale-mismatch correction (none of the three checked by hand has a list; Exodus
  generates one).

## Corpus and method

- Repositories: `hidden-chars/repos.txt` in this census (4,693 F-Droid source repositories, the
  corpus of every census run since hidden-chars), at HEAD of each default branch on the day of
  the run. Each is cloned shallow and blob-less; the full file list is read with `git ls-tree`,
  then a sparse checkout fetches `**/AndroidManifest.xml`, `**/build.gradle`,
  `**/build.gradle.kts`, `**/res/xml/*.xml`, `**/resources.properties` and `**/res/values*/*.xml`.
  Folders named `test`, `androidTest`, `testFixtures` or `sharedTest` are ignored.
- **Module:** the part of a path before its last `src` folder (`app/src/main/res` belongs to
  `app`), or the parent folder if there is no `src` folder.
- **Translation folder:** a `values-<locale>` folder next to a `values` folder in a folder named
  `res`, whose name Android reads as a locale (same rule as locale-mismatch: not `en-rXA`,
  `ar-rXB` or `values-car`), with at least one **translated item**: a `<string>`, `<plurals>` or
  `<string-array>` with non-empty text, in a file that also exists in `values`, whose name is an
  item of that default file not marked `translatable="false"`. A folder's language is its
  language subtag, with `iw`, `in`, `ji` read as `he`, `id`, `yi`.
- **Hand-written list:** a manifest with `android:localeConfig="@xml/<name>"` (XML comments
  ignored). Its file is `res/xml/<name>.xml` in the same module if there is one, else the first
  such file in the repository (sorted by path). Status: `missing` (no such file in the repository,
  for example written at build time), `parse-failed` (not XML or not `<locale-config>`), `empty`
  (no `<locale>` entries) or `ok`. A list's languages are the language subtags of its
  `android:name` values (`en-US` gives `en`, `zh-Hans-CN` gives `zh`).
- **Regenerated:** the list's file name (for example `locales_config`) appears in any
  `build.gradle(.kts)` of the repository. Such a list may be rewritten at build time, so it is not
  evaluated.
- **Default language:** `unqualifiedResLocale` in the module's `res/resources.properties` if there
  is one, else English. The default language is never a phantom or an orphan.
- **Phantom language:** in the list, with no translation folder of that language anywhere in the
  repository.
- **Orphan language:** not in the list, with translation folders in the declaring module whose
  best folder (summing its translated items over the module's `res` folders) holds at least half
  of the module's translatable default items. Below half, it is a **weak orphan**: reported, but
  not drift, since a project may leave out a language on purpose until it is mostly translated.
- A list is **evaluable** if its status is `ok` or `empty` and it is not regenerated. It
  **drifts** if it is evaluable and has at least one phantom or orphan language.
- Generated lists (`generateLocaleConfig = true` in a `build.gradle(.kts)`, line comments
  ignored) are counted but not graded.

## Predictions

Gate: at least 4,000 repositories read (cloned and scanned, with or without translations).
Otherwise every prediction is NOT TESTABLE. All counts are repositories.

- **C1.** At least **100** repositories have a hand-written list whose file is in the repository
  (status `ok`, `empty` or `parse-failed`).
- **C2.** At least **a quarter** of the repositories with an evaluable list have a list that
  drifts. NOT TESTABLE if fewer than 20 repositories have an evaluable list.
- **C3.** Among those repositories, more have an orphan language than have a phantom language
  (strictly more). NOT TESTABLE on the same condition as C2.
- **C4 (precision, hand check).** Sample: for each drifting repository, its drifting list with the
  lowest SHA-256 of `locale-config v1|<repo>|<manifest path>`; then the first 16 of those by the
  same key. If the sample has fewer than 8 rows, C4 is NOT TESTABLE. C4 holds if at least 3/4 of
  the sample is labelled `real` (other labels stay in the denominator).

C1 to C3 are graded by the job (`summary.json`, integers only). C4 is graded by hand.

Our honest guesses before reading: a few hundred hand-written lists, drift in roughly 30 to 50% of
them, and mostly orphans (translations from Weblate or Crowdin arrive without anyone editing the
list). We are not confident about any of these.

### Hand labels for C4

For each sample row, at the recorded commit:

- `real`: each reported phantom language has no translation of that language the app ships
  (also checking other source sets and modules), or each reported orphan language has a
  translation the app ships that the list leaves out; and no script in the repository rewrites
  the list (searched for its file name). If a row reports several languages, one confirmed
  language is enough, and the note lists the others that did not hold.
- `not-real`: none of the reported languages holds up (for example the translation lives in a
  folder or format the method doesn't read, or a script rewrites the list).
- `other`: can't tell.

The labels are made by AI agents working in MV2's name and published with a note per row.
Borderline rows are marked, and the verdict is also reported with every borderline label flipped.

## Controls

- Built-in control (the job stops with exit 6 if it fails): a synthetic repository with one
  hand-written list must give exactly one phantom (`fr`), one orphan (`uk`, 75% translated), one
  weak orphan (`ko`, 25%), a test folder and an empty translation ignored, a commented-out
  `generateLocaleConfig` ignored and a real one found, and the bad code `ua` reported.
- Self-test: NewPipe and the F-Droid client must be read with at least 10 translation folders
  (exit 3 otherwise).

## Exploratory (not graded)

Generated lists, and how many of them come with a not-a-language folder (`values-ua`) that the
generated list would offer; repositories with both a generated and a hand-written list;
repositories with 3 or more translation languages and no list at all; list statuses; regenerated
lists; which languages are most often phantoms, orphans and weak orphans; repositories with only
weak orphans.

## Limits

- Languages only: a list with `pt-BR` and a folder `values-pt-rPT` count as matching. Region and
  script mismatches are not counted.
- Translations that live outside the repository (a library's own translations, files downloaded at
  build time) or in formats other than Android XML are not seen; such a language can look like a
  phantom. The hand check looks for these.
- Orphans are counted only in the module that declares the list. Apps whose strings live in other
  modules may have orphans this misses (a lower bound).
- A script outside Gradle (Python, shell) that rewrites the list is not detected by the method;
  the hand check looks for one.
- Product flavors and build types are merged by module; a list declared only for one flavor is
  compared with all of the module's folders.
- One commit per repository (HEAD on the run day); F-Droid apps only.

## What happens after

RESULTS.md with the verdicts unchanged, `lists.csv` (every hand-written list), `sample.csv` with
labels, `repos.jsonl` and `summary.json`, all checked for personal data before publishing. If C2
and C4 hold, l10n-guard gets a check that compares a locale config with the translation folders.
Real cases go on MV2's paced list of upstream reports (at most one outward action a day, only where
a project's rules allow AI-assisted contributions, each saying it was made with AI agents).
