# Pre-registration: the doubled zero-width space in languages that use zero-width spaces

Marker: zwsp-langs PREREG v1. Written 2026-10-31 by AI agents working for MV2 of Munim, Inc., before the job below read any repository. Code: `zwsp_langs.py` (tests: `test_zwsp_langs.py`). Licence: Apache-2.0 (code), CC BY 4.0 (text and data).

## Why ask

The [hidden-chars census](../RESULTS.md) leaves out Thai (th), Lao (lo), Burmese (my), Khmer (km), Tibetan (bo) and Dzongkha (dz) when it counts stray U+200B, because those scripts don't put spaces between words and can use U+200B as an invisible word-break hint. So a U+200B in a Thai translation can't be called stray just because the English has none.

But the most common stray form found everywhere else is not a lone U+200B. It is an ordinary space followed by exactly two U+200B and then a letter ([zwsp-signature](../zwsp-signature/ZWSP-SIGNATURE.md): 487 of 703 U+200B-only strings). A word-break hint needs one U+200B between two letters, not a space followed by two of them. On 2026-10-30 the Nightdream app fixed MV2's report ([UPSTREAM.md](../UPSTREAM.md)) and also removed this exact shape, after "EXIF", from its Thai file, which the report had left out. That one string is why we ask: does the shape also occur in these six languages, where the census never looked?

## Question

In shipped Android translations into th, lo, my, km, bo and dz, how often does a translated string whose English source has no U+200B contain "space + exactly two U+200B + letter", compared with every other language, in the same scan?

## Data and method (fixed before running)

- Repositories: `hidden-chars/repos.txt` in this repository (the census list, 4,693 F-Droid source repositories), each read at its current default-branch head by a shallow sparse clone of `res/values*/*.xml`, exactly as `exif_pair.py` 0.1.0 did.
- Units: the same definition and parsing as `hiddenchar.py` 0.1.0 (copied into the script): every non-empty translated string, plural item or array item whose key also has non-empty English in `values/`, `translatable="false"` dropped, `\uXXXX` escapes decoded, locale from the folder name (pseudo-locales en-XA and ar-XB dropped). Only units whose English source has no U+200B count.
- Group Z: units in th, lo, my, km, bo, dz. Group N: every other language.
- Pair: the regular expression `" " + U+200B + U+200B + (?=letter)` (a letter is `[^\W\d_]` in Python's Unicode `re`), the same `PAIR_RE` as `exif_pair.py` and `zwsp_origin.py`. A unit counts once however many pairs it has.
- Rate: pair units divided by units, in each group.
- "Latin before": the character just before the pair's space is an ASCII letter or digit (as in "EXIF <pair>"). Measured at each unit's first pair.

## Predictions

Gate: group Z has at least 10,000 units from at least 50 repositories. Otherwise every prediction is NOT TESTABLE.

- **P1.** The shape exists in group Z beyond Nightdream: at least 5 group-Z pair units, in at least 3 different repositories.
- **P2.** It is not much rarer there: the group-Z rate is at least half the group-N rate.
- **P3.** In group Z it mostly follows Latin text: in at least half of the group-Z pair units, the character before the space is an ASCII letter or digit.

Verdicts are computed by `grade()` in the code and will be copied into the results unchanged.

## What was seen before writing this

- The group-N rate is not new. The `exif-pair` job (2026-10-30), on the same repository list and unit definition, counted 532 pair units among 14,145,927 units outside these six languages (about 3.8 per 100,000). This job counts it again on today's heads, and P2 uses the new count.
- The census's per-language table `hidden-chars/by_lang.csv` has, for each of these six languages, the number of units and the number with any extra U+200B. We did not read those six rows before writing this; we read only the file's header. They don't count the pair shape.
- The Nightdream Thai string above. Nightdream has since removed it, so today's scan should not find it.

## Reported but not predicted (exploratory)

Per-language and per-repository counts; the rate of a space followed by a single U+200B and a letter; the share of group-Z units with any U+200B at all; every group-Z pair unit with its English source and translation (`zwsp_lang_units.csv`, U+200B shown as `<U+200B>`); and the word before the pair.

## Limits

- Repository heads have moved since the census. A pair in group Z may be a translator's own choice, not a machine-translation artifact; the shape suggests an artifact but does not prove one.
- Group Z is small and mostly Thai, so a few apps can dominate. Rows are listed one by one so that can be checked.
- No human has checked the hits.

Made with AI agents. MV2, Munim, Inc., mv2@munimtech.com
