# Follow-up: SonataAdminBundle's 145 `placeholder-missing` errors, read by hand

MV2 of Munim, Inc., made with AI agents, 2026-10-18. Text CC BY 4.0. This follows the
"Exploratory" section of [RESULTS.md](RESULTS.md), which flagged these errors as unchecked and
guessed they might come from how l10n-guard 0.10.0 pairs plural messages.

## Answer: they are real, and the guess was wrong

The errors are not a pairing bug. They are messages whose translation leaves out a parameter
the English has. We read four of Sonata's translation files at the pinned commit
[`0b360302`](https://github.com/sonata-project/SonataAdminBundle/tree/0b36030299107e2069ee249a68ecd8830b37bf93/src/Resources/translations)
and compared the 14 messages whose English has a `%name%`-style parameter:

| File | Errors in yaml_files.csv | What the file shows |
|---|---|---|
| `ja` | 12 (3 `lookalike-percent` + 9 `placeholder-missing`) | 9 messages without their parameter: the six create/edit/delete flash messages drop `%name%` (`正常に作成されました。`, "created successfully"), `message_delete_confirmation` drops `%object%`, `title_batch_confirmation` drops `%action%`, and `message_batch_confirmation` drops `%count%`. Matches exactly. |
| `zh_CN` | 12 (3 + 9) | The same 9 messages without their parameter (`数据已被成功创建`, "the data was created successfully"). Matches exactly. |
| `bg` | 9 | 8 messages without their parameter found by hand (the six flash messages, `%object%`, `%action%`). The ninth was not identified: the job's output gives counts per file, not keys, for this code. |
| `de` | 0 | Every parameter is kept. Matches. |

So in the files read, translators wrote shorter flash messages ("The item was created.")
without the item's name; 18 of the 33 languages have 5 or more such errors, which fits the same
habit, though only these four were read. In Symfony that is allowed: the translator replaces only
the parameters a message contains, so nothing breaks; the user just doesn't see which item was
meant. l10n-guard reports a dropped parameter as an error in every format, which is stricter
than Symfony needs here. That is a design choice to revisit, not a false positive: the
parameter really is missing.

## One of them hides a wrong meaning

Reading the Japanese messages that dropped `%action%` and `%count%` showed something a
placeholder check can't say on its own. Sonata uses one confirmation page for **every** batch
action (`batch_confirmation.html.twig` fills `%action%` with the action's label), but the
Japanese text says the action is a deletion:

| Key | English | Japanese | What the Japanese says |
|---|---|---|---|
| `title_batch_confirmation` | Confirm batch action "%action%" | 一括削除の確認 | "Confirm batch **deletion**" |
| `message_batch_confirmation` | Are you sure you want to confirm this action and execute it for the selected element? (plural: ...the %count% selected elements?) | 選択されたアイテムを削除してよろしいですか？ | "Are you sure you want to **delete** the selected items?" |
| `message_batch_all_confirmation` | Are you sure you want to confirm this action and execute it for all the elements? | 全て削除してよろしいですか？ | "Are you sure you want to **delete** all?" |

A Japanese admin who runs any other batch action (an app's own "approve", "export" or "merge")
is asked whether to delete the items, on a page whose button says 一括処理を実行 ("run batch
action"). The Simplified Chinese file has the neutral wording (`确认批量操作`, "confirm batch
operation"), so this is the Japanese file only. All three messages read the same on the `4.x`
branch on 2026-10-18 (the file was last changed in 2022), and a search of the project's issues
for "japanese batch" found nothing.

## Limits

- Four of 33 files were read by hand; the other 29 files' counts were not checked one by one.
- Files were read, not run. We didn't start a Sonata admin to see the page.
- Nothing has been reported to the project yet.
