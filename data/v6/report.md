# Translation-crash census of open-source Android apps

Generated 2026-10-16T12:59:53Z by census.py 0.4.0 (MV2 of Munim, Inc., made with AI agents).

- Index: https://f-droid.org/repo/index-v2.json, 4667 apps, 4476 distinct repositories, 4476 scanned (0 not reached in the time budget).
- Repositories with Android string resources: 3751; with translated strings the app formats: 1704.
- Translations of formatted strings checked: 1269051, with openjdk version "21.0.12.1" 2026-08-18.
- Real java.util.Formatter verdicts: 360 crash whatever the app passes, 93 crash if the app passes text for a %s argument, 4 only if it passes an Int (not a Long) for a %d, 0 only if it passes a Long (not an Int), 1268594 fine, 0 skipped because the source string itself fails.
- Repositories with at least one crashing translation: 95 (59 of them updated in the last year).
- How the app's Kotlin/Java code uses the strings behind the crashing translations: 232 formatted with arguments (the crash is reachable), 40 used only in other ways, 88 never named in the code, 0 unknown.
- Repositories with a crashing translation of a string the code formats: 64.
- l10n-guard's static java-format check against the JVM: precision 1.0, recall 0.9833.

## Exceptions

- UnknownFormatConversionException: 249
- MissingFormatArgumentException: 49
- FormatFlagsConversionMismatchException: 39
- IllegalFormatConversionException: 19
- IllegalFormatFlagsException: 4

## Languages with the most crashing translations

- ug: 55
- tr: 18
- ar: 16
- ru: 14
- es: 10
- it: 10
- eu: 10
- el: 10
- uk: 9
- ckb: 8
- zh: 8
- sr: 7
- hu: 7
- bn: 6
- bg: 6
- ko: 6
- fr: 5
- in: 5
- my: 5
- pl: 5
- sl: 5
- zh-rCN: 4
- sq-rAL: 4
- fa-rIR: 4
- vi: 4

## By the translation platform each repository names

Repositories with translated strings the app formats, by the platform their config files (crowdin.yml, .tx/config...) or, failing that, their README/CONTRIBUTING name.

| platform | repositories | translations checked | crash | per 100,000 | repositories with a crash | crash in strings the code formats |
|---|---:|---:|---:|---:|---:|---:|
| none named | 1108 | 582383 | 129 | 22.2 | 35 | 73 |
| weblate | 341 | 350914 | 90 | 25.6 | 26 | 48 |
| crowdin | 170 | 208665 | 61 | 29.2 | 21 | 48 |
| transifex | 63 | 97294 | 65 | 66.8 | 7 | 49 |
| several | 5 | 14214 | 2 | 14.1 | 1 | 2 |
| localazy | 1 | 11962 | 2 | 16.7 | 1 | 2 |
| poeditor | 15 | 3170 | 9 | 283.9 | 3 | 8 |
| pontoon | 1 | 449 | 2 | 445.4 | 1 | 2 |

## Repositories with the most crashing translations

| crashes | in formatted strings | app | repository |
|---:|---:|---|---|
| 56 | 47 | ownCloud | https://github.com/owncloud/android |
| 36 | 26 | Commons | https://github.com/commons-app/apps-android-commons |
| 25 | 25 | Cashiro | https://github.com/ritesh-kanwar/Cashiro |
| 12 | 12 | OsmAnd~ | https://github.com/osmandapp/Osmand |
| 8 | 8 | Husky | https://github.com/captainepoch/husky |
| 10 | 7 | MoneyWallet | https://github.com/AndreAle94/moneywallet |
| 6 | 6 | Flashy | https://github.com/Crazy-Marvin/Flashy |
| 7 | 5 | FadCam | https://github.com/anonfaded/FadCam |
| 5 | 5 | Stepsy: Step Counter | https://github.com/nvllz/stepsy |
| 4 | 4 | Mastodon | https://github.com/mastodon/mastodon-android |
| 4 | 4 | Package Manager | https://github.com/SmartPack/PackageManager |
| 4 | 4 | Bimba | https://codeberg.org/bimba/czwek |
| 4 | 4 | pretixSCAN | https://github.com/pretix/pretixscan-android |
| 4 | 4 | Moshidon | https://github.com/LucasGGamerM/moshidon |
| 4 | 3 | APK Explorer & Editor | https://github.com/apk-editor/APK-Explorer-Editor |
| 4 | 3 | spaRSS DecSync | https://github.com/39aldo39/spaRSS-DecSync |
| 3 | 3 | LibreTube | https://github.com/libre-tube/LibreTube |
| 3 | 3 | p!n | https://github.com/nproth/pin |
| 4 | 2 | Rethink: DNS + Firewall + VPN | https://github.com/celzero/rethink-app |
| 3 | 2 | Metro - A music player for Android | https://github.com/MuntashirAkon/Metro |
| 2 | 2 | Private Internet Access VPN | https://github.com/pia-foss/mobile-android |
| 2 | 2 | Shader Editor | https://github.com/markusfisch/ShaderEditor |
| 2 | 2 | Ceno Browser: Share the Web | https://gitlab.com/ceno-app/ceno-android |
| 2 | 2 | Homer Audio Player for Seniors | https://github.com/msimonides/homerplayer2 |
| 2 | 2 | Andor's Trail | https://github.com/AndorsTrailRelease/andors-trail |
| 2 | 2 | Element X - Secure Chat & Call | https://github.com/element-hq/element-x-android |
| 2 | 2 | Adiresy | https://github.com/nynosy/adiresy-mobile |
| 2 | 2 | SchildiChat Next | https://github.com/SchildiChat/schildichat-android-next |
| 2 | 2 | Exodus | https://github.com/Exodus-Privacy/exodus-android-app |
| 2 | 2 | Cofi - Brew Timer | https://github.com/rozPierog/Cofi |
| 2 | 2 | MemeTastic | https://github.com/gsantner/memetastic |
| 19 | 1 | Tella | https://github.com/Horizontal-org/Tella-Android |
| 2 | 1 | Habit-Maker | https://github.com/dessalines/habit-maker |
| 2 | 1 | Money Manager Ex | https://github.com/moneymanagerex/android-money-manager-ex |
| 2 | 1 | Retro Music | https://github.com/RetroMusicPlayer/RetroMusicPlayer |
| 1 | 1 | RiPlay | https://github.com/fast4x/RiPlay |
| 1 | 1 | Cryptomator | https://github.com/cryptomator/android |
| 1 | 1 | Inure App Manager (Trial) | https://github.com/Hamza417/Inure |
| 1 | 1 | Iris Gallery | https://github.com/MohamadOday/iris-gallery |
| 1 | 1 | Booming Music | https://github.com/mardous/BoomingMusic |

## Limits

- A string counts as formatted when its default (values/) text has a printf specifier that isn't prose. An app that never passes arguments for it would not crash; one that passes more arguments than the source uses could escape a MissingFormatArgumentException.
- Plurals: getQuantityString passes every quantity the same arguments, so each translated plural form is checked against the source form that reads the most of them, with each argument's type taken from any source form that shows it.
- Integer arguments are tried as both an Int and a Long; a translation counts as 'crash' only if it throws with both. Which one the app passes is in its code.
- Code use is found by matching R.string.name / R.plurals.name (and Res.string) in the .kt and .java files, fetched only for repositories with a flagged translation. 'formatted' means a getString/stringResource/getQuantityString/pluralStringResource call passes arguments, or the string is wrapped in String.format or .format(). Strings looked up by name at runtime, or formatted in ways these patterns miss, count as 'referenced' or 'unreferenced'.
- The platform is what the repository names at its root, not proof that every translation came through it; 'none named' mixes in-repository translation with platforms these patterns miss.
- Verdicts come from the JDK in the container. Android's java.util.Formatter is the same OpenJDK code for these cases, but edge cases can differ by API level.
- Only the latest commit of each repository's default branch is read; a translation may already be fixed on a translation platform but not merged yet.
