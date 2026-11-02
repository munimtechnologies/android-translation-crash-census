# Results: Simplified characters in Traditional Chinese Android translations

Graded 2026-11-02 by AI agents working for MV2 of Munim, Inc., against
[PREREG.md](PREREG.md) (hanzi-leak PREREG v1, published 2026-11-01 before any repository was
read). The verdicts below are copied unchanged from the job's [summary.json](summary.json).
Code: [hanzi_leak.py](hanzi_leak.py). Code Apache-2.0; results and data CC BY 4.0.

**Three of four predictions held; the copy prediction failed.** About 1 in 4 open-source
Android apps with a Traditional Chinese translation ships Simplified-only characters in it. Most
flagged *strings* are exact copies of the app's Simplified string, but in the typical app with a
flag, most are not: they are single leftover characters in otherwise converted text, or
Simplified text that differs from the app's own Simplified file.

## The run

- Job `hanzi-leak-v1`, 2026-11-01 19:49-20:08 UTC, 2 CPUs, peak memory 0.13 GB.
- Corpus: `hidden-chars/repos.txt` (4,693 F-Droid source repositories, SHA-256 in summary.json).
  1,257 had Chinese string files, 3,346 had none, 90 could not be cloned. No file failed to parse.
- Character sets from OpenCC `ver.1.4.2` (hashes recorded): S (Simplified-only) has 3,771
  characters, T (Traditional-only) has 3,198. Both are in [s_set.txt](s_set.txt) and
  [t_set.txt](t_set.txt).
- Positive control passed: the sets contain and exclude the characters PREREG names, and the
  detector fires on 这是设置 and stays quiet on 這是設定. The self-test on NewPipe and F-Droid's
  client read 1,491 and 653 Traditional units.

## Verdicts

| | Prediction | Measured | Verdict |
|---|---|---|---|
| Gate | Traditional units >= 20,000 in >= 100 repos | 313,111 units in 692 repos | met |
| P1 | >= 10% of repos with Traditional units ship a flagged one | 188 of 692 (27.2%) | **HELD** |
| P2 | repo-weighted mean of identical/available >= 1/2 (>= 10 repos) | 0.3865 over 183 repos | **FAILED** |
| P3 | flagged share lower in Simplified files than in Traditional | 624 of 356,235 (0.18%) vs 2,721 of 313,111 (0.87%) | **HELD** |
| P4 | flagged share lower in repos with no Simplified or plain `zh` folder | 4 of 4,990 (0.08%, 42 repos) vs 2,717 of 308,121 (0.88%, 650 repos) | **HELD** |

P2's exact sum of shares is in summary.json (`tables.p2.sum_of_shares`); the verdict was decided
on that fraction, not on the rounded mean.

## Numbers reported, not predicted

| | Traditional files (S characters) | Simplified files (T characters) |
|---|---|---|
| Repositories with units | 692 | 932 |
| Units | 313,111 | 356,235 |
| Flagged units | 2,721 | 624 |
| Repositories with a flag | 188 | 61 |
| Flagged, other script's string available | 2,417 | 591 |
| Flagged and identical to it | 1,625 | 482 |
| Flagged and also containing own-script-only characters | 419 | 63 |
| Units whose source string has a Han character | 2,036 | 671 |

- **Unit-weighted, most flags are copies.** 1,625 of the 2,417 flagged Traditional strings with
  a Simplified counterpart (67.2%) are identical to it. This is the number P2 was designed *not*
  to rely on: five repositories hold 1,472 of the 2,721 flagged Traditional units (54.1%):
  Windscribe/Android-App 349, OpenArchive/Save-app-android 310, mtotschnig/MyExpenses 293,
  Chiu-xaH/HFUT-Schedule 269 and owncloud/android 251.
- **Repo-weighted, most are not.** Across the 183 repositories with a comparable flagged string,
  the mean share of copies is 0.3865. 419 flagged Traditional strings (15.4%) mix both scripts,
  which is a partly converted string, not a copied one.
- **The reverse direction exists but is concentrated.** Two repositories hold 468 of the 624
  flagged Simplified units (75%): yuetyam/jyutping-android 234 and owncloud/android 234. 438 of those 468 are identical to
  the app's Traditional string, so here the Simplified file was copied from the Traditional one.
- **Apps with nothing to copy from almost never leak.** In the 42 repositories with no
  Simplified or plain `zh` folder, 3 ship a flag (4 strings), against 185 of 650 repositories
  that have one.
- **Plain `values-zh` folders are Simplified.** 109,717 units in 338 repositories: 85,699
  (78.1%) contain an S character and 4,474 (4.1%) a T character.

## Hand check (not pre-registered)

A systematic sample of 40 flagged Traditional strings (the 35th row of the Traditional group in
[flagged.csv](flagged.csv), then every 68th) was read by hand. Labels and notes per row are in
[handcheck.csv](handcheck.csv).

| Label | Strings |
|---|---|
| Whole string is a copy of the app's Simplified string | 20 |
| Whole string Simplified, different from the app's Simplified string | 6 |
| Whole string Simplified, no Simplified string for that key to compare | 5 |
| Partly converted: one or more Simplified characters left in Traditional text | 8 |
| Correct use, not a defect | 1 |

**39 of 40 flags show text that a reader in Taiwan or Hong Kong would not expect.** The one
correct use is in NewPipe's Hong Kong file, where the Cantonese particle for "all" is
conventionally written 晒 (OpenCC maps it to 曬, the Traditional form of "dry in the sun").
Deliberate Simplified text was rare: a search of all 2,721 flagged Traditional strings found 3
that name the Simplified language (简体中文) on purpose, and none fell in the sample. The sample
is unit-weighted, so 22 of the 40 come from the five largest repositories above; precision in
small repositories may differ.

## What this means

- For P2, the cyrillic-leak study's copy guess failed too (9 of 49 Ukrainian strings). Copying
  explains the big cases, whole files that ship Simplified text under a Taiwan or Hong Kong
  folder, but in the typical app the leak is one or a few characters left in converted text
  (内 for 內, 来 for 來, 对 for 對, 踪 for 蹤).
- A character check finds these with high precision on this sample. A wrong-script warning for
  `zh-Hant`/`zh-TW`/`zh-HK` targets is a good candidate for a translation checker. Its precision
  should be measured on held-out files (other projects, other file formats) before it ships.

## Limits

- Lower bound: Simplified text written only with characters shared by both scripts is not
  counted, nor is mainland vocabulary in Traditional characters (軟件 for 軟體).
- One snapshot of default branches on 2026-11-01. Forks and copies of an app count separately.
- OpenCC's tables decide which characters belong to which script; regional variants such as 晒
  can be correct in one region.
- The hand check is one reading of 40 strings by AI agents, not by native readers.

## Files

- [summary.json](summary.json): the job's own summary and verdicts, unchanged.
- [flagged.csv](flagged.csv): every flagged unit (3,345 rows: 2,721 Traditional, 624 Simplified).
- [repos.jsonl](repos.jsonl): per-repository status, commit, units and flags.
- [handcheck.csv](handcheck.csv): the 40-string hand check.
- [s_set.txt](s_set.txt), [t_set.txt](t_set.txt): the character sets used.

Made with AI agents by MV2 of Munim, Inc. (mv2@munimtech.com).
