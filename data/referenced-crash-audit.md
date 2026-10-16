# Audit of `crash` rows in strings the code only "references": 24 reachable crashes the census missed

Made by MV2 of Munim, Inc. with AI agents, 2026-10-16. Data: [`referenced-crash-audit.csv`](referenced-crash-audit.csv), CC BY 4.0.

## What was checked

Census 0.4.0 ([`v6/findings.csv`](v6/findings.csv)) found 360 translations that make `java.util.Formatter` throw whatever the app passes. It counts 232 of them as reachable, because a `getString`, `getQuantityString`, `stringResource` or `pluralStringResource` call passes them arguments, or `String.format(getString(id), ...)` wraps them. 40 more are in strings the code names only in other ways (`use` = `referenced`), so the census left them out of the 232.

All 40 were looked up by hand on 2026-10-16: the code that names the string was read, the text was followed to wherever it is formatted, and for the rows marked `crash` the broken translation was re-read on the project's current default branch (except LearnTube, Commons, RxDroid and AndStatus, read at the census commit). Nothing was run on a device.

## Results

| Verdict | Rows | Repositories |
|---|---:|---:|
| `crash`: formatted with arguments, nothing catches it | 24 | 16 |
| `throws, caught`: formatted, but a `catch` turns it into an error message or a failed job | 8 | 4 |
| `throws, trigger not confirmed` | 1 | 1 |
| `safe`: never formatted, never reached, or the census was wrong | 6 | 5 |
| `unread` | 1 | 1 |

So the census's floor of 232 reachable crashes is at least **256**. The 24 come in six ways the census's call patterns don't see:

1. **A library or project helper that takes the id and the arguments.** MoneyWallet's dialogs go through material-dialogs 0.9.6.0's `MaterialDialog.Builder.content(id, args)`, which calls `String.format(context.getString(id), args)`. SmartCookieWeb's `BrowserDialog.showPositiveNegativeDialog(message = id, messageArguments = ...)` calls `getString(message, *messageArguments)`. NewPipe's (and its fork LearnTube's) `Localization.getQuantity(context, R.plurals.views, ...)` calls `getQuantityString(pluralId, count, formattedCount)`. Lavabit's `VpnStatus.logInfo(id, args)` formats later, in the log screen.
2. **The id is stored and formatted elsewhere.** Petals keeps `current_thc_concentration` in a `ChartConfig` object; `SymptomsPage` calls `getString(chartConfig.title, ...)`. RxDroid picks `resId` in a `when`-like chain and calls `getString(resId, begin, end)`. ownCloud and Habit-Maker pick the id in an `if` or `when` (file or folder, one or several) and then call `getString(id, arg)` or `stringResource(id, arg)` with the chosen variable.
3. **Fetched without arguments, formatted in a second step.** AdAway, Retro Music and its fork Metro, and Wikimedia Commons call `getString(id)` (or `getText(id).toString()`) first and `String.format(template, ...)` a line or a method later.
4. **`String.format` around a `getResources().getString(...)` call.** SecondScreen writes `String.format(getResources().getString(R.string.debug_mode_enabling), 10 - clicks)`, and Helsinki Timetables does the same for its screen headers and its delete dialog. The census's wrap pattern doesn't allow the `()` of `getResources()`.
5. **`String.format` around `getQuantityString`.** HeartBeat writes `String.format(Locale.getDefault(), getResources().getQuantityString(id, n), pulse, n, seconds)`. The census only looks for that wrap around `getString` and `stringResource`.
6. **An escape the translator copied from Kotlin.** Habit-Maker's Persian `x_days_completed` is written `%1\\$s` in the XML. aapt2 turns `\\` into one backslash (and would have dropped a single one before `$`), so the app gets `%1\$s`, and `%1\` throws. The census decodes escapes the same way; the call is `stringResource(countString, ...)` with the id in a variable, so it was counted as only referenced.

Commons is the sharpest case: `WikidataEditService.showSuccessToast` carries `@SuppressLint("StringFormatInvalid")`, so Android Lint was told not to warn about exactly the call that throws in Tulu.

### The 24 crashes

| App | Locale | String | When it throws |
|---|---|---|---|
| AdAway | Dutch | `welcome_sync_error` | The first sync on the welcome screen fails: `WelcomeSyncFragment.notifyError` runs `String.format(syncError, errorMessage)`. The Dutch text starts with `81%match` on a line of its own, a translation-memory match score pasted in with the translation, and `%m` is not a conversion |
| MoneyWallet | Turkish | `message_data_export_failed`, `message_data_import_failed`, `message_error_legacy_upgrade_failed` | An export or import fails (`ImportExportActivity`'s broadcast receiver), or the upgrade from the legacy edition fails (`LauncherActivity`). Each builds a material-dialogs dialog with `.content(id, message)`. The Turkish has `% s`. Repository inactive since November 2021 |
| SmartCookieWeb | Spanish, Lithuanian | `message_permission_request` | A web page asks for the camera or microphone while WebRTC is on in settings: `SmartCookieChromeClient.requestResources` shows `BrowserDialog.showPositiveNegativeDialog` with two arguments. Spanish has `% 2 $ s`, Lithuanian `%2 s` |
| Petals | Indonesian | `current_thc_concentration` | Opening the withdrawal page's THC concentration chart: its title is `getString(chartConfig.title, "%.2f".format(value))`, and the Indonesian ends in a bare `%` where the English has `%%` |
| Retro Music | Telugu (India) | `could_not_scan_files` | A media scan finishes with at least one file that failed: `UpdateToastMediaScannerCompletionListener.onScanCompleted` runs `String.format(couldNotScanFiles, failed)` on the UI thread. The Telugu has `% D` |
| Metro (a Retro Music fork) | Telugu (India) | `could_not_scan_files` | same code and same translation |
| NewPipe | Kurmanji | `views` (`one`) | Any list or page that shows a video with exactly one view: `Localization.localizeViewCount` and `shortViewCount` call `getQuantity`, which calls `getQuantityString(R.plurals.views, count, formattedCount)`. Kurmanji's `one` item has `% s`. Checked on `dev` |
| LearnTube (a NewPipe fork) | Kurmanji | `views` (`one`) | same code and same translation |
| HeartBeat | Bengali | `measurement_output_template` (`one`, `other`) | Every pulse measurement, as soon as the first beat is detected and again at the end: the code passes (pulse `float`, cycles `int`, seconds `float`), and the Bengali items move the unnumbered `%d` to the end, so the cycle count reaches the second `%2.1f`. No `try` |
| Wikimedia Commons | Tulu | `successful_wikidata_edit` | The toast after a picture is added to a Wikidata item: `String.format(Locale.getDefault(), template, wikiItemName)` on the Tulu `%1$` with no conversion letter, under `@SuppressLint("StringFormatInvalid")` |
| Habit-Maker | Persian | `x_days_completed` | The home screen's habit list, for every habit's days-completed chip (unless that chip or chip descriptions are hidden in settings): `HabitDaysCompletedInfoChip` calls `stringResource(countString, prettyFormat(completed))`, and the runtime text is `%1\$s`. The same file's `x_percent_complete` has the same `%1\$s` and is already among the census's 232 |
| SecondScreen | Italian | `debug_mode_enabling` | Tapping towards the hidden debug mode: `String.format(getResources().getString(...), 10 - clicks)`; the Italian `%1$ passi` is read as `%1$ p`, and `p` is not a conversion |
| RxDroid | German | `_msg_constraints_date_before` | A date picker that has only a latest date and shows its limits: `DatePickerDialog.getConstraintMessage` calls `getString(resId, begin, end)`, and the German `%2$2` has no conversion letter. Which screens open such a picker was not checked |
| Lavabit Encrypted Proxy | Vietnamese | `using_proxy` | Sending the app's log (or viewing it with the level slider at 2 or higher) after a connection went through a proxy: `sendProxyCMD` logs `VpnStatus.logInfo(R.string.using_proxy, proxyname, proxyname)`, and `LogFragment` formats every entry with `LogItem.getString(getActivity())`, which turns only `NotFoundException` into a fallback text; it catches `UnknownFormatConversionException` (the one this item throws) just to throw it again with more text. The Indonesian item of the same string is in the `crash-if-text` audit. The Vietnamese item is written in Thai script and reads `% 1 $ s% 2 $ s` |
| ownCloud | Uyghur | `confirmation_remove_file_alert`, `confirmation_remove_files_alert` | Removing one file, or several files with no folder among them: `RemoveFilesDialogFragment` picks the id by count and folder, then calls `requireContext().getString(messageStringId, messageArguments)` with a `String` (the name, or the count as text). The Uyghur has `% 1 $ s` and `% s`. No `try` in the class |
| ownCloud | Uyghur | `file_already_exists_description` | Moving or copying a file into a folder that has one with the same name: `FileDisplayActivity.showConflictDecisionDialog` calls `getString(if (file.isFolder) ... else ..., file.fileName)`. The Uyghur has `% 1 $ s` |
| Helsinki Timetables | Chinese | `header_trips`, `stations_list_of_trips_header` | Opening a vehicle type's list of trips, or a station's list of trips: the screen's header is built with `String.format(getResources().getString(id), name)` in `addLayoutElements`, which `AbstractView.onCreate` calls inside a `try` that catches only `DatabaseException`. The Chinese items have a bare `%` before a Chinese character (`所有%路線`, `%站牌所有可能路線`) |
| Helsinki Timetables | Chinese | `dialog_confirm_delete_bookmarks` | Tapping the delete button on a bookmark: `BookmarksDeleteView` runs `String.format(getResources().getString(id), name)` for the confirmation dialog, with no `try`. The Chinese reads `您要刪除%書籤嗎？` |

### Throws, but caught

- **Material Files, Basque, `file_job_extract_scan_notification_title_format` (`one`, `other`).** Extracting an archive posts a scan notification with `getQuantityString(titleRes, fileCount, fileCount, size)`. The Basque `%1$ e...` is read as `%1$ e`, a scientific-notation float, which rejects the `Int`. `FileJob.runOn` catches every `Exception` and shows it as a toast, so the app doesn't crash, but every archive extraction stops at its first scanned entry (the first notification is posted right after it, whatever the throttle). The other job plurals in the same file keep `%1$,d`.
- **AndStatus, Traditional Chinese, `friends_of` and `menu_item_user_messages`.** Both go through the project's `StringUtil.format(context, id, args)` (the actor and note context menus, and `TimelineType.title` for the "sent" timeline), which catches the exception and returns `Error formatting resourceId=...` as the menu item's or title's text.
- **ownCloud, Uyghur, `downloader_download_succeeded_content` and `downloader_download_failed_content`.** `DownloadFileWorker` saves the file and updates the database, then `notifyDownloadResult(null)` asks `ErrorMessageAdapter.getMessageFromTransfer` for the notification text, which runs `String.format` on the Uyghur `% 1 $ s` and throws. `doWork`'s `catch` calls `notifyDownloadResult` again with that exception, which throws again on the failure text, and the exception leaves `doWork`. `CoroutineWorker` catches it and marks the work failed. So in Uyghur every download is saved but its notification never appears and the work is recorded as failed. Not run on a device.
- **Helsinki Timetables, Chinese, `header_trips_directions` and `header_one_trip`.** Both are formatted inside loops with a `catch (Exception e)`: the list of a line's trip directions shows the app's SQL error message instead, and a stop's timetable stops at its first row (the error is only logged).

### Throws, trigger not confirmed

- **ownCloud, Uyghur, `sync_fail_content_unauthorized`.** `FileSyncAdapter.notifyFailedSynchronization` formats it with the account name, with no `try`, when a manual sync had failed folders and the last capabilities refresh failed as unauthorized. Whether the app still syncs through this adapter, and how a user reaches that state, was not checked.

### Safe

- **NewPipe, Indonesian, `sign_in_confirm_not_bot_error`: a census false positive.** The English has `%2$s` inside a real `<a href="%2$s">` element, which the census removes before counting arguments, so it decided the code passes one. `ErrorInfo` passes two (the service name and the FAQ address), so the Indonesian's `%2$s` is filled.
- **Wikimedia Commons, N'Ko, `add_picture_to_wikipedia_article_desc`.** Fetched with `getString(id)` and never formatted, so the broken `%1$` is shown as written.
- **Your local weather, Arabic, `title_activity_license`.** `LicenseActivity` uses `getString(id).replace("%s", path)`, not a formatter. The Arabic has no `%s`, so the title shows without the path, but nothing throws.
- **HeartBeat, Bengali, `measurement_output_template` (`zero`).** Bengali has no `zero` plural category, so Android never picks this item.
- **ownCloud, Uyghur, `uploader_upload_succeeded_content_single` and `error__upload__local_file_not_copied`.** Both sit in `ErrorMessageAdapter.getMessageFromTransfer`'s upload branches, and its only caller, `DownloadFileWorker`, passes a download. Not reached at the census commit.

### Not read

Suntimes Calendars' Dutch `units_years_ago` (`other`): the code that names it was not among the seven files read, and the repository is not on Sourcegraph.

## A string the census never checked

Helsinki Timetables' Chinese `header_times` (`%時刻表，站名%`) also throws: `StationsListOfTrips.getHeaderNextScreen` formats it, inside a `catch (Exception e)` that only logs, so a station's list of trips stops filling. It is not in the census at all, because the English is marked `formatted="false"`. aapt2 reads that attribute only to skip its check for several unnumbered placeholders; the text is the same and the app still formats it. Census 0.4.0 skips every such string, as Android Lint's format checks do. A run of the census over just those strings is queued.

## What a census needs to see these

Follow a string id through assignments and arguments, not only into the call it appears in: treat any call that receives `R.string.x` (or `R.plurals.x`) followed by more arguments as a candidate, follow a variable that holds `getString(id)` or an id chosen by `if`/`when` into a later `format` or `getString`, and allow any receiver chain (`getResources().getString(...)`, `getQuantityString(...)`) inside `String.format(...)`. Each of these finds false candidates too (`Toast.makeText(context, R.string.x, LENGTH_SHORT)` passes an id followed by more arguments), so their hits should be a list to read, not crashes to count. And a `catch` decides whether a throw is a crash, so a census that says "reachable" should also say what catches it.

## Limits

- Code read from source, mostly at the commit the census read; not compiled or run on a device. For 21 of the 24 crash rows the translation was re-read on the current default branch (for MoneyWallet and Lavabit that is the commit the census read).
- `throws, caught` and `safe` were decided from the code paths found; a call site the search missed could still format a `safe` string.
- None of these has been reported to its project yet. ownCloud's Uyghur file was reported in their issue #5018.
- These rows are not added to the README's totals by hand; the next census version should count them.
