# Results: letters from another alphabet in Cyrillic Android translations

Graded 2026-11-01 by AI agents working for MV2 of Munim, Inc., against the pre-registration
[PREREG.md](PREREG.md) (cyrillic-leak PREREG v1, SHA-256 `6503431701226106db9756439aaa07f305a31045b5df6aa21174e02493f7bd45`,
recorded by the job). The job ran on 2026-11-01 from 08:13 to 08:37 UTC with
[cyrillic_leak.py](cyrillic_leak.py) 0.1.0; its unit tests passed first. Verdicts below are copied
unchanged from [summary.json](summary.json). Every flagged string is in [flagged.csv](flagged.csv).
Apache-2.0 code; results and data CC BY 4.0.

## Headline

Shipped Ukrainian translations in F-Droid apps rarely contain Russian-only letters (54 of
302,844 strings, about 1.8 per 10,000), but they do so in 39 apps. Our guess about where they
come from was wrong: only 9 of 49 are copies of the app's own Russian string. Most are a Russian
word or spelling inside an otherwise Ukrainian sentence (`режим электронного ключа`,
`Увымкнути Wi-Fi`, `выдкрийте`). Belarusian files have the problem nearly four times as often
(6.7 per 10,000), and there half of the hits are whole Russian strings left in place.

## Verdicts

| | Prediction | Numbers | Verdict |
|---|---|---|---|
| Gate | each language >= 10,000 units in >= 30 repositories | uk 302,844 in 756; be 93,355 in 220; ru 475,756 in 1,313 | passed |
| P1 | >= 20 repositories ship a flagged Ukrainian unit | 39 repositories | **HELD** |
| P2 | of flagged uk units with a Russian string, at least half are identical to it | 9 of 49 | **FAILED** |
| P3 | flagged share higher in Belarusian than in Ukrainian | 63 / 93,355 vs 54 / 302,844 | **HELD** |
| P4 | flagged share lower in Russian than in Ukrainian | 240 / 475,756 vs 54 / 302,844 | **FAILED** |

The positive control passed (before the scan, the detector fired on known foreign-letter strings and stayed quiet on clean ones), and the
two self-test repositories (NewPipe, F-Droid client) were read in all six languages.
4,693 repositories were listed: 1,376 had Cyrillic translations, 3,219 had none, 98 failed to
clone, and 1 file could not be parsed.

## All six languages

| Language | Repos | Units | Flagged | Repos flagged | Per 10,000 | Russian string available | Identical to it | Also has a letter of its own (`native`) |
|---|---|---|---|---|---|---|---|---|
| uk Ukrainian | 756 | 302,844 | 54 | 39 | 1.8 | 49 | 9 | 28 |
| be Belarusian | 220 | 93,355 | 63 | 23 | 6.7 | 63 | 26 | 28 |
| ru Russian | 1,313 | 475,756 | 240 | 8 | 5.0 | - | - | 0 |
| bg Bulgarian | 344 | 126,835 | 15 | 6 | 1.2 | 15 | 0 | 0 |
| sr Serbian (Cyrillic) | 286 | 112,273 | 76 | 5 | 6.8 | 76 | 24 | 4 |
| mk Macedonian | 127 | 32,683 | 5 | 5 | 1.5 | 5 | 0 | 3 |

## Why P4 failed: one app's ru-UA folder

219 of the 240 flagged Russian units are in one app, FreezeYou, whose `values-ru-rUA` folder
(Android's "Russian, Ukraine" locale) holds Ukrainian text identical to its `values-uk`.
ActivityLauncher does the same with 4 strings. Users whose phones are set to Russian in Ukraine
see Ukrainian there. That may be a deliberate choice rather than a mistake, and the
pre-registration did not foresee it. Post hoc, not pre-registered: without the two `ru-rUA`
folders, 17 flagged units remain in 6 repositories, which would have put Russian below
Ukrainian. The verdict stays FAILED. Among those 17, multivnc's `values-ru` has 12 Ukrainian
strings (10 SSH prompts and 2 quality settings), so Russian users see Ukrainian there.

Similar concentration elsewhere: 69 of the 76 Serbian units are a Russian file in
`_old/SlimFacebook/.../values-sr-rRS` of SlimSocial-for-Facebook (old code). In Bulgarian, three
"Скрыть ..." strings in Session (and in a fork of it) are Russian.

## Hand check of every flagged Ukrainian and Belarusian unit (not pre-registered)

All 117 flagged uk and be units were read and labelled by AI agents (not native speakers) after
the verdicts were fixed. Labels are in [hand_check.csv](hand_check.csv).

| Label | uk | be |
|---|---|---|
| `mixed`: a Russian word, spelling or keyboard slip inside a real translation | 32 | 28 |
| `russian_string`: the whole string is Russian | 11 | 31 |
| `other_language`: Belarusian text in a uk file, or Ukrainian in a be file | 1 | 3 |
| `deliberate`: not a defect | 10 | 1 |
| A user sees text that isn't in their language | 44 of 54 (81%) | 62 of 63 (98%) |

- **What the false flags were.** 8 of the 10 deliberate uk hits are keyboard keys or letter lists:
  hackerskeyboard's and klavesnice's key maps, Jellyfin's A-Z jump bar (which lists Russian letters
  on purpose so Russian titles can be found), and emerald-dialer's T9 letter classes. The other
  2 are the Soviet calculator brand "Электроника". All 10 are a single letter, a run of letters
  with no word, or a proper name.
- **Keyboard slips.** On a Ukrainian layout `і` sits on the key where a Russian layout has `ы`,
  and on a Belarusian layout `і` is where Russian `и` is. Hits like `Увымкнути`, `выдкрийте`,
  `выберіть` (uk) and `прывесци`, `радки` (be) look like typing with the wrong layout switched on.
  Others are Russian words: `электронного`, `монеты`, `службы`, `дымка`.
- **Copies across forks.** The same flagged string often appears in several repositories: the
  ics-openvpn routing FAQ (3), the bitcoin-wallet send title (3), Gadgetbridge and a fork (2), a
  launcher family's "Электронна пошта" (4), Organic Maps and CoMaps (2 per language), and an
  InnerTune-family "Змяниць тэкст песні" (5). Merging forks, about 30 independent Ukrainian
  sources remain, so P1 would still hold (post hoc).

## What this means for a checker

A per-language letter rule finds real problems with high precision in shipped Android apps here:
81% of Ukrainian and 98% of Belarusian flags were text in the wrong language, and the false
flags had an easy shape to exclude (no word of two or more letters, or a key-map file). A
`wrong-alphabet` warning for [l10n-guard](https://github.com/munimtechnologies/l10n-guard) is
the natural follow-up; its precision should be measured on data not used here, with the rule
fixed first.

## Prior art and what is new

[python-po-lint](https://pypi.org/project/python-po-lint/) (0.3.0, MIT) already checks Ukrainian
and Russian `.po` files for each other's distinctive letters, and
[Kuantor/kuantorflow#544](https://github.com/Kuantor/kuantorflow/issues/544) applied the same idea to
machine-translated flashcards. We found no published count of such strings in shipped app
translations, and no test of whether they are copies of the app's Russian file. This study adds
both, and the answer to the second (mostly not) was the opposite of our pre-registered guess.

## Limits

- The letter rule only sees Russian text that uses one of the foreign letters, so these are lower
  bounds, looser for Ukrainian (four rare letters) than for Belarusian (`и`). P3 is partly a test
  of that difference.
- One snapshot of default branches on 2026-11-01. Labels are AI-graded, not checked by speakers.
- Repositories that build an old folder or none of a flagged file still count; SlimSocial's
  `_old` folder is the clearest case.
