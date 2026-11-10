# Pre-registration: translated .lproj string tables the Xcode project never references (v2)

Marker: xcode-lproj census PREREG v2

Written 2026-11-10 by AI agents working for MV2 of Munim, Inc., before the job reads any repository
of the population. Code: [xcode_lproj_v2.py](xcode_lproj_v2.py); tests:
[test_xcode_lproj_v2.py](test_xcode_lproj_v2.py). The job prints the sha256 of this file before it
reads any repository, and stops if the unit tests fail. Licence: CC BY 4.0 for this text,
Apache-2.0 for the code.

## Why a v2

[v1](../xcode-lproj/RESULTS.md) failed its hand check: 6 of 12 sampled findings were real. The
structural rule (a language file on disk that no `PBXVariantGroup` lists) was right every time, but
v1 counted files that hold no translation: empty files, template comments, Xcode's unfilled
copyright template, `$(PRODUCT_NAME)`, an English copy and a value identical to English. v1's
"substantive" label separated real from not real in that sample, but this was seen after the
labels, so it is only a hypothesis. v2 turns it into a rule fixed in advance and tests it on
**repositories v1 never saw**.

## Population

Every GitHub repository linked as `repo_url` in `applications.json` of the open-source macOS apps
list ([serhii-londar/open-source-mac-os-apps](https://github.com/serhii-londar/open-source-mac-os-apps),
CC0-1.0) at commit `23b6184ebcee27318c28e4d40661f4435a697a3d` (2026-10-31). Links are reduced to
`github.com/<owner>/<repo>` and deduplicated regardless of case. Every repository in v1's source
table (`ios-lproj/v2/repos.csv`, all rows) is removed. Each repository is read at the head of its
default branch on the day the job runs, and the commit is recorded. A repository is **translated**
when it holds at least one `<lang>.lproj/*.strings` file outside vendored folders in a language
other than English or Base.

## Method (all in the code; differences from v1 in bold)

1. Project files, references, folder references, synchronized folders, vendored folders, and
   Swift-package/CocoaPods folders are handled exactly as in v1.
2. **Generated projects:** `project.yml` or `project.yaml` (XcodeGen) anywhere outside vendored
   folders; `Project.swift` or `Workspace.swift` only when the repository also has a `Tuist` folder,
   a `Tuist.swift` or a `.tuist-version` file. (v1 also left out apps with a data model named
   `Project.swift`.)
3. A table is managed when at least one of its language files is referenced directly; in a managed
   table, a language file neither referenced nor under a referenced folder is **unreferenced**.
4. **Up to 50** (v1: 10) unreferenced files per repository are read, with the same table in a
   reference language (`en`, `Base`, `en-US`, `en-GB`, **`English`**).
5. **Translated entry:** after trimming spaces, the value is not empty, is not equal to its key,
   contains no Xcode template placeholder (guillemet-wrapped capitals, or `__Name__`), still holds
   a letter after build variables (`$(...)`, `${...}`) and format specifiers (`%@`, `%1$d`...) are
   removed, and, when the reference file has the key, differs from the reference text.
6. **Confirmed file:** at least one translated entry and, when keys could be compared with the
   reference, at least half of the compared keys differ.
7. A repository is **governed** when it was read, is translated, has at least one managed table and
   no generator file. It is **flagged** when it is governed and has at least one confirmed
   unreferenced file. Platform group: a translation-platform config file, as in v1.

## Predictions (graded with integers in the code)

- **G (gate):** at least 120 translated repositories read, at least 80 governed, at most 5% of
  parsed project files unparsed. If G fails, P1-P3 and H1 are not testable.
- **P1:** between 2% and 15% (inclusive) of governed repositories are flagged.
- **P2:** of governed repositories with any unreferenced file (the v1 rule), between 30% and 80%
  (inclusive) are flagged under the v2 rule. Needs at least 10 such repositories.
- **P3 (replication of v1's P3):** governed repositories with a translation-platform config are
  flagged at a higher rate than those without. Needs at least 10 in each group and at least 4
  flagged in all.
- **H1 (hand check):** the job picks up to 12 flagged repositories by a fixed hash and one
  confirmed file in each (`sample.csv`). A finding is **real** when, at the recorded commit, the
  file holds at least one translated string, no `project.pbxproj` in the repository lists that
  language's file for the table, and nothing else ships it (no folder reference, synchronized
  folder, build-phase script, package or pod, and no project generator under another name). H1
  holds if at least 10 of 12 are real; with fewer than 12 sampled, at least 5 in 6 of those
  sampled must be real (integer rule: 6 x real >= 5 x sampled); with fewer than 6 sampled it is
  not testable and **no rate is claimed**. A label that a reasonable reader could set either way is
  marked borderline, and RESULTS.md reports the verdict both ways if the flip would change it.

Only if G, P1 and H1 all hold will the flagged share be reported as an estimate of real
untranslated languages in this population.

## Exploratory, not graded

Flagged share among repositories with a commit since 2024-11-10 (active); files by table and
language; how many confirmed files are in a language the project already declares in
`knownRegions`; files left unread by the 50-file cap.

## Limits stated now

- Precision only, never recall. A file the project lists but no target copies is not counted, and
  String Catalogs (`.xcstrings`) are out of scope.
- The rule in step 5 was designed after reading v1's 12 labels. It is tested here only on
  repositories v1 never read, and v1's labels are not reused.
- One curated list, which favours known apps. Many entries are not Apple-native (Electron, web,
  cross-platform), so they are not translated in the `.lproj` sense and drop out.
- The code and tests were written and traced by hand without being run first. The job runs the
  tests before it reads anything and stops if they fail. Any change made after this file is public
  goes in DEVIATIONS.md.

Made with AI agents by MV2 of Munim, Inc. (mv2@munimtech.com).
