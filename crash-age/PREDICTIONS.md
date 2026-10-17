# crash_age 0.1.0 predictions: how old are crashing translations, and how did they arrive?

MV2 of Munim, Inc. Made with AI agents. Written 2026-10-17, before crash_age.py was first run.
Licence: this text CC BY 4.0; crash_age.py, fetch_code.py and the tests Apache-2.0.

## Question

The census's 2026-10-17 read ([callsites/findings.csv](../callsites/findings.csv)) lists 360
translations in open-source Android apps that make `String.format` throw ("crash") and 93 that
throw when the app passes text ("crash-if-text"). Nobody seems to have measured how long such
translations sit in a repository, or how they get there. A search on 2026-10-17 found work on
i18n layout bugs in Android GUIs (Escobar-Velasquez et al., ICSME 2020) and on Android crash
bugs in general, but no count of the age or arrival path of format-crashing translations, and
no count of how often a fixed one comes back.

## Method

For each row, [crash_age.py](crash_age.py) clones the repository with full history but no file
contents, walks the first-parent history of the commit the census read for the row's
strings.xml, downloads every version of that file, and parses each with the census's own
`l10n_guard.parse_android` and `_android_text`. It finds the commit from which the exact
flagged text has been there without a break (its **age** is counted to 2026-10-17 05:13 UTC),
classes that commit's **pipeline** (Weblate, Crowdin, Transifex, translatewiki.net and other
platforms by author, committer and subject, or by the merged commits for a merge; "other bot";
or "direct"), counts the separate **episodes** the text has been in the file, and notes what
the key held before (**new**, **replaced**, or **file start**). A row whose run starts at the
file's first version at that path (or at the 3,000-version cap) is a **lower bound**: its true
age may be greater. "Dated" below means dated exactly or as a lower bound. No names or email
addresses are recorded, only commit hashes and pipeline classes.

## Predictions (on the "crash" rows)

- **A1.** The median age of dated crash rows is at least 365 days.
- **A2.** At least half of dated crash rows arrived through a translation platform's commit.
- **A3.** Weblate is the most common pipeline, ahead of direct commits and every other
  platform.
- **A4.** At least 5% of dated crash rows were gone at some point and came back (two or more
  episodes).
- **A5.** At least 80% of crash rows are dated (the job can find and date them).
- **A6.** The median age of dated crash rows the census calls "formatted" (a call site that
  formats the string was found) is at least 180 days.

The crash-if-text rows are summarised the same way but not scored.

## Known limits, stated before the run

- Rows cluster by repository: one platform sync can bring many crashing strings at once. The
  output reports per-repository medians too.
- Renamed or moved files restart their history at the new path (`--no-renames`), so their rows
  are lower bounds.
- A merge's pipeline is read from the merged commits that touch the file; a maintainer who
  downloads translations from a platform and commits them by hand counts as "direct" unless the
  commit names the platform.
- "Came back" means the exact text was absent from at least one readable version and present
  again later. It does not say why (a revert, a platform sync over a fix, or the same mistake
  made twice).
- The job refuses to run until this file is on main.
