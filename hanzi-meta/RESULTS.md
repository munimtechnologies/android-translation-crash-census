# Results: Simplified characters in Traditional Chinese app-store listings

Graded 2026-11-02 by AI agents working for MV2 of Munim, Inc., against the
[pre-registration](PREREG.md) (hanzi-meta PREREG v1, SHA-256 `3ea8e78f...fbde`), which was public
before the job read any listing. Code: [hanzi_meta.py](hanzi_meta.py) 0.1.0, which imports
[hanzi_leak.py](../hanzi-leak/hanzi_leak.py) 0.1.0 (SHA-256 `70d46c1f...5774`) for the character
sets and detector. Apache-2.0; results and data CC BY 4.0.

**Verdicts: M1 HELD, M2 FAILED, M3 HELD.** M2 and M3 are the job's verdicts, copied unchanged
from [summary.json](summary.json). M1 was graded by hand from [sample_labels.csv](sample_labels.csv),
as the pre-registration said.

| Prediction | Result | Verdict |
|---|---|---|
| M1: at least 80% of the hand-check sample are real defects | 32 of 35 (91.4%); 32 x 5 = 160 >= 35 x 4 = 140 | **held** |
| M2: at least 10% of repositories with Traditional listing lines ship a flagged line | 25 of 287 (8.7%); 25 x 10 = 250 < 287 | **failed** |
| M3: listings leak more often in repositories whose string files leak | 8 of 48 (16.7%) against 11 of 172 (6.4%); 8 x 172 = 1,376 > 11 x 48 = 528 | **held** |

## What was read

The job cloned the 4,693 F-Droid source repositories of `hidden-chars/repos.txt` (SHA-256
`4159ab19...b9310`) at their default branch on 2 November 2026, found 4,341 listing roots, and read
every listing file in a Chinese locale folder. 657 repositories have a Chinese listing, 3,944 have
none, and 92 could not be cloned (2.0%). No file had undecodable bytes. The positive control (a
synthetic `zh-TW` listing with 这是设置 flagged, 這是設定 not) and a self-test on NewPipe and the
F-Droid client (both found their listing roots) passed before any repository was read. The
character sets are hanzi-leak's, from OpenCC `ver.1.4.2` (3,771 Simplified-only and 3,198
Traditional-only characters); nothing was tuned after hanzi-leak's results.

| | Repositories | Lines with Han characters | Flagged lines | Repositories flagged |
|---|---|---|---|---|
| Traditional (zh-TW, zh-HK, zh-MO, Hant) | 287 | 14,337 | 295 (2.06%) | 25 (8.7%) |
| Simplified (zh-CN, zh-SG, Hans), reverse check | 620 | 29,499 | 13 (0.04%) | 9 (1.5%) |

Traditional lines by file kind: release notes 244 of 8,854 flagged, full descriptions 40 of
4,988, short descriptions 8 of 323, titles 3 of 119, other files 0 of 53. Every flagged line is in
[flagged.csv](flagged.csv); per-repository counts are in [repos.jsonl](repos.jsonl).

## M1: the check is precise on text it was not checked on (held)

The job drew 35 flagged lines (at most 2 per repository, from all 25 flagged repositories) before
anyone read one. AI agents labelled them in sample order, in one pass, with the five labels the
pre-registration fixed:

| Label | Lines |
|---|---|
| `defect` | 32 |
| `regional` | 2 (NewPipe's Hong Kong release notes: the Cantonese particle 晒, "all") |
| `name_or_quote` | 1 (the Xime keyboard's own product name, 曦码输入法, in its Taiwan title) |
| `deliberate`, `not_chinese` | 0 |

The defects are of two shapes (a post-hoc split). 13 are whole lines left in Simplified in a
Taiwan, Hong Kong or Macau folder (for example Pachli's Macau release notes, the F-Droid Build
Status listing and Amarok's short description); 19 are one or two characters left behind in
otherwise converted text: 跟踪 for 跟蹤 (the F-Droid client's own Hong Kong release notes,
Fossify Launcher, Neo Store, Metadata Remover), 内 for 內, 并 for 並, 给 for 給, 没 for 沒,
复 for 覆, 繁琐 for 繁瑣 (SD Maid SE).

Not pre-registered: three of the 32 defect labels are the least clear (猫 for 貓, which Taiwan also
sees as a variant; the card game name 掼蛋; the app name 树林 in a line that writes 樹 elsewhere).
Counting all three against the check still gives 29 of 35, and 29 x 5 = 145 >= 140, so M1 would
still hold. The two misses repeat the one false alarm of hanzi-leak's hand check: OpenCC treats 晒
as the Simplified form of 曬, but Hong Kong Cantonese writes the particle 晒 on purpose. Together
with hanzi-leak's 39 of 40, the check was right on 71 of 75 hand-checked lines in two kinds of text.

## M2: listings leak in fewer apps than strings (failed)

25 of 287 repositories (8.7%) ship a flagged Traditional listing line, below the predicted 10%.
In the apps' string files hanzi-leak found 188 of 692 (27.2%). Per line, listings look worse
(2.06% against 0.87% of string units), but one repository decides that: Pachli's Taiwan and Macau
release notes hold 216 of the 295 flagged lines (216 of its 234 Traditional lines). Without
Pachli, 79 of 14,103 lines are flagged (0.56%).

Not pre-registered: 279 of the 295 flagged lines have a Simplified file of the same name in the
same app, but only 14 are identical to a line in it. In string files, 67% of flagged strings were
copies of the app's own Simplified string; listings that leak were mostly translated or edited
separately and left unconverted, not copied. One app, CENO, has no Simplified listing at all and
still ships 16 of its 18 Taiwan lines in Simplified.

## M3: the same apps leak in both places (held)

220 repositories have Traditional units both in their string files (hanzi-leak's
[repos.jsonl](../hanzi-leak/repos.jsonl)) and in their listings. Of the 48 whose string files were
flagged, 8 (16.7%) have a flagged listing line; of the 172 whose string files were clean, 11
(6.4%). The prediction held; the groups are small, and no significance test was pre-registered.

## Limits

- A lower bound: Simplified text written only with characters both scripts share, and mainland
  vocabulary in Traditional characters (軟件 for 軟體), are not counted.
- Listings in a repository can differ from what F-Droid or Google Play shows; F-Droid's own
  metadata repository and translation platforms were not read. One snapshot of default branches.
- The hand check is one reading by AI agents, not native readers. The labels and a note per line
  are published so anyone can disagree with a row.

## What follows

The precision (32 of 35 here, 39 of 40 in string files) is what the pre-registration required
before this check goes into MV2's free translation checker
[l10n-guard](https://github.com/munimtechnologies/l10n-guard). Version 0.17.0, with a
`wrong-script` warning for Traditional Chinese targets that leaves the Cantonese 晒 alone in Hong
Kong and Macau, is being built and tested.

This study was made with AI agents. MV2, Munim, Inc.
