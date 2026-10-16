# Audit of `crash-if-text` rows: 43 more real crashes, and one false-positive cluster

Made by MV2 of Munim, Inc. with AI agents, 2026-10-16. Data: [`crash-if-text-audit.csv`](crash-if-text-audit.csv), CC BY 4.0.

## What was checked

The census gives a `crash-if-text` verdict when the English string has `%s` (or nothing) for an argument and the translation has `%d` there. Whether that throws depends on what the app passes, which the census doesn't know, so these rows are not in its crash totals. In the latest census run (not yet published here) every one of the 189 `crash-if-text` rows has this shape.

For the biggest clusters and the most likely rows, the call that formats the string was read by hand on the project's current default branch, the argument's declared type was looked up, and the translation was re-read on that branch (2026-10-16). A row is `crash` only when a non-null `String` reaches the `%d`. (`java.util.Formatter` prints `null` for `%d` given a null argument, so a nullable value that happens to be null doesn't throw.) Nothing was run on a device.

## Results

43 rows in 10 repositories throw `IllegalFormatConversionException` (`d != java.lang.String`):

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

**False positive, 56 rows:** Jellyfin's `download_remove_description`. The English `one` item is `Do you want to remove "%2$s" ...?` and `other` is `... these %1$d downloads?`. The census compared every translated item with the English `one` item, but the translations follow `other`, and the code passes an `Int` there. Safe. The next census version compares each plural item with the English item of the same quantity, falling back to `other`.

The rows were picked because they looked likeliest, not at random, so 43 out of the rows read is not a rate for the whole bucket. About 75 `crash-if-text` rows haven't been read yet.

## Three translator habits behind these rows

1. **Unindexed placeholders moved to fit word order** (PhoneTrack, KeyMapper, Amaze). The English `%d ... %s` becomes `%s ... %d`, so each argument lands in the other's slot. The fix is indexed placeholders in the source (`%1$d ... %2$s`), which let a translator reorder safely.
2. **A quoted name's `%1$s` typed as `%1$d`** (Tella French 4 times, mako Galician twice in one file while a neighbouring string kept `%1$s`, Open Food Facts). It looks like a per-translator habit, not a one-off slip.
3. **Indexes kept, types swapped** (Session Sinhala and Telugu): the emoji and the count trade places, and each index takes the other's conversion.

A possible fourth, not verified: in Amaze's Urdu `1%d`, the digit may be left over from a `%1$d` whose `%1$` was broken up, so a reorder that was correct with indexes became a crash without them.

## Fixed once, back again

Open Food Facts fixed exactly this crash in `txtHomeOnline` by hand in 2020 ([PR #3558](https://github.com/openfoodfacts/openfoodfacts-androidapp/pull/3558), 6 locales). SD Maid SE fixed a Georgian one in February 2026 (PR #2162). Neither added a check, and both ship the same kind of crash again today. Searches from 2026-10-13 to 2026-10-16 found no earlier write-up of hand-fixed translation format crashes coming back.

## What a check needs to catch these

Compare each translated placeholder's conversion type with the source's at the same argument index. For unindexed placeholders, compare the sequence of types. Flag a digit stuck to an unindexed `%`. Android Lint's `StringFormatMatches` can only do this where it resolves the call. It doesn't look inside `<plurals>`, and it can't see through project helpers like KeyMapper's.

## Limits

- Code read from source on the default branch, not compiled or run on a device. Argument types come from declarations.
- Row selection is not random.
- These 43 rows will count in the census totals only once the next census version re-runs and resolves argument types itself. They are not added to the totals in the README by hand.
- None of these has been reported to its project yet.
