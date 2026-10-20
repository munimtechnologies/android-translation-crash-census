# Third held-out test of the antonym-collision check (five react-intl projects): results

Graded 2026-10-20 against [HOLDOUT3-PREREG.md](HOLDOUT3-PREREG.md), published before any
translation of the five projects was compared. The job `holdout3-eval-v1` ran from 18:07 to 18:09 UTC
on 2026-10-20 in a sealed container, with the released l10n-guard v0.14.0 (`l10n_guard.py` 113,752
bytes, sha256 `7d12df8c469090ae`) and the pre-registration as fetched from `main` (6,949 bytes, sha256
`8390d71389ea4562`). Its 16 offline tests passed. Made by MV2 of Munim, Inc. with AI agents; P3 and
P4 were graded by AI agents, not by native speakers (see limits). Text CC BY 4.0; code Apache-2.0.

## Verdicts

| | Prediction | Result | Evidence |
|---|---|---|---|
| P0 | Every reference parses; at least 10 locale files per project, at least 120 in all | **HELD** | Mastodon 104, BigBlueButton 60, Strapi 34, Umami 52, Open Collective 18: 268 |
| P1 | At least 10,000 comparisons pooled | **HELD** | 12,037 |
| P2 | Pooled rate 0.5 to 5.0 per 1,000, and at least 3 of the 5 projects warned | **HELD** | 15 warnings, 1.25 per 1,000; Mastodon, BigBlueButton and Open Collective warned |
| P3 | At least 60% of judged warnings are real (at least 5 judged) | **HELD** | 15 judged, 15 real, 0 not, 0 unsure: 100% |
| P4 | At least 20% of the real rows name neither side (at least 10 real rows) | **FAILED** | 0 of 15 |
| P5 | At least 80% of warned rows have both keys as literals in source | **HELD** | 15 of 15, Open Collective included (3 of 3) |

`check_catalog` and the evaluation's own call of `_antonym_collisions` agreed on every file
(`consistent: true`). There were only 15 warnings, so `sample.csv` holds all of them and every
warning was graded.

## Per project (l10n-guard 0.14.0)

| Project | Ref | Commit | Locale files | Antonym pairs | Comparisons | Warnings | Per 1,000 |
|---|---|---|---|---|---|---|---|
| Mastodon | `main` | `ff9c250c` | 104 | 96 | 5,734 | 8 | 1.40 |
| BigBlueButton HTML5 client | `develop` | `302f514f` | 60 (1 unparsed) | 109 | 4,248 | 4 | 0.94 |
| Strapi admin | `develop` | `61d63100` | 34 | 20 | 438 | 0 | 0.00 |
| Umami | `master` | `e92fdab9` | 52 | 12 | 573 | 0 | 0.00 |
| Open Collective frontend | `main` | `679f61f0` | 18 | 58 | 1,044 | 3 | 2.87 |

By word class: MUTE 9, ARCHIVE 3, NEXT 2, SHOW 1. The pooled rate (1.25 per 1,000) sits inside the
range of the earlier projects (0.69 to 3.08; Mattermost 2.63).

## P3 hand grading

The verdicts are in [holdout3-sample-graded.csv](holdout3-sample-graded.csv) (keys, verdict and an
ASCII note per row; the texts are in [holdout3-results/sample.csv](holdout3-results/sample.csv)).
All 15 are real: each shared translation states one side of the pair.

- **BigBlueButton (4 rows).** Bengali and Tamil label both the Mute and the Unmute button of the
  actions bar "Mute"; Malayalam and Tamil label both the "Mute user" and "Unmute user" menu items
  "Mute user". All four are also present in the released `v4.0.x-release` branch (checked
  2026-10-20), not only in `develop`.
- **Mastodon (8 rows).** Greek and Kurmanji "Mute notifications" for both the mute and unmute
  shortcuts; Italian "Muta" on both video controls; Basque "Hide boosts in timeline" on the Show
  boosts menu item; Macedonian one phrase for "Mute @{name}" and "Unmute @{name}"; Burmese "forward"
  on both lightbox buttons (two rows, one defect: `lightbox.previous`) and "shut the conversation" for
  both Mute and Unmute conversation. Mastodon's AI policy does not accept issues or pull requests
  that result from running an AI tool over its code, so these rows are published as data only and
  will not be reported to Mastodon by MV2.
- **Open Collective (3 rows).** Spanish and Chinese show "Archive ..." on the Unarchive button, and
  Chinese "Archive {name}" as the Unarchive dialog header. These are the same warnings that the
  Open Collective within-project test ([OC-LOCALES-PREREG.md](OC-LOCALES-PREREG.md)) will report;
  they are discussed there.

Counting the Burmese pair once, the 15 rows are 14 distinct defects in 11 locales of 3 projects.

## P4: the "neither" signature did not recur

In Mattermost, 15 of the 40 real sampled rows named neither side, and 21 of its 67 warnings were one
stale string: an English message later split into two antonyms ("Convert to private" / "Convert to
public") whose old translation survived under both keys ([FORMATJS-RESULTS.md](FORMATJS-RESULTS.md)).
P4 asked whether that signature shows up in other react-intl projects. It did not: 0 of 15 real
rows name neither side. Every defect here is the ordinary kind, one side's translation copied to its
opposite, and 9 of the 15 are Mute / Unmute. This is a negative result for the generality of the
split-source mechanism: on this evidence it is a Mattermost finding, not a pattern of react-intl
projects. The prediction stays recorded as FAILED, and no `SPLIT-SOURCE.md` write-up follows.

## A side finding: BigBlueButton's Catalan file on `develop` is not JSON

The one unparsed file, `bigbluebutton-html5/public/locales/ca.json` on `develop`, contains two
leftover git merge-conflict lines (`<<<<<<< HEAD` after the `app.audio.captions.select.af-ZA` entry
and `=======` after `app.audio.captions.select.en-GB`, with no closing marker), so both sides of the
captions language list are kept: `app.audio.captions.select.sq-AL` appears twice, once as "Albanès"
and once as "Albanian". The lines arrived with merge commit `9f1cb0d5` (2025-03-21, "Merge branch
'v3.0.x-release' ... into guest-breakouts-layout-fix"); its first parent `5ecd6257` has no markers,
and no later commit has touched the file on `develop`. The released `v4.0.x-release` branch has a
larger `ca.json` with no conflict marker in the first 100,000 characters that were read, so released
versions are most likely not affected; `develop`'s copy is 19 months old and cannot be parsed. Checked by reading the raw files on 2026-10-20; nothing has been
reported to BigBlueButton.

That also qualifies BigBlueButton's row above: its locale files were read from `develop`, which can
lag the release branch where Transifex updates land. The four BigBlueButton warnings were re-checked
on `v4.0.x-release` and are present there too.

## Running total of the check's precision

Outside the UPLOAD class (removed in 0.13.0), every graded antonym-collision warning so far has been
real: 49 of 49 in the second held-out test, 40 of 40 in Mattermost and 15 of 15 here, 104 of 104 in
all. These are AI-agent gradings of warnings the check raised; they say nothing about how many
defects it misses.

## Limits

- Graders are AI agents working in MV2's name, not native speakers. Burmese, Macedonian, Kurmanji,
  Malayalam and Tamil had no fluent reader; their verdicts rest on one phrase standing for two
  opposite actions. For Macedonian the side the phrase reads as was not settled. Reading those 8 rows
  as `unsure` leaves 7 of 7 real, so P3 would still hold; P4 would be NOT TESTED (fewer than 10 real
  rows) rather than FAILED.
- 15 warnings across five projects is a small count, and Strapi and Umami raised none, so this says
  little about those two.
- One commit per project, BigBlueButton from `develop` (see above); English variants were skipped.
- `neither` versus `one side` is a judgement about the shared text, not a check of each project's git
  history.
- Open Collective's results here were graded before the within-project test ran (its first run
  stopped on a failing offline test; see the Open Collective results page when published).

## Files

- [holdout3-results/warnings.csv](holdout3-results/warnings.csv): all 15 warnings with both English
  texts, the shared value, the word class and whether each key is used in source.
- [holdout3-results/sample.csv](holdout3-results/sample.csv): the same 15 rows as written by the job
  (blank verdicts).
- [holdout3-sample-graded.csv](holdout3-sample-graded.csv): the verdicts.
- [holdout3-results/summary.json](holdout3-results/summary.json) and
  [holdout3-results/stdout.txt](holdout3-results/stdout.txt): the job's own summary and log.
- [holdout3/eval_holdout3.py](holdout3/eval_holdout3.py), [holdout3/test_eval_holdout3.py](holdout3/test_eval_holdout3.py)
  and [holdout3/job.json](holdout3/job.json): the code and the job that ran it.
