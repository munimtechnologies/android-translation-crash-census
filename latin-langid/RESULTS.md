# Results: Android translation folders that hold another language in the same alphabet

Graded 2026-11-09 by AI agents working for MV2 of Munim, Inc. (mv2@munimtech.com) against
[PREREG.md](PREREG.md) (SHA-256 `64bec06e…c392b`, printed by the job). Job `latin-langid-v1`,
run 2026-11-09 14:13-14:38 UTC; its outputs are unchanged under [v1/](v1/). Hand labels are in
[labels.csv](labels.csv). Licence: Apache-2.0 (code), CC BY 4.0 (text and data).

## Headline

**The hand check failed.** The code's predictions S0-S4 all held, but only 4 of the 24 sampled
"other-language" folders really hold another language (H1 needed 18). So **no rate of
same-alphabet misplaced translations is claimed from this census.** The identifier works as a
language identifier (S0: 99.2% of folders came out as their own language), but the flagging rule
mostly caught small languages that have no profile of their own (Cebuano, Romansh, Javanese,
Faroese, Ligurian, Latin…) and sit close to a big neighbour that does have one.

A small post-hoc subset looks much better: where the folder's own language *has* a profile, 5 of
the 6 flagged folders outside the design cases really hold another language. That is a hypothesis
for a new pre-registered test, not a result.

## Gate and predictions

| Item | Rule | Observed | Verdict |
|---|---|---|---|
| Gate | >= 4,000 repos read, >= 20 profiles | 4,598 read (2,391 with checked folders), 51 profiles | PASSED |
| S0 | >= 95% of checked folders with a profile are consistent | 25,213 / 25,413 = 99.2% | HELD |
| S1 | other-language folders in >= 5 repos | 51 repos | HELD |
| S2 | other-language < 1% of checked folders | 126 / 26,597 = 0.47% | HELD |
| S3 | >= 2 of the 3 Thunderbird design cases flagged right | 2 of 3 (`values-az` → it, `values-br` → tr; `values-ast` read closest to hu but was not flagged) | HELD (design-known, not out-of-sample) |
| S4 | >= half of other-language folders have a sibling for the language they hold | 95 / 126 | HELD |
| **H1** | real × 4 >= 3 × checked, >= 8 checked | **4 real of 24** (16 < 72) | **FAILED** |

S1, S2 and S4 count flags, and H1 shows that most flags are wrong, so those three verdicts say
nothing about real misplacements. The 4,693 listed repositories: 2,391 read with translations,
2,207 without, 94 clone failures, 1 timeout.

## Hand check (H1)

24 folders, one per repository, chosen by hash before reading (`v1/sample.csv`). For the 7 where
the three strings the job recorded were not clearly in the folder's own language, AI agents read
the first 10 translated strings at the recorded commit. For the other 17, the three recorded
strings were all clearly in the folder's own language and the label rests on them. This
**deviates** from "first 10 strings", but it cannot change the verdict: even if all 17 were
real, the count would be 21, and none of them is.

**Real (4):**
- `zazentimer` `values-xh`: Uzbek (Latin script) in the Xhosa folder; `values-uz` also exists.
- `privacy-friendly-sudoku` `values-br`: Brazilian Portuguese in the **Breton** folder; there is
  no `values-pt`, so phones set to Portuguese show English.
- `SpamBlocker-Extended` `values-gal`: Galician in a folder coded `gal` (ISO 639-3 Galolen);
  there is no `values-gl`. This is a wrong code rather than wrong text.
- `NewPipe` `values-dum` (**borderline**): modern Dutch in the Middle Dutch folder. It flips to not
  real if an ancestor language counts as related; then 3 of 24.

**Not real (20):** the folder holds its own language, which has no profile: Cebuano, Romansh (2),
Waray, Hunsrik, Ligurian (2), Sundanese, Extremaduran (2), Javanese (2), Campidanese Sardinian,
Latin (2), Faroese (2), Chavacano, Turkmen (2). Turkmen sits next to Turkish, Faroese next to
Icelandic, Javanese and Sundanese next to Indonesian, and so on. The connectbot `values-tk`
folder is Turkmen in its first 10 strings, but some later machine-translated strings slip into
Turkish forms.

**Why it failed.** Rule (b) compares a folder's best profile against its own language's profile,
but it only applies when that language has a profile (at least 30 repositories). Without one,
the 90th-percentile rule alone decides, and a minority language written like its big neighbour
passes it. Of all 417 flags (126 other-language plus 291 English), 302 were in folders whose
own language has no profile.

## Exploratory, post hoc (not pre-registered)

The job flagged 8 other-language folders whose own language has a profile, so rule (b) applied.
AI agents read the first 10 strings of each (or all strings, for short files):

| Repository | Folder | Holds (code) | Read | Label |
|---|---|---|---|---|
| AdguardTeam/ContentBlocker | `values-lv` | lt | Lithuanian (Nustatymai, Įvyko klaida!); `values-lt` also exists, so **Latvian phones get Lithuanian** | real |
| SecUSo/privacy-friendly-sudoku | `values-br` | pt | Portuguese; no `values-pt` | real |
| isseigx/kotori (GitLab) | `values-br` | pt | Portuguese (Velocidade Máxima, aplicativo); no `values-pt` | real |
| phikal/ReGeX | `values-eo` | es | Spanish, 15 of 15 strings; no `values-es` | real |
| phyphox/phyphox-android | `values-ca` | es | 9 of the first 10 strings Spanish, a few Catalan (Ajustaments) | real |
| six-seven-or-8/crt_android | `values-de` | fr | mostly German, with some French strings (form_hint) | not real (under half) |
| thunderbird/thunderbird-android | `values-az`, `values-br` | it, tr | design cases (issue #11893) | not re-labelled |

So 5 of the 6 outside the design cases are real. Two of them are the same slip: **Brazilian
Portuguese filed under `br`, which is Breton**, the same country-code-for-language mix-up as
`cn`, `cz` and `ua` folders. Six folders is far too few for a rate, and the rule was chosen after
seeing them. A next step would pre-register "flag only when the folder's own language has a
profile" and test it on folders this census did not read.

`v1/profiles.json` (top 400 character n-grams of 51 language profiles, built from F-Droid apps'
own translations) is released under CC BY 4.0. The 291 folders read as English (stale copies of
the source strings) are listed in `v1/folders.csv` with category `english`. They are not hand-checked.

## Limits

One commit per repository, F-Droid sources only, `res/values*` XML only. The labels were made by
AI agents, not native speakers; minority-language calls rest on spelling and vocabulary markers.
