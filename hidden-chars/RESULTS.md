# Results: invisible characters in shipped Android translations

MV2, Munim, Inc. (mv2@munimtech.com). Graded 2026-10-30 (UTC) by AI agents working in his name,
against [PREREG.md](PREREG.md), which was published before the job ran. Made with AI agents; no
human has checked the hits. Code: `hiddenchar.py` 0.1.0 (Apache-2.0). Data in this folder:
`summary.json`, `by_lang.csv`, `hits.csv`, `repos.txt` (CC BY 4.0; quoted translations stay under
their projects' licences).

## Verdicts (computed by `aggregate()`, copied unchanged)

| | Prediction | Verdict |
|---|---|---|
| P1 | >= 3% of repositories with translations have a primary unit | **HELD** (330 of 2,392 = 13.8%) |
| P2 (main) | Weblate's extra-U+200B rate ratio rz < 0.5 and rz < the control ratio rc | **HELD** (rz = 0.25, rc = 1.75) |
| P3 | >= 80% of units with an extra `mark` are in right-to-left languages | **FAILED** (4,522 of 8,364 = 54.1%) |
| P4 | `zwsp` is the most common primary class | **FAILED** (`mark` 3,842 and `bidi` 924 beat `zwsp` 710) |

## The run

- Job `hiddenchar-census-v1`, 2026-10-29 23:59 to 2026-10-30 00:35 UTC (34 minutes, 0.41 GB peak).
  It was filed on 2026-10-29 and waited about 3 hours for compute; the corpus is the default branch
  of each repository on that night.
- F-Droid `index-v2.json` (timestamp 1793277778529): 4,693 distinct source repositories. 2,392 had
  translated units, 2,210 had none, 91 could not be cloned, 0 were left out by the time budget.
- Self-test: F-Droid client (29,487 units) and NewPipe (56,909 units) both read; both labelled Weblate.
- Platforms of the 2,392: Weblate 493, Crowdin 102, Transifex 73, other 1,724.
- 14.37 million translated units: 5.38 million in Weblate repositories, 8.99 million in the rest.

## P2: Weblate's zero-width-space autofix shows in what apps ship

| | Weblate (493 repos) | Not Weblate (1,899 repos) | Ratio W/N |
|---|---|---|---|
| Units with an extra U+200B (outside th/lo/my/km/bo/dz) | 92 of 5,303,773 (17 per million) | 618 of 8,834,037 (70 per million) | **rz = 0.25** |
| Units with an extra control-class character | 2,853 of 5,375,874 (531 per million) | 2,722 of 8,990,116 (303 per million) | **rc = 1.75** |
| Repositories with any extra U+200B | 23 (4.7%) | 140 (7.4%) | |

Weblate repositories ship about a quarter as many stray zero-width spaces as other repositories,
while the characters Weblate does not remove are not rarer there (they are more common). Removing
the single repository with the most zero-width-space hits gives rz = 0.21 (without the top Weblate
repository) and 0.27 (without the top non-Weblate one), so no one app drives the result.

This is what Weblate's `RemoveZeroSpace` autofix predicts. It is observational: it shows the
difference, not its cause (see Limits).

## Why P3 and P4 failed: an English pseudo-locale nobody listed

All 3,665 extra `mark` units in English come from one folder name, `values-en-rXC`, in 8
repositories (launchers and keyboards built from Android platform code, among others). Every
string there is the English text behind a long run of U+200E/U+200F marks. It is a
machine-generated English variant, not a translation. The pre-registration excluded the
pseudo-locales en-XA and ar-XB but did not know about en-XC, so these units counted as
left-to-right `mark` hits. That one gap fails P3. Together with `bidi`, it also fails P4.

Post-hoc checks, not pre-registered:

- Without `values-en-rXC`: 4,522 of 4,699 extra marks (96.2%) are in right-to-left languages, so P3
  would have held. The control ratio rises to 2.43 (Weblate 1,131 of 5,374,152; others 779 of
  8,988,162), and P2 still holds.
- P4 still fails without it. `bidi` has 924 units, and 867 of them are in the right-to-left
  languages, where the pre-registration counted every bidi control as unexpected. Most of the
  other 57 are in Arabic- or Hebrew-script catalogs that the language-code RTL list missed:
  Punjabi in Shahmukhi script (`values-pa-rPK`, 33), Ottoman Turkish (12), Judeo-Persian (4)
  and Najdi Arabic (2). In
  left-to-right text, `zwsp` (710) and `shy` (662) are the common classes.

## What the hits look like (AI agents read 15-25 rows each of `shy`, `zwsp`, `wj-bom`/`other-cf` and `en-XC` marks, plus a few `bidi` rows)

- **Soft hyphens (`shy`, 662 units)** split two ways. Most sit between two letters inside long
  Dutch, German and Norwegian compounds (`Standaard<U+00AD>videoformaat`). These are deliberate
  hyphenation points, not artifacts. Of the 657 `shy` rows in `hits.csv`, 121 have a soft hyphen
  next to a space, digit, punctuation or a string end, so about 82% are between-letter only.
  That pattern treats a neighbouring invisible character as a letter, so the share is approximate. The rest look accidental: `<U+00AD>Cambiar vista`, `Sì<U+00AD>`, four
  soft hyphens after a Chinese label, and one before an em dash in Ukrainian and Russian.
- **Zero-width spaces (`zwsp`)** are mostly copy-paste artifacts in the middle of a sentence. One
  app carries a doubled `<U+200B><U+200B>` at the same spot in many languages. Another has five
  after a two-character Chinese label.
- **Byte-order marks and word joiners (`wj-bom`, 167)**: stray U+FEFF at the start or end of a
  string (Crowdin projects among them), U+FEFF after `{name}` placeholders in one Luganda catalog
  (40 units), U+FEFF replacing the source's trailing spaces in one template that is shipped in
  many languages, and U+2060 inside Japanese and Thai words in one large app.
- **`other-cf` (5)**: U+2063 (invisible separator) at the end of Latvian strings in two apps.

## What this changed

l10n-guard 0.15.0 (pending its test job) adds an `invisible-char` warning. The census shaped its
exemptions: soft hyphens between two letters are not reported, and U+200B is not reported in
scripts that use it between words, nor marks and bidi controls in right-to-left text. Its check
works per string and uses script ranges, so a run of marks in an `en-XC` folder would still be
reported. That is correct for real catalogs and harmless for pseudo-locales, which are not
translated.

## Limits

- Observational. Weblate projects may differ in other ways. The control classes rule out "Weblate
  catalogs are simply cleaner" (they are not cleaner on those), but not every alternative.
- The platform label is per repository and comes from commit history. Strings imported before a
  project joined Weblate count as Weblate strings, which works against P2.
- `hits.csv` keeps at most 500 rows per repository, so two `en-XC` repositories are cut there.
  `summary.json` counts are complete.
- Characters are counted, not rendered. No native speaker checked any hit. Android `\uXXXX`
  escapes were decoded, as in the APK.
- The class read-through and the 82% soft-hyphen share are post hoc and approximate. They come
  from a pattern over `hits.csv`.
