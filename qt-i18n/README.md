# qt-i18n: Qt translation files that QTranslator::load never tries

`qt_l10n.py` is a small checker (Python standard library only, no network) for Qt apps in C++
or Python (PyQt/PySide). It finds `.ts` / `.qm` translation files whose locale part the app's
own `QTranslator::load` call can never build. Qt gives no error or warning for these: `load()`
returns false, and the app stays in its source language. A community translator can add the
file, see it merged and released, and the language never appears.

Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.

## What Qt does (source reading, not a build test)

Read on 13 November 2026 from qtbase `src/corelib/kernel/qtranslator.cpp`,
`src/corelib/text/qlocale.cpp` and the Qt 6 `QLocale` / `QTranslator` docs (Qt is LGPL/GPL/
commercial; nothing from it is copied here).

**Style A, the string overload with `QLocale::name()`.** Many apps (and older Qt tutorials) do
`load("myapp_" + QLocale::system().name(), dir)`. The Qt docs say `name()` is
`language_territory` and that it never includes a script, "even if the QLocale object was
constructed with an explicit script". The string overload tries that name with `.qm`, then
without, then cuts it at the rightmost `_` or `.` and tries again. It never lowercases. So on a
Chinese (China) system it tries `myapp_zh_CN`, `myapp_zh`, `myapp`, and **never `myapp_zh_Hans`**.

**Style A2: the same, cut to the language first** (`.left(2)`, `[:2]`, `.split('_')[0]`,
`.section('_', 0, 0)`). Only `myapp_pt` is tried, never `myapp_pt_BR`.

**Style B, the QLocale overload** (`load(QLocale(), "myapp", "_", dir)`, which KDAB and the Qt
docs recommend). It tries each `QLocale::uiLanguages()` entry joined with `_` (and in lowercase).
The docs' example list for US English is `en-Latn-US`, `en-US`, `en-Latn`, `en`, so script forms
are tried. Since Qt 6.9 truncations are added too. A `QQmlApplicationEngine` loads
`i18n/qml_<lang>.qm` this way.

| File | A (`name()`) | A2 (language only) | B (`QLocale`) | Why |
|---|---|---|---|---|
| `app_pt_BR` | yes | **no** | yes | A2 only tries `pt`. |
| `app_zh_Hans`, `app_sr_Latn` | **no** | **no** | yes | `name()` never has a script. |
| `app_pt-BR` | **no** | **no** | **no** | Qt joins with `_` only. |
| `app_sr@latin`, `app_ca@valencia` | **no** | **no** | **no** | Qt locale names have no `@` modifier (a gettext/glibc form). |
| `app_pt_br` | **no** on Linux and in `:/` resources | **no** | yes | The string overload never lowercases. |
| `app_no` (also `iw`, `in`, `ji`, `tl`, `sh`, `mo`) | **no** | **no** | not judged | QLocale reads `no` as Norwegian Bokmål and names it `nb`. |

The Weblate and Crowdin habit of naming Chinese files `zh_Hans` / `zh_Hant` is the case most
likely to bite: with style A, Chinese users on a `zh_CN` or `zh_TW` system get the
source-language interface.

## Prior art

KDAB's post "Fixing a common antipattern when loading translations in Qt" and the Qt docs
already tell people to use the QLocale overload instead of `QLocale::system().name()`, and a
PythonGUIs FAQ covers `load()` returning false. We found no published tool that checks which of a
project's translation files its load call can actually reach, nor any write-up of the script-code
(`zh_Hans`) and lowercase cases above. A web search on 13 November 2026 found no clazy check for
it either.

## What the checker reports

```
python qt_l10n.py <project root> [--json] [--strict]
```

It groups translation files by folder and file-name prefix (`myapp_`), skipping Qt's own catalogs
(`qt_`, `qtbase_` ...) and TypeScript `.ts` files (a Qt `.ts` file has a `<TS` element). It reads
`.cpp/.h/.mm/.py` files that mention `QTranslator`, finds each `.load(...)` call, classifies it
as A, A2 or B, and ties it to a file group through the string literals in the call (or one
assignment the call uses, `QString locale = QLocale::system().name();`). If no literal matches and
the project uses only one load style, that style is used.

| Kind | Meaning |
|---|---|
| `script_code` | `zh_Hans`, `sr_Latn` ... with style A or A2. |
| `hyphen` | `pt-BR` with any style. |
| `modifier` | `sr@latin` with any style. |
| `case` | `pt_br` with style A: missed on case-sensitive file systems and in Qt resources (`:/`). |
| `legacy_code` | `no`, `iw`, `in` ... with style A or A2. |
| `region_code` | `pt_BR` with style A2. |

When a group is tied to calls of two styles, a file is a finding only if every style misses it.
Notes (not findings): `not_modelled` (a `bcp47Name()` call or a hand-written `uiLanguages()`
loop) and `no_load_call_found`. `--strict` exits 1 on any finding; the exit code is 2 when no
translation files are found.

## Limits

- Source is read as text. Only one assignment step is followed (`lang = locale[:2]` after
  `locale = ...name()` is not resolved), and `self.locale`-style attributes are not followed.
  Calls the checker cannot classify are left out, which can only hide findings.
- The `.qm` file is assumed to keep the `.ts` file's base name (true for `qt_add_translations`
  and qmake's default). Renames in CMake or resource aliases (`<file alias=...>`) are not read.
- The file-name prefix is guessed per folder: first a prefix that a load call names, then the
  most common one. A lone `tr_de.ts` with no call naming `tr` is read as code `tr_de`.
- That `name()` writes `nb` for `no` (and so on) is read from the legacy table in
  `QLocalePrivate::codeToLanguage`, not run.
- Which script and truncated forms `uiLanguages()` lists depends on the Qt version and the
  platform, so style B is judged only for `-` and `@`.
- Nothing here was checked against a running Qt app.

MV2 published the same kind of checker for [Android locale filters](../android-localefilters/README.md),
[Flutter](../flutter-l10n/README.md), [VitePress](../vitepress-i18n/README.md),
[Sphinx](../sphinx-i18n/README.md) and [Starlight](../starlight-i18n/README.md).

## Tests

`python -m unittest -v test_qt_l10n` covers file-name splitting (including the ambiguous `tr_de`),
every finding kind for each style, comment stripping, call classification (C++ and Python,
f-strings, a QLocale variable, `bcp47Name`, a non-translator `load`), and three synthetic
projects. In the first, a C++ app loads `":/i18n/app_%1"` with `QLocale::system().name()`:
`zh_Hans`, `zh_Hant`, `pt-PT`, `sr@latin` and `no` are reported, while `de`, `pt_BR` and `es_419`
are not, and the TypeScript `web/de.ts` and Qt's `qt_de.ts` are ignored. In the second, a PyQt app
uses the QLocale overload for `viewer_*` (only `pt-BR` is reported) and `[:2]` for `plugin_*`
(only `pt_BR` is reported). The third covers a QML `i18n/qml_*.qm` folder and a folder no call
loads.
