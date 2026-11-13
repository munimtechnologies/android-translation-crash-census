# android-localefilters: Android translations the app's own locale filter drops

`android_localefilters.py` is a small checker (Python standard library only, no network) for
Android apps built with Gradle. It finds translated `values-*` folders that the app's own
`resConfigs`, `resourceConfigurations` or `androidResources.localeFilters` list keeps out of
the APK or bundle. A community translator can add a language and see it merged, and nobody
gets an error or a warning. The language just never ships.

Since 0.2.0 it also reads [moko-resources](https://github.com/icerockdev/moko-resources)
(Kotlin Multiplatform) locale folders, and reports the ones whose script is lost on Android.

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

## moko-resources: the script of a locale folder is lost on Android

moko-resources keeps shared strings in `src/<sourceSet>/moko-resources/<locale>/strings.xml`
(`src/<sourceSet>/resources/MR/<locale>/` before 0.24) and generates Android resources from
them. From its source on the master branch
([`LanguageType.kt`](https://github.com/icerockdev/moko-resources/blob/master/resources-generator/src/main/kotlin/dev/icerock/gradle/generator/localization/LanguageType.kt),
[`AndroidStringResourceGenerator.kt`](https://github.com/icerockdev/moko-resources/blob/master/resources-generator/src/main/kotlin/dev/icerock/gradle/generator/resources/string/AndroidStringResourceGenerator.kt),
Apache-2.0, IceRock MAG Inc., read on 13 November 2026):

- The folder name, with `-r` replaced by `-`, goes through `java.util.Locale.forLanguageTag`.
- The Android folder is `values-` + the language (with `he`, `yi` and `id` written `iw`, `ji`
  and `in`) + `-r` + the country if there is one. The script is never written. The iOS folder is
  the full tag (`zh-Hant.lproj`), so iOS keeps it.
- Strings are grouped by the full locale, so `zh-Hans` and `zh-Hant` stay separate. Each group
  is then written to `<android folder>/multiplatform_strings.xml` with `writeText`, which
  replaces the file.

What follows on Android:

| moko folder | Android folder | Effect |
|---|---|---|
| `zh-rTW`, `zh-TW` | `values-zh-rTW` | Fine. |
| `zh-Hant` | `values-zh` | Traditional Chinese becomes the plain `zh` fallback, so a mainland China (`zh-CN`) device gets it too unless a `zh-rCN` folder exists. |
| `zh-Hans` + `zh-Hant` | `values-zh` (twice) | Only the group written last survives. The other language is gone on Android but still ships on iOS. |
| `sr-Latn` | `values-sr` | Latin Serbian is shown to Serbian devices set to Cyrillic, the default script for `sr`. |
| `zh-Hans`, `zh-Hant-TW` | `values-zh`, `values-zh-rTW` | Fine: Android works out the same script from the language and region. |
| `b+zh+Hant`, `pt_BR` | `values-` | Not a valid folder, so the build fails. This is moko issue [#644](https://github.com/icerockdev/moko-resources/issues/644) (open since February 2024). |

Prior art: #644 covers the `b+` form, which breaks the build. We found no report of the
dashed script form (`zh-Hant`, `sr-Latn`), which builds without a warning. Two large
moko-resources apps we looked at, Mihon and Animetail, use region folders (`zh-rCN`, `zh-rTW`)
and are not affected. We have not found an affected project yet, and no real build has been
run.

The generated folders are merged into the app like any other library resources, so the app's
locale filter applies to them too. The checker counts them as translations of the module that
holds them.

## What the checker reports

```
python android_localefilters.py <project root> [--json] [--strict]
```

It reads every `build.gradle` / `build.gradle.kts` that applies an Android application plugin
(a line naming `com.android.application`, or `android.application` / `android-application`
as in version catalogs and convention plugins). It also follows project dependencies,
transitively, written as `project(":a:b")` or as type-safe accessors (`projects.a.b`,
`projects.coreUi` for a folder `core-ui` or `core_ui`), because their translations are
merged into the app and filtered with it. A folder counts as a translation when one of its XML
files has a `<string`, `<string-array` or `<plurals` element (`<plural` for moko folders).
moko folders are read only in modules whose build file mentions `moko` or
`multiplatform-resources`.

| Kind | Meaning |
|---|---|
| `filtered_out` | A translated folder that the filter drops, with the reason: `language_not_listed`, `region_not_listed` or `script_mismatch`. |
| `declared_but_filtered` | A language listed in the manifest's `android:localeConfig` file for which no translated folder survives the filter. Android 13+ offers it in Settings, and the app then shows its default strings. |
| `moko_script_dropped` | A moko folder whose script differs from the one Android works out for the folder it becomes (`zh-Hant` to `values-zh`, `sr-Latn` to `values-sr`). |
| `moko_collision` | Two or more moko folders in one source set that become the same Android folder for different locales. Only one reaches the app. |
| `moko_unparsable` | A moko folder that becomes `values-` (`b+zh+Hant`, `pt_BR`); the build fails (#644). |

Notes (not findings):

| Kind | Meaning |
|---|---|
| `dynamic_filter` | The list is built in code (a variable, a spread, string interpolation, `clear()` ...). The module's filter is not judged; moko findings are still reported. |
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
- `project(":...")` paths are looked up next to the app module, then at the nearest folder
  with a `settings.gradle(.kts)`, then at the root given. `projects.*` accessors are matched
  to folder names under that settings folder; a `projectDir` set in settings is not read.
- moko: the Java locale parser is modelled for language, script and country only (no extlang
  subtags, no grandfathered tags). A custom moko `resourcesSourceSets` folder is not read.
  Which group wins a collision depends on the order moko reads the files, so the checker
  does not name it.
- The likely-script table covers about 90 languages and their common regional exceptions
  (`zh-TW`, `sr-ME` and so on). For any other language with an explicit script folder the
  scripts count as matching, which can only hide a `filtered_out` finding.
- `iw`/`he`, `in`/`id` and `ji`/`yi` are treated as the same language. aapt2 compares the
  codes as written, so a mix of the two can drop more than reported.
- Translations shipped by libraries from Maven (AppCompat and the like) are out of scope.

## Tests

`python -m unittest -v test_android_localefilters` covers folder and filter parsing, aapt2's
matching rules (region, script, unknown script, legacy codes), Groovy and Kotlin DSL files (with
comments, a `//` inside a string, flavors, `create("play")`, a list built from a variable, and
a read-only use), and two synthetic projects.

- In the first, an app module filters to `en`, `pt`, `zh-rTW` and `xxhdpi`. That drops
  `values-pt-rBR`, `values-de` and a dependency module's `values-ja`, keeps `values-pt` and
  `values-b+zh+Hant`, and reports `de` as declared in `locales_config.xml` but filtered out.
- In the second, a Kotlin Multiplatform app reaches a shared moko module through
  `projects.shared`, and that module reaches `core-ui` through `projects.coreUi`. The moko
  folders `zh-Hans` and `zh-Hant` collide in `values-zh`, `zh-Hant` and `sr-Latn` lose their
  script, an `images/` folder is ignored, and the app's filter (`en`, `zh-rTW`, `sr`) drops the
  moko `fr-rCA` folder and `core-ui`'s `values-ja`.

The moko tests also cover the Java locale parser (`zh-hant-tw`, `es-419`, and the ill-formed
`pt_BR` and `b+zh+Hant`).
