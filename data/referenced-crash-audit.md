# Audit of `crash` rows in strings the code only "references": 17 reachable crashes the census missed

Made by MV2 of Munim, Inc. with AI agents, 2026-10-16. Data: [`referenced-crash-audit.csv`](referenced-crash-audit.csv), CC BY 4.0.

## What was checked

Census 0.4.0 ([`v6/findings.csv`](v6/findings.csv)) found 360 translations that make `java.util.Formatter` throw whatever the app passes. It counts 232 of them as reachable, because a `getString`, `getQuantityString`, `stringResource` or `pluralStringResource` call passes them arguments, or `String.format(getString(id), ...)` wraps them. 40 more are in strings the code names only in other ways (`use` = `referenced`), so the census left them out of the 232.

All 40 were looked up by hand on 2026-10-16: the code that names the string was read, the text was followed to wherever it is formatted, and for the rows marked `crash` the broken translation was re-read on the project's current default branch (except LearnTube, Commons, RxDroid and AndStatus, read at the census commit). Nothing was run on a device.

## Results

| Verdict | Rows | Repositories |
|---|---:|---:|
| `crash`: formatted with arguments, nothing catches it | 17 | 13 |
| `throws, caught`: formatted, but a `catch` turns it into an error message | 3 | 2 |
| `safe`: never formatted, or the census was wrong | 4 | 4 |
| `unread` | 16 | 5 |

So the census's floor of 232 reachable crashes is at least **249**. The 17 come in five ways the census's call patterns don't see:

1. **A library or project helper that takes the id and the arguments.** MoneyWallet's dialogs go through material-dialogs 0.9.6.0's `MaterialDialog.Builder.content(id, args)`, which calls `String.format(context.getString(id), args)`. SmartCookieWeb's `BrowserDialog.showPositiveNegativeDialog(message = id, messageArguments = ...)` calls `getString(message, *messageArguments)`. NewPipe's (and its fork LearnTube's) `Localization.getQuantity(context, R.plurals.views, ...)` calls `getQuantityString(pluralId, count, formattedCount)`. Lavabit's `VpnStatus.logInfo(id, args)` formats later, in the log screen.
2. **The id is stored and formatted elsewhere.** Petals keeps `current_thc_concentration` in a `ChartConfig` object; `SymptomsPage` calls `getString(chartConfig.title, ...)`. RxDroid picks `resId` in a `when`-like chain and calls `getString(resId, begin, end)`.
3. **Fetched without arguments, formatted in a second step.** AdAway, Retro Music and its fork Metro, and Wikimedia Commons call `getString(id)` (or `getText(id).toString()`) first and `String.format(template, ...)` a line or a method later.
4. **`String.format` around a `getResources().getString(...)` call.** SecondScreen writes `String.format(getResources().getString(R.string.debug_mode_enabling), 10 - clicks)`. The census's wrap pattern doesn't allow the `()` of `getResources()`.
5. **`String.format` around `getQuantityString`.** HeartBeat writes `String.format(Locale.getDefault(), getResources().getQuantityString(id, n), pulse, n, seconds)`. The census only looks for that wrap around `getString` and `stringResource`.

Commons is the sharpest case: `WikidataEditService.showSuccessToast` carries `@SuppressLint("StringFormatInvalid")`, so Android Lint was told not to warn about exactly the call that throws in Tulu.

### The 17 crashes

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
| SecondScreen | Italian | `debug_mode_enabling` | Tapping towards the hidden debug mode: `String.format(getResources().getString(...), 10 - clicks)`; the Italian `%1$ passi` is read as `%1$ p`, and `p` is not a conversion |
| RxDroid | German | `_msg_constraints_date_before` | A date picker that has only a latest date and shows its limits: `DatePickerDialog.getConstraintMessage` calls `getString(resId, begin, end)`, and the German `%2$2` has no conversion letter. Which screens open such a picker was not checked |
| Lavabit Encrypted Proxy | Vietnamese | `using_proxy` | Sending the app's log (or viewing it with the level slider at 2 or higher) after a connection went through a proxy: `sendProxyCMD` logs `VpnStatus.logInfo(R.string.using_proxy, proxyname, proxyname)`, and `LogFragment` formats every entry with `LogItem.getString(getActivity())`, which turns only `NotFoundException` into a fallback text; it catches `UnknownFormatConversionException` (the one this item throws) just to throw it again with more text. The Indonesian item of the same string is in the `crash-if-text` audit. The Vietnamese item is written in Thai script and reads `% 1 $ s% 2 $ s` |

### Throws, but caught

- **Material Files, Basque, `file_job_extract_scan_notification_title_format` (`one`, `other`).** Extracting an archive posts a scan notification with `getQuantityString(titleRes, fileCount, fileCount, size)`. The Basque `%1$ e...` is read as `%1$ e`, a scientific-notation float, which rejects the `Int`. `FileJob.runOn` catches every `Exception` and shows it as a toast, so the app doesn't crash, but every archive extraction stops at its first scanned entry (the first notification is posted right after it, whatever the throttle). The other job plurals in the same file keep `%1$,d`.
- **AndStatus, Traditional Chinese, `friends_of`.** `ActorContextMenu` calls the project's `StringUtil.format(context, id, shortName)`, which catches the exception and returns `Error formatting resourceId=...` as the menu item's text.

### Safe

- **NewPipe, Indonesian, `sign_in_confirm_not_bot_error`: a census false positive.** The English has `%2$s` inside a real `<a href="%2$s">` element, which the census removes before counting arguments, so it decided the code passes one. `ErrorInfo` passes two (the service name and the FAQ address), so the Indonesian's `%2$s` is filled.
- **Wikimedia Commons, N'Ko, `add_picture_to_wikipedia_article_desc`.** Fetched with `getString(id)` and never formatted, so the broken `%1$` is shown as written.
- **Your local weather, Arabic, `title_activity_license`.** `LicenseActivity` uses `getString(id).replace("%s", path)`, not a formatter. The Arabic has no `%s`, so the title shows without the path, but nothing throws.
- **HeartBeat, Bengali, `measurement_output_template` (`zero`).** Bengali has no `zero` plural category, so Android never picks this item.

### Not read

ownCloud's 8 Uyghur rows (the same file its maintainers acknowledged in [#5018](https://github.com/owncloud/android/issues/5018)), Helsinki Timetables' 5 Chinese rows, AndStatus's `menu_item_user_messages`, Suntimes Calendars' Dutch `units_years_ago`, and Habit-Maker's Persian `x_days_completed`. Habit-Maker formats it with `stringResource(id, prettyFormat(completed))`, but the Persian writes `%1\$s`. Whether Android's resource compiler turns `\$` into `$` (which would make it safe) was not checked.

## What a census needs to see these

Follow a string id through assignments and arguments, not only into the call it appears in: treat any call that receives `R.string.x` (or `R.plurals.x`) followed by more arguments as a candidate, follow a variable that holds `getString(id)` into a later `format`, and allow any receiver chain (`getResources().getString(...)`, `getQuantityString(...)`) inside `String.format(...)`. Each of these finds false candidates too (`Toast.makeText(context, R.string.x, LENGTH_SHORT)` passes an id followed by more arguments), so their hits should be a list to read, not crashes to count.

## Limits

- Code read from source, mostly at the commit the census read; not compiled or run on a device. For 14 of the 17 crash rows the translation was re-read on the current default branch (for MoneyWallet and Lavabit that is the commit the census read).
- `throws, caught` and `safe` were decided from the code paths found; a call site the search missed could still format a `safe` string.
- None of these has been reported to its project yet.
- These rows are not added to the README's totals by hand; the next census version should count them.
