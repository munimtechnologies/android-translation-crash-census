# Results: store-listing language keys in F-Droid's index that no phone can select

listing-codes census, graded 2026-11-09 against [PREREG.md](PREREG.md) (sha256
`ed683eff6d004c92df3d13af144e108d4d97515fc7948f34cb514061f5f3b3d0`, public before the job read any
index). Made with AI agents by MV2 of Munim, Inc. The hand labels were made by AI agents, not by the
apps' maintainers or by F-Droid. Code Apache-2.0; text and data CC BY 4.0.

## Verdicts

| | Prediction | Result | Verdict |
|---|---|---|---|
| Gate | >= 3,000 packages, >= 8,000 registry languages | 4,988 packages; 8,276 languages (registry of 2026-09-17) | passed |
| K1 | packages with an invalid key are 0.5-6.0% | 152 of 4,988 (3.05%) | **HELD** |
| K2 | >= 8 packages with an `unregistered-language` key | 49 | **HELD** |
| K3 | >= half of the packages with a listed mistyped code have lost that language | 16 of 16 | **HELD** |
| K4 | `android-r` is the most common invalid class | it is the *least* common: 17 packages, against 49 `unregistered-language`, 43 `underscore`, 26 `unregistered-subtag`, 22 `malformed` | **FAILED** |
| H1 | >= 3 in 4 sampled keys hold a translation (>= 8 checked) | 12 of 20 (60%) | **FAILED** |

Three of five held. Both misses are real misses, and both come from the same wrong picture: we
expected Android-style folder names (`zh-rCN`) copied from `res/values-*` to dominate, and we
expected an invalid key to hold a real translation. Neither is true:

- **K4.** Underscore keys (`pt_BR` 16, `zh_CN` 10, `zh_Hans` 10, `nb_NO` 11, `en_US` 6) and
  unregistered codes are far more common than `zh-rCN`-style keys. The most common single invalid
  key is `sr-SP` (19 packages; `SP` is not a region code).
- **H1.** Of the 20 sampled keys, 12 hold a translation, 5 hold English and 3 have no text (only
  screenshots or an icon). Of the 5 English ones, 2 are `en_US` / `en_GB` keys where English is
  the right language (the prediction's wording counted them as non-translations; we note it but
  do not change the verdict), 2 are copies of the en-US text under another language's key
  (`es-rMX`, `fi_FI`), and 1 is a product-flavour key (`opff`). A post-hoc reading that drops
  the 2 English-meant keys and the 3 keys with no text gives 12 of 15 (80%), which would have
  passed; this is reported only as a description, not as a verdict.

Labels: [labels.csv](labels.csv). Job outputs, unchanged: [v1/](v1/).

## What the census found

F-Droid's index of 2026-11-09 has 4,988 packages, 2,848 of them with at least one non-English
listing key. 152 packages (3.05%) publish at least one key that is not a valid BCP 47 language tag,
292 keys in all. IzzyOnDroid (exploratory) has 27 of 1,405 (1.9%).

**Mistyped language codes lose their language.** 16 packages carry a key whose language part is a
country or a made-up code from the fixed list (`sp` for Spanish 5, `ua` 4, `cz`/`cz-CZ` 3, `jp-JP`
2, `gr` 1, `du-NL` 1), and none of the 16 has a valid key for the meant language. F-Droid's client
chooses a key by the phone's languages, and a key whose language part is not a language is never
chosen that way, so these translations reach no one who reads the language (they can only appear
as a last fallback when a field has no English). This reading of the client comes from its source
(`LocaleChooser.kt`), not from running it.

**Exploratory, classified by hand after the run: one in five invalid packages has a folder name, not a
language, as a key.** 33 of the 152 packages publish a file-layout word as a language:
`android` (11), `phoneScreenshots` (8), `metadata` (4), `featureGraphic` (3), `images`/`Images`
(3), `icon` (2), `play` (2), `changelogs` (1) and `tr_description.txt` (1). Most of these keys
carry screenshots, icons or feature graphics. When the same field also has English, which is true
for most of them, the images under the stray key are never shown. A few work only by accident,
because the stray key is the field's only key (for example KDE KTrip's phone screenshots under
`android`). fdroidserver takes any folder whose name starts with two lowercase letters as a locale
(the `[a-z][a-z]*` glob in `update.py`), so these land in the index without a warning. Separately,
the Open Food Facts apps publish product-flavour keys (`off`, `obf`, `opf`, `opff`) and four
gsantner apps publish `zz`.

Other exploratory counts (from [v1/summary.json](v1/summary.json)):

- How invalid keys are reached in the client (`reach_by_class`): almost always the field also has
  English (`fallback-en`, 280 of the 311 counts), so the key is shown to nobody it was meant for;
  15 counts are a field's only key (shown to everyone) and 16 a field with no English.
- Registered codes often used for another language (`kr`, `se`, `ee`, `ch`): 0 packages.
- Valid tags in non-canonical case (`en-us`, `pt-br`, `de-De`, ...): 14 keys, 19 package counts.

## Limits

- The index shows what F-Droid publishes, not which folder each key came from (fastlane, Triple-T
  or fdroiddata). The mechanism for the file-layout keys is inferred from fdroidserver's source.
  It has not been reproduced.
- `android-r`, `underscore` and `unregistered-subtag` keys may still be reached through the
  client's language-prefix fallback; only mistyped language codes are claimed to be unreachable.
- Other clients (Droid-ify, Neo Store) and the f-droid.org website choose keys their own way and
  were not tested.
- The classifier checks that every subtag is registered, not that an extlang's prefix fits, so
  `sl-rSI` (read as Slovenian plus the sign-language extlang `rsi`) counted as valid. It is an
  Android-style key, so `android-r` is undercounted by at least one package. This does not change K4.
- The 20-row sample covers keys of three classes only (`android-r`, `underscore`,
  `unregistered-language`), as pre-registered.

## Prior art

F-Droid's issuebot has an open idea to validate fastlane/Triple-T locale names (issue 30, with
`pt-rBR` and `zh-rCN` as examples, no counts). The `validate-fastlane-supply-metadata` GitHub
Action checks one project's folders against Google Play's list. We found no earlier count across
a published F-Droid index, and no report of file-layout folders published as languages.

## Files

- [PREREG.md](PREREG.md), [listing_codes.py](listing_codes.py), [test_listing_codes.py](test_listing_codes.py)
- [labels.csv](labels.csv): hand labels for the H1 sample
- [v1/](v1/): job outputs, unchanged: `summary.json`, `sample.csv`, `fdroid-keys.csv` and
  `izzyondroid-keys.csv` (every invalid key with its text), `fdroid-all-keys.csv` and
  `izzyondroid-all-keys.csv` (every key each index publishes, with class and package count;
  CC BY 4.0)
