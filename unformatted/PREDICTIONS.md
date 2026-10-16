# Predictions for census-unformatted 0.1.0 (written 2026-10-16, before the run)

Made by MV2 of Munim, Inc. with AI agents.

## Question

Census 0.4.0 skips every string whose default (`values/`) text is marked `formatted="false"`.
aapt2 reads that attribute only to skip its "multiple substitutions specified in non-positional
format" check, and the compiled text is the same, so an app that passes the string arguments still
runs it through `java.util.Formatter`. Android Lint's format checks skip these strings too. How
many translations of such strings throw?

The one case known before the run: Helsinki Timetables' Chinese `header_times`
(`%時刻表，站名%`; the English is `Route "%s" / Station "%s"`, marked `formatted="false"`),
which `StationsListOfTrips.getHeaderNextScreen` formats with `String.format`. It was found by
hand on 2026-10-16. The run must report it as `crash`, or the run is not trusted.

## Predictions

- **P1.** At least 2,000 translations of `formatted="false"` strings are checked.
- **P2.** Their `crash` rate is at least twice census 0.4.0's (360 in 1,269,051, or 28.4 per
  100,000), so at least 56.7 per 100,000. Reason for the guess: authors mark a string
  `formatted="false"` mostly because it has several unnumbered placeholders, and translators break
  those more often.
- **P3.** At least one `crash` row is in a string the code formats (`use` = `formatted`), outside
  Helsinki Timetables.

## What happens next

Every `crash` row is read by hand before anything is claimed. The census's code-use labels miss
some formatting (see `data/referenced-crash-audit.md`), so `referenced` rows are read too. Rows
in strings the code never formats are not crashes, whatever the JVM says.
