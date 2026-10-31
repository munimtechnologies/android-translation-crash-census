# Results: the doubled zero-width space in Thai, Lao, Burmese, Khmer, Tibetan and Dzongkha translations

Graded 2026-10-31 by AI agents working for MV2 of Munim, Inc. Pre-registration: [PREREG.md](PREREG.md) (marker "zwsp-langs PREREG v1", public before the job read any repository; the job recorded its SHA-256, `a397e843...`). Code: `zwsp_langs.py` 0.1.0, unchanged. Job `zwsp-langs-v1` ran 2026-10-31 09:45-10:05 UTC: its offline tests passed, then it read all 4,693 listed repositories in 17.5 minutes (2,392 with translations, 2,209 without, 92 clones failed). Licence: Apache-2.0 (code), CC BY 4.0 (text and data).

## Pre-registered verdicts (copied unchanged from `summary.json`)

Group Z = th, lo, my, km, bo, dz. Group N = every other language. Pair = a space, then exactly two U+200B, then a letter, in a translated string whose English source has no U+200B.

| | Prediction | Result | Verdict |
|---|---|---|---|
| Gate | group Z has at least 10,000 units from at least 50 repositories | 228,725 units from 341 repositories | met |
| P1 | at least 5 group-Z pair units, in at least 3 repositories | **4** units in 3 repositories | **FAILED** |
| P2 | group-Z pair rate at least half the group-N rate | Z 4 / 228,725 (1.7 per 100,000); N 521 / 14,155,380 (3.7 per 100,000); ratio 0.475 | **FAILED** |
| P3 | at least half of the group-Z pairs follow an ASCII letter or digit | 0 of 4 | **FAILED** |

**In short:** all three predictions failed. The doubled zero-width space is not hiding in the six languages the census skipped. It appears in only 4 of their 228,725 translated strings, at about half the rate seen in every other language, and none of the 4 follows Latin text the way "EXIF <U+200B><U+200B>" does elsewhere. So leaving these languages out of the census's stray-U+200B count removed very little of this shape. The Thai "EXIF" string that prompted the question (Nightdream) was fixed upstream before the scan and, as expected, was not found.

P2 missed its bar narrowly (0.475 against 0.5), and with only 4 group-Z pairs the group-Z rate is very imprecise. The fair reading is "rare in both groups, no sign that it is commoner in group Z", not "half as common".

## The four strings (exploratory)

All four are in [`zwsp_lang_units.csv`](zwsp_lang_units.csv), with the English source and the translation (U+200B shown as `<U+200B>`).

| App | Language | Word before the pair | What follows |
|---|---|---|---|
| Rhythm | Thai | ทันสมัย ("modern") | Thai text (2 strings) |
| mullvadvpn-app | Burmese | ကို (object marker) | Burmese text |
| RecorderX | Tibetan | དང་། ("and") | "H.265" |

In each, a native word ends a phrase, then comes a space, the pair, and the next phrase. That is the same shape as elsewhere, just after a native word instead of a Latin one. Whether these came from a tool or a translator wasn't checked, and no native speaker has looked at them.

## Other numbers (exploratory, not predicted)

- **Group N recount.** 521 pair units in 14,155,380, against 532 in 14,145,927 when the `exif-pair` job read the same list on 2026-10-30. Heads moved in between (Nightdream's fix is one known change).
- **Any U+200B in group Z.** 7,102 of 228,725 group-Z units (3.1%) contain U+200B somewhere, against 698 of 14,155,380 in group N. This is the legitimate word-break use the census excluded on purpose, and it is very uneven: Khmer 19.3% of units, Lao 6.4%, Burmese 0.48%, Tibetan 0.02%, Thai 0.03%, Dzongkha 0%. It is also concentrated: 13 repositories hold 6,281 of the 7,102, several of them keyboard apps that share the same strings, plus Google's TalkBack.
- **Space + one U+200B + letter.** 33 group-Z units (21 of them Khmer) against 12 in group N. In Khmer this may be ordinary use, so it is not called an error here.

| Language | Units | Pair | Space + one U+200B | Any U+200B |
|---|---:|---:|---:|---:|
| th | 122,257 | 2 | 1 | 31 |
| lo | 39,669 | 0 | 7 | 2,553 |
| my | 39,008 | 1 | 4 | 186 |
| km | 22,430 | 0 | 21 | 4,331 |
| bo | 4,023 | 1 | 0 | 1 |
| dz | 1,338 | 0 | 0 | 0 |

## What this means for checkers

A checker should keep treating a lone U+200B as normal in these six languages. The doubled shape is rare there too, and when it occurs it is just as out of place (a space already breaks the line, so the U+200B adds nothing). A checker could flag "space + two U+200B" in every language without hurting the legitimate use in Khmer or Lao. That is a suggestion from four strings, not a measured false-positive rate.

## Limits

- 4 group-Z pairs is too few to estimate a rate. The verdicts are what the pre-registration said they would be, and it set its bars before anyone knew the count would be this small.
- Heads were read on 2026-10-31. Group Z is mostly Thai (53% of its units), and Dzongkha and Tibetan are tiny.
- The census list is F-Droid source repositories; apps translated outside Android `res/values*` files are not covered.
- No human has checked the hits.

## Files

- [`PREREG.md`](PREREG.md), [`zwsp_langs.py`](zwsp_langs.py), [`test_zwsp_langs.py`](test_zwsp_langs.py): the pre-registration and the code that was run.
- [`summary.json`](summary.json): the job's output, with the verdicts, the pre-registration and repository-list hashes and the per-language counts.
- [`zwsp_lang_units.csv`](zwsp_lang_units.csv): the four group-Z pair strings.
- [`repos.jsonl`](repos.jsonl): per repository, its head, status and the group-Z / group-N counts (units, pair, space + one U+200B, any U+200B).

Made with AI agents. MV2, Munim, Inc., mv2@munimtech.com
