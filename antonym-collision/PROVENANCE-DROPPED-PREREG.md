# Provenance of the Mattermost defects in four restored locales (pre-registration)

Pre-registered 2026-10-20 (written about 22:25 UTC) by MV2 of Munim, Inc. The predictions, script and
tests were written with AI agents. Text licensed CC BY 4.0, code Apache-2.0.

**Publication note.** This page was first sent for publication at 22:28 UTC on 2026-10-20, but that
commit failed on a GitHub race (HTTP 422, "Update is not a fast forward") because it followed two other
commits to this repository by a few seconds. The sealed job `mm-provenance-dropped-v1` waited 20 minutes
for this page, never saw it and exited before reading any Mattermost catalog, as designed. The
predictions, method, script, tests and inputs below are unchanged. Only this note, the writing time
(earlier text said "about 22:45 UTC", an estimate) and the job name (`mm-provenance-dropped-v2`) were
added or corrected. No value of the four locales at B2 was read in between.

## Why this follow-up exists

The [provenance test](PROVENANCE-PREREG.md) failed its method check R0
([results](PROVENANCE-RESULTS.md)): the Czech, Finnish, Croatian and Lithuanian catalogs returned 404 at
B (`751b8cb6`, 2026-10-01), so 12 of the 67 warning rows (8 of the 40 graded-real rows) could not be
classed. The pre-registration assumed every graded locale was on `master` at B. It was not:

- [#38219](https://github.com/mattermost/mattermost/pull/38219) "Remove EnableExperimentalLocales and the
  experimental locales" (merged 2026-09-04 as `e937969`) deleted these catalogs.
- [#38944](https://github.com/mattermost/mattermost/pull/38944) "Bring back eight dropped locales as
  (Experimental) languages and fill their catalogs" (merged 2026-10-02 as `70c1732`) restored da, be, cs,
  hr, fi, lt, nb-NO and pt. Its description says the base catalogs were restored verbatim from the commit
  before #38219, then synced to `en.json`; strings that failed validation were cleared and retranslated;
  the remaining gaps (32,557 webapp strings) were filled by translation agents. It gives the restored
  human coverage as 60-93% for five of the eight locales and 20-31% for hr, fi and pt.

So for these four locales the right "before" snapshot is **B2 = the first parent of `e937969`**, the last
`master` state with their human-era catalogs. R1-R4 of the first test stay NOT TESTED; this is a new,
separate test of the 12 rows it could not read.

## What was read before writing this

- The job output of the first test: the 55 readable rows (all INHERITED) and the 12 unreadable rows
  (cs 5, fi 3, hr 2, lt 2). No value of any of the four locales at B2, or at any commit other than
  `be207f89`, was read.
- The commit titles of `webapp/channels/src/i18n/cs.json` on `master` (which led to #38219 and #38944),
  and the description of #38944 summarised above.
- Our grading notes for the 8 graded rows (in `provenance/graded.csv`): the hr and lt rows share one
  stale translation of the old single English permission name "Convert Channels".

## Method

Unchanged from the first test: `provenance.classify` on each row, with B2 in place of B and the English
catalog read at B2. The job (`provenance/provenance_dropped.py`, inputs `provenance/dropped_rows.csv`)
resolves `e937969` and its first parent through the GitHub API and reads
`webapp/channels/src/i18n/<locale>.json` at B2 and at T = `be207f89725df343da628e859d1ef25acde02fbc`.
INHERITED here means both values existed, translated, at B2 and are unchanged at T, i.e. the defect came
back with the restore of human-era text. INTRODUCED or CHANGED means the shared value appeared after B2
(the restore's validation reset, the agents' gap fill, or a later edit).

## Predictions

- **S0** (method): B2 resolves to one commit dated on or before 2026-09-04; all four catalogs and `en`
  are readable at B2; all 12 rows (8 graded) are reproduced at T; no row is UNREADABLE or NOT_REPRODUCED.
- **S1**: all 4 hr and lt rows (Convert Channels permission names) are INHERITED. Reason: a stale
  translation of the pre-split English name can only come from the human era.
- **S2**: at least 4 of the 5 cs rows are INHERITED (Czech's restored human coverage is high).
- **S3**: at least 2 of the 3 fi rows are INTRODUCED or CHANGED (Finnish's restored human coverage was
  20-31%, so most Finnish strings came from the agents). Low confidence.

S1-S3 are tested only if S0 holds. Post hoc and not a test: the job also reports how many of all 40
graded rows are INHERITED across B and B2 together (the first test's R1 threshold was 34); because R0
failed, R1 is not re-graded by this number.

## Limits

Four locales, 12 rows. INHERITED says a value existed at B2, not who wrote it. INTRODUCED or CHANGED
cannot tell the restore's agents from later human edits. Graders were AI agents, not native speakers.
