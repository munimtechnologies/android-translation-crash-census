# Census findings compared

| | old | new |
|---|---:|---:|
| crash rows | 382 | 360 |
| crash-if-text rows | 190 | 93 |
| reachable crash rows (formatted) | 250 | 232 |
| repositories with a crash | 99 | 95 |

## Crash rows no longer reported: 27

- Wikipedia: 11
- Tallybook: 9
- Cashiro: 4
- Automation: 2
- NightDream: 1

| app | locale | key | use | exception |
|---|---|---|---|---|
| Automation | de | `httpParametersExplanation` | referenced | IllegalFormatConversionException |
| Automation | nl | `httpParametersExplanation` | referenced | UnknownFormatConversionException |
| NightDream | es-rAR | `copy_images` | formatted | UnknownFormatConversionException |
| Tallybook | tr | `message_backup_creation_failed` | formatted | FormatFlagsConversionMismatchException |
| Tallybook | tr | `message_backup_restoring_failed` | formatted | FormatFlagsConversionMismatchException |
| Tallybook | tr | `message_data_export_failed` | formatted | FormatFlagsConversionMismatchException |
| Tallybook | tr | `message_data_import_failed` | formatted | FormatFlagsConversionMismatchException |
| Tallybook | tr | `message_error_legacy_upgrade_failed` | formatted | FormatFlagsConversionMismatchException |
| Tallybook | tr | `notification_content_backup_error_internal` | formatted | FormatFlagsConversionMismatchException |
| Tallybook | tr | `notification_content_error_message` | formatted | FormatFlagsConversionMismatchException |
| Tallybook | tr | `setting_summary_exchange_rate_api_key` | formatted | FormatFlagsConversionMismatchException |
| Tallybook | tr | `setting_summary_exchange_rate_update` | formatted | FormatFlagsConversionMismatchException |
| Cashiro | is | `duration_hours_minutes` | formatted | IllegalFormatConversionException |
| Cashiro | is | `duration_minutes_seconds` | formatted | IllegalFormatConversionException |
| Cashiro | is | `duration_seconds` | formatted | IllegalFormatConversionException |
| Cashiro | vi | `duration_hours_minutes` | formatted | IllegalFormatConversionException |
| Wikipedia | da | `year_in_review_slide_app_icon_body_unlock` | formatted | MissingFormatArgumentException |
| Wikipedia | da | `year_in_review_slide_most_read_english_articles_body[other]` | formatted | MissingFormatArgumentException |
| Wikipedia | in | `temp_account_edit_status` | formatted | MissingFormatArgumentException |
| Wikipedia | pt | `temp_account_edit_status` | formatted | MissingFormatArgumentException |
| Wikipedia | qq | `error_blocked_by` | unreferenced | MissingFormatArgumentException |
| Wikipedia | qq | `error_blocked_footer` | unreferenced | MissingFormatArgumentException |
| Wikipedia | qq | `temp_account_edit_status` | formatted | MissingFormatArgumentException |
| Wikipedia | qq | `year_in_review_reading_list_dialog_message` | unreferenced | MissingFormatArgumentException |
| Wikipedia | qq | `year_in_review_slide_app_icon_body_unlock` | formatted | MissingFormatArgumentException |
| Wikipedia | ro | `temp_account_edit_status` | formatted | MissingFormatArgumentException |
| Wikipedia | ru | `temp_account_edit_status` | formatted | MissingFormatArgumentException |

## New crash rows: 5

- Commons: 4
- NewPipe: 1

| app | locale | key | use | exception |
|---|---|---|---|---|
| NewPipe | in | `sign_in_confirm_not_bot_error` | referenced | MissingFormatArgumentException |
| Commons | b+nds+NL | `about_improve` | formatted | IllegalFormatConversionException |
| Commons | haw | `about_improve` | formatted | IllegalFormatConversionException |
| Commons | hrx | `about_improve` | formatted | IllegalFormatConversionException |
| Commons | hsb | `about_improve` | formatted | IllegalFormatConversionException |
