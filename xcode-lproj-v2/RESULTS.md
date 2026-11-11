# Results: translated .lproj string tables the Xcode project never references (v2, pre-registered)

Graded 2026-11-11 against [PREREG.md](PREREG.md) (marker "xcode-lproj census PREREG v2", sha256
2d53d43d9419d0e28550728837887147dcd565038308f989a966e80dfdceb81a, printed by the job before it read
any repository). Job `xcode-lproj-v2`, run on 2026-11-11 00:38-00:43 UTC; its unit tests passed
before it read anything. Made with AI agents by MV2 of Munim, Inc. (mv2@munimtech.com). Text CC BY
4.0, code Apache-2.0.

## Verdict first: P1, P2 and the hand check FAILED, so no rate of real findings is claimed

| Prediction | Pre-registered rule | Result |
|---|---|---|
| G (gate) | at least 120 translated repositories read, at least 80 governed, at most 5% of projects unparsed | **PASSED** (130 read, 82 governed, 1 of 158 projects unparsed) |
| **P1** | 2% to 15% of governed repositories flagged | **FAILED: 21 of 82 (25.6%)** |
| **P2** | 30% to 80% of governed repositories with any unreferenced file are flagged under the v2 rule | **FAILED: 21 of 23 (91%)** |
| P3 | repositories with a translation-platform config flagged more often | NOT TESTABLE (only 8 platform repositories; 10 needed) |
| **H1** | at least 10 of 12 sampled findings real | **FAILED: 7 of 12 real** |

The population was the open-source macOS apps list at a fixed commit (947 GitHub repositories,
939 read), with every repository from v1 removed. G passed narrowly. P1 and P2 failed on the high
side: the v2 content rule removed almost nothing (only 2 of the 23 repositories with an
unreferenced file dropped out), and the flagged share was far above the predicted range. H1 failed
too, so **25.6% is not a rate of real untranslated apps** and must not be quoted as one.

## The hand check (labels in [labels.csv](labels.csv))

For each of the 12 repositories the job picked by a fixed hash, the sampled file was read at the
recorded commit. The check covered every `project.pbxproj` reference to that table (Sourcegraph
code search pinned to the commit, or the raw project file read in full when the commit was not
indexed), `knownRegions`, folder references, synchronized folders, shell-script build phases and,
for Cyberduck, its Maven and Ant build files.

**Not real (5), all in two groups that the rule could have caught:**

- **English, not a translation (3):** Adium `en_CA` (a copyright line that differs from `en` only by
  its years), Cakebrew `en` and Thor `en` (English storyboard strings; the Base files already show
  the same text). The rule compares a file with English, and these files *are* English, so they
  passed as "different from English" or had nothing to compare with.
- **A regional copy of a language that already ships (2):** Quicksilver `ja_JP` (the listed
  `ja.lproj` holds the same Japanese string) and Turbo Boost Switcher `es-ES` (an older 44-entry
  copy of the listed 65-entry `es.lproj`). Both are marked borderline, because no project lists the
  regional folder itself; flipping both to real gives 9 of 12, which still fails H1.

**Real (7):** Gray `ja`, LyricsX `hr`, syncthing-macos `tr`, gSwitch `tr`, PhotoMiner `hr`,
Cyberduck `cy` (the crash-report dialog; borderline, see labels.csv) and Maccy `fa`. Five of the
seven repositories have commits since 2024-11-10. Flipping Cyberduck to not real gives 6 of 12;
the verdict is FAILED in every combination.

## Why it failed, and what is a hypothesis now

v1 failed because files with no translation (empty files, templates, build variables) were
counted. v2 removed those, and in this sample none of them came back. The new false findings are a
different kind: English-locale files (`en`, `en_CA`, also `Base` in the full output) and regional
copies such as `ja_JP` beside `ja`.

**Post-hoc, not pre-registered:** in the full output, 4 of the 21 flagged repositories (Adium,
Juice, Cakebrew, Thor) are flagged only by English-locale files, and Turbo Boost Switcher only by
`es-ES`. Removing those 5 leaves at most 16 of 82 (19.5%), still above P1's upper bound. A v3 rule
would skip `en`, `en-*`, `English` and `Base` files and any file whose base language the table
already lists. That rule was found after reading the labels, so it is a hypothesis. Both curated
app lists (iOS in v1, macOS here) are now used up, so testing it needs a new population.

## What the real findings show (exploratory)

- **syncthing-macos** has Turkish and German translation folders, but its project lists only
  English and Spanish. The maintainers already know: PR #284 ("Not yet added to the XCode project
  file") asks for someone with Xcode to add the files. Syncthing's contributing rules do not
  accept contributions that are wholly or mostly AI-generated, so MV2 will not send a fix.
- **Maccy** (a clipboard manager with frequent releases) has 10 languages on disk that are in no
  variant group and not in `knownRegions`: bn, ca, el, eo, fa, fi, hi, id, sv, ta. Indonesian is
  fully translated in the five tables the job read. These files come from Hosted Weblate, which
  adds the `.strings` files but cannot edit the Xcode project.
- In both repositories the pattern is the same: a translation platform or a translator adds the
  files, but someone with Xcode has to register them in the project by hand, so a finished
  translation can sit unused until someone does.
- 13 of the 40 governed repositories with a commit since 2024-11-10 are flagged (unverified
  detector output, same caveats as P1). 49 of the 175 confirmed unreferenced files are in a
  language the project declares in `knownRegions`. 9 repositories were left out as generated
  (XcodeGen/Tuist); no file was left unread by the 50-file cap.

## Files

- [summary.json](summary.json), [sample.csv](sample.csv) and [unreferenced.csv](unreferenced.csv)
  are byte-identical job outputs.
- [labels.csv](labels.csv): the hand labels with the evidence for each.

Limits: one curated list that favours well-known apps; precision only, never recall; String
Catalogs (`.xcstrings`) are out of scope; a file the project lists but no target copies is not
counted; the hand check read project files, not built apps.

Made with AI agents by MV2 of Munim, Inc. (mv2@munimtech.com).
