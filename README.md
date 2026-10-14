# Android translation-crash census

How many open-source Android apps ship translations that make `String.format` throw? This repository has the tool that measures it across every app on F-Droid, its tests, and the results so far. Made by MV2 of Munim, Inc. with AI agents. Code: Apache-2.0. Data and write-up: CC BY 4.0.

## Why a translation can crash an app

`getString(R.string.x, arg)`, `getQuantityString(...)` and `String.format(getString(...), ...)` hand the translation for the user's language to `java.util.Formatter`. A translator who types `%1$` instead of `%1$s`, `% s`, `%$1s`, or a bare `100%` makes the format string invalid, and the call throws (`UnknownFormatConversionException`, `FormatFlagsConversionMismatchException`, `MissingFormatArgumentException`...). This only happens for people using that language, so developers rarely see it. Wikimedia Commons alone has fixed this crash several times, one string at a time (commons-app/apps-android-commons #4877 Bengali, #4653 Burmese, #2330 Japanese).

## Method

1. Read F-Droid's index (`index-v2.json`): 4,667 apps in 4,476 distinct source repositories.
2. For each repository, make a depth-1, blobless, sparse clone of the latest commit and check out only `res/values*/*.xml`.
3. Pair every translation with its default (`values/`) string when the default text has a printf specifier and isn't marked `formatted="false"`. Plural forms are checked against the source form that reads the most arguments, because `getQuantityString` passes the same arguments to every quantity.
4. Give each pair two verdicts:
   - **static**: the `java-format` check of [l10n-guard](https://github.com/munimtechnologies/l10n-guard) (vendored here as `l10n_guard.py`, 0.5.1);
   - **JVM**: the real OpenJDK 21 `java.util.Formatter` (`FormatCheck.java`), formatting the source and the translation with arguments of the source's types. A `%s` argument gets text once and a number once. `crash` means the translation throws either way. `crash-if-text` means it throws only when the app passes text. A pair whose source string throws too is set aside.
5. **Code use** (from 0.2.0): repositories with a flagged translation also get their `.kt` and `.java` files checked out. Each flagged string is then classified as `formatted` (a `getString`/`stringResource`/`getQuantityString`/`pluralStringResource` call passes it arguments, or it is wrapped in `String.format(...)`/`.format(...)`), `referenced` (used only in other ways), `unreferenced`, or `unknown`. The headline count is JVM crashes in `formatted` strings, because only those are reachable.
6. Write `apps.jsonl` (one line per repository), `findings.csv` (every crash with a link to the file at the commit read), `summary.json` and `report.md`.

The census reads public files only. It files nothing and contacts no one.

## Results so far

### First pass (census 0.1.0, partial)

The first run stopped after 1,523 of the 4,476 repositories. An emoji written as two `\u` escapes broke the hand-off to the JVM; 0.2.0 fixes that. Its summary and report are in [`data/v1-partial/`](data/v1-partial/).

- 1,273 repositories had Android string resources, and 714 had translations of strings the app formats.
- 810,419 translated format strings were checked. The JVM rejected 253 whatever the app passes, and 61 more only when the app passes text.
- Those 253 crashes were in 39 repositories, all updated within the last year.
- Static check vs JVM: l10n-guard flagged 252 of the 253 JVM crashes and never flagged a translation the JVM accepted (precision 1.0, recall 0.996).

Checking these rows by hand turned up two false-positive classes, both fixed in 0.2.0:

- **Plurals.** 58 of the 72 `MissingFormatArgumentException` rows were plural forms that legitimately use arguments only the English `other` form shows (KDE Connect, Zorin Connect, SchildiChat). 0.1.0 compared each form only with the same English form.
- **Strings no code uses.** 18 of Tella's 19 crashes belong to one string that no Kotlin or Java file names. A crash there can't happen, which is why 0.2.0 classifies code use. Wire's Russian `%@` in `meeting_repeating_years` is another: no code formats that plural.

So the 253 is an upper bound. The real first-pass count of reachable crashes is lower.

### Hand-verified cases (2026-10-14)

Each was checked against the project's current default branch, and the call that formats the string was read by hand. None was reproduced on a device. The same list is in [`data/verified-cases.csv`](data/verified-cases.csv).

| App | Broken translations | Where the code formats them | Translation route and report |
|---|---|---|---|
| ownCloud Android | Uyghur: 55 strings with `% 1 $ s`, `% s`, `% @`; Swedish: 1 (`%1$ musikspelare`) | `FileListAdapter` (file-list footer), `DrawerActivity` (storage quota) | Transifex; issue drafted, filing queued |
| Wikimedia Commons | 22 translations of 13 strings in Bengali, Central Kurdish, Georgian, Mingrelian, Polish, Afrikaans, Arabic, Chinese, Burmese, Thai, Indonesian, Tulu and Slovenian (`%1$`, `%1`, `s$%1`, `%$1s`, `%1$ so`) | `UploadWorker` (upload started / finishing / done / failed / paused notifications), search empty states, `DeleteHelper`, `QuizResultActivity`, `WikidataEditService`, `CategoryEditHelper` | translatewiki.net; issue drafted, filing queued |
| Tallybook | Turkish: 9 strings with `% s` | `ImportExportActivity` and `BackupListActivity` error dialogs | pull requests welcome; fix PR queued |
| Mastodon (official Android app) | Indonesian `x_new_notifications` (`%,d` written twice, so it reads a second argument); Albanian `x_people_talking` one and other (`%1`); Belarusian `x_quotes` one (`%,d% цытата`) | `PushNotificationReceiver.doNotify` builds the grouped summary on a background thread with no catch, whenever an account has 2 or more notifications (Indonesian has only the `other` form, so every count is affected); `TrendingHashtagsFragment` and `HashtagStatusDisplayItem` (Albanian); `StatusQuotesFragment` and `ExtendedFooterStatusDisplayItem` (Belarusian) | Crowdin. Mastodon's AI contribution policy says its repositories are for humans only and turns away issues that come from running AI tools over the code, so MV2 has not reported it there. It is listed here for Mastodon's translators. |
| Homer Audio Player 2 | Chinese (Simplified): both battery content descriptions end in a bare `%` (`电量 %1$d %`) | `BatteryIcon` via `pluralStringResource`, drawn in the player screen's top row when **Show battery indicator** is on (off by default) | Lokalise; issue queued |
| Shader Editor | Russian: `few` and `many` forms of `n_shaders_successfully_imported` read `%2$d`, which only the `_m_failed` plural gets | `ImportExportAsFiles.importFromDirectory` (Android 9 and older; only `IOException` is caught) | translations in the repo; fix PR queued |
| AnkiDroid | Croatian: `pref_milliseconds` is `% ms` | `SliderPreference` runs `String.format(displayFormat, value)`, and the accessibility settings use this string as `app:displayFormat` | Crowdin. AnkiDroid's contributing guide bars new contributors from using AI tools, so MV2 has not reported it there. |

Two of the seven projects (Mastodon and AnkiDroid) don't accept reports or fixes made with AI tools from new contributors. A census like this one can still help them, because their translators and maintainers can find the rows here and in the full results.

### Full pass (census 0.2.0)

The full run, with code-use classification, is queued on MV2's shared compute runner. Its `summary.json`, `findings.csv` and `report.md` will be added under `data/`.

## Run it

Needs Python 3.10+, git and a JDK (`javac` and `java`). Without a JDK the census runs the static check only.

```sh
python bootstrap.py --data-dir cache      # apt-get git + JDK, or Temurin 21 under cache/jdk
python census.py --data-dir cache --out-dir out --workers 12 --budget-minutes 140
python census.py --local path/to/android-app --out-dir out   # one checkout, no git
python test_census.py
```

## Prior art

- **Android Lint** (`StringFormatInvalid`, `StringFormatMatches`) checks format strings within a project. It runs only where a project runs lint, and translations from a translation platform often arrive after the lint step that matters.
- **Weblate** has a "Java format" check (`java-printf-format`) that catches these. Its documentation lists Android string resources among the formats that turn it on automatically. By default a failing check warns rather than blocks, unless a component enforces it. Crowdin, Transifex and Lokalise have their own placeholder checks. Even so, the verified cases above include translations that came through Crowdin, Transifex, translatewiki.net and Lokalise.
- **translate-toolkit / pofilter** has printf checks for gettext-style files.
- Many single-project reports and fixes exist: Commons #4877/#4653, Firefox for Android (fenix) #1580 (German, `Conversion = '@'`), ConnectBot #2478 (Arabic, trailing `%`), OsmAnd #26194, NuvioTV #3697.
- Research: Escobar-Velásquez et al., "An Empirical Study of i18n Collateral Changes and Bugs in GUIs of Android apps" (ICSME 2020), studies layout and GUI damage from translation, not format strings. Fan et al., "Large-Scale Analysis of Framework-Specific Exceptions in Android Apps" (ICSE 2018, arXiv:1801.07009), studies crashes from collected exception traces, not translation files.

Searches of GitHub, arXiv and the web (2026-10-13 and 2026-10-14) found no cross-project measurement of how often shipped Android translations crash `java.util.Formatter`. None found checks static verdicts against a real JVM, or checks which crashing strings the code actually formats. That is what's new here.

## Limits

- A string counts as formatted when its default text has a printf specifier. Code-use classification is pattern-based. Strings looked up by name at runtime, or formatted in ways the patterns miss, count as `referenced` or `unreferenced`.
- Verdicts come from OpenJDK 21. Android's `java.util.Formatter` is the same OpenJDK code for these cases, but edge cases can differ by API level.
- Only the latest commit of each repository's default branch is read. A translation may already be fixed on its translation platform but not yet exported.
- Apps whose source isn't a reachable public git repository, or that keep strings outside `res/values*/`, aren't covered.

## Licence

- Code (`census.py`, `FormatCheck.java`, `bootstrap.py`, `test_census.py`, and the vendored `l10n_guard.py`): Apache-2.0 (see `LICENSE`).
- Data under `data/` and this write-up: CC BY 4.0. The translated strings quoted belong to their projects, under those projects' licences.

Made by MV2 of Munim, Inc. with AI agents. Contact: munimversion2@gmail.com.
