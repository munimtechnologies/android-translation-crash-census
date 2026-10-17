# np-order 0.1.0: results

Made by MV2 of Munim, Inc. with AI agents. Code Apache-2.0; text and data CC BY 4.0. WALS data:
Dryer & Haspelmath (eds.) 2013, CC BY 4.0.

The question, the method and five predictions were published in [PREDICTIONS.md](PREDICTIONS.md) before
the job ran. The job (np-order-v1, 2026-10-17 02:50Z) checked that file was on main before it started.
Full output: [np_order.md](np_order.md), [np_order.json](np_order.json), [languages.csv](languages.csv).

## Short answer

No. A language's noun-phrase order does not predict how often its app translators reorder numbered
placeholders better than its clause order does. Verb-final (SOV) order still separates the 75
languages best (AUC 0.99). Genitive order and adposition order come close but do not beat it.
Two of five predictions held, two failed and one could not be tested.

| | prediction | result | numbers |
|---|---|---|---|
| P1 | genitive order (86A) beats verb-final order (81A) | FAILED | AUC 0.924 vs 0.988 on 46 languages; difference 95% CI [-0.162, 0.008] |
| P2 | adposition order (85A) beats verb-final order (81A) | FAILED | AUC 0.983 vs 0.995 on 50 languages; difference 95% CI [-0.050, 0.010] |
| P3 | among SOV languages, noun-genitive ones reorder less | NOT TESTABLE | only one SOV noun-genitive language (Persian) met the size rule |
| P4 | among non-SOV languages (zh, yue left out), genitive-noun ones reorder more | HELD | median 1.56% (6 languages) vs 0.44% (21 languages) |
| P5 | genitive order beats adjective order (87A) | HELD | AUC 0.926 vs 0.821 on 53 languages; difference 95% CI [0.008, 0.224] |

AUC is the chance that a random language on the first side (SOV, postpositions, genitive-noun, ...)
has a higher reorder rate than a random language on the other side. Both P1 and P2 intervals touch
zero, so the data say "not better", not "clearly worse".

## What the numbers mean

- **Clause order is the best single sign, but it is not alone.** Relative-clause order (90A, not part of
  any prediction) is about as strong (AUC 0.987). In the languages app translators use, verb-final order,
  postpositions, genitive-first and relative-clause-first go together, so these comparisons cannot say
  which one moves the placeholders. That is why the next study looks at the strings instead (below).
- **P3 had too few languages to test.** Persian, the only SOV noun-genitive language with at least 300
  translations in 10 repositories, reorders 2.9% of the time, against a median of 14.7% for the 17 SOV
  genitive-noun languages. Central Kurdish (2.4%) is below the size rule (125 translations) and was not
  used. One language cannot carry a test.
- **P4 held, but on four languages.** The genitive-noun side was Estonian 3.0%, Lithuanian 2.2%, Latvian
  2.1%, Finnish 1.0%, Swedish 0.3% and Danish 0.09%. Danish and Swedish, genitive-first like the others,
  are among the lowest rates of all. The four that lift the median are Baltic and Finnic languages,
  which have rich case systems. Genitive order alone does not explain them.
- **P5 held:** adjective order separates the languages least well (AUC 0.82), as expected, since English
  already puts adjectives first and adjectives rarely hold an argument.
- **Not predicted, so not a finding:** the two SOV languages with the lowest rates, Georgian (2.2%) and
  Persian (2.9%), are both coded by WALS as noun-relative clause. Sinhala has the same code and reorders
  13.0% of the time, so even this does not hold cleanly. With a fixed set of languages it cannot be
  tested on these data.

## Checks

- Built-in mapping checks (ja SOV and genitive-noun, fr SVO and noun-genitive, tr postpositions, es
  prepositions): all passed.
- By hand on wals.info, 17 datapoints compared with languages.csv, all matching: Georgian 81A SOV, 86A
  Genitive-Noun, 90A Noun-Relative clause; Persian 81A SOV, 86A Noun-Genitive, 90A Noun-Relative clause;
  Eastern Armenian 81A No dominant order; Hungarian 81A No dominant order, 86A Genitive-Noun; German 81A
  No dominant order; Finnish 86A Genitive-Noun; Mandarin 85A No dominant order, 86A Genitive-Noun;
  Japanese 81A SOV; French 86A Noun-Genitive; Latvian 86A Genitive-Noun; Estonian 85A Postpositions;
  Danish 86A Genitive-Noun; Sinhala 90A Noun-Relative clause.
- WALS entries that looked odd by code were checked: `arz` is Armenian (Iranian), `kug` is Kunming
  (a Mandarin variety), `lat` is Latvian.
- Arabic and Malay have no 81A value here because their WALS varieties disagree; the method leaves such
  languages out of that feature, as written.

## Limits

- 75 languages, many of them Indo-European, and the features are correlated. A higher AUC is a pattern,
  not a cause.
- WALS describes each language's main spoken variety; app text is written. Rates are pooled over apps,
  so large apps weigh more; the AUCs on unique string pairs and on repository means are close to the
  pooled ones (np_order.md, "Each feature alone").
- Rates come from [placeholder-order 0.1.0](../README.md) (189,599 translations in 4,476 F-Droid
  repositories), read in source files, not on devices.

## Next

[shape 0.1.0](../shape/PREDICTIONS.md) tests the same idea at the level of single strings: whether
"X of Y" and "X to Y" sources are reordered more in SOV languages than sources whose arguments are only
separated by punctuation. Its predictions were published before it runs.
