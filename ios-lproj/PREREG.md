# Pre-registration: country codes used as language codes in iOS `.lproj` folders

Marker: ios-lproj census PREREG v1
Written 2026-11-09 by AI agents working for MV2 of Munim, Inc. (mv2@munimtech.com), before any
repository in the population is read. Code: `lproj_census.py`, tests: `test_lproj_census.py`
(same folder, same commit). Licence: Apache-2.0 (code), CC BY 4.0 (text and data).

## Question

Apple apps keep each translation in a folder named `<language>.lproj`. iOS picks the folder whose
name matches a language in the user's preferred-language list, and Apple's naming rule is an
ISO 639 language code with optional script and region (Technical Q&A QA1828; "Language and
Locale IDs"). Czech is `cs`, Ukrainian `uk`, Japanese `ja`, Chinese `zh`. A folder named with the
**country** code instead (`cz.lproj`, `ua.lproj`, `jp.lproj`, `cn.lproj`) matches no language a
user can choose, so by that rule iOS never selects it from the system language setting. If the app
has no correctly named folder for that language, the translation ships but users never see it.

The companion Android census in this repository (`locale-mismatch/`) found 26 such folders in 23
of 2,386 F-Droid apps with translations (about 1%). We found no published count for Apple
platforms. App Store Connect has a warning for invalid locale folder names (ITMS-90176,
"Unrecognized Locale"), but we found no statement of whether it fires for well-formed codes such as
`cz`, and open-source apps often never pass through it.

## Population

Every unique GitHub repository named as a project `source` in
[dkhamsing/open-source-ios-apps](https://github.com/dkhamsing/open-source-ios-apps)
`contents.json`, read at that list's HEAD when the job starts (the commit is recorded in
`summary.json`). URLs are reduced to `https://github.com/<owner>/<repo>` and deduplicated without
regard to case. Projects hosted elsewhere are left out. Archived projects stay in. Each
repository is read once, at its default branch's HEAD, with a blobless depth-1 git fetch.

## Definitions (as coded)

- **Language folder:** a path component ending in `.lproj` (only the outermost one on a path). Its
  language is the part before the first `-` or `_` when that part is 2-3 letters, lowercased
  (`pt-BR` is `pt`, `zh_CN` is `zh`). The legacy names English, French, German, Japanese, Spanish,
  Italian and Dutch map to their codes. `Base.lproj` is not a language.
- **Vendored:** the folder path has a component named (case-insensitively) Pods, Carthage, vendor,
  vendors, node_modules, thirdparty, third_party, third-party, 3rdparty, .build, SourcePackages,
  external, externals, deps or submodules, or ending in `.framework` / `.xcframework`. Vendored
  folders are counted separately and are not part of P1-P4.
- **Country-code folder:** an own (not vendored) language folder whose language part is one of the
  21 codes l10n-guard 0.19.0 already uses for Android:
  cn cz ua jp by dk gr sp du vn al ir il hk us gb pk ge mx rs kz
  (meant: zh cs uk ja be da el es nl vi sq fa he zh en en ur ka es sr kk).
- **Has translations:** at least one own language folder whose language is not `en`.
- **Flagged repository:** has translations and at least one country-code folder.
- **Unreachable:** a flagged repository with a country-code folder for which no own folder exists
  for the meant language (for `il`, `he` or `iw`).
- **Holds a translation** (per folder, from up to 5 `.strings` files in it): if at least 5 keys
  are shared with the same file in a sibling `en`, `Base`, `English`, `en-US`, `en_US` or
  `en-GB` folder, "yes" when at least half of the shared values differ, else "no". Otherwise, for
  codes whose language has its own script (cn hk jp ua by kz gr il ir pk ge), "yes" when at least
  half of the values with letters (at least 5) contain that script, else "no". Otherwise unknown.

## Gate

At least 1,000 repositories read and at least 300 with translations. If not, P1-P4 are NOT
TESTABLE and no rate is claimed.

## Predictions (graded by code, integer arithmetic)

- **P1.** Between 0.3% and 5.0% of repositories with translations are flagged
  (HELD if 1000*k >= 3*n and 20*k <= n).
- **P2.** At least half of the flagged repositories are unreachable (testable with >= 4 flagged).
- **P3.** The most frequent code among country-code folders is one of cn, cz, ua, jp; on a tie,
  every tied code must be in that set (testable with >= 4 folders).
- **P4.** At least 3 in 4 country-code folders with known content hold a translation, not an
  English copy (testable with >= 4 such folders).

## Hand check (H1, next run, before any claim of precision)

Up to 12 flagged repositories, chosen by SHA-256 of "ios-lproj census v1|<repo>", one
country-code folder each (also by hash), listed in `sample.csv`. Each is read at the recorded
commit and labelled **real** when (a) the folder name is a country code standing for a language,
(b) the folder is part of what the app ships (named in the Xcode project, a Swift package's
resources, or a project generator's sources), and (c) no app code loads it by that code (an
in-app language switcher that asks for `cz` itself would make it work). H1 holds if
real*4 >= 3*checked, testable with at least 6 checked. Borderline calls are reported.

## Exploratory (no predictions)

Country-code folders in vendored paths and which codes; real ISO 639 codes that are also country
codes and may be meant for another language (`kr` is Kanuri, not Korean; also se, ch, si, ee, br),
with script evidence; country codes used as language keys inside Xcode String Catalogs
(`.xcstrings`); names with region `UK` instead of `GB`; the 60 most common `.lproj` names;
whether each flagged folder is in a `knownRegions` list and whether app code quotes its name.

## Limits stated now

- The rule "iOS never selects it" comes from Apple's documentation, not from a device test.
- One public list of open-source iOS apps, which over-represents small and archived projects.
- Folder names only for P1-P3; strings inside storyboards, `.stringsdict` and catalogs are not
  graded.
- The code-mention search is textual and cannot prove an in-app switcher exists or not.

## What happens next

Results go to `ios-lproj/RESULTS.md` with the job outputs unchanged under `ios-lproj/v1/` and the
hand labels in a separate `labels.csv`. If H1 holds, l10n-guard gets an `.lproj` version of its
existing `locale-code` warning, and confirmed cases are reported upstream one at a time, where
each project's contribution rules allow it, saying the check was made with AI agents.
