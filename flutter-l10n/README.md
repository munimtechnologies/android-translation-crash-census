# flutter-l10n: Flutter translations the app or a platform leaves out

`flutter_l10n.py` is a small checker (Python standard library only, no network) for Flutter
apps that translate with ARB files (`flutter gen-l10n`, or `intl_utils`). It finds translations
that the app's own `supportedLocales` list never selects, languages the app lists with no ARB
file behind them, and languages that the iOS project or the Android 13+ language list doesn't
declare. Flutter accepts all of these with no error, and with no warning at build time.

Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.

## What Flutter does (source reading, not a build test)

Read in [flutter/flutter](https://github.com/flutter/flutter) `master` on 13 November 2026
(BSD-3-Clause) and in Flutter's
[Internationalizing Flutter apps](https://docs.flutter.dev/ui/internationalization) page.

| Step | Source | Behaviour |
|---|---|---|
| An ARB file's locale | `packages/flutter_tools/lib/src/localizations/gen_l10n_types.dart` (`AppResourceBundle`) | `@@locale` if set. Otherwise the whole file name is parsed as a locale, then the text after each `_`; the first parse whose language is in gen-l10n's ISO 639-1 list (plus `fil` and `gsw`) wins. `app_pt_BR.arb` is `pt_BR`. Only files directly in `arb-dir` are read. |
| Which ARB a locale gets | `gen_l10n_templates.dart` (`lookupAppLocalizations`) | Language + script + country, then language + script, then language + country, then language alone. Matching is exact and case-sensitive. |
| When the class loads at all | `gen_l10n_templates.dart` (the delegate's `isSupported`) | Only for a language that has an ARB file. For any other language `AppLocalizations` isn't loaded, so `AppLocalizations.of(context)` returns null. |
| Which locale the app uses | `packages/flutter/lib/src/widgets/app.dart` (`basicLocaleListResolution`) | Always one of `supportedLocales`, or `supportedLocales.first`. The default is `const <Locale>[Locale('en', 'US')]`. |
| iOS | Flutter docs, "Localizing for iOS" | Add the supported languages in Xcode (`knownRegions` in `ios/Runner.xcodeproj/project.pbxproj`), "This ensures your entry in the App Store correctly displays the supported languages." |
| Android 13+ | Android's per-app language docs | The system language picker offers exactly the `<locale>` entries of the file named by `android:localeConfig`. |

Put together:

- **A translation outside a hand-written `supportedLocales` list never shows.** With ARB files
  for `zh` and `zh_Hant` and `supportedLocales: [Locale('en'), Locale('zh', 'TW')]`, Taiwan
  users resolve to `zh_TW`, which looks up `zh`: the Traditional Chinese file is unused.
  The same happens to `pt_BR` when the list has only `Locale('pt')`. Using the generated
  `AppLocalizations.supportedLocales` avoids this.
- **A language in that list with no ARB file** never loads `AppLocalizations`, so a `!` on
  `AppLocalizations.of(context)` throws.
- **An app that never passes `supportedLocales`** supports only `en_US`; no other translation
  is ever chosen.
- **A language missing from `knownRegions`** is not shown in the App Store's language list. If
  the app sets `CFBundleLocalizations` in `Info.plist`, a language missing from it is reported
  too, because Apple reads that key as the list of localizations the app handles.
- **A language missing from `locales_config.xml`** can't be picked in Android 13+'s per-app
  language settings.

Nothing here was checked with a real Flutter build or on a device. MV2 published the same kind of
checker for [VitePress](../vitepress-i18n/README.md), [Sphinx](../sphinx-i18n/README.md) and
[Starlight](../starlight-i18n/README.md).

## Prior art

Blog posts at flutterlocalisation.com and lingohub.com explain that ARB files, `Info.plist`
and `knownRegions` must agree, and one post gives a short Dart script for the `Info.plist`
part. We found no published tool that checks hand-written `supportedLocales` lists against the
generated lookup, or that checks iOS and Android together.

## What the checker reports

```
python flutter_l10n.py <project root> [--arb-dir lib/l10n] [--template-arb-file app_en.arb] [--strict]
```

The ARB folder and template come from `l10n.yaml`, then from the `flutter_intl` section of
`pubspec.yaml`, else `lib/l10n` and `app_en.arb`. Each ARB file gets a status:

| Status | Meaning | Counted as a translation? |
|---|---|---|
| `ok` | At least one message differs from the template (or it is the template). | yes |
| `empty` | No messages of its own. | no |
| `same_as_template` | Every message equals the template's. | no |
| `conflict` | `@@locale` disagrees with the file name (gen-l10n stops with an error). | no |
| `no_locale` | No `@@locale` and no locale in the file name (gen-l10n stops with an error). | no |
| `invalid_json` | Not a JSON object. | no |

Findings:

| Kind | Meaning |
|---|---|
| `unreachable` | A translation no entry of the hand-written `supportedLocales` list looks up. Only reported when every `supportedLocales:` argument under `lib/` is a complete list of `Locale(...)` / `Locale.fromSubtags(...)` literals (followed to a variable if needed) and no `localeResolutionCallback` or `localeListResolutionCallback` is set. |
| `unsupported_language` | A listed locale whose language has no ARB file. |
| `default_supported_locales` | No `supportedLocales:` argument anywhere under `lib/`, but a `MaterialApp`, `CupertinoApp` or `WidgetsApp` exists: every translation that `en_US` doesn't look up. |
| `ios_not_declared` | A translated language with no `knownRegions` entry for that language. |
| `plist_not_declared` | The same for `CFBundleLocalizations`, only when `Info.plist` sets it. |
| `android_not_declared` | The same for the `android:localeConfig` file, only when the manifest names one. |

Languages are compared by primary language only (`es` matches `es-419`; `iw`, `in` and `ji`
count as `he`, `id` and `yi`), so a finding means the language is missing outright.
Declared languages with no translation are listed as `no_translation` but are not findings,
because an app can have native strings of its own. `--strict` exits 1 on any finding; the exit
code is 2 when there is no `pubspec.yaml` or no ARB folder.

## Limits

- Dart is read as text, not analysed. A list built in code, spread from another list, or
  passed in from a package is not judged. `supportedLocales:` arguments in widgets other than
  the app widget are read as if they were the app's. Files ending `.g.dart`, `.freezed.dart`,
  `.gr.dart` and gen-l10n's own output are skipped.
- The lookup model follows gen-l10n. `intl_utils` (`S.delegate`) builds a similar lookup; its
  source was not read.
- ARB locales are written in canonical case (`zh_Hant`, `pt_BR`); a raw `@@locale` such as
  `pt_br` is treated as `pt_BR`.
- iOS: only `ios/Runner.xcodeproj` and `ios/Runner/Info.plist`; macOS is not checked. Whether
  a missing `CFBundleLocalizations` entry changes anything at run time was not tested.
- Android: a `localeConfig` generated by the Android Gradle Plugin (`generateLocaleConfig`) is
  noted, not modelled.
- Apps that translate with `easy_localization`, `slang` or other JSON/YAML systems are out of
  scope; a `supportedLocales:` inside a file that uses `EasyLocalization(` is skipped.

## Tests

`python -m unittest -v test_flutter_l10n` builds synthetic projects in a temporary folder: a
literal list that strands `pt_BR` and `zh_Hant` and names a language with no ARB file (with a
commented-out list and a string holding `)` and `,`); a list in a `const` in another file; a
custom resolution callback; an app with no `supportedLocales`; `knownRegions`,
`CFBundleLocalizations` (with `iw`) and an Android `localeConfig` with a commented-out entry;
`flutter_intl` settings; and broken ARB files.
