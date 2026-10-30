# The doubled zero-width space in shipped Android translations

**Exploratory follow-up, NOT pre-registered.** Rough counts of this pattern were seen
first (with a text search on `hits.csv`, 2026-10-30), and the script was then written to
count it properly. Read the numbers as a description of the census data, not as a tested
prediction.

Part of MV2's [hidden-chars census](../RESULTS.md) (4,693 F-Droid source repos, 2,392 with
translations, 14.37 million translated units). Made with AI agents working for MV2 of
Munim, Inc. Code Apache-2.0; text and data CC BY 4.0.

## Question

The census found 703 translated strings whose only stray invisible character is the zero-width
space U+200B (the source string has none). How are those zero-width spaces arranged?

One public report describes a specific shape. In a 2017 thread on the google-translate-api
Google Group, a developer showed Translate API output with **an ordinary space followed by
two U+200B before a word** ("il <U+200B><U+200B>rilascio"), and asked whether that was a
flaw. The thread shows no answer from Google on the cause:
https://groups.google.com/g/google-translate-api/c/k7A12V7u0e4 . In September 2026 a
pingcap/docs issue counted 45 doubled U+200B in English docs and, separately, called the
same characters in its Japanese branch "MT artifacts" (no engine named):
https://github.com/pingcap/docs/issues/23792 . We found no count of this shape in app
translations.

## Method

`zwsp_signature.py` reads the published `hidden-chars/hits.csv`
(sha256 `45476a3d815f2c06dc33c0cafeeb1b16f0ccb54a12355d3bf12c902acd017554`), keeps rows whose
only class is `zwsp` and whose only code point is U+200B, finds every run of U+200B in the
target, and gives each row one kind, taking the first that applies:

| kind | meaning |
|---|---|
| `pair-after-space` | a run of exactly two U+200B, after an ordinary space and before a letter (the "signature") |
| `pair-other` | a run of exactly two U+200B anywhere else |
| `longer` | a run of three or more |
| `single` | a lone U+200B |
| `none` | no U+200B left in the stored text (the census stores targets cut at about 200 characters) |

It ran in a sealed container (job `zwsp-signature-v1`, 2026-10-30, 6 unit tests passed first).

## Results

| kind | rows | share |
|---|---:|---:|
| pair-after-space (signature) | 487 | 69.3% |
| pair-other | 97 | 13.8% |
| single | 59 | 8.4% |
| longer | 22 | 3.1% |
| none (cut off) | 38 | 5.4% |
| **total** | **703** | |

- **Seven in ten** of these stray zero-width spaces are the exact shape from the Translate API
  report: space, two U+200B, then a word. Doubled runs of any kind are 83.1% (584 of 703);
  a lone U+200B is only 8.4%.
- **Widespread, not one project.** The signature appears in 122 of the 163 repos with
  U+200B-only rows and in 56 language codes. The largest repo holds 41 rows (8.4%) and the
  top five hold 117 (24.0%). Most rows: ru 62, nl 51, tr 27, then vi, pt and ga with 25 each.
- **Every translation route shows it** (share of each platform's U+200B-only rows):
  Transifex 58 of 74 (78.4%), Weblate 70 of 90 (77.8%), Crowdin 101 of 136 (74.3%),
  no detected platform 258 of 403 (64.0%).
- **The same key, many languages.** Seven keys carry the signature in three or more
  languages of one app (`shared_keys.csv`). The largest: ActivityDiary's `setting_tag_yes`
  in 14 languages and `setting_tag_no` in 11, and Nightdream's `background_exif_summary` in 7.

### Post hoc: the word before the pair is often "EXIF"

Found while reading `shared_keys.csv`, after the job ran; counted with a text search on
`hits.csv`, not by the script.

- In **41** of the 703 U+200B-only rows, the zero-width spaces come right after "EXIF "
  (40 with exactly two, 1 Vietnamese row with four). They are in **6 apps** (ActivityDiary,
  Nightdream, Kompact, Wikimedia Commons, SD Maid SE, Twig) and **23 language codes**.
- 43 of the 703 rows mention EXIF at all, so in 41 of those 43 the pair follows it directly.
- Of the 43 rows where the pair follows a short all-capital abbreviation, 41 are "EXIF";
  the others are "2FA" and "QR".

Example (ActivityDiary, Italian, English "Write current activity into EXIF tag UserComment
of new images"): "Scrivi l'attività corrente nel tag EXIF <U+200B><U+200B>UserComment ...".

We can't tell from this data how often "EXIF" is translated *without* the pair: `hits.csv`
only holds strings with a hidden character. A check over every census translation whose
English source contains "EXIF" is the natural next step.

## What it means for maintainers

The stray zero-width spaces in shipped Android translations mostly have one shape, and that
shape matches the one reported in machine-translation output. They are invisible on screen
but break search, string comparison and line wrapping. They are safe to remove, apart from
scripts that use U+200B on purpose (Thai, Lao, Khmer, Myanmar, Tibetan).
[l10n-guard](https://github.com/munimtechnologies/l10n-guard) 0.15.0 and later flags them
in CI (`invisible-char` warning) and skips those scripts.

## Limits

- Not pre-registered (see top). Observational.
- **Not proof of origin.** The shape matches one public Translate API report. It does not
  show that any given string came from Google Translate or any other tool.
- `hits.csv` keeps at most 500 rows per repo and cuts targets at about 200 characters
  (hence the 38 `none` rows).
- Rows are counted, not distinct strings. Android `iw` and `he` are separate codes here.
- Repos are F-Droid source repos at the census snapshot. Some strings may have been fixed
  since.

## Files

- `zwsp_signature.py`: the script (Python standard library only). `test_zwsp_signature.py`: its tests.
- `summary.json`: all counts, top repos and languages, shared keys, 40 example rows.
- `by_repo.csv`, `by_lang.csv`, `shared_keys.csv`: per-repo, per-language and shared-key counts.

Reproduce: `python zwsp_signature.py --out-dir out` (downloads `hits.csv` from this repo).

MV2, Munim, Inc., mv2@munimtech.com
