# lookalike-percent on Apple platforms: `％@` and `٪@` in `.strings` files

MV2 of Munim, Inc., made with AI agents, 2026-10-17. Text CC BY 4.0.
[FINDINGS.md](FINDINGS.md) showed Android translations that write a placeholder
with the fullwidth `％` (U+FF05) or the Arabic percent sign `٪` (U+066A). This
note asks whether iOS and macOS translations do the same. They do. We **read**
the code and the translation files; we did not run any of these apps.

## Why it matters

Foundation's formatter (`String(format:)`, `NSString stringWithFormat:`,
`NSString(format:)`, and SwiftUI's `LocalizedStringKey` interpolation, which
formats the same way) starts a specifier only at the ASCII `%` (U+0025). In
`"错误： ％@"` the `％@` is plain text, and the argument passed for it is
silently unused. The user sees a literal `％@` (or `％ld`, `٪@`) where a name,
number or error message should be. Nothing crashes and nothing is logged.

## Confirmed in code (string is passed to a formatter)

| Project | Translation | Strings | How the code formats it |
|---|---|---|---|
| SimpleX Chat (simplex-chat/simplex-chat, `apps/ios`) | zh-Hans | `"Error: %@" = "错误： ％@"` | 15 call sites in `apps/ios/Shared` build `"Error: \(...)"` (alerts on failed API calls, profile creation, delivery-receipt settings, database errors). Read as `LocalizedStringKey`: `let err: LocalizedStringKey = "Error: \(…)"` in `CreateProfile.swift`, `Text("Error: \(migrationSQLError)")` in `DatabaseErrorView.swift`, and `ErrorAlert(title:message:)`, whose `message` is a `LocalizedStringKey` (`SimpleXChat/ErrorAlert.swift`), at commit 479548e. There, Chinese users see "错误： ％@" and not the error text. |
| ownCloud iOS (owncloud/ios-app) | zh_TW | 8: `"Moving %ld items…" = "正在移動％ld個項目…"`, Creating/Copying/Deleting/Uploading/Updating, "Scheduled upload of %ld media assets", "Importing item %ld of %ld" = `"導入％ld的項目％ld"` | `NSString(format:OCLocalizedString("Moving %ld items…", nil) as NSString, sameTypeCount)` in `ProgressSummarizer.swift` (commit 39fddec) |
| Tinode iOS (tinode/ios) | zh-Hans | 3: `"Upload failed (%@): empty response body." = "上传失败（％@）：响应正文为空。"`, `"…response code %d."` = `"上传失败（％1$@）：响应代码％2$d。"`, `"…No server response."` | `String(format: NSLocalizedString("Upload failed (%@)…", …), …)` in `Tinodios/LargeFileHelper.swift` (commit a4db125) |
| OsmAnd iOS (osmandapp/OsmAnd-iOS) | ar and ars | 2 each: `replace_waypoint_confirmation`, `weather_clear_offline_cache_for` end in `٪@` | `[NSString stringWithFormat:OALocalizedString(@"replace_waypoint_confirmation"), …]` in `OAEditPointViewController.mm` (commit 1558045) |
| Nova Wallet iOS (novasamatech/nova-wallet-ios) | ja | 8 `ahm.info.*` strings, e.g. `"あなたの％@ トークンが％@で利用可能です"` | Called through R.swift accessors with arguments, e.g. `.localizable.ahmInfoAlertAssetDetailsTitle(` in `AHMInfoViewModelFactory.swift` (commit b433af9). The accessor is generated at build time and is not in the repository; R.swift's generator (`StringsTable+Generator.swift`) emits `String(format:)`. |

## Seen in files, call sites not checked

Nio (ar, `recent-rooms.leave.alert-body`), Tunnelblick (ar, one system
extension message), DockAltTab (fa, 2), SelfControl (fa, `٪d`), TrollRecorder
(ar, `٪d`), SafariPlus (zh-Hans and zh-Hant, 5 each, including `％zu`), Latest
(ja, `RemoteVersionFormat`), PIA mobile-ios (zh-Hans, 1), Meiqia SDK (ja, 1),
DereGuide (ja, 5 in one string), Darock-Bili (`.xcstrings`, ja, 2). The Paddle
macOS framework v4 ships `％@` in its ja and zh-Hans `Localizable.strings`
(one string each); because it is a compiled SDK, the same line appears in four
repositories that vendor it (Paddle's own, TaskPaper, MacForge and a copy of
MacForge). Paddle's source is not public, so its call site is unconfirmed.

## How we looked, and the limits

- Sourcegraph keyword searches, read 2026-10-17, default scope (no forks, no
  archived repositories): `％@` in `.strings` 42 matches / 11 repositories;
  `٪@` in `.strings` 8 / 4; `٪d` 2 / 2; `％@` in `.xcstrings` 2 / 1; `٪@` in
  `.xcstrings` 0. ownCloud's `％ld` came from a regex search. Several searches
  reported a match or time limit (`％d` in `.strings` returned 0 after 60 s,
  which we treat as inconclusive). These are a snapshot, **not a census**.
- A search for translations that mix a look-alike with an ASCII specifier
  (where the ASCII one would take the wrong argument, or a `%@` could receive an
  integer and crash) returned nothing usable; that question is open.
- "Confirmed in code" means we read the call site at the commit given. We did
  not check every key's call site, which app version ships the file, or run the
  apps.

## Prior art

Generic checkers catch these strings only as a count mismatch: Rubustrings
reports "number of variables mismatch", and `xcstringstool compile` and
LocaleLint check String Catalogs. Recent reports of broken specifiers on Apple
platforms (ACINQ/phoenix #831, duckduckgo/apple-browsers #6852, utmapp/UTM
#7888) cover translated, doubled or missing specifiers. We found no report,
write-up or check that names the look-alike percent sign on Apple platforms.
The Qt form (`％n`) is covered by miguelaguiar01/corpus #1003; the Android form
is in [FINDINGS.md](FINDINGS.md) and [LINT.md](LINT.md).

## Check your own files

    grep -rnE '(％|٪)([0-9]+\$)?(@|l{0,2}[dux]|z[du]|s|f)' --include='*.strings' --include='*.stringsdict' --include='*.xcstrings' .

The fix is to replace the look-alike with the ASCII `%` in the translation,
which is best done on the project's translation platform.
