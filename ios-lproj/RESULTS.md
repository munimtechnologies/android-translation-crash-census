# Results: iOS translation folders named with a country code

Graded 2026-11-10 against [PREREG.md](PREREG.md) (sha256
`9fec06e0c2bccc487ac24e0884bda6843afce05a4c1ebcffae9ab40c1f8acd1e`, printed by the job before it read
any repository). Made with AI agents by MV2 of Munim, Inc. Code Apache-2.0, text and data CC BY 4.0.
The run is job `ios-lproj-v2` (2026-11-09, 21:50-21:53 UTC); the first run stopped before reading
anything, see [DEVIATIONS.md](DEVIATIONS.md).

## Outcome: the predicted problem was not found

Among 1,633 open-source iOS apps read, 334 ship translations, and **none** of them has a translation
folder named with one of the 21 country codes we looked for (`cz.lproj`, `ua.lproj`, `cn.lproj`,
`jp.lproj`, `dk.lproj` and the rest). P1 predicted 0.3% to 5.0% of them; the result is 0 of 334, so
**P1 FAILED**, and P2, P3, P4 and the hand check H1 have nothing to grade.

| | Prediction | Result | Verdict |
|---|---|---|---|
| Gate | >= 1,000 repositories read and >= 300 with translations | 1,633 read (55 could not be fetched: deleted or private), 334 with translations | PASSED |
| P1 | 0.3% to 5.0% of repositories with translations are flagged | **0 of 334 (0.0%)** | **FAILED** |
| P2 | at least half of flagged repositories have no correctly named folder for the language | 0 flagged | NOT TESTABLE |
| P3 | the most common code is cn, cz, ua or jp | 0 folders | NOT TESTABLE |
| P4 | >= 3 in 4 country-code folders with known content hold a translation | 0 folders | NOT TESTABLE |
| H1 | >= 3 in 4 sampled flagged folders are real (>= 6 checked) | sample of 0 | NOT TESTABLE |

No vendored copy (Pods, Carthage and similar folders) had a country-code folder either, and none of
the 105 repositories with Xcode string catalogs (`.xcstrings`) used a country code as a language.

## What this means

In the companion Android census, 23 of 2,386 F-Droid apps with translations (about 1%) had a folder
named with a country code (`values-cz`, `values-ua`, ...). Here, in a smaller population of iOS apps,
there were none. A rough comparison, added after the fact and not pre-registered: if iOS apps had the
same rate as the Android ones (0.96%), seeing none in 334 would happen about 4% of the time
(0.9904^334), and with 0 of 334 the usual 95% upper bound on the iOS rate is about 0.9% (3/334). So
the data suggest the mistake is rarer on iOS, but they cannot show by how much.

A plausible reason, not tested here: on iOS a translation folder is usually created by Xcode when a
developer picks a language from Apple's list, so nobody types its name, while Android's `values-xx`
folders are often named by hand or by a translation platform's export settings.

Our prediction was based on the Android rate. It was wrong, and we report it as it is.

## Exploratory: valid language codes that look like country codes (not graded)

The job also listed folders named `br`, `si`, `se`, `ch`, `ee` and `kr` (it found no `kr`). Each of
the other five is a real language code (Breton, Sinhala, Northern Sami, Chamorro, Ewe) that is also a country code
(Brazil, Slovenia, Sweden, Switzerland, Estonia), so such a folder may be either. From
[v2/summary.json](v2/summary.json):

| Code | Folders | Of which the country's language also has a folder |
|---|---|---|
| `si` | 33 | 30 have `sl` |
| `br` | 27 | 27 have `pt` |
| `se` | 6 | 5 have `sv` |
| `ch` | 1 | 1 has `zh` |
| `ee` | 1 | 1 has `et` |

Almost all of them sit beside the folder for the country's language, which suggests they are what
they say (most come from translation platforms that offer Sinhala and Breton). One spot check:
Bitwarden's `BitwardenResources/Localizations/si.lproj/Localizable.strings` is written in Sinhala
script, a real Sinhala translation. We did not check the others. Some of these folders are copies of
English (for example `holds_translation = no` rows in [v2/folders.csv](v2/folders.csv)); that is a
different, known problem (untranslated exports) and was not part of this study.

## Limits

- The population is the curated [open-source-ios-apps](https://github.com/dkhamsing/open-source-ios-apps)
  list (list commit `8018bb2`), which leans towards well-known, maintained apps. A wider sample of
  iOS code could still contain the mistake.
- We looked only for the 21 codes in the pre-registration, at each repository's default branch.
- Whether a folder is reachable is judged from Apple's naming rules, not from device tests.

## Files

- [PREREG.md](PREREG.md), [lproj_census.py](lproj_census.py), [test_lproj_census.py](test_lproj_census.py),
  [DEVIATIONS.md](DEVIATIONS.md) (published before the run)
- [v2/](v2/): job outputs, unchanged: `summary.json`, `repos.csv` (one row per repository, with the
  fetch error where there was one), `folders.csv` (every folder the job looked at more closely),
  `results.jsonl`, `sample.csv` (empty: nothing to sample)
