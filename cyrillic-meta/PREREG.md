# Pre-registration: letters from another alphabet in Cyrillic app-store listings

cyrillic-meta PREREG v1. Written 2026-11-06 by AI agents working for MV2 of Munim, Inc., and
published before the job reads any repository. Nobody working on this study has run the detector
on any store listing. Code: Apache-2.0. Text and data: CC BY 4.0.

## Why

The census's [cyrillic-leak](../cyrillic-leak/RESULTS.md) study counted Ukrainian, Belarusian and
other Cyrillic Android translations that contain a letter the language's alphabet doesn't have
(Russian ы, э, ё, ъ in Ukrainian; и, щ, ъ in Belarusian; Ukrainian і, ї, є, ґ in Russian). In
Ukrainian, 39 apps ship such strings, and a hand check (made after grading, not pre-registered)
found 44 of 54 Ukrainian and 62 of 63 Belarusian hits to show the user text in the wrong language.

That detector has only been checked on the strings it was built on. The Chinese counterpart was
tested on held-out text, the apps' store listings
([hanzi-meta](../hanzi-meta/RESULTS.md): 32 of 35 flagged lines were real defects), before it went
into l10n-guard. This study does the same for the Cyrillic detector: same letter table, same rule,
new text (the F-Droid / Google Play store listings kept in each repository), and a hand check whose
rule is fixed here. A Russian word in a Ukrainian store description is also the first thing a
Ukrainian user sees of the app, before installing it.

A web search on 6 November 2026 found no count of Russian letters in Ukrainian or Belarusian store
listings; the only count of the class we found is MV2's own string-file study above.

## What is already known

- The string-file results above, including their false flags: keyboard maps, letter lists (an A-Z
  jump bar listing Russian letters) and brand names such as "Электроника".
- Store listings are free text, not UI strings. A Ukrainian description may name the languages the
  app supports ("Русский") or quote Russian text on purpose. Such lines are not defects (see labels).
- Nothing has been read from any listing for this study.

## Method (fixed)

- **Corpus.** The 4,693 repositories of `hidden-chars/repos.txt`, read at HEAD with the published
  `hanzi-meta/hanzi_meta.py` 0.1.0 clone method and listing walker (imported unchanged): sparse
  checkout of `fastlane/metadata/android/*/*.txt` and its `changelogs/`, `play/listings/*/*.txt`,
  `play/release-notes/*/*.txt` and top-level `metadata/*/*.txt` and its `changelogs/`.
- **Listing folders.** A folder whose name starts with `uk`, `be`, `ru`, `bg`, `sr` or `mk`
  (`uk`, `uk-UA`, `be_BY`, `sr-Cyrl`, ...); a name with `Latn` after the language is not read.
- **Unit.** One non-empty line, stripped, that contains a Cyrillic letter (U+0400-U+04FF).
- **Flag.** The letter table and rule of `cyrillic-leak/cyrillic_leak.py` 0.1.0 (imported
  unchanged): a unit is flagged if, after NFC normalisation and lower-casing, it contains a letter
  its language's alphabet lacks that the same file in the English listing (`en-US`, `en-GB` or
  `en`, in that order) does not contain.
- **Control,** before any repository is read: `cyrillic_leak.control()` and a synthetic listing in
  `control()` must give exactly the three planted flags (a Ukrainian line with ы, a Belarusian line
  with и, a Russian title with і), and must not flag a Ukrainian line whose letters the English file
  also has, nor a `sr-Latn` folder.
- **Gate:** at least 4,000 repositories read (cloned, with or without listings). Each prediction
  has its own gate below.

## Predictions

| | Prediction | Rule |
|---|---|---|
| C1 | the detector is precise on text it was never tuned on | hand check of the sample: `defect` >= 3/4 of the rows (needs >= 15 rows) |
| C2 | Ukrainian listings leak too | at least 10 repositories have a flagged Ukrainian line (gate: >= 2,000 Ukrainian lines in >= 50 repositories) |
| C3 | leaks travel together | among repositories with Ukrainian or Belarusian listing lines and string files, those whose uk/be string files had a flagged string in cyrillic-leak have a flagged uk/be listing line more often than the others (each group >= 10 repositories) |
| C4 | Belarusian leaks more than Ukrainian, as in the string files | flagged Belarusian lines / Belarusian lines > flagged Ukrainian lines / Ukrainian lines (gate: >= 300 Belarusian lines in >= 10 repositories, and C2's gate) |

C2-C4 are graded by the job with integer cross-multiplication. C3 reads the string-file counts of
cyrillic-leak (`cyrillic-leak/repos.jsonl`, published with this file, from the 1 November 2026
run); a repository it doesn't list is left out of C3. If a gate isn't met the prediction is "not
testable" and is reported as such.

## C1 sample and labels

- **Sample:** flagged lines of all six languages. Per repository, the flagged line with the lowest
  SHA-256 of `cyrillic-meta v1|repo|path|line`; those lines in order of the same hash; the first 40
  (all of them if fewer).
- **Labels,** one per row with a note, from the line, its letters and the language:
  - `defect`: the user sees text not in the listing's language because of it: a whole line in
    another language, a word or phrase from another language in a real translation, or a word
    misspelt with a letter from the wrong keyboard layout;
  - `fine`: deliberate: a name, brand or title in another language, a list of languages or letters,
    a quotation, or a line meant to be in several languages;
  - `other`: can't be judged.
  `other` counts in the denominator. Borderline calls are marked and the verdict is also reported
  with them flipped (reported, not used to grade).
- The labels are made by AI agents, not by native speakers; every label and note is published.

## What follows from the results

- If C1 holds, l10n-guard gets a `wrong-alphabet` warning for Cyrillic targets (Ukrainian,
  Belarusian, Russian, Bulgarian, Serbian, Macedonian), as hanzi-meta's result led to its
  Traditional Chinese warning. If C1 fails, the warning waits, and the false flags show what it
  would need to skip.
- Lines judged defects are candidates for small upstream fixes, at most one a day, only where the
  project accepts such changes and no translation platform owns the files (otherwise a report to
  the platform's project).
- Every outcome is published, including failures and anything not testable.

## Files

`cyrillic_meta.py` 0.1.0 and `test_cyrillic_meta.py` in this folder. The job downloads
`cyrillic-leak/cyrillic_leak.py`, `hanzi-meta/hanzi_meta.py` and `hanzi-leak/hanzi_leak.py` from
this repository and records their SHA-256. It writes `summary.json` (counts, verdicts, hashes),
`flagged.csv`, `sample.csv` and `repos.jsonl`.

Made by MV2 of Munim, Inc. with AI agents. Contact: mv2@munimtech.com.
