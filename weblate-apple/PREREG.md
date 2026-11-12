# Pre-registration: Weblate-managed Apple translations that never ship (census xcode-lproj v3)

Marker: xcode-lproj census PREREG v3. Written 2026-11-12, after the Hosted Weblate listing
(stage 1, [PLAN.md](PLAN.md)) and before any repository of the population has been read for
this census. Made with AI agents by MV2 of Munim, Inc. (mv2@munimtech.com). Text CC BY 4.0;
code (`xcode_lproj_v3.py`, `test_xcode_lproj_v3.py`, `fetch_v2.py`) Apache-2.0.

## Question

Weblate commits a new language's `.strings` file into `<lang>.lproj/` folders, but it does not
edit `project.pbxproj`. In a classic Xcode project, a localized string table ships only for the
languages its variant group (`PBXVariantGroup`) lists, so a language Weblate adds is committed
but never built into the app until someone registers it in Xcode. Projects that use
file-system-synchronized folders (Xcode 16) or Swift packages don't have this gap, and neither
would a String Catalog (`.xcstrings`), but Weblate can't translate String Catalogs yet
([WeblateOrg/weblate#10848](https://github.com/WeblateOrg/weblate/issues/10848), open, checked
2026-11-12), so Apple apps on Weblate keep per-language files in `.lproj` folders. The stage 1
listing found 92 `strings`, 3 `stringsdict`, 2 `json`, 1 `html` and 1 `go-i18n-json-v2`
components and no `xcstrings` component. How often do
the open-source apps translated on Hosted Weblate carry finished translations that their Xcode
project never ships?

## Population (fixed by stage 1)

Every repository behind a Hosted Weblate component whose file format is Apple strings or whose
file mask contains `.lproj/`: [v1/apple_components.csv](v1/apple_components.csv), 99
components, listed on 2026-11-12 from Weblate's public component API (all 11,363 components
read, listing complete). Components with no repository URL (`local:`) are dropped, which leaves
35 repositories. Each one is read at the branch most of its Weblate components commit to (falling
back to the default branch if that fetch fails), with a blobless depth-1 git fetch.

## What is counted

- Project files: every `*.xcodeproj/project.pbxproj` outside vendored folders, read with census
  v2's parser (`xcode_lproj_v2.py`, fetched unchanged by `fetch_v2.py`; the job records whether
  its sha256 matches the v2 run's `982fdafd...`). File references and synchronized folders both
  count as references. Project files up to 20 MB are read (v2: 5 MB).
- Weblate-managed string tables: `<dir>/<lang>.lproj/<Table>.strings` paths that match one of
  the repository's Weblate file masks (`*` = one path segment), outside vendored folders and
  outside folders that hold a `Package.swift` or `.podspec`.
- A table is managed by Xcode when at least one of its languages is referenced file by file.
- A lost file is a language of a managed table that the project does not reference, except:
  (a) English and Base (`en`, `en-*`, `en_*`, `English`, `Base`); (b) a regional copy
  (`ja_JP`, `es-ES`, `es-419`) of a plain language the same table already ships. Script
  subtags (`zh-Hant`) are never treated as regional copies. Rules (a) and (b) were found post
  hoc in census v2; this is their first pre-registered use.
- A lost file is confirmed when v2's content rule says it is a real translation (at least one
  translated entry and, when compared with the English or Base table, at least half of the
  compared entries differ).
- A repository is governed when it was read, has at least one non-English Weblate-managed file,
  at least one Xcode-managed Weblate table, and no XcodeGen or Tuist project generator. It is
  flagged when it has at least one confirmed lost file.
- A lost language is whole when no `.lproj` file of that language anywhere in the repository
  is referenced by the project (the language doesn't ship at all), and partial otherwise.

## Predictions (fixed before any population repository is read)

- G (gate): at least 30 of the 35 repositories read without error, at least 10 governed, and at
  most 2 project files unparsed. If G fails, P1 and P2 are not testable.
- P1: between 15% and 50% (inclusive) of governed repositories are flagged.
- P2: at least half of the lost languages (repository and language pairs with a confirmed lost
  file) are whole. Our guess at the mechanism: a translator adds a language on Weblate, and
  nobody registers it in Xcode. Not testable with fewer than 3 lost languages.
- H (hand check): up to 12 flagged repositories (sorted by a SHA-256 key of the repository URL,
  one confirmed lost file each, written to `sample.csv`) are checked by hand at the recorded
  commit. A case is confirmed when the file exists and is a real translation, the project
  file has no reference to it (searched for `<lang>.lproj/<Table>`, the language inside the
  table's variant group, and synchronized folders above it), no build-phase script copies
  `.lproj` folders, and the app is built from that Xcode project. H holds if at least 90% are
  confirmed. Not testable with fewer than 3.

Exploratory, not predicted: the same repositories counted by census v2's rule (every table,
not only Weblate's, and no English or regional-copy exclusions), languages and tables most
often lost, and lost languages already listed in `knownRegions`.

Unit tests (`test_xcode_lproj_v3.py`, offline) run first.

## Cases seen before this pre-registration

Two repositories in this population were flagged in census v2, which used a different
population. **p0deje/Maccy** has 10 Weblate languages not registered in `Maccy.xcodeproj`
(reported in [p0deje/Maccy#1635](https://github.com/p0deje/Maccy/issues/1635)).
**syncthing/syncthing-macos** has German and Turkish folders that are not in the project file
(its PR #284 says so). Both count if they are still flagged; together they are expected to be
at most 2 of 10 or more governed repositories, so P1 still needs at least one more.

## Limits

One snapshot of one platform's public projects (Hosted Weblate). Apps built from a generated
project, a Swift package or a script that copies `.lproj` folders are outside what the code
measures. The hand check covers only the sampled file of each flagged repository. A lost
language may be held back on purpose (an unfinished translation), and the census cannot see
intent. Results are published unchanged, negatives first, with any deviations stated.

## What it is for

If P2 and H hold, the result supports a short note for Weblate's documentation on Apple
`.strings` projects (a new language also needs registering in Xcode, or a String Catalog), and
one-language fixes offered to the affected projects one at a time, each checked by hand first,
with AI disclosed.
