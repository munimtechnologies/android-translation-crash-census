# l10n-guard 0.7.1 Android check on strings with look-alike percent signs

| repository | file | seen by hand | commit | lookalike-percent | placeholder-missing | all issues by code |
|---|---|---|---|---:|---:|---|
| Windscribe/Android-App | base/src/main/res/values-fa/strings.xml | ٪s (3 lines) | 2c585dd597 | 6 | 0 | extra-key/warning 2, lookalike-percent/error 6, missing-key/warning 4, tags/error 1, untranslated/warning 6 |
| Windscribe/Android-App | base/src/main/res/values-ar/strings.xml | ٪s (3 lines) | 2c585dd597 | 5 | 0 | empty/warning 1, extra-key/warning 2, lookalike-percent/error 5, missing-key/warning 4, untranslated/warning 6 |
| Windscribe/Android-App | base/src/main/res/values-de/strings.xml | control | 2c585dd597 | 0 | 0 | extra-key/warning 2, missing-key/warning 4, untranslated/warning 27 |
| threema-ch/threema-android | app/src/main/res/values-zh-rCN/strings.xml | ％d in a plural | d44a2b53b2 | 1 | 1 | lookalike-percent/error 1, placeholder-missing/error 1, tags/error 1, untranslated/warning 3 |
| threema-ch/threema-android | app/src/main/res/values-de/strings.xml | control | d44a2b53b2 | 0 | 1 | placeholder-missing/warning 1, tags/error 2, untranslated/warning 38 |
| TrackerControl/tracker-control-android | app/src/main/res/values-ja-rJP/strings.xml | ％d in a plural | 62642862f2 | 1 | 0 | lookalike-percent/error 1, missing-key/warning 20, untranslated/warning 5 |
| apk-editor/APK-Explorer-Editor | app/src/main/res/values-ar-rSA/strings.xml | ٪s (25 lines) | 988401012e | 25 | 4 | lookalike-percent/error 25, missing-key/warning 56, placeholder-missing/error 4 |
| Utazukin/Ichaival | app/src/main/res/values-ja/strings.xml | ％d in a plural (2 lines) | a59e67db5b | 4 | 0 | lookalike-percent/error 4, missing-key/warning 53, untranslated/warning 14 |

lookalike-percent and placeholder-missing issues, in full:

## Windscribe/Android-App base/src/main/res/values-fa/strings.xml

- ERROR lookalike-percent [connected_to]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [connecting_to]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [next_in_up]: %d is written "٪D" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [ping_time]: %d is written "٪D" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [set_this_protocol_as_preferred]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [trying_next_protocol]: %d is written "٪d" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost

## Windscribe/Android-App base/src/main/res/values-ar/strings.xml

- ERROR lookalike-percent [connected_to]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [connecting_to]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [next_in_up]: %d is written "٪d" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [set_this_protocol_as_preferred]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [trying_next_protocol]: %d is written "٪d" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost

## threema-ch/threema-android app/src/main/res/values-zh-rCN/strings.xml

- ERROR lookalike-percent [really_delete_thread_message[other]]: %d is written "％d" with the fullwidth percent sign ％ (U+FF05), which no formatter reads: the text is shown as written and the value is lost
- ERROR placeholder-missing [saving_media[other]]: placeholder(s) missing: %d

## threema-ch/threema-android app/src/main/res/values-de/strings.xml

- WARNING placeholder-missing [really_delete_thread_message[one]]: placeholder(s) missing: %d

## TrackerControl/tracker-control-android app/src/main/res/values-ja-rJP/strings.xml

- ERROR lookalike-percent [n_companies_found[other]]: %d is written "％d" with the fullwidth percent sign ％ (U+FF05), which no formatter reads: the text is shown as written and the value is lost

## apk-editor/APK-Explorer-Editor app/src/main/res/values-ar-rSA/strings.xml

- ERROR lookalike-percent [android_version]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [bundle_install_question]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [copying]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [decompiling]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [delete_question]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [deleting]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [explore_error_status]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [exploring]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [export_complete_message]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [exporting]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [install_question]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [installing]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [last_modified]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [preparing_apk]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [preparing_bundle_install]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [replace_question]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [resigned_apks_path]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [sdk_compile]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [sdk_minimum]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [signing]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [signing_question]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [signing_select_question]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [size]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [unknown_file_message]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [wrong_extension]: %s is written "٪s" with the Arabic percent sign ٪ (U+066A), which no formatter reads: the text is shown as written and the value is lost
- ERROR placeholder-missing [assembling]: placeholder(s) missing: %s
- ERROR placeholder-missing [building]: placeholder(s) missing: %s
- ERROR placeholder-missing [export_project_replace]: placeholder(s) missing: %s
- ERROR placeholder-missing [failed_smali_message]: placeholder(s) missing: %s

## Utazukin/Ichaival app/src/main/res/values-ja/strings.xml

- ERROR lookalike-percent [delete_archive_count[one]]: %d is written "％d" with the fullwidth percent sign ％ (U+FF05), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [delete_archive_count[other]]: %d is written "％d" with the fullwidth percent sign ％ (U+FF05), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [fullscreen_timeout_summary]: %s is written "％s" with the fullwidth percent sign ％ (U+FF05), which no formatter reads: the text is shown as written and the value is lost
- ERROR lookalike-percent [search_delay_summary]: %s is written "％s" with the fullwidth percent sign ％ (U+FF05), which no formatter reads: the text is shown as written and the value is lost
