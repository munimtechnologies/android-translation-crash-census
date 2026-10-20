# Inherited or introduced? Results of the Mattermost provenance test

Results written 2026-10-20 (about 22:45 UTC) by MV2 of Munim, Inc., with AI agents, for the
[pre-registration](PROVENANCE-PREREG.md). Text licensed CC BY 4.0. Job output:
[provenance-results/](provenance-results/) (`provenance.csv`, `summary.json`, `stdout.txt`).

## Run

Sealed job `mm-provenance-v1`, 2026-10-20 21:46-21:48 UTC: 19 offline tests passed, then the script waited
for the pre-registration on `main`, resolved B and read 17 locales plus `en`.

- T = `be207f89725df343da628e859d1ef25acde02fbc` (2026-10-20, the commit graded in
  [FORMATJS-RESULTS.md](FORMATJS-RESULTS.md)).
- B = `751b8cb67b946baecb991b6ce5c04a5caecc39fe` (2026-10-01 08:06 UTC), the first parent of
  `f5b9b0ed4742ffac6dba6bb0f20680fe92b93b87` (#38904, the pipeline's first fill).

## Predictions

| id | prediction | result | verdict |
|---|---|---|---|
| R0 | all 67 rows reproduced at T, B before 2026-10-01, no row UNREADABLE | 67 rows, 40 graded, **12 UNREADABLE**, B dated 2026-10-01T08:06:00Z | **FAILED** |
| R1 | >= 34 of 40 graded rows INHERITED | 32 of 40 (8 unreadable) | not tested |
| R2 | all 12 Convert Channels rows INHERITED | 9 of 12 (3 unreadable) | not tested |
| R3 | <= 3 of 40 graded rows INTRODUCED | 0 of 40 | not tested |
| R4 | >= 80% of 67 rows INHERITED | 55 of 67 (12 unreadable) | not tested |

R0 failed on its own terms, so as pre-registered R1-R4 are reported as NOT TESTED. Two more R0 terms are
also worth stating plainly: B's date is 2026-10-01 08:06 UTC, the same calendar day as the pipeline merge,
not before it (the script compared dates by day, so this alone would also have failed R0); and every row
that could be read was reproduced at T.

## Why R0 failed

The Czech (`cs`), Finnish (`fi`), Croatian (`hr`) and Lithuanian (`lt`) catalogs return 404 at B. They were
not on `master` then: [#38219](https://github.com/mattermost/mattermost/pull/38219) removed them (and
four other experimental locales) on 2026-09-04, and
[#38944](https://github.com/mattermost/mattermost/pull/38944) brought them back on 2026-10-02, restoring
the human-era catalogs from the commit before #38219 and then filling the gaps with translation agents.
The pre-registration wrongly assumed all 17 graded locales existed at B; we did not check the file
history before writing it. This was found after the run, by reading the history of `cs.json` and the
description of #38944.

| locale | rows | graded | class |
|---|---|---|---|
| cs | 5 | 3 | UNREADABLE |
| fi | 3 | 2 | UNREADABLE |
| hr | 2 | 1 | UNREADABLE |
| lt | 2 | 2 | UNREADABLE |

The 12 rows, by key pair: cs `admin.plugin.disabling`/`enabling`, `change_url.endWithLetter`/
`startWithLetter`, `channel_header.delete`/`unarchive`, `channel_header.unarchive`/
`channel_settings.tab.archive`, `shortcuts.browser.font_decrease`/`font_increase`; fi
`convertConfirmModal.toPrivateTitle`/`toPublicTitle`, `api.channel.delete_channel.archived`/
`restore_channel.unarchived`, `delete_channel.confirm`/`unarchive_channel.confirm`; hr and lt the two
Convert Channels permission-name pairs each. The full keys are in `provenance-results/provenance.csv`.

A separate, newly pre-registered test reads these four locales at the commit before #38219:
[PROVENANCE-DROPPED-PREREG.md](PROVENANCE-DROPPED-PREREG.md).

## What the readable rows show (descriptive, not a test)

In the 13 locales that were on `master` at B, **every one of the 55 warning rows was INHERITED**: both
translated values were already in the catalog before the pipeline's first fill, and both are identical
at T. None was INTRODUCED and none CHANGED.

| locale | rows | graded | INHERITED |
|---|---|---|---|
| bg | 2 | 1 | 2 |
| es | 2 | 0 | 2 |
| fa | 2 | 0 | 2 |
| it | 7 | 4 | 7 |
| ko | 16 | 11 | 16 |
| nl | 1 | 1 | 1 |
| pl | 4 | 4 | 4 |
| pt-BR | 3 | 2 | 3 |
| ro | 6 | 2 | 6 |
| sv | 6 | 2 | 6 |
| tr | 1 | 1 | 1 |
| vi | 3 | 2 | 3 |
| zh-TW | 2 | 2 | 2 |
| **total** | **55** | **32** | **55** |

That includes all 32 readable graded-real defects and all 9 readable Convert Channels rows. Between B and
T these catalogs went through the gap fill (#38904), the new-strings run (#38945), the pt-BR fixes
(#39113) and an agent pass that fixed existing translation errors (#39207); none of these 55 value pairs
changed.

## What it means

For the locales that could be read, the antonym collisions came from the human-era catalogs and survived
an AI pipeline that fills "changed or new strings", and also a later agent review of existing
translations. A quality check that looks only at a pipeline's new output would not have seen any of
them. This matches the one Open Collective case ([OC-LOCALES-RESULTS.md](OC-LOCALES-RESULTS.md)), now
with 55 rows in one project.

## Limits

- R0 failed, so this is not a confirmed pre-registered result; the counts above are descriptive.
- One project, two snapshots. INHERITED says a value existed at B, not who wrote it or when (Weblate
  translations can include machine suggestions accepted by volunteers).
- The 55 rows are the checker's warnings, not every defect: recall is unknown.
- Graders were AI agents, not native speakers (see [FORMATJS-RESULTS.md](FORMATJS-RESULTS.md)).
