# Pre-registration: invisible characters in shipped Android translations

MV2, Munim, Inc. (mv2@munimtech.com). Written 2026-10-29 (UTC), before any corpus data was
fetched or read. Made with AI agents. Code: `hiddenchar.py` (Apache-2.0), tests:
`test_hiddenchar.py`. Results will be added next to this file, unchanged predictions above them.

## Question

Translated app strings sometimes carry invisible characters that their English source does not
have: zero-width spaces (U+200B), soft hyphens (U+00AD), bidi controls, word joiners and other
Unicode format characters. They come in through copy-paste from machine-translation pages and
editors. They are invisible on screen, but they break search, string comparison and line
wrapping. Weblate already treats one of them specially: its `RemoveZeroSpace` autofix deletes
U+200B from a translation whose source has none (Khmer exempt), and its `zero-width-space` check
flags it. It does nothing like this for the other characters.

1. How common are these characters in shipped open-source Android catalogs?
2. Is Weblate's zero-width-space removal visible in what apps actually ship? If it is, repositories
   translated on Weblate should have fewer extra U+200B, while the characters Weblate does not
   touch (the control classes) should not drop the same way.

## Why this is new

Prior art we checked: Weblate's U+200B check and autofix (docs and `weblate/trans/autofixes/chars.py`);
Open Collective's own clean-up of U+200B and U+00AD in its translation files (opencollective-frontend
PR #12455, merged 2026-09-29; found by Renovate's hidden-Unicode warning) and its new translation
validator (PR #12613, open); general "hidden Unicode" guides; and MV2's own census of crashing Android
format strings (this repository). We found no published count of invisible characters across a
corpus of shipped translation catalogs, and no test of whether a translation platform's autofix
changes what ships.

## Corpus and method

- Every source repository listed in F-Droid's `index-v2.json` (downloaded by the job), normalised
  and de-duplicated. Each one gets a depth-1, blobless, sparse clone of `**/res/values*/*.xml` at the
  default branch's latest commit (the commit is recorded per repository).
- A unit is one translated text: a `<string>`, or one `<item>` of a `<plurals>` or `<string-array>`,
  in a `values-<lang>` folder whose key exists, translatable and non-empty, in the sibling `values`
  folder. Android `\uXXXX` escapes and XML character references are decoded first. Strings marked
  `translatable="false"` and pseudo-locales (en-XA, ar-XB) are excluded.
- An extra character is a code point of one of these classes that appears in the unit and not in its
  source (for arrays, the item at the same index; otherwise all of the key's source texts):
  `zwsp` U+200B; `shy` U+00AD; `joiner` U+200C/U+200D; `mark` U+200E/U+200F/U+061C;
  `bidi` U+202A-U+202E and U+2066-U+2069; `wj-bom` U+2060/U+FEFF; `other-cf` any other Unicode
  format (Cf) character except Arabic number signs and emoji tag characters.
- A primary unit is a unit with at least one unexpected extra character: `zwsp` except in th, lo,
  my, km, bo, dz (scripts that use U+200B between words); `mark` except in right-to-left languages;
  `shy`, `bidi`, `wj-bom` and `other-cf` always. `joiner` is never primary (ZWNJ/ZWJ are required in
  Persian and many Indic scripts).
- The control classes are `shy`, `bidi`, `wj-bom`, `other-cf`, and `mark` outside right-to-left languages.
- Platform: a second, treeless clone of the repository's history. "weblate" if any commit's committer
  or author mentions Weblate or its subject contains "using Weblate"; otherwise "crowdin" if a commit
  is by Crowdin or titled "New translations ... (...)"; otherwise "transifex"; otherwise "other".
  Non-Weblate = crowdin + transifex + other. Repositories whose history could not be fetched are "unknown"
  and are left out of P2.
- Rates are pooled: hits divided by units over all repositories of a group.

## Predictions (fixed before any data was read)

- **P1.** At least 3% of repositories that ship at least one translated unit have at least one
  primary unit.
- **P2 (main).** Let rz = (extra-`zwsp` rate in Weblate repositories) / (the same rate in non-Weblate
  repositories), counted only outside th/lo/my/km/bo/dz, and rc = the same ratio for units with a
  control-class extra. P2 holds if rz < 0.5 and rz < rc.
- **P3.** At least 80% of units with an extra `mark` character are in right-to-left languages.
- **P4.** Among primary units, `zwsp` (outside th/lo/my/km/bo/dz) is the most common class: more
  units than each of `shy`, `bidi`, `wj-bom`, `other-cf` and non-RTL `mark`.

A prediction with a zero denominator is NOT TESTABLE. Verdicts are computed by `aggregate()` in
`hiddenchar.py` and will be reported as HELD / FAILED / NOT TESTABLE without edits.

Reported but not predicted: repository-level shares, per-language counts (`by_lang.csv`), the P2 ratio
recomputed without the single repository contributing the most `zwsp` hits in each group, and every
primary unit with its source and target text (`hits.csv`, invisible characters shown as `<U+XXXX>`,
at most 500 per repository).

## What was read before writing this

Weblate's checks documentation and `chars.py` autofix source, Weblate's example `AUTOFIX_LIST`,
Open Collective PRs #12455 and #12613 (summaries), and search results on hidden Unicode in
localization. No F-Droid repository, catalog or count was opened for this study.

## Limits, stated now

- This is observational. Weblate repositories may differ in other ways (more volunteers, more
  languages). The control classes are there to separate the autofix from "Weblate projects are just
  cleaner"; they cannot rule out everything.
- Platform is per repository, not per string: strings imported before a project joined Weblate count
  as Weblate strings.
- An extra invisible character is not always a visible bug. This study counts characters; it does not
  test how each app renders them. No native speaker checks the hits.
- The corpus is the latest commit of each default branch on the day the job runs; it is not pinned.
- The job has a time budget; repositories not reached in time are listed and not counted.

Licence: code Apache-2.0; data and text CC BY 4.0; quoted translations stay under their projects' licences.
