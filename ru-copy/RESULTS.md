# Results: Russian copies in Ukrainian and Belarusian Android translations

Graded 2026-11-05 by AI agents working for MV2 of Munim, Inc., against the pre-registration
[PREREG.md](PREREG.md) (ru-copy PREREG v1, 3 November 2026) and [DEVIATIONS.md](DEVIATIONS.md)
(ru-copy DEVIATION 1: a wrong control case fixed before any data was read). Code: Apache-2.0.
Text and data: CC BY 4.0.

**In short:** 3 of 4 predictions held, but the one that gives the others their meaning failed.
Ukrainian strings that are exact copies of the app's Russian string are common: 279 apps ship at
least one multi-word copy. But a hand check of 40 of them found **only 4 that are Russian**. The
other 36 are phrases that are written the same way in both languages ("По центру", "Формат
координат", "Список покупок"). Exact copying is a poor sign of a Russian leak, so the low share
caught by cyrillic-leak's letter rule says little about that rule's recall.

## The run

Job `ru-copy-v3`, 5 November 2026, 00:02 to 00:43 UTC. It ran the published `ru_copy.py` 0.1.1
byte for byte (downloaded from `main` once DEVIATION 1 was public) and the published
`cyrillic_leak.py` 0.1.0, on the census's 4,693 repositories. All SHA-256s are in
[summary.json](summary.json).

- Control and self-test passed. 766 repositories had Ukrainian or Belarusian strings; 3,829 had
  none; 95 clones failed and 3 timed out.
- **Ukrainian:** 284,563 pairs (a Ukrainian string with a Russian string for the same key) in 715
  repositories. 11,585 are exact copies (622 repositories); 878 copies have two or more words, and
  877 of those have no Ukrainian-only letter (і ї є ґ) and are candidates, in 279 repositories. 4
  candidates (4 repositories) contain a Russian-only letter (ы э ё ъ).
- **Belarusian:** 91,591 pairs in 218 repositories; 2,473 exact copies; 138 candidates in 52
  repositories, 12 of them (3 repositories) letter-flagged.
- Gate (at least 50,000 Ukrainian pairs in 100 repositories): **passed**.

## Verdicts

| | Prediction | Result | Verdict |
|---|---|---|---|
| R1 | >= 20 repositories ship a Ukrainian candidate | 279 | HELD |
| R2 | mean share of letter-flagged candidates per repository < 1/2 | 0.0076 (279 repositories) | HELD |
| R3 | the Belarusian mean is higher than the Ukrainian one | 0.0302 vs 0.0076 | HELD |
| R4 | >= 3/4 of a 40-candidate sample is Russian (hand check) | 4 of 40 | **FAILED** |

## R4: the hand check

One Ukrainian candidate per repository, drawn by the pre-registered hash rule
([sample.csv](sample.csv)), labelled with a note each ([sample_labels.csv](sample_labels.csv)):

- **`russian`: 4.** вибрировать (Ukrainian: вібрувати), ПЗУ (Ukrainian abbreviation: ПЗП), вклад
  for a contribution (Ukrainian: внесок), статуса (Ukrainian genitive: статусу).
- **`both`: 36.** Valid in Ukrainian and Russian alike, mostly two-word UI labels and loanwords:
  По центру (4 times), Веб-сайт, Формат координат, Порт хоста, Тип ключа, Список статей.
- **`ukrainian` and `other`: 0.**

**Robustness.** 5 calls are marked borderline. Flipping every one toward `russian` gives 8 of 40,
far from the bar of 30. The verdict does not depend on them.

**Post hoc (not pre-registered):** none of the 4 Russian rows has a Russian-only letter, so the
letter rule caught 0 of them. Each was recognisable only by vocabulary or grammar.

## What this means

- PREREG.md said R2 can be read as the letter rule's recall on Russian copies only if R4 holds.
  R4 failed, so it can't: most exact copies are not Russian at all, and the 0.8% letter rate is
  low mainly because there is little Russian to find among them.
- The cyrillic-leak study's count of Russian letters in Ukrainian files remains a lower bound, but
  this study gives no evidence on how loose that bound is. The 4 Russian copies found here could
  only be caught by a word list or a native reader.
- A `copied-from-locale` warning in l10n-guard would be wrong about 9 times in 10 on Ukrainian
  files, so it will **not** be built.
- R3 held: Belarusian copies of Russian are more often letter-flagged than Ukrainian ones. Since
  R4 sampled only Ukrainian, this study can't say how many Belarusian copies are Russian.

## Limits

- Labels by AI agents, not native speakers of Ukrainian. Every label and note is published.
- Exact copies only; one snapshot of each repository's HEAD; plural and array items compared
  item by item.
- `copies.csv` (every copy) is not published here because of its size. It can be rebuilt with
  `ru_copy.py` and the hashes in `summary.json`.

Made by MV2 of Munim, Inc. with AI agents. Contact: mv2@munimtech.com.
