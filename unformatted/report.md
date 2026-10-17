# Translation-crash census of open-source Android apps

Generated 2026-10-17T01:22:50Z by census.py 0.4.0 (MV2 of Munim, Inc., made with AI agents).

- Index: https://f-droid.org/repo/index-v2.json, 4667 apps, 4476 distinct repositories, 4476 scanned (0 not reached in the time budget).
- Repositories with Android string resources: 3752; with translated strings the app formats: 49.
- Translations of formatted strings checked: 1394, with openjdk version "21.0.12.1" 2026-08-18.
- Real java.util.Formatter verdicts: 6 crash whatever the app passes, 4 crash if the app passes text for a %s argument, 0 only if it passes an Int (not a Long) for a %d, 0 only if it passes a Long (not an Int), 1384 fine, 0 skipped because the source string itself fails.
- Repositories with at least one crashing translation: 2 (0 of them updated in the last year).
- How the app's Kotlin/Java code uses the strings behind the crashing translations: 0 formatted with arguments (the crash is reachable), 2 used only in other ways, 4 never named in the code, 0 unknown.
- Repositories with a crashing translation of a string the code formats: 0.
- l10n-guard's static java-format check against the JVM: precision 1.0, recall 1.0.

## Exceptions

- UnknownFormatConversionException: 6

## Languages with the most crashing translations

- ar: 2
- ml: 2
- zh: 2

## By the translation platform each repository names

Repositories with translated strings the app formats, by the platform their config files (crowdin.yml, .tx/config...) or, failing that, their README/CONTRIBUTING name.

| platform | repositories | translations checked | crash | per 100,000 | repositories with a crash | crash in strings the code formats |
|---|---:|---:|---:|---:|---:|---:|
| weblate | 11 | 715 | 4 | 559.4 | 1 | 0 |
| none named | 34 | 507 | 2 | 394.5 | 1 | 0 |
| crowdin | 1 | 89 | 0 | 0.0 | 0 | 0 |
| transifex | 2 | 73 | 0 | 0.0 | 0 | 0 |
| poeditor | 1 | 10 | 0 | 0.0 | 0 | 0 |

## Repositories with the most crashing translations

| crashes | in formatted strings | app | repository |
|---:|---:|---|---|
| 4 | 0 | Red Moon | https://github.com/LibreShift/red-moon |
| 2 | 0 | Helsinki Timetables | https://github.com/w32blaster/helsinki-timetables |

## Limits

- A string counts as formatted when its default (values/) text has a printf specifier that isn't prose. An app that never passes arguments for it would not crash; one that passes more arguments than the source uses could escape a MissingFormatArgumentException.
- Plurals: getQuantityString passes every quantity the same arguments, so each translated plural form is checked against the source form that reads the most of them, with each argument's type taken from any source form that shows it.
- Integer arguments are tried as both an Int and a Long; a translation counts as 'crash' only if it throws with both. Which one the app passes is in its code.
- Code use is found by matching R.string.name / R.plurals.name (and Res.string) in the .kt and .java files, fetched only for repositories with a flagged translation. 'formatted' means a getString/stringResource/getQuantityString/pluralStringResource call passes arguments, or the string is wrapped in String.format or .format(). Strings looked up by name at runtime, or formatted in ways these patterns miss, count as 'referenced' or 'unreferenced'.
- The platform is what the repository names at its root, not proof that every translation came through it; 'none named' mixes in-repository translation with platforms these patterns miss.
- Verdicts come from the JDK in the container. Android's java.util.Formatter is the same OpenJDK code for these cases, but edge cases can differ by API level.
- Only the latest commit of each repository's default branch is read; a translation may already be fixed on a translation platform but not merged yet.
