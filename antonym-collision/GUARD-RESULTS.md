# l10n-guard 0.12.0 antonym-collision warning: results

Graded on 2026-10-19 against the [pre-registration](GUARD-PREREG.md), which
was published on 2026-10-19 before the build or evaluation ran. The job
(`l10n-guard-0120-v2`) ran from 13:38 to 13:40 UTC in a sealed container. Made
by MV2 of Munim, Inc. with AI agents; G4 was graded by AI agents, not by
native speakers (see limits). Text CC BY 4.0; code Apache-2.0.

## Verdicts

| | Prediction | Result | Evidence |
|---|---|---|---|
| G0 | 7 tarballs download; each new project has its English reference and >=10 parsing locale files | **HELD** | all seven downloaded; locale files: Excalidraw 56, Immich 87, Lobe Chat 969, Element Web 40, Jitsi Meet 59; none unparsed |
| G1 | patch applies to 0.11.0 on main; 10 existing test files pass unchanged; U1-U10 pass | **HELD** | all 14 steps exit 0: the patch (0.11.0 on main, 107,754 bytes, sha256 fc917bb2487d09c7), the ten test files fetched from main (184 tests, 1 skipped, as in the 0.11.0 build), `test_0120.py` (11 tests) |
| G2 | NocoBase @10810697 + Mastodon @cab53a59 warnings == the 27 flagged rows of collisions.csv | **HELD** | published 27, guard 27, missing none, extra none |
| G3 | >=20 warnings on the five new projects, from >=3 of 5 | **FAILED** | 19 warnings, from 4 of 5 projects; one short of the bar |
| G4 | >=60% of judged sample rows are real defects; >=20 judged, else "not tested" | **NOT TESTED** | only 19 warnings exist, so 19 judged; 13 of 19 (68%) real, but the bar of 20 judged was not met |
| G5 | >=50% of new-project warnings have both keys as code literals | **HELD** | 18 of 19 (95%) |

`check_catalog` and the evaluation's own call of `_antonym_collisions` agreed
on every file.

Release rule (fixed in advance): 0.12.0 ships only if G1 and G2 hold, and not at
all if G4 fails. Decision: **released as v0.12.0**, because G1 and G2 held and
G4 did not fail. G4 was not tested, so the release rests on the hand reading of
the original scan and on the 68% seen here, not on a passed precision test.

## Per project

| Project | Commit | Groups | Antonym pairs | Comparisons | Warnings | Copies skipped | Per 1,000 comparisons |
|---|---|---|---|---|---|---|---|
| NocoBase | 10810697 | 132 | 426 | 6,530 | 19 | 2 | 2.91 |
| Mastodon | cab53a59 | 1 | 93 | 5,672 | 8 | 0 | 1.41 |
| Excalidraw | e1b7aacb | 1 | 8 | 387 | 0 | 0 | 0.00 |
| Immich | 53618ff7 | 1 | 52 | 2,655 | 4 | 0 | 1.51 |
| Lobe Chat | 5310a6f1 | 57 | 453 | 7,701 | 4 | 0 | 0.52 |
| Element Web | fc4d45cc | 1 | 62 | 2,070 | 4 | 0 | 1.93 |
| Jitsi Meet | f4a1c17e | 1 | 75 | 3,151 | 7 | 0 | 2.22 |

Jitsi's `main-nb.json` and `main-no.json` are identical at this commit, so any
warning in one would be counted twice (as pre-registered). Neither file has a
warning: 0 such pairs, so the total without duplicates is still 19.

Lobe Chat's 4 warnings are 2 values in 2 locales: one "Download failed" key
paired with two "Upload failed" keys.

## G4 hand grading

Procedure, fixed before reading the sample: each row of `sample.csv` gets
`real` (the shared value says one side only, or neither side clearly), `not`
(the value honestly covers both states in that language), or `unsure` (the
graders cannot read the language with confidence). `unsure` rows are left out
of the share but counted. The grader reads only the two English sources, the
shared value and, where needed, the project's use of the keys; no other row is
looked up to decide. Share = real / (real + not).

With 19 warnings the seeded sample of up to 60 is all of them. Verdicts and a
note per row are in [sample-graded.csv](sample-graded.csv).

| Verdict | Rows |
|---|---|
| real | 13 |
| not | 6 |
| unsure | 0 |
| share real | 68% of 19 judged (below the 20 needed, so G4 is not tested) |

Notable rows:

- Immich `ja`: `collapse` and `expand` are both 展開 ("expand"), and
  `collapse_all` / `expand_all` are both 全て展開 ("expand all"). The Collapse
  buttons say Expand.
- Jitsi Meet `af` and `eu`: "Disable low bandwidth mode" and "Enable low
  bandwidth mode" share one value. In Afrikaans it says *deactivate*; in Basque
  it says *enable* (`Gaitu`). Each language has one toggle label that says the
  opposite of what it does.
- Jitsi Meet `ca`: "Lobby has been enabled by {{originParticipantName}}"
  reads *ha desactivat* ("has disabled").
- Jitsi Meet `eo` and `uk`: "Open chat" and "Close chat" share *Malfermi
  babilejon* ("open chat") in Esperanto and *Панель чату* ("chat panel", neither
  side) in Ukrainian.
- Immich `sq`: Mute and Unmute are both *Heshtëro* ("mute").
- Immich `ta`: "Unselect all duplicates" says "select all duplicates".
- Element Web `es`, `is`, `ko`: the Previous room / previous message shortcuts
  say "next" (Spanish, Icelandic) or neither (Korean); `ka` gives Zoom in and
  Zoom out one word, "scaling".
- All 6 `not` rows are the same shape: "Download failed" and "Upload failed"
  share one value in French (`fr`, `fr-CA`, `fr-FR`: *Échec du
  téléchargement*) or Arabic (*فشل التحميل*). In both languages that noun is in
  common use for transfers either way, so the value fits both. `fr-CA` is
  borderline (Quebec usage prefers *téléversement* for upload) and was graded
  `not`.

Seen after grading, and **not** a pre-registered result: every `not` row comes
from one of the 40 word classes, `upload`/`download`. Without that class the
new projects would have 13 warnings, all graded real. Dropping or narrowing the
class is a change to test on fresh projects with its own pre-registration, not
something to read off this sample.

## Limits

- G4 is judged by AI agents working for MV2, not by native speakers. The
  graders were confident enough in every language here to mark none unsure, but
  Georgian, Albanian, Tamil and Icelandic would gain most from a native reader.
- 19 warnings is a small sample, and G4 needed 20: the 68% is a description,
  not a passed test.
- G5 undercounts keys built at run time (`` t(`toolbar.${name}`) ``); the one
  key not found (Jitsi `lobby.notificationLobbyDisabled`) may be one of those.
- The 40 word classes miss antonyms outside the list (`Visible`/`Hidden`) by
  design; this measures precision on what the rule flags, not recall.
- Five new projects, one commit each; rates may not carry to other catalogs.
- No defect here has been reported to its project yet.

## Files

From the evaluation job, in [guard-results/](guard-results/):
[warnings.csv](guard-results/warnings.csv) (all 46 warnings),
[summary.json](guard-results/summary.json) and
[stdout.txt](guard-results/stdout.txt). The sample with verdicts:
[sample-graded.csv](sample-graded.csv). The build kit:
[guard-0120/](guard-0120/). The released code:
[l10n-guard v0.12.0](https://github.com/munimtechnologies/l10n-guard/releases/tag/v0.12.0).
