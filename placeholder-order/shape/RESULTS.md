# shape 0.1.0 results: "X of Y" and "X to Y" strings are the ones SOV translators reorder

MV2 of Munim, Inc. Made with AI agents. Written 2026-10-17 from the sealed run of 2026-10-17
(05:05-05:22 UTC). Licence: this text CC BY 4.0.

**All six pre-registered predictions held.** The predictions were [published first](PREDICTIONS.md);
the run's full output is [shape.md](shape.md), [shape.json](shape.json),
[by_language.csv](by_language.csv) and [top_sources.csv](top_sources.csv).

## What was measured

148,963 translations of Android strings with exactly two numbered arguments (`%1$s`, `%2$d`), in the
same 4,476 F-Droid repositories as [placeholder-order 0.1.0](../README.md). Each English source gets a
shape from the words between its two placeholders. The unit tests and all six shape checks passed.
Left out: 34,856 translations of sources with three or more arguments and 373 translations that are not
"valid" (an argument dropped, doubled or changed in kind).

| SOV languages | valid | reordered | rate | 95% CI (repos) |
|---|---:|---:|---:|---|
| `of` ("%1$d of %2$d") | 2,660 | 1,416 | 53.2% | 42.6-61.5% |
| `adposition` ("%1$s to %2$s") | 2,400 | 718 | 29.9% | 23.2-35.2% |
| `other` (clauses, longer phrases) | 12,873 | 1,130 | 8.8% | 6.9-10.9% |
| `no_words` ("%1$s: %2$s") | 9,576 | 87 | 0.9% | 0.5-1.5% |
| `and_or` ("%1$s and %2$s") | 923 | 1 | 0.1% | 0.0-0.4% |

In SVO languages the same shapes are reordered 2.3%, 4.7%, 1.6%, 0.3% and 0.0% of the time.

| Prediction | Result | Numbers |
|---|---|---|
| S1. SOV: `of` reordered at least 3x as often as `no_words` | HELD | 53.2% vs 0.9% (about 59x) |
| S2. SOV: `adposition` reordered more often than `other` | HELD | 29.9% vs 8.8% |
| S3. SVO: `of` reordered less than 3% of the time | HELD | 2.3% |
| S4. SOV/SVO ratio higher for `of`+`adposition` than for `other` | HELD | 12.1x vs 5.4x |
| S5. SOV: `no_words` reordered less than 3% of the time | HELD | 0.9% |
| S6. `of`+`adposition` give more than half of SOV reorders | HELD | 2,134 of 3,352 (63.7%) |

The result is not carried by one project or by repeated strings: repository means (44.1% for SOV
`of`, 0.8% for SOV `no_words`) and unique-pair rates (54.2%, 1.2%) tell the same story.

## Checked by hand

- **Shapes.** We read the shape of ten of the thirty most often reordered SOV sources. All ten are
  right: `%1$s and hold to %2$s`, `%1$s free of %2$s`, `%1$s to read by %2$s`, `Tap %1$s to type the
  letter %2$s` and `Search for %1$s items in "%2$s"` are `other`; `Swipe %1$s with %2$s fingers`,
  `This app occupies %1$s on "%2$s".` and `Currently listening to %1$s by %2$s.` are `adposition`;
  `%1$d of %2$d on` is `of`; and `Touch "%2$s" to confirm adding "%1$s"` is `other`, measured in its
  own text order.
- **Counting, not possession.** "of" covers both. The top SOV sources are counting strings:
  `%1$d of %2$d` (209 of 395 SOV translations reordered, 45 repositories), `Page %1$d of %2$d` (112 of
  222), `Step %1$d of %2$d` (35 of 109). `%1$s of %2$s` (122 of 182) may be a count or a possessive;
  we did not read its translations. So much of the 53% is counting strings, where SOV languages
  typically name the total before the part (the pattern of Japanese "%2$d 件中 %1$d 件"; an
  illustration, not a quoted string).
- **Totals.** placeholder-order counted 34,835 SOV translations of numbered sources with two or more
  arguments, 12.1% reordered. This run's 28,432 two-argument ones are 11.8% reordered: consistent.

## Something we did not predict (exploratory, now being tested)

Joined by hand with np-order's WALS table, the per-language rates for `of` sources follow genitive
order (WALS 86A) at least as well as clause order. Persian is SOV but puts the genitive after the noun,
and reorders `of` sources 0.5% of the time (1 of 192); 18 SOV languages that put the genitive first
reorder them 57.0% of the time (1,191 of 2,090). Chinese is SVO but puts the genitive first, and
reorders them 20.9% of the time (160 of 765); 24 non-SOV languages that put the genitive after the noun
reorder them 0.07% of the time (4 of 5,873).

This is an after-the-fact reading, and it has only one SOV Noun-Genitive language. So before
believing it, we wrote down six predictions for a different corpus (the Qt `.ts` files of 39 desktop
projects) and published them before looking: [qt-shape/PREDICTIONS.md](../qt-shape/PREDICTIONS.md).

## What it means for software

- Strings shaped "%1 of %2" and "%1 to %2" are the ones whose translations into Japanese, Korean,
  Turkish, Hindi and other SOV languages move the arguments. Those strings must use numbered
  placeholders. A string like "%s of %s" with unnumbered placeholders forces a translator either to
  keep English order or to reorder in a way that can crash on Android (placeholder-order found 13 such
  unsafe reorders, all already in the crash audit).
- Checkers and placeholder-validation code that compare placeholders in text order (one fixed in
  cmux for Japanese "Move %@ to %@") will reject correct translations of exactly these strings.

## Limits

- The shape comes from the English text only, and a translator can rewrite a whole sentence.
- Language groups are placeholder-order 0.1.0's simplified WALS 81A groups.
- Strings repeat across forks and copied libraries; repository-resampled intervals and unique-pair
  rates are given for that reason.
