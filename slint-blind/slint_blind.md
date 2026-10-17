# i18n-security-lint over the census's crashing translations

slint_blind.py 0.1.0 (MV2 of Munim, Inc., made with AI agents), i18n-security-lint 0.2.1 from PyPI, rows from data/checks-blind-rows.csv at 50cd0ac6baf1e8f31baa05f221eaf803e6f39d63.

## Predictions (PREDICTIONS.md, written before the run)

- P1 HELD: android res/ tree and strings.xml named directly: no findings; --strict exits 0
- P2 HELD: XLIFF with <source> and <target>: 0 drift findings
- P3 HELD: the 12 rows no other check sees: 0 flagged
- P4 FAILED: fewer than pofilter's 322 of 366 flagged (api)
- P5 HELD: po path agrees with api path on at least 360 of 366 rows

## File paths

- android res-directory: 0 findings, --strict exit 0
- android values-es-strings.xml: 0 findings, --strict exit 0
- xliff (366 pairs with <source>): 0 drift findings

## all-crash: 366 rows in 98 repositories

- api: flagged 323, unflagged 43
- po file through the CLI: flagged 323, unflagged 43
- flagged by i18n-security-lint and by none of Weblate, pofilter, Lint: 0
- seen by none of the three: 12; by none of the four: 12

| mistake kind | rows | i18n-security-lint | pofilter |
|---|---:|---:|---:|
| argument-not-passed | 48 | 43 | 43 |
| conversion-invalid | 10 | 10 | 10 |
| conversion-missing | 66 | 63 | 66 |
| conversion-native | 28 | 27 | 28 |
| flag-mismatch | 52 | 47 | 42 |
| malformed-index | 65 | 62 | 65 |
| stray-percent | 82 | 62 | 55 |
| wrong-type | 15 | 9 | 13 |

## formatted-crash: 237 rows in 66 repositories

- api: flagged 206, unflagged 31
- po file through the CLI: flagged 206, unflagged 31
- flagged by i18n-security-lint and by none of Weblate, pofilter, Lint: 0
- seen by none of the three: 9; by none of the four: 9

| mistake kind | rows | i18n-security-lint | pofilter |
|---|---:|---:|---:|
| argument-not-passed | 27 | 22 | 22 |
| conversion-invalid | 7 | 7 | 7 |
| conversion-missing | 43 | 40 | 43 |
| conversion-native | 26 | 25 | 26 |
| flag-mismatch | 34 | 30 | 30 |
| malformed-index | 50 | 49 | 50 |
| stray-percent | 45 | 29 | 32 |
| wrong-type | 5 | 4 | 5 |

## Crashing rows i18n-security-lint does not flag (formatted first)

- argument-not-passed | Flashy gl `farnsworth_unit_length_explanation` | `Farnsworth timing makes recognizing the sound patterns easier by increasing the gaps between the characters and words to give more recognition time. A Farnsworth unit is longer than a basic unit. Enter your desired length of a Farnsworth unit below (must be longer than a basic unit: %d milliseconds). Leave blank to use the length of the basic unit plus an additional 25 percent of it.` -> `A sincronización Farnsworth facilita o recoñecemento dos patróns de son aumentando os espazos entre os caracteres e as palabras para dar máis tempo de recoñecemento. Unha unidade Farnsworth é máis longa que unha unidade básica. Introduce a continuación a lonxitude desexada dunha unidade Farnsworth (debe ser maior que unha unidade básica: %d milisegundos). Déixao en branco para utilizar a lonxitude da unidade básica máis un 25% adicional da mesma.` (MissingFormatArgumentException, formatted; others: lint)
- argument-not-passed | Flashy pt `farnsworth_unit_length_explanation` | `Farnsworth timing makes recognizing the sound patterns easier by increasing the gaps between the characters and words to give more recognition time. A Farnsworth unit is longer than a basic unit. Enter your desired length of a Farnsworth unit below (must be longer than a basic unit: %d milliseconds). Leave blank to use the length of the basic unit plus an additional 25 percent of it.` -> `O tempo Farnsworth facilita o reconhecimento dos padrões sonoros, aumentando os espaços entre os caracteres e as palavras para proporcionar mais tempo de reconhecimento.  Uma unidade Farnsworth é mais longa que uma unidade básica.  Insira abaixo o comprimento desejado de uma unidade Farnsworth (deve ser maior que uma unidade básica: %d milissegundos).  Deixe em branco para usar o comprimento da unidade básica mais 25% adicionais.` (MissingFormatArgumentException, formatted; others: lint)
- argument-not-passed | Flashy pt-rBR `farnsworth_unit_length_explanation` | `Farnsworth timing makes recognizing the sound patterns easier by increasing the gaps between the characters and words to give more recognition time. A Farnsworth unit is longer than a basic unit. Enter your desired length of a Farnsworth unit below (must be longer than a basic unit: %d milliseconds). Leave blank to use the length of the basic unit plus an additional 25 percent of it.` -> `O tempo Farnsworth facilita o reconhecimento dos padrões sonoros, aumentando os espaços entre os caracteres e as palavras para proporcionar mais tempo de reconhecimento.  Uma unidade Farnsworth é mais longa que uma unidade básica.  Insira abaixo o comprimento desejado de uma unidade Farnsworth (deve ser maior que uma unidade básica: %d milissegundos).  Deixe em branco para usar o comprimento da unidade básica mais 25% adicionais.` (MissingFormatArgumentException, formatted; others: lint)
- argument-not-passed | Mastodon in-rID `x_new_notifications[other]` | `%,d new notifications` -> `%,d notifikasi baru %,d notifikasi baru` (MissingFormatArgumentException, formatted; others: weblate)
- argument-not-passed | Moshidon in-rID `x_new_notifications[other]` | `%,d new notifications` -> `%,d notifikasi baru %,d notifikasi baru` (MissingFormatArgumentException, formatted; others: weblate)
- conversion-missing | Cryptomator nl-rNL `dialog_vaults_removed_during_migration_title` | `Please re-add vaults for %1s cloud` -> `Voeg de kluis voor %1's cloud opnieuw toe` (UnknownFormatConversionException, formatted; others: weblate pofilter lint)
- conversion-missing | Jellyfin sv `download_remove_description[one]` | `Do you want to remove "%2$s" from your downloads?` -> `Vill du ta bort %1"%2$s" från dina nedladdningar?` (UnknownFormatConversionException, formatted; others: pofilter)
- conversion-missing | ntfy - PUT/POST to your phone sv `settings_backup_restore_backup_failed` | `Backup failed: %1$s` -> `Säkerhetskopiering%1$ misslyckad: %1$s` (UnknownFormatConversionException, formatted; others: pofilter)
- conversion-native | Stepsy: Step Counter ar `milestone_short_millions_decimal` | `%.1fM` -> `%.1فم` (UnknownFormatConversionException, formatted; others: weblate pofilter lint)
- flag-mismatch | Exodus tr `trackers_presence[one]` | `Present in %1$d%% (%2$d apps) of your applications` -> `Uygulamalarınızın %1$d% (%2$d uygulama) içinde mevcut` (IllegalFormatFlagsException, formatted; others: none)
- flag-mismatch | Exodus tr `trackers_presence[other]` | `Present in %1$d%% (%2$d apps) of your applications` -> `Uygulamalarınızın %1$d% (%2$d uygulama) içinde mevcut` (IllegalFormatFlagsException, formatted; others: none)
- flag-mismatch | Private Internet Access VPN da-rDK `save_percentage` | `Save %d%%` -> `Spar %d% %` (IllegalFormatFlagsException, formatted; others: lint)
- flag-mismatch | Private Internet Access VPN nb-rNO `save_percentage` | `Save %d%%` -> `Spar %d% %` (IllegalFormatFlagsException, formatted; others: lint)
- malformed-index | Pedometer (PFA) sv `notification_text_distance` | `%1$.2f %2$s walked today.` -> `%1 $ .2f %2$s gått idag.` (UnknownFormatConversionException, formatted; others: weblate pofilter lint)
- stray-percent | Cashiro hu `percentage_format` | `(%1$d%%)` -> `(%1$d%)` (UnknownFormatConversionException, formatted; others: lint)
- stray-percent | Cashiro ro `percentage_format_no_brackets` | `%1$d%%` -> `%1$d%` (UnknownFormatConversionException, formatted; others: lint)
- stray-percent | Cashiro tk `percentage_format` | `(%1$d%%)` -> `(%1$d%)` (UnknownFormatConversionException, formatted; others: lint)
- stray-percent | Commons ky `quiz_alert_message` | `More than %1$s of the images you uploaded have been deleted. If you carry on uploading images that require deletion, your account will likely be banned.  Would you like to view the tutorial again and then take a quiz to help you learn what type of images you should or shouldn't upload?` -> `Сиз жүктөгөн сүрөттөрдүн %1$s%дан көбү өчүрүлгөн. Эгер өчүрүлүшү керек болгон сүрөттөрдү жүктөөнү уланта берсеңиз, аккаунтуңуз бөгөттөлүшү мүмкүн. Окутуу сабактарын кайра көрүп, кайсы сүрөттөрдү жүктөш керек, кайсынысы керек эмес экенин үйрөнүү үчүн тесттен өтөсүзбү?` (UnknownFormatConversionException, formatted; others: pofilter lint)
- stray-percent | Element X - Secure Chat & Call el `troubleshoot_notifications_test_unified_push_success[one]` | `%1$d distributors found: %2$s.` -> `%Βρέθηκε %1$d διανομέας: %2$s.` (UnknownFormatConversionException, formatted; others: pofilter)
- stray-percent | Element X - Secure Chat & Call ja `a11y_polls_percent_of_total[other]` | `%1$d percents of total votes` -> `総投票数うち%1$d% パーセント` (UnknownFormatConversionException, formatted; others: none)
- stray-percent | Flashy fr `farnsworth_unit_length_explanation` | `Farnsworth timing makes recognizing the sound patterns easier by increasing the gaps between the characters and words to give more recognition time. A Farnsworth unit is longer than a basic unit. Enter your desired length of a Farnsworth unit below (must be longer than a basic unit: %d milliseconds). Leave blank to use the length of the basic unit plus an additional 25 percent of it.` -> `La méthode Farnsworth permet de reconnaître les motifs sonores plus facilement en augmentant le délai entre les lettres et entre les mots, ce qui laisse plus de temps pour les identifier.  Une unité Farnsworth est plus longue qu'une unité de base.  Écrivez ci-contre la longueur voulue pour votre unité Farnsworth (plus longue qu'une unité de base : %d millisecondes).  Laissez vide pour utiliser la longueur d'une unité de base augmentée de 25%.` (UnknownFormatConversionException, formatted; others: lint)
- stray-percent | Flashy it `farnsworth_unit_length_explanation` | `Farnsworth timing makes recognizing the sound patterns easier by increasing the gaps between the characters and words to give more recognition time. A Farnsworth unit is longer than a basic unit. Enter your desired length of a Farnsworth unit below (must be longer than a basic unit: %d milliseconds). Leave blank to use the length of the basic unit plus an additional 25 percent of it.` -> `La temporizzazione di Farnsworth facilita il riconoscimento dei pattern sonori aumentando gli intervalli tra caratteri e parole, offrendo così più tempo per il riconoscimento. Un'unità Farnsworth è più lunga di un'unità base. Inserisci qui sotto la durata desiderata per un'unità Farnsworth (deve essere maggiore di un'unità base: %d millisecondi). Lascia vuoto per utilizzare la durata dell'unità base più un ulteriore 25%.` (UnknownFormatConversionException, formatted; others: lint)
- stray-percent | Flashy zh-rCN `farnsworth_unit_length_explanation` | `Farnsworth timing makes recognizing the sound patterns easier by increasing the gaps between the characters and words to give more recognition time. A Farnsworth unit is longer than a basic unit. Enter your desired length of a Farnsworth unit below (must be longer than a basic unit: %d milliseconds). Leave blank to use the length of the basic unit plus an additional 25 percent of it.` -> `法恩斯沃斯计时法通过增加字符和单词之间的间隔来给予更多的识别时间，从而使识别声音模式更容易。  法恩斯沃斯单位比基本单位长。  在下面输入您想要的法恩斯沃斯单位长度(必须大于基本单位：%d 毫秒)。  留空，使用基本单位的长度加上额外的 25%。` (UnknownFormatConversionException, formatted; others: lint)
- stray-percent | Homer Audio Player for Seniors zh-rCN `battery_level_charging_content_description[other]` | `battery charging, %1$d percent` -> `充电中， %1$d %` (UnknownFormatConversionException, formatted; others: none)
- stray-percent | Homer Audio Player for Seniors zh-rCN `battery_level_content_description[other]` | `battery %1$d percent` -> `电量 %1$d %` (UnknownFormatConversionException, formatted; others: none)
- stray-percent | LibreTorrent cs `pref_custom_battery_control_summary` | `Set a battery %% to pause downloads at. (Ignores the default %1$d%%.)` -> `Nastavte vlastní % úroveň stavu baterie při které se pozastaví stahování. (Ignoruje výchozí hodnotu %1$d%%.)` (UnknownFormatConversionException, formatted; others: none)
- stray-percent | Mastodon be-rBY `x_quotes[one]` | `%,d quotes` -> `%,d% цытата` (UnknownFormatConversionException, formatted; others: none)
- stray-percent | Moshidon be-rBY `x_quotes[one]` | `%,d quotes` -> `%,d% цытата` (UnknownFormatConversionException, formatted; others: none)
- stray-percent | SchildiChat Next el `troubleshoot_notifications_test_unified_push_success[one]` | `%1$d distributors found: %2$s.` -> `%Βρέθηκε %1$d διανομέας: %2$s.` (UnknownFormatConversionException, formatted; others: pofilter)
- stray-percent | SchildiChat Next ja `a11y_polls_percent_of_total[other]` | `%1$d percents of total votes` -> `総投票数うち%1$d% パーセント` (UnknownFormatConversionException, formatted; others: none)
- wrong-type | Andor's Trail la `iteminfo_effect_critical_multiplier` | `Enables critical hits with a multiplier of x%1$.1f` -> `Hits critica ope multiplicatoris ex x %1$,d.1f *` (IllegalFormatConversionException, formatted; others: weblate pofilter lint)
- flag-mismatch | BOINC bg `notice_notification[one]` | `%2$,d new notices` -> `Ново известие от %1$ s` (FormatFlagsConversionMismatchException, unreferenced; others: pofilter)
- malformed-index | BOINC az `notice_notification[one]` | `%2$,d new notices` -> `% 2 $, d yeni xəbərdarlıq` (UnknownFormatConversionException, unreferenced; others: pofilter)
- malformed-index | BOINC az `notice_notification[other]` | `%2$,d new notices` -> `% 2 $, d yeni xəbərdarlıq` (UnknownFormatConversionException, unreferenced; others: pofilter)
- stray-percent | AdAway nl `welcome_sync_error` | `Failed to sync: %1$s Retry now?` -> `81%match Het synchroniseren is mislukt: %1$s Wilt u het opnieuw proberen?` (UnknownFormatConversionException, referenced; others: weblate pofilter)
- stray-percent | Commons sl `contribution_state_in_progress` | `%1$d%% complete` -> `Opravljeno %1$d%&nbsp;%% nalaganja` (UnknownFormatConversionException, unreferenced; others: none)
- stray-percent | FeinstaubWidget de `toggletext_on` | `°C, %hum.` -> `°C, %LF` (UnknownFormatConversionException, unreferenced; others: weblate pofilter)
- stray-percent | Petals: Cannabis Use Tracker in `current_thc_concentration` | `Current THC concentration: %s %%` -> `Konsentrasi THC saat ini: %s %` (UnknownFormatConversionException, referenced; others: lint)
- wrong-type | HeartBeat bn `measurement_output_template[one]` | `Pulse: %2.1f (%d cycles in %2.1f seconds)` -> `স্পন্দন: %2.1f (%2.1f সেকেন্ডে %d চক্র)` (IllegalFormatConversionException, referenced; others: weblate pofilter)
- wrong-type | HeartBeat bn `measurement_output_template[other]` | `Pulse: %2.1f (%d cycles in %2.1f seconds)` -> `স্পন্দন: %2.1f (%2.1f সেকেন্ডে %d চক্র)` (IllegalFormatConversionException, referenced; others: weblate pofilter)
- wrong-type | HeartBeat bn `measurement_output_template[zero]` | `Pulse: %2.1f (%d cycles in %2.1f seconds)` -> `স্পন্দন: %2.1f (%2.1f সেকেন্ডে %d চক্র)` (IllegalFormatConversionException, referenced; others: weblate pofilter)
- wrong-type | Material Files eu `file_job_extract_scan_notification_title_format[one]` | `Preparing to extract %1$,d files (%2$s)` -> `Fitxategi %1$ erauzteko prestatzen (%2$s)` (IllegalFormatConversionException, referenced; others: none)
- wrong-type | Material Files eu `file_job_extract_scan_notification_title_format[other]` | `Preparing to extract %1$,d files (%2$s)` -> `%1$ fitxategi erauzteko prestatzen (%2$s)` (IllegalFormatConversionException, referenced; others: none)
