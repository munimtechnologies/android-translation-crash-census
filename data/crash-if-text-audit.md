# Audit of `crash-if-text` rows: 50 more real crashes, and one false-positive cluster

Made by MV2 of Munim, Inc. with AI agents, 2026-10-16. Data: [`crash-if-text-audit.csv`](crash-if-text-audit.csv), CC BY 4.0.

## What was checked

The census gives a `crash-if-text` verdict when the English string has `%s` (or nothing) for an argument and the translation has `%d` there. Whether that throws depends on what the app passes, which the census doesn't know, so these rows are not in its crash totals. In the latest census run (not yet published here) every one of the 189 `crash-if-text` rows has this shape.

For the biggest clusters and the most likely rows, the call that formats the string was read by hand on the project's current default branch, the argument's declared type was looked up, and the translation was re-read on that branch (2026-10-16). A row is `crash` only when a non-null `String` reaches the `%d`. (`java.util.Formatter` prints `null` for `%d` given a null argument, so a nullable value that happens to be null doesn't throw.) Nothing was run on a device.

## Results

50 rows in 14 repositories throw `IllegalFormatConversionException` (`d != java.lang.String`):

| App | Locales | String | When it throws |
|---|---|---|---|
| Session | Sinhala, Telugu | `emojiReactsCountOthers` (one, other) | Reactions sheet, once more than 5 people reacted to an emoji. `getBaseEmoji()` is `@NonNull String` |
| ThreatScoopOnionChat (a Session fork) | Sinhala, Telugu | same | same; the fix belongs in Session first |
| Open Beauty / Products / Pet Food Facts (legacy app flavors) | Serbian (Cyrillic, Latin, sr-rCS, sr-rME), Hebrew | `txtHomeOnline` | Home screen, once the product count loads: the count is passed already formatted as text |
| Tella | French | 4 strings: `Resources_RemovedResource`, `Uwazi_Entity_Deleted_Toast`, `Uwazi_Template_Removed_Toast`, `Vault_SaveToDevice_SheetTitle` | Deleting a resource or Uwazi entity, removing a template, "save to device" for a vault file |
| KeyMapper | Turkish, Simplified Chinese | `description_pinch_coordinate_default`, `_with_description` | Showing a key map that has a pinch action. The arguments go through the project's own `getString(resId, Array)` helper |
| PhoneTrack | Bulgarian, Polish, Russian, Chinese (Simplified, Traditional) | `sms_logjob_created` | When an SMS command creates a log job |
| Amaze File Manager | Urdu (ur, ur-rPK) | `copyingapks` | Backing up any app from App Manager (the path is `File.getPath()`) |
| mako | Catalan, Spanish, Galician | `filepicker_selected_icon_pack`; Galician also `toast_app_selected` | Icon settings once a pack is selected; picking a clock-tap or date-tap app (`AppEntry.label: String`) |
| AURdroid | Spanish | `plurals_formatted_package_found` | Every search with results (repository inactive since 2022) |
| SD Maid SE | Finnish, Georgian | `appcleaner_delete_confirmation_message_x`, `corpsefinder_watcher_notification_delete_result` | App cleaner delete confirmation; the uninstall-watcher notification |
| EweSticker | Bengali, Urdu, Traditional Chinese | `imported_033` | Importing a sticker folder that holds a file of an unsupported type: its MIME type (`DocumentFile.getType()`, a non-null `String` for any real file) reaches `%1$d`. Only `IOException` is caught there, so the exception also cancels the folder's other imports |
| YTDLnis | Indonesian | `waiting_download_delay` | Starting a download with a download delay set in settings: the delay is passed already formatted as text (`"%.2f".format(delaySec)`). The call runs in a coroutine launched under a `SupervisorJob` with no `CoroutineExceptionHandler`, so the worker's own `try` doesn't catch it and, by kotlinx.coroutines' rules, it goes to the thread's uncaught-exception handler. Every other locale keeps `%s` |
| DashPay Wallet | Japanese, Korean | `wallet_coinjoin_timeskew_dialog_msg` | The clock warning shown when CoinJoin mixing is on and the device time is off: the app passes the word for ahead/behind (a `String`) and then the seconds (a `Long`), and these two translations put an unnumbered `%d` before `%s`, so the text reaches `%d`. The dialog is built inside `lifecycleScope.launch` with no `try`. Unnumbered reorder, as in PhoneTrack, KeyMapper and Amaze. The census found it in the HashEngineeringSolutions copy; checked on dashpay/dash-wallet |
| VLC for Android | Hindi | `duplicate_three_options_secondary` (`other`) | Adding tracks to an existing playlist when two or more of them, but not all, are already in it. The app passes the duplicate count (`Int`) and then `playlist.title` (a `String`); the Hindi item reads `"%s" ... %d`, an unnumbered reorder of the English `%d ... "%s"`, so the title reaches `%d`. With exactly one duplicate the app passes only the title and uses the `one` item, which is safe. No `try` around the call. The Hindi file was last changed in February 2025. Checked on the GitHub mirror of code.videolan.org/videolan/vlc-android |

**False positive, 56 rows:** Jellyfin's `download_remove_description`. The English `one` item is `Do you want to remove "%2$s" ...?` and `other` is `... these %1$d downloads?`. The census compared every translated item with the English `one` item, but the translations follow `other`, and the code passes an `Int` there. Safe. The next census version compares each plural item with the English item of the same quantity, falling back to `other`.

The rows were picked because they looked likeliest, not at random, so 50 out of the rows read is not a rate for the whole bucket. About 68 `crash-if-text` rows haven't been read yet.

## Four translator habits behind these rows

1. **Unindexed placeholders moved to fit word order** (PhoneTrack, KeyMapper, Amaze, DashPay Wallet, VLC). The English `%d ... %s` becomes `%s ... %d`, so each argument lands in the other's slot. The fix is indexed placeholders in the source (`%1$d ... %2$s`), which let a translator reorder safely.
2. **A quoted name's `%1$s` typed as `%1$d`** (Tella French 4 times, mako Galician twice in one file while a neighbouring string kept `%1$s`, Open Food Facts). It looks like a per-translator habit, not a one-off slip.
3. **Indexes kept, types swapped** (Session Sinhala and Telugu): the emoji and the count trade places, and each index takes the other's conversion.
4. **A translation of an older English string kept after its placeholders changed** (EweSticker). English `imported_033` is now `E033: Unsupported format found (%1$s, file: %2$s/%3$s)`, with the MIME type first. The Bengali, Urdu and Traditional Chinese items still translate an earlier text ("some stickers failed to import (%1$d imported)") with `%1$d`. Why the old text is still exported was not checked.

A possible fifth, not verified: in Amaze's Urdu `1%d`, the digit may be left over from a `%1$d` whose `%1$` was broken up, so a reorder that was correct with indexes became a crash without them.

## Fixed once, back again

Open Food Facts fixed exactly this crash in `txtHomeOnline` by hand in 2020 ([PR #3558](https://github.com/openfoodfacts/openfoodfacts-androidapp/pull/3558), 6 locales). SD Maid SE fixed a Georgian one in February 2026 (PR #2162). Neither added a check, and both ship the same kind of crash again today. Searches from 2026-10-13 to 2026-10-16 found no earlier write-up of hand-fixed translation format crashes coming back.

## What a check needs to catch these

Compare each translated placeholder's conversion type with the source's at the same argument index. For unindexed placeholders, compare the sequence of types. Flag a digit stuck to an unindexed `%`. Android Lint's `StringFormatMatches` can only do this where it resolves the call. It doesn't look inside `<plurals>`, and it can't see through project helpers like KeyMapper's.

## Limits

- Code read from source on the default branch, not compiled or run on a device. Argument types come from declarations.
- Row selection is not random.
- These 50 rows will count in the census totals only once the next census version re-runs and resolves argument types itself. They are not added to the totals in the README by hand.
- None of these has been reported to its project yet.
