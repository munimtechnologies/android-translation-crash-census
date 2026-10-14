# Translation-crash census of open-source Android apps

Generated 2026-10-14T08:54:31Z by census.py 0.1.0 (MV2 of Munim, Inc., made with AI agents).

- Index: https://f-droid.org/repo/index-v2.json, 4667 apps, 4476 distinct repositories, 1523 scanned (2953 not reached in the time budget).
- Repositories with Android string resources: 1273; with translated strings the app formats: 714.
- Translations of formatted strings checked: 810419, with openjdk version "21.0.12.1" 2026-08-18.
- Real java.util.Formatter verdicts: 253 crash whatever the app passes, 61 crash if the app passes text for a %s argument, 810105 fine, 0 skipped because the source string itself fails.
- Repositories with at least one crashing translation: 39 (39 of them updated in the last year).
- l10n-guard's static java-format check against the JVM: precision 1.0, recall 0.996.

## Exceptions

- UnknownFormatConversionException: 148
- MissingFormatArgumentException: 72
- FormatFlagsConversionMismatchException: 25
- IllegalFormatConversionException: 6
- IllegalFormatFlagsException: 2

## Languages with the most crashing translations

- ug: 55
- ru: 17
- uk: 14
- sl: 14
- tr: 9
- ar: 9
- sr: 7
- ckb: 6
- eu: 6
- pl: 5
- in: 5
- my: 5
- qq: 5
- lt: 4
- es: 4
- zh-rCN: 4
- ka: 4
- tcy: 4
- fr: 3
- it: 3
- hu: 3
- el: 3
- xmf: 3
- sq-rAL: 2
- pt: 2

## Repositories with the most crashing translations

| crashes | app | repository |
|---:|---|---|
| 56 | ownCloud | https://github.com/owncloud/android |
| 32 | Commons | https://github.com/commons-app/apps-android-commons |
| 19 | KDE Connect | https://invent.kde.org/network/kdeconnect-android |
| 19 | Zorin Connect | https://github.com/ZorinOS/zorin-connect-android |
| 19 | Tella | https://github.com/Horizontal-org/Tella-Android |
| 12 | Wikipedia | https://github.com/wikimedia/apps-android-wikipedia |
| 12 | OsmAnd~ | https://github.com/osmandapp/Osmand |
| 11 | SchildiChat Legacy | https://github.com/SchildiChat/SchildiChat-android |
| 9 | Tallybook | https://github.com/herrerad85/tallybook |
| 6 | Flashy | https://github.com/Crazy-Marvin/Flashy |
| 4 | Mastodon | https://github.com/mastodon/mastodon-android |
| 4 | Jellyfin | https://github.com/jellyfin/jellyfin-android |
| 4 | Rethink: DNS + Firewall + VPN | https://github.com/celzero/rethink-app |
| 4 | APK Explorer & Editor | https://github.com/apk-editor/APK-Explorer-Editor |
| 4 | Package Manager | https://github.com/SmartPack/PackageManager |
| 3 | DuckDuckGo Privacy Browser | https://github.com/duckduckgo/Android |
| 2 | Ceno Browser: Share the Web | https://gitlab.com/ceno-app/ceno-android |
| 2 | Material Files | https://github.com/zhanghai/MaterialFiles |
| 2 | Look4Sat: Satellite tracker | https://github.com/rt-bishop/Look4Sat |
| 2 | Private Internet Access VPN | https://github.com/pia-foss/mobile-android |
| 2 | Homer Audio Player for Seniors | https://github.com/msimonides/homerplayer2 |
| 2 | Money Manager Ex | https://github.com/moneymanagerex/android-money-manager-ex |
| 2 | Shader Editor | https://github.com/markusfisch/ShaderEditor |
| 2 | Element X - Secure Chat & Call | https://github.com/element-hq/element-x-android |
| 2 | Habit-Maker | https://github.com/dessalines/habit-maker |
| 2 | Cryptomator | https://github.com/cryptomator/android |
| 2 | AnkiDroid: Flashcards | https://github.com/ankidroid/Anki-Android |
| 2 | Andor's Trail | https://github.com/AndorsTrailRelease/andors-trail |
| 1 | Wire • Secure Messenger | https://github.com/wireapp/wire-android |
| 1 | Your local weather | https://github.com/thuryn/your-local-weather |
| 1 | Les Pas - Photo Album for Nextcloud | https://github.com/scubajeff/lespas |
| 1 | Booming Music | https://github.com/mardous/BoomingMusic |
| 1 | Suntimes Calendars | https://github.com/forrestguice/SuntimesCalendars |
| 1 | NightDream | https://github.com/firebirdberlin/nightdream |
| 1 | RiPlay | https://github.com/fast4x/RiPlay |
| 1 | Iris Gallery | https://github.com/MohamadOday/iris-gallery |
| 1 | Petals: Cannabis Use Tracker | https://github.com/LeoColman/Petals |
| 1 | Inure App Manager (Trial) | https://github.com/Hamza417/Inure |
| 1 | Briar | https://code.briarproject.org/briar/briar |

## Limits

- A string counts as formatted when its default (values/) text has a printf specifier that isn't prose. An app that never passes arguments for it would not crash; one that passes more arguments than the source uses could escape a MissingFormatArgumentException.
- Verdicts come from the JDK in the container. Android's java.util.Formatter is the same OpenJDK code for these cases, but edge cases can differ by API level.
- Only the latest commit of each repository's default branch is read; a translation may already be fixed on a translation platform but not merged yet.
