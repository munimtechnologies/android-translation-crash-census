# Results: how often is zhtw-mcp's mainland-vocabulary check right on Taiwan app strings?

Graded 2026-11-05 by AI agents working for MV2 of Munim, Inc., against the pre-registration
[PREREG.md](PREREG.md) (zhtw-lint PREREG v1, published 4 November before the job ran). Code:
Apache-2.0. Text and data: CC BY 4.0.

**In short:** 3 of 4 predictions held, but the headline one failed. zhtw-mcp finds most of the
strings already known to use mainland vocabulary (12 of 16) and repeats very few of OpenCC's false
alarms (2 of 24). But in a fresh sample of its own findings, only **19 of 40** were mainland usage
that Taiwan says differently; the pre-registered bar was 30. Most of the rest are words that are
correct in Taiwan and that the tool flags as a style preference, above all 查看 ("view").

## The run

Job `zhtw-lint-v1`, 5 November 2026, 00:48 to 02:07 UTC, on the census's 4,693 repositories
(`hidden-chars/repos.txt`). zhtw-mcp `latest` (release assets of 2 November 2026, `main` at
`1927945`), binary SHA-256 `59386bd5...`, checked against the release's `SHA256SUMS`; command
`zhtw-mcp lint --format json --profile base --relaxed --content-type plain --`. Every SHA-256 is
in [summary.json](summary.json).

- Control passed: 軟件 and 默認 were found, 這個軟體很好用 gave nothing ([control.json](control.json)).
- 653 repositories had Taiwan strings; 244,340 units in 650 repositories were linted
  (147,276 distinct texts, **0 lint errors**). 846 units whose English source has Han characters
  were left out, as pre-registered. 93 clones failed and 2 timed out.
- Gate (at least 20,000 units in 100 repositories, at most 1% lint errors): **passed**.

## Verdicts

| | Prediction | Result | Verdict |
|---|---|---|---|
| Z1 | most of zhtw-mcp's findings on Taiwan app strings are right (>= 3/4 `mainland`) | 19 of 40 `mainland` (47.5%) | **FAILED** |
| Z2 | it catches >= 12 of zh-vocab's 16 known mainland strings | 12 of 16 | HELD (exactly at the bar) |
| Z3 | it repeats <= 6 of the 24 OpenCC false alarms | 2 of 24 | HELD |
| Z4 | it flags fewer units than OpenCC's table | 18,024 vs 22,669 units | HELD |

**Z2 detail** ([known_rows.csv](known_rows.csv)). Caught: rows 5, 6, 11, 13, 17, 21, 24, 30, 31,
33, 34, 40. Missed: 9 (設置), 23 (保存), 25 (文件) and 26 (鏡像). Row 25 was an expected miss:
the pre-registration said zhtw-mcp disables 文件 as a false friend. It still caught 文件名 in row 24.

**Z3 detail.** It repeated OpenCC's false alarm on row 14 (發佈 in a GPL notice) and row 18 (儲存設備).
On the other 22 `fine` rows, including all 15 權限 and 項目 rows that made OpenCC's raw table useless,
it said nothing.

**Z4 detail.** On the same 244,340 units: 12,945 flagged by both, 5,079 by zhtw-mcp only, 9,724 by
OpenCC only. 572 of 650 repositories have at least one zhtw-mcp finding.

## Z1: the hand check

40 findings, one per repository, drawn by the pre-registered hash rule and never one of
zh-vocab's 40 rows ([sample.csv](sample.csv)). Each was labelled from the Taiwan text and its
English source, with a note ([sample_labels.csv](sample_labels.csv)):

- **`mainland`: 19.** For example 存儲 (Taiwan: 儲存), 條形碼 (條碼), 網絡 (網路), 組件 (元件), 回收站,
  運行 (執行), 密鑰 (金鑰), 意大利 (義大利), 壁紙 (桌布), 點擊 for "tap", 連接 for a saved
  connection. Two of these strings (rows 24 and 39) are entirely in Simplified characters.
- **`fine`: 19.** The word is correct Taiwan usage in that meaning:
  - 查看 ("view", rule: 檢視) in **7 rows**. 檢視 is the Microsoft/Apple Taiwan UI term, but 查看
    is in the Ministry of Education dictionary and common in Taiwan apps.
  - 原始碼 ("source code", rule: 原始程式碼) in 2 rows. 原始碼 is the usual Taiwan word.
  - 連接 for a physically connected keyboard or headset (rule: 連線, which is for network
    connections) in 2 rows.
  - One row each: 一次性 in 一次性驗證碼, a one-time code (the rule's 拋棄式 means "disposable");
    程序 meaning an OS process (the rule reads "program" because 執行 is nearby); 註銷 meaning
    "unregister" (the rule's 登出 means "log out"); 發佈 for posting (rule: 釋出, a software
    release); 平板電腦 (rule: 平板); 數據 for a data allowance; 閾值; 對話框 for chat bubbles.
- **`other`: 2.** 消息 used for "Information" (a mistranslation, but not mainland usage in that
  sense), and 克隆 matched inside the place name 密克隆群島 (Miquelon): a word-boundary error.

**Robustness.** 14 calls are marked borderline. Z1 still fails if every 查看 row is counted as
`mainland` (26 of 40). It would reach the bar (31 of 40) only if every borderline call were
flipped, including the `other` row 18. The verdict stands as labelled.

## What this means

- zhtw-mcp is clearly better than OpenCC's raw Taiwan phrase table as a lint list: it keeps most
  of the real catches and drops the 權限/項目 noise. zh-vocab's hand check found 16 of 40 OpenCC
  flags right; here 19 of 40 zhtw-mcp findings are. The two samples are different, so this is
  not a controlled comparison.
- But on shipped app strings, fewer than half of its `cross_strait` findings are mainland
  vocabulary. Many are preferences between two words that are both used in Taiwan (查看/檢視,
  原始碼/原始程式碼), or rules that fire on another meaning of the word. As a hard check that fails
  a build, it would be wrong more often than right; as a style suggestion it is useful.
- As pre-registered, l10n-guard will **not** point to zhtw-mcp as its Taiwan vocabulary check
  (that needed Z1 and Z2 to hold). The terms behind the wrong findings are listed above, so they
  can be offered to zhtw-mcp's maintainers as a data note once a person has checked them.

## Limits

- Labels are by AI agents, not by native speakers from Taiwan. Every label and note is published.
- One snapshot of each repository's HEAD and of zhtw-mcp's rolling `latest` build.
- Precision is measured on findings, one per repository. Recall is measured only on zh-vocab's 16
  known rows.
- `flagged.csv` (all 18,024 flagged units) is not published here because of its size. It can be
  rebuilt with `zhtw_lint.py` and the hashes in `summary.json`.

Made by MV2 of Munim, Inc. with AI agents. Contact: mv2@munimtech.com.
