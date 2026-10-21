# Inherited or introduced? Results for the four restored Mattermost locales

Results written 2026-10-21 (about 01:35 UTC) by MV2 of Munim, Inc., with AI agents, for the
[pre-registration](PROVENANCE-DROPPED-PREREG.md). Text licensed CC BY 4.0. Job output:
[provenance-dropped-results/](provenance-dropped-results/) (`provenance_dropped.csv`, `summary.json`,
`stdout.txt`).

## Run

Sealed job `mm-provenance-dropped-v2`, 2026-10-21 01:12-01:14 UTC: 8 offline tests passed, then the script
found the pre-registration on `main`, resolved B2 and read cs, fi, hr, lt and `en`.

- T = `be207f89725df343da628e859d1ef25acde02fbc` (2026-10-20, the same T as the
  [first provenance test](PROVENANCE-RESULTS.md)).
- B2 = `bbd208cffdc23be2bfd86e2338a1bc4b591247c2` (2026-09-04 15:58:37 UTC), the first parent of
  `e9379690d5873cbf65049fabaab22f1317696868` ([#38219](https://github.com/mattermost/mattermost/pull/38219),
  which removed these four locales).

## Predictions

| id | prediction | result | verdict |
|---|---|---|---|
| S0 | B2 dated on or before 2026-09-04; all 12 rows (8 graded) reproduced; none UNREADABLE or NOT_REPRODUCED | 12 rows, 8 graded, 0 unreadable or not reproduced, B2 dated 2026-09-04T15:58:37Z | **HELD** |
| S1 | all 4 hr and lt rows INHERITED | 4 of 4 | **HELD** |
| S2 | at least 4 of 5 cs rows INHERITED | 5 of 5 | **HELD** |
| S3 | at least 2 of 3 fi rows INTRODUCED or CHANGED (low confidence) | 0 of 3 | **FAILED** |

B2 is dated the same calendar day as the removal; the pre-registered rule was "on or before", so S0 holds.

## The 12 rows

Every row is INHERITED: both keys were translated at B2 (value differs from English at B2) and both values
are identical at T.

| locale | key 1 | key 2 | graded real | class |
|---|---|---|---|---|
| cs | `admin.plugin.disabling` | `admin.plugin.enabling` | yes | INHERITED |
| cs | `change_url.endWithLetter` | `change_url.startWithLetter` | yes | INHERITED |
| cs | `channel_header.delete` | `channel_header.unarchive` | yes | INHERITED |
| cs | `channel_header.unarchive` | `channel_settings.tab.archive` | no (not sampled) | INHERITED |
| cs | `shortcuts.browser.font_decrease` | `shortcuts.browser.font_increase` | no (not sampled) | INHERITED |
| fi | `admin.team_channel_settings.convertConfirmModal.toPrivateTitle` | `...toPublicTitle` | yes | INHERITED |
| fi | `api.channel.delete_channel.archived` | `api.channel.restore_channel.unarchived` | yes | INHERITED |
| fi | `delete_channel.confirm` | `unarchive_channel.confirm` | no (not sampled) | INHERITED |
| hr | `admin.permissions.group.convert_public_channel_to_private.name` | `admin.permissions.permission.convert_private_channel_to_public.name` | yes | INHERITED |
| hr | `admin.permissions.permission.convert_private_channel_to_public.name` | `admin.permissions.permission.convert_public_channel_to_private.name` | no (not sampled) | INHERITED |
| lt | `admin.permissions.group.convert_public_channel_to_private.name` | `admin.permissions.permission.convert_private_channel_to_public.name` | yes | INHERITED |
| lt | `admin.permissions.permission.convert_private_channel_to_public.name` | `admin.permissions.permission.convert_public_channel_to_private.name` | yes | INHERITED |

No row is INTRODUCED or CHANGED, so there is nothing to attribute to the period after B2 (which includes
#38944's validation reset, its agent gap fill and any later edit).

## Why S3 failed

S3 reasoned that Finnish's restored human coverage was low (20-31% per
[#38944](https://github.com/mattermost/mattermost/pull/38944)), so most Finnish strings, including these,
would have come from the agents. Coverage is a share of all strings, not of these ones: all three Finnish
pairs were already translated, with the same shared value, in the human-era catalog before the removal.
The prediction used a catalog-wide rate for a per-string question; that was the mistake.

## Both tests together (post hoc, not a test)

| | rows | graded real | INHERITED |
|---|---|---|---|
| first test, 13 locales at B (2026-10-01) | 55 | 32 | 55 |
| this test, 4 locales at B2 (2026-09-04) | 12 | 8 | 12 |
| **total** | **67** | **40** | **67** |

All 67 antonym-collision warnings that l10n-guard 0.14.0 raised at T, and all 40 graded-real defects among
them, were already in Mattermost's catalogs before its AI translation pipeline started, and none changed by
T. The first test's R1 (>= 34 of 40) is not re-graded by this, because its R0 failed; the combined count
is descriptive. For the four restored locales this also means the defects were deleted with the locales in
September and came back verbatim with the October restore.

## What it means

In Mattermost, every collision the checker found came from the human-era text and passed through an AI
pipeline that filled gaps and added new strings, and in four locales also through a removal and restore,
without being touched. A quality step that reviews only a pipeline's new output would see none of them;
a whole-catalog check does.

## Limits

- Four locales, 12 rows; one project.
- INHERITED says both values existed at B2 and match at T, not who wrote them (Weblate translations can
  include machine suggestions accepted by volunteers), and not that they were unchanged at every commit in
  between.
- The 67 rows are the checker's warnings, not every defect: recall is unknown.
- Graders were AI agents, not native speakers (see [FORMATJS-RESULTS.md](FORMATJS-RESULTS.md)).
