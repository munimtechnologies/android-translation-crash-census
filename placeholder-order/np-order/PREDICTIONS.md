# np-order 0.1.0 predictions: noun-phrase order and placeholder reordering

MV2 of Munim, Inc. Made with AI agents. Written 2026-10-17, before np_order.py was first run.
Licence: this text CC BY 4.0; np_order.py and its tests Apache-2.0.

## Question

[placeholder-order 0.1.0](../README.md) found that translators of verb-final (SOV) languages reorder the
numbered placeholders of Android app strings far more often than translators of SVO languages (12.1% vs
1.5%). But the English strings with two or more arguments are mostly short noun phrases and
prepositional phrases ("%1$s of %2$s", "%1$s by %2$s", "%1$d from %2$s"), not clauses. If that is what
moves the arguments, then a language's noun-phrase order should predict its reorder rate better than its
clause order: where the genitive comes before the noun, or the language has postpositions, "X of Y" and
"X from Y" become "Y's X" and "Y-from X".

No prior work we could find measures this. Style guides tell translators to number placeholders so that
they can reorder them; placeholder-order 0.1.0 was the first per-language count we know of.

## What we had already seen

placeholder-order 0.1.0's report: the SOV and SVO group rates, Chinese (zh) at 7.7%, and five SOV
languages with low rates (ka, hy, ckb, fa, am). That last list is what suggested noun-phrase order: ckb and
fa put the genitive after the noun. But ka and hy, as far as we know, put it before, so the idea does not
explain all five. We have not looked at WALS values for any other language, or at the per-language rates
beyond those named here.

## Method (fixed now)

- Rates: placeholder-order 0.1.0's `by_language.csv` (pooled reorder rate of numbered sources per
  language), languages with at least 300 such translations in at least 10 repositories.
- Language codes -> ISO 639-3 with the SIL code tables; for macrolanguages, a short main-variety list in
  the code (zh -> cmn, fa -> pes, and others), then the code itself, then its member languages. Where WALS
  entries disagree, the language is left out of that feature.
- WALS (Dryer & Haspelmath 2013, CLDF data, CC BY 4.0), dominant orders only:
  81A SOV vs SVO/VSO/VOS; 85A postpositions vs prepositions; 86A genitive-noun vs noun-genitive;
  87A adjective-noun vs noun-adjective; 90A relative clause-noun vs noun-relative clause.
- Measure: AUC, the chance that a random language on the first side has a higher rate than a random
  language on the second side. Comparisons use languages that have both features. A bootstrap over languages
  gives a 95% interval for each difference, reported but not part of the predictions. A comparison needs
  at least 3 languages on each side, or it is "not testable".
- Mapping checks: ja is SOV and genitive-noun, fr is SVO and noun-genitive, tr has postpositions, es has
  prepositions. If any of them fails, no prediction is scored.

## Predictions

- P1. Genitive order (86A) separates reorder rates better than verb-final order (81A): higher AUC.
- P2. Adposition order (85A) separates them better than verb-final order (81A).
- P3. Among SOV languages, noun-genitive ones have a lower median rate than genitive-noun ones (needs at
  least 2 noun-genitive and 3 genitive-noun SOV languages).
- P4. Among SVO, VSO and VOS languages other than zh and yue (already seen), genitive-noun ones have a
  higher median rate than noun-genitive ones.
- P5. Genitive order (86A) separates rates better than adjective order (87A), because English already puts
  adjectives first and adjectives rarely hold an argument.

## Limits

- These features are strongly correlated in the world's languages, and the sample is the few dozen
  languages app translators use, many of them Indo-European. A higher AUC is a pattern, not a cause.
- WALS describes a language's main variety; app text is written language. Rates are pooled over apps, so
  a few large apps weigh a lot. The output also gives AUCs on unique string pairs and repository means.
