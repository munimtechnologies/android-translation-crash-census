# Pre-registration: translated .lproj string tables the Xcode project never references

Marker: xcode-lproj census PREREG v1

Written 2026-11-10 by AI agents working for MV2 of Munim, Inc., before the job reads any
`project.pbxproj` or `.strings` file of the population. Code: `xcode_lproj_census.py`; tests:
`test_xcode_lproj_census.py` (both in this folder). The job prints the sha256 of this file before
it reads any repository. Licence: CC BY 4.0 for this text, Apache-2.0 for the code.

## Question

In an Xcode project, a localized string table (`Localizable.strings`, `InfoPlist.strings`,
`Main.strings`...) is a variant group: the project file lists one file per language
(`fr.lproj/Localizable.strings`, `de.lproj/Localizable.strings`...), and only the listed files are
copied into the app. A `<lang>.lproj/<Table>.strings` file that sits on disk beside listed
siblings but is not itself listed is never built into the app, and Xcode does not warn. This
happens when a translation platform or a contributor adds a new `.lproj` folder to the
repository without adding it in Xcode.

This is the iOS and macOS version of the `po/LINGUAS` gap measured in `linguas/` (51 of 526
Flathub repositories whose build reads `LINGUAS` left translations out). How often does it
happen in open-source Apple apps?

## Prior art (searched 2026-11-10)

- General "files not in the Xcode project" finders exist: xcutility (`norefs`, `unbuilt`),
  Frizlab's find-unreferenced-xcode-files, the old findxcprojorphan gem, and scripts on the
  xcodeproj libraries. They are pointed at source files (`*.swift`, `*.m`) one project at a time
  and do not treat a variant group's languages as a set.
- xcprojectlint checks the opposite direction (project references with no file on disk).
- Apple forum threads and issue trackers describe the symptom one project at a time (a new
  `.lproj` folder that never shows up in the app).
- We found no localization-aware check of this kind and no count across a population.

## Population

The 334 repositories marked `translated = yes` (status `ok`) in `ios-lproj/v2/repos.csv` of this
repository (the curated dkhamsing/open-source-ios-apps list, read on 2026-11-09), each read at the
commit recorded there, so the run is reproducible. That census looked only at `.lproj` folder
names, never at project files.

## Method (all in the code)

For each repository:

1. Every `*.xcodeproj/project.pbxproj` outside vendored folders (`Pods`, `Carthage`,
   `node_modules`, `vendor`, `third_party`, `build`, `.build`, `SourcePackages`, `Checkouts`...,
   and `.framework`, `.xcframework`, `.bundle`, `.app`, `.appex` folders), at most 30, is parsed
   as an old-style property list. Each file reference's repository path is resolved through its
   parent groups (`<group>`), the project folder (`SOURCE_ROOT`) and `projectDirPath`; absolute
   and build-product paths are ignored. Xcode 16 file-system-synchronized folders count as
   references to everything under them, and so does any reference to a folder (folder
   references, bundles).
2. Tables: every `<dir>/<lang>.lproj/<Table>.strings` outside vendored folders, grouped by
   `<dir>` and `<Table>`. Files in or under a folder that holds `Package.swift` or a `.podspec`
   are left out (Swift Package Manager and CocoaPods copy them by their own rules).
3. A table is **managed** when at least one of its language files is referenced directly by a
   project. In a managed table, a language file that is neither referenced nor under a
   referenced folder is **unreferenced**.
4. For up to 10 unreferenced files per repository the job reads the file and the same table in
   a reference language (`en`, else `Base`, `en-US`, `en-GB`) and counts keys, keys present in
   both, and keys whose text differs. **Substantive**: at least half of the compared keys
   differ; an empty file is not substantive; no reference file means unknown.
5. A repository is **governed** when it was read, has at least one managed table, and has no
   project-generator file (`project.yml`, `project.yaml`, `Project.swift`, `Workspace.swift`,
   `Tuist.swift`), since a generated project may be stale in the repository. It is **flagged**
   when it is governed and has at least one unreferenced file.
6. **Platform group**: the repository has a translation-platform config (`crowdin.yml`,
   `.tx/config`, `lokalise.yml`, `.phrase.yml`, `transifex.yml` and dot-file variants).

## Predictions (graded with integers in the code)

- **G (gate)**: at least 250 repositories read, at least 100 governed, and at most 5% of the
  parsed project files fail to parse. If G fails, P1-P3 are not testable.
- **P1**: between 2% and 20% of governed repositories are flagged (inclusive).
- **P2**: at least half of the unreferenced files with known content are substantive (needs at
  least 4 such files).
- **P3**: governed repositories with a translation-platform config are flagged at a higher rate
  than those without (needs at least 10 in each group and at least 4 flagged in all).
- **H1 (hand check)**: the job picks up to 12 flagged repositories by a fixed hash and one
  unreferenced file in each (`sample.csv`). A finding is **real** when, at the recorded commit:
  the file exists and holds at least one translated string; no `project.pbxproj` in the
  repository lists that language's file for the table (checked by reading the variant group);
  and nothing else ships it (no folder reference, synchronized folder, build-phase script,
  package or pod, and no project generator spec under another name). H1 holds if at least 4 in
  5 sampled findings are real (10 of 12), and needs at least 6 sampled.

## Exploratory, not graded

Unreferenced files by table name and language; how many unreferenced languages appear in the
project's `knownRegions` anyway; projects that fail to parse; repositories left out as
generated.

## Limits stated now

- Precision only: a file the project lists but no target copies is not counted (an undercount).
- The reference language heuristic misses tables with no English or Base file (`Main.strings`
  for storyboards), which stay "unknown".
- The population is one curated list and favours well-known, maintained apps.
- Code and tests were written and traced by hand without running them first; the job runs the
  tests before it reads anything, and stops if they fail. Any change after this file is public
  goes in DEVIATIONS.md.

Made with AI agents by MV2 of Munim, Inc. (mv2@munimtech.com).
