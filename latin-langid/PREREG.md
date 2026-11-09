# Pre-registration: Android translation folders that hold another language in the same alphabet

Marker: latin-langid census PREREG v1
Written 2026-11-09 by AI agents working for MV2 of Munim, Inc. (mv2@munimtech.com), before any
repository in the population is read by this code. Code: `latin_langid.py`, tests:
`test_latin_langid.py` (same folder, same commit). Licence: Apache-2.0 (code), CC BY 4.0 (text
and data).

## Question

An Android app keeps each translation in a `values-<language>` folder, and the phone shows the
folder that matches the user's language. If the folder holds a *different* language, users get
that language instead. The earlier `locale-mismatch/` census in this repository found such
folders by **script** (Cyrillic text in `values-ko`), so it could not see a wrong language in the
same alphabet. By hand it found three in one Thunderbird module: Hungarian in `values-ast`,
Italian in `values-az` and Turkish in `values-br` (thunderbird-android issue #11893). All three
were still there at `main` on 2026-11-09.

This census asks how common such same-alphabet misplacements are across F-Droid apps, using a
language identifier that is built from the corpus itself, so no outside model or data is needed.

**Prior art we checked.** Weblate's checks (docs 2026.11) include "unchanged translation",
character-set checks for a few languages and LLM-based fluency checks, but no language
identification of a translation file. Android Lint has none. Language identification by character
n-gram profiles is old (Cavnar & Trenkle 1994, "N-Gram-Based Text Categorization"). We found no
census that applies it to app translation folders, and no published rate.

## Population

Every repository in `hidden-chars/repos.txt` of this repository (the F-Droid source repositories
used by the earlier censuses, 4,693 lines), each read once at its default branch's HEAD with the
same sparse clone as `locale_mismatch.py` 0.1.0 (`**/res/values*/*.xml`). Its helpers and those of
`cyrillic_leak.py` 0.1.0 are imported unchanged; the job prints both files' SHA-256.

## Definitions (as coded)

- **Translated string:** a string, plural item or array item in a `values-*` folder whose key also
  exists in the same file of `values/`, and whose text is not identical to the source item.
- **Language key:** the folder's language code with `in`→`id`, `iw`→`he`, `ji`→`yi`, `no`→`nb`,
  `mo`→`ro`, plus the script subtag if one is given (`values-b+sr+Latn` → `sr-Latn`); regions
  are dropped. Codes that are not ISO 639-1 languages (`values-ua`) are left out (covered by
  `locale-mismatch`), and so are languages with their own script in `locale_mismatch.EXPECT`.
- **Checked folder:** at least 10 translated strings and at least 100 letters, at least half of
  them Latin. Text is lowercased and NFC-normalised after format placeholders, `{...}`, markup,
  entities, URLs and backslash escapes are removed; up to 40,000 letters per folder are used.
- **Profiles:** each folder's 1- to 3-gram counts of its words (padded `_word_`). Each checked
  folder's relative frequencies are averaged per repository and language key, then summed over
  repositories, so each repository counts once per language. Each repository's source
  strings (the `values/` items that have at least one translated string) are added under `en`
  as one more folder, if it passes the same size and Latin rules. A language gets a profile if at least 30 repositories
  contribute; the profile is its top 400 n-grams.
- **Distance:** a folder's top 300 n-grams against a profile, by the Cavnar-Trenkle out-of-place
  sum (missing n-gram = 400); normalised distance = sum / (n-grams × 400).
- **Related languages** are never flagged for each other: nb nn da; sr hr bs sh cnr; hr sl;
  id ms; cs sk; es gl ast an; gl pt; ca oc; nl af fy li; de lb gsw; fil tl; ga gd; tr az;
  it co sc; pl szl csb; fr wa; lv ltg; en sco.
- **Holds:** the closest profile that is not related to the folder's language.
- **Flagged:** (a) the normalised distance to *holds* is at most the 90th percentile of the
  normalised distances of folders labelled with that language (for `en`, the source strings), and
  (b) if the folder's own language or a related one has a profile, the distance to *holds* is at
  most 9/10 of the smallest such distance. A flagged folder is **english** when *holds* is `en`
  (stale English, reported separately) and **other-language** otherwise.
- **Consistent:** among checked folders whose language has a profile, the overall closest
  profile is the folder's own language or a related one.

## Gate

At least 4,000 repositories read and at least 20 profiles. If not, S0-S4 and H1 are NOT
TESTABLE and no rate is claimed.

## Predictions (graded by code, integer arithmetic)

- **S0 (the identifier works).** At least 95% of checked folders whose language has a profile
  are consistent. If S0 fails, S1-S4 are still reported, but no claim is made from them.
- **S1.** Other-language folders are found in at least 5 repositories.
- **S2.** Other-language folders are under 1% of checked folders (100 × flagged < checked).
- **S3 (known cases).** Of the three Thunderbird folders above (module
  `feature/mail/message/list/internal`), at least 2 of those checked are flagged other-language
  with the expected language (hu, it, tr). Testable if at least 2 are checked. These cases were
  known while the method was designed (they are why the minimum is 100 letters, not more), so
  S3 tests that the method works; it is not an out-of-sample result.
- **S4.** In at least half of the other-language folders, the same `res/` folder also has a
  folder for the language it holds (a misfiled copy, as in Thunderbird). Testable with >= 4.

## Hand check (H1, next run, before any claim of precision)

Up to 24 other-language folders, one per repository (lowest SHA-256 of
"latin-langid v1|repo|res_dir|locale_dir"), listed in `sample.csv`. Each is read at the recorded
commit and labelled **real** when at least half of the first 10 translated strings are in a
language other than the folder's own (and not a related one), and the folder is not an
intentional choice the project documents. H1 holds if real × 4 >= 3 × checked, testable with at
least 8 checked. The labels are made by AI agents, not native speakers; borderline calls are
reported with the flips.

## Exploratory (no predictions)

Flagged language pairs; the most common inconsistent pairs; english folders and repositories;
flags for languages with no profile; checked folders and repositories per language; the 90th
percentiles; `profiles.json` (top 400 n-grams of every profile, CC BY 4.0).

## Limits stated now

- A folder is judged as a whole: a few misplaced strings in a large folder are not seen, and
  folders under 10 strings or 100 letters are not checked.
- Related languages are excluded, so Danish in `values-nb` or Spanish in `values-gl` is never
  counted. Every count is a lower bound.
- Profiles come from the same corpus, so a language whose folders often hold another language
  would get a mixed profile; a repository's own folders are part of its language's profile
  (at most 1 in 30), which makes the check more conservative.
- One commit per repository, F-Droid only, `res/values*` XML only.

## What happens next

Results go to `latin-langid/RESULTS.md`, with the job outputs unchanged under
`latin-langid/v1/` and the hand labels in a separate `labels.csv`. If S0 and H1 hold, l10n-guard
gets an offline wrong-language check that ships these profiles, with its own pre-registered
held-out test, and confirmed cases are reported upstream one at a time where each project's rules
allow it, saying the check was made with AI agents.
