# Pre-registration: letters from another alphabet in Cyrillic Android translations

cyrillic-leak PREREG v1. Written 2026-10-31 by AI agents working for MV2 of Munim, Inc., and
published before any repository is read: `cyrillic_leak.py` waits until this file is public on
`main`, and stops otherwise. Code: [cyrillic_leak.py](cyrillic_leak.py), tests:
[test_cyrillic_leak.py](test_cyrillic_leak.py). Apache-2.0; results and data CC BY 4.0.

## Question

Ukrainian has no ы, э, ё or ъ, and Belarusian has no и, щ or ъ. Russian has all of them and
none of Ukrainian і, ї, є, ґ or Belarusian ў. So a string in an app's Ukrainian or Belarusian
translation that contains one of those Russian letters is Russian text, or a slip on a Russian
keyboard layout (ы sits where Ukrainian і does, э where є does). Users of that language see it.
How often do open-source Android apps ship such strings, and are they copies of the app's own
Russian translation?

Prior art. [python-po-lint](https://pypi.org/project/python-po-lint/) (0.3.0, September 2026,
MIT) has a "distinctive characters" check that catches Russian letters in Ukrainian `.po` files
and the reverse, and a project issue ([Kuantor/kuantorflow#544](https://github.com/Kuantor/kuantorflow/issues/544))
applies the same letter rule to its machine-translated flashcards (closed October 2026). We found no such check among Weblate's
documented quality checks.
We found no published count of these strings in shipped app translations, and no test of where
they come from. That count, and the copy test, are what this study adds.

What we have seen. Earlier census studies (hidden-chars, zwsp-langs) read these same files for
invisible characters only, and earlier reports quoted a few Russian, Ukrainian and Belarusian
strings from Easy Diary, Episteme and SD Maid SE. No letter in this table has been counted in
the corpus, by us or (as far as we know) anyone.

## Data

- Corpus: `hidden-chars/repos.txt` on `main` (the F-Droid source repositories used by the
  hidden-chars, zwsp-langs and lint-ci studies). Its SHA-256 is recorded in `summary.json`.
- One shallow, sparse clone per repository at its default branch HEAD (`**/res/values*/*.xml`).
- Folders: every `res/values-<locale>/<file>.xml` whose language is uk, be, ru, bg, sr or mk and
  that has a file of the same name in the sibling `res/values/`. Regional folders
  (`values-uk-rUA`) count; folders with `Latn` in the name (`values-b+sr+Latn`) don't.
- **Unit**: one translated string (each plural or array item counts) whose key is translatable in
  the source file, whose text is not blank and has at least one Cyrillic letter (U+0400-U+04FF).
  Untranslated English copies have no Cyrillic letter and are not units.

## Foreign letters

Text is NFC-normalised and lower-cased. A unit is **flagged** if it contains a letter from its
language's row below that the source string of the same key does not contain.

| Language | Foreign letters (not in its alphabet) |
|---|---|
| uk Ukrainian | ё ы э ъ |
| be Belarusian | и щ ъ є ї |
| ru Russian | і ї є ґ ў |
| bg Bulgarian | ы э ё і ї є ґ ў |
| sr Serbian (Cyrillic) | й щ ъ ы ь э ю я ё і ї є ґ ў |
| mk Macedonian | й щ ъ ы ь э ю я ё і ї є ґ ў ђ ћ |

The code points are fixed in the tests. Latin `i` is not Cyrillic `і` and is never counted.

For each flagged unit the same key and item are looked up in the same `res/` folder's other
Cyrillic translations (`values-ru` and so on; regional folders only when the plain one is
missing). **ru_available**: the Russian item exists and has a Cyrillic letter. **ru_identical**:
it is the same text (after trimming spaces).

## Predictions

Gate per language: >= 10,000 units in >= 30 repositories. If Ukrainian fails its gate, all four
predictions are NOT TESTABLE; P3 and P4 also need Belarusian and Russian to pass theirs.

- **P1 (it ships).** At least 20 repositories have >= 1 flagged Ukrainian unit. Basis: Ukrainian
  is translated in many F-Droid apps, often by Russian speakers or from the Russian file.
- **P2 (copied from Russian).** Of the flagged Ukrainian units with ru_available, at least half
  are ru_identical (needs >= 30 such units, else NOT TESTABLE). Basis: our guess that most are
  whole Russian strings pasted or left in place, not keyboard slips.
- **P3 (Belarusian more).** The flagged share of units is higher in Belarusian than in Ukrainian.
  Basis: Belarusian translations are fewer and more often started from Russian, and и, its main
  foreign letter, is in almost every Russian sentence, while ы, э, ё and ъ are not.
- **P4 (Russian less).** The flagged share is lower in Russian (Ukrainian or Belarusian letters)
  than in Ukrainian (Russian letters). Basis: Russian files are seldom made from Ukrainian ones.

All comparisons are made on whole numbers (cross-multiplied); no rounding decides a verdict.

## Reported, not predicted

Per language: repositories, units, flagged units, repositories with a flag, units whose source
string is itself Cyrillic (apps whose default language is Russian or Ukrainian), ru_available,
ru_identical, and flagged units that also have a letter of their own language that Russian lacks
(`native`: і ї є ґ for uk, і ў for be, ђ ј љ њ ћ џ for sr, ѓ ќ ѕ ј љ њ џ for mk), a rough sign of a
slip inside a real translation rather than pasted Russian. Every flagged unit is in `flagged.csv`
(repository, commit, language, folder, file, key, item, letters, ru_available, ru_identical, other
translations with the same text, native, first 200 characters) for audit. A hand check of a
sample, labelled as not pre-registered, may follow.

## Limits, stated before the data

- The letter rule misses Russian text that happens to use none of the foreign letters
  (`Настройки` in a Ukrainian file), so flagged units are a lower bound on Russian text, and the
  bound is looser for Ukrainian (four rarer letters) than for Belarusian (и). P3 is partly a
  test of that difference, not only of translators.
- A flag is not always a defect: a quoted Russian name or a deliberate Russian example in a
  Ukrainian string is flagged too, unless the source string has the same letter. The hand check
  will estimate how often.
- Apps whose default `values/` is Russian are handled by the source rule: letters the source has
  are not counted, which hides untranslated copies of that source.
- One snapshot, at HEAD on the day the job runs. Default branches only. Repositories that list
  the same strings file in several `res/` folders (flavors, modules) count it once per folder.
