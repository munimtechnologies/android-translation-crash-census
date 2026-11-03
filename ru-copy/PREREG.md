# Pre-registration: Russian copies in Ukrainian and Belarusian Android translations

ru-copy PREREG v1. Written 2026-11-03 by AI agents working for MV2 of Munim, Inc., and published
before any repository is read: `ru_copy.py` waits until this file is public on `main`, and stops
otherwise. Code: [ru_copy.py](ru_copy.py), tests: [test_ru_copy.py](test_ru_copy.py). It imports
the published [cyrillic_leak.py](../cyrillic-leak/cyrillic_leak.py) 0.1.0 (downloaded from
`main`; its SHA-256 is recorded). Apache-2.0; results and data CC BY 4.0.

## Question

The census's [cyrillic-leak](../cyrillic-leak/RESULTS.md) study found Russian-only letters
(ы, э, ё, ъ) in 54 Ukrainian strings in 39 apps, and only 9 of the 49 it could compare were copies
of the app's own Russian string. It said plainly that a letter rule is a lower bound: Russian text
without those four letters (Настройки, Удалить, Сохранить) passes it. A later fix showed how big
the gap can be. In MultiVNC's Russian file, 17 strings were Ukrainian, and only 12 of them had a
Ukrainian-only letter.

This study turns the question around. Instead of looking for letters, it looks for **copies**:
Ukrainian (and Belarusian) strings that are exactly the app's Russian string for the same key. It
asks how often apps ship them, how many of them a letter rule would catch (its recall on copies),
and, by hand, how many copies really are Russian text rather than words that are spelled the same
in both languages (Сервер, Файл ключа).

Prior art (read before writing this). Weblate's "Unchanged translation" check compares a
translation with the source string and, in recent versions, with configured source alternatives,
so a project could set Russian as one. Its "Inconsistent" check works within one language. We
found no count of Ukrainian strings identical to the Russian string in shipped apps, and no
measurement of how many such copies a letter rule catches.

What we have seen. cyrillic-leak's counts above (Ukrainian: 302,844 strings in 756 repositories;
Belarusian: 93,355 in 220), and the MultiVNC file. We have not counted copies in this corpus.

## Data

- Corpus: `hidden-chars/repos.txt` on `main` (the F-Droid source repositories of the census). Its
  SHA-256 is recorded.
- One shallow, sparse clone per repository at its default branch HEAD (`**/res/values*/*.xml`),
  as in cyrillic-leak.
- Folders: every Ukrainian (`uk`) and Belarusian (`be`) folder by cyrillic-leak's rule (for example
  `values-uk`, `values-uk-rUA`, `values-b+be`; not Latin-script folders), each with a file of the
  same name in the sibling `res/values/`. The Russian folder compared with is `values-ru` in the
  same `res/` folder, or, if there is none, the first Russian folder by name.
- **Unit**: as in cyrillic-leak, one translated item (each plural or array item counts) whose key
  is translatable in the source file, whose text is not blank and has a Cyrillic letter.
- **Pair**: a unit whose source string has no Cyrillic letter and whose Russian item for the same
  key and index exists and has a Cyrillic letter. Units whose source string is Cyrillic are counted
  apart and never paired (the app's default language may be Russian).
- **Copy**: a pair whose text, after trimming spaces at both ends, equals the Russian text.
- **Word**: two or more characters of the Cyrillic block (U+0400-U+04FF) in a row. A copy with
  at least two words is **multi-word**. One-word copies are counted and listed but not graded, as
  many words are spelled the same in both languages (Сервер, Телефон).
- A multi-word copy holding any of і, ї, є, ґ, ў is **not Russian** (it is Ukrainian or
  Belarusian text in the Russian file, as in MultiVNC) and is counted apart. The rest are
  **candidates**.
- A candidate is **letter-flagged** if cyrillic-leak's rule finds a letter its language lacks
  that its source string doesn't have: ы, э, ё, ъ for Ukrainian; и, щ, ъ, є, ї for Belarusian.
- Before any repository is read, the job checks that cyrillic-leak's own control passes, and that
  the copy finder gives the expected answer on fixed cases: Выберите файл (copy, flagged ы),
  Настройки сохранены (copy, not flagged in Ukrainian, flagged и in Belarusian), Ключ імпорту
  (not Russian), Сервер (one word), a non-copy and a missing Russian item. It stops otherwise.

## Predictions

Gate: Ukrainian pairs >= 50,000 in >= 100 repositories, else all four are NOT TESTABLE.

- **R1 (copies ship).** At least 20 repositories ship >= 1 Ukrainian candidate. Basis:
  cyrillic-leak found 9 letter-flagged copies, and if the letter rule catches about a third of
  Russian strings, there are several times more copies than that, spread across apps.
- **R2 (the letter rule misses most copies).** Among repositories with at least one Ukrainian
  candidate, the mean over repositories of (letter-flagged candidates / candidates) is below 1/2.
  Needs >= 10 such repositories, else NOT TESTABLE. Weighting each repository once keeps one app
  with a whole copied file from deciding it. Basis: ы, э, ё and ъ together are about 2-3% of
  letters in Russian text (ё is usually written е), so a 20-letter string has roughly a 60%
  chance of holding none.
- **R3 (Belarusian is easier to catch).** The same mean for Belarusian candidates is higher than
  for Ukrainian ones. Needs Belarusian pairs >= 5,000 in >= 20 repositories and >= 10 repositories
  on each side, else NOT TESTABLE. Basis: Belarusian lacks и, one of the most common Russian
  letters, so a letter rule should catch most Russian copies there.
- **R4 (copies are Russian, by hand).** The job writes `sample.csv`: one Ukrainian candidate per
  repository (the one with the lowest SHA-256 of `repo|res_dir|locale_dir|file|key|index`),
  repositories taken in order of the SHA-256 of their URL, up to 40. Each is labelled from its
  text and English source only:
  - `russian`: at least one word is not standard Ukrainian spelling or form (Выберите,
    Настройки, удалось, сохранены), or the phrase is Russian grammar;
  - `both`: every word is standard Ukrainian and the phrase is correct Ukrainian for the source
    (Файл ключа for "Key file"), and it is correct Russian too;
  - `ukrainian`: correct Ukrainian but not correct Russian (Перезаписати ключ): the copy went the
    other way, into the Russian file;
  - `other`: a name, code, a quotation, or can't be judged.

  R4 holds if `russian` labels are at least 3/4 of the sample. Needs >= 4 sampled units, else NOT
  TESTABLE. Basis: a multi-word string identical in both languages is uncommon in real
  translations, but short technical phrases do occur.

R2 reads as the letter rule's recall on Russian copies only if R4 holds. The recall within the
hand-labelled `russian` rows will be reported as a post-hoc number, labelled as such. All
comparisons are made on whole numbers (cross-multiplied) or exact fractions; no rounding decides a
verdict.

## Reported, not predicted

For Ukrainian and Belarusian: repositories, units, units with a Cyrillic source, pairs, copies,
multi-word copies, not-Russian copies (Ukrainian or Belarusian in the Russian file), candidates,
letter-flagged candidates, each with its number of repositories, and the per-repository mean. Every
copy (one-word ones too) is in `copies.csv` (repository, commit, language, folders, file, key,
item, word count, multi-word, not Russian, candidate, letters, first 200 characters of the text and
the source) for audit.

## Limits, stated before the data

- Only exact copies of the app's own Russian string are found. Russian text that differs from the
  Russian file (an older version, a different wording) is missed, so copies are a lower bound on
  Russian text in Ukrainian files, just as letters are.
- Copies that are correct in both languages are not errors; R4 estimates how many there are. The
  hand check is done by AI agents reading the English source, not by native speakers. Labels,
  rules and every sampled line will be published so anyone can re-grade.
- A copy can go either way: Russian text in the Ukrainian file, or Ukrainian text without і, ї, є,
  ґ in the Russian file. The hand check judges the text, so it tells the two apart.
- One snapshot at HEAD on the day the job runs, default branches only. Forks and copies of the
  same app count separately. Strings files in several `res/` folders count once per folder.
