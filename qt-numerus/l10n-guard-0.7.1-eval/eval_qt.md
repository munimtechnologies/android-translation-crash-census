# l10n-guard 0.7.1 Qt check on real .ts files

| repository | file | seen by hand | commit | messages | finished | issues by code |
|---|---|---|---|---:|---:|---|
| bitcoin/bitcoin | src/qt/locale/bitcoin_ar.ts | ٪n in plural forms (49 lines) | 924f4c4ac7 | 854 | 850 | qt-count/error 66 |
| bitcoin/bitcoin | src/qt/locale/bitcoin_zh_TW.ts | ％n in a plural form (1 line) | 924f4c4ac7 | 1121 | 1117 | qt-count/error 1 |
| bitcoin/bitcoin | src/qt/locale/bitcoin_zh-Hant.ts | ％n in a plural form (1 line) | 924f4c4ac7 | 664 | 660 | qt-count/error 1 |
| bitcoin/bitcoin | src/qt/locale/bitcoin_de.ts | control | 924f4c4ac7 | 494 | 494 | none |
| keepassxreboot/keepassxc | share/translations/keepassxc_ar.ts | ٪n in plural forms (30 lines) | b05b0dd2e8 | 2501 | 2044 | qt-arg-missing/error 44, qt-count/error 38 |
| keepassxreboot/keepassxc | share/translations/keepassxc_de.ts | control | b05b0dd2e8 | 2501 | 2500 | none |
| pbek/QOwnNotes | src/languages/QOwnNotes_ur.ts | ٪n (4 lines) | 352ce1f460 | 2665 | 888 | qt-arg-missing/error 45, qt-count/error 4 |
| pbek/QOwnNotes | src/languages/QOwnNotes_ja.ts | ％n (6 lines) | 352ce1f460 | 2665 | 1091 | qt-arg-missing/error 37, qt-count/error 6 |
| OtterBrowser/otter-browser | resources/translations/otter-browser_ja.ts | ％n (3 lines) | b03cba7601 | 1925 | 1925 | qt-arg-missing/error 10, qt-count/error 3 |
| OpenOrienteering/mapper | translations/OpenOrienteering_zh_CN.ts | ％n (2 lines) | 7c4455de4b | 1657 | 1473 | qt-arg-missing/error 49, qt-arg-order/error 2, qt-count-missing/warning 2, qt-count/error 2 |

Plural-count issues, in full:

## bitcoin/bitcoin src/qt/locale/bitcoin_ar.ts

- ERROR [BitcoinGUI: Processed %n block(s) of transaction history.]: form 1: '٪ n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪ n' is shown as written
- ERROR [BitcoinGUI: Processed %n block(s) of transaction history.]: form 2: '٪ n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪ n' is shown as written
- ERROR [BitcoinGUI: Processed %n block(s) of transaction history.]: form 3: '٪ n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪ n' is shown as written
- ERROR [BitcoinGUI: Processed %n block(s) of transaction history.]: form 4: '٪ n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪ n' is shown as written
- ERROR [BitcoinGUI: Processed %n block(s) of transaction history.]: form 5: '٪ n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪ n' is shown as written
- ERROR [BitcoinGUI: Processed %n block(s) of transaction history.]: form 6: '٪ n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪ n' is shown as written
- ERROR [Intro: (%n GB needed for full chain)]: form 1: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [Intro: (%n GB needed for full chain)]: form 2: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [Intro: (%n GB needed for full chain)]: form 3: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [Intro: (%n GB needed for full chain)]: form 4: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [Intro: (%n GB needed for full chain)]: form 5: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [Intro: (%n GB needed for full chain)]: form 6: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [Intro: (of %n GB needed)]: form 1: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [Intro: (of %n GB needed)]: form 2: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [Intro: (of %n GB needed)]: form 3: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [Intro: (of %n GB needed)]: form 4: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [Intro: (of %n GB needed)]: form 5: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [Intro: (of %n GB needed)]: form 6: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n day(s)]: form 1: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n day(s)]: form 2: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n day(s)]: form 3: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n day(s)]: form 4: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n day(s)]: form 5: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n day(s)]: form 6: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n hour(s)]: form 1: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n hour(s)]: form 2: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n hour(s)]: form 3: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n hour(s)]: form 4: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n hour(s)]: form 5: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n hour(s)]: form 6: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n minute(s)]: form 1: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n minute(s)]: form 2: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n minute(s)]: form 3: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n minute(s)]: form 4: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n minute(s)]: form 5: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n minute(s)]: form 6: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n second(s)]: form 1: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n second(s)]: form 2: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n second(s)]: form 3: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n second(s)]: form 4: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n second(s)]: form 5: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n second(s)]: form 6: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n week(s)]: form 1: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n week(s)]: form 2: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n week(s)]: form 3: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n week(s)]: form 4: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n week(s)]: form 5: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n week(s)]: form 6: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [QObject: %n year(s)]: form 1: '٪ n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪ n' is shown as written
- ERROR [QObject: %n year(s)]: form 2: '٪ n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪ n' is shown as written
- ERROR [QObject: %n year(s)]: form 3: '٪ n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪ n' is shown as written
- ERROR [QObject: %n year(s)]: form 4: '٪ n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪ n' is shown as written
- ERROR [QObject: %n year(s)]: form 5: '٪ n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪ n' is shown as written
- ERROR [QObject: %n year(s)]: form 6: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [SendCoinsDialog: Estimated to begin confirmation within %n block...]: form 1: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [SendCoinsDialog: Estimated to begin confirmation within %n block...]: form 2: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [SendCoinsDialog: Estimated to begin confirmation within %n block...]: form 3: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [SendCoinsDialog: Estimated to begin confirmation within %n block...]: form 4: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [SendCoinsDialog: Estimated to begin confirmation within %n block...]: form 5: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [SendCoinsDialog: Estimated to begin confirmation within %n block...]: form 6: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [TransactionDesc: matures in %n more block(s)]: form 1: '٪ n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪ n' is shown as written
- ERROR [TransactionDesc: matures in %n more block(s)]: form 2: '٪ n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪ n' is shown as written
- ERROR [TransactionDesc: matures in %n more block(s)]: form 3: '٪ n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪ n' is shown as written
- ERROR [TransactionDesc: matures in %n more block(s)]: form 4: '٪ n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪ n' is shown as written
- ERROR [TransactionDesc: matures in %n more block(s)]: form 5: '٪ n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪ n' is shown as written
- ERROR [TransactionDesc: matures in %n more block(s)]: form 6: '٪ n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪ n' is shown as written

## bitcoin/bitcoin src/qt/locale/bitcoin_zh_TW.ts

- ERROR [Intro: (%n GB needed for full chain)]: form 1: '％n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '％n' is shown as written

## bitcoin/bitcoin src/qt/locale/bitcoin_zh-Hant.ts

- ERROR [Intro: (%n GB needed for full chain)]: form 1: '％n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '％n' is shown as written

## keepassxreboot/keepassxc share/translations/keepassxc_ar.ts

- ERROR [CsvImportWidget: [%n more message(s) skipped]]: form 1: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [CsvImportWidget: [%n more message(s) skipped]]: form 2: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [CsvImportWidget: [%n more message(s) skipped]]: form 3: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [CsvImportWidget: [%n more message(s) skipped]]: form 4: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [CsvImportWidget: [%n more message(s) skipped]]: form 5: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [CsvParserModel: %n row(s)]: form 1: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [CsvParserModel: %n row(s)]: form 2: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [CsvParserModel: %n row(s)]: form 3: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [CsvParserModel: %n row(s)]: form 4: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [CsvParserModel: %n row(s)]: form 5: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [DatabaseSettingsWidgetBrowser: Successfully removed %n encryption key(s) from ...]: form 1: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [DatabaseSettingsWidgetBrowser: Successfully removed %n encryption key(s) from ...]: form 2: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [DatabaseSettingsWidgetBrowser: Successfully removed %n encryption key(s) from ...]: form 3: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [DatabaseSettingsWidgetBrowser: Successfully removed %n encryption key(s) from ...]: form 4: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [DatabaseSettingsWidgetBrowser: Successfully removed %n encryption key(s) from ...]: form 5: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [DatabaseSettingsWidgetBrowser: Successfully removed permissions from %n entry(s).]: form 1: '٪ n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪ n' is shown as written
- ERROR [DatabaseSettingsWidgetBrowser: Successfully removed permissions from %n entry(s).]: form 2: '٪ n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪ n' is shown as written
- ERROR [DatabaseSettingsWidgetBrowser: Successfully removed permissions from %n entry(s).]: form 3: '٪ n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪ n' is shown as written
- ERROR [DatabaseSettingsWidgetBrowser: Successfully removed permissions from %n entry(s).]: form 4: '٪ n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪ n' is shown as written
- ERROR [DatabaseSettingsWidgetBrowser: Successfully removed permissions from %n entry(s).]: form 5: '٪ n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪ n' is shown as written
- ERROR [DatabaseSettingsWidgetMaintenance: Purged %n icon(s) from the database.]: form 1: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [DatabaseSettingsWidgetMaintenance: Purged %n icon(s) from the database.]: form 2: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [DatabaseSettingsWidgetMaintenance: Purged %n icon(s) from the database.]: form 3: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [DatabaseSettingsWidgetMaintenance: Purged %n icon(s) from the database.]: form 4: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [DatabaseSettingsWidgetMaintenance: Purged %n icon(s) from the database.]: form 5: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [EditWidgetIcons: %n icon(s) already exist in the database]: form 1: '٪ n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪ n' is shown as written
- ERROR [EditWidgetIcons: %n icon(s) already exist in the database]: form 4: '٪ n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪ n' is shown as written
- ERROR [EditWidgetIcons: %n icon(s) already exist in the database]: form 5: '٪ n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪ n' is shown as written
- ERROR [FdoSecrets::Service: %n Entry(s) was used by %1]: form 1: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [FdoSecrets::Service: %n Entry(s) was used by %1]: form 2: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [FdoSecrets::Service: %n Entry(s) was used by %1]: form 3: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [FdoSecrets::Service: %n Entry(s) was used by %1]: form 4: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [FdoSecrets::Service: %n Entry(s) was used by %1]: form 5: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [TotpDialog: Expires in <b>%n</b> second(s)]: form 1: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [TotpDialog: Expires in <b>%n</b> second(s)]: form 2: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [TotpDialog: Expires in <b>%n</b> second(s)]: form 3: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [TotpDialog: Expires in <b>%n</b> second(s)]: form 4: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [TotpDialog: Expires in <b>%n</b> second(s)]: form 5: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written

## pbek/QOwnNotes src/languages/QOwnNotes_ur.ts

- ERROR [FakeVim: %n lines moved.]: form 1: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [FakeVim: %n lines moved.]: form 2: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [FakeVim: %n lines filtered.]: form 1: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written
- ERROR [FakeVim: %n lines filtered.]: form 2: '٪n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '٪n' is shown as written

## pbek/QOwnNotes src/languages/QOwnNotes_ja.ts

- ERROR [LocalTrashDialog: <strong>%n</strong> note(s) were restored]: form 1: '％n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '％n' is shown as written
- ERROR [LocalTrashDialog: <strong>%n</strong> note(s) were removed]: form 1: '％n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '％n' is shown as written
- ERROR [QObject: A change of the note path was detected. Would y...]: form 1: '％n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '％n' is shown as written
- ERROR [QObject: …and %n more note(s)]: form 1: '％n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '％n' is shown as written
- ERROR [ServerBookmarksImportDialog: <strong>%n bookmarks</strong> found on server]: form 1: '％n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '％n' is shown as written
- ERROR [WebSocketServerService: %n bookmark(s) created]: form 1: '％n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '％n' is shown as written

## OtterBrowser/otter-browser resources/translations/otter-browser_ja.ts

- ERROR [Otter::AddonsContentsWidget: You are about to irreversibly remove %n addon(s).]: form 1: '％n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '％n' is shown as written
- ERROR [Otter::PasswordsContentsWidget: You are about to delete %n password(s).]: form 1: '％n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '％n' is shown as written
- ERROR [Otter::TabBarWidget: You are about to open %n URL(s).]: form 1: '％n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '％n' is shown as written

## OpenOrienteering/mapper translations/OpenOrienteering_zh_CN.ts

- WARNING [OpenOrienteering::MapEditorController: Copied %n object(s)]: no plural form shows the count (%n)
- WARNING [OpenOrienteering::MapEditorController: Pasted %n object(s)]: no plural form shows the count (%n)
- ERROR [OpenOrienteering::MapEditorController: Duplicated %n object(s)]: form 1: '％n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '％n' is shown as written
- ERROR [OpenOrienteering::OgrFileImport: Unable to load %n objects, reason: %1]: form 1: '％n' is not %n; Qt replaces only an ASCII %n or %Ln with the count, so '％n' is shown as written
