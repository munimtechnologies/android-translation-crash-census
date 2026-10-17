# lookalike-percent: Android placeholders written with ٪ or ％

MV2 of Munim, Inc., made with AI agents, 2026-10-17. Text CC BY 4.0.
Read in source and in translation files; not run on a device.
Nothing here has been reported to the projects yet.

## The rule

On Android, `getString(id, args)`, `getQuantityString(id, n, args)` and
`String.format` hand the translation to `java.util.Formatter`. Formatter only
starts a placeholder at the ASCII percent sign `%` (U+0025). If a translation
writes the placeholder with the Arabic percent sign `٪` (U+066A) or the fullwidth
percent sign `％` (U+FF05), the call doesn't crash. Formatter just copies `٪s`,
`٪1$s` or `％d` to the screen as plain text and never uses the argument. The
user sees "٪s" where a name, size or count should be, and only in that
language.

This is the Android counterpart of the Qt case in [qt-numerus](../qt-numerus/FINDINGS.md),
where `٪n` and `％n` take the place of Qt's `%n`.

## How common it is (Sourcegraph snapshot, 2026-10-17)

These are literal searches of `strings.xml` files on sourcegraph.com. Sourcegraph
leaves out forks and archived repositories by default. This is a snapshot of
what it indexes, not a census.

| Query (keyword, quoted) | Matches | Repositories |
|---|---:|---:|
| `"٪d" file:strings\.xml$` | 9 | 2 |
| `"٪s" file:strings\.xml$` | 68 | 9 |
| `"٪1$" file:strings\.xml$` | 83 | 6 |
| `"％d" file:strings\.xml$` | 9 | 6 |
| `"％1$" file:strings\.xml$` | 6 | 6 |
| `"％s" file:strings\.xml$` | about 74 files (stream incomplete) | 33 or more |
| `"﹪"` (U+FE6A small percent sign) `file:strings\.xml$` | 0 | 0 |

The `％s` count is mostly not a format bug. About 50 of those files are copies
of ZXing's Barcode Scanner string `preferences_custom_product_search_summary`.
In English it reads "Substitutions: %s = contents, %f = format, %t = type": it
tells the user which tokens to type into a custom search URL. Its Chinese and
Japanese copies say `％s`, `％f`, `％t`. That is a documentation slip (a user who
copies it types a token the app doesn't replace), not a lost argument. It is
counted here but not in the table below.

Arabic `٪` turns up in Arabic, Persian, Central Kurdish (ckb), Uyghur and
Kashmiri files. Fullwidth `％` turns up in Chinese and Japanese files.

## Confirmed in code (each string is formatted with an argument)

For each row we found the call that formats the string and checked that the
English source uses an ASCII placeholder in the same place.

| App | Locale(s) | String | Look-alike | Formatting call (file:line @ commit) | What the user sees |
|---|---|---|---|---|---|
| Windscribe Android-App | ar, fa | `set_this_protocol_as_preferred` | `٪s` | `mobile/.../SetupPreferredProtocolScreen.kt:122` `stringResource(..., Util.getProtocolLabel(...))` @ 2c585dd | the "set as preferred protocol?" prompt without the protocol's name |
| Windscribe Android-App | fa | `ping_time` | `٪D` | `tv/.../StaticIpAdapter.kt:44`, `FavouriteAdapter.kt:50`, `DetailViewAdapter.kt:54` `getString(R.string.ping_time, pingTime)` @ 2c585dd | "٪D" in place of each server's latency on Android TV |
| Retro Music Player | zh-rCN | `delete_song_x` | `％1$s` | `dialogs/DeleteSongsDialog.kt:119` `String.format(getString(R.string.delete_song_x), songs[0].title)` @ a7d4d05 | the delete-song dialog without the song title |
| Threema | zh-rCN | plurals `really_delete_thread_message` | `％d` | `archive/ArchiveViewModel.kt` (around line 212) `getQuantityString(..., selectedConversationUiModels.size, ...size)` @ d44a2b5 | "delete ％d chats?" without the number |
| TrackerControl | ja-rJP | plurals `n_companies_found` | `％d` | `eu/faircode/netguard/AdapterRule.java:323` `getQuantityString(R.plurals.n_companies_found, trackerCount, trackerCount)` @ 6264286 | the tracker-company count shown as "％d" |
| SimpleStorage (library) | ja | `ss_please_select_root_storage_primary_with_location` (the SD-card twin on line 6 is the same) | `％s` | `storage/.../SimpleStorageHelper.kt` (around line 206) `getString(resId, rootPath)` @ b3fce1d | the storage-access dialog without the path to pick. Apps that ship the library, or a copy of these strings (Thanox carries one), get the same text |
| APK Explorer & Editor | ar-rSA | 25 strings, e.g. `android_version`, `sdk_compile`, `sdk_minimum`, `delete_question` | `٪s` | `utils/ExternalAPKData.java:26, 29, 52-122`, `adapters/APKsAdapter.java:114` `getString(R.string.<name>, ...)` | APK details and prompts without the version, size or file name |

One more is mixed, not lost. EventFahrplan's Japanese
`schedule_parsing_error_with_version` writes `％s` and later an ASCII `%s`
(English: "Parsing error for schedule version %s", formatted at
`net/errors/ErrorMessage.kt:123` @ d403273). The version still appears, after a
stray "％s".

Found by the searches but not checked in code: Shevery (ckb and ug, about 80 lines),
Cashiro (fa, ks; noted in an earlier run), AniZen (ar), NewPipe and its fork
Tubular-Revived (ckb `progressive_load_interval_summary`), ShizukuHack (ar, a
link target `href="٪1$s"`), intra42, SmartPack PackageManager, Goodwy PlayBook,
kasahorow Keyboard, Ichaival (ja), chat-sdk (zh), andstatus (zh-rTW), Retro
Music forks (PureMusic, EffinMusic, Lost), and others in the `％s` list.

## Why checks miss it, and why it is new

- A check that compares placeholders between source and translation (Weblate's
  format checks, Crowdin QA, l10n-guard's `placeholder-missing`, the xDrip test
  added in NightscoutFoundation/xDrip#4762) sees `٪s` as "placeholder missing".
  So it is caught where such a check runs and someone reads it. None of these
  names the cause, though, and to the eye `٪s` and `％s` look like correct
  placeholders.
- Prior art we found: miguelaguiar01/corpus #1003/#1102 refuses `٪` and `％` in
  front of Qt's `%n`/`%1` markers (KeePassXC, Qt only). The Unicode list (2014)
  discusses U+066A as the percent sign used with Arabic-Indic digits. We found
  no write-up, issue or check about look-alike percent signs in
  Android/Java format strings, and no count of them.
- Not tested: what Android Lint (StringFormatCount, StringFormatMatches) reports
  for these strings.
- Not claimed: how these strings were made. Some files read like machine
  translation, but we have no evidence of which tool, if any, wrote them.

## Limits

- Sourcegraph indexes a subset of public repositories, skips forks and
  archives, and one `％s` stream stopped early. The counts are lower bounds for
  what it indexes, not for Android as a whole.
- "Confirmed" means read in code at the commit given. Nothing was run on a
  device, and we did not check which app releases contain these strings.
- Android picks a locale folder at runtime. A string in `values-ar-rSA` reaches
  users whose locale resolves to it, which may not be every Arabic user.

## Next

- Count this in MV2's census corpus (1.26 million F-Droid strings) instead of
  a search snapshot.
- Give l10n-guard a hint for it: when a placeholder is "missing" and the
  translation has `٪` or `％` right before a conversion or `n$`, say so.
