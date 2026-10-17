# shape 0.1.0 predictions: which English string shapes do translators reorder?

MV2 of Munim, Inc. Made with AI agents. Written 2026-10-17, before shape.py was first run.
Licence: this text CC BY 4.0; shape.py, fetch_code.py and the tests Apache-2.0.

## Question

[placeholder-order 0.1.0](../README.md) found that translators of verb-final (SOV) languages reorder
the numbered placeholders of Android app strings far more often than translators of SVO languages
(12.1% vs 1.5%). [np-order 0.1.0](../np-order/RESULTS.md) then asked whether a language's noun-phrase
order (WALS genitive or adposition order) predicts its rate better than clause order. It does not:
verb-final order separated the languages best (AUC 0.99), and genitive order (0.92) and adposition order
(0.98) did not beat it. Across languages these features go together, so a language-level test cannot
separate them.

This study moves the test to the strings. For each English source with exactly two numbered arguments,
it looks at the words between the two placeholders. If the reordering comes from genitives and
adpositions ("Page %1$d of %2$d" -> Japanese "%2$d ページ中 %1$d ページ", "Move %1$s to %2$s" ->
"%2$s に %1$s を移動"), SOV reorders should concentrate in strings joined by "of" or by a preposition,
and be rare where the arguments are only separated by punctuation ("%1$s: %2$s", "%1$d/%2$d").

We found no earlier measurement of which source-string shapes translators reorder. Searches found
style guides, tool docs and single examples (Microsoft's "Selected {0} out of {1}", a cmux pull request
about "Move %@ to %@"), not counts.

## What we had already seen

Only the published numbers above, the two Japanese examples quoted here, and placeholder-order's 13
unsafe unnumbered reorders. We have not counted any source shape, nor read the per-string data with
source text (pairs.csv.gz has no text).

## Method (fixed now)

- Data: the same 4,476 F-Droid repositories and strings as placeholder-order 0.1.0 (census.py 0.3.0 +
  census_fixes 0.3.1, placeholder_order.py 0.1.0, fetched from this repo at run time). Plural forms
  are left out, as there.
- Counted: translations of sources with exactly two argument placeholders, both numbered (%1$s, %2$d),
  whose translation is "valid" in placeholder-order's sense (both arguments once, same kinds). A
  translation is reordered when its arguments appear in a different order from the source.
- Shape: the source text between the first and the second placeholder, in text order:
  - `no_words`: no letters at all (": ", "/", " - ", ", ", " (").
  - `of`: the words are exactly "of", "out of" or "of the".
  - `adposition`: one word from a fixed list (to, from, in, on, at, by, for, with, into, onto, via,
    than, over, under, per, as, about, through, within, after, before, across, toward, towards,
    against, without, near, between, inside, outside, behind, beyond, since, until, during), alone or
    followed by "the", "a" or "an".
  - `and_or`: exactly "and" or "or".
  - `other`: anything else (clauses such as "%1$s sent you %2$s", longer phrases, non-English text).
  Punctuation around the words does not change the shape (", from " is `adposition`).
- Groups: placeholder-order 0.1.0's word-order groups (SOV, SVO, ...), unchanged.
- A rate needs at least 200 valid translations, or the prediction using it is "not testable".
- Shape checks: six fixed strings must get their expected shape; if one fails, no prediction is scored.

## Predictions

- S1. In SOV languages, `of` sources are reordered at least 3 times as often as `no_words` sources.
- S2. In SOV languages, `adposition` sources are reordered more often than `other` sources.
- S3. In SVO languages, `of` sources are reordered less than 3% of the time.
- S4. The SOV/SVO ratio of reorder rates is higher for `of` and `adposition` sources together than for
  `other` sources.
- S5. In SOV languages, `no_words` sources are reordered less than 3% of the time.
- S6. `of` and `adposition` sources together account for more than half of all SOV reorders of
  numbered two-argument sources (needs at least 20 such reorders).

## Limits

- The shape is read from the English text only; a translator may restructure the whole sentence.
- Strings repeat across forks and copied libraries; the output also gives unique-pair rates, repository
  means and repository-resampled 95% intervals.
- "of" covers both possession ("%1$s of %2$s") and counting ("%1$d of %2$d"); the output lists the most
  often reordered sources so readers can see which kind dominates.
