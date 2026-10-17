# placeholder-order: how often translators move format arguments, by language

Made by MV2 of Munim, Inc. with AI agents. Code Apache-2.0; data and text CC BY 4.0.

When an English Android string has two or more format arguments (`%1$s`, `%d` ...), how often does a
translation put them in a different order, and how often is that done in a way that breaks the app?
This study counts it across every F-Droid app whose source the census reads.

- Data: the same 4,476 F-Droid source repositories as census 0.3.1
  (index read 2026-10-17T01:05Z; 4,386 read, 90 errors). Plurals excluded.
- 189,599 translations of non-plural strings with two or more arguments.
- Predictions were published before the run: [PREDICTIONS.md](PREDICTIONS.md).
- Full tables: [report.md](report.md), [by_language.csv](by_language.csv), [summary.json](summary.json).
  The per-pair file (pairs.csv.gz) is not published here; rerun `placeholder_order.py` to rebuild it.
- Run: sealed container job `placeholder-order-v1`, 2026-10-17 00:52-01:06Z, all tests passed.

## Results

| source strings | translations | reordered | rate |
|---|---:|---:|---:|
| numbered (`%1$s %2$d`) | 183,583 | 6,285 | 3.4% |
| unnumbered, mixed kinds (`%s ... %d`) | 1,011 | 13 | 1.3% |
| unnumbered, same kind (`%s ... %s`) | 4,485 | 7 seen | 0.2% (lower bound) |

Numbered sources, by the dominant clause order of the target language:

| group | translations | reordered | rate |
|---|---:|---:|---:|
| SOV (Japanese, Korean, Turkish, Hindi ...) | 34,835 | 4,202 | 12.1% |
| SVO (French, Russian, Chinese ...) | 116,459 | 1,703 | 1.5% |
| VSO | 2,458 | 26 | 1.1% |
| no dominant order (German, Dutch, Hungarian) | 16,113 | 225 | 1.4% |

Predictions: P1, P2, P4, P5 and P6 held; **P3 failed**. Japanese (11.9%) and Korean (16.0%) are not in the
top five; Burmese, Mongolian, Kyrgyz, Marathi and Kannada are (18-22%, among languages with 20+ repositories).
P4 (at least 10% of mixed-kind unnumbered reorders are unsafe) came out at 100%, but that is close to true by
construction: moving a `%s` past a `%d` without numbers always hands each one the other's value.

### Hand checks

- All 13 unsafe reorders in [unnumbered_reordered.csv](unnumbered_reordered.csv) were opened and read: each
  is a real reorder of unnumbered placeholders (Dash Wallet ja/ko, Amaze ur/ur-rPK, KeyMapper tr/zh-rCN x2
  each, PhoneTrack bg/pl/ru/zh-rCN/zh-rTW). They are the same rows already counted in the census's
  crash-if-text audit (habit 1), so this study adds no new crash; it puts them in proportion.
- Translation count is above the 10^4-10^5 range guessed beforehand (1.9 x 10^5) because every language
  file of every module is counted; the unique-pair column in report.md shows repeats (forks, copied
  libraries) change the rates little.

### Exploratory (not predicted, read after the run)

- About half of all SVO reorders are Chinese: zh has 873 of the 1,703 (7.7% of 11,325). Without zh and yue,
  the SVO rate is 815 of 104,854, 0.8%, so SOV languages reorder about 15 times as often.
- The SOV languages that reorder least are Georgian (2.2%), Armenian (2.2%), Central Kurdish (2.4%), Persian
  (2.9%) and Amharic (3.8%). Part of this fits the limit written before the run (placeholder position may
  depend more on order inside noun phrases than on clause order): Chinese, though SVO, puts relative clauses
  and possessors before the noun, as Japanese, Korean, Turkish and the Indic languages do, while Persian and
  Kurdish put modifiers after the noun. Amharic and Armenian do not obviously fit. This is a pattern seen
  after the fact in one data set, not a test; a proper test would assign each language its noun-modifier
  order (for example from WALS) before looking.

## Prior art

Style guides (Microsoft, Django, WebTranslateIt, Localazy, Phrase) tell developers to number placeholders so
translators can reorder them, and give single examples. A web search on 2026-10-17 found no published count of
how often translators actually do it, per language, in a real corpus. Machine-translation research measures
word reordering between languages, but not format placeholders in software strings.

## Limits

- Word order groups are coarse, and one language's group is a judgment call.
- Unnumbered same-kind reorders are invisible, so that row is a lower bound.
- Only the latest commit of each repository's default branch is read.
- An unsafe reorder crashes only if text reaches a `%d`; otherwise the values just show in the wrong places.

## Run it

```
python fetch_code.py          # census code from this repository
python bootstrap.py --data-dir /data
python -B test_placeholder_order.py -v
python -B placeholder_order.py --data-dir /data --out-dir /out --workers 8
```
