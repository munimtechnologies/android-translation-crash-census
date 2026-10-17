# Qt plural counts written ％n or ٪n: three more projects

MV2 of Munim, Inc., made with AI agents, 2026-10-17. Text CC BY 4.0.

[FINDINGS.md](FINDINGS.md) describes Bitcoin Core's Arabic and Chinese plural forms that write
the count as `٪n` (Arabic percent sign, U+066A) or `％n` (fullwidth, U+FF05). Qt replaces only
an ASCII `%n` or `%Ln` in a plural (numerus) message, so these forms show the text `％n` where
the number should be. lupdate marks a message `numerus="yes"` only when the code passes a count
to `tr()`, so each case below is a message that is given a number and never shows it.

A test build of l10n-guard 0.7.0 (all tests passed in a sealed container on 2026-10-17; release
pending), run on ten real .ts files ([evaluation](l10n-guard-0.7.0-eval/eval_qt.md)), found the
same in three more projects. Every line below was read again in the project's file
through a Sourcegraph search on 2026-10-17, at the commit given.

| project | file, commit | plural messages | example |
|---|---|---:|---|
| QOwnNotes | `src/languages/QOwnNotes_ja.ts`, 352ce1f460 | 6 | `…さらに％n個のメモ` (…and %n more note(s)) |
| QOwnNotes | `src/languages/QOwnNotes_ur.ts`, 352ce1f460 | 2 (4 forms) | FakeVim `%n lines moved.` / `%n lines filtered.` with `٪n` |
| Otter Browser | `resources/translations/otter-browser_ja.ts`, c72f79215f | 3 | `％n個のパスワード(s)を削除しようとしています。` (You are about to delete %n password(s).) |
| OpenOrienteering Mapper | `translations/OpenOrienteering_zh_CN.ts`, 7c4455de4b | 2 | `无法加载％n个对象，原因：％1` (Unable to load %n objects, reason: %1) |

Japanese and Chinese have a single plural form, so in these files the count never appears at
all. The Otter Browser confirmation dialogs (remove add-ons, delete passwords, open URLs) ask the
user to confirm an action without saying how many items it affects. Two of the messages also
write their `arg()` marker as `％1`/`％2`, which Qt does not fill either (QOwnNotes' note-path
dialog and Mapper's load error), so the file name or reason is lost as well.

The fix in each case is to type the ASCII `%` again (`％n` to `%n`), in the project's own
translation workflow. No issue about these strings was found in the three projects' GitHub
issues on 2026-10-17. Nothing was run in the apps; the effect follows from Qt's
`QCoreApplication::translate` plural handling described in FINDINGS.md.

Earlier work: the translation workbench [corpus](https://github.com/miguelaguiar01/corpus/pull/1102)
found `٪n` in KeePassXC's Arabic file first.

## Check your own files

Once l10n-guard 0.7.0 is released ([releases](https://github.com/munimtechnologies/l10n-guard/releases)),

```sh
python3 l10n_guard.py qt translations/app_ja.ts
```

reports each such form as `ERROR qt-count`.
