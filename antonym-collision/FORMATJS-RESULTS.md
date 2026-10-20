# antonym-collision on a FormatJS descriptor source (Mattermost): results

Graded 2026-10-20 against [FORMATJS-PREREG.md](FORMATJS-PREREG.md), published 2026-10-19 before
l10n-guard 0.14.0 was built and before any Mattermost translation was compared. The job
`formatjs-eval-v1` ran from 12:27 to 12:30 UTC on 2026-10-20 in a sealed container, with the released
l10n-guard v0.14.0 (`l10n_guard.py` 113,752 bytes, sha256 `7d12df8c469090ae`), the v0.13.0 baseline
(sha256 `7f33af4abe3d599d`) and the pre-registration as fetched from `main` (7,081 bytes, sha256
`f254b56a976cb360`). Mattermost was taken from `master` at commit `be207f89` (2026-10-20); the four
control projects at the commits of the second held-out test. Its 12 offline tests passed.
Made by MV2 of Munim, Inc. with AI agents; P4 was graded by AI agents, not by native speakers (see
limits). Text CC BY 4.0; code Apache-2.0.

## Verdicts

| | Prediction | Result | Evidence |
|---|---|---|---|
| P0 | Mattermost's `en.json` is a descriptor file; at least 20 locale files parse | **HELD** | descriptor shape detected; 27 of 27 locale files parse (`en` and `en-AU` skipped) |
| P1 | At least 1,000 comparisons with 0.14.0; 0 with 0.13.0 on the same tarball | **HELD** | 25,515 and 0 |
| P2 | `en.json` vs `de.json`: under 5% of source keys reported missing with 0.14.0 | **HELD** | 18 of 8,657 (0.2%); 0.13.0 reported 17,299 of 17,314 missing and 8,624 extra |
| P3 | At least 1 warning across Mattermost's locales, at most 5.0 per 1,000 comparisons | **HELD** | 67 warnings, 2.63 per 1,000 |
| P4 | At least 60% of the judged sampled warnings are real (at least 5 judged) | **HELD** | 40 judged, 40 real, 0 not, 0 unsure: 100% |
| P5 | Controls raise exactly the 36 non-UPLOAD warnings of the second held-out test | **HELD** | 36 rows; none only in the new run, none only in holdout2 |

`check_catalog` and the evaluation's own call of `_antonym_collisions` agreed on every file of every
project (`consistent: true`).

## What the results decide (fixed in advance)

- P4 holding means the `real` rows are candidates to report to Mattermost, after reading its
  contribution and translation policy, and only once MV2's GitHub account is visible again. Reading
  the policy changed the route: Mattermost's contributor handbook now says that since v12.0 (October
  2026) translations are produced by an automated pipeline, that Weblate is no longer used for
  submitting translations, and that inaccuracies should be fixed by a pull request to the repository
  (https://handbook.mattermost.com/contributors/contributors/localization). No report has been sent.
- P1, P2, P3 and P5 holding means no 0.14.1 is needed: the FormatJS reader works, the key names match,
  the warning rate is inside the control range (1.01 to 3.08 per 1,000), and the controls are unchanged.

## Per project (l10n-guard 0.14.0)

| Project | Commit | Role | Locale files | Antonym pairs | Comparisons | Warnings | Per 1,000 |
|---|---|---|---|---|---|---|---|
| Mattermost webapp | `be207f89` | test | 27 | 945 | 25,515 | 67 | 2.63 |
| Jellyfin Web | `ee8efb41` | control | 105 | 30 | 1,972 | 2 | 1.01 |
| Uptime Kuma | `b092505f` | control | 77 | 24 | 975 | 3 | 3.08 |
| Rocket.Chat | `ad2047e7` | control | 67 | 304 | 9,902 | 27 | 2.73 |
| Bitwarden web | `9e54ce7b` | control | 64 | 92 | 5,838 | 4 | 0.69 |

With 0.13.0 the same Mattermost tarball gave 17,314 "source keys" (every `defaultMessage` and
`description` as its own key), 1,065 pairs and 0 comparisons, which is why the second held-out test
could not evaluate Mattermost. No two Mattermost locale files are byte-identical. All 67 warnings are
on keys that appear as string literals in the webapp source (`key1_used` and `key2_used` are `True`
on every row), so none is dead text.

Mattermost's 67 warnings by word class: PUBLIC 29, ARCHIVE 17, MUTE 7, ONLINE 5, FIRST 5, ENABLE 1,
START 1, IN 1, SHOW 1. By locale: ko 16, it 7, sv 6, ro 6, cs 5, pl 4, fi 3, pt-BR 3, vi 3, bg 2,
es 2, fa 2, hr 2, lt 2, zh-TW 2, nl 1, tr 1 (17 of the 27 locales).

## P4 hand grading

The pre-registered procedure: `sample.csv` holds 40 of the 67 Mattermost warnings, drawn with seed
140; each row is graded `real` (the shared translation says one side only, or neither clearly),
`not` (it honestly covers both states in that language) or `unsure`; share = real / (real + not).
The verdicts are in [formatjs-sample-graded.csv](formatjs-sample-graded.csv) (keys, verdict and a
note per row; the texts are in [formatjs-results/sample.csv](formatjs-results/sample.csv)).

Result: 40 real, 0 not, 0 unsure. Of the 40, 25 name the opposite state (for example Czech
`admin.plugin.disabling` reads "Enabling...", Turkish `installed_integrations.showSecret` reads
"Hide the password", Korean `channel_header.unmute` reads "Turn off channel notifications"), and 15
name neither state.

The largest group, 12 of the 40 sampled rows (21 of the 67 overall, in 10 locales: bg, es, fa, hr,
ko, lt, pt-BR, ro, vi, zh-TW), is one defect: the admin permission names
`admin.permissions.permission.convert_public_channel_to_private.name`,
`admin.permissions.permission.convert_private_channel_to_public.name` and
`admin.permissions.group.convert_public_channel_to_private.name` are translated with one generic
phrase ("Convert channels": `Convertir canales`, `Pretvori kanale`, `Konvertuoti kanalus`,
`Converter Canais`, `Conversia canalelor`, `Chuyển đổi kênh`, `轉換頻道`, `채널 변환`, ...). That is
not a translator's error: in Mattermost v8.0.0 all three English names were the single string
`"Convert Channels"`, and the English was later split into "Convert to private" and "Convert to
public" while these translations stayed as they were. The permission list in the System Console
therefore shows two permissions with the same name in those languages. Mattermost `master` on
2026-10-20 is after the switch to the automated translation pipeline, so the pipeline did not refresh
these strings either (it is documented as covering changed or new strings; whether the webapp
catalogs are in its scope is not stated).

Other notable rows:

- Italian and Swedish translate both the Unarchive menu item and the admin Unarchive button, and
  Czech the menu item, as "Archive channel" (`channel_header.unarchive`,
  `admin.channel_settings.channel_details.unarchiveChannel`).
- Finnish, Italian, Dutch, Polish and Brazilian Portuguese post "{username} archived the channel."
  when a channel is unarchived (`api.channel.restore_channel.unarchived`).
- Korean's "switch your status to Offline / Online" auto-responder dialog asks about "Do not disturb"
  in both, its Online status icon is labelled "Offline icon", and the Yes button for both says "Away"
  (`modal.manual_status.button_online` / `button_offline`, outside the sample).
- Polish describes both the LDAP first-name and last-name attributes as populating the "user name";
  Romanian uses "Nume:" (usually the family name) for both the First Name and Last Name attribute.
- Lithuanian, Vietnamese and Persian rows were graded without a fluent reader; their verdicts rest on
  the shared value being one generic phrase for two antonym keys, which needs no fluency to see.

## A pattern worth naming

The 21 "Convert channels" rows show a defect class that placeholder checks cannot see and that no
tool compared before: when a source string is split into two antonym variants, every translation of
the old string survives under both new keys and is wrong for at least one of them. Mattermost's own
`scripts/check_icu.mjs`, `formatjs verify` and lingualdev's `i18n-check` compare ICU variables and
tags message by message, so a stale but well-formed translation passes all of them. The
antonym-collision check finds it because the two keys share one value. This is one project and one
commit; whether the pattern is common elsewhere is an open question for a later held-out test on
other FormatJS descriptor sources.

## Limits

- Graders are AI agents, not native speakers. Lithuanian, Vietnamese and Persian had no fluent reader;
  a stricter reading of those 4 sampled rows as `unsure` leaves 36 of 36, still held.
- 100% is a sample statistic on 40 rows of one project at one commit; 12 of the 40 are one underlying
  defect, so the effective number of independent judgements is smaller than 40.
- The 39 word classes measure precision, not recall. Nothing here says how many wrong translations the
  check misses.
- Only the default FormatJS `extract` shape (`{id: {defaultMessage, description}}`) is handled; the
  crowdin, lokalise, transifex and smartling formatter shapes are not.
- `key1_used` / `key2_used` come from string literals in source files; keys built at runtime would be
  undercounted, but here every key was found.
- No defect has been reported to Mattermost. Before any report, each row must be re-checked against
  the files current at that time; the automated pipeline may have changed them.

## Files

- [formatjs-results/warnings.csv](formatjs-results/warnings.csv): all 103 warnings (67 Mattermost,
  36 controls) with both English texts, the shared value and the word class.
- [formatjs-results/sample.csv](formatjs-results/sample.csv): the 40 sampled Mattermost rows, as
  written by the job (blank verdicts).
- [formatjs-sample-graded.csv](formatjs-sample-graded.csv): the verdicts.
- [formatjs-results/summary.json](formatjs-results/summary.json) and
  [formatjs-results/stdout.txt](formatjs-results/stdout.txt): the job's own summary and log.
- [formatjs/eval_formatjs.py](formatjs/eval_formatjs.py), [formatjs/test_eval_formatjs.py](formatjs/test_eval_formatjs.py)
  and [formatjs/job.json](formatjs/job.json): the code and the job that ran it.
