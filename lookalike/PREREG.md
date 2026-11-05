# Pre-registration: look-alike letters inside markup tags and format specifiers of Android translations

lookalike PREREG v1. Written 2026-11-05 by AI agents working for MV2 of Munim, Inc., and published
before the job reads any repository. Nobody working on this study has run the finder on any
repository. Code: Apache-2.0. Text and data: CC BY 4.0.

## Why

While fixing MultiVNC's Russian translation (PR
[#321](https://github.com/bk138/multivnc/pull/321), merged 4 November 2026), we noticed that its
`changelog_dialog_text` closes a link with `</а>`, where the `а` is the Cyrillic letter U+0430.
To an HTML parser that is not `</a>`, so the link is never closed. The same slip inside a format
specifier is worse: `%1$ѕ` with a Cyrillic `ѕ` (U+0455) is not `%1$s`, and Java's
`String.format` throws `UnknownFormatConversionException` on it, so the app crashes when it shows
that string.

Generic checks can notice the symptom. Weblate's and Crowdin's format checks and Android Lint's
`StringFormatInvalid` compare specifiers between source and translation, and our own l10n-guard
compares tags. But they report "missing `%1$s`" or "tag mismatch", not the cause, and we found
no Android Lint check for the HTML inside CDATA strings. A search on 5 November 2026 found general advice on
Unicode confusables in localization (keys, variable names) and generic homoglyph detectors, but
no count of look-alike letters inside the markup and format syntax of shipped translations.

What is new: a pre-registered census of this defect class, markup tags included and not only
strings that crash, across the 4,693 F-Droid source repositories of the census, with the alphabet
of each look-alike letter and a hand check.

## What is already known (stated so it can't shape the predictions unseen)

- One case: MultiVNC's `values-ru` `</а>` above (seen 4 November 2026). A one-character fix may be
  offered to MultiVNC around the time this job runs; if it is merged first, MultiVNC is not counted.
- The census itself (README, "Mistake types") found the format side among its crashing rows:
  26 reachable crashes in 6 repositories have the conversion letter in another script, and 14 of
  them look like or transliterate the Latin letter (Russian `%1$с` for `%1$s`, Greek `%1$δδ`,
  Arabic `%1$دم`). Only the Cyrillic and fullwidth cases of that kind fall under this study's
  table (Greek δ and Arabic د don't look like a Latin letter). This was known when K3 was written.
- The census's `lookalike-percent` and `lookalike-brace` studies cover look-alike delimiters
  (`٪`, `％`, `｛0｝`), not letters. The hidden-chars, cyrillic-leak and hanzi-leak studies did not
  look for look-alike letters in tags or specifiers, and nobody has searched their outputs for it.

## Method (fixed)

- **Corpus and reading.** The repositories of `hidden-chars/repos.txt`, cloned at HEAD with the
  published `cyrillic-leak/cyrillic_leak.py` 0.1.0 method (sparse checkout of
  `**/res/values*/*.xml`). Every `.xml` file in every translation folder of every `res/` folder
  that has a `values/` folder. A translation folder is `values-xx`, `values-xxx` (with or without
  more qualifiers such as `-rTW`) or `values-b+...`; `values/` and qualifier-only folders
  (`values-night`, `values-v21`, `values-car`, ...) are not read. The raw file text is scanned, so
  markup inside CDATA and escaped markup (`&lt;/а&gt;`) are both seen.
- **Look-alike letters.** The fixed table in `lookalike.py` (`CONFUSABLE`): 30 Cyrillic letters
  (such as а е о р с у х ѕ і ј, А В Е К М Н О Р С Т Х), 18 Greek letters (such as ο ν ι α, Α Β Ε Ο
  Ρ), and the 52 fullwidth Latin letters, each mapped to the Latin letter it looks like.
- **Tag hit.** `<` or `&lt;`, an optional `/`, then a name of 1 to 12 characters followed by
  whitespace, `>`, `/` or `&gt;`, where the name has at least one non-ASCII letter, and swapping
  its look-alike letters for Latin ones gives, in lower case, one of: a b i u p s q br em tt li ul
  ol big small font strong sup sub strike span div del ins code pre h1-h6 annotation xliff:g.
- **Format hit.** `%` not preceded by `%`, an optional `n$`, flags from `-#+0,(` (no space), a
  width, a precision, then one character that is a look-alike of one of the Java conversions
  s S d f x X c C o e E g G a A b B h H. Without `n$`, the character after it must not be a letter
  (so `100%сегодня` is text, not a specifier).
- **Recorded per hit:** string key, look-alike letters and code points, alphabet, context, and
  whether the default string of the same key has the same token in plain ASCII (`source_has`).
- **Control,** before any repository is read: 12 fixed strings must give exactly the listed hits
  (`control()` in `lookalike.py`), including `</а>`, `&lt;/а&gt;`, `<і>…</і>`, `%1$ѕ`, `%ｓ` (hits)
  and `&lt;b&gt;`, `&lt;имя&gt;`, `50% с картой`, `50%%с`, `100%сегодня` (no hits).
- **Gate:** at least 4,000 repositories read (cloned and scanned, with or without translations).

## Predictions

Counted per repository: a repository "has a hit" if any of its translation files has one.

| | Prediction | Rule |
|---|---|---|
| K1 | the defect is not a one-off | at least 10 repositories have a hit |
| K2 | it is mostly a Cyrillic problem | in more than half of the repositories with a hit, some hit's look-alike letter is Cyrillic |
| K3 | tags are hit more often than format specifiers | repositories with a tag hit > repositories with a format hit |
| K4 | the hits are real defects | hand check of the sample: `defect` >= 3/4 of rows (needs >= 8 rows) |

K1-K3 are graded by the job. If there are no hits, K2 and K3 are not testable.

## K4 sample and labels

- **Sample:** one hit per repository, the one with the lowest SHA-256 of
  `lookalike v1|repo|res folder|locale folder|file|key|index`; repositories in order of SHA-256 of
  `lookalike v1|repo`; the first 40 (all of them if fewer).
- **Labels,** one per row with a note, from the context, the code points and the source string:
  `defect` if the token stands where the source string has the same tag or specifier in ASCII (or
  plainly means it), so the markup or formatting breaks; `fine` if the token is meant as text
  (for example a placeholder hint like `&lt;Р&gt;` in the source too, or a word after a literal
  `%`); `other` if it can't be judged. Borderline calls are marked, and the verdict is checked
  with them flipped (reported, not used to grade).
- The labels are made by AI agents, not by native speakers; every label and note is published.

## What follows from the results

- Every hit judged a defect is a candidate for a small upstream fix, offered at most one a day and
  only where the project accepts such changes and no translation platform owns the file
  (otherwise a report to the platform's project).
- If K4 holds, l10n-guard gets a `lookalike` rule that names the cause ("Cyrillic а in `</а>`")
  instead of a generic mismatch.
- Every outcome is published, including failures and anything not testable.

## Files

`lookalike.py` 0.1.0 and `test_lookalike.py` in this folder. The job writes `summary.json`
(counts, verdicts, every SHA-256), `sample.csv`, `hits.csv` and `repos.jsonl`.

Made by MV2 of Munim, Inc. with AI agents. Contact: mv2@munimtech.com.
