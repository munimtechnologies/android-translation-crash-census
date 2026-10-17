# qt-shape 0.1.0 results: the "X of Y" effect carries over to Qt; the genitive-order reading does not, beyond Chinese

MV2 of Munim, Inc. Made with AI agents. Written 2026-10-17 from the sealed run of 2026-10-17
(08:24-08:29 UTC). Licence: this text CC BY 4.0.

**Two predictions held (Q2, Q3) and four were not testable under the minimum sample sizes we fixed
in advance (Q1, Q4, Q5, Q6).** The data the rule set aside are reported below as description, not as
verdicts. The most important of them: Q3 held only because of Chinese. Leave Chinese out and
genitive-first languages that are not verb-final reordered **0 of 95** "of" strings. So the
after-the-fact reading in [shape 0.1.0](../shape/RESULTS.md) (that genitive order, not clause
order, decides which "of" strings get reordered) **did not replicate** outside Chinese.

The predictions were [published first](PREDICTIONS.md). The run's full output is in
[qt_shape.md](qt_shape.md), [qt_shape.json](qt_shape.json), [by_language.csv](by_language.csv),
[top_sources.csv](top_sources.csv) and [repos.csv](repos.csv).

## What was measured

29,659 translations of English Qt sources that contain exactly `%1` and `%2`, taken from the `.ts`
files of all 39 listed repositories (all 39 cloned and read; 3 of them, qterminal, FeatherPad and
GPXSee, have no two-argument sources). The left-out files were 8 copies of Qt's own translations
(mumble 4, smplayer 3, goldendict-ng 1) and 2 `.ts` files that are not Qt XML. The unit tests and
all six shape checks passed.

| Prediction | Result | Numbers |
|---|---|---|
| Q1. SOV: `of` reordered at least 3x as often as `no_words` | not testable (94 `of` translations, rule needs 100) | 55.3% (52 of 94) vs 0.4% (6 of 1,384) |
| Q2. SOV: `no_words` reordered less than 3% of the time | **HELD** | 0.4% |
| Q3. Not SOV: `of` reordered 3x as often in Genitive-Noun as in Noun-Genitive languages | **HELD** | 12.9% (18 of 139) vs 0.0% (0 of 306) |
| Q4. Q3 without Chinese | not testable (95, rule needs 100) | 0.0% (0 of 95) vs 0.0% (0 of 306): **would have failed** |
| Q5. Persian under 5%, SOV Genitive-Noun over 25% | not testable (Persian has 9, rule needs 30; pool 76) | Persian 0 of 9; pool 60.5% (46 of 76) |
| Q6. SOV Genitive-Noun above non-SOV Genitive-Noun | not testable (76, rule needs 100) | 60.5% vs 12.9% |

## What it means

- **The shape effect replicates in a second corpus.** In Qt desktop projects, translators into
  verb-final languages reorder "X of Y" sources 55.3% of the time, close to the 53.2% that shape 0.1.0
  measured on Android (F-Droid). "X to Y" (adposition) sources come in at 24.0% (Android: 29.9%),
  and punctuation-only sources at 0.4% (Android: 0.9%). Q1 is below the sample size we committed to,
  so it is not a verdict, but the direction and size match.
- **Genitive order adds nothing outside Chinese here.** All 18 reordered "of" translations in the
  non-SOV Genitive-Noun pool are Chinese (18 of 44, 40.9%). Finnish 0 of 16, Hungarian 0 of 15, Estonian
  0 of 10, Latvian 0 of 8, Lithuanian 0 of 13, Swedish 0 of 20 and Danish 0 of 13 kept the English
  order every time. On Android, Hungarian (32 of 217), Estonian, Latvian and Lithuanian reordered them
  3-15% of the time and Finnish 2.4%, while Swedish and Danish never did. So the evidence that genitive order matters on its own comes down to two languages, Chinese
  and Persian (Persian: 0 of 9 here, 1 of 192 on Android). Two languages are not a pattern. Clause order
  (SOV) remains the only grouping that holds up in both corpora.
- For software teams the practical rule is unchanged: "%1 of %2" and "%1 to %2" strings are the
  ones Japanese, Korean, Turkish and other SOV translators reorder, and Chinese often does too. Those
  strings need numbered placeholders, and checkers must not insist on text order for them.

## Checked by hand

- **Real reorders.** In nextcloud/desktop at the commit read (372e36d), Korean translates `Syncing
  %1 of %2` as `%2 중 %1 동기화 중` and `%1 of %2 in use` as `%2의 %1 사용중`: both reordered, the
  total first. Persian keeps the order (`همگام سازی %1 از %2`), and so does Simplified Chinese in this
  project (`正在同步 %1 / %2`, `使用量 %1 / %2`). All of these match how the run counted them.
- **Shapes.** We read all 15 SOV `of` sources in top_sources.csv. Every one is a count ("Syncing %1
  of %2", "Results (showing %1 out of %2)", "Patched %1 of %2 selected instructions", "Confirming (%1
  of %2 recommended confirmations)"), so it is correctly labelled `of`. As on Android, "of" here means
  counting, not possession.
- **Repositories.** 39 of 39 read with status ok. No Qt-own file was counted (8 were skipped by name).
- **Persian's few reorders** (3 of 223) are `%1%2%`, `Result for equation: %1 = %2` and `Cannot %1
  device %2`. The first two are probably about right-to-left layout around numbers and symbols, not
  grammar. We did not open them.

## What we got wrong in the design

The Qt corpus turned out about 5 times smaller than the Android one (29,659 vs 148,963 two-argument
translations). We set the minimum sizes (100 per pool, 30 for Persian) without first counting how
many "of" sources Qt projects have. Four of six predictions then fell just short. Next time we count
the cells before fixing the thresholds. We have not changed any threshold after seeing the data, and
the numbers above that the rule set aside are description only.

## Limits

- 39 desktop projects. Some translators work on many of them, and strings repeat inside a project.
  Repository-resampled intervals, repository means and unique-pair rates are in qt_shape.md.
- WALS 86A describes a language's main genitive construction. A counting string ("3 of 10") may use
  a different one. Swedish and Danish say "%1 av %2".
- The shape comes from the English text only, and a translator can rewrite a whole sentence.
