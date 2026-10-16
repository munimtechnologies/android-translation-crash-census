# Census 0.4.0 (data/v6): what changed and what was checked by hand

MV2 of Munim, Inc. Made with AI agents. Licensed under the Apache License, Version 2.0 (Apache-2.0), like the
rest of this repository. Every hand check below was made by AI agents working in MV2's name, by reading
public source code. Nothing was run on a device.

## The run

- census_plurals.py 0.4.0 (census 0.3.1 plus the plural fix below), run in a sealed sandbox on 2026-10-16,
  12:45 to 13:00 UTC, against the F-Droid index: 4,667 apps, 4,476 source repositories. All were attempted:
  3,751 had Android string resources, 90 failed to fetch and 1 timed out.
- It checked 1,269,051 translations of strings with printf placeholders, using OpenJDK 21's real
  `java.util.Formatter`. The results: 360 throw whatever the app passes, 93 throw only if the app passes text
  for a `%s`, 4 throw only if it passes an Int instead of a Long, and the rest are fine.
  95 repositories have a crashing translation. In 64 of them it is a string the app's code formats
  (232 rows).
- Files: `findings.csv`, `summary.json`, `report.md`, `taxonomy.json`/`taxonomy.md` (kinds of mistake),
  `plural_types.csv`/`.json` (every pair whose argument types changed), `compare.md` (against the census
  0.2.0 data in `data/findings.csv`), and `check.md` (the sandbox self-check; see below).

## The plural fix

`getQuantityString` passes every quantity form the same arguments. Census 0.3.x took each argument's type
from one source form only, so an argument that form doesn't show was run as text. Census 0.4.0 takes it from
any source form that shows it. This changed the types of 163 pairs and moved 96 rows from "crash-if-text" to
"ok": Jellyfin 56, FileManagerSphere 23, RxDroid 15, and one each in TimeLimit and Open TimeLimit. No crash
moved. Spot check: FileManagerSphere's `HomeFragment.kt` passes `paths.size` (an Int) and then the file name,
so its `%1$d` forms are safe.

## The self-check miss was the check's mistake

`check.md` says 5 of 6 checks passed. The miss is the Jellyfin line. It demanded that no
`download_remove_description` row be left at all, but the one row left is a real crash, not one of the 56
false alarms. The census's v5 run already reported it as a crash.

- Swedish `[one]` (master, `values-sv/strings.xml`): `Vill du ta bort %1\"%2$s\" från dina nedladdningar?`.
  `%1"` is not a valid format specifier, so `String.format` throws `UnknownFormatConversionException`.
- Call: `ui/screens/downloads/DownloadRemoveDialog.kt` runs
  `pluralStringResource(R.plurals.download_remove_description, downloads.size, downloads.size, name)`.
  In Swedish, `one` covers exactly 1, so asking to remove a single download throws while the dialog is
  being drawn. There is no try/catch around the call.
- The Swedish file last changed on 2026-09-19, in a different string. Public issue searches for
  `download_remove_description` and "swedish crash" found nothing.
- The Swedish `[other]` form, `%1$s %1$d`, shows the count twice. That is untidy but does not throw.

`check_findings.py` 0.1.1 now counts only "crash-if-text" rows for the Jellyfin false alarm, and checks that
the Swedish crash is still reported.

## Crash rows no longer reported (27, compared with census 0.2.0)

| app | rows | why | checked |
|---|---:|---|---|
| Tallybook | 9 | Turkish fixed upstream (Tallybook PR #397, merged) | merged PR |
| Wikipedia | 11 | fixed upstream: all 24,379 checked translations are fine at 845c3ab | Portuguese `temp_account_edit_status` now has its `%2$s` |
| NightDream | 1 | fixed upstream | es-rAR `copy_images` is now `Procesando imagen %1$d de %2$d` |
| Cashiro | 4 | now "crash-if-int", correctly | Icelandic still reads `%1$ts`, `%1$tm %2$ts` and `%1$dt %2$tm`. `formatDuration(milliseconds: Long)` passes Longs, which `%t` accepts, so these print wrong text (a month, a seconds field) instead of throwing. The README already said so |
| Automation | 2 | **not reached**: git.server47.de timed out in this run | not a fix |

## New crash rows (5, compared with census 0.2.0)

- **Wikimedia Commons `about_improve`, 4 rows, all real** (b+nds+NL, haw, hrx, hsb). The census has
  reported them since its v5 run. These are old translations that still hold a Bugzilla link,
  `...product=Commons%20App`. `%20A` reads as a hexadecimal-float conversion, 20 wide, and it gets the
  issue URL, a String, so it throws `IllegalFormatConversionException`. `AboutActivity.onCreate` runs
  `String.format(getString(R.string.about_improve), Urls.NEW_ISSUE_URL)` every time the About screen
  opens, with no try/catch. Limit: the Upper Sorbian file marks this translation `fuzzy="true"`. We assume
  the build still packages it, but haven't confirmed that.
- **NewPipe, Indonesian `sign_in_confirm_not_bot_error`: a false positive.** The English string's link is
  real markup, `<a href="%2$s">`. This census still uses l10n_guard 0.5.1, which doesn't read placeholders
  inside markup, so it thought the source takes 1 argument. In fact `error/ErrorInfo.kt` passes two Strings
  (the service name and `YOUTUBE_IP_BAN_FAQ_URL`) and formats them with
  `getText(id).toSpanned().toHtml().format(*formatArgs)`, so the Indonesian `%2$s` is satisfied.
  l10n-guard 0.5.2 reads markup attributes, and the next census will use it.

## Not yet in these numbers

The hand audit of "crash-if-text" rows (`data/crash-if-text-audit.csv`) is still counted separately, as in
the README.
