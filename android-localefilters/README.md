# android-localefilters: Android translations the app's own locale filter drops

`android_localefilters.py` is a small checker (Python standard library only, no network) for
Android apps built with Gradle. It finds translated `values-*` folders that the app's own
`resConfigs`, `resourceConfigurations` or `androidResources.localeFilters` list keeps out of
the APK or bundle. A community translator can add a language and see it merged, and nobody
gets an error or a warning. The language just never ships.

Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.

## What the build does (source reading, not a build test)

The Android Gradle Plugin hands these lists to aapt2's `-c` option. aapt2 decides which
locale folders to keep in `AxisConfigFilter::Match`
([`tools/aapt2/filter/ConfigFilter.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/tools/aapt2/filter/ConfigFilter.cpp),
Apache-2.0, read on 13 November 2026). A folder is kept only if:

1. its locale equals a filter entry exactly, or
2. the folder names a language with **no region and no variant**, a filter entry has the same
   language, and the scripts match (`ScriptsMatch`). A missing script is worked out from the
   language and region; if it can't be worked out, the scripts count as matching.

Folders with no locale (`values/`, `values-night/`) are always kept. Density entries such as
`xxhdpi` are ignored for this purpose. aapt2's parser (`libs/androidfw/Locale.cpp`) never
adds a script on its own, and it never reads `car` as a language.

What follows:

| Filter lists | Folder | Kept? | Why |
|---|---|---|---|
| `pt` | `values-pt-rBR` | **no** | A regional folder needs its own entry (`pt-rBR`). |
| `pt-rBR` | `values-pt` | yes | A language-only folder is kept by any entry of that language. |
| `zh` | `values-zh-rTW` | **no** | Same as `pt`. |
| `zh` | `values-b+zh+Hant` | **no** | The script of `zh` works out to `Hans`. |
| `zh-rTW` | `values-b+zh+Hant` | yes | The script of `zh-TW` works out to `Hant`. |
| `sr` | `values-b+sr+Latn` | **no** | The script of `sr` works out to `Cyrl`. |
| `en`, `de` | `values-fr` | **no** | Language not listed. |

The AGP docs mark `resourceConfigurations` as deprecated since 8.8, in favour of
`androidResources.localeFilters` ("Added in 8.8.2"). Both reach aapt2 the same way. Public
pull requests on AGP 8.11 (d4rken-org/porter #21) and 9.4 (sceneview/sceneview #3661) report two
more things. AGP passes the entries through unchanged, so a BCP-47 form like `en-US` or `pt-BR`
makes aapt2 stop with `invalid config ... for -c option`. And with
`generateLocaleConfig` on, the generated Android 13+ language list follows the same filter.

Nothing here was checked with a real build. MV2 published the same kind of checker for
[Flutter](../flutter-l10n/README.md), [VitePress](../vitepress-i18n/README.md),
[Sphinx](../sphinx-i18n/README.md) and [Starlight](../starlight-i18n/README.md).

## Prior art

Android lint's translation check (`TranslationDetector`) leaves out the locales a
`resConfigs` list filters, so it stays silent about exactly these folders. Some projects build
`localeFilters` from their `values-*` folders so the list can't drift (Porter #21 does this).
We found no published tool that checks a hand-written list against the folders with aapt2's
own matching rules, including the region and script cases above.

## What the checker reports

```
python android_localefilters.py <project root> [--json] [--strict]
```

It reads every `build.gradle` / `build.gradle.kts` that applies an Android application plugin
(a line naming `com.android.application`, or `android.application` / `android-application`
as in version catalogs and convention plugins). It also follows `project(":a:b")` dependencies
(transitively), because their translations are merged into the app and filtered with it. A
folder counts as a translation when one of its XML files has a `<string`, `<string-array` or
`<plurals` element.

| Kind | Meaning |
|---|---|
| `filtered_out` | A translated folder that the filter drops, with the reason: `language_not_listed`, `region_not_listed` or `script_mismatch`. |
| `declared_but_filtered` | A language listed in the manifest's `android:localeConfig` file for which no translated folder survives the filter. Android 13+ offers it in Settings, and the app then shows its default strings. |

Notes (not findings):

| Kind | Meaning |
|---|---|
| `dynamic_filter` | The list is built in code (a variable, a spread, string interpolation, `clear()` ...). The module is not judged. |
| `invalid_entry` | An entry in BCP-47 form (`en-US`, `zh-Hant`, `zh_CN`) that aapt2 is reported to reject. The remaining entries are still checked. |
| `not_modelled` | An entry for another qualifier axis (`night`, `fr-land`, the old `auto`). That variant is not judged. |

Entries in `defaultConfig` and `androidResources` apply to every variant. A product flavor's
own entries are added to them, and each such flavor is checked separately.
`--strict` exits 1 on any finding. The exit code is 2 when no application module is found.

## Limits

- Gradle files are read as text, not evaluated. Lists in convention plugins under
  `build-logic/` or `buildSrc/` (Kotlin source, not build files) are not read. `res.srcDirs`
  overrides and flavor-only source sets (`src/fdroid/res`) are not modelled: every
  `src/*/res` folder of the module counts for every variant.
- Project dependencies are found only through `project(":...")`, not through type-safe
  `projects.*` accessors. Modules are looked up next to the app module, then at the
  repository root.
- The likely-script table covers about 90 languages and their common regional exceptions
  (`zh-TW`, `sr-ME` and so on). For any other language with an explicit script folder the
  scripts count as matching, which can only hide a finding.
- `iw`/`he`, `in`/`id` and `ji`/`yi` are treated as the same language. aapt2 compares the
  codes as written, so a mix of the two can drop more than reported.
- Translations shipped by libraries from Maven (AppCompat and the like) are out of scope.

## Tests

`python -m unittest -v test_android_localefilters` covers folder and filter parsing, aapt2's
matching rules (region, script, unknown script, legacy codes), Groovy and Kotlin DSL files (with
comments, a `//` inside a string, flavors, `create("play")`, a list built from a variable, and
a read-only use), and a synthetic project. In that project an app module filters to `en`, `pt`,
`zh-rTW` and `xxhdpi`. That drops `values-pt-rBR`, `values-de` and a dependency module's
`values-ja`, keeps `values-pt` and `values-b+zh+Hant`, and reports `de` as declared in
`locales_config.xml` but filtered out.
