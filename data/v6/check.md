# census 0.4.0 checks against the hand audit

| repo | locale | key | expected | rows found | verdicts | result |
|---|---|---|---|---|---|---|
| jellyfin/jellyfin-android | all | download_remove_description[ | gone | 1 | crash | MISS |
| session-foundation/session-android | b+si+LK | emojiReactsCountOthers[one] | reported | 1 | crash-if-text | ok |
| session-foundation/session-android | b+si+LK | emojiReactsCountOthers[other] | reported | 1 | crash-if-text | ok |
| rascarlo/AURdroid | es | plurals_formatted_package_found[one] | reported | 1 | crash-if-text | ok |
| rascarlo/AURdroid | es | plurals_formatted_package_found[other] | reported | 1 | crash-if-text | ok |
| d4rken-org/sdmaid-se | ka-rGE | corpsefinder_watcher_notification_delete_result[one] | reported | 1 | crash-if-text | ok |

5 of 6 checks passed.
