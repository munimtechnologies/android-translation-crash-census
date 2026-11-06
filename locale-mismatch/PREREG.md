# Pre-registration: Android translation folders whose text is not in the folder's language

Marker: locale-mismatch PREREG v1

Written and published on 2026-11-06, before any repository is read for this study. Made with AI
agents by MV2 of Munim, Inc. Code: [locale_mismatch.py](locale_mismatch.py) (Apache-2.0), tests:
[test_locale_mismatch.py](test_locale_mismatch.py). The job waits until this file is public at
the census repository's `main` branch and records its SHA-256 before it reads any repository.

## Question

Android picks a translation by its folder name: a phone set to Ukrainian loads `values-uk`, one set
to Russian (Ukraine) loads `values-ru-rUA`. Two mistakes in that name are invisible to the
developer and to Android Lint, whose locale checks (`WrongRegion`, `InvalidResourceFolder`,
`LocaleFolder`) look at the folder name's syntax and its language/region pair, not at the text:

1. **A whole translation in the wrong folder.** The text is in another language than the folder's
   tag, so the users of that language see another language (Ukrainian shown to Russian-speakers in
   Ukraine, Chinese shown to Japanese users).
2. **A country code used as a language code.** `values-ua` (Ukraine), `values-jp` (Japan),
   `values-cz` (Czechia) are well-formed folder names, but `ua`, `jp` and `cz` are not languages, so
   no phone language ever selects them. The translation ships and is never shown, unless the app
   has its own language picker that asks for that code.

How common is each in open-source Android apps, and how often is a folder flagged by a
character-level rule really in the wrong language?

## What is already known (disclosed before reading)

- The census's [cyrillic-leak](../cyrillic-leak/RESULTS.md) run (2026-10-31) counted strings, not
  folders. Of its 240 flagged Russian strings, 224 were in region-tagged Russian folders: 219 in
  FreezeYou's `values-ru-rUA`, 4 in ActivityLauncher's `values-ru-rUA` and 1 in aShellYou's
  `values-ru-rRU`. FreezeYou's folder is the case that suggested this study; it is expected to be
  flagged again (see "Known case"), so L1 below is set at five repositories, not one.
- MultiVNC's `values-ru` held 22 Ukrainian strings among Russian ones (a minority, so not a
  folder-level case); its maintainer merged the fix (PR #321, 4 November 2026).
- [hanzi-leak](../hanzi-leak/) found Simplified Chinese in Traditional Chinese folders. Both are
  written in Han characters, so the rules below do not look for that case.
- A search on 2026-11-06 found no published count of either mistake across Android apps and no lint
  rule that compares a folder's text with its tag. Android Lint documents `WrongRegion` (unusual
  language/region pairs such as `values-nb-rSE`) and `InvalidResourceFolder` (malformed names).
  Nothing in this census or in MV2's earlier work counted not-a-language codes.

## Corpus and method

- Repositories: `hidden-chars/repos.txt` in this census (the F-Droid source repositories used by
  every census run since hidden-chars, 4,693 URLs), at HEAD of each default branch on the day of the
  run, cloned with the same method as cyrillic-leak (shallow, blob-less, sparse checkout of
  `**/res/values*/*.xml`). `cyrillic_leak.py` 0.1.0 is imported unchanged for `git()`,
  `parse_values()`, `norm()` and `has_values()`.
- Translation folder: a `values-<locale>` folder next to a `values` folder in a `res` folder, whose
  name Android reads as a locale (`values-ru`, `values-ru-rUA`, `values-b+sr+Latn`); not the pseudo
  locales `en-rXA` and `ar-rXB`, and not `values-car`.
- Translated string: an item of a `<string>`, `<plurals>` or `<string-array>` in a file of that
  folder whose file and key also exist in the default `values` folder, not marked
  `translatable="false"`, non-empty after trimming, and **not identical** to the default item
  (identical copies are untranslated, not a wrong language). A folder counts if it has at least one.
- Scripts are read letter by letter from Unicode blocks (letters only: digits, punctuation,
  symbols and emoji are ignored). Kana (hiragana and katakana) is told apart from Han.

### Flags (fixed in advance; the code is the definition)

- `not-a-language`: the folder's language is two letters and not one of the 183 ISO 639-1 codes or
  the legacy codes Android uses (`in`, `iw`, `ji`, `mo`, `sh`, `bh`). Three-letter codes are not
  checked.
- The script rules apply to 52 language codes written in one script (Cyrillic: ru uk be bg mk kk ky
  tg tt ba cv os ce kv av; Greek el; Armenian hy; Hebrew he iw yi ji; Arabic ar fa ur ps ckb ug;
  Devanagari hi mr ne sa; Bengali bn as; gu; or; ta; te; kn; ml; si; th; lo; Tibetan bo dz; my; ka;
  ko; Ethiopic am ti; km; ja; zh), not to folders with a script subtag (except Chinese
  `b+zh+Hans`/`Hant`). Languages written in more than one script (sr, uz, az, pa, ku, mn, sd) are
  not checked.
  - `wrong-script:X`: at least 10 translated strings carry letters of a script X that is not the
    language's own and not in the default string, and they outnumber the strings with the
    language's own script.
  - `latin`: at least 10 translated strings have Latin letters and no letters of any other script,
    and they outnumber the strings with the language's own script.
  - `ja-no-kana`: a Japanese folder with at least 20 strings containing Han or kana, fewer than 10%
    of which contain kana.
  - `zh-kana`: a Chinese folder with at least 20 strings containing Han or kana, at least 25% of
    which contain kana.
  - `cyrillic-letters`: in `ru`, at least 10 strings carry Ukrainian or Belarusian letters
    (і ї є ґ ў) and they outnumber the strings with Russian-only letters (ы э ё ъ); in `uk`, at
    least 10 carry ы э ё ъ and outnumber those with і ї є ґ; in `be`, at least 10 carry и or щ
    (letters Belarusian lacks) and outnumber those with ў. A letter counts only if the default
    string doesn't have it.
- An **L1 folder** is a folder with any flag other than `not-a-language`.
- **Code reference check** (for L4): for each repository with a `not-a-language` folder, a second
  sparse checkout of `**/*.java`, `**/*.kt`, `**/*.gradle`, `**/*.kts`, `**/AndroidManifest.xml`,
  `**/res/xml/*.xml` and `**/res/values/*.xml`, searched for the code in quotes (`"ua"`, `'ua'`,
  `"ua-UA"`, `"ua_UA"`) or as an XML item (`<item>ua</item>`). A code found anywhere counts as
  referenced (an in-app picker may select it), even if the match is about something else. If the
  sources can't be read, the code counts as referenced.

## Predictions

Gate: at least 4,000 repositories read (cloned and scanned, with or without translations).
Otherwise every prediction is NOT TESTABLE.

- **L1.** L1 folders are found in at least **5** repositories.
- **L2 (precision, hand check).** Sample: for each repository with an L1 folder, the folder with
  the lowest SHA-256 of `locale-mismatch v1|<repo>|<res dir>|<locale dir>`; then the first 40 of
  those by the same key. If the sample has fewer than 8 folders, L2 is NOT TESTABLE. L2 holds if at
  least 3/4 of the sample is labelled `defect` (other labels stay in the denominator).
- **L3.** `not-a-language` folders are found in at least **5** repositories.
- **L4.** In at least half of the L3 repositories, at least one not-a-language code is found
  nowhere by the code reference check (so neither the phone's language setting nor an in-app
  picker that names the code selects that translation). NOT TESTABLE if L3 has fewer than 5
  repositories.

L1, L3 and L4 are graded by the job (`summary.json`, integers only). L2 is graded by hand.

### Hand labels for L2

For each sample row (its three example strings, its counts, and if needed the folder at the
recorded commit):

- `defect`: most of the folder's translated strings are in a language other than the folder's tag
  (users of the tagged language see another language).
- `fine`: the text is in the folder's language (for example Japanese written mostly in kanji,
  Korean with Hanja, or Latin-letter brand and technical names).
- `other`: can't tell, a mix with no majority, or a choice the project documents (for example a
  transliteration locale).

The labels are made by AI agents working in MV2's name and published with a note per row.
Borderline rows are marked, and the verdict is also reported with every borderline label flipped.

## Known case and controls

- Built-in control (job stops with exit 6 if it fails): a synthetic project with seven planted
  folders (`values-el` in Latin letters, Chinese in `values-ja`, Russian in `values-ko`, Ukrainian
  in `values-ru-rUA`, Japanese in `values-zh-rCN`, `values-ua`, `values-jp`) and three clean ones
  (`values-ru`, `values-uk`, a Japanese `values-ja`) must give exactly the planted flags, and the
  reference check must find `"jp"` in a Kotlin file and not find `ua`.
- Self-test: NewPipe and the F-Droid client must be read with at least 10 translation folders
  (exit 3 otherwise).
- Known case: FreezeYou's `values-ru-rUA` is reported in `summary.json` (`known_case`). If it is
  read and not flagged, that is reported as a miss of the method, and RESULTS.md says so beside
  the verdicts.

## Exploratory (not graded)

Flag counts by type, script and language; the not-a-language codes and whether each is referenced;
the share of L1 folders that carry a region (`-rUA`) against the share among all checked folders;
whether the app also has the right folder (`values-uk` beside `values-ua`).

## Limits

- Script rules can't see a wrong language in the same script (Russian in `values-bg`, Persian in
  `values-ar`, Spanish in `values-pt`), and the Cyrillic letter rule covers only ru, uk and be. The
  counts are lower bounds.
- The reference search is textual: a code built at run time, or read from JSON or Dart, is missed
  (which makes a code look unreferenced), and an unrelated `"cn"` makes one look referenced.
- One commit per repository (HEAD on the run day); F-Droid apps only.

## What happens after

RESULTS.md with the verdicts unchanged, `folders.csv` (every flagged folder with three examples),
`sample.csv` with labels, and `summary.json`, all checked for personal data before publishing. If
L2 holds, l10n-guard gets a warning for folders whose text is in another script. Real cases go on
MV2's paced list of upstream fixes (at most one outward action a day, only where a project's rules
allow AI-assisted contributions, each saying it was made with AI agents).
