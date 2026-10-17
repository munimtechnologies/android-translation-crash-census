# qt-numerus: plural counts Qt never fills (٪n and ％n)

MV2 of Munim, Inc., made with AI agents, 2026-10-17. Text CC BY 4.0. Read in source and in
translation files; not run on a device. Nothing here has been reported to the projects yet.

## The rule

A Qt plural ("numerus") message is fetched with `tr("%n day(s)", "", n)`. Before returning the
translation, `QCoreApplication::translate` calls `replacePercentN`, which looks for the ASCII
percent sign only (`u'%'` in qtbase dev, `QLatin1Char('%')` in 5.15) followed by `n` or `Ln`,
and puts the number there. So a translation that writes the count with another percent sign,
such as the Arabic percent sign `٪` (U+066A) or the fullwidth `％` (U+FF05), or with a space
(`٪ n`), shows that text instead of the number, in every count that uses that form.

qt-args 0.1.0 (the place-marker census in `../qt-args/`) skips plural messages, so it does not
count these.

## Bitcoin Core (read on master, 2026-10-17; code at 924f4c4ac78b)

`src/qt/locale/bitcoin_ar.ts`: 11 plural messages write the count with `٪`, in all 6 of their
Arabic forms (66 forms: 49 written `٪n`, 17 written `٪ n`; literal Sourcegraph searches):

| English source | where Bitcoin Core shows it |
|---|---|
| `%n second(s)`, `%n minute(s)`, `%n hour(s)`, `%n day(s)`, `%n week(s)`, `%n year(s)` | `GUIUtil::formatNiceTimeOffset`: the "behind" text while syncing (bitcoingui.cpp), the time left in the sync overlay (modaloverlay.cpp), and the fee confirmation-target list (sendcoinsdialog.cpp) |
| `(%n GB needed for full chain)`, `(of %n GB needed)` | the disk-space line of the first-run dialog (intro.cpp, `UpdateFreeSpaceLabel`) |
| `Processed %n block(s) of transaction history.` | the sync progress tooltip (bitcoingui.cpp line 1215) |
| `Estimated to begin confirmation within %n block(s).` | the send dialog (SendCoinsDialog context) |
| `matures in %n more block(s)` | transaction details of an immature mined coin (transactiondesc.cpp line 183) |

Ten of the eleven were checked in the code: each is a `tr(..., "", count)` call (guiutil.cpp,
intro.cpp, bitcoingui.cpp, transactiondesc.cpp). The send-dialog string is named from its .ts
context only.

Chinese: one plural message in each of `bitcoin_zh.ts`, `bitcoin_zh-Hans.ts`, `bitcoin_zh-Hant.ts`,
`bitcoin_zh_TW.ts`, `bitcoin_zh_HK.ts`, `bitcoin_cmn.ts`, `bitcoin_yue.ts` and `bitcoin_hak.ts` writes
`％n` (fullwidth), for example `（完整區塊鏈需要％n GB）` for `(%n GB needed for full chain)`.
Chinese has one plural form, so the number is missing for every count. All nine files (Arabic
and the eight Chinese ones) are listed in `src/qt/bitcoin_locale.qrc`, so they are built in.

### Why Bitcoin Core's own check lets it through

Translations are pulled from Transifex by `update-translations.py`
(bitcoin-core/bitcoin-maintainer-tools), which drops any translation whose format specifiers
differ from the source, with one exception, quoted from `check_format_specifiers`:

```python
if numerus and source_f == (set(), ['n']) and translation_f == (set(), []) and translation.find('%') == -1:
    # Allow numerus translations to omit %n specifier (usually when it only has one possible value)
    return True
```

The exception is meant for forms such as "one day" that spell the number out. `٪n` and `％n`
contain no ASCII `%`, so they look like a form that dropped the count on purpose and pass.

The same Chinese line is in at least 11 other repositories built from Bitcoin Core's
translations (Elements, Qtum, Xaya and others; Sourcegraph, forks and archives excluded).

## Prior art

- miguelaguiar01/corpus [#1003](https://github.com/miguelaguiar01/corpus/issues/1003) /
  [#1102](https://github.com/miguelaguiar01/corpus/pull/1102) (2026-09-30 / 10-01) found `٪n` in
  KeePassXC's Arabic file (30 forms over 6 messages, for example `%n row(s)`) and made its
  workbench refuse a look-alike percent before `n`, `L` or a digit. It names no Bitcoin Core
  file and no fullwidth `％n` case.
- No Bitcoin Core or bitcoin-core/gui issue about this was found (searches for "arabic" and for
  `%n` translation placeholders, 2026-10-17), and no Qt bug report about `％n`.

What is new here: the Bitcoin Core cases, the fullwidth `％n` cases in Chinese, and the reason a
specifier check passes them (an exemption keyed on the absence of an ASCII `%`).

## Other search hits (not checked in code)

Literal Sourcegraph searches of `.ts` files, 2026-10-17: `％n` in QOwnNotes (ja 6 lines, zh_TW 2),
Otter Browser (ja 3), OpenOrienteering Mapper (zh_CN 2) and theDesk (zh_CN 1); `٪n` in QOwnNotes
(ur 4). Each still needs its code read before it is called a bug.

## Checking for it

l10n-guard 0.7.0 (`python3 l10n_guard.py qt app_ar.ts`, in testing) reports a count written `٪n`,
`％n` or `% n`, and a `%1` where the source has only `%n`, as an error. The fix in a translation
is to write the ASCII `%n`. A checker that exempts plural forms without a count should also
require that the form contains no `٪`, `％` or `﹪` directly before `n`.

## Limits

- The Arabic and Chinese texts were found by literal search and read through a web reader;
  right-to-left text around placeholders can display out of order, so the counts above rest on
  the literal searches, not on the rendered lines.
- Nothing was run. The display claim follows from `replacePercentN` and the `tr(..., n)` calls
  quoted above.
- The search index excludes forks and archived repositories and may lag the default branch.
