# Inherited or introduced? Provenance of the Mattermost antonym-collision defects (pre-registration)

Pre-registered 2026-10-20 (about 21:40 UTC) by MV2 of Munim, Inc. The predictions, script and tests were
written with AI agents. Text licensed CC BY 4.0, code Apache-2.0.

## Question

Starting with v12.0 (October 2026), Mattermost translates its catalogs with an AI-driven pipeline instead
of Weblate ([handbook](https://handbook.mattermost.com/contributors/contributors/localization)). The
[FormatJS evaluation](FORMATJS-RESULTS.md) graded 40 warnings real on Mattermost `master` at
`be207f89725df343da628e859d1ef25acde02fbc` (2026-10-20): two opposite English labels (archive/unarchive,
mute/unmute, private/public and so on) share one translation. Were these defects already in the
human-translated catalogs before the pipeline ran, or did the pipeline put them there?

## What was read before writing this

- The handbook page above: the pipeline "produces translations for supported languages for all changed or
  new strings", and Mattermost Engineering reviews its PRs.
- The commit titles (not the diffs) of `webapp/channels/src/i18n/ko.json` on `master` since 2026-09-08.
- The descriptions of PR #38904 "Fill the gaps in the 21 locale catalogs" (merged 2026-10-01 as
  `f5b9b0ed4742ffac6dba6bb0f20680fe92b93b87`: adds 60,781 webapp translations; "No translation already on
  master is changed or reordered", except one key, `adminConsole.list.table.exactTime`, in six locales) and
  PR #39207 "Fix existing translation errors and add glossary terms" (merged 2026-10-19 as `57ea425`;
  fixes errors the translation agents found; its description names no archive/unarchive or mute/unmute fix).
- Our own graded results: the 40 rows of `formatjs-sample-graded.csv` and the 67 rows of the job's
  `warnings.csv`, both at `be207f89`. No locale file at any earlier commit was read.

## Snapshots

- **T** (target): `be207f89725df343da628e859d1ef25acde02fbc`, the commit graded.
- **B** (before the pipeline): the first parent of `f5b9b0e`, read from the GitHub API by the job.
  B is the last `master` state whose webapp catalogs are Weblate-era translations plus the
  deterministic clean-ups of September 2026 (#38231, #38412).

## Classes (per warning row: one locale, two keys that share one value at T)

- **INHERITED**: at B both keys have a non-empty value that differs from the English at B, and both
  equal their values at T.
- **INTRODUCED**: at B at least one of the two keys is missing, empty, or equal to its English source
  (so a translation added after B produced the shared value).
- **CHANGED**: both keys translated at B, but at least one value differs from its value at T.
- **UNREADABLE**: a file could not be fetched or parsed at B (reported, never counted as a class above).

## Predictions

- **R0** (method): at T, all 40 graded rows and all 67 warning rows are reproduced (both keys present
  with one identical value) from the locale files `webapp/channels/src/i18n/<locale>.json`; B resolves to
  one commit dated before 2026-10-01; no row is UNREADABLE.
- **R1**: at least 34 of the 40 graded-real rows (85%) are INHERITED.
- **R2**: all 12 graded-real rows in which a permission name keeps the old single "Convert Channels"
  translation (bg, hr, ko x3, lt x2, pt-BR, ro, vi, zh-TW x2) are INHERITED.
- **R3**: at most 3 of the 40 graded-real rows are INTRODUCED.
- **R4** (all 67 warnings, graded or not): at least 80% are INHERITED.

R1-R4 are tested only if R0 holds. A failed prediction is reported as failed. No graded row is dropped
or re-graded after the job runs.

## Why it matters, and why it is new

A whole-catalog consistency check is only needed if old defects survive a pipeline that fills gaps.
If R1 holds, the pipeline (and the agent review in #39207) inherited these defects rather than
creating them, so a check that looks only at a pipeline's new output cannot see them. We found no
published per-defect provenance of translation errors across a switch from community to AI-pipeline
translation (searched GitHub and the web for Mattermost translation pipeline quality, 2026-10-20).
Open Collective's one agent-locale defect predated its agents ([results](OC-LOCALES-RESULTS.md));
that was one row, and this is 40.

## Limits

One project, two snapshots. INHERITED says a value existed at B, not who wrote it or when.
INTRODUCED rows are attributed to "after B", which includes human edits as well as the pipeline.
Graders were AI agents, not native speakers (see [FORMATJS-RESULTS.md](FORMATJS-RESULTS.md)).
