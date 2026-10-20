# Agent-kept versus Crowdin-kept locales in one project: Open Collective (results)

Graded 2026-10-20 against [OC-LOCALES-PREREG.md](OC-LOCALES-PREREG.md). The job `oc-locales-v2` ran
from 19:27 to 19:29 UTC on 2026-10-20 in a sealed container, with the released l10n-guard v0.14.0
(`l10n_guard.py` 113,752 bytes, sha256 `7d12df8c469090ae`) and the pre-registration as fetched from
`main` (7,433 bytes, sha256 `c7a98d60c1da9a21`). Its offline tests passed. Made by MV2 of Munim,
Inc. with AI agents; Q3 was graded by AI agents, not by native speakers. Text CC BY 4.0; code
Apache-2.0.

## Two things to know first

- **The first run failed.** `oc-locales-v1` (18:35 UTC) stopped in its own offline tests before
  downloading anything: `test_wilson` compared a computed float with `==` (0.9999999999999999 against
  1.0). The test was changed to an approximate comparison and the job re-run as `oc-locales-v2`;
  `oc_locales.py` itself was not changed.
- **The three warnings were read before this job ran.** Open Collective was also one of the five
  projects in the [third held-out test](HOLDOUT3-RESULTS.md), whose results came back at 18:08 UTC
  and were graded while `oc-locales-v1` had failed. Its three Open Collective rows are the same three
  warnings reported here, at the same commit, and their grades are reused. So Q3's grading was not
  blind to this job's output. The machine-checked predictions Q0 to Q2 were not affected: they were
  fixed in code before either job ran.

## Verdicts

| | Prediction | Result | Evidence |
|---|---|---|---|
| Q0 | `en.json` parses, at least 18 locale files parse, agent group exactly de, es, fr, pt-BR | **HELD** | 18 locale files parsed; workflows for de, es, fr, pt-BR |
| Q1 | The four agent locales carry at least half of all comparisons | **FAILED** | 232 of 1,044 (22.2%) |
| Q2 | The two groups' 95% Wilson intervals overlap (at least 500 comparisons each and 5 warnings) | **NOT TESTED** | agent 1 / 232, Crowdin 2 / 812: 3 warnings in all |
| Q3 | At least 60% of judged warnings are real (at least 5 judged) | **NOT TESTED** | 3 judged, 3 real |
| Q4 | Among real rows with two hashed ids, under 20% name neither side (at least 5 such rows) | **NOT TESTED** | 0 rows with hashed ids: all 3 warnings are between named keys |

## Per locale (l10n-guard 0.14.0, commit `679f61f0`)

5,025 source keys, 58 antonym pairs. Every locale file carries every key, so every locale has 58
comparisons; the column that says how much was actually translated is "both translated".

| Group | Locales | Comparisons | Both translated | Warnings | Per 1,000 comparisons |
|---|---|---|---|---|---|
| Agent (de, es, fr, pt-BR) | 4 | 232 | 227 | 1 (es) | 4.31 (95% 0.76 to 24.0) |
| Crowdin (14 locales) | 14 | 812 | 250 | 2 (zh) | 2.46 (95% 0.68 to 8.94) |

Per-locale counts are in [oc-locales-results/locales.csv](oc-locales-results/locales.csv).

## Why Q1 failed

The pre-registration counted a comparison whenever both values of a pair are non-blank, the
definition the held-out tests use. It did not foresee that Open Collective writes every key into
every locale file and leaves untranslated keys equal to the English. So each Crowdin locale got 58
comparisons even where it had translated only 4 of the 58 pairs (Catalan). Counting only pairs with
both sides translated (not pre-registered), the agent share is 227 of 477 (47.6%), still under half,
so Q1 fails on either count.

The reasoning behind Q1 was also wrong: it expected Crowdin translators to have done core UI strings
first, so that antonym pairs would be translated well above each locale's overall completion. They
weren't. The fourteen Crowdin locales have 31.1% of their keys translated (21,847 of 70,350) and 30.8%
of their antonym pairs translated on both sides (250 of 812).

## Q3 grading: all three are real

The verdicts are in [oc-locales-graded.csv](oc-locales-graded.csv); the texts are in
[oc-locales-results/warnings.csv](oc-locales-results/warnings.csv).

- **Spanish (agent group):** the Unarchive button `collective.unarchive.button` reads "¿Estás seguro
  que quieres archivar ...", "Are you sure you want to archive ...", the same text as
  `collective.archive.title`.
- **Chinese (Crowdin):** the Unarchive dialog header `unarchive.modal.header` reads "归档 {name}",
  "Archive {name}", and the Unarchive button `collective.unarchive.button` reads "归档..." ("Archive
  ..."), the same as the Archive title.

All three state one side of the pair (Archive), so the user is shown "Archive" on a control that
unarchives. There are 3 defects in 2 locales, all in the ARCHIVE class.

## The one agent-locale warning was not made by the agents

The agent workflows only translate strings that still match English and never edit an existing
translation. So the Spanish row could be the agents' work or an older translation they kept. The
Spanish file's history settles it (read 2026-10-20):

- At `915c869` (2026-08-25), before both AI batches, `collective.unarchive.button` already had the
  "archivar" text, identical to `collective.archive.title`.
- It was the same after the Cursor agent batch `99118fc` ("Spanish translations batch (288 strings,
  94% complete)", #12371, 2026-09-07) and is the same at `679f61f0` (2026-10-20). The agent
  workflows came with #12393 (2026-09-14).

So none of the three warnings in this project was made by an AI pipeline. The test also shows the
other side of that design: an agent that only fills strings still equal to English keeps every older
defect in the locales it now owns, so the Spanish one was carried into a "100% complete" locale.
An antonym check run over the whole catalog, not just the new strings, would have flagged it.

## What this says, and what it doesn't

- With 3 warnings, nothing can be said about whether AI-kept or Crowdin-kept locales collide more
  often. The pre-registration called Q2 weak in advance, and it was not even testable.
- Q4, the mechanism check for the "neither" signature seen in Mattermost
  ([FORMATJS-RESULTS.md](FORMATJS-RESULTS.md)), could not be run: no warning involved a hashed
  id. The third held-out test had already found no "neither" row in five react-intl projects. As
  the pre-registration fixed in advance, the census README will describe that signature as seen in
  Mattermost only and not tested here.
- **Effect on the third held-out test's rate.** Its Open Collective figure (1,044 comparisons) uses
  the same definition, so 567 of its comparisons involve at least one value still equal to the English.
  Leaving those out moves that test's pooled rate from 1.25 to 1.31 per 1,000 (15 of 11,470). Whether
  other projects' files also carry English fallbacks was not checked. Future pre-registrations should
  count only pairs with both sides translated.

## Limits

- One project at one commit; four agent locales, which are also the four complete ones, so group and
  completeness are confounded.
- The graders are AI agents, not native speakers. Spanish and Chinese were read directly, and each
  verdict rests on the plain verb "archive" appearing on an Unarchive control.
- The grades were made before this job ran (see above).
- Six-character ids made only of letters are classed `ambiguous` by design; that did not matter
  here, since all three warnings are between named keys.
- The Chinese rows' history was not read. Whether people on Crowdin or a machine-translation step
  made them is unknown.
- Nothing has been reported to Open Collective yet.

## Files

- [oc-locales-graded.csv](oc-locales-graded.csv): the three verdicts (keys, verdict, ASCII note).
- [oc-locales-results/warnings.csv](oc-locales-results/warnings.csv),
  [oc-locales-results/locales.csv](oc-locales-results/locales.csv),
  [oc-locales-results/summary.json](oc-locales-results/summary.json) and
  [oc-locales-results/stdout.txt](oc-locales-results/stdout.txt): the job's outputs and log.
- [oc-locales/oc_locales.py](oc-locales/oc_locales.py), [oc-locales/test_oc_locales.py](oc-locales/test_oc_locales.py)
  and [oc-locales/job.json](oc-locales/job.json): the code and the job that ran it.
