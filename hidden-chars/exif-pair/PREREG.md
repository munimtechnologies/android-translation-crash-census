# Pre-registration: the doubled zero-width space after "EXIF"

<!-- exif-pair PREREG v1 -->

MV2, Munim, Inc. (mv2@munimtech.com). Written 2026-10-30 (UTC), before the job below reads any
repository. Made with AI agents. Code: `exif_pair.py` (Apache-2.0), tests: `test_exif_pair.py`.
Results will be added next to this file, with the predictions above them unchanged. The job
checks that this file is public before it reads anything.

## Question

MV2's [zwsp-signature](../zwsp-signature/ZWSP-SIGNATURE.md) follow-up found that most stray
zero-width spaces (U+200B) in shipped Android translations have one shape: an ordinary space,
then exactly two U+200B, then a word. The same shape was reported in Google Translate API output
in 2017. Post hoc, it noticed the pair often comes right after the abbreviation "EXIF".

That count only saw strings that *had* a hidden character, so it cannot say how often "EXIF" is
translated *without* the pair, or whether "EXIF" is special at all. This study measures both:

1. Of all translated strings whose English source has "EXIF" followed by a space and a word, what
   share carry the pair right after "EXIF "?
2. Is that share higher than for every other all-capital word in the same position ("GPS data",
   "URL now", "PDF file")?

## What was seen before writing this

Known, from a text search of the published `hidden-chars/hits.csv` (post hoc, labelled as such in
ZWSP-SIGNATURE.md): 41 rows have U+200B right after "EXIF " (40 with exactly two, 1 Vietnamese
row with four), in 6 apps and 23 language codes; 43 of the 703 U+200B-only rows mention EXIF;
where the pair follows a short all-capital abbreviation, 41 of 43 rows are "EXIF" and the others
are "2FA" and "QR". So the numerator for EXIF is roughly known. **No denominator was seen**: no
count of how many translated strings mention EXIF or any other capital word, for any app or language.

## Prior art

Searched 2026-10-30: the 2017 google-translate-api Google Group thread (k7A12V7u0e4, doubled
U+200B in Italian output), pingcap/docs#23792 (doubled U+200B called "MT artifacts", no engine
named), Weblate's zero-width-space check and autofix, and a web search for EXIF together with
zero-width space and machine translation. The only hit linking them is MV2's own Nightdream report
(firebirdberlin/nightdream#389, filed 2026-10-30). We found no measurement of how often the pair
follows a given word, in any corpus.

## Corpus and method

- Repositories: the 4,693 URLs in the census's published `hidden-chars/repos.txt` (the job
  downloads it and records its sha256). Each gets the same depth-1, blobless, sparse clone of
  `**/res/values*/*.xml` at the default branch's latest commit as `hiddenchar.py` 0.1.0.
- Units: exactly as in `hiddenchar.py` 0.1.0 (its parsing code is copied unchanged): a `<string>`, or
  one `<item>` of a `<plurals>` or `<string-array>`, in a `values-<lang>` folder whose key exists,
  translatable and non-empty, in the sibling `values` folder; Android `\uXXXX` escapes decoded;
  pseudo-locales excluded. Languages th, lo, my, km, bo, dz (which use U+200B between words) are
  left out entirely. Units whose source already has U+200B are not scored.
- Capital word: an all-capital run of 2-5 ASCII letters, not preceded by a letter or digit, followed
  by one space and a letter (`(?<![A-Za-z0-9])([A-Z]{2,5})(?= [^\W\d_])`). A unit is a *T-unit* for
  each distinct capital word T in its source.
- Signature after T: the translation contains T (same case, not preceded by a letter or digit), one
  space, exactly two U+200B, then a letter.
- EXIF rate = EXIF-units with the signature after EXIF / EXIF-units.
- Control rate = units with at least one capital word other than EXIF that have the signature after
  any of those words / units with at least one capital word other than EXIF. Pooled over all
  repositories.
- Named controls: GPS, PDF, URL, VPN, QR, API, HTTP, HTTPS, USB, SD, PIN, NFC, SMS, JSON, CSV, HTML.

## Gate

The self-test must find translations in F-Droid's client or NewPipe, and at least 2,000 repositories
must yield at least one unit. Otherwise every prediction is NOT TESTABLE (gate). P1, P2, P4 and P5
are NOT TESTABLE if there are fewer than 100 EXIF-units.

## Predictions (fixed before any denominator was seen)

- **P1.** The EXIF rate is at least 1%.
- **P2 (main).** The EXIF rate is at least 20 times the control rate (and above zero).
- **P3.** Every named control with at least 200 units has a signature rate below 0.2%.
- **P4.** In the repositories with at least one EXIF signature, fewer than half of their EXIF-units
  (pooled) carry it: the pair is not in every translation of "EXIF" even in the apps that have it.
- **P5.** Among languages with at least 30 EXIF-units, at least half have one or more EXIF
  signatures.

Verdicts are computed by `grade()` in `exif_pair.py` and will be reported as HELD / FAILED /
NOT TESTABLE without edits.

Reported but not predicted (exploratory): the same rate for mixed-case "Exif"; the word after
"EXIF" in signature and non-signature sources; any-U+200B and pair-anywhere counts; a table of
every capital word's units and signatures (`words.csv`); every EXIF and Exif unit with its source and
target (`exif_units.csv`, U+200B shown as `<U+200B>`).

## Limits, stated now

- Observational. A high EXIF rate says the pair clusters after this word in these catalogs; it does
  not show which tool put it there.
- Repositories are read at their latest commit on the day the job runs, not at the census
  snapshot. Some strings may have been fixed since (Nightdream#389 was filed the same day).
- One app with many languages can carry a large share of EXIF-units; per-repository counts are
  published so this can be checked.
- No native speaker checks the units. The job has a time budget; repositories not reached in time
  are counted and listed as not started.

Licence: code Apache-2.0; text and data CC BY 4.0; quoted translations stay under their projects'
licences.
