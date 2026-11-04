# Results: mainland vocabulary in Taiwan Android translations

Graded 2026-11-04 by AI agents working for MV2 of Munim, Inc., against [PREREG.md](PREREG.md)
(zh-vocab PREREG v1, published before any repository was read). The verdicts below are the
pre-registered ones and are not changed. Anything decided after seeing the data is marked
**post hoc**. Code: Apache-2.0. Results and data: CC BY 4.0.

**Two of four predictions held, and the hand check failed.** Read naively, the word list flags
602 of 655 apps (92%). But in a hand check of 40 flagged strings, one per app, only 16 used a
mainland word in that meaning. The other 24 were correct Taiwan usage that the list flags anyway.
So OpenCC's Taiwan phrase table works well as a conversion table but poorly as a lint list. As
pre-registered, the count of flagged apps does not say how many apps really use mainland
vocabulary.

## What was run

- Job `zh-vocab-v2`, 3 November 2026 (about 14:36 to 14:59 UTC). It ran the published `zh_vocab.py`
  0.1.0 byte for byte, through the CSV-safe wrapper described in [DEVIATIONS.md](DEVIATIONS.md)
  (zh-vocab DEVIATION 1). The first run had crashed on an emoji before grading. `summary.json`
  records the SHA-256 of `zh_vocab.py`, the wrapper, DEVIATIONS.md, PREREG.md, the repository list and
  OpenCC's files (tag `ver.1.4.2`).
- Corpus: the 4,693 repositories in `hidden-chars/repos.txt`. 694 have a Traditional Chinese
  translation, 3,906 have none, and 93 failed to clone. No repository was left unread. No file
  failed to parse. The positive control and the two self-test repositories (NewPipe, F-Droid
  client) passed.
- A string is **flagged** when forward maximum matching over OpenCC's `TWPhrases.txt` finds a key
  that is mainland usage (Taiwan's value differs from the key) and the source string doesn't
  contain that key. There are 768 such keys.

## Verdicts

| Prediction | Pre-registered rule | Result | Verdict |
|---|---|---|---|
| Gate | Taiwan units >= 20,000 in >= 100 repositories | 245,416 units in 655 repositories | passed |
| V1 | at least a third of Taiwan repositories ship a flagged unit | 602 of 655 (91.9%) | **held** |
| V2 | Hong Kong files have a higher flagged share than Taiwan files (HK gate 2,000 units / 20 repos) | HK 5,275 of 47,090 (11.20%) vs TW 22,808 of 245,416 (9.29%) | **held** |
| V3 | mean over repositories of (flagged units that are a character-by-character conversion of the app's Simplified string / flagged units with a Simplified string) >= 1/2, needs >= 10 repos | mean 0.286 over 557 repositories | **failed** |
| V4 | hand check: `mainland` labels >= 3/4 of the 40-string sample | 16 of 40 (40%) | **failed** |

The V2 comparison is cross-multiplied: 5,275 x 245,416 = 1,294,569,400 > 22,808 x 47,090 =
1,074,028,720. V3's exact sum of shares is in `summary.json`. Pooled rather than averaged, 6,018
of 21,805 flagged Taiwan units with a Simplified string are a character-by-character conversion
of it (27.6%), and 770 are identical to it.

## The hand check (V4)

Each sampled string was labelled from its Taiwan text and English source only, under the
pre-registered rules. `mainland` means the term is mainland usage in that meaning and Taiwan uses
something else. `fine` means it is correct Taiwan usage in that meaning. `other` means a word
boundary is crossed, it is part of a name or quotation, or it can't be judged. Every label has a
note in [sample_labels.csv](sample_labels.csv), and the strings are in [sample.csv](sample.csv).

- **mainland: 16.** 設備 for a phone ("device"; Taiwan: 裝置) 3 times. Twice each: 點擊 for "tap"
  (點選, 輕觸), 發送 for "send" (傳送), 連接 for a network connection (連線), and 文件 / 文件名 for
  "file" / "file name" (檔案, 檔名). Once each: 設置 (設定), 頁腳 (頁尾), 保存 (儲存), 鏡像 for a
  disk image (映像), and 應用程序 + 添加 in one string (應用程式, 新增).
- **fine: 24.** Two keys account for 15 of them. **權限** ("permission"; the table's Taiwan value is
  許可權) was correct in all 9 rows where it was the only flagged term. Android's own Traditional
  Chinese settings call a permission 權限, and 許可權 is the Windows file-permission term. **項目**
  ("item"; the table's value 專案 means "project") was correct in all 6. The other 9 are 局部 in
  weather text (2), 程序 for a procedure, 聲明 for "states", 發佈 and 類型 in a GPL notice, and four
  borderline words that are common in Taiwan but have a stricter Taiwan alternative: 聯繫 (聯絡),
  腳本 (指令碼), 儲存設備 (儲存裝置) and 字體 (字型).
- **other: 0.**

**Post hoc, labelled as such.** Even if all four borderline `fine` rows were `mainland`, the count
would be 20 of 40, still short of the 30 needed. If the 15 rows whose only flagged term is 權限 or
項目 are set aside, 16 of the remaining 25 are `mainland` (64%), still below 3/4. In the full data,
權限 is the most frequent flagged term in Taiwan files (2,476 units in 403 repositories), and 項目 is
third (1,553 in 258). So a large share of the 602 flagged apps may be flagged for words that are
correct.

The hand check also shows the list misses things. Sample row 28 uses 數據 for "data", and row 30
uses 菜單 for "menu". Both are mainland usage, but neither word was flagged in those strings.
Row 24 also contains a Simplified character (长), the problem the census's
[hanzi-leak](../hanzi-leak/RESULTS.md) study counts.

## Other numbers (reported, not predicted)

| | Taiwan (`-rTW`, `b+zh+Hant+TW`) | Hong Kong / Macau | Hant without region |
|---|---:|---:|---:|
| repositories with units | 655 | 145 | 35 |
| units | 245,416 | 47,090 | 20,971 |
| flagged units | 22,808 | 5,275 | 1,947 |
| repositories with a flagged unit | 602 | 125 | 30 |
| distinct flagged terms | 239 | 189 | 120 |
| flagged units with a Simplified-only character | 317 | 188 | 15 |
| units whose English source contains Han characters | 849 | 1,172 | 40 |

The most frequent flagged terms in Taiwan files (units, repositories) are 權限 (2,476, 403), 點擊
(2,288, 242), 項目 (1,553, 258), 文件 (1,375, 203), 類型 (1,301, 261), 連接 (1,242, 246), 發送
(1,165, 171), 設置 (851, 154), 設備 (843, 156) and 查看 (833, 260). The full top-40 for each group is
in [summary.json](summary.json). A Hong Kong flag is not a defect, because the table describes
Taiwan usage. Hong Kong is there only as a contrast (V2).

## What this means

- **For tools:** turning OpenCC's `TWPhrases.txt` into a "wrong vocabulary" lint rule as it
  stands would mostly raise false alarms on Android text. The playbook made an l10n-guard warning
  conditional on V4 holding. V4 failed, so **no such warning will be added**. A short list of terms
  that the hand check found to be mainland usage in UI text (設備 for the device, 點擊, 設置, 保存,
  文件名, 鏡像, 頁腳, 連接 for a network connection) could be tested as a narrower rule. That would need its own
  pre-registered test on strings not used here, since the list was chosen after seeing this
  sample.
- **For V3:** most flagged Taiwan strings are not a character-by-character conversion of the app's
  own Simplified string (mean 0.29 per repository). The flagged words either came from somewhere
  else (a translator, a machine translation, an older Simplified text), or they are correct Taiwan
  usage, which the hand check shows is common.

## Prior art

OpenCC's own issue tracker already discusses over-conversion in its Taiwan phrase tables. For
example, [OpenCC #1313](https://github.com/BYVoid/OpenCC/issues/1313) (open, June 2026) lists
risky pairs such as 程序/程式 and 文件/檔案 and suggests keeping only clearly technical phrases.
We found no measurement of
how often the table's flags are right on shipped app strings. This study adds one for OpenCC
`ver.1.4.2` on Android translations. It also names two high-volume keys, 權限 and 項目, that were
wrong in every sampled case.

## Limits

- The hand check was done by AI agents reading the English source, not by native speakers from
  Taiwan. Some labels are judgement calls (four are marked borderline). Every label and its reason
  is published so anyone can re-grade. The post-hoc check above shows the V4 verdict would not
  change even if all four borderline labels flipped.
- V4 measures precision only. The list also misses mainland words that aren't among its keys
  (數據, 菜單 above), so the flagged count is not a count of mainland vocabulary either way.
- This is one snapshot of default branches on 3 November 2026. Forks and copies of an app count
  separately, and strings files in several `res/` folders count once per folder.

## Files

- [summary.json](summary.json): every count, the verdicts, top terms, SHA-256 of every input.
- [sample.csv](sample.csv): the pre-registered V4 sample. [sample_labels.csv](sample_labels.csv)
  has its labels.
- `zh_vocab.py` 0.1.0, `run_zh_vocab.py` and their tests in this folder.
- The job also wrote `flagged.csv`, every flagged unit (22,808 Taiwan rows plus the Hong Kong and
  region-less ones, with repository, commit, key, terms, text and source). It is not in this
  repository: an automatic content filter in MV2's publishing step stopped the first commit on a
  word in a few app strings. Running `run_zh_vocab.py` on the same repository list writes it
  again (later commits of the apps may differ).

Made by MV2 of Munim, Inc. with AI agents. Contact: mv2@munimtech.com.
