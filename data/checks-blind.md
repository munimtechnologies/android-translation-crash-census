# Which open-source format checks see the census's crashing translations

checks_blind.py 0.1.0 (MV2 of Munim, Inc., made with AI agents). Weblate's JAVA_MATCH and translate-toolkit's printf_pat are read from their sources at the commits pinned in weblate_deps.py / checks_deps.py; Android Lint's FORMAT pattern is copied from StringFormatDetector.kt (Apache-2.0).

Dropped before counting: date conversion (%t), wrong output not crash 5, cleared repo 11.

## all-crash: 366 rows in 98 repositories

- weblate: flagged 300, plural-dependent 39, unflagged 27
- pofilter: flagged 322, unflagged 44
- lint: flagged 239, ignored 35, not-visited 90, unflagged 2

| seen by | rows | repos |
|---|---:|---:|
| lint | 12 | 4 |
| none | 12 | 9 |
| pofilter | 41 | 21 |
| pofilter lint | 1 | 1 |
| weblate | 6 | 3 |
| weblate lint | 14 | 1 |
| weblate pofilter | 68 | 30 |
| weblate pofilter lint | 212 | 57 |

| mistake kind | rows | repos | weblate | pofilter | lint | none |
|---|---:|---:|---:|---:|---:|---:|
| stray-percent | 82 | 41 | 53 | 55 | 41 | 8 |
| malformed-index | 65 | 11 | 62 | 65 | 62 | 0 |
| conversion-missing | 66 | 26 | 49 | 66 | 44 | 0 |
| conversion-native | 28 | 8 | 28 | 28 | 28 | 0 |
| conversion-invalid | 10 | 7 | 10 | 10 | 0 | 0 |
| flag-mismatch | 52 | 22 | 40 | 42 | 41 | 2 |
| argument-not-passed | 48 | 19 | 45 | 43 | 13 | 0 |
| wrong-type | 15 | 10 | 13 | 13 | 10 | 2 |

## formatted-crash: 237 rows in 66 repositories

- weblate: flagged 198, plural-dependent 14, unflagged 25
- pofilter: flagged 215, unflagged 22
- lint: flagged 176, ignored 19, not-visited 41, unflagged 1

| seen by | rows | repos |
|---|---:|---:|
| lint | 11 | 3 |
| none | 9 | 7 |
| pofilter | 18 | 13 |
| pofilter lint | 1 | 1 |
| weblate | 2 | 2 |
| weblate pofilter | 32 | 16 |
| weblate pofilter lint | 164 | 41 |

| mistake kind | rows | repos | weblate | pofilter | lint | none |
|---|---:|---:|---:|---:|---:|---:|
| stray-percent | 45 | 26 | 22 | 32 | 21 | 7 |
| malformed-index | 50 | 5 | 50 | 50 | 50 | 0 |
| conversion-missing | 43 | 18 | 36 | 43 | 33 | 0 |
| conversion-native | 26 | 6 | 26 | 26 | 26 | 0 |
| conversion-invalid | 7 | 4 | 7 | 7 | 0 | 0 |
| flag-mismatch | 34 | 14 | 28 | 30 | 30 | 2 |
| argument-not-passed | 27 | 14 | 24 | 22 | 11 | 0 |
| wrong-type | 5 | 5 | 5 | 5 | 5 | 0 |

## Rows no check sees (formatted first)

- flag-mismatch | Exodus tr `trackers_presence[one]` | `Present in %1$d%% (%2$d apps) of your applications` -> `Uygulamalarınızın %1$d% (%2$d uygulama) içinde mevcut` (IllegalFormatFlagsException, formatted; weblate unflagged, lint not-visited)
- flag-mismatch | Exodus tr `trackers_presence[other]` | `Present in %1$d%% (%2$d apps) of your applications` -> `Uygulamalarınızın %1$d% (%2$d uygulama) içinde mevcut` (IllegalFormatFlagsException, formatted; weblate unflagged, lint not-visited)
- stray-percent | Element X - Secure Chat & Call ja `a11y_polls_percent_of_total[other]` | `%1$d percents of total votes` -> `総投票数うち%1$d% パーセント` (UnknownFormatConversionException, formatted; weblate unflagged, lint not-visited)
- stray-percent | Homer Audio Player for Seniors zh-rCN `battery_level_charging_content_description[other]` | `battery charging, %1$d percent` -> `充电中， %1$d %` (UnknownFormatConversionException, formatted; weblate unflagged, lint not-visited)
- stray-percent | Homer Audio Player for Seniors zh-rCN `battery_level_content_description[other]` | `battery %1$d percent` -> `电量 %1$d %` (UnknownFormatConversionException, formatted; weblate unflagged, lint not-visited)
- stray-percent | LibreTorrent cs `pref_custom_battery_control_summary` | `Set a battery %% to pause downloads at. (Ignores the default %1$d%%.)` -> `Nastavte vlastní % úroveň stavu baterie při které se pozastaví stahování. (Ignoruje výchozí hodnotu %1$d%%.)` (UnknownFormatConversionException, formatted; weblate unflagged, lint unflagged)
- stray-percent | Mastodon be-rBY `x_quotes[one]` | `%,d quotes` -> `%,d% цытата` (UnknownFormatConversionException, formatted; weblate unflagged, lint not-visited)
- stray-percent | Moshidon be-rBY `x_quotes[one]` | `%,d quotes` -> `%,d% цытата` (UnknownFormatConversionException, formatted; weblate unflagged, lint not-visited)
- stray-percent | SchildiChat Next ja `a11y_polls_percent_of_total[other]` | `%1$d percents of total votes` -> `総投票数うち%1$d% パーセント` (UnknownFormatConversionException, formatted; weblate unflagged, lint not-visited)
- stray-percent | Commons sl `contribution_state_in_progress` | `%1$d%% complete` -> `Opravljeno %1$d%&nbsp;%% nalaganja` (UnknownFormatConversionException, unreferenced; weblate unflagged, lint unflagged)
- wrong-type | Material Files eu `file_job_extract_scan_notification_title_format[one]` | `Preparing to extract %1$,d files (%2$s)` -> `Fitxategi %1$ erauzteko prestatzen (%2$s)` (IllegalFormatConversionException, referenced; weblate plural-dependent, lint not-visited)
- wrong-type | Material Files eu `file_job_extract_scan_notification_title_format[other]` | `Preparing to extract %1$,d files (%2$s)` -> `%1$ fitxategi erauzteko prestatzen (%2$s)` (IllegalFormatConversionException, referenced; weblate plural-dependent, lint not-visited)
