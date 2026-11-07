# Results: l10n-guard 0.18.0 build check (folder-script and locale-code)

Graded on 2026-11-07 (UTC) by AI agents working for MV2 of Munim, Inc. The predictions in
[PREDICTIONS.md](PREDICTIONS.md) were published before the job ran and are graded here unchanged.

Job `guard-0180-v1` ran on 2026-11-07 from 03:41 to 03:44 UTC. It downloaded l10n-guard 0.17.0
from `main`, ran every test module, applied the patch in [guard_job.py](guard_job.py) (the new code
is in [folder_script_block.txt](folder_script_block.txt)), and ran every test module again. Then it
ran the new check on every translation folder of Thunderbird for Android's message-list module
(`feature/mail/message/list/internal/src/main/res`) at commit
`467787fcc43e560aae2d670c7cfa5f9036ca486d`. Job outputs published unchanged here:
[summary.json](summary.json), [report.txt](report.txt), [thunderbird.tsv](thunderbird.tsv) (one
row per folder) and [cli-thunderbird-ar.txt](cli-thunderbird-ar.txt) (the command line's output for
`values-ar`).

## Verdicts: 4 of 4 held

| | Prediction | Result | Verdict |
|---|---|---|---|
| B1 | `test_0180` passes; no module that passed before fails after (version pins aside) | all 17 modules passed before and after, plus `test_0180` (19 tests); `regressions: []`. No test pins 0.17.0 | HELD |
| B2 | at least 4 of the 5 script-visible Thunderbird folders get `folder-script` | 5 of 5: `values-am`, `values-ar`, `values-be`, `values-bg`, `values-bn` | HELD |
| B3 | at most 2 other folders of the module flagged | 0 | HELD |
| B4 | no folder crashes the check | 0 crashes in 73 folders | HELD |

## What the warnings say

- `values-ar` (Welsh text): "22 of 22 translated strings in this 'ar' folder use only Latin
  letters and 0 use Arabic script; only 0 of them reuse the source's words, so they may be another
  Latin-script language under the wrong code, or a deliberate Latin spelling of 'ar' ...".
  `values-am` (Corsican), `values-bg` (Lithuanian) and `values-bn` (Romanian) get the same
  message for their scripts.
- `values-be` (Japanese): "10 of 11 translated strings in this 'be' folder are written in Kana
  script and 0 in Cyrillic: it may hold another language's translation under the wrong code".
- The three Latin-in-Latin cases (`values-ast` Hungarian, `values-az` Italian, `values-br`
  Turkish) are not flagged, as expected: a script rule cannot see them.

## Limits (read before relying on this)

- This is a build check on the case that motivated the rule, not an independent test of
  precision. The evidence for precision is the census's hand check (26 of 32 flagged folders were
  defects, [locale-mismatch/RESULTS.md](../locale-mismatch/RESULTS.md)), which used the same rule.
- 33 of the module's 73 folders have 0 in the `strings` column of thunderbird.tsv (nothing to
  check in this module), so they could not be flagged either way.
- The Latin-text message offers "a deliberate Latin spelling" as one possible cause. In all four
  Thunderbird cases the real cause is another language's translation; the message names both
  because the rule cannot tell them apart.
- Thunderbird was told about these folders on 2026-11-07
  ([thunderbird-android #11893](https://github.com/thunderbird/thunderbird-android/issues/11893)).

## What happened next

The patch was released as l10n-guard v0.18.0 with the README describing the two warnings and
their limits: [munimtechnologies/l10n-guard](https://github.com/munimtechnologies/l10n-guard).
