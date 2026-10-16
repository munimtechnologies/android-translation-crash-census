# Hand checks waiting to enter the audit

MV2 of Munim, Inc. Made with AI agents. Licensed under the Apache License, Version 2.0 (Apache-2.0), like
the rest of this repository.

These are rows of the census 0.4.0 data (`data/v6/findings.csv`) marked `crash-if-text`: they throw only
if the app passes text where the translation expects a number. AI agents working in MV2's name read
each app's call site and the argument's declared type, then re-read the translation on the app's
default branch. Nothing was compiled or run on a device. The rows will move into
`data/crash-if-text-audit.csv` when its next update lands. They stay here until then, so the totals in the
README don't count them yet.

Checked on 2026-10-16.

## Crashes (5 rows, 5 apps)

| app | repo | branch | locale | key | what reaches the placeholder | call site |
|---|---|---|---|---|---|---|
| ownCloud | owncloud/android | master | lo | lock_time_try_again | `PassCodeViewModel` posts the lockout countdown as an "mm:ss" String (`String.format(Locale.US, "%02d:%02d", ...)`). The English `%1$s` reads it as text, but the Lao translation has `%1$d` | `PassCodeActivity.kt`, `getString(R.string.lock_time_try_again, it)` in the countdown observer |
| FileManagerSphere | Ruan625Br/FileManagerSphere | master | zh-rCN | an_error_message_occurred[other] | the file name (String) reaches `%d`. The English is `%d errors occurred while saving the file %s`; the translation `保存文件「%s」时发生 %d 个错误` moves the unnumbered placeholders, and Chinese uses the `other` form even for 1 | `CodeEditorFragment.java` `saveFile`: `getQuantityString(R.plurals.an_error_message_occurred, 1, 1, fileName)`, no try/catch; shown when saving fails |
| LightNovelReader | dmzz-yyhyy/LightNovelReader | dev/1.3 | zh-rTW | plugin_signature_public_key_value | `publicKeyAlgorithm` (String) reaches `%2$d`. The English is `%1$d-bit %2$s`; the translation `%1$s 位 %2$d` swaps the types | `PluginManagerDialog.kt` `PluginSignatureDialog`: `stringResource(R.string.plugin_signature_public_key_value, sig.publicKeyLength, sig.publicKeyAlgorithm)` (`Int`, `String` in `utils/Signature.kt`) |
| FadCam | anonfaded/FadCam | master | it | faditor_export_info | `durationStr` (String) reaches `%1$d`. The English is `%1$s • %2$d clip(s)%3$s • H.264 + AAC`; the Italian `%1$d segmenti • %2$s` reads like a translation of an older English text | `FaditorEditorActivity.java` `showExportInfoOnScreen`: `getString(R.string.faditor_export_info, durationStr, clipCount, audioInfo)` (`String`, `int`, `String`), no try/catch |
| J2ME Loader | nikita36078/J2ME-Loader | master | pt | err_missing_app | `storageName` (String: `""`, or the storage volume's name in quotes) reaches `% d`. The English is `... storage device %savailability ...`; the Portuguese `Verifique a% de disponibilidade` has a stray `%` that Java reads as `% d` (a `%d` with a space flag) | `ConfigActivity.java` `onCreate`: `getString(R.string.err_missing_app, storageName)`, no try/catch; shown when the app's folder is missing |

## Safe (3 strings, 4 apps)

| app | locale | key | why |
|---|---|---|---|
| N-Zik | fr | format_ms | `GeneralSettings.kt` passes `it.toLong()`, so the French `%1$d ms` gets a number |
| NotallyX | ru | exported_notes (all forms) | every call goes through the project helper `Context.getQuantityString(id, quantity, vararg)` in `UiExtensions.kt`, which passes `quantity` (an Int) as argument 1. The same holds for `imported_notes` |
| Delta Chat, ArcaneChat | ja, ko | ask_send_following_n_files_to[other] | the census marks the string unreferenced, and a code search of deltachat-android finds no use outside the XML files. The Japanese and Korean move the unnumbered `%d` and `%s`, so they would print wrongly or crash if the string were ever used, but nothing uses it now |

## What the five crashes have in common

Three of the five are habits already listed in the audit: placeholders moved without numbers
(FileManagerSphere), numbered types swapped (LightNovelReader), and a translation of an older English
string (FadCam). The ownCloud row is the "number given as preformatted text" habit: the code formats the
number itself and passes a String, which the English `%1$s` accepts but a translator's `%1$d` does not.
J2ME Loader is a percent sign in prose that Java reads as a placeholder.

`% d` is not always a mistake, though. In ownCloud's Uyghur strings `% d` stands for the English `%d`, and
Java prints the number with a leading space without throwing. In J2ME Loader the English has `%s`, the
app passes text, and `% d` throws. A check has to compare against the source to tell the two apart.
l10n-guard 0.6.0 will do this: a warning for the first case, an error for the second.

None of the five had been reported, according to each project's issue search on 2026-10-16. Reports for
LightNovelReader, FadCam and ownCloud are drafted but not filed yet.
