# Android translation-crash census

How many open-source Android apps ship translations that make `String.format` throw? This repository has the tool that measures it across every app on F-Droid, its tests, and the results. Made by MV2 of Munim, Inc. with AI agents. Code: Apache-2.0. Data and write-up: CC BY 4.0.

## Why a translation can crash an app

`getString(R.string.x, arg)`, `getQuantityString(...)` and `String.format(getString(...), ...)` hand the translation for the user's language to `java.util.Formatter`. A translator who types `%1$` instead of `%1$s`, `% s`, `%$1s`, or a bare `100%` makes the format string invalid, and the call throws (`UnknownFormatConversionException`, `FormatFlagsConversionMismatchException`, `MissingFormatArgumentException`...). This only happens for people using that language, so developers rarely see it. Wikimedia Commons alone has fixed this crash several times, one string at a time (commons-app/apps-android-commons #4877 Bengali, #4653 Burmese, #2330 Japanese).

## Latest run (census 0.4.0, 2026-10-16)

Census 0.4.0 read the whole F-Droid index again on 2026-10-16, with the plural fix described in [`data/v6/NOTES.md`](data/v6/NOTES.md). Its files are in [`data/v6/`](data/v6/). The sections after this one describe the first full pass (census 0.2.0) and the corrections found by reading its rows by hand; the numbers here already include those corrections.

- 4,476 source repositories attempted: 3,751 have Android string resources, 90 failed to fetch and 1 timed out.
- 1,269,051 translations of strings with printf placeholders were formatted with OpenJDK 21's real `java.util.Formatter`.
- **360 translations, in 95 repositories, throw whatever the app passes. 232 of them, in 64 repositories, are strings the app's code formats with arguments**: the reachable crashes.
- 93 more throw only if the app passes text where the translation has a number (`crash-if-text`), and 4 only if it passes an `Int` instead of a `Long` (Cashiro's Icelandic `%t` durations, which print the wrong text with the `Long` the app passes).
- A hand audit of the `crash-if-text` rows ([`data/crash-if-text-audit.md`](data/crash-if-text-audit.md)) found 58 that really throw, in 21 repositories. A second audit, of the 40 `crash` rows in strings the code only references ([`data/referenced-crash-audit.md`](data/referenced-crash-audit.md)), found 25 reachable crashes in 17 repositories that the census's call patterns miss, because the app formats the string through a helper or in a second step (AdAway, MoneyWallet, SmartCookieWeb, Petals, Retro Music and its fork Metro, NewPipe and its fork LearnTube, HeartBeat, Wikimedia Commons, SecondScreen, RxDroid, Lavabit Encrypted Proxy, ownCloud, Helsinki Timetables, Habit-Maker, Suntimes Calendars). So the 232 is at least 257. They are not added to the numbers above.
- By exception: `UnknownFormatConversionException` 249, `MissingFormatArgumentException` 49, `FormatFlagsConversionMismatchException` 39, `IllegalFormatConversionException` 19, `IllegalFormatFlagsException` 4.
- By language: Uyghur 55 (one app), Turkish 18, Arabic 16, Russian 14, then Spanish, Italian, Basque and Greek with 10 each. Most reachable crashes: ownCloud 47, Wikimedia Commons 26, Cashiro 25, OsmAnd~ 12.
- Compared with census 0.2.0 ([`data/v6/compare.md`](data/v6/compare.md)): 27 crash rows are gone (Tallybook 9 and NightDream 1 fixed by their projects, Wikipedia 11 as in Correction 2 below, Cashiro 4 now `crash-if-int`, Automation 2 not reached because its server timed out) and 5 are new: 4 real Wikimedia Commons `about_improve` rows, and one false positive in NewPipe's Indonesian (a placeholder inside link markup, which the l10n-guard 0.5.1 used here can't see; the code only references that string, so it isn't one of the 232).
- The plural fix moved 96 `crash-if-text` rows to fine (Jellyfin 56, FileManagerSphere 23, RxDroid 15, TimeLimit and Open TimeLimit 1 each). No crash moved.
- l10n-guard 0.5.1's static check agreed with the JVM on 354 of the 360 crashes and called nothing an error that the JVM accepted (precision 1.0, recall 0.983).
- Crashes per 100,000 checked translations, by the translation platform a repository names: Weblate 25.6 (341 repositories), Crowdin 29.2 (170), Transifex 66.8 (63; most of its 65 crashes are ownCloud's Uyghur file), none named 22.2 (1,108). The platform is read from config files or the README, which doesn't prove every translation came through it, and one large file can dominate a platform's count, so these are not ratings of the platforms.

## First full pass (census 0.2.0, 2026-10-14)

Census 0.2.0 read the latest commit of every one of the 4,476 source repositories behind F-Droid's 4,667 apps, in 11 minutes on 4 cores. The files are in [`data/`](data/): [`summary.json`](data/summary.json), [`report.md`](data/report.md) and [`findings.csv`](data/findings.csv), which has every flagged translation with a link to the line at the commit read. The numbers below are what 0.2.0 measured. Two corrections found by hand follow, and the corrected totals are in bold there.

- 3,755 repositories have Android string resources. 1,703 of them have translations of strings with printf placeholders.
- 1,262,958 such translations were formatted with OpenJDK 21's real `java.util.Formatter`.
- 382 translations, in 99 repositories, throw whatever the app passes. 190 more throw only if the app passes text for a `%s`.
- 250 of the 382 are strings the app's Kotlin or Java code formats with arguments, in 67 repositories. Those are the reachable crashes. The other 132 are strings the code uses some other way (41) or never names (91).
- That is about 1 crash in every 3,300 formatted translations. It is concentrated: ownCloud (47 reachable, nearly all one Uyghur file), Cashiro (29) and Wikimedia Commons (22) hold 98 of the 250. Most of the other 64 repositories have one to four.
- By exception: `UnknownFormatConversionException` 251, `MissingFormatArgumentException` 59, `FormatFlagsConversionMismatchException` 48, `IllegalFormatConversionException` 20, `IllegalFormatFlagsException` 4.
- By language, Uyghur leads (55, one app), then Turkish 27, Arabic 16, Russian 15, and Spanish, Italian, Basque and Greek with 10 each.
- **Static check vs JVM:** l10n-guard 0.5.1 called 375 of the 382 JVM crashes errors and the other 7 warnings. It called nothing an error that the JVM accepted (precision 1.0, recall 0.98). Both read the same extracted text, so a text-extraction mistake fools both (see the Wikipedia correction below).
- **Maintainers confirm it.** Tallybook's maintainer reproduced the Turkish crash on an emulator, found that one of the strings crashes the Utility settings screen as soon as it opens (a bug present since 2019), and merged the fix ([PR #397](https://github.com/herrerad85/tallybook/pull/397)). ownCloud acknowledged its report ([#5018](https://github.com/owncloud/android/issues/5018)).

### Correction 1: `%t` and `Long`

The JVM check passes an `Integer` for each `%d` in the English string. 4 of the 250 reachable rows (Cashiro's Icelandic `duration_*` and one Vietnamese string) use a `%t` date conversion there. `%t` rejects an `Integer` but accepts a `Long`, and Cashiro passes a `Long`. So those 4 don't throw; they print a month or an AM/PM marker instead of a duration. No other row in the data depends on `Integer` vs `Long` in this direction. Census 0.3.0 tests both types and reports `crash-if-int` and `crash-if-long` separately.

### Correction 2: Wikipedia's 11 rows are not crashes (markup that is text)

Wikipedia's English `temp_account_edit_status` is written in CDATA: `<![CDATA[<b>You are using a temporary account.</b> Your edit will be attributed to %1$s. <a href="%2$s">Learn more</a>.]]>`. Markup inside CDATA (or written as `&lt;a href=...&gt;`) is plain text to Android, so the app gets the `<a href="%2$s">` as written, formats it with two arguments, and then runs it through `Html.fromHtml`. The code passes both (`getString(R.string.temp_account_edit_status, AccountUtil.getUserNameFromCookie(), getString(R.string.temp_accounts_help_url))` in `EditSummaryFragment` and `TalkReplyActivity`). l10n-guard 0.5.1 removed every `<...>` before checking, so the `%2$s` inside the `href` disappeared from the English string and the census thought it passed one argument. Most translations kept the link intact and were stripped the same way. A few have broken link markup that the stripping missed (Portuguese `<a href="%2$s2Saiba mais`, or a stray `<span class="notranslate">` inside the `href` in Romanian, Indonesian and Russian), so their `%2$s` looked like an extra argument. They show a broken link, but they don't throw. The same holds for two Danish Year in Review strings: in the English, `%3$s` and `%4$s` are link targets inside CDATA, and the English string itself needs them, so the code must pass them or it would throw for every English user. The five `values-qq` rows are translatewiki.net's notes for translators, not a language any device loads.

So all 11 Wikipedia rows (8 of them in formatted strings) are false positives. No other `crash` row in `findings.csv` has a placeholder inside literal markup. Rows whose English hides a placeholder in CDATA markup while the translation shows it as plain text wouldn't show up in that search, which is one reason for the full re-run. With both corrections:

- **371 translations, in 98 repositories, throw whatever the app passes.**
- **238 of them are reachable** (formatted by the code) in 66 repositories: 250, minus 4 for `%t`, minus 8 for Wikipedia.

Census 0.3.1 (`census_fixes.py`, on top of `census.py` 0.3.0) fixes the cause: only real child elements lose their markup, and literal markup keeps its placeholders, as on a device. It also skips `values-qq`. This works both ways. A translation that puts a placeholder the English never passes inside a literal link (`<a href="%3$s">` where the English has `%2$s`) is now caught. 0.5.1 removed it and missed it. Its full run is queued, and it will report every row that appears or disappears (`compare.py`). l10n-guard 0.5.2 carries the same text fix.

### Correction in the other direction: `crash-if-text` rows can be real

The 190 `crash-if-text` rows aren't counted above, because whether they throw depends on what the app passes. Reading code shows some do throw. FadCam's Italian `faditor_export_info` is `%1$d segmenti • %2$s`, and the code passes the duration as a `String` for `%1$`, so it throws `IllegalFormatConversionException` every time an export starts. 238 is a floor in this sense.

A hand audit of these rows (2026-10-16, [`data/crash-if-text-audit.md`](data/crash-if-text-audit.md) and [`.csv`](data/crash-if-text-audit.csv)) read the call and the argument's declared type for the biggest clusters and the likeliest rows. **58 more rows in 21 repositories throw**: Session, Open Food Facts' Beauty/Products/Pet Food flavors, Tella, KeyMapper, PhoneTrack, Amaze File Manager, mako, SD Maid SE, AURdroid, EweSticker, YTDLnis, DashPay Wallet, VLC for Android, ownCloud, FileManagerSphere, LightNovelReader, FadCam, J2ME Loader, OpenKeychain, Lavabit Encrypted Proxy, and a Session fork. Two of those projects had already fixed the same kind of crash by hand once (Open Food Facts PR #3558 in 2020, SD Maid SE PR #2162 in 2026), and it came back. The audit also found the census's own false positive: 56 Jellyfin plural rows are safe, because the census compared them with the wrong English plural item. Neither change is added to the totals above by hand; the next census version will count them.

## Mistake types

`taxonomy.py` (0.1.1) names the mistake behind the first placeholder `Formatter` can't use in each crashing row. Run on [`data/findings.csv`](data/findings.csv), its output is in [`data/taxonomy.md`](data/taxonomy.md) and [`data/taxonomy.json`](data/taxonomy.json). The 250 reachable rows as 0.2.0 counted them (the 8 Wikipedia rows of Correction 2 are all "argument not passed", so that kind has 27 real rows in 14 repositories):

| Kind | Example | Rows | Repositories | Top languages |
|---|---|---:|---:|---|
| malformed index | `% 1 $ s`, `%$1s` | 50 | 5 | Uyghur 44 (ownCloud) |
| stray percent | `(%1$d%)`, `电量 %1$d %`, `d% مقالات` | 45 | 26 | Arabic 6, Chinese (Simplified) 3, Persian 3, Slovenian 3 |
| conversion missing | `%1$ musikspelare`, `Wideo (%1)` | 43 | 18 | Serbian 7, Albanian 4, Central Kurdish 4 |
| argument not passed | Russian `few` reads `%2$d` | 35 | 15 | Korean 6, Ukrainian 4, Russian 4 |
| flag mismatch | `Mesaj:% s` | 34 | 14 | Turkish 22 |
| conversion letter in another script | `%1$с`, `%1$دم`, `%1$δδ` | 26 | 6 | Russian 6, Bulgarian 5, Arabic 3, Punjabi 3, Ukrainian 3 |
| wrong type | `%g` or `%t` for `%d` | 10 | 5 | Icelandic 3, Vietnamese 3 (4 of the 10 are the `%t` rows above) |
| unknown Latin conversion | `%1$DH`, `%2$vs` | 7 | 4 | Occitan 2, Latin 2, Turkish 2 |

What the counts say:

- **A stray `%` is the most widespread mistake** (26 repositories), not the biggest cluster. The malformed index is almost all one Uyghur file.
- **Turkish `% s`** accounts for 22 of the 34 flag mismatches: a space between `%` and the letter makes `Formatter` read the space as a flag.
- **The conversion letter gets "translated"**: Russian `%1$с` (Cyrillic *es*), Bulgarian `%1$дмлн.`, Arabic `%1$دم` (*dal* for `d`), Greek `%1$δδ`. To a reader these look right. It is real but narrow: 26 reachable rows in 6 repositories. In 14 of them, the letter looks like or transliterates the Latin conversion letter (`с`/`s`, `д`/`d`, `δ`/`d`, `د`/`d`). The rest are mostly a unit letter typed where the conversion letter should be (`%1$ч` for hours), or a dropped letter right before a word (`%1$的`).

Two more patterns turned up when reading rows by hand. Neither has its own kind in `taxonomy.py`:

- **A percent sign the English avoided.** In the 0.2.0 data, 10 crashing rows in 4 repositories come from English strings that spell out "percent" so they need no `%%`, translated with a bare `%`: Flashy (6 languages), Homer Audio Player 2 (`电量 %1$d %` for "battery %1$d percent"), and Element X with its fork SchildiChat Next (Japanese `%1$d% パーセント` for "%1$d percents of total votes"). Flashy's English writes "plus an additional 25 percent of it", and six translations write `25%`. In French and Italian `25%.` throws at `%.`. In Galician and Portuguese `25% adicional` is read as `% a`, a valid hex-float conversion with a space flag, which then asks for a second argument the app never passes. Element X fixed the same string's Chinese translation after a crash report (#7596) and added a placeholder check to its Localazy sync script, but the script can't fail the sync (see the table below), so the Japanese one still ships.
- **Both plural forms pasted into one.** Korean has a single plural category (`other`). pretixSCAN's Korean `other` items hold the English singular and plural forms one after the other, each under a label (`단수형` "singular", `복수형` "plural"), so every item reads `%d` twice and `getQuantityString(id, n, n)` throws for every count. These plurals look like they came from a tool that showed the two English forms with labels, and the translator copied both into the one Korean field.

`patterns.py` (0.1.0) goes one step further and tags each crashing row with how the mistake got in, by comparing it with the English (a dropped escape, a letter in another script, a space typed into a placeholder, ...). Its output over the full data is pending.

## What the free checks can see

Three open-source checks could have looked at every one of these translations before it shipped: Weblate's Java format check (on by itself for Android strings on Weblate), translate-toolkit's `printf` test (`pofilter`), and Android Lint's `StringFormatDetector`. [`CHECKS.md`](CHECKS.md) reads all three at pinned commits, mirrors their rules (`weblate_blind.py`, `checks_blind.py`), and tests the mirrors on the hand-verified cases below. What that shows:

- **Weblate and pofilter pass every stray-percent row** whose real placeholders are intact (Flashy's `25%.` and `25% adicional`, Cashiro's `(%1$d%)`, Element X's `%1$d% パーセント`, Mastodon's `%,d% цытата`). Both only recognise a `%` that a conversion letter directly follows, so a `%` before a space, a period or the end of the string is not a placeholder to them, while it is exactly where `Formatter` throws. That is the census's most widespread mistake.
- **Lint sees those, but mostly as a side effect**: a stray `%` makes it classify the translation as "not a format string", so it reports an argument-count mismatch (`StringFormatCount`, a warning, with a misleading message). Only when the next word starts with a conversion letter (Flashy's Galician and Portuguese `25% adicional`) does Lint, like `Formatter`, read `% a` as a placeholder, and then it also raises a `StringFormatInvalid` error. Lint ignores a translation whose `%` is followed by a Latin letter it doesn't know (`%D`), and its detector visits `<string>` elements only, never `<plurals>`, so every plural row is outside its reach.
- **No single check sees all of the verified cases.** The union of the three does, except a literal `%` written before a digit (Turkish `%25`), which only pofilter catches, by accident.

Over the whole census (366 crashing translations once date conversions, rows that print wrong text instead of crashing, and a cleared repository are left out), Weblate's check flags 300, pofilter 322 and Lint 239. 24 pass both Weblate and pofilter, and 12 pass all three. 22 of the 24 are an extra lone `%`. The tables, and a rule that would catch those 22, are in [`CHECKS.md`](CHECKS.md); the rows are in [`data/checks-blind-rows.csv`](data/checks-blind-rows.csv).

## Earlier partial pass (census 0.1.0)

The first run stopped after 1,523 of the 4,476 repositories. An emoji written as two `\u` escapes broke the hand-off to the JVM; 0.2.0 fixes that. Its summary and report are in [`data/v1-partial/`](data/v1-partial/). Checking its rows by hand turned up two false-positive classes, both fixed in 0.2.0:

- **Plurals.** 58 of its 72 `MissingFormatArgumentException` rows were plural forms that legitimately use arguments only the English `other` form shows (KDE Connect, Zorin Connect, SchildiChat). 0.1.0 compared each form only with the same English form.
- **Strings no code uses.** 18 of Tella's 19 crashes belong to one string that no Kotlin or Java file names. A crash there can't happen, which is why 0.2.0 classifies code use. Wire's Russian `%@` in `meeting_repeating_years` is another: no code formats that plural.

## Hand-verified cases

Each was checked against the project's current default branch, and the call that formats the string was read by hand. MV2 reproduced none of them on a device (Tallybook's maintainer did, on an emulator). The same list is in [`data/verified-cases.csv`](data/verified-cases.csv). The `crash-if-text` audit above adds 58 more rows in 21 repositories; none of those has been reported yet.

| App | Broken translations | Where the code formats them | Translation route and report |
|---|---|---|---|
| ownCloud Android | Uyghur: 55 strings with `% 1 $ s`, `% s`, `% @`; Swedish: 1 (`%1$ musikspelare`) | `FileListAdapter` (file-list footer), `DrawerActivity` (storage quota) | Transifex; [issue #5018](https://github.com/owncloud/android/issues/5018), acknowledged ("We will fix it.") |
| Wikimedia Commons | 22 translations of 13 strings in Bengali, Central Kurdish, Georgian, Mingrelian, Polish, Afrikaans, Arabic, Chinese, Burmese, Thai, Indonesian, Tulu and Slovenian (`%1$`, `%1`, `s$%1`, `%$1s`, `%1$ so`) | `UploadWorker` (upload started / finishing / done / failed / paused notifications), search empty states, `DeleteHelper`, `QuizResultActivity`, `WikidataEditService`, `CategoryEditHelper` | translatewiki.net; issue filed 2026-10-15 while MV2's GitHub account was hidden, so the maintainers can't see it yet |
| Cashiro | 25 strings: the SMS-scan durations in Russian, Ukrainian, Bulgarian, Gujarati, Kannada, Punjabi, Hebrew, Turkish, Latin and Vietnamese (`%1$ч %2$м`, `%1$DH`, `%2$g`); percentages in Hungarian, Turkmen, Romanian (`(%1$d%)`). Plus 4 Icelandic/Vietnamese `%t` strings that print the wrong thing without throwing | `SmsParsingProgressDialog.formatDuration` (elapsed and remaining time while SMS messages are scanned), `AnalyticsCharts`, `ChatScreen` | Crowdin; [issue #189](https://github.com/ritesh-kanwar/Cashiro/issues/189) |
| Tallybook | Turkish: 9 strings with `% s` | `ImportExportActivity` and `BackupListActivity` error dialogs; the maintainer found one more path, the exchange-rate summary on the Utility settings screen | pull requests welcome; [fix PR #397](https://github.com/herrerad85/tallybook/pull/397), **merged 2026-10-14** after the maintainer reproduced the crash on an emulator |
| Stepsy | Arabic: 3 milestone labels (`%1$دم`, `%.1فم`, `%1$دألف`); Bulgarian: 2 (`%1$дмлн.`, `%1$дхил.`), the conversion letter typed in the target script | `GoalNotificationWorker.showMilestoneNotification` (the step-milestone notification title; added 2026-09-28) | translations in the repo; fix PR queued |
| FadCam | Italian: `delete_videos_log` (`%2$d` never passed), `export_eta_minutes`/`_hours` (`%2$` never passed), `faditor_export_info` (`%1$d` gets a String); Greek: `records_delete_header_eta_*` (`%1$δδ`) | `RecordsFragment.deleteSelectedVideos` (deleting selected videos, before deletion starts), `FaditorEditorActivity.showExportInfoOnScreen` and `FaditorMiniFragment.formatEta` (export), `RecordsFragment.buildDeletionEta` (deletion progress) | Hosted Weblate; [issue #360](https://github.com/anonfaded/FadCam/issues/360) |
| Flashy | French, Italian, Simplified Chinese, Galician, Portuguese, Brazilian Portuguese: `farnsworth_unit_length_explanation` ends with a bare `25%` (`25%.`, `25%。`, `25% adicional`) | `SettingsActivity.SettingsFragment`: tapping the Farnsworth unit length setting calls `getString(..., ditLength)`, with no catch | Hosted Weblate; [issue #384](https://github.com/Crazy-Marvin/Flashy/issues/384), filed 2026-10-15 while MV2's GitHub account was hidden. The one-character fix (`25%%`) was saved on Hosted Weblate on 2026-10-15 in all six languages and reaches the app with Weblate's next export |
| Element X | Japanese: `a11y_polls_percent_of_total` is `総投票数うち%1$d% パーセント` (the Chinese one crashed in [#7596](https://github.com/element-hq/element-x-android/issues/7596) and was fixed) | `PollAnswerView` builds a poll answer's content description with `pluralStringResource` whenever votes are shown and the answer has votes. `tools/localazy/checkForbiddenTerms.py` flags the string, but `downloadStrings.sh` runs it in `xargs` child shells, so the failure never reaches the parent and the sync prints "Success!" | Localazy; issue #7942 filed 2026-10-15 while MV2's GitHub account was hidden, so the maintainers can't see it yet. SchildiChat Next, a fork, ships the same string. |
| Mastodon (official Android app) | Indonesian `x_new_notifications` (`%,d` written twice, so it reads a second argument); Albanian `x_people_talking` one and other (`%1`); Belarusian `x_quotes` one (`%,d% цытата`) | `PushNotificationReceiver.doNotify` builds the grouped summary on a background thread with no catch, whenever an account has 2 or more notifications (Indonesian has only the `other` form, so every count is affected); `TrendingHashtagsFragment` and `HashtagStatusDisplayItem` (Albanian); `StatusQuotesFragment` and `ExtendedFooterStatusDisplayItem` (Belarusian) | Crowdin. Mastodon's AI contribution policy says its repositories are for humans only and turns away issues that come from running AI tools over the code, so MV2 has not reported it there. It is listed here for Mastodon's translators. |
| Homer Audio Player 2 | Chinese (Simplified): both battery content descriptions end in a bare `%` (`电量 %1$d %`) | `BatteryIcon` via `pluralStringResource`, drawn in the player screen's top row when **Show battery indicator** is on (off by default) | Lokalise; [issue #26](https://github.com/msimonides/homerplayer2/issues/26) |
| Shader Editor | Russian: `few` and `many` forms of `n_shaders_successfully_imported` read `%2$d`, which only the `_m_failed` plural gets | `ImportExportAsFiles.importFromDirectory` (Android 9 and older; only `IOException` is caught) | translations in the repo; [fix PR #294](https://github.com/markusfisch/ShaderEditor/pull/294) |
| AnkiDroid | Croatian: `pref_milliseconds` is `% ms` | `SliderPreference` runs `String.format(displayFormat, value)`, and the accessibility settings use this string as `app:displayFormat` | Crowdin. AnkiDroid's contributing guide bars new contributors from using AI tools, so MV2 has not reported it there. |
| LibreTube | Bengali `videoCount` (`%1$টি ভিডিও`, no conversion letter); Central Kurdish `sleep_timer_chip_minutes` (`d% خولەک`, letter and percent swapped) | `SearchResultsAdapter` (channel search results that show only a video count) and `PlaylistFragment` (playlists without an uploader); `SleepTimerSheet` (the quick-select chips, built when the sleep timer sheet opens) | Hosted Weblate. LibreTube's contributing guide says contributions and issues made with AI are closed and ignored, so MV2 has not reported it there. |
| pretixSCAN | Korean: `sync_status_pending` and `sync_status_time_days`/`_hours`/`_minutes` each read `%d` twice (both plural forms pasted into the one Korean item, see Mistake types) | `BaseScanActivity.syncStatusText`, shown by `reloadSyncStatus` on the scan screen, on the UI thread (the sync timer and `reload()`); `onResume` catches only `IllegalStateException` | pretix's translation platform. pretix accepts AI-assisted issues only after a person has reviewed and edited them, so MV2 has not filed one. |

Of these 14 projects, three (Mastodon, AnkiDroid, LibreTube) don't accept reports or fixes made with AI tools, and pretix accepts AI-assisted issues only once a person has reviewed and edited them. A census like this one can still help them, because their translators and maintainers can find the rows here.

Checked and cleared: **Wikipedia** (11 rows, see Correction 2). Its Portuguese, Romanian, Indonesian and Russian `temp_account_edit_status` links are broken, which is worth fixing on translatewiki.net, but nothing throws.

Every translation route appears in that table: Crowdin, Transifex, translatewiki.net, Lokalise, Localazy, Weblate, and files edited in the repository. All of these platforms have placeholder checks of some kind, and the crashes shipped anyway. Element X shows that a project's own check can miss them too: its sync script finds the Japanese string but can't fail. Census 0.3.x records which platform each repository names, to compare crash rates by platform.

## Sub-studies

Each folder below is its own study, made with AI agents. Where a folder has a `PREDICTIONS.md`
or `PREREG.md`, the predictions were published before the data were read.

Android and Java `String.format`:

- [callsites/](callsites/RESULTS.md): pre-registered test of call-site rules for which census rows
  really reach code that formats them.
- [unformatted/](unformatted/RESULTS.md): pre-registered check of translations of strings marked
  `formatted="false"`.
- [slint-blind/](slint-blind/RESULTS.md): what i18n-security-lint catches among the census's
  crashing translations.
- [crash-age/](crash-age/RESULTS.md): how long crashing translations stayed in their repositories
  (median 745.5 days); [NOT-FOUND.md](crash-age/NOT-FOUND.md) explains the five rows it could not date.
- [placeholder-order/](placeholder-order/README.md): how often translators move format arguments,
  by language; follow-ups [shape/](placeholder-order/shape/RESULTS.md),
  [np-order/](placeholder-order/np-order/RESULTS.md) and [qt-shape/](placeholder-order/qt-shape/RESULTS.md).

Qt Linguist:

- [qt-args/](qt-args/RESULTS.md): Qt translations that put a value in the wrong place;
  [RTL.md](qt-args/RTL.md) and its pre-registered
  [replication](qt-args/rtl-replication/RESULTS.md).
- [qt-numerus/](qt-numerus/FINDINGS.md): plural counts Qt never fills (`٪n`, `％n`);
  [MORE-PROJECTS.md](qt-numerus/MORE-PROJECTS.md).
- [qt-count/](qt-count/RESULTS.md): pre-registered count of those look-alike counts in 40 more Qt
  projects (both predictions failed).

Look-alike characters (a placeholder written with a character that looks right but is not ASCII):

- [lookalike-percent/](lookalike-percent/FINDINGS.md): `٪` or `％` for `%` in Android; the same in
  [Apple](lookalike-percent/APPLE.md), [gettext](lookalike-percent/GETTEXT.md) and
  [Rails YAML](lookalike-percent/RAILS.md) and [Symfony](lookalike-percent/SYMFONY.md) files, with a
  pre-registered [check of 150 files in five projects](lookalike-percent/yaml-eval/RESULTS.md) (six of
  seven predictions held) and a [by-hand read](lookalike-percent/yaml-eval/SONATA-CHECK.md) of
  SonataAdminBundle's 145 missing-parameter errors (all real); [LINT.md](lookalike-percent/LINT.md).
- [lookalike-brace/](lookalike-brace/BRACES.md): `｛0｝` for `{0}`; the same in
  [Java .properties](lookalike-brace/JAVA.md) and [JSON](lookalike-brace/JSON.md) files, and
  [how common it is per format](lookalike-brace/FORMATS.md); a pre-registered
  [check of .NET .resx files](lookalike-brace/resx-eval/RESULTS.md) (all four predictions held).
- [lookalike-colon/](lookalike-colon/LARAVEL.md): `：attribute` for Laravel's `:attribute`; a
  pre-registered [check of 191 languages](lookalike-colon/laravel-eval/RESULTS.md) in three
  applications (four of five predictions held).

Rates across many projects:

- [rails-rate/](rails-rate/RESULTS.md): pre-registered measurement, over the 214 apps and engines pinned in
  Real World Rails, of how often translations lose, misspell or add `%{name}` (all seven predictions held;
  about 1 in 100 placeholder strings is broken, and every look-alike is in a Chinese, Japanese, Arabic or
  Sindhi file, a quarter of Loomio's Arabic placeholders among them).

Machine-translation artifacts:

- [mt-artifacts/](mt-artifacts/KATAKANA-READING.md): Japanese translations that ship the word's katakana
  reading between fullwidth number signs (`削除＃サクジョ＃`); a pre-registered
  [rule](mt-artifacts/READING-LEAK-PREREG.md) for an l10n-guard warning on them, its
  [results](mt-artifacts/reading-leak/RESULTS.md) (four of four held, found since in NocoBase and
  DuckPro-Kobra3) and a [false-positive test](mt-artifacts/reading-leak/FP-RESULTS.md) on 33 Japanese
  files that use `＃` (four of four held: 25 of 25 matches real, 0 of 113 other uses matched).

Stale translations after a source fix:

- [antonym-collision/](antonym-collision/RESULTS.md): pre-registered scan of NocoBase and Mastodon locale
  files for two keys whose English texts differ by antonyms alone ("Default expanded" vs "Default
  collapse") but share one translation, the shape a source-string fix leaves when translations are
  not refreshed; started from NocoBase's "Default expanded" switch, whose label says the opposite
  in 13 of 16 non-English locales. The rule became l10n-guard 0.12.0's `antonym-collision` warning
  under a [pre-registered test](antonym-collision/GUARD-PREREG.md): on five projects it had never seen
  it raised 19 warnings, one short of the 20 predicted, and 13 of the 19 were graded real by AI agents
  ([results](antonym-collision/GUARD-RESULTS.md)); all 6 that were not defects are "Download failed" /
  "Upload failed" in French or Arabic. A second held-out test on five more projects, with a rule fixed
  in advance for that word class, is [pre-registered](antonym-collision/HOLDOUT2-PREREG.md). It raised
  42 warnings in four of the five (Mattermost's English file has a layout the check can't read yet);
  AI agents graded all 36 outside that class real and 5 of its 6 not defects (Russian, Ukrainian and
  Finnish use one verb for both directions), so l10n-guard 0.13.0 drops the class
  ([results](antonym-collision/HOLDOUT2-RESULTS.md)). l10n-guard 0.14.0 then read Mattermost's
  FormatJS layout, as [pre-registered](antonym-collision/FORMATJS-PREREG.md): 67 warnings in 25,515
  comparisons (2.63 per 1,000), all 40 sampled graded real by AI agents; 21 of the 67 are one defect,
  a permission name English later split into "Convert to private" and "Convert to public" while ten
  languages kept the old single "Convert channels" ([results](antonym-collision/FORMATJS-RESULTS.md)).

## Method

1. Read F-Droid's index (`index-v2.json`): 4,667 apps in 4,476 distinct source repositories.
2. For each repository, make a depth-1, blobless, sparse clone of the latest commit and check out only `res/values*/*.xml`.
3. Pair every translation with its default (`values/`) string when the default text has a printf specifier and isn't marked `formatted="false"`. Plural forms are checked against the source form that reads the most arguments, because `getQuantityString` passes the same arguments to every quantity. From 0.3.1, the text compared is the text a device gets: real child elements (`<b>`, `<xliff:g>`, an `<a>` element) lose their markup and attributes, and markup that is text (CDATA, `&lt;`) stays, placeholders included. `values-qq` (translator notes) is skipped.
4. Give each pair two verdicts:
   - **static**: the `java-format` check of [l10n-guard](https://github.com/munimtechnologies/l10n-guard) (vendored here as `l10n_guard.py`, 0.5.1; `census_fixes.py` applies the 0.3.1 text fix on top);
   - **JVM**: the real OpenJDK 21 `java.util.Formatter` (`FormatCheck.java`), formatting the source and the translation with arguments of the source's types. A `%s` argument gets text once and a number once. `crash` means the translation throws either way. `crash-if-text` means it throws only when the app passes text. A pair whose source string throws too is set aside.
5. **Code use** (from 0.2.0): repositories with a flagged translation also get their `.kt` and `.java` files checked out. Each flagged string is then classified as `formatted` (a `getString`/`stringResource`/`getQuantityString`/`pluralStringResource` call passes it arguments, or it is wrapped in `String.format(...)`/`.format(...)`), `referenced` (used only in other ways), `unreferenced`, or `unknown`. The headline count is JVM crashes in `formatted` strings, because only those are reachable.
6. Write `apps.jsonl` (one line per repository), `findings.csv` (every crash with a link to the file at the commit read), `summary.json` and `report.md`. `apps.jsonl` isn't committed here because of its size; running the census recreates it.
7. `taxonomy.py` sorts the `crash` rows by mistake type (see above). `patterns.py` tags how each mistake got in. `compare.py` lists the crash rows that appear or disappear between two runs. `weblate_blind.py` and `checks_blind.py` run the three free checks over the crash rows (see `CHECKS.md`).

The census reads public files only. It files nothing and contacts no one.

## Run it

Needs Python 3.10+, git and a JDK (`javac` and `java`). Without a JDK the census runs the static check only.

```sh
python bootstrap.py --data-dir cache      # apt-get git + JDK, or Temurin 21 under cache/jdk
python census_fixes.py --data-dir cache --out-dir out --workers 12 --budget-minutes 140   # census 0.3.1
python census_fixes.py --local path/to/android-app --out-dir out   # one checkout, no git
python taxonomy.py out/findings.csv --out-dir out/taxonomy
python patterns.py out/findings.csv --out-dir out/patterns
python compare.py data/findings.csv out/findings.csv --out out/compare.md
python checks_deps.py && python checks_blind.py data/findings.csv --out-dir out/checks   # downloads the checks' sources, pinned
python test_census.py
python test_census_fixes.py
python test_taxonomy.py
python test_patterns.py
python test_weblate_blind.py
python test_checks_blind.py
```

## Prior art

- **Android Lint** (`StringFormatInvalid`, `StringFormatCount`, `StringFormatMatches`) checks format strings within a project. It runs only where a project runs lint, and translations from a translation platform often arrive after the lint step that matters. What it can and can't see of these rows is in `CHECKS.md`.
- **Weblate** has a "Java format" check (`java-printf-format`). Its documentation lists Android string resources among the formats that turn it on automatically. By default a failing check warns rather than blocks, unless a component enforces it. What it can and can't see is in `CHECKS.md`. Crowdin, Transifex and Lokalise have their own placeholder checks, closed source.
- **translate-toolkit / pofilter** has a `printf` test; see `CHECKS.md`.
- Many single-project reports and fixes exist: Commons #4877/#4653, Firefox for Android (fenix) #1580 (German, `Conversion = '@'`), ConnectBot #2478 (Arabic, trailing `%`), OsmAnd #26194, NuvioTV #3697.
- Research: Escobar-Velásquez et al., "An Empirical Study of i18n Collateral Changes and Bugs in GUIs of Android apps" (ICSME 2020), studies layout and GUI damage from translation, not format strings. Fan et al., "Large-Scale Analysis of Framework-Specific Exceptions in Android Apps" (ICSE 2018, arXiv:1801.07009), studies crashes from collected exception traces, not translation files.

Searches of GitHub, arXiv and the web (2026-10-13 to 2026-10-15) found no cross-project measurement of how often shipped Android translations crash `java.util.Formatter`. None found checks static verdicts against a real JVM, checks which crashing strings the code actually formats, sorts the crashes by mistake type, or measures what the free format checks miss on real shipped translations. That is what's new here.

## Limits

- A string counts as formatted when its default text has a printf specifier. Code-use classification is pattern-based. Strings looked up by name at runtime, or formatted in ways the patterns miss, count as `referenced` or `unreferenced`. So the reachable count (232 in census 0.4.0) is a floor in that sense. The corrections above show the census can also overcount; every correction so far was found by reading rows by hand.
- The static check and the JVM read the same extracted text, so their agreement doesn't catch text-extraction mistakes (Correction 2).
- The JVM check passes `Integer` for `%d` arguments. An app that passes `Long` can get a different answer for `%t` (see above) or `%c`.
- `crash-if-text` rows aren't counted, though some are real crashes (the 58 rows of the audit, FadCam's Italian among them).
- Verdicts come from OpenJDK 21. Android's `java.util.Formatter` is the same OpenJDK code for these cases, but edge cases can differ by API level.
- Only the latest commit of each repository's default branch is read. A translation may already be fixed on its translation platform but not yet exported.
- Apps whose source isn't a reachable public git repository (7 in the index), whose clone failed (85) or timed out (2), or that keep strings outside `res/values*/`, aren't covered.
- Translations that don't crash but print the wrong thing (a `٪` instead of `%`, a `%1$2s` where `%1$ds` was meant, a broken link) are outside this census.
- The mistake types are rule-based, from the first placeholder `Formatter` can't use; a row with two different mistakes is counted once.
- The three checks in `CHECKS.md` are mirrored from their sources and run on extracted text, not run inside Weblate, pofilter or Gradle.

## Licence

- Code (`census.py`, `census_fixes.py`, `compare.py`, `FormatCheck.java`, `bootstrap.py`, `taxonomy.py`, `patterns.py`, `weblate_blind.py`, `weblate_deps.py`, `checks_blind.py`, `checks_deps.py`, the `test_*.py` files, and the vendored `l10n_guard.py`): Apache-2.0 (see `LICENSE`). Weblate's and translate-toolkit's sources are downloaded for their patterns only and are not part of this repository.
- Data under `data/` and this write-up: CC BY 4.0. The translated strings quoted belong to their projects, under those projects' licences.

Made by MV2 of Munim, Inc. with AI agents. Contact: mv2@munimtech.com.
