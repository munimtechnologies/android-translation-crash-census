# census-unformatted 0.1.0: results

Made by MV2 of Munim, Inc. with AI agents. Code Apache-2.0; data and text CC BY 4.0.

Census 0.4.0 and Android Lint skip strings whose default text is marked `formatted="false"`, but aapt2
compiles them the same way, so any that the code formats still go through `java.util.Formatter`. This run
checked their translations. Predictions were published before the run: [PREDICTIONS.md](PREDICTIONS.md).

- Run: sealed container job `census-unformatted-v1`, 2026-10-17 01:09-01:23Z, census 0.4.0 at
  `7d7ee70`, OpenJDK 21.0.12.1, all 4,476 F-Droid repositories reached. Tests passed.
- 3,564 string names are marked `formatted="false"` in 137 repositories. 192 of them have a printf
  placeholder and translations, in 49 repositories: 1,394 translations checked.
- JVM verdicts: 1,384 fine, 6 crash, 4 crash only if text reaches a `%d`.
- Files: [findings.csv](findings.csv) (the 10 flagged rows), [report.md](report.md),
  [summary.json](summary.json), [unformatted.json](unformatted.json).

## Predictions

- Known answer (Helsinki Timetables zh `header_times` must come out as crash): **HELD**.
- P1, at least 2,000 translations checked: **FAILED** (1,394). The blind spot is smaller than guessed.
- P2, crash rate at least twice census 0.4.0's 28.4 per 100,000: **HELD** (430 per 100,000), but on 6 rows
  from 2 repositories, so the rate means little.
- P3, at least one crash in a string the code formats, outside Helsinki Timetables: **FAILED** (0).

## Every flagged row, read by hand

| app | locale | key | JVM | what the code does | verdict |
|---|---|---|---|---|---|
| Red Moon | ar, ml | pref_summary_schedule_custom | crash | not named in any Kotlin/Java file | no crash |
| Red Moon | ar, ml | pref_summary_schedule_sun | crash | not named in any Kotlin/Java file | no crash |
| Helsinki Timetables | zh | header_times, header_stations | crash | already in the referenced-crash audit | known |
| SpeakThat! | ko, tr | app_filter_found_matches | crash-if-text | see below | caught, wrong result |
| SpeakThat! | ko, tr | log_app_filter_found_matches | crash-if-text | not formatted in code | no crash |

- **Red Moon**: `%on` and `%off` are the app's own tokens, not printf placeholders; the Arabic and
  Malayalam translators translated the token words (`%تشغيل`, `%ഓൺ`). A code search of LibreShift/red-moon
  (Sourcegraph, commit d4d1c44) finds both strings only in XML, so nothing formats or fills them today.
- **SpeakThat!** (commit 1af2d9a): the Korean and Turkish translations move `'%s'` before `%d` without
  numbers. `AppAutoCompleteAdapter.AppFilter.performFiltering` calls
  `String.format(context.getString(R.string.app_filter_found_matches), suggestions.size(), filterText)`
  with `filterText` a String, so in those languages it throws IllegalFormatConversionException on every
  non-empty filter. It does not crash the app: Android's `Filter` catches any exception from
  `performFiltering`, logs a warning and publishes an empty result, so the suggestion list would come up
  empty. A code search finds no other file that names `AppAutoCompleteAdapter`, so the adapter appears unused
  at this commit, and no user is affected today.

## What this adds

- A measured size for the `formatted="false"` blind spot in open-source Android apps: 1,394 translations in
  49 repositories, a small slice of what census 0.4.0 checks. Its crash rate per translation is high, but every crash in
  it is in a string nothing formats, or is already known.
- A new way a format crash is hidden, for the census's list of misses: `Filter.performFiltering` swallows the
  exception and turns it into an empty result, so a broken translation there shows as "no matches" rather
  than as a crash.
- Census 0.4.1 will include these strings in the main run, as planned, since they cost little.

## Limits

- Code use comes from name matching and a Sourcegraph search; strings looked up by name at runtime would be
  missed.
- Only the latest commit of each repository's default branch is read. Nothing was run on a device.
